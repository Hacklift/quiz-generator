from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.core.dependencies import get_current_user
from server.app.core.config import settings
from server.app.core.rate_limiter import limiter
from server.app.db.core.connection import (
    get_users_collection, get_user_sessions_collection,
    get_organizations_collection, get_organization_memberships_collection,
)
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.organizations.repository import OrganizationRepository
from server.app.quiz.repositories.v2.models.reference_models import QuizAttemptDocumentV2
from server.app.quiz.repositories.v2.repositories.attempt_repository import QuizAttemptV2Repository
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.repositories.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.quiz.repositories.v2.models.reference_models import SavedQuizDocumentV2
from server.app.quiz.repositories.v2.setup import ensure_v2_collections_and_validators
from pymongo.errors import OperationFailure
from server.app.quiz.routes import attempts, grading
from server.app.quiz.services.quiz_attempt_service import QuizAttemptService
from server.app.quiz.services.quiz_grading_service import QuizGradingService
from server.app.quiz.services.quiz_practice_access import QuizPracticeAccess
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
        quiz_access=QuizPracticeAccess(OrganizationRepository(test_db.organizations)),
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
async def test_attempt_repository_never_reads_unscoped_records_after_cutover(test_db):
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    legacy = attempt_payload().model_dump(by_alias=True, exclude={"organization_id", "created_by_user_id"})
    await test_db.quiz_attempts_v2.insert_one(legacy)
    assert await repository.list_attempts_for_user("user-1", organization_id="org-1") == []
    assert await repository.list_attempts_for_user("user-1", organization_id="personal-1") == []
    assert await repository.list_attempts_for_user(
        "user-2", organization_id="personal-2",
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
    service = QuizAttemptService(quiz_repository=quiz_repository, attempt_repository=repository, quiz_access=QuizPracticeAccess(OrganizationRepository(test_db.organizations)))
    payload = await service.get_attempt(
        user_id="user-1", organization_id="org-1", attempt_id=str(attempt.id),
    )
    assert payload is not None
    assert payload["quiz_title"] is None


@pytest.mark.asyncio
async def test_grading_persists_in_active_tenant_not_public_source_tenant(test_db):
    quiz_repository = QuizV2Repository(test_db.quizzes_v2)
    quiz = build_quiz_document()
    platform = await test_db.organizations.insert_one({"kind": "personal", "status": "active"})
    quiz.organization_id = str(platform.inserted_id)
    await quiz_repository.insert_quiz(quiz)
    repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    service = QuizGradingService(
        quiz_access=QuizPracticeAccess(OrganizationRepository(test_db.organizations)),
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
        quiz_access=QuizPracticeAccess(OrganizationRepository(test_db.organizations)),
        quiz_repository=quiz_repository, reference_repository=FakeReferenceRepository(),
        attempt_repository=QuizAttemptV2Repository(test_db.quiz_attempts_v2),
    )
    result = await service.grade_submission(str(quiz.id), [], user_id="user-1", organization_id="org-1")
    assert result is None
    assert await test_db.quiz_attempts_v2.count_documents({}) == 0


@pytest.mark.asyncio
async def test_real_token_grading_and_history_follow_server_session_scope(test_db, monkeypatch):
    user_id = str(ObjectId())
    now = datetime.now(timezone.utc)
    first = await test_db.organizations.insert_one({"kind": "corporate", "status": "active"})
    second = await test_db.organizations.insert_one({"kind": "school", "status": "active"})
    organization_id = str(first.inserted_id)
    await test_db.users.insert_one({
        "_id": ObjectId(user_id), "username": "learner", "email": "learner@example.com",
        "status": "active", "is_verified": True, "last_seen_at": now,
        "default_organization_id": organization_id,
    })
    await test_db.user_sessions.insert_one({
        "session_id": "session-1", "user_id": user_id, "revoked_at": None,
        "expires_at": now + timedelta(hours=1), "active_organization_id": organization_id,
    })
    await test_db.organization_memberships.insert_many([{
        "user_id": user_id, "organization_id": str(org_id), "role": "learner", "status": "active",
    } for org_id in (first.inserted_id, second.inserted_id)])
    quiz_repository = QuizV2Repository(test_db.quizzes_v2)
    quiz = build_quiz_document()
    quiz.organization_id = organization_id
    quiz.owner_user_id = quiz.created_by_user_id = user_id
    quiz.visibility = type(quiz.visibility).PRIVATE
    await quiz_repository.insert_quiz(quiz)
    attempt_repository = QuizAttemptV2Repository(test_db.quiz_attempts_v2)
    access = QuizPracticeAccess(OrganizationRepository(test_db.organizations))
    grading_service = QuizGradingService(
        quiz_repository=quiz_repository, attempt_repository=attempt_repository,
        reference_repository=FakeReferenceRepository(), quiz_access=access,
    )
    monkeypatch.setattr(grading, "QuizGradingService", lambda: grading_service)
    monkeypatch.setattr(attempts, "quiz_attempt_service", QuizAttemptService(
        quiz_repository=quiz_repository, attempt_repository=attempt_repository, quiz_access=access,
    ))
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.include_router(grading.router, prefix="/api")
    app.include_router(attempts.router, prefix="/api")
    def collection_dependency(collection):
        async def dependency():
            return collection
        return dependency

    for dependency, collection in (
        (get_users_collection, test_db.users),
        (get_user_sessions_collection, test_db.user_sessions),
        (get_organizations_collection, test_db.organizations),
        (get_organization_memberships_collection, test_db.organization_memberships),
    ):
        app.dependency_overrides[dependency] = collection_dependency(collection)
    token = jwt.encode({
        "sub": user_id, "sid": "session-1", "jti": "test-token", "type": "access",
        "exp": now + timedelta(minutes=5),
    }, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.post(f"/api/quizzes/{quiz.id}/grade", json={"answers": [
            {"question": question.question, "user_answer": question.correct_answer}
            for question in quiz.questions
        ]})
        assert response.status_code == 200
        assert response.headers["x-quiz-attempt-status"] == "saved"
        rows = (await client.get("/api/quiz-attempts")).json()
        assert len(rows) == 1
        assert rows[0]["quiz_title"] == quiz.title
        attempt_id = rows[0]["_id"]
        await test_db.user_sessions.update_one(
            {"session_id": "session-1"}, {"$set": {"active_organization_id": str(second.inserted_id)}},
        )
        assert (await client.get("/api/quiz-attempts")).json() == []
        assert (await client.get(f"/api/quiz-attempts/{attempt_id}")).status_code == 404
        assert (await client.delete(f"/api/quiz-attempts/{attempt_id}")).status_code == 404


@pytest.mark.asyncio
async def test_saved_attempt_alias_requires_both_user_and_tenant(test_db):
    repository = ReferenceV2Repository(
        test_db.folders_v2, test_db.folder_items_v2, test_db.saved_quizzes_v2, test_db.quiz_history_v2,
    )
    saved = await repository.insert_saved_quiz(SavedQuizDocumentV2(
        user_id="user-1", organization_id="org-1", quiz_id="canonical-quiz",
        legacy_saved_quiz_id="old-saved-alias",
    ))
    for identifier in (str(saved.id), saved.legacy_saved_quiz_id):
        resolved = await repository.get_saved_quiz_for_attempt(
            identifier, user_id="user-1", organization_id="org-1",
        )
        assert resolved.id == saved.id
        assert await repository.get_saved_quiz_for_attempt(
            identifier, user_id="user-1", organization_id="org-2",
        ) is None
        assert await repository.get_saved_quiz_for_attempt(
            identifier, user_id="user-2", organization_id="org-1",
        ) is None


@pytest.mark.asyncio
async def test_attempt_mongo_validator_rejects_missing_scope_after_cutover(test_db):
    await ensure_v2_collections_and_validators(test_db)
    document = attempt_payload().model_dump(by_alias=True, exclude={"organization_id"})
    with pytest.raises(OperationFailure) as exc:
        await test_db.quiz_attempts_v2.insert_one(document)
    assert exc.value.code == 121
