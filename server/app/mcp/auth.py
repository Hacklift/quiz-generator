from fastapi import HTTPException

from server.app.core.authentication import resolve_user_from_access_token
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

    context = McpRequestContext(
        user_id=str(user.id),
        is_authenticated=True,
        is_verified=bool(user.is_verified),
        role=user.role,
        scopes=required_scopes or set(),
    )

    if require_verified and not context.is_verified:
        raise McpAuthorizationError("Email verification is required for this MCP action.")

    return context
