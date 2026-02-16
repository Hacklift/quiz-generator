"""
Enhanced Rate Limiter Configuration for FastAPI
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Callable


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_rate_limit_key(request: Request) -> str:
    
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        return f"token:{hash(token)}"
    
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["200/hour"],  
    storage_uri=REDIS_URL,
    strategy="fixed-window",  
    headers_enabled=True,  
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    retry_after = getattr(exc, "retry_after", None)
    
    response_content = {
        "error": "rate_limit_exceeded",
        "message": "Too many requests. Please slow down and try again later.",
        "detail": str(exc.detail) if hasattr(exc, "detail") else None,
    }
    
    if retry_after:
        response_content["retry_after_seconds"] = retry_after
    
    return JSONResponse(
        status_code=429,
        content=response_content,
        headers={"Retry-After": str(retry_after)} if retry_after else {}
    )

class RateLimits:
    
    AUTH_LOGIN = "5/minute;20/hour"  
    AUTH_REGISTER = "3/hour"  
    AUTH_PASSWORD_RESET = "3/hour"  
    AUTH_VERIFY = "10/minute"  
    AUTH_REFRESH = "30/hour"  
    
    
    QUIZ_GENERATE = "10/minute;50/hour"  
    QUIZ_DOWNLOAD = "20/minute"
    
    
    API_READ = "100/minute;500/hour"  
    API_WRITE = "30/minute;200/hour"  
    
    
    PUBLIC = "50/minute"


def custom_rate_limit(limit: str):
    
    def decorator(func):
        return limiter.limit(limit)(func)
    return decorator