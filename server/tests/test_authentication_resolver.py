from datetime import datetime, timedelta, timezone
import os

from bson import ObjectId
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("EMAIL_SENDER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("EMAIL_HOST", "smtp.example.com")
os.environ.setdefault("EMAIL_PORT", "587")
os.environ.setdefault("SHARE_URL", "http://localhost:3000")
os.environ.setdefault("DB_NAME", "quizApp_test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("FERNET_KEY", "l65zsWSMsTUO0VNMNxhXCQ0UKlTuBXZH8QC0a5F18fM=")

from server.app.auth.utils import create_access_token
from server.app.core.authentication import resolve_user_from_access_token


class FakeCollection:
    def __init__(self, document=None):
        self.document = document
        self.updated = None

    async def find_one(self, _query):
        return self.document

    async def update_one(self, query, update):
        self.updated = {"query": query, "update": update}


@pytest.mark.asyncio
async def test_resolve_user_from_access_token_validates_session_and_returns_user():
    user_id = str(ObjectId())
    session_id = "session-1"
    users_collection = FakeCollection(
        {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "profile": {"full_name": "Test User"},
            "is_active": True,
            "is_verified": True,
            "status": "active",
            "role": "user",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    sessions_collection = FakeCollection(
        {
            "session_id": session_id,
            "user_id": user_id,
            "revoked_at": None,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        }
    )

    token = create_access_token({"sub": user_id}, session_id=session_id)

    user = await resolve_user_from_access_token(
        token,
        users_collection=users_collection,
        sessions_collection=sessions_collection,
    )

    assert user.id == user_id
    assert user.email == "test@example.com"
    assert users_collection.updated["query"] == {"_id": ObjectId(user_id)}
