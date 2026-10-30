from __future__ import annotations

from pymongo.errors import OperationFailure


def _identifier() -> dict:
    return {"bsonType": "string", "pattern": "^[0-9a-f]{24}$"}


def cohort_validator() -> dict:
    properties = {
        "_id": {"bsonType": "objectId"},
        "organization_id": _identifier(),
        "kind": {"enum": ["class", "course", "team", "department", "campaign"]},
        "name": {"bsonType": "string", "minLength": 1, "maxLength": 160, "pattern": "\\S"},
        "parent_cohort_id": {"bsonType": ["string", "null"], "pattern": "^[0-9a-f]{24}$"},
        "status": {"enum": ["active", "archived"]},
        "created_by_user_id": _identifier(),
        "created_at": {"bsonType": "date"},
        "updated_at": {"bsonType": "date"},
    }
    return {"$jsonSchema": {
        "bsonType": "object", "required": list(properties),
        "additionalProperties": False, "properties": properties,
    }}


def cohort_membership_validator() -> dict:
    properties = {
        "_id": {"bsonType": "objectId"},
        "organization_id": _identifier(),
        "cohort_id": _identifier(),
        "user_id": _identifier(),
        "role": {"enum": ["facilitator", "member", "guardian"]},
        "status": {"enum": ["active", "removed"]},
        "can_assign": {"bsonType": "bool"},
        "can_report": {"bsonType": "bool"},
        "created_by_user_id": _identifier(),
        "created_at": {"bsonType": "date"},
        "updated_at": {"bsonType": "date"},
    }
    return {"$and": [
        {"$jsonSchema": {
            "bsonType": "object", "required": list(properties),
            "additionalProperties": False, "properties": properties,
        }},
        {"$or": [
            {"role": "facilitator"}, {"can_assign": False, "can_report": False},
        ]},
    ]}


async def _ensure_validator(database, name: str, validator: dict) -> None:
    command = {
        "collMod": name, "validator": validator,
        "validationLevel": "strict", "validationAction": "error",
    }
    try:
        await database.command(command)
    except OperationFailure as exc:
        if exc.code != 26:
            raise
        try:
            await database.create_collection(
                name, validator=validator,
                validationLevel="strict", validationAction="error",
                check_exists=False,
            )
        except OperationFailure as create_error:
            if create_error.code != 48:
                raise
            # Another application process created it between collMod and create.
            await database.command(command)


async def ensure_cohort_collections(database) -> None:
    """Startup hook; safe for repeated/concurrent application initialization."""
    await _ensure_validator(database, "cohorts", cohort_validator())
    await _ensure_validator(database, "cohort_memberships", cohort_membership_validator())
    await _ensure_validator(database, "cohort_hierarchy_locks", {"$jsonSchema": {
        "bsonType": "object", "required": ["_id", "token", "expires_at"],
        "additionalProperties": False,
        "properties": {
            "_id": _identifier(), "token": {"bsonType": "string"},
            "expires_at": {"bsonType": "date"},
        },
    }})
    cohorts = database["cohorts"]
    memberships = database["cohort_memberships"]
    await cohorts.create_index(
        [("organization_id", 1), ("status", 1), ("_id", -1)],
        name="cohort_scope_status_cursor",
    )
    await cohorts.create_index(
        [("organization_id", 1), ("parent_cohort_id", 1), ("status", 1)],
        name="cohort_scope_parent_status",
    )
    await memberships.create_index(
        [("organization_id", 1), ("cohort_id", 1), ("user_id", 1)],
        unique=True, name="cohort_membership_scope_user_unique",
    )
    await memberships.create_index(
        [("organization_id", 1), ("cohort_id", 1), ("status", 1), ("_id", -1)],
        name="cohort_membership_scope_cursor",
    )
    await memberships.create_index(
        [("organization_id", 1), ("user_id", 1), ("status", 1), ("cohort_id", 1)],
        name="cohort_membership_user_scope",
    )
