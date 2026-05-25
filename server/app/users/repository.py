from typing import Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from server.app.core.security import hash_password
from server.app.users.identity import (
    USER_SCHEMA_VERSION,
    build_profile,
    coerce_user_status,
    default_user_status,
    get_profile_value,
    normalize_email,
    normalize_username,
    now_utc,
)
from server.app.users.schemas import (
    CreateUserRequest,
    DeleteUserResponse,
    NewUserSchema,
    UpdateUserSchema,
    UserSchema,
)
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def serialize_user_document(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "full_name": get_profile_value(user, "full_name"),
        "quizzes": user.get("quizzes", []),
        "is_active": user.get("is_active", True),
        "is_verified": user.get("is_verified", False),
        "status": coerce_user_status(user),
        "role": user.get("role", "user"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


def build_user_out_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "full_name": get_profile_value(user, "full_name"),
        "bio": get_profile_value(user, "bio"),
        "location": get_profile_value(user, "location"),
        "website": get_profile_value(user, "website"),
        "avatar_color": get_profile_value(user, "avatar_color", "#143E6F"),
        "role": user.get("role", "user"),
        "status": coerce_user_status(user),
        "is_active": user.get("is_active", True),
        "is_verified": user.get("is_verified", False),
        "stripe_customer_id": user.get("stripe_customer_id"),
        "stripe_subscription_id": user.get("stripe_subscription_id"),
        "subscription_plan": user.get("subscription_plan", "free"),
        "subscription_status": user.get("subscription_status", "inactive"),
        "current_period_end": user.get("current_period_end"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


def active_user_query(extra: dict[str, Any]) -> dict[str, Any]:
    return {
        **extra,
        "$or": [
            {"deleted_at": {"$exists": False}},
            {"deleted_at": None},
        ],
        "status": {"$ne": "deleted"},
    }


async def create_user(users_collection: AsyncIOMotorCollection, user: CreateUserRequest) -> Optional[NewUserSchema]:
    try:
        user_dict = user.model_dump()
        now = now_utc()
        is_verified = False
        new_user_data = {
            "username": user_dict["username"].strip(),
            "username_normalized": normalize_username(user_dict["username"]),
            "email": user_dict["email"],
            "email_normalized": normalize_email(user_dict["email"]),
            "profile": build_profile(full_name=user_dict.get("full_name")),
            "quizzes": [],
            "is_active": True,
            "is_verified": is_verified,
            "status": default_user_status(is_verified),
            "role": "user",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "subscription_plan": "free",
            "subscription_status": "inactive",
            "current_period_end": None,
            "password_changed_at": None,
            "last_login_at": None,
            "last_seen_at": None,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
            "deleted_by": None,
            "deletion_reason": None,
            "schema_version": USER_SCHEMA_VERSION,
            "hashed_password": hash_password(user_dict["password"])
        }

        new_user = await users_collection.insert_one(new_user_data)
        logger.info(f"New user created with ID: {new_user.inserted_id}")
    
        return  NewUserSchema(
            id=str(new_user.inserted_id),
            username=new_user_data["username"],
            email=user_dict["email"],
            full_name=new_user_data["profile"]["full_name"],
            is_active=new_user_data["is_active"],
            is_verified=new_user_data["is_verified"],
            status=new_user_data["status"],
            role=new_user_data["role"],
            created_at=new_user_data["created_at"],
            updated_at=new_user_data["updated_at"]
        ) 
    
    except PyMongoError as e:
        logger.error(f"Database error while creating user: {e}")
    except ValueError as e:
        logger.error(f"Invalid data: {e}")
    return None

async def get_user_by_id(users_collection: AsyncIOMotorCollection, user_id: str) -> Optional[UserSchema]:
    try:
        user = await users_collection.find_one(
            active_user_query({"_id": ObjectId(user_id)}), projection={"hashed_password": 0}
            )
        if user:
            return UserSchema(**serialize_user_document(user))
        return None
    
    except InvalidId:
        logger.error(f"Invalid user_id format: {user_id}")
    except PyMongoError as e:
        logger.error(f"Error retrieving user by ID: {e}")
    return None


async def get_user_by_email(users_collection: AsyncIOMotorCollection, email: str) -> Optional[UserSchema]:
    try:
        user = await users_collection.find_one(
            active_user_query({"email_normalized": normalize_email(email)}), projection={"hashed_password": 0}
            )
        if user:
             return UserSchema(**serialize_user_document(user))
        return None
    
    except PyMongoError as e:
        logger.error(f"Error retrieving user by email: {e}")
    return None



async def update_user(users_collection: AsyncIOMotorCollection, user_id: str, user_update: UpdateUserSchema) -> Optional[UserSchema]:
    try:
        update_data = user_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = now_utc()

        profile_updates = {}
        if "full_name" in update_data:
            profile_updates["profile.full_name"] = update_data.pop("full_name")

        password = update_data.pop("password", None)  
        if password:
            update_data["hashed_password"] = hash_password(password)
            update_data["password_changed_at"] = now_utc()

        if "email" in update_data:
            update_data["email_normalized"] = normalize_email(update_data["email"])

        if "username" in update_data:
            update_data["username"] = update_data["username"].strip()
            update_data["username_normalized"] = normalize_username(update_data["username"])

        update_data = {**update_data, **profile_updates}

        updated_user = await users_collection.find_one_and_update(
            active_user_query({"_id": ObjectId(user_id)}),
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )

        if updated_user:
            logger.info(f"User {user_id} updated successfully") 
            return UserSchema(**serialize_user_document(updated_user))

        return None
    
    except InvalidId:
        logger.error(f"Invalid user_id format: {user_id}")
    except PyMongoError as e:
        logger.error(f"Database error while updating user: {e}")
    return None
    



async def delete_user(users_collection: AsyncIOMotorCollection, user_id: str) -> Optional[DeleteUserResponse]:
    try:
        now = now_utc()
        result = await users_collection.update_one(
            active_user_query({"_id": ObjectId(user_id)}),
            {
                "$set": {
                    "status": "deleted",
                    "is_active": False,
                    "deleted_at": now,
                    "updated_at": now,
                }
            },
        )
        
        if result.modified_count > 0 :
            return DeleteUserResponse(
                message=f"User with ID {user_id} deleted successfully",
                delete_count=result.modified_count
            )
        
        return DeleteUserResponse(
            message="User not found",
            delete_count=0
        )
    
    except PyMongoError as e:
        logger.error(f"Error while deleting user: {e}")

    return DeleteUserResponse(
            message="An error occurred while deleting the user",
            delete_count=0
        )


async def list_users(users_collection: AsyncIOMotorCollection) -> List[UserSchema]:
    try:
        users_cursor = users_collection.find({}, projection={"hashed_password": 0})
        users = await users_cursor.to_list(length=None)

        return [
        UserSchema(**serialize_user_document(user))
        for user in users
        if coerce_user_status(user) != "deleted"
        ]

    except PyMongoError as e:
        logger.error(f"Database error while listing users: {e}")
    return []


async def find_user_for_login(users_collection: AsyncIOMotorCollection, identifier: str) -> dict[str, Any] | None:
    normalized = normalize_email(identifier) if "@" in identifier else normalize_username(identifier)
    return await users_collection.find_one(
        {
            "$or": [
                {"email_normalized": normalized},
                {"username_normalized": normalized},
                {"email": identifier},
                {"username": identifier},
            ]
        }
    )


async def backfill_user_identity_fields(users_collection: AsyncIOMotorCollection, *, limit: int = 1000) -> int:
    updated_count = 0
    cursor = users_collection.find(
        {
            "$or": [
                {"email_normalized": {"$exists": False}},
                {"username_normalized": {"$exists": False}},
                {"status": {"$exists": False}},
                {"profile": {"$exists": False}},
                {"schema_version": {"$exists": False}},
                {"refresh_token": {"$exists": True}},
                {"refresh_token_jti": {"$exists": True}},
                {"refresh_token_expires_at": {"$exists": True}},
            ]
        }
    )
    async for user in cursor:
        now = now_utc()
        updates = {
            "email_normalized": user.get("email_normalized") or normalize_email(user["email"]),
            "username_normalized": user.get("username_normalized") or normalize_username(user["username"]),
            "status": coerce_user_status(user),
            "profile": user.get("profile") or build_profile(
                full_name=user.get("full_name"),
                bio=user.get("bio"),
                location=user.get("location"),
                website=user.get("website"),
                avatar_color=user.get("avatar_color"),
            ),
            "is_active": user.get("is_active", True),
            "stripe_customer_id": user.get("stripe_customer_id"),
            "stripe_subscription_id": user.get("stripe_subscription_id"),
            "subscription_plan": user.get("subscription_plan", "free"),
            "subscription_status": user.get("subscription_status", "inactive"),
            "current_period_end": user.get("current_period_end"),
            "schema_version": USER_SCHEMA_VERSION,
            "updated_at": user.get("updated_at") or now,
        }
        for field in ("password_changed_at", "last_login_at", "last_seen_at", "deleted_at", "deleted_by", "deletion_reason"):
            if field not in user:
                updates[field] = None
        update_doc: dict[str, Any] = {"$set": updates}
        legacy_auth_fields = {
            field: ""
            for field in ("refresh_token", "refresh_token_jti", "refresh_token_expires_at")
            if field in user
        }
        if legacy_auth_fields:
            update_doc["$unset"] = legacy_auth_fields
        await users_collection.update_one({"_id": user["_id"]}, update_doc)
        updated_count += 1
        if updated_count >= limit:
            break
    return updated_count


async def create_user_session(
    sessions_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    session_id: str,
    jti: str,
    refresh_token_hash: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = now_utc()
    session_doc = {
        "user_id": user_id,
        "session_id": session_id,
        "jti": jti,
        "refresh_token_hash": refresh_token_hash,
        "created_at": now,
        "updated_at": now,
        "last_used_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "revoke_reason": None,
        "device_info": device_info,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    await sessions_collection.insert_one(session_doc)
    return session_doc


async def get_active_session(
    sessions_collection: AsyncIOMotorCollection,
    *,
    session_id: str,
    user_id: str | None = None,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "session_id": session_id,
        "revoked_at": None,
        "expires_at": {"$gt": now_utc()},
    }
    if user_id:
        query["user_id"] = user_id
    return await sessions_collection.find_one(query)


async def rotate_user_session(
    sessions_collection: AsyncIOMotorCollection,
    *,
    session_id: str,
    jti: str,
    refresh_token_hash: str,
    expires_at: datetime,
) -> dict[str, Any] | None:
    now = now_utc()
    return await sessions_collection.find_one_and_update(
        {"session_id": session_id, "revoked_at": None},
        {
            "$set": {
                "jti": jti,
                "refresh_token_hash": refresh_token_hash,
                "expires_at": expires_at,
                "last_used_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )


async def revoke_user_session(
    sessions_collection: AsyncIOMotorCollection,
    *,
    session_id: str,
    revoke_reason: str,
) -> int:
    result = await sessions_collection.update_one(
        {"session_id": session_id, "revoked_at": None},
        {"$set": {"revoked_at": now_utc(), "revoke_reason": revoke_reason, "updated_at": now_utc()}},
    )
    return result.modified_count


async def revoke_user_sessions(
    sessions_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    revoke_reason: str,
) -> int:
    result = await sessions_collection.update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": now_utc(), "revoke_reason": revoke_reason, "updated_at": now_utc()}},
    )
    return result.modified_count


async def record_auth_event(
    auth_events_collection: AsyncIOMotorCollection,
    *,
    event_type: str,
    status: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        await auth_events_collection.insert_one(
            {
                "user_id": user_id,
                "event_type": event_type,
                "status": status,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "metadata": metadata or {},
                "created_at": now_utc(),
            }
        )
    except PyMongoError as exc:
        logger.warning("Failed to record auth event %s: %s", event_type, exc)
