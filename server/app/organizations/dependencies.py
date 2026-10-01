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


def choose_active_organization_id(
    *,
    selected_organization_id: str | None,
    default_organization_id: str | None,
    selected_is_active: bool,
    default_is_active: bool,
) -> tuple[str | None, bool]:
    """Choose only between organization memberships already proven active."""
    if selected_is_active:
        return selected_organization_id, False
    if default_is_active:
        return (
            default_organization_id,
            selected_organization_id is not None and selected_organization_id != default_organization_id,
        )
    return None, False


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
    if not selected_organization_id and not default_organization_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization context has not been provisioned",
        )

    organization_repository = OrganizationRepository(organizations_collection)
    membership_repository = OrganizationMembershipRepository(memberships_collection)
    organization = None
    membership = None
    if selected_organization_id:
        organization = await organization_repository.get_active(selected_organization_id)
        membership = await membership_repository.get_active_membership(
            organization_id=selected_organization_id,
            user_id=principal.user_id,
        )
    # A stale session selector must not lock a multi-organization user out.
    # Fall back only to their proven default membership; never trust a client
    # selector or replace a still-valid explicit selection.
    selected_is_active = organization is not None and membership is not None
    fallback_organization = None
    fallback_membership = None
    if (
        not selected_is_active
        and default_organization_id
        and default_organization_id != selected_organization_id
    ):
        fallback_organization = await organization_repository.get_active(default_organization_id)
        fallback_membership = await membership_repository.get_active_membership(
            organization_id=default_organization_id,
            user_id=principal.user_id,
        )
    default_is_active = fallback_organization is not None and fallback_membership is not None
    organization_id, active_scope_recovered = choose_active_organization_id(
        selected_organization_id=selected_organization_id,
        default_organization_id=default_organization_id,
        selected_is_active=selected_is_active,
        default_is_active=default_is_active,
    )
    if active_scope_recovered or selected_organization_id is None:
        organization = fallback_organization
        membership = fallback_membership

    if organization is None or membership is None:
        # Do not distinguish a bad selector from a missing membership.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")

    if session.get("active_organization_id") != organization_id:
        # A fallback is a server recovery, not an authority decision. Guard
        # the write with the selector we read so a concurrent user-initiated
        # switch cannot be overwritten by this request.
        result = await sessions_collection.update_one(
            {
                "session_id": principal.session_id,
                "revoked_at": None,
                "active_organization_id": selected_organization_id,
            },
            {
                "$set": {
                    "active_organization_id": organization_id,
                    "updated_at": now_utc(),
                }
            },
        )
        if result.matched_count != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Organization selection changed; retry the request",
            )

    return OrganizationContext(
        organization_id=organization_id,
        organization_kind=organization["kind"],
        membership_role=membership["role"],
        principal=principal,
        membership=membership,
        active_scope_recovered=active_scope_recovered,
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
        # Optional-auth endpoints retain their anonymous behavior when an
        # incomplete legacy identity is supplied. Normal token resolution
        # already requires `sid`, so this is a defensive compatibility guard.
        return None
    principal = OrganizationPrincipal(
        user_id=current_user.id,
        session_id=session_id,
        platform_role=current_user.role or "user",
    )
    try:
        return await resolve_active_organization_context(
            current_user=current_user,
            principal=principal,
            sessions_collection=sessions_collection,
            organizations_collection=organizations_collection,
            memberships_collection=memberships_collection,
        )
    except HTTPException as exc:
        # Optional routes retain guest behavior when an authenticated identity
        # cannot prove a usable tenant. Callers must not persist tenant-owned
        # data unless this dependency returns an organization context.
        if exc.status_code in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
        }:
            return None
        raise
