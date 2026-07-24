from fastapi import HTTPException
from redis import Redis
from bson import ObjectId
from datetime import timedelta
import jwt
import uuid
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
    DecodeError
)
from server.app.db.core.connection import (
    get_auth_events_collection,
    get_user_sessions_collection,
    users_collection,
)
from motor.motor_asyncio import AsyncIOMotorCollection
from server.app.users.identity import (
    ACTIVE_USER_STATUSES,
    BLOCKED_USER_STATUSES,
    coerce_user_status,
    normalize_email,
    now_utc,
)
from server.app.users.repository import (
    create_user,
    create_user_session,
    find_user_for_login,
    get_active_session,
    record_auth_event,
    revoke_user_session,
    revoke_user_sessions,
    rotate_user_session,
)
from server.app.users.schemas import (
    CreateUserRequest,
    MessageResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RequestPasswordReset,
    UserRegisterSchema,
    UserResponseSchema,
)
import hmac
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
from server.app.core.config import settings
from server.app.email_platform.service import EmailService


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
  

async def register_user_service(user: UserRegisterSchema, email_svc: EmailService) -> UserResponseSchema:
    auth_events_collection = get_auth_events_collection()
    existing_user = await users_collection.find_one(
        {
            "$or": [
                {"email_normalized": normalize_email(user.email)},
                {"username_normalized": user.username.strip().casefold()},
            ],
            "status": {"$ne": "deleted"},
        }
    )
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
    await record_auth_event(
        auth_events_collection,
        event_type="register",
        status="success",
        user_id=created_user.id,
    )
   
    redis_client = await get_redis_client()
    otp = generate_otp()
    token = generate_verification_token(user.email, purpose="email_verification")
    normalized_email = normalize_email(user.email)
    

    await redis_client.setex(f"otp:{normalized_email}", timedelta(minutes=10), otp)
    await redis_client.setex(f"token:{normalized_email}", timedelta(minutes=30), token)
    await redis_client.delete(f"attempts:{normalized_email}")

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
        status=created_user.status,
        role=created_user.role
    )

async def resend_verification_email_service(email: str, email_svc: EmailService) -> MessageResponse:
    normalized_email = normalize_email(email)
    neutral_message = MessageResponse(
        message="If an account exists for this email, a verification email has been sent."
    )
    user_data = await users_collection.find_one({"email_normalized": normalized_email})
    # Neutral responses: don't reveal whether the account exists or its state.
    if not user_data or user_data.get("is_verified", False):
        return neutral_message

    redis_client = await get_redis_client()

    otp = generate_otp()
    token = generate_verification_token(user_data["email"], purpose="email_verification")

    await redis_client.setex(f"otp:{normalized_email}", timedelta(minutes=10), otp)
    await redis_client.setex(f"token:{normalized_email}", timedelta(minutes=30), token)
    await redis_client.delete(f"attempts:{normalized_email}")

    await email_svc.send_email(
        to=user_data["email"],
        template_id="verification",
        template_vars={"code": otp, "token": token},
        purpose="verification",  # Celery → Background → Direct
        priority="default",
    )

    return neutral_message

async def verify_otp_service(email: str,
    otp: str,
    users_collection: AsyncIOMotorCollection,
    redis_client: Redis):
    normalized_email = normalize_email(email)
    stored_otp = await redis_client.get(f"otp:{normalized_email}") or await redis_client.get(f"otp:{email}")
    attempts_raw = await redis_client.get(f"attempts:{normalized_email}")
    attempts = int(attempts_raw or 0)

    if attempts >= 4:
        raise HTTPException(status_code=403, detail="Too many attempts. Request a new OTP.")

    if stored_otp is None:
        raise HTTPException(status_code=400, detail="OTP expired or not requested.")

    if not hmac.compare_digest(otp, stored_otp):
        attempts_key = f"attempts:{normalized_email}"
        await redis_client.incr(attempts_key)
        otp_ttl = await redis_client.ttl(f"otp:{normalized_email}")
        if otp_ttl and otp_ttl > 0:
            await redis_client.expire(attempts_key, otp_ttl)
        else:
            await redis_client.expire(attempts_key, 600)
        raise HTTPException(status_code=401, detail="Invalid OTP. Try again.")

    user = await users_collection.find_one({"email_normalized": normalized_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True, "status": "active", "updated_at": now_utc()}}
    )
    await record_auth_event(
        get_auth_events_collection(),
        event_type="email_verification_completed",
        status="success",
        user_id=str(user["_id"]),
    )

    await redis_client.delete(f"otp:{normalized_email}")
    await redis_client.delete(f"token:{normalized_email}")
    await redis_client.delete(f"attempts:{normalized_email}")

    return {"message": "OTP verified successfully!"}

async def verify_link_service(
    token: str,
    users_collection: AsyncIOMotorCollection,
    redis_client: Redis
):
    try:
        email = decode_verification_token(token, purpose="email_verification")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    if not email:
        raise HTTPException(status_code=400, detail="Could not decode token.")

    normalized_email = normalize_email(email)
    stored_token = await redis_client.get(f"token:{normalized_email}") or await redis_client.get(f"token:{email}")
    if not stored_token or not hmac.compare_digest(token, stored_token):
        raise HTTPException(status_code=400, detail="Invalid or already used verification link.")

    user = await users_collection.find_one({"email_normalized": normalized_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.get("is_verified"):
        return {"message": "Email already verified."}

   
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True, "status": "active", "updated_at": now_utc()}}
    )
    await record_auth_event(
        get_auth_events_collection(),
        event_type="email_verification_completed",
        status="success",
        user_id=str(user["_id"]),
    )

  
    await redis_client.delete(f"token:{normalized_email}")
    await redis_client.delete(f"otp:{normalized_email}")
    await redis_client.delete(f"attempts:{normalized_email}")

    return {"message": "Email verified successfully!"}

async def login_service(
    identifier: str,
    password: str,
    users_collection: AsyncIOMotorCollection,
    sessions_collection: AsyncIOMotorCollection | None = None,
    auth_events_collection: AsyncIOMotorCollection | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Handle user login and generate access + refresh tokens"""
    
    # Find user by email or username
    if sessions_collection is None:
        sessions_collection = get_user_sessions_collection()
    if auth_events_collection is None:
        auth_events_collection = get_auth_events_collection()
    user = await find_user_for_login(users_collection, identifier)
    
    if not user or not verify_password(password, user["hashed_password"]):
        await record_auth_event(
            auth_events_collection,
            event_type="login_failed",
            status="failed",
            metadata={"identifier": identifier},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    status_value = coerce_user_status(user)
    if status_value in BLOCKED_USER_STATUSES or status_value not in ACTIVE_USER_STATUSES:
        await record_auth_event(
            auth_events_collection,
            event_type="login_failed",
            status="blocked",
            user_id=str(user["_id"]),
            metadata={"account_status": status_value},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=403, detail="Account is not active")
    
    user_id = str(user["_id"])
    session_id = str(uuid.uuid4())
    
    access_token = create_access_token({"sub": user_id}, session_id=session_id)
    
    refresh_token, jti, expires_at = create_refresh_token({"sub": user_id}, session_id=session_id)
    
    hashed_refresh_token = hash_token(refresh_token)
    await create_user_session(
        sessions_collection,
        user_id=user_id,
        session_id=session_id,
        jti=jti,
        refresh_token_hash=hashed_refresh_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "last_login_at": now_utc(),
                "last_seen_at": now_utc(),
                "updated_at": now_utc(),
            }
        }
    )
    await record_auth_event(
        auth_events_collection,
        event_type="login_success",
        status="success",
        user_id=user_id,
        metadata={"session_id": session_id},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_verified": user.get("is_verified", False),
    }

async def refresh_token_service(
    refresh_token: str,
    users_collection: AsyncIOMotorCollection,
    sessions_collection: AsyncIOMotorCollection | None = None,
    auth_events_collection: AsyncIOMotorCollection | None = None,
):
    if sessions_collection is None:
        sessions_collection = get_user_sessions_collection()
    if auth_events_collection is None:
        auth_events_collection = get_auth_events_collection()
    try:
        payload = decode_refresh_token(refresh_token)
    except HTTPException:
        raise
    
    user_id = payload.get("sub")
    token_jti = payload.get("jti")
    session_id = payload.get("sid")
    
    if not user_id or not token_jti or not session_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if coerce_user_status(user) not in ACTIVE_USER_STATUSES:
        raise HTTPException(status_code=403, detail="Account is not active")
    
    session = await get_active_session(
        sessions_collection,
        session_id=session_id,
        user_id=user_id,
    )
    
    if not session:
        raise HTTPException(status_code=401, detail="No refresh token found")
    
    if not verify_token_hash(refresh_token, session["refresh_token_hash"]):
        await revoke_user_session(
            sessions_collection,
            session_id=session_id,
            revoke_reason="refresh_reuse_detected",
        )
        await record_auth_event(
            auth_events_collection,
            event_type="refresh_reuse_detected",
            status="failed",
            user_id=user_id,
            metadata={"session_id": session_id},
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if token_jti != session["jti"]:
        await revoke_user_session(
            sessions_collection,
            session_id=session_id,
            revoke_reason="refresh_jti_mismatch",
        )
        await record_auth_event(
            auth_events_collection,
            event_type="refresh_reuse_detected",
            status="failed",
            user_id=user_id,
            metadata={"session_id": session_id},
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    
    new_access_token = create_access_token({"sub": user_id}, session_id=session_id)

    new_refresh_token, new_jti, new_expires_at = create_refresh_token({"sub": user_id}, session_id=session_id)
    hashed_new_refresh_token = hash_token(new_refresh_token)
    await rotate_user_session(
        sessions_collection,
        session_id=session_id,
        jti=new_jti,
        refresh_token_hash=hashed_new_refresh_token,
        expires_at=new_expires_at,
    )
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen_at": now_utc(), "updated_at": now_utc()}},
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

async def request_password_reset_service(request: RequestPasswordReset, email_svc: EmailService):
    normalized_email = normalize_email(request.email)
    auth_events_collection = get_auth_events_collection()
    user = await users_collection.find_one({"email_normalized": normalized_email})
    message = {"message": "If this email exists, reset instructions have been sent."}
    if not user:
        return message
    
    otp = generate_otp()
    token = generate_verification_token(user["email"], purpose="password_reset")
    
    redis_client = await get_redis_client()
    await redis_client.setex(f"password_reset_otp:{normalized_email}", 300, otp)
    await redis_client.setex(f"password_reset_token:{normalized_email}", 1800, token)
    await redis_client.delete(f"password_reset_attempts:{normalized_email}")
    await record_auth_event(
        auth_events_collection,
        event_type="password_reset_requested",
        status="success",
        user_id=str(user["_id"]),
    )

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
    normalized_email = normalize_email(request.email)
    user = await users_collection.find_one({"email_normalized": normalized_email})

    # Neutral response: don't reveal whether the account exists.
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset credentials")

    if request.reset_method == "otp":
        attempts_key = f"password_reset_attempts:{normalized_email}"
        attempts = int(await redis_client.get(attempts_key) or 0)
        if attempts >= 4:
            raise HTTPException(status_code=403, detail="Too many attempts. Request a new reset code.")

        stored_otp = await redis_client.get(f"password_reset_otp:{normalized_email}")
        if stored_otp is None:
            raise HTTPException(status_code=400, detail="Invalid or expired reset credentials")
        if not request.otp or not hmac.compare_digest(request.otp, stored_otp):
            await redis_client.incr(attempts_key)
            otp_ttl = await redis_client.ttl(f"password_reset_otp:{normalized_email}")
            await redis_client.expire(attempts_key, otp_ttl if otp_ttl and otp_ttl > 0 else 600)
            raise HTTPException(status_code=401, detail="Invalid or expired reset credentials")

    elif request.reset_method == "token":
        if not request.token:
            raise HTTPException(status_code=400, detail="Token is required")
        stored_token = await redis_client.get(f"password_reset_token:{normalized_email}")
        if not stored_token or not hmac.compare_digest(request.token, stored_token):
            raise HTTPException(status_code=400, detail="Invalid or already used reset token")
        try:
            email_from_token = decode_verification_token(request.token, purpose="password_reset")
        except HTTPException as e:
            raise e
        if normalize_email(email_from_token) != normalized_email:
            raise HTTPException(status_code=403, detail="Token email mismatch")

    hashed_password = pwd_context.hash(request.new_password)

    
    result = await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": hashed_password, "password_changed_at": now_utc(), "updated_at": now_utc()}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Password reset failed")

    await revoke_user_sessions(
        get_user_sessions_collection(),
        user_id=str(user["_id"]),
        revoke_reason="password_reset",
    )
    await record_auth_event(
        get_auth_events_collection(),
        event_type="password_reset_completed",
        status="success",
        user_id=str(user["_id"]),
    )

   
    await redis_client.delete(f"password_reset_otp:{normalized_email}")
    await redis_client.delete(f"password_reset_token:{normalized_email}")
    await redis_client.delete(f"password_reset_attempts:{normalized_email}")

    return PasswordResetResponse(message="Password reset successful", success=True)

async def logout_service(
    token: str,
    users_collection: AsyncIOMotorCollection,
):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload.get("sub")
        session_id = payload.get("sid")

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token or missing subject")

        if user_id:
            if session_id:
                await revoke_user_session(
                    get_user_sessions_collection(),
                    session_id=session_id,
                    revoke_reason="logout",
                )
            else:
                await revoke_user_sessions(
                    get_user_sessions_collection(),
                    user_id=user_id,
                    revoke_reason="logout_legacy_token",
                )
            await record_auth_event(
                get_auth_events_collection(),
                event_type="logout",
                status="success",
                user_id=user_id,
                metadata={"session_id": session_id},
            )

        return {"message": "Logged out successfully"}
    
    except (ExpiredSignatureError, InvalidTokenError, DecodeError):
         raise HTTPException(status_code=401, detail="Invalid token or expired token")
    except Exception as e:
         raise HTTPException(status_code=500, detail="An error occurred during logout") from e
