from fastapi import HTTPException

from server.app.core.authentication import resolve_user_from_access_token
from server.app.db.core.connection import (
    get_organization_memberships_collection,
    get_organizations_collection,
    get_user_sessions_collection,
)
from server.app.organizations.dependencies import resolve_active_organization_context
from server.app.organizations.models import OrganizationPrincipal
from server.app.mcp.context import McpRequestContext, get_bearer_token


class McpAuthenticationError(PermissionError):
    pass


class McpAuthorizationError(PermissionError):
    pass


async def get_mcp_request_context(
    *,
    require_auth: bool = False,
    require_verified: bool = False,
    required_scopes: set[str] | None = None,
) -> McpRequestContext:
    token = get_bearer_token()
    if not token:
        if require_auth:
            raise McpAuthenticationError("Authentication required. Send Authorization: Bearer <access_token>.")
        return McpRequestContext()

    try:
        user = await resolve_user_from_access_token(token)
    except HTTPException as exc:
        if require_auth:
            raise McpAuthenticationError(str(exc.detail))
        return McpRequestContext()

    if not user.session_id:
        raise McpAuthenticationError("Session context is missing.")
    try:
        organization_context = await resolve_active_organization_context(
            current_user=user,
            principal=OrganizationPrincipal(
                user_id=str(user.id),
                session_id=user.session_id,
                platform_role=user.role or "user",
            ),
            sessions_collection=get_user_sessions_collection(),
            organizations_collection=get_organizations_collection(),
            memberships_collection=get_organization_memberships_collection(),
        )
    except HTTPException as exc:
        raise McpAuthorizationError(str(exc.detail)) from exc

    context = McpRequestContext(
        user_id=str(user.id),
        is_authenticated=True,
        is_verified=bool(user.is_verified),
        role=user.role,
        scopes=required_scopes or set(),
        tenant_id=organization_context.organization_id,
        tenant_kind=organization_context.organization_kind,
        organization_context=organization_context,
    )

    if require_verified and not context.is_verified:
        raise McpAuthorizationError("Email verification is required for this MCP action.")

    return context
