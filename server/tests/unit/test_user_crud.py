import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from bson import ObjectId
from server.app.db.crud.user_crud import create_user, get_user_by_id, update_user
from server.app.db.schemas.user_schemas import CreateUserRequest, UpdateUserSchema


@pytest.mark.asyncio
async def test_create_user_success():
    collection = AsyncMock()
    collection.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

    user = CreateUserRequest(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="Abcd1234!",
    )

    result = await create_user(collection, user)

    assert result is not None
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_id_success():
    user_id = ObjectId()
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": user_id,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "quizzes": [],
        "is_active": True,
        "is_verified": False,
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await get_user_by_id(collection, str(user_id))

    assert result is not None
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_update_user_success():
    user_id = ObjectId()
    collection = AsyncMock()
    collection.find_one_and_update.return_value = {
        "_id": user_id,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Updated",
        "quizzes": [],
        "is_active": True,
        "is_verified": False,
        "role": "user",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    update = UpdateUserSchema(full_name="Updated")

    result = await update_user(collection, str(user_id), update)

    assert result is not None
    assert result.full_name == "Updated"
