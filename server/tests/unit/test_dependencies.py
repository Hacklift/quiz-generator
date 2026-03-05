import pytest
from bson import ObjectId
from fastapi.security import HTTPAuthorizationCredentials

from server.app import dependancies


@pytest.mark.asyncio
async def test_get_current_user_valid_token(monkeypatch, fake_users_collection, fake_blacklist_collection):
  user_id = ObjectId()
  token = dependancies.jwt.encode(
    {"sub": str(user_id), "jti": "j1", "type": "access"},
    dependancies.settings.JWT_SECRET,
    algorithm=dependancies.settings.JWT_ALGORITHM,
  )
  fake_users_collection.docs.append(
    {"_id": user_id, "username": "u", "email": "u@x.com"}
  )

  creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
  user = await dependancies.get_current_user(
    credentials=creds,
    users_collection=fake_users_collection,
    blacklist_collection=fake_blacklist_collection,
  )
  assert user.id == str(user_id)


@pytest.mark.asyncio
async def test_get_current_user_blacklisted(monkeypatch, fake_users_collection, fake_blacklist_collection):
  user_id = ObjectId()
  token = dependancies.jwt.encode(
    {"sub": str(user_id), "jti": "j2", "type": "access"},
    dependancies.settings.JWT_SECRET,
    algorithm=dependancies.settings.JWT_ALGORITHM,
  )
  fake_users_collection.docs.append(
    {"_id": user_id, "username": "u", "email": "u@x.com"}
  )
  fake_blacklist_collection.docs.append({"jti": "j2"})
  creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

  with pytest.raises(Exception):
    await dependancies.get_current_user(
      credentials=creds,
      users_collection=fake_users_collection,
      blacklist_collection=fake_blacklist_collection,
    )


@pytest.mark.asyncio
async def test_get_current_user_optional_missing():
  user = await dependancies.get_current_user_optional(
    credentials=None,
    users_collection=None,
    blacklist_collection=None,
  )
  assert user is None
