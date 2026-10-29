from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import OperationFailure


async def ensure_organization_collections(
    database,
    organizations_collection: AsyncIOMotorCollection,
    memberships_collection: AsyncIOMotorCollection,
    invitations_collection: AsyncIOMotorCollection | None = None,
) -> None:
    await _ensure_collection_validator(
        database,
        "organizations",
        _organization_validator(),
    )
    await _ensure_collection_validator(
        database,
        "organization_memberships",
        _membership_validator(),
    )
    await _ensure_organization_indexes(organizations_collection)
    await _ensure_membership_indexes(memberships_collection)
    if invitations_collection is not None:
        await _ensure_collection_validator(
            database,
            "organization_invitations",
            _invitation_validator(),
        )
        await _ensure_invitation_indexes(invitations_collection)


async def _ensure_collection_validator(database, name: str, validator: dict) -> None:
    try:
        await database.command(
            {
                "collMod": name,
                "validator": validator,
                "validationLevel": "moderate",
                "validationAction": "error",
            }
        )
    except OperationFailure as exc:
        if exc.code != 26:
            raise
        await database.create_collection(
            name,
            validator=validator,
            validationLevel="moderate",
            validationAction="error",
        )


async def _ensure_organization_indexes(collection: AsyncIOMotorCollection) -> None:
    await collection.create_index(
        "personal_owner_user_id",
        name="organization_personal_owner_unique",
        unique=True,
        partialFilterExpression={"personal_owner_user_id": {"$type": "string"}},
    )
    await collection.create_index(
        "system_key",
        name="organization_system_key_unique",
        unique=True,
        partialFilterExpression={"system_key": {"$type": "string"}},
    )
    await collection.create_index(
        [("status", 1), ("kind", 1)],
        name="organization_status_kind",
    )


async def _ensure_membership_indexes(collection: AsyncIOMotorCollection) -> None:
    await collection.create_index(
        [("organization_id", 1), ("user_id", 1)],
        name="organization_membership_unique",
        unique=True,
    )
    await collection.create_index(
        [("user_id", 1), ("status", 1)],
        name="organization_membership_user_status",
    )
    await collection.create_index(
        [("organization_id", 1), ("status", 1), ("role", 1)],
        name="organization_membership_scope_status_role",
    )


async def _ensure_invitation_indexes(collection: AsyncIOMotorCollection) -> None:
    # Earlier development builds created these membership-only indexes on the
    # invitation collection. Remove only our named mistakes before ensuring
    # the correct invitation indexes; no application data is affected.
    existing_indexes = await collection.index_information()
    for index_name in (
        "organization_membership_user_status",
        "organization_membership_scope_status_role",
    ):
        if index_name in existing_indexes:
            await collection.drop_index(index_name)
    await collection.create_index(
        [("organization_id", 1), ("email_normalized", 1)],
        name="organization_invitation_scope_email_unique",
        unique=True,
    )
    await collection.create_index(
        "token_hash",
        name="organization_invitation_token_unique",
        unique=True,
    )
    await collection.create_index(
        [("status", 1), ("expires_at", 1)],
        name="organization_invitation_status_expiry",
    )
    await collection.create_index(
        [("organization_id", 1), ("_id", -1)],
        name="organization_invitation_scope_cursor",
    )


def _organization_validator() -> dict:
    return {
        "$and": [
            {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": [
                        "kind",
                        "name",
                        "status",
                        "settings",
                        "personal_owner_user_id",
                        "system_key",
                        "created_by_user_id",
                        "created_at",
                        "updated_at",
                    ],
                    "properties": {
                        "kind": {"enum": ["personal", "school", "tutoring", "corporate"]},
                        "name": {"bsonType": "string", "minLength": 1, "maxLength": 160},
                        "status": {"enum": ["provisioning", "active", "suspended", "archived"]},
                        "settings": {"bsonType": "object"},
                        "personal_owner_user_id": {
                            "bsonType": ["string", "null"],
                            "minLength": 1,
                        },
                        "system_key": {"enum": ["platform_library", None]},
                        "created_by_user_id": {"bsonType": ["string", "null"]},
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"},
                    },
                }
            },
            # Personal organizations are always user-owned, except for the
            # one deliberate platform tenant used by curated content.
            {
                "$or": [
                    {"kind": {"$ne": "personal"}},
                    {"personal_owner_user_id": {"$type": "string"}},
                    {"system_key": "platform_library"},
                ]
            },
            # `system_key` is a platform-reserved identity, never a flag that
            # can be attached to a customer organization.
            {
                "$or": [
                    {"system_key": {"$exists": False}},
                    {"system_key": None},
                    {
                        "$and": [
                            {"kind": "personal"},
                            {"system_key": "platform_library"},
                            {"personal_owner_user_id": None},
                            {"created_by_user_id": None},
                        ]
                    },
                ]
            },
        ]
    }


def _membership_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "organization_id",
                "user_id",
                "role",
                "status",
                "joined_at",
                "invited_by_user_id",
                "created_at",
                "updated_at",
            ],
            "properties": {
                "organization_id": {"bsonType": "string", "minLength": 1},
                "user_id": {"bsonType": "string", "minLength": 1},
                "role": {
                    "enum": [
                        "owner",
                        "admin",
                        "author",
                        "facilitator",
                        "learner",
                        "guardian",
                        "auditor",
                    ]
                },
                "status": {"enum": ["invited", "active", "suspended", "removed"]},
                "joined_at": {"bsonType": ["date", "null"]},
                "invited_by_user_id": {"bsonType": ["string", "null"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    }


def _invitation_validator() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "organization_id",
                "email",
                "email_normalized",
                "role",
                "status",
                "token_hash",
                "invited_by_user_id",
                "accepted_by_user_id",
                "acceptance_claim_id",
                "acceptance_lease_expires_at",
                "expires_at",
                "accepted_at",
                "declined_at",
                "revoked_at",
                "email_delivery_status",
                "email_delivery_attempted_at",
                "created_at",
                "updated_at",
            ],
            "properties": {
                "organization_id": {"bsonType": "string", "minLength": 1},
                "email": {"bsonType": "string", "minLength": 3, "maxLength": 320},
                "email_normalized": {"bsonType": "string", "minLength": 3, "maxLength": 320},
                "role": {
                    "enum": ["admin", "author", "facilitator", "learner", "guardian", "auditor"]
                },
                "status": {"enum": ["invited", "accepting", "accepted", "declined", "revoked", "expired"]},
                "token_hash": {"bsonType": "string", "minLength": 64, "maxLength": 64},
                "invited_by_user_id": {"bsonType": "string", "minLength": 1},
                "accepted_by_user_id": {"bsonType": ["string", "null"]},
                "acceptance_claim_id": {"bsonType": ["string", "null"]},
                "acceptance_lease_expires_at": {"bsonType": ["date", "null"]},
                "expires_at": {"bsonType": "date"},
                "accepted_at": {"bsonType": ["date", "null"]},
                "declined_at": {"bsonType": ["date", "null"]},
                "revoked_at": {"bsonType": ["date", "null"]},
                "email_delivery_status": {"enum": ["pending", "sent", "failed"]},
                "email_delivery_attempted_at": {"bsonType": ["date", "null"]},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"},
            },
        }
    }
