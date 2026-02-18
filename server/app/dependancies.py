from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    DecodeError
)
from bson import ObjectId
from typing import Dict
from server.app.db.core.config import settings
from .auth.utils import decode_token
from server.app.db.core.redis import get_redis_client
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import PyMongoError
from server.app.db.core.connection import get_users_collection, get_blacklisted_tokens_collection
from server.app.db.models.user_models import UserOut
import redis.asyncio as redis

redis_client = get_redis_client()

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    users_collection=Depends(get_users_collection),
    blacklist_collection=Depends(get_blacklisted_tokens_collection),
) -> UserOut:
    """
    Extract and validate the current user from a JWT token.
    Returns a UserOut object if successful.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")

        if not user_id or not jti:
            raise credentials_exception

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except (ExpiredSignatureError, InvalidTokenError, DecodeError): 
        raise credentials_exception

    # Check if token has been blacklisted (revoked)
    blacklisted = await blacklist_collection.find_one({"jti": jti})
    if blacklisted:
        raise HTTPException(status_code=401, detail="Token has been revoked")

    # Fetch the user from DB
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if user is None:
        raise credentials_exception

    # Handle date fields gracefully
    created_at = user.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    updated_at = user.get("updated_at")
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    # Return a UserOut object
    return UserOut(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        full_name=user.get("full_name"),
        bio=user.get("bio"),
        location=user.get("location"),
        website=user.get("website"),
        avatar_color=user.get("avatar_color", "#143E6F"),
        role=user.get("role", "user"),
        is_active=user.get("is_active", True),
        is_verified=user.get("is_verified", False),
        created_at=created_at,
        updated_at=updated_at,
    )

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    users_collection=Depends(get_users_collection),
    blacklist_collection=Depends(get_blacklisted_tokens_collection),
) -> UserOut | None:
    """
    Optional version of get_current_user. Returns None when no/invalid token is provided.
    """
    if credentials is None:
        return None

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")

        if not user_id or not jti:
            return None

    except (ExpiredSignatureError, InvalidTokenError, DecodeError):
        return None

    blacklisted = await blacklist_collection.find_one({"jti": jti})
    if blacklisted:
        return None

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

    if user is None:
        return None

    created_at = user.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    updated_at = user.get("updated_at")
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    return UserOut(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        full_name=user.get("full_name"),
        bio=user.get("bio"),
        location=user.get("location"),
        website=user.get("website"),
        avatar_color=user.get("avatar_color", "#143E6F"),
        role=user.get("role", "user"),
        is_active=user.get("is_active", True),
        is_verified=user.get("is_verified", False),
        created_at=created_at,
        updated_at=updated_at,
    )
