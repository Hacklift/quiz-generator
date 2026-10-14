from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from bson import ObjectId
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.core.config import settings
from server.app.core.dependencies import get_current_user_optional
from server.app.core.rate_limiter import limiter
from server.app.organizations.dependencies import get_optional_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.db.core.connection import get_user_sessions_collection, get_users_collection
from server.app.quiz.routes import grading
from server.app.quiz.services.quiz_grading_service import QuizGradingService
from server.app.quiz.services.quiz_practice_access import QuizPracticeAccess
from server.tests.test_quiz_attempts import (
    FakeAttemptRepository,
    FakeOrganizationRepository,
    FakeQuizRepository,
    FakeReferenceRepository,
    FailingAttemptRepository,
    build_quiz_document,
)


@pytest.fixture
def grading_app(monkeypatch):
    quiz = build_quiz_document()
    attempts = FakeAttemptRepository()
    service = QuizGradingService(
        quiz_access=QuizPracticeAccess(FakeOrganizationRepository()),
        quiz_repository=FakeQuizRepository({str(quiz.id): quiz}),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )
    monkeypatch.setattr(grading, "QuizGradingService", lambda: service)
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.include_router(grading.router, prefix="/api")
    async def optional_context(current_user=Depends(get_current_user_optional)):
        if current_user is None:
            return None
        return OrganizationContext(
            organization_id="org-1", organization_kind="personal", membership_role="owner",
            principal=OrganizationPrincipal(user_id=str(current_user.id), session_id="session-1"),
            membership={},
        )
    app.dependency_overrides[get_optional_active_organization_context] = optional_context
    return app, quiz, service, attempts


def submission(quiz):
    return {"answers": [
        {"question": question.question, "user_answer": question.correct_answer}
        for question in quiz.questions
    ]}


@pytest.mark.asyncio
async def test_grading_write_failure_returns_scores_and_save_status(grading_app):
    app, quiz, service, _ = grading_app
    service.attempt_repository = FailingAttemptRepository()
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 200
    assert response.headers["x-quiz-attempt-status"] == "failed"
    assert all(result["is_correct"] for result in response.json())


@pytest.mark.asyncio
async def test_authenticated_grading_saves_the_attempt(grading_app):
    app, quiz, _, attempts = grading_app
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 200
    assert response.headers["x-quiz-attempt-status"] == "saved"
    assert len(attempts.attempts) == 1
    assert attempts.attempts[0].user_id == "user-1"


@pytest.mark.asyncio
async def test_real_access_token_resolves_the_attempt_owner(grading_app):
    app, quiz, _, attempts = grading_app
    user_id = ObjectId()
    users = SimpleNamespace(
        find_one=AsyncMock(return_value={
            "_id": user_id, "username": "learner", "email": "learner@example.com",
            "status": "pending_verification", "is_verified": False,
            "last_seen_at": datetime.now(timezone.utc),
        }),
    )
    sessions = SimpleNamespace(find_one=AsyncMock(return_value={"session_id": "session-1"}))
    app.dependency_overrides[get_users_collection] = lambda: users
    app.dependency_overrides[get_user_sessions_collection] = lambda: sessions
    token = jwt.encode(
        {"sub": str(user_id), "jti": "token-1", "sid": "session-1", "type": "access",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/quizzes/{quiz.id}/grade", json=submission(quiz),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.headers["x-quiz-attempt-status"] == "saved"
    assert attempts.attempts[0].user_id == str(user_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("token_kind", ["absent", "invalid", "expired"])
async def test_optional_auth_grading_remains_available_without_a_valid_token(grading_app, token_kind):
    app, quiz, _, attempts = grading_app
    users = SimpleNamespace(find_one=AsyncMock())
    sessions = SimpleNamespace(find_one=AsyncMock())
    app.dependency_overrides[get_users_collection] = lambda: users
    app.dependency_overrides[get_user_sessions_collection] = lambda: sessions
    headers = {}
    if token_kind == "invalid":
        headers["Authorization"] = "Bearer invalid-token"
    elif token_kind == "expired":
        token = jwt.encode(
            {"sub": "user-1", "jti": "token-1", "sid": "session-1", "type": "access",
             "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM,
        )
        headers["Authorization"] = f"Bearer {token}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz), headers=headers)
    assert response.status_code == 200
    assert response.headers["x-quiz-attempt-status"] == "not-requested"
    assert attempts.attempts == []
    users.find_one.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("authenticated", [False, True])
async def test_incomplete_submission_is_rejected_before_persistence(grading_app, authenticated):
    app, quiz, _, attempts = grading_app
    if authenticated:
        app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    payload = submission(quiz)
    payload["answers"].pop()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=payload)
    assert response.status_code == 400
    assert attempts.attempts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", [None, "other-user"])
async def test_grading_cannot_reveal_another_users_private_answer_key(grading_app, user_id):
    app, quiz, _, attempts = grading_app
    quiz.owner_user_id = "owner-1"
    quiz.organization_id = "org-2"
    quiz.visibility = type(quiz.visibility).PRIVATE
    if user_id:
        app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 404
    assert attempts.attempts == []


@pytest.mark.asyncio
async def test_deleted_quiz_cannot_be_graded(grading_app):
    app, quiz, _, attempts = grading_app
    quiz.status = type(quiz.status).DELETED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 404
    assert attempts.attempts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [403, 409])
async def test_authenticated_context_failures_do_not_silently_grade_as_guest(grading_app, status_code):
    from fastapi import HTTPException

    app, quiz, _, attempts = grading_app
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    async def unavailable_context():
        raise HTTPException(status_code=status_code, detail="Organization unavailable")
    app.dependency_overrides[get_optional_active_organization_context] = unavailable_context
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == status_code
    assert attempts.attempts == []


@pytest.mark.asyncio
@pytest.mark.parametrize("role,creator,expected", [
    ("learner", "user-1", 200),
    ("learner", "another-user", 403),
    ("author", "another-user", 200),
    ("facilitator", "another-user", 200),
    ("admin", "another-user", 200),
    ("guardian", "user-1", 403),
    ("auditor", "user-1", 403),
])
async def test_private_grading_obeys_membership_content_policy(grading_app, role, creator, expected):
    app, quiz, _, attempts = grading_app
    quiz.visibility = type(quiz.visibility).PRIVATE
    quiz.owner_user_id = creator
    quiz.created_by_user_id = creator
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    app.dependency_overrides[get_optional_active_organization_context] = lambda: OrganizationContext(
        organization_id="org-1", organization_kind="corporate", membership_role=role,
        principal=OrganizationPrincipal(user_id="user-1", session_id="session-1"), membership={},
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == expected
    assert len(attempts.attempts) == (1 if expected == 200 else 0)


@pytest.mark.asyncio
async def test_public_grading_stops_when_source_organization_is_inactive(grading_app):
    app, quiz, service, attempts = grading_app
    service.quiz_access.organizations.get_active = AsyncMock(return_value=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 404
    assert attempts.attempts == []
