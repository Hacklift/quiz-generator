from fastapi import Request, HTTPException, Depends, status
from redis import Redis
import random
from datetime import datetime, timezone, timedelta
import jwt
import uuid
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    DecodeError
)
import os
from server.email_utils import send_otp_email
from fastapi.security import OAuth2PasswordBearer
import redis
from server.app.db.core.connection import users_collection, blacklisted_tokens_collection, get_blacklisted_tokens_collection
from motor.motor_asyncio import AsyncIOMotorCollection
from server.app.db.crud.user_crud import create_user, get_user_by_email
from server.app.db.schemas.user_schemas import  UserRegisterSchema, UserResponseSchema, CreateUserRequest, PasswordResetRequest, PasswordResetResponse, RequestPasswordReset, MessageResponse
from .utils import verify_password, create_access_token, generate_otp, generate_verification_token, decode_verification_token
from server.app.db.core.redis import get_redis_client
from passlib.context import CryptContext
from server.app.db.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

#mock_db: list[UserModel] = []  

async def register_user_service(user: UserRegisterSchema) -> UserResponseSchema:
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = CreateUserRequest(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        password=user.password
    )
    
    created_user = await create_user(users_collection, user_data)
    if not created_user:
        raise HTTPException(status_code=500, detail="User registration failed")
   
    redis_client = await get_redis_client()
    otp = generate_otp()
    token = generate_verification_token(user.email)
    

    await redis_client.setex(f"otp:{user.email}", timedelta(minutes=10), otp)
    await redis_client.setex(f"token:{user.email}", timedelta(minutes=30), token)

    send_otp_email(user.email, otp, token, mode="register")

    return UserResponseSchema(
        id=created_user.id,
        username=created_user.username,
        email=created_user.email,
        full_name=created_user.full_name,
        created_at=created_user.created_at, 
        updated_at=created_user.updated_at,
        is_active=created_user.is_active,
        is_verified=created_user.is_verified,
        role=created_user.role
    )

async def verify_otp_service(email: str,
    otp: str,
    users_collection: AsyncIOMotorCollection,
    redis_client: Redis):
    stored_otp = await redis_client.get(f"otp:{email}")
    attempts_raw = await redis_client.get(f"attempts:{email}")
    attempts = int(attempts_raw or 0)

    if attempts >= 4:
        raise HTTPException(status_code=403, detail="Too many attempts. Request a new OTP.")

    if stored_otp is None:
        raise HTTPException(status_code=400, detail="OTP expired or not requested.")

    if otp != stored_otp:
        await redis_client.incr(f"attempts:{email}")
        raise HTTPException(status_code=401, detail="Invalid OTP. Try again.")

    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    await users_collection.update_one(
        {"email": email},
        {"$set": {"is_verified": True}}
    )

    await redis_client.delete(f"otp:{email}")
    await redis_client.delete(f"token:{email}")
    await redis_client.delete(f"attempts:{email}")

    return {"message": "OTP verified successfully!"}

async def verify_link_service(
    token: str,
    users_collection: AsyncIOMotorCollection,
    redis_client: Redis
):
    try:
        email = decode_verification_token(token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    if not email:
        raise HTTPException(status_code=400, detail="Could not decode token.")

    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.get("is_verified"):
        return {"message": "Email already verified."}

   
    await users_collection.update_one(
        {"email": email},
        {"$set": {"is_verified": True}}
    )

  
    await redis_client.delete(f"token:{email}")
    await redis_client.delete(f"otp:{email}")
    await redis_client.delete(f"attempts:{email}")  

    return {"message": "Email verified successfully!"}

async def login_service(identifier: str, password: str, users_collection: AsyncIOMotorCollection):
    user = await users_collection.find_one({
        "$or": [{"email": identifier}, {"username": identifier}]
    })
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")
    token = create_access_token({"sub": str(user["_id"])})
    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer"
    }

async def request_password_reset_service(request: RequestPasswordReset):
    user = await users_collection.find_one({"email": request.email})
    message = {"message": "If this email exists, reset instructions have been sent."}
    if not user:
        return message
    
    otp = generate_otp()
    token = generate_verification_token(request.email)
    
    redis_client = await get_redis_client()
    await redis_client.setex(f"otp:{request.email}", 300, otp)
    await redis_client.setex(f"token:{request.email}", 1800, token)

    send_otp_email(request.email, otp, token, mode="reset")
    return message

async def reset_password_service(request: PasswordResetRequest):
    redis_client = await get_redis_client()
    user = await users_collection.find_one({"email": request.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.reset_method == "otp":
        stored_otp = await redis_client.get(f"otp:{request.email}")
        if stored_otp is None:
            raise HTTPException(status_code=400, detail="OTP expired or not found")
        if request.otp != stored_otp:  
            raise HTTPException(status_code=401, detail="Invalid OTP")

    elif request.reset_method == "token":
        if not request.token:
            raise HTTPException(status_code=400, detail="Token is required")
        try:
            email_from_token = decode_verification_token(request.token)
        except HTTPException as e:
            raise e
        if email_from_token != request.email:
            raise HTTPException(status_code=403, detail="Token email mismatch")

    hashed_password = pwd_context.hash(request.new_password)

    
    result = await users_collection.update_one(
        {"email": request.email},
        {"$set": {"hashed_password": hashed_password}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Password reset failed")

   
    await redis_client.delete(f"otp:{request.email}")
    await redis_client.delete(f"token:{request.email}")

    return PasswordResetResponse(message="Password reset successful", success=True)

async def logout_service(token: str, blacklist_collection = Depends(get_blacklisted_tokens_collection)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti or not exp:
            raise HTTPException(status_code=400, detail="Invalid token or missing JTI/exp")

        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)

        await blacklisted_tokens_collection.insert_one({
            "jti": jti,
            "expires_at": expires_at
        })

        return {"message": "Logged out successfully"}
    
    except (ExpiredSignatureError, InvalidTokenError, DecodeError):
         raise HTTPException(status_code=401, detail="Invalid token or expired token")
    except Exception as e:
         raise HTTPException(status_code=500, detail="An error occurred during logout") from e