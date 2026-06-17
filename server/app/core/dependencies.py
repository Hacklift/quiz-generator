from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.app.core.authentication import (
    resolve_user_from_access_token,
    try_resolve_user_from_access_token,
)
from server.app.db.core.connection import (
    get_user_sessions_collection,
    get_users_collection,
)
from server.app.users.models import UserOut

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    users_collection=Depends(get_users_collection),
    sessions_collection=Depends(get_user_sessions_collection),
) -> UserOut:
    """
    Extract and validate the current user from a JWT token.
    Returns a UserOut object if successful.
    """
    return await resolve_user_from_access_token(
        credentials.credentials,
        users_collection=users_collection,
        sessions_collection=sessions_collection,
    )

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    users_collection=Depends(get_users_collection),
    sessions_collection=Depends(get_user_sessions_collection),
) -> UserOut | None:
    """
    Optional version of get_current_user. Returns None when no/invalid token is provided.
    """
    if credentials is None:
        return None

    return await try_resolve_user_from_access_token(
        credentials.credentials,
        users_collection=users_collection,
        sessions_collection=sessions_collection,
    )


async def get_verified_user(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Ensure the current authenticated user has a verified email."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return current_user
