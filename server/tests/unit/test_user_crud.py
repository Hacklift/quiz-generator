import pytest
from bson import ObjectId
from datetime import datetime, timezone

from server.app.db.crud import user_crud
from server.app.db.schemas.user_schemas import CreateUserRequest, UpdateUserSchema


@pytest.mark.asyncio
async def test_create_user_success(fake_users_collection):
  payload = CreateUserRequest(
    username="tester",
    email="tester@example.com",
    full_name="Tester",
    password="StrongP@ss1",
  )
  user = await user_crud.create_user(fake_users_collection, payload)
  assert user is not None
  assert user.email == "tester@example.com"


@pytest.mark.asyncio
async def test_update_user_success(fake_users_collection):
  user_id = ObjectId()
  fake_users_collection.docs.append(
    {
      "_id": user_id,
      "username": "tester",
      "email": "tester@example.com",
      "full_name": "Tester",
      "quizzes": [],
      "is_active": True,
      "is_verified": False,
      "role": "user",
      "hashed_password": "hashed",
      "created_at": datetime.now(timezone.utc),
      "updated_at": None,
    }
  )
  update = UpdateUserSchema(full_name="Updated")
  updated = await user_crud.update_user(fake_users_collection, str(user_id), update)
  assert updated is not None
  assert updated.full_name == "Updated"
