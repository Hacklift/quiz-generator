import pytest
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from bson import ObjectId
from unittest.mock import AsyncMock

from server.app.dependancies import get_current_user
from server.app.db.core.config import settings


def setup_module(module):
    settings.JWT_SECRET = "testsecret"
    settings.JWT_ALGORITHM = "HS256"


@pytest.mark.asyncio
async def test_get_current_user_rejects_blacklisted_token():
    user_id = str(ObjectId())
    payload = {
        "sub": user_id,
        "jti": "jti123",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    users_collection = AsyncMock()
    users_collection.find_one.return_value = {
        "_id": ObjectId(user_id),
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "is_verified": False,
        "created_at": None,
        "updated_at": None,
    }

    blacklist_collection = AsyncMock()
    blacklist_collection.find_one.return_value = {"jti": "jti123"}

    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            credentials=credentials,
            users_collection=users_collection,
            blacklist_collection=blacklist_collection,
        )

    assert exc.value.status_code == 401
