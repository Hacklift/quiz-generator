from fastapi import APIRouter, HTTPException, Depends, Request, status
from redis.asyncio import Redis
from server.app.db.core.connection import startUp, get_users_collection, get_quizzes_collection, get_blacklisted_tokens_collection
from motor.motor_asyncio import AsyncIOMotorCollection
from server.schemas.model.password_reset_model import PasswordResetRequest, PasswordResetResponse, RequestPasswordReset, MessageResponse
#from server.schemas.model import UserModel, LoginRequestModel, LoginResponseModel
from ..auth.services import (
    register_user_service,
    verify_otp_service,
    verify_link_service,
    resend_verification_email_service,
    login_service,
    request_password_reset_service,
    reset_password_service,
    #get_current_user,
    logout_service
)
from server.app.auth.utils import generate_otp, generate_verification_token, create_access_token
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from server.app.db.schemas.user_schemas import  UserRegisterSchema, UserResponseSchema, ResendVerificationRequest
from server.app.db.models.user_models import UserDB
from server.app.dependancies import get_current_user
from server.app.auth.models import LoginRequestModel, LoginResponse
from server.app.db.core.redis import get_redis_client

router = APIRouter()

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
security = HTTPBearer()
TOKEN_BLACKLIST_PREFIX = "blacklist:"

@router.get("/ping")
async def ping():
    return {"message": "Auth route is active"}

@router.post("/register/", response_model=UserResponseSchema)
async def register_user(user: UserRegisterSchema):
    return await register_user_service(user)

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
async def resend_verification(request: ResendVerificationRequest):
    return await resend_verification_email_service(request.email)

@router.post("/login", response_model=LoginResponse)
async def login(
    request_data: LoginRequestModel, 
    request: Request):
    users_collection = request.app.state.users_collection
    return await login_service(
        identifier=request_data.identifier,
        password=request_data.password,
        users_collection=users_collection
    )

@router.get("/profile")
def get_profile(current_user: UserDB = Depends(get_current_user)):
    return {"username": current_user.username}

@router.post("/request-password-reset", response_model=MessageResponse)
async def request_password_reset(request: RequestPasswordReset):
    return await request_password_reset_service(request)

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(request: PasswordResetRequest):
    return await reset_password_service(request)

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    # token: str = Depends(oauth2_scheme),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    blacklist_collection = Depends(get_blacklisted_tokens_collection)
):
    token = credentials.credentials
    return await logout_service(token, blacklist_collection)
   