from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from server.app.db.core.connection import users_collection
from server.app.db.schemas.user_schemas import UserResponseSchema
import jwt
from jwt.exceptions import PyJWTError
from server.app.db.core.config import settings
from bson import ObjectId

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False,
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )

        user = await users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        user["_id"] = str(user["_id"])

        return UserResponseSchema(**user)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
):
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None

        user["_id"] = str(user["_id"])
        return UserResponseSchema(**user)
    except PyJWTError:
        return None
