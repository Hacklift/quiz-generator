from contextvars import ContextVar, Token
from dataclasses import dataclass, field


_authorization_header: ContextVar[str | None] = ContextVar(
    "mcp_authorization_header",
    default=None,
)


@dataclass(frozen=True)
class McpRequestContext:
    user_id: str | None = None
    is_authenticated: bool = False
    is_verified: bool = False
    role: str | None = None
    scopes: set[str] = field(default_factory=set)
    tenant_id: str | None = None


def set_authorization_header(value: str | None) -> Token[str | None]:
    return _authorization_header.set(value)


def reset_authorization_header(token: Token[str | None]) -> None:
    _authorization_header.reset(token)


def get_authorization_header() -> str | None:
    return _authorization_header.get()


def get_bearer_token() -> str | None:
    authorization = get_authorization_header()
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
