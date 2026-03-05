import pytest
from bson import ObjectId
from datetime import datetime, timezone

from server.app.auth import services
from server.app.db.schemas.user_schemas import UserRegisterSchema


class DummyEmailService:
  def __init__(self):
    self.sent = []

  async def send_email(self, **kwargs):
    self.sent.append(kwargs)
    return {"ok": True}


@pytest.mark.asyncio
async def test_register_user_service_creates_user_and_sends_email(
  monkeypatch, fake_users_collection, fake_redis
):
  async def fake_create_user(_collection, _data):
    return type(
      "User",
      (),
          {
            "id": str(ObjectId()),
            "username": _data.username,
            "email": _data.email,
            "full_name": _data.full_name,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "is_active": True,
            "is_verified": False,
        "role": "user",
      },
    )()

  monkeypatch.setattr(services, "users_collection", fake_users_collection)
  async def fake_get_redis_client():
    return fake_redis

  monkeypatch.setattr(services, "get_redis_client", fake_get_redis_client)
  monkeypatch.setattr(services, "create_user", fake_create_user)

  email_svc = DummyEmailService()
  payload = UserRegisterSchema(
    username="tester",
    email="tester@example.com",
    full_name="Tester",
    password="StrongP@ss1",
  )

  resp = await services.register_user_service(payload, email_svc=email_svc)
  assert resp.email == "tester@example.com"
  assert len(email_svc.sent) == 1


@pytest.mark.asyncio
async def test_verify_otp_service_success(monkeypatch, fake_users_collection, fake_redis):
  user_id = ObjectId()
  fake_users_collection.docs.append({"_id": user_id, "email": "a@b.com"})
  fake_redis.store["otp:a@b.com"] = "123456"

  result = await services.verify_otp_service(
    "a@b.com",
    "123456",
    fake_users_collection,
    fake_redis,
  )
  assert result["message"] == "OTP verified successfully!"


@pytest.mark.asyncio
async def test_login_service_rejects_unverified(monkeypatch, fake_users_collection):
  monkeypatch.setattr(services, "verify_password", lambda *_args, **_kwargs: True)
  user_id = ObjectId()
  fake_users_collection.docs.append(
    {
      "_id": user_id,
      "email": "a@b.com",
      "username": "tester",
      "hashed_password": "irrelevant",
      "is_verified": False,
    }
  )
  with pytest.raises(Exception):
    await services.login_service("a@b.com", "StrongP@ss1", fake_users_collection)


@pytest.mark.asyncio
async def test_refresh_token_service_invalid_hash(monkeypatch, fake_users_collection):
  monkeypatch.setattr(services, "verify_token_hash", lambda *_args, **_kwargs: False)
  user_id = ObjectId()
  refresh_token, jti, exp = services.create_refresh_token({"sub": str(user_id)})
  fake_users_collection.docs.append(
    {
      "_id": user_id,
      "refresh_token": "irrelevant",
      "refresh_token_jti": jti,
      "refresh_token_expires_at": exp,
    }
  )
  with pytest.raises(Exception):
    await services.refresh_token_service(refresh_token, fake_users_collection)
