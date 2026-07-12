from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import model_validator
from pymongo.errors import OperationFailure

from server.app.users.repository import backfill_user_identity_fields


class PyObjectId(ObjectId):
    def __get_pydantic_json_schema__(self, *args, **kwargs):
        return {
            "type": "string",
            "description": "MongoDB ObjectId",
        }

    @classmethod
    @model_validator(mode="before")
    def check_valid_objectid(cls, values):
        value = values.get("value")
        if value is not None and not isinstance(value, ObjectId):
            raise ValueError("Invalid ObjectId")
        return values


async def ensure_user_collections(
    database,
    users_collection: AsyncIOMotorCollection,
    user_sessions_collection: AsyncIOMotorCollection,
    auth_events_collection: AsyncIOMotorCollection,
    *,
    backfill_limit: int = 100_000,
):
    """Prepare user-domain collections during application startup."""
    await backfill_user_identity_fields(users_collection, limit=backfill_limit)
    await ensure_users_validator(database)
    await ensure_user_session_validator(database)
    await ensure_auth_event_validator(database)
    await ensure_user_indexes(users_collection)
    await ensure_user_session_indexes(user_sessions_collection)
    await ensure_auth_event_indexes(auth_events_collection)


async def ensure_user_indexes(users_collection: AsyncIOMotorCollection):
    await users_collection.create_index(
        "email_normalized",
        unique=True,
        partialFilterExpression={"deleted_at": None},
    )
    await users_collection.create_index(
        "username_normalized",
        unique=True,
        partialFilterExpression={"deleted_at": None},
    )
    await users_collection.create_index("status")
    await users_collection.create_index("created_at")
    await users_collection.create_index("last_login_at")
    await users_collection.create_index("is_active")
    await users_collection.create_index("stripe_customer_id", sparse=True)
    await users_collection.create_index("stripe_subscription_id", sparse=True)


async def ensure_users_validator(database):
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "email",
                "email_normalized",
                "username",
                "username_normalized",
                "hashed_password",
                "status",
                "is_verified",
                "created_at",
                "updated_at",
                "schema_version",
            ],
            "properties": {
                "email": {"bsonType": "string", "minLength": 3},
                "email_normalized": {"bsonType": "string", "minLength": 3},
                "username": {"bsonType": "string", "minLength": 1},
                "username_normalized": {"bsonType": "string", "minLength": 1},
                "hashed_password": {"bsonType": "string", "minLength": 1},
                "status": {
                    "enum": ["pending_verification", "active", "suspended", "deleted"],
                },
                "is_verified": {"bsonType": "bool"},
                "is_active": {"bsonType": "bool"},
                "role": {"bsonType": "string"},
                "stripe_customer_id": {"bsonType": ["string", "null"]},
                "stripe_subscription_id": {"bsonType": ["string", "null"]},
                "subscription_plan": {"bsonType": ["string", "null"]},
                "subscription_status": {"bsonType": ["string", "null"]},
                "current_period_end": {"bsonType": ["string", "null"]},
                "profile": {
                    "bsonType": ["object", "null"],
                    "properties": {
                        "full_name": {"bsonType": ["string", "null"]},
                        "bio": {"bsonType": ["string", "null"]},
                        "location": {"bsonType": ["string", "null"]},
                        "website": {"bsonType": ["string", "null"]},
                        "avatar_color": {"bsonType": ["string", "null"]},
                    },
                },
                "password_changed_at": {"bsonType": ["date", "null"]},
                "last_login_at": {"bsonType": ["date", "null"]},
                "last_seen_at": {"bsonType": ["date", "null"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": ["date", "null"]},
                "deleted_at": {"bsonType": ["date", "null"]},
                "deleted_by": {"bsonType": ["string", "null"]},
                "deletion_reason": {"bsonType": ["string", "null"]},
                "schema_version": {"bsonType": "int", "minimum": 1},
            },
        }
    }
    await _ensure_collection_validator(database, "users", validator)


async def ensure_user_session_indexes(user_sessions_collection: AsyncIOMotorCollection):
    await user_sessions_collection.create_index("session_id", unique=True)
    await user_sessions_collection.create_index("jti", unique=True)
    await user_sessions_collection.create_index("user_id")
    await user_sessions_collection.create_index([("user_id", 1), ("revoked_at", 1)])
    await user_sessions_collection.create_index("expires_at", expireAfterSeconds=0)


async def ensure_user_session_validator(database):
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "user_id",
                "session_id",
                "jti",
                "refresh_token_hash",
                "created_at",
                "updated_at",
                "expires_at",
            ],
            "properties": {
                "user_id": {"bsonType": "string"},
                "session_id": {"bsonType": "string"},
                "jti": {"bsonType": "string"},
                "refresh_token_hash": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
                "last_used_at": {"bsonType": ["date", "null"]},
                "expires_at": {"bsonType": "date"},
                "revoked_at": {"bsonType": ["date", "null"]},
                "revoke_reason": {"bsonType": ["string", "null"]},
                "device_info": {"bsonType": ["object", "null"]},
                "ip_address": {"bsonType": ["string", "null"]},
                "user_agent": {"bsonType": ["string", "null"]},
            },
        }
    }
    await _ensure_collection_validator(database, "user_sessions", validator)


async def ensure_auth_event_indexes(auth_events_collection: AsyncIOMotorCollection):
    await auth_events_collection.create_index("user_id")
    await auth_events_collection.create_index([("event_type", 1), ("created_at", -1)])
    await auth_events_collection.create_index("created_at")


async def ensure_auth_event_validator(database):
    validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["event_type", "status", "created_at"],
            "properties": {
                "user_id": {"bsonType": ["string", "null"]},
                "event_type": {"bsonType": "string"},
                "status": {"bsonType": "string"},
                "ip_address": {"bsonType": ["string", "null"]},
                "user_agent": {"bsonType": ["string", "null"]},
                "metadata": {"bsonType": "object"},
                "created_at": {"bsonType": "date"},
            },
        }
    }
    await _ensure_collection_validator(database, "auth_events", validator)


async def _ensure_collection_validator(database, collection_name: str, validator: dict):
    try:
        await database.command(
            {
                "collMod": collection_name,
                "validator": validator,
                "validationLevel": "moderate",
                "validationAction": "error",
            }
        )
    except OperationFailure as exc:
        if exc.code == 26:
            await database.create_collection(
                collection_name,
                validator=validator,
                validationLevel="moderate",
                validationAction="error",
            )
        else:
            raise
