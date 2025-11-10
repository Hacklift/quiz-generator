from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from server.app.db.core.connection import get_blacklisted_tokens_collection
from server.schemas.model.password_reset_model import (
    PasswordResetRequest, 
    PasswordResetResponse, 
    RequestPasswordReset, 
    MessageResponse
)
from typing import Dict
from server.app.db.core.connection import get_blacklisted_tokens_collection, get_users_collection
from server.schemas.model.password_reset_model import PasswordResetRequest, PasswordResetResponse, RequestPasswordReset, MessageResponse
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
    get_user_profile_service,
    update_user_profile_service
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from server.app.db.schemas.user_schemas import (
    UserRegisterSchema, 
    UserResponseSchema, 
    ResendVerificationRequest
)
from server.app.db.models.user_models import UserDB
from server.app.db.schemas.user_schemas import  UserRegisterSchema, UserResponseSchema, ResendVerificationRequest
from server.app.db.models.user_models import (
    UserDB,
    UserOut,
    UpdateProfileRequest,
    UpdateProfileResponse
    ) 
from server.app.dependancies import get_current_user
from server.app.auth.models import (
    LoginRequestModel, 
    LoginResponse,
    RefreshTokenResponse,
    RefreshTokenRequest
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService

# Import rate limiter
from server.app.db.core.rate_limiter import limiter, RateLimits

router = APIRouter()
security = HTTPBearer()
TOKEN_BLACKLIST_PREFIX = "blacklist:"

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
async def verify_otp(request: Request, response: Response, email: str, otp: str):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis
    return await verify_otp_service(email, otp, users_collection, redis_client)

@router.post("/verify-link/")
@limiter.limit(RateLimits.AUTH_VERIFY)
async def verify_link(request: Request, response: Response, token: str):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis
    return await verify_link_service(token, users_collection, redis_client)

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
    return await login_service(
        identifier=request_data.identifier,
        password=request_data.password,
        users_collection=users_collection
    )

@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit(RateLimits.AUTH_REFRESH)  
async def refresh_token(
    request: Request,
    response: Response,
    request_data: RefreshTokenRequest,
):
    """Refresh access token using refresh token"""
    users_collection = request.app.state.users_collection
    return await refresh_token_service(
        refresh_token=request_data.refresh_token,
        users_collection=users_collection
    )

@router.get("/profile")
@limiter.limit(RateLimits.API_READ)  
async def get_profile(
    request: Request,
    response: Response,
    current_user: UserDB = Depends(get_current_user)
):
    return {"username": current_user.username}

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
    blacklist_collection = Depends(get_blacklisted_tokens_collection),
):
    token = credentials.credentials
    return await logout_service(token, blacklist_collection)
