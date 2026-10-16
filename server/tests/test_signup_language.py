from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from server.app.auth import services
from server.app.core.config import settings
from server.app.core.rate_limiter import limiter
from server.app.i18n.locales import resolve_effective_locale
from server.app.organizations.routes import router
from server.app.organizations.services import resolve_user_effective_locale
from server.app.users.models import UserOut
from server.app.users.schemas import UserRegisterSchema

USER_ID = "507f1f77bcf86cd799439011"
ORG_ID = "507f1f77bcf86cd799439012"


def invitation(**overrides):
    return jwt.encode({"type": "organization_onboarding", "organization_id": ORG_ID,
                       "email": "learner@example.com", "exp": 4102444800, **overrides},
                      settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def registration(monkeypatch):
    users = SimpleNamespace(find_one=AsyncMock(return_value=None), update_one=AsyncMock())
    organizations = SimpleNamespace(find_one=AsyncMock(return_value={
        "_id": ObjectId(ORG_ID), "name": "French school", "default_locale": "fr"}))
    memberships = SimpleNamespace(update_one=AsyncMock(), find_one=AsyncMock(return_value={"role": "member"}))
    now = datetime.now(timezone.utc)
    created = SimpleNamespace(id=USER_ID, username="learner", email="learner@example.com",
                              full_name="Learner Test", created_at=now, updated_at=now,
                              is_active=True, is_verified=False, status="pending_verification", role="user")
    create = AsyncMock(return_value=created)
    mail = SimpleNamespace(send_email=AsyncMock())
    monkeypatch.setattr(services, "users_collection", users)
    monkeypatch.setattr(services, "get_organizations_collection", lambda: organizations)
    monkeypatch.setattr(services, "get_organization_memberships_collection", lambda: memberships)
    monkeypatch.setattr(services, "get_auth_events_collection", lambda: object())
    monkeypatch.setattr(services, "record_auth_event", AsyncMock())
    monkeypatch.setattr(services, "create_user", create)
    monkeypatch.setattr(services, "get_redis_client", AsyncMock(return_value=SimpleNamespace(setex=AsyncMock(), delete=AsyncMock())))
    return SimpleNamespace(users=users, organizations=organizations, memberships=memberships, create=create, mail=mail)


def request(**overrides):
    return UserRegisterSchema(username="learner", email="learner@example.com", full_name="Learner Test",
                              password="ValidPass123!", **overrides)


@pytest.mark.asyncio
@pytest.mark.parametrize("preference", [None, "en", "fr", "es", "yo"])
async def test_independent_signup_preserves_choice_without_organization(registration, preference):
    response = await services.register_user_service(request(preferred_locale=preference), registration.mail)
    saved = registration.create.call_args.args[1]
    assert saved.preferred_locale == preference
    assert resolve_effective_locale(saved.preferred_locale) == (preference or "en")
    registration.organizations.find_one.assert_not_awaited()
    registration.memberships.update_one.assert_not_awaited()
    assert response.is_verified is False


@pytest.mark.asyncio
@pytest.mark.parametrize("preference,expected", [(None, "fr"), ("en", "en"), ("es", "es")])
async def test_invitation_default_never_overwrites_explicit_choice(registration, preference, expected):
    response = await services.register_user_service(request(preferred_locale=preference, organization_invitation_token=invitation()), registration.mail)
    saved = registration.create.call_args.args[1]
    assert saved.preferred_locale == preference
    persisted_user = UserOut(id=USER_ID, username="learner", email="learner@example.com",
                             preferred_locale=saved.preferred_locale, onboarding_organization_id=ORG_ID)
    assert await resolve_user_effective_locale(persisted_user, registration.organizations, registration.memberships) == expected
    member = registration.memberships.update_one.call_args
    assert member.args[0] == {"organization_id": ORG_ID, "user_id": USER_ID}
    assert member.args[1]["$setOnInsert"]["role"] == "member"
    written = registration.users.update_one.call_args.args[1]["$set"]
    assert written["profile.onboarding_organization_id"] == ORG_ID
    assert "profile.preferred_locale" not in written
    assert "is_verified" not in written
    assert response.is_verified is False


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["invalid", invitation(email="someone-else@example.com"), invitation(exp=1), invitation(type="access"), invitation(organization_id=[])])
async def test_invalid_invitation_rejected_before_account_creation(registration, token):
    with pytest.raises(HTTPException) as error:
        await services.register_user_service(request(organization_invitation_token=token), registration.mail)
    assert error.value.status_code == 400
    registration.create.assert_not_awaited()
    registration.memberships.update_one.assert_not_awaited()
    registration.mail.send_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_deleted_organization_rejected_before_registration(registration):
    registration.organizations.find_one.return_value = None
    with pytest.raises(HTTPException) as error:
        await services.register_user_service(request(organization_invitation_token=invitation()), registration.mail)
    assert error.value.status_code == 404
    registration.create.assert_not_awaited()


def test_invitation_preview_exposes_only_organization_context(registration, monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)
    app = FastAPI()
    app.state.organizations_collection = registration.organizations
    app.include_router(router, prefix="/api/organizations")
    with TestClient(app) as client:
        response = client.post("/api/organizations/onboarding/preview", json={"token": invitation()})
        assert response.status_code == 200
        assert response.json() == {"organization_id": ORG_ID, "name": "French school", "default_locale": "fr"}
        assert client.post("/api/organizations/onboarding/preview", json={"token": "invalid"}).status_code == 400
    registration.memberships.update_one.assert_not_awaited()
