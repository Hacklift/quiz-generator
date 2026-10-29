from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pymongo.errors import ConnectionFailure

from server.app.core.dependencies import get_current_user_optional, get_verified_user
from server.app.core.rate_limiter import limiter
from server.app.db.core.connection import (
    get_organization_memberships_collection,
    get_organizations_collection,
    get_quizzes_v2_collection,
    get_user_sessions_collection,
)
from server.app.email_platform.deps import get_email_service
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.repositories.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.share import routes
from server.app.share.services import SharedQuizReadService


@pytest_asyncio.fixture
async def share_app(test_db, monkeypatch):
    library = await test_db.organizations.insert_one({
        "system_key": "platform_library", "kind": "personal", "status": "active",
    })
    organization_id = str(library.inserted_id)
    state = {"user": None, "role": "author"}
    repository = QuizV2Repository(test_db.quizzes_v2)
    references = ReferenceV2Repository(
        test_db.folders_v2, test_db.folder_items_v2, test_db.saved_quizzes_v2, test_db.quiz_history_v2,
    )
    monkeypatch.setattr(routes, "get_quizzes_v2_collection", lambda: test_db.quizzes_v2)
    monkeypatch.setattr(routes, "shared_quiz_read_service", SharedQuizReadService(
        quiz_repository=repository, reference_repository=references,
        organizations_collection=test_db.organizations,
    ))
    monkeypatch.setattr(limiter, "enabled", False)

    def context():
        return OrganizationContext(
            organization_id=organization_id, organization_kind="corporate", membership_role=state["role"],
            principal=OrganizationPrincipal(user_id="author-1", session_id="session-1"), membership={},
        )

    async def resolve_context(**_kwargs):
        return context()

    monkeypatch.setattr(routes, "resolve_current_user_organization_context", resolve_context)
    app = FastAPI()
    app.include_router(routes.router, prefix="/share")
    email = SimpleNamespace(send_email=AsyncMock())
    app.dependency_overrides[get_current_user_optional] = lambda: state["user"]
    app.dependency_overrides[get_verified_user] = lambda: state["user"]
    app.dependency_overrides[get_active_organization_context] = context
    app.dependency_overrides[get_email_service] = lambda: email
    app.dependency_overrides[get_quizzes_v2_collection] = lambda: test_db.quizzes_v2
    app.dependency_overrides[get_organizations_collection] = lambda: test_db.organizations
    app.dependency_overrides[get_organization_memberships_collection] = lambda: test_db.organization_memberships
    app.dependency_overrides[get_user_sessions_collection] = lambda: test_db.user_sessions
    return app, state, repository, organization_id, email


def quiz_document(organization_id, **changes):
    return QuizDocumentV2(
        organization_id=organization_id, title="Template quiz", quiz_type="multichoice",
        owner_user_id="author-1", created_by_user_id="author-1",
        questions=[{"question": "Choose", "options": ["A", "B"], "correct_answer": "A"}],
        **changes,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("authenticated", [False, True])
async def test_malformed_share_identifier_is_404_not_500(share_app, authenticated):
    app, state, _, _, _ = share_app
    if authenticated:
        state["user"] = SimpleNamespace(id="author-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/share/share-quiz/not-an-objectid")
        assert response.status_code == 404
        assert response.json()["detail"] == "Quiz not found"


@pytest.mark.asyncio
@pytest.mark.parametrize("role,foreign,expected", [
    ("author", False, 409), ("admin", False, 409),
    ("learner", False, 403), ("admin", True, 404), ("learner", True, 404),
])
async def test_private_email_and_link_checks_preserve_policy_order(share_app, role, foreign, expected):
    app, state, repository, organization_id, email = share_app
    state.update(user=SimpleNamespace(id="author-1"), role=role)
    quiz = await repository.insert_quiz(quiz_document(
        "foreign-organization" if foreign else organization_id, visibility="private",
    ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        link = await client.get(f"/share/share-quiz/{quiz.id}")
        sent = await client.post("/share/share-email", json={
            "quiz_id": str(quiz.id), "recipient_email": "recipient@example.com",
        })
    assert link.status_code == sent.status_code == expected
    if expected == 409:
        assert "public or unlisted" in link.json()["detail"]
        assert "public or unlisted" in sent.json()["detail"]
    email.send_email.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("visibility", ["public", "unlisted"])
async def test_guest_link_still_works_for_explicit_public_capabilities(share_app, visibility):
    app, _, repository, organization_id, _ = share_app
    quiz = await repository.insert_quiz(quiz_document(organization_id, visibility=visibility))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/share/share-quiz/{quiz.id}")
        assert response.status_code == 200
        assert response.json()["link"].endswith(f"/share/{quiz.id}")


@pytest.mark.asyncio
async def test_random_template_requires_public_active_seed_in_platform_tenant(share_app):
    app, _, repository, organization_id, _ = share_app
    eligible = await repository.insert_quiz(quiz_document(organization_id, source="seed", visibility="public"))
    for changes in (
        {"source": "seed", "visibility": "private"},
        {"source": "seed", "visibility": "unlisted"},
        {"source": "seed", "visibility": "public", "status": "archived"},
        {"source": "seed", "visibility": "public", "status": "deleted"},
        {"source": "manual", "visibility": "public"},
    ):
        await repository.insert_quiz(quiz_document(organization_id, **changes))
    await repository.insert_quiz(quiz_document("another-tenant", source="seed", visibility="public"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/share/get-quiz-id")
        assert response.status_code == 200
        assert response.json()["id"] == str(eligible.id)
        assert response.json()["description"]
        await repository.collection.delete_one({"_id": eligible.id})
        response = await client.get("/share/get-quiz-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "No public template quizzes are available"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["missing", "suspended", "deleted"])
async def test_unavailable_library_has_clear_error_and_never_returns_seed(share_app, status, caplog):
    app, _, repository, organization_id, _ = share_app
    await repository.insert_quiz(quiz_document(organization_id, source="seed", visibility="public"))
    if status == "missing":
        await repository.collection.database.organizations.delete_many({})
    else:
        await repository.collection.database.organizations.update_many({}, {"$set": {"status": status}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/share/get-quiz-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Public quiz library is unavailable"
    assert "platform_library is missing or inactive" in caplog.text


@pytest.mark.asyncio
async def test_share_database_failure_is_not_disguised_as_missing_quiz(share_app, monkeypatch):
    app, _, _, _, _ = share_app
    monkeypatch.setattr(routes.shared_quiz_read_service.quiz_repository, "find_public_shareable_by_id",
                        AsyncMock(side_effect=ConnectionFailure("private database diagnostics")))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/share/share-quiz/507f1f77bcf86cd799439011")
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to generate shareable link"
