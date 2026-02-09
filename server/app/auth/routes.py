from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
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


router = APIRouter()

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
security = HTTPBearer()
TOKEN_BLACKLIST_PREFIX = "blacklist:"

@router.get("/ping")
async def ping():
    return {"message": "Auth route is active"}

@router.post("/register/", response_model=UserResponseSchema)
async def register_user(
    user: UserRegisterSchema,
    email_svc: EmailService = Depends(get_email_service),
    ):
    return await register_user_service(user, email_svc=email_svc)

@router.post("/verify-otp/")
async def verify_otp(email: str, otp: str, request: Request):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis

    return await verify_otp_service(email, otp, users_collection, redis_client)

@router.post("/verify-link/")
async def verify_link(token: str, request: Request):
    users_collection = request.app.state.users_collection
    redis_client = request.app.state.redis
    return await verify_link_service(token, users_collection, redis_client)

@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    email_svc: EmailService = Depends(get_email_service),
    ):
    return await resend_verification_email_service(request.email, email_svc=email_svc)

@router.post("/login", response_model=LoginResponse)
async def login(
    request_data: LoginRequestModel, 
    request: Request
):
    users_collection = request.app.state.users_collection
    return await login_service(
        identifier=request_data.identifier,
        password=request_data.password,
        users_collection=users_collection
    )

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request
):
    """Refresh access token using refresh token"""
    users_collection = request.app.state.users_collection
    return await refresh_token_service(
        refresh_token=request_data.refresh_token,
        users_collection=users_collection
    )

@router.post("/request-password-reset", response_model=MessageResponse)
async def request_password_reset(
    request: RequestPasswordReset,
    email_svc: EmailService = Depends(get_email_service),
    ):
    return await request_password_reset_service(request, email_svc=email_svc)

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(request: PasswordResetRequest):
    return await reset_password_service(request)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    blacklist_collection = Depends(get_blacklisted_tokens_collection)
):
    token = credentials.credentials
    return await logout_service(token, blacklist_collection)

@router.get("/profile", response_model=Dict)
async def get_profile(current_user: UserOut = Depends(get_current_user)):
    """Get the current user's profile"""
    return get_user_profile_service(current_user)


@router.put("/profile", response_model=UpdateProfileResponse)
async def update_profile(
    profile_data: UpdateProfileRequest,
    current_user: UserOut = Depends(get_current_user),  
    users_collection=Depends(get_users_collection) 
):
    """Update the current user's profile"""
    return await update_user_profile_service(
        profile_data, 
        current_user, 
        users_collection 
    )
   