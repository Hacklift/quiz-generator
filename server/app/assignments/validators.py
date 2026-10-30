"""Additive setup for immutable quiz revision records."""

from pymongo.errors import OperationFailure


async def ensure_assignment_collections(database):
    validator = {"$jsonSchema": {
        "bsonType": "object",
        "required": ["organization_id", "quiz_id", "content_hash", "snapshot", "created_by_user_id", "created_at", "schema_version"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "organization_id": {"bsonType": "string", "minLength": 1},
            "quiz_id": {"bsonType": "string", "minLength": 1},
            "content_hash": {"bsonType": "string", "minLength": 64, "maxLength": 64},
            "created_by_user_id": {"bsonType": "string", "minLength": 1},
            "created_at": {"bsonType": "date"},
            "schema_version": {"enum": [1]},
            "snapshot": {
                "bsonType": "object", "required": ["title", "quiz_type", "questions"],
                "additionalProperties": False,
                "properties": {
                    "title": {"bsonType": "string"}, "quiz_type": {"bsonType": "string"},
                    "questions": {"bsonType": "array", "minItems": 1, "items": {"bsonType": "object"}},
                },
            },
        },
    }}
    command = {
        "collMod": "quiz_revisions", "validator": validator,
        "validationLevel": "strict", "validationAction": "error",
    }
    try:
        await database.command(command)
    except OperationFailure as error:
        if error.code != 26:
            raise
        try:
            await database.create_collection(
                "quiz_revisions", validator=validator, check_exists=False,
                validationLevel="strict", validationAction="error",
            )
        except OperationFailure as create_error:
            if create_error.code != 48:
                raise
            await database.command(command)
    await database["quiz_revisions"].create_index(
        [("organization_id", 1), ("quiz_id", 1), ("content_hash", 1)],
        unique=True, name="organization_quiz_revision_content",
    )
    await database["training_runs"].create_index(
        [("organization_id", 1), ("delivery_kind", 1), ("cohort_id", 1), ("_id", -1)],
        name="organization_cohort_assignments",
    )
    await database["training_runs"].create_index(
        [("organization_id", 1), ("delivery_kind", 1), ("_id", -1)],
        name="organization_delivery_cursor",
    )
    await database["training_assignments"].create_index(
        [("organization_id", 1), ("recipient_user_id", 1), ("training_run_id", 1)],
        name="organization_recipient_assignment",
    )
    await database["training_assignments"].create_index(
        [("organization_id", 1), ("delivery_kind", 1), ("recipient_user_id", 1), ("_id", -1)],
        name="organization_recipient_delivery_cursor",
    )
    await database["training_assignments"].create_index(
        [("organization_id", 1), ("training_run_id", 1), ("_id", -1)],
        name="organization_assignment_register_cursor",
    )
    await database["live_quiz_sessions"].create_index(
        [("organization_id", 1), ("training_run_id", 1), ("user_id", 1), ("_id", -1)],
        name="organization_assignment_recipient_attempts",
    )
