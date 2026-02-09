import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException

from server.app.auth import services
from server.app.auth.utils import create_refresh_token
from server.app.db.core.config import settings
from server.app.db.schemas.user_schemas import UserRegisterSchema
from server.app.db.schemas.user_schemas import RequestPasswordReset, PasswordResetRequest


class DummyUser:
    def __init__(self, _id):
        self.id = str(_id)
        self.username = "testuser"
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = None
        self.is_active = True
        self.is_verified = False
        self.role = "user"


def setup_module(module):
    settings.JWT_SECRET = "testsecret"
    settings.JWT_ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 5
    settings.REFRESH_TOKEN_EXPIRE_DAYS = 7


@pytest.mark.asyncio
async def test_register_user_success_sends_verification(monkeypatch):
    mock_users = AsyncMock()
    mock_users.find_one.return_value = None

    dummy = DummyUser(ObjectId())

    async def fake_create_user(_collection, _data):
        return dummy

    mock_redis = AsyncMock()
    async def fake_get_redis():
        return mock_redis

    mock_email = AsyncMock()

    monkeypatch.setattr(services, "users_collection", mock_users)
    monkeypatch.setattr(services, "create_user", fake_create_user)
    monkeypatch.setattr(services, "get_redis_client", fake_get_redis)

    user = UserRegisterSchema(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="Abcd1234!",
    )

    resp = await services.register_user_service(user, email_svc=mock_email)

    assert resp.email == "test@example.com"
    mock_email.send_email.assert_called_once()
    assert mock_redis.setex.await_count == 2


@pytest.mark.asyncio
async def test_login_success_returns_tokens(monkeypatch):
    user_id = ObjectId()
    hashed = "hashed-password"
    mock_users = AsyncMock()
    mock_users.find_one.return_value = {
        "_id": user_id,
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": hashed,
        "is_verified": True,
    }

    monkeypatch.setattr(services, "users_collection", mock_users)
    monkeypatch.setattr(services, "verify_password", lambda _p, _h: True)
    monkeypatch.setattr(services, "hash_token", lambda _t: "hashed-refresh-token")

    result = await services.login_service("testuser", "Abcd1234!", mock_users)

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_success(monkeypatch):
    user_id = ObjectId()
    token, jti, exp = create_refresh_token({"sub": str(user_id)})

    mock_users = AsyncMock()
    mock_users.find_one.return_value = {
        "_id": user_id,
        "refresh_token": "hashed-refresh-token",
        "refresh_token_jti": jti,
        "refresh_token_expires_at": exp,
    }

    monkeypatch.setattr(services, "verify_token_hash", lambda _t, _h: True)
    monkeypatch.setattr(services, "hash_token", lambda _t: "hashed-refresh-token")

    result = await services.refresh_token_service(token, mock_users)

    assert "access_token" in result
    assert "refresh_token" in result


@pytest.mark.asyncio
async def test_verify_otp_expired_returns_400():
    users = AsyncMock()
    redis_client = AsyncMock()
    redis_client.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        await services.verify_otp_service("test@example.com", "123456", users, redis_client)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_otp_invalid_returns_401():
    users = AsyncMock()
    users.find_one.return_value = {"email": "test@example.com"}
    redis_client = AsyncMock()
    redis_client.get.side_effect = ["999999", "0"]

    with pytest.raises(HTTPException) as exc:
        await services.verify_otp_service("test@example.com", "123456", users, redis_client)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_resend_verification_for_verified_user(monkeypatch):
    mock_users = AsyncMock()
    mock_users.find_one.return_value = {"email": "test@example.com", "is_verified": True}
    monkeypatch.setattr(services, "users_collection", mock_users)

    with pytest.raises(HTTPException) as exc:
        await services.resend_verification_email_service("test@example.com", email_svc=AsyncMock())

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_request_password_reset_sends_otp(monkeypatch):
    mock_users = AsyncMock()
    mock_users.find_one.return_value = {"email": "test@example.com"}
    monkeypatch.setattr(services, "users_collection", mock_users)

    mock_redis = AsyncMock()
    async def fake_get_redis():
        return mock_redis

    monkeypatch.setattr(services, "get_redis_client", fake_get_redis)

    email_svc = AsyncMock()
    req = RequestPasswordReset(email="test@example.com")

    result = await services.request_password_reset_service(req, email_svc=email_svc)

    assert "message" in result
    assert mock_redis.setex.await_count == 2
    email_svc.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_via_token_updates_password(monkeypatch):
    mock_users = AsyncMock()
    mock_users.find_one.return_value = {"email": "test@example.com"}
    mock_users.update_one.return_value = AsyncMock(modified_count=1)
    monkeypatch.setattr(services, "users_collection", mock_users)

    mock_redis = AsyncMock()
    async def fake_get_redis():
        return mock_redis

    monkeypatch.setattr(services, "get_redis_client", fake_get_redis)

    monkeypatch.setattr(services, "decode_verification_token", lambda token: "test@example.com")
    monkeypatch.setattr(services.pwd_context, "hash", lambda _p: "hashed-password")

    req = PasswordResetRequest(
        email="test@example.com",
        reset_method="token",
        token="validtoken",
        new_password="Abcd1234!",
    )

    result = await services.reset_password_service(req)

    assert result.success is True
    assert mock_redis.delete.await_count == 2
