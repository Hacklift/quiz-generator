import hmac
from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse

from server.app.core.config import settings
from server.app.mcp.context import reset_authorization_header, set_authorization_header

INTERNAL_MCP_HEADER = b"x-internal-mcp-token"


class McpAuthorizationHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive: Callable, send: Callable[..., Awaitable[None]]):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        authorization = None
        internal_token = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"authorization":
                authorization = value.decode("latin1")
            if key.lower() == INTERNAL_MCP_HEADER:
                internal_token = value.decode("latin1")

        expected_token = settings.resolved_assistant_internal_mcp_secret
        if not internal_token or not hmac.compare_digest(internal_token, expected_token):
            response = JSONResponse(
                {"detail": "Internal MCP endpoint is not available."},
                status_code=403,
            )
            await response(scope, receive, send)
            return

        token = set_authorization_header(authorization)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_authorization_header(token)
