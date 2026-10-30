"""Exercise JSON routes through FastAPI and the real SlowAPI wrapper."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

for name, value in {
    "JWT_SECRET": "test-secret",
    "EMAIL_SENDER": "test@example.com",
    "EMAIL_PASSWORD": "password",
    "EMAIL_HOST": "smtp.example.com",
    "EMAIL_PORT": "587",
    "SHARE_URL": "http://localhost:3000",
    "MONGO_URI": "mongodb://localhost:27017",
}.items():
    os.environ.setdefault(name, value)

import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from slowapi.errors import RateLimitExceeded

from server.app.core.dependencies import get_current_user
from server.app.core.rate_limiter import limiter, rate_limit_handler
from server.app.organizations import routes
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext, OrganizationPrincipal
from server.app.share import routes as share_routes


ORGANIZATION_ID = "507f1f77bcf86cd799439011"
MEMBER_ID = "507f1f77bcf86cd799439012"
INVITATION_ID = "507f1f77bcf86cd799439013"
OWNER_ID = "507f1f77bcf86cd799439014"


@pytest.fixture
def organization_app(monkeypatch):
    # Only storage is isolated; production limits, decorators and header
    # injection remain enabled. No Redis or application database is contacted.
    storage = MemoryStorage()
    monkeypatch.setattr(limiter, "enabled", True)
    monkeypatch.setattr(limiter, "_headers_enabled", True)
    monkeypatch.setattr(limiter, "_storage_dead", False)
    monkeypatch.setattr(limiter, "_storage", storage)
    monkeypatch.setattr(limiter, "_limiter", FixedWindowRateLimiter(storage))

    user = SimpleNamespace(
        id=OWNER_ID, session_id="session-1", is_verified=True,
        default_organization_id=ORGANIZATION_ID,
        email="owner@example.com",
    )
    context = OrganizationContext(
        organization_id=ORGANIZATION_ID,
        organization_kind="corporate",
        membership_role="owner",
        principal=OrganizationPrincipal(user_id=user.id, session_id=user.session_id),
        membership={"role": "owner", "status": "active"},
    )
    organization = {
        "_id": ObjectId(ORGANIZATION_ID), "kind": "corporate", "name": "Test team",
    }
    membership = {
        "organization_id": ORGANIZATION_ID, "user_id": user.id,
        "role": "owner", "status": "active",
    }
    now = datetime.now(timezone.utc)
    invitation = {
        "_id": ObjectId(INVITATION_ID), "organization_id": ORGANIZATION_ID,
        "email": "member@example.com", "role": "learner", "status": "invited",
        "expires_at": now + timedelta(days=7), "created_at": now,
    }

    memberships = SimpleNamespace(
        list_active_for_user=AsyncMock(return_value=[membership]),
        get_active_membership=AsyncMock(return_value=membership),
        list_for_organization=AsyncMock(return_value=([membership], None)),
        get_membership=AsyncMock(return_value={"role": "learner", "status": "active"}),
        set_status=AsyncMock(return_value={"status": "suspended"}),
    )
    organizations = SimpleNamespace(
        list_active_by_ids=AsyncMock(return_value=[organization]),
        get_active=AsyncMock(return_value=organization),
    )
    invitations = SimpleNamespace(
        list_for_organization=AsyncMock(return_value=([invitation], None)),
    )
    service = SimpleNamespace(
        invite=AsyncMock(return_value=invitation),
        accept=AsyncMock(return_value={"membership": membership}),
        decline=AsyncMock(),
        get_for_revoke=AsyncMock(return_value=invitation),
        revoke=AsyncMock(return_value={**invitation, "status": "revoked"}),
    )
    lifecycle = SimpleNamespace(
        create_shared_organization=AsyncMock(return_value=(organization, membership)),
    )
    users_cursor = SimpleNamespace(to_list=AsyncMock(return_value=[{
        "_id": ObjectId(user.id), "email": user.email, "username": "owner",
    }]))
    users_collection = SimpleNamespace(find=lambda *_args, **_kwargs: users_cursor)
    sessions = SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)))

    monkeypatch.setattr(routes, "OrganizationMembershipRepository", lambda _collection: memberships)
    monkeypatch.setattr(routes, "OrganizationRepository", lambda _collection: organizations)
    monkeypatch.setattr(routes, "OrganizationInvitationRepository", lambda _collection: invitations)
    monkeypatch.setattr(routes, "OrganizationLifecycleService", lambda **_kwargs: lifecycle)
    monkeypatch.setattr(routes, "_invitation_service", lambda: service)
    monkeypatch.setattr(routes, "get_organization_memberships_collection", lambda: None)
    monkeypatch.setattr(routes, "get_organizations_collection", lambda: None)
    monkeypatch.setattr(routes, "get_organization_invitations_collection", lambda: None)
    monkeypatch.setattr(routes, "get_users_collection", lambda: users_collection)
    monkeypatch.setattr(routes, "get_user_sessions_collection", lambda: sessions)
    monkeypatch.setattr(routes, "get_active_session", AsyncMock(return_value={
        "active_organization_id": ORGANIZATION_ID,
    }))

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.include_router(routes.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_active_organization_context] = lambda: context
    app.dependency_overrides[routes.get_email_service] = lambda: SimpleNamespace()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(
            app=app, client=client, user=user, context=context,
            memberships=memberships, service=service,
        )


SUCCESS_CASES = [
    ("POST", "", {"kind": "corporate", "name": "New team"}, 201),
    ("GET", "/memberships", None, 200),
    ("PUT", "/active", {"organization_id": ORGANIZATION_ID}, 200),
    ("POST", "/invitations", {"email": "member@example.com", "role": "learner"}, 201),
    ("GET", "/invitations", None, 200),
    ("GET", "/members", None, 200),
    ("POST", "/invitations/accept", {"token": "a" * 64}, 200),
    ("POST", "/invitations/decline", {"token": "a" * 64}, 200),
    ("POST", f"/invitations/{INVITATION_ID}/revoke", None, 200),
    ("PATCH", f"/memberships/{MEMBER_ID}", {"status": "suspended"}, 200),
]


@pytest.mark.parametrize("method,path,payload,expected_status", SUCCESS_CASES)
def test_organization_successes_keep_json_status_and_rate_limit_headers(
    organization_app, method, path, payload, expected_status,
):
    response = organization_app.client.request(method, f"/api/organizations{path}", json=payload)

    assert response.status_code == expected_status, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), (dict, list))
    assert int(response.headers["x-ratelimit-limit"]) > 0
    assert int(response.headers["x-ratelimit-remaining"]) >= 0
    assert "x-ratelimit-reset" in response.headers
    assert "retry-after" in response.headers
    if path == "/memberships":
        assert response.json()[0]["organization_id"] == ORGANIZATION_ID
        assert response.json()[0]["is_active"] is True


def test_organization_memberships_still_enforces_the_read_limit(organization_app):
    responses = [
        organization_app.client.get("/api/organizations/memberships")
        for _ in range(101)
    ]

    assert all(response.status_code == 200 for response in responses[:100])
    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"] == "rate_limit_exceeded"
    assert organization_app.memberships.list_active_for_user.await_count == 100


@pytest.mark.parametrize("decision", ["accept", "decline"])
def test_unverified_invitation_decisions_remain_forbidden(organization_app, decision):
    organization_app.user.is_verified = False

    response = organization_app.client.post(
        f"/api/organizations/invitations/{decision}", json={"token": "a" * 64},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Email not verified"
    organization_app.service.accept.assert_not_awaited()
    organization_app.service.decline.assert_not_awaited()


def test_membership_policy_denial_remains_403(organization_app):
    organization_app.context.membership_role = "learner"

    response = organization_app.client.get("/api/organizations/invitations")

    assert response.status_code == 403
    assert response.json()["detail"] == "Organization invitation access denied"


def test_missing_authentication_remains_401(organization_app):
    def unauthenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")

    organization_app.app.dependency_overrides[get_current_user] = unauthenticated

    response = organization_app.client.get("/api/organizations/memberships")

    assert response.status_code == 401
    organization_app.memberships.list_active_for_user.assert_not_awaited()


@pytest.fixture
def public_share_app(organization_app, monkeypatch):
    quiz = {
        "id": MEMBER_ID, "title": "Public quiz", "description": "Sample quiz",
        "quiz_type": "multichoice", "questions": [],
    }
    now = datetime.now(timezone.utc)
    quizzes = SimpleNamespace(aggregate=lambda _pipeline: SimpleNamespace(
        to_list=AsyncMock(return_value=[{
            **quiz, "_id": ObjectId(MEMBER_ID), "created_at": now, "updated_at": now,
        }]),
    ))
    organizations = SimpleNamespace(find_one=AsyncMock(return_value={
        "_id": ObjectId(ORGANIZATION_ID),
    }))
    monkeypatch.setattr(
        share_routes.shared_quiz_read_service, "resolve_shared_quiz",
        AsyncMock(return_value=quiz),
    )
    app = organization_app.app
    app.include_router(share_routes.router, prefix="/api/share")
    app.dependency_overrides[share_routes.get_current_user_optional] = lambda: None
    app.dependency_overrides[share_routes.get_quizzes_v2_collection] = lambda: quizzes
    app.dependency_overrides[share_routes.get_organizations_collection] = lambda: organizations
    return organization_app


@pytest.mark.parametrize("path", [
    "/get-quiz-id", f"/share-quiz/{MEMBER_ID}", f"/shared-quiz/{MEMBER_ID}",
])
def test_public_share_successes_keep_json_and_rate_limit_headers(public_share_app, path):
    response = public_share_app.client.get(f"/api/share{path}")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), dict)
    assert int(response.headers["x-ratelimit-limit"]) > 0
    assert int(response.headers["x-ratelimit-remaining"]) >= 0
    assert "x-ratelimit-reset" in response.headers


def test_public_shared_quiz_still_enforces_its_rate_limit(public_share_app):
    responses = [
        public_share_app.client.get(f"/api/share/shared-quiz/{MEMBER_ID}")
        for _ in range(51)
    ]

    assert all(response.status_code == 200 for response in responses[:50])
    assert responses[-1].status_code == 429
    assert responses[-1].json()["error"] == "rate_limit_exceeded"


@pytest.mark.parametrize("status_code", [403, 404, 409])
def test_private_share_errors_remain_unchanged(public_share_app, monkeypatch, status_code):
    monkeypatch.setattr(
        share_routes.shared_quiz_read_service, "resolve_shared_quiz", AsyncMock(return_value=None),
    )
    if status_code != 404:
        public_share_app.app.dependency_overrides[share_routes.get_current_user_optional] = (
            lambda: public_share_app.user
        )
        monkeypatch.setattr(
            share_routes, "resolve_current_user_organization_context",
            AsyncMock(return_value=public_share_app.context),
        )
        permission = AsyncMock()
        if status_code == 403:
            permission.side_effect = HTTPException(status_code=403, detail="Permission denied")
        monkeypatch.setattr(share_routes, "_require_share_permission", permission)

    response = public_share_app.client.get(f"/api/share/share-quiz/{MEMBER_ID}")

    assert response.status_code == status_code
    if status_code == 409:
        assert "public or unlisted" in response.json()["detail"]
