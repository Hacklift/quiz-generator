from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.core.config import settings
from server.app.core.dependencies import get_current_user_optional
from server.app.core.rate_limiter import limiter
from server.app.db.core.connection import get_user_sessions_collection, get_users_collection
from server.app.quiz.routes import grading
from server.app.quiz.services.quiz_grading_service import QuizGradingService
from server.tests.test_quiz_attempts import (
    FakeAttemptRepository,
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
        quiz_repository=FakeQuizRepository({str(quiz.id): quiz}),
        reference_repository=FakeReferenceRepository(),
        attempt_repository=attempts,
    )
    monkeypatch.setattr(grading, "QuizGradingService", lambda: service)
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.include_router(grading.router, prefix="/api")
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
async def test_grading_returns_per_question_correctness_and_explanations(grading_app):
    app, quiz, _, attempts = grading_app
    app.dependency_overrides[get_current_user_optional] = lambda: SimpleNamespace(id="user-1")
    # Add an explanation to the first question
    quiz.questions[0].explanation = "HTTP is the standard application protocol for distributed, collaborative hypermedia."
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json=submission(quiz))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["is_correct"] is True
    assert data[0]["result"] == "Correct"
    assert data[0]["correct_answer"] == "HTTP"
    assert data[0]["explanation"] == "HTTP is the standard application protocol for distributed, collaborative hypermedia."
    assert len(attempts.attempts) == 1
    assert attempts.attempts[0].question_results[0].explanation == "HTTP is the standard application protocol for distributed, collaborative hypermedia."

