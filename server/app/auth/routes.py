from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from ..auth.services import (
    register_user_service,
    verify_otp_service,
    verify_link_service,
    resend_verification_email_service,
    login_service,
    refresh_token_service,
    request_password_reset_service,
    reset_password_service,
    logout_service,
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from server.app.users.schemas import (
    MessageResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RequestPasswordReset,
    UserRegisterSchema, 
    UserResponseSchema, 
    ResendVerificationRequest,
)
from server.app.auth.models import (
    LoginRequestModel,
    LoginResponse,
    RefreshTokenResponse,
    RefreshTokenRequest,
    VerifyLinkRequest,
    VerifyOtpRequest,
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.core.config import settings

# Import rate limiter
from server.app.core.rate_limiter import limiter, RateLimits

router = APIRouter()
security = HTTPBearer()

@router.get("/ping")
@limiter.limit("100/minute")
async def ping(request: Request, response: Response):
    return {"message": "Auth route is active"}

@router.post("/register/", response_model=UserResponseSchema)
@limiter.limit(RateLimits.AUTH_REGISTER)  
async def register_user(
    request: Request,
    response: Response,
    user: UserRegisterSchema,
    email_svc: EmailService = Depends(get_email_service),
):
    return await register_user_service(user, email_svc=email_svc)

@router.post("/verify-otp/")
@limiter.limit(RateLimits.AUTH_VERIFY)
async def verify_otp(request: Request, response: Response, payload: VerifyOtpRequest):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis
    return await verify_otp_service(payload.email, payload.otp, users_collection, redis_client)

@router.post("/verify-link/")
@limiter.limit(RateLimits.AUTH_VERIFY)
async def verify_link(request: Request, response: Response, payload: VerifyLinkRequest):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis
    return await verify_link_service(payload.token, users_collection, redis_client)

@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("5/hour")  
async def resend_verification(
    request: Request,
    response: Response,
    req: ResendVerificationRequest,
    email_svc: EmailService = Depends(get_email_service),
):
    return await resend_verification_email_service(req.email, email_svc=email_svc)

@router.post("/login", response_model=LoginResponse)
@limiter.limit(RateLimits.AUTH_LOGIN)  
async def login(
    request: Request,
    response: Response,
    request_data: LoginRequestModel, 
):
    users_collection = request.app.state.users_collection
    result = await login_service(
        identifier=request_data.identifier,
        password=request_data.password,
        users_collection=users_collection,
        sessions_collection=request.app.state.user_sessions_collection,
        auth_events_collection=request.app.state.auth_events_collection,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    refresh_token = result.get("refresh_token")
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
        )
    return {
        "message": result.get("message", "Login successful"),
        "access_token": result["access_token"],
        "token_type": result.get("token_type", "bearer"),
        "is_verified": result.get("is_verified", False),
    }

@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit(RateLimits.AUTH_REFRESH)  
async def refresh_token(
    request: Request,
    response: Response,
    request_data: RefreshTokenRequest,
):
    """Refresh access token using refresh token"""
    users_collection = request.app.state.users_collection
    cookie_refresh_token = request.cookies.get("refresh_token")
    token = request_data.refresh_token or cookie_refresh_token
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    result = await refresh_token_service(
        refresh_token=token,
        users_collection=users_collection,
        sessions_collection=request.app.state.user_sessions_collection,
        auth_events_collection=request.app.state.auth_events_collection,
    )
    new_refresh_token = result.get("refresh_token")
    if new_refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
        )
    return {
        "access_token": result["access_token"],
        "token_type": result.get("token_type", "bearer"),
    }

@router.post("/request-password-reset", response_model=MessageResponse)
@limiter.limit(RateLimits.AUTH_PASSWORD_RESET)  
async def request_password_reset(
    request: Request,
    response: Response,
    req: RequestPasswordReset,
    email_svc: EmailService = Depends(get_email_service),
):
    return await request_password_reset_service(req, email_svc=email_svc)

@router.post("/reset-password", response_model=PasswordResetResponse)
@limiter.limit(RateLimits.AUTH_VERIFY)  
async def reset_password(
    request: Request,
    response: Response,
    req: PasswordResetRequest
):
    return await reset_password_service(req)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    users_collection = request.app.state.users_collection
    response.delete_cookie("refresh_token", path="/")
    return await logout_service(token, users_collection)
