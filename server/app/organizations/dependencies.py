from __future__ import annotations

from fastapi import Depends, HTTPException, status

from server.app.core.dependencies import get_current_user, get_current_user_optional
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
) -> OrganizationPrincipal:
    """Bind the validated user to the session that carries active scope."""
    session_id = current_user.session_id
    if not session_id:
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
    return await resolve_active_organization_context(
        current_user=current_user,
        principal=principal,
        sessions_collection=sessions_collection,
        organizations_collection=organizations_collection,
        memberships_collection=memberships_collection,
    )


async def resolve_active_organization_context(
    *,
    current_user: UserOut,
    principal: OrganizationPrincipal,
    sessions_collection,
    organizations_collection,
    memberships_collection,
) -> OrganizationContext:
    """Resolve a scope for any authenticated transport, including MCP.

    The client never supplies authority here: the selected organization comes
    from the validated server session and is re-proven against an active
    membership before it can be used.
    """
    session = await get_active_session(
        sessions_collection,
        session_id=principal.session_id,
        user_id=principal.user_id,
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")

    selected_organization_id = session.get("active_organization_id")
    default_organization_id = current_user.default_organization_id
    organization_id = selected_organization_id or default_organization_id
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
    # A stale session selector must not lock a multi-organization user out.
    # Fall back only to their proven default membership; never trust a client
    # selector or replace a still-valid explicit selection.
    if (
        (organization is None or membership is None)
        and selected_organization_id
        and default_organization_id
        and selected_organization_id != default_organization_id
    ):
        fallback_organization = await organization_repository.get_active(default_organization_id)
        fallback_membership = await membership_repository.get_active_membership(
            organization_id=default_organization_id,
            user_id=principal.user_id,
        )
        if fallback_organization is not None and fallback_membership is not None:
            organization_id = default_organization_id
            organization = fallback_organization
            membership = fallback_membership

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


async def get_optional_active_organization_context(
    current_user: UserOut | None = Depends(get_current_user_optional),
    sessions_collection=Depends(get_user_sessions_collection),
    organizations_collection=Depends(get_organizations_collection),
    memberships_collection=Depends(get_organization_memberships_collection),
) -> OrganizationContext | None:
    """Resolve tenant scope for authenticated optional-auth endpoints only."""
    if current_user is None:
        return None
    session_id = current_user.session_id
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session context is missing",
        )
    principal = OrganizationPrincipal(
        user_id=current_user.id,
        session_id=session_id,
        platform_role=current_user.role or "user",
    )
    return await resolve_active_organization_context(
        current_user=current_user,
        principal=principal,
        sessions_collection=sessions_collection,
        organizations_collection=organizations_collection,
        memberships_collection=memberships_collection,
    )
