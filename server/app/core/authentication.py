from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from server.app.core.config import settings
from server.app.db.core.connection import get_user_sessions_collection, get_users_collection
from server.app.users.identity import ACTIVE_USER_STATUSES, coerce_user_status, now_utc
from server.app.users.models import UserOut
from server.app.users.repository import build_user_out_payload, get_active_session


async def resolve_user_from_access_token(
    token: str,
    *,
    users_collection=None,
    sessions_collection=None,
    update_last_seen: bool = True,
) -> UserOut:
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
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except (InvalidTokenError, DecodeError):
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    jti: str | None = payload.get("jti")
    session_id: str | None = payload.get("sid")
    token_type: str | None = payload.get("type")

    if not user_id or not jti or not session_id or token_type != "access":
        raise credentials_exception

    if users_collection is None:
        users_collection = get_users_collection()
    if sessions_collection is None:
        sessions_collection = get_user_sessions_collection()

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    if user is None:
        raise credentials_exception
    if coerce_user_status(user) not in ACTIVE_USER_STATUSES:
        raise HTTPException(status_code=403, detail="Account is not active")

    session = await get_active_session(
        sessions_collection,
        session_id=session_id,
        user_id=user_id,
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Session has been revoked")

    if update_last_seen:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_seen_at": now_utc()}},
        )

    user_payload = build_user_out_payload(user)
    if isinstance(user_payload.get("created_at"), datetime):
        user_payload["created_at"] = user_payload["created_at"].isoformat()
    return UserOut(**user_payload)


async def try_resolve_user_from_access_token(
    token: str,
    *,
    users_collection=None,
    sessions_collection=None,
    update_last_seen: bool = True,
) -> UserOut | None:
    try:
        return await resolve_user_from_access_token(
            token,
            users_collection=users_collection,
            sessions_collection=sessions_collection,
            update_last_seen=update_last_seen,
        )
    except HTTPException:
        return None
