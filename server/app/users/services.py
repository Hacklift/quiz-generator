import json
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.auth.utils import generate_otp, generate_verification_token
from server.app.db.core.connection import get_auth_events_collection, get_user_sessions_collection
from server.app.db.core.redis import get_redis_client
from server.app.email_platform.service import EmailService
from server.app.users.identity import normalize_email, now_utc
from server.app.users.models import UpdateProfileRequest, UpdateProfileResponse, UserOut
from server.app.users.repository import (
    build_user_out_payload,
    delete_user,
    record_auth_event,
    revoke_user_sessions,
)
from server.app.users.schemas import MessageResponse


def get_user_profile_service(current_user: UserOut) -> dict:
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "bio": current_user.bio,
        "location": current_user.location,
        "website": current_user.website,
        "avatar_color": current_user.avatar_color,
        "role": current_user.role,
        "status": current_user.status,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "stripe_customer_id": current_user.stripe_customer_id,
        "stripe_subscription_id": current_user.stripe_subscription_id,
        "subscription_plan": current_user.subscription_plan,
        "subscription_status": current_user.subscription_status,
        "current_period_end": current_user.current_period_end,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


async def update_user_profile_service(
    profile_data: UpdateProfileRequest,
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
) -> UpdateProfileResponse:
    update_data = {
        f"profile.{key}": value
        for key, value in {
            "full_name": profile_data.full_name,
            "bio": profile_data.bio,
            "location": profile_data.location,
            "website": profile_data.website,
            "avatar_color": profile_data.avatar_color,
        }.items()
        if value is not None
    }
    update_data["updated_at"] = now_utc()

    try:
        user_object_id = ObjectId(current_user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user ID format: {str(exc)}",
        ) from exc

    result = await users_collection.update_one(
        {"_id": user_object_id, "status": {"$ne": "deleted"}},
        {"$set": update_data},
    )
    if result.modified_count == 0:
        user_exists = await users_collection.find_one({"_id": user_object_id, "status": {"$ne": "deleted"}})
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated_user = await users_collection.find_one({"_id": user_object_id})
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found after update",
        )

    created_at = updated_user.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    updated_at_value = updated_user.get("updated_at")
    if isinstance(updated_at_value, datetime):
        updated_at_value = updated_at_value.isoformat()

    return UpdateProfileResponse(
        message="Profile updated successfully",
        user=UserOut(
            **{
                **build_user_out_payload(updated_user),
                "created_at": created_at,
                "updated_at": updated_at_value,
            }
        ),
    )


async def request_email_change_service(
    new_email: str,
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
    email_svc: EmailService,
) -> MessageResponse:
    normalized_new_email = normalize_email(new_email)
    if normalized_new_email == normalize_email(current_user.email):
        raise HTTPException(status_code=400, detail="New email must be different.")

    existing_user = await users_collection.find_one(
        {"email_normalized": normalized_new_email, "status": {"$ne": "deleted"}}
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use.")

    redis_client = await get_redis_client()
    otp = generate_otp()
    token = generate_verification_token(new_email, purpose="email_change")
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
    await record_auth_event(
        get_auth_events_collection(),
        event_type="email_change_requested",
        status="success",
        user_id=current_user.id,
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

    normalized_new_email = normalize_email(new_email)
    existing_user = await users_collection.find_one(
        {"email_normalized": normalized_new_email, "status": {"$ne": "deleted"}}
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use.")

    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {
            "$set": {
                "email": new_email,
                "email_normalized": normalized_new_email,
                "is_verified": True,
                "status": "active",
                "updated_at": now_utc(),
            }
        },
    )
    await redis_client.delete(f"email_change:{current_user.id}")
    await record_auth_event(
        get_auth_events_collection(),
        event_type="email_change_completed",
        status="success",
        user_id=current_user.id,
    )

    return MessageResponse(message="Email updated successfully.")


async def delete_account_service(
    current_user: UserOut,
    users_collection: AsyncIOMotorCollection,
) -> MessageResponse:
    result = await delete_user(users_collection, current_user.id)
    if result.delete_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    await revoke_user_sessions(
        get_user_sessions_collection(),
        user_id=current_user.id,
        revoke_reason="account_deleted",
    )
    await record_auth_event(
        get_auth_events_collection(),
        event_type="account_deleted",
        status="success",
        user_id=current_user.id,
    )
    return MessageResponse(message="Account deleted successfully.")
