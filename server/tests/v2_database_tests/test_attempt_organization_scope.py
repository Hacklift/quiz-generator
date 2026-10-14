from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.core.dependencies import get_current_user
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.quiz.repositories.v2.models.reference_models import QuizAttemptDocumentV2
from server.app.quiz.repositories.v2.repositories.attempt_repository import QuizAttemptV2Repository
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.routes import attempts
from server.app.quiz.services.quiz_attempt_service import QuizAttemptService
from server.app.quiz.services.quiz_grading_service import QuizGradingService
from server.tests.test_quiz_attempts import FakeReferenceRepository, build_quiz_document


def context(organization_id="org-1", user_id="user-1", kind="corporate"):
    return OrganizationContext(
        organization_id=organization_id, organization_kind=kind, membership_role="owner",
        principal=OrganizationPrincipal(user_id=user_id, session_id="session-1"), membership={},
    )


def attempt_payload(**changes):
    return QuizAttemptDocumentV2(
        user_id="user-1", organization_id="org-1", created_by_user_id="user-1",
        quiz_id="missing-quiz", question_results=[], score=0, percentage=0,
    ).model_copy(update=changes)


@pytest.mark.asyncio
async def test_attempt_routes_isolate_same_user_across_organizations(test_db, monkeypatch):
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    own = await repository.insert_attempt(attempt_payload())
    foreign = await repository.insert_attempt(attempt_payload(organization_id="org-2"))
    other_user = await repository.insert_attempt(attempt_payload(user_id="user-2", created_by_user_id="user-2"))
    monkeypatch.setattr(attempts, "quiz_attempt_service", QuizAttemptService(
        quiz_repository=QuizV2Repository(test_db.quizzes_v2), attempt_repository=repository,
    ))
    app = FastAPI()
    app.include_router(attempts.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    app.dependency_overrides[get_active_organization_context] = lambda: context()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        listing = await client.get("/api/quiz-attempts")
        assert listing.status_code == 200
        assert [row["_id"] for row in listing.json()] == [str(own.id)]
        for inaccessible in (foreign, other_user):
            url = f"/api/quiz-attempts/{inaccessible.id}"
            assert (await client.get(url)).status_code == 404
            assert (await client.delete(url)).status_code == 404
        assert (await client.delete(f"/api/quiz-attempts/{own.id}")).status_code == 200
        assert (await client.get(f"/api/quiz-attempts/{own.id}")).status_code == 404
    assert (await test_db.quiz_attempts_v2.find_one({"_id": own.id}))["deleted_at"] is not None
    assert (await test_db.quiz_attempts_v2.find_one({"_id": foreign.id}))["deleted_at"] is None


@pytest.mark.asyncio
async def test_attempt_repository_legacy_reads_require_explicit_personal_scope(test_db):
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    legacy = attempt_payload().model_dump(by_alias=True, exclude={"organization_id", "created_by_user_id"})
    await test_db.quiz_attempts_v2.insert_one(legacy)
    assert await repository.list_attempts_for_user("user-1", organization_id="org-1") == []
    recovered = await repository.list_attempts_for_user(
        "user-1", organization_id="personal-1", allow_legacy_personal=True,
    )
    assert [row.id for row in recovered] == [legacy["_id"]]
    assert await repository.list_attempts_for_user(
        "user-2", organization_id="personal-2", allow_legacy_personal=True,
    ) == []


@pytest.mark.asyncio
async def test_attempt_history_does_not_join_a_foreign_private_quiz(test_db):
    quiz_repository = QuizV2Repository(test_db.quizzes_v2)
    quiz = build_quiz_document()
    quiz.organization_id = "org-2"
    quiz.visibility = type(quiz.visibility).PRIVATE
    await quiz_repository.insert_quiz(quiz)
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    attempt = await repository.insert_attempt(attempt_payload(quiz_id=str(quiz.id)))
    service = QuizAttemptService(quiz_repository=quiz_repository, attempt_repository=repository)
    payload = await service.get_attempt(
        user_id="user-1", organization_id="org-1", attempt_id=str(attempt.id),
    )
    assert payload is not None
    assert payload["quiz_title"] is None


@pytest.mark.asyncio
async def test_grading_persists_in_active_tenant_not_public_source_tenant(test_db):
    quiz_repository = QuizV2Repository(test_db.quizzes_v2)
    quiz = build_quiz_document()
    quiz.organization_id = "platform-library"
    await quiz_repository.insert_quiz(quiz)
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    service = QuizGradingService(
        quiz_repository=quiz_repository, reference_repository=FakeReferenceRepository(),
        attempt_repository=repository,
    )
    result = await service.grade_submission(
        str(quiz.id), [{"question": q.question, "user_answer": q.correct_answer} for q in quiz.questions],
        user_id="user-1", organization_id="org-1",
    )
    assert result.attempt_saved is True
    stored = await test_db.quiz_attempts_v2.find_one({})
    assert stored["organization_id"] == "org-1"
    assert stored["created_by_user_id"] == stored["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_scoped_grading_rejects_same_users_foreign_private_quiz(test_db):
    quiz_repository = QuizV2Repository(test_db.quizzes_v2)
    quiz = build_quiz_document()
    quiz.visibility = type(quiz.visibility).PRIVATE
    quiz.owner_user_id = "user-1"
    quiz.organization_id = "org-2"
    await quiz_repository.insert_quiz(quiz)
    service = QuizGradingService(
        quiz_repository=quiz_repository, reference_repository=FakeReferenceRepository(),
        attempt_repository=QuizAttemptV2Repository(test_db.quiz_attempts_v2),
    )
    result = await service.grade_submission(str(quiz.id), [], user_id="user-1", organization_id="org-1")
    assert result is None
    assert await test_db.quiz_attempts_v2.count_documents({}) == 0
