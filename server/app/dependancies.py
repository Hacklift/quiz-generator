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




async def get_current_user(


    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),

    users_collection = Depends(get_users_collection),

    blacklist_collection = Depends(get_blacklisted_tokens_collection)

) -> UserOut:

    token = credentials.credentials

    credentials_exception = HTTPException(

        status_code=status.HTTP_401_UNAUTHORIZED,

        detail="Could not validate credentials",

    )


    try:

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])

        user_id: str = payload.get("sub")

        jti: str = payload.get("jti")

        if user_id is None or jti is None:

            raise credentials_exception

    except (ExpiredSignatureError, InvalidTokenError, DecodeError):

        raise credentials_exception


    blacklisted = await blacklist_collection.find_one({"jti": jti})

    if blacklisted:

        raise HTTPException(status_code=401, detail="Token has been revoked")


    user = await users_collection.find_one({"_id": ObjectId(user_id)})

    if user is None:

        raise credentials_exception


    return UserOut(

        id=str(user["_id"]),

        username=user["username"],

        email=user["email"],

        is_active=user.get("is_active", True),

        created_at=str(user.get("created_at"))

    )
