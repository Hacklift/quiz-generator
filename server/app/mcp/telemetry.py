import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from server.app.mcp.auth import McpAuthenticationError, McpAuthorizationError

logger = logging.getLogger(__name__)


def instrument_mcp_call(name: str):
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            started_at = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    "mcp_call_success",
                    extra={
                        "mcp_name": name,
                        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    },
                )
                return result
            except (McpAuthenticationError, McpAuthorizationError):
                logger.warning(
                    "mcp_call_auth_error",
                    extra={
                        "mcp_name": name,
                        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    },
                )
                raise
            except Exception:
                logger.exception(
                    "mcp_call_error",
                    extra={
                        "mcp_name": name,
                        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    },
                )
                raise

        return wrapper

    return decorator
