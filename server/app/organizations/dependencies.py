from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.app.core.dependencies import get_current_user
from server.app.db.core.connection import (
    get_organization_memberships_collection,
    get_organizations_collection,
    get_user_sessions_collection,
)
from server.app.organizations.models import (
    OrganizationContext,
    OrganizationPrincipal,
)
from server.app.organizations.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from server.app.users.models import UserOut
from server.app.users.identity import now_utc
from server.app.users.repository import get_active_session


async def get_organization_principal(
    current_user: UserOut = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> OrganizationPrincipal:
    """Bind the validated user to the session that carries active scope."""
    # Keep settings out of module import so data-context tests and migration
    # tooling do not require unrelated email/runtime configuration.
    from server.app.core.config import settings

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError as exc:
        # get_current_user normally rejects this first. Keep this dependency
        # independently safe if FastAPI dependency ordering changes.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

    session_id = payload.get("sid")
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session context is missing",
        )
    return OrganizationPrincipal(
        user_id=current_user.id,
        session_id=session_id,
        platform_role=current_user.role or "user",
    )


async def get_active_organization_context(
    principal: OrganizationPrincipal = Depends(get_organization_principal),
    current_user: UserOut = Depends(get_current_user),
    sessions_collection=Depends(get_user_sessions_collection),
    organizations_collection=Depends(get_organizations_collection),
    memberships_collection=Depends(get_organization_memberships_collection),
) -> OrganizationContext:
    """Resolve server-owned active scope and prove membership for every request."""
    session = await get_active_session(
        sessions_collection,
        session_id=principal.session_id,
        user_id=principal.user_id,
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")

    organization_id = session.get("active_organization_id") or current_user.default_organization_id
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization context has not been provisioned",
        )

    organization_repository = OrganizationRepository(organizations_collection)
    membership_repository = OrganizationMembershipRepository(memberships_collection)
    organization = await organization_repository.get_active(organization_id)
    membership = await membership_repository.get_active_membership(
        organization_id=organization_id,
        user_id=principal.user_id,
    )
    if organization is None or membership is None:
        # Do not distinguish a bad selector from a missing membership.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")

    if session.get("active_organization_id") != organization_id:
        await sessions_collection.update_one(
            {"session_id": principal.session_id, "revoked_at": None},
            {
                "$set": {
                    "active_organization_id": organization_id,
                    "updated_at": now_utc(),
                }
            },
        )

    return OrganizationContext(
        organization_id=organization_id,
        organization_kind=organization["kind"],
        membership_role=membership["role"],
        principal=principal,
        membership=membership,
    )
