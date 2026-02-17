from fastapi import Request, HTTPException, Depends, status
from typing import Dict
from redis import Redis
import random
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import jwt
import uuid
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    DecodeError
)
from server.app.db.models.user_models import (
    UserDB,
    UserOut,
    UpdateProfileRequest,
    UpdateProfileResponse
    )
import os
from fastapi.security import OAuth2PasswordBearer
import redis
from server.app.db.core.connection import users_collection, blacklisted_tokens_collection, get_blacklisted_tokens_collection
from motor.motor_asyncio import AsyncIOMotorCollection
from server.app.db.crud.user_crud import create_user, get_user_by_email
from server.app.db.schemas.user_schemas import  UserRegisterSchema, UserResponseSchema, CreateUserRequest, PasswordResetRequest, PasswordResetResponse, RequestPasswordReset, ResendVerificationRequest, MessageResponse
from server.app.db.crud.user_crud import delete_user
import json
from .utils import (
    verify_password, 
    create_access_token, 
    generate_otp, 
    generate_verification_token, 
    decode_verification_token,     
    create_refresh_token, 
    decode_refresh_token,
    hash_token,
    verify_token_hash)
from server.app.db.core.redis import get_redis_client
from passlib.context import CryptContext
from server.app.db.core.config import settings
from server.app.email_platform.service import EmailService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
  

async def register_user_service(user: UserRegisterSchema, email_svc: EmailService) -> UserResponseSchema:
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

    await email_svc.send_email(
        to=user.email,
        template_id="verification",
        template_vars={"code": otp, "token": token},
        purpose="verification",              # Celery → Background → Direct
        priority="default",
    )

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

async def resend_verification_email_service(email: str, email_svc: EmailService) -> MessageResponse:
    user_data = await users_collection.find_one({"email": email})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Email already verified")

    redis_client = await get_redis_client()

    otp = generate_otp()
    token = generate_verification_token(email)

    await redis_client.setex(f"otp:{email}", timedelta(minutes=10), otp)
    await redis_client.setex(f"token:{email}", timedelta(minutes=30), token)

    await email_svc.send_email(
        to=email,
        template_id="verification",
        template_vars={"code": otp, "token": token},
        purpose="verification",  # Celery → Background → Direct
        priority="default",
    )

    return MessageResponse(message="Verification email resent successfully")

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
    """Handle user login and generate access + refresh tokens"""
    
    # Find user by email or username
    user = await users_collection.find_one({
        "$or": [{"email": identifier}, {"username": identifier}]
    })
    
    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")
    
    user_id = str(user["_id"])
    
    access_token = create_access_token({"sub": user_id})
    
    refresh_token, jti, expires_at = create_refresh_token({"sub": user_id})
    
    hashed_refresh_token = hash_token(refresh_token)
    
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "refresh_token": hashed_refresh_token,
                "refresh_token_jti": jti,
                "refresh_token_expires_at": expires_at
            }
        }
    )
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

async def refresh_token_service(refresh_token: str, users_collection: AsyncIOMotorCollection):
    try:
        payload = decode_refresh_token(refresh_token)
    except HTTPException:
        raise
    
    user_id = payload.get("sub")
    token_jti = payload.get("jti")
    
    if not user_id or not token_jti:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    stored_token_hash = user.get("refresh_token")
    stored_jti = user.get("refresh_token_jti")
    token_expires_at = user.get("refresh_token_expires_at")
    
    if not stored_token_hash or not stored_jti:
        raise HTTPException(status_code=401, detail="No refresh token found")
    
    if not verify_token_hash(refresh_token, stored_token_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if token_jti != stored_jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if token_expires_at:
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > token_expires_at:
            raise HTTPException(status_code=401, detail="Refresh token expired")

    
    new_access_token = create_access_token({"sub": user_id})

    new_refresh_token, new_jti, new_expires_at = create_refresh_token({"sub": user_id})
    hashed_new_refresh_token = hash_token(new_refresh_token)
    
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "refresh_token": hashed_new_refresh_token,
                "refresh_token_jti": new_jti,
                "refresh_token_expires_at": new_expires_at
            }
        }
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

async def request_password_reset_service(request: RequestPasswordReset, email_svc: EmailService):
    user = await users_collection.find_one({"email": request.email})
    message = {"message": "If this email exists, reset instructions have been sent."}
    if not user:
        return message
    
    otp = generate_otp()
    token = generate_verification_token(request.email)
    
    redis_client = await get_redis_client()
    await redis_client.setex(f"otp:{request.email}", 300, otp)
    await redis_client.setex(f"token:{request.email}", 1800, token)

    await email_svc.send_email(
        to=request.email,
        template_id="password_reset",
        template_vars={"code": otp, "token": token},
        purpose="password_reset",           # Celery → Background → Direct
        priority="default",
    )

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

def get_user_profile_service(current_user: UserOut) -> dict:
    """Return serialized user profile"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "bio": current_user.bio,
        "location": current_user.location,
        "website": current_user.website,
        "avatar_color": current_user.avatar_color,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


async def update_user_profile_service(
    profile_data: UpdateProfileRequest,
    current_user: UserOut,
    users_collection  
) -> UpdateProfileResponse:
    try:
        update_data = {}

        if profile_data.full_name is not None:
            update_data["full_name"] = profile_data.full_name
        if profile_data.bio is not None:
            update_data["bio"] = profile_data.bio
        if profile_data.location is not None:
            update_data["location"] = profile_data.location
        if profile_data.website is not None:
            update_data["website"] = profile_data.website
        if profile_data.avatar_color is not None:
            update_data["avatar_color"] = profile_data.avatar_color

        update_data["updated_at"] = datetime.now(timezone.utc)

        try:
            user_object_id = ObjectId(current_user.id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID format: {str(e)}"
            )

        result = await users_collection.update_one(
            {"_id": user_object_id},
            {"$set": update_data}
        )

        if result.modified_count == 0:
            user_exists = await users_collection.find_one({"_id": user_object_id})
            if not user_exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

        updated_user = await users_collection.find_one({"_id": user_object_id})
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found after update"
            )

        created_at = updated_user.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        updated_at_value = updated_user.get("updated_at")
        if isinstance(updated_at_value, datetime):
            updated_at_value = updated_at_value.isoformat()

        user_out = UserOut(
            id=str(updated_user["_id"]),
            username=updated_user["username"],
            email=updated_user["email"],
            full_name=updated_user.get("full_name"),
            bio=updated_user.get("bio"),
            location=updated_user.get("location"),
            website=updated_user.get("website"),
            avatar_color=updated_user.get("avatar_color", "#143E6F"),
            is_active=updated_user.get("is_active", True),
            is_verified=updated_user.get("is_verified", False),
            created_at=created_at,
            updated_at=updated_at_value,
        )

        return UpdateProfileResponse(
            message="Profile updated successfully",
            user=user_out
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
            )


async def request_email_change_service(
    new_email: str,
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
    email_svc: EmailService,
) -> MessageResponse:
    if new_email.lower() == current_user.email.lower():
        raise HTTPException(status_code=400, detail="New email must be different.")

    existing_user = await users_collection.find_one({"email": new_email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use.")

    redis_client = await get_redis_client()
    otp = generate_otp()
    token = generate_verification_token(new_email)

    payload = json.dumps({"new_email": new_email, "otp": otp, "token": token})
    await redis_client.setex(
        f"email_change:{current_user.id}",
        timedelta(minutes=10),
        payload,
    )

    await email_svc.send_email(
        to=new_email,
        template_id="verification",
        template_vars={"code": otp, "token": token},
        purpose="verification",
        priority="default",
    )

    return MessageResponse(message="Verification code sent to new email.")


async def verify_email_change_service(
    otp: str,
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
) -> MessageResponse:
    redis_client = await get_redis_client()
    stored = await redis_client.get(f"email_change:{current_user.id}")
    if not stored:
        raise HTTPException(status_code=400, detail="No pending email change request.")

    data = json.loads(stored)
    stored_otp = data.get("otp")
    new_email = data.get("new_email")

    if otp != stored_otp:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    existing_user = await users_collection.find_one({"email": new_email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use.")

    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"email": new_email, "is_verified": True, "updated_at": datetime.now(timezone.utc)}},
    )

    await redis_client.delete(f"email_change:{current_user.id}")
    return MessageResponse(message="Email updated successfully.")


async def delete_account_service(
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
) -> MessageResponse:
    result = await delete_user(users_collection, current_user.id)
    if result.delete_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return MessageResponse(message="Account deleted successfully.")
