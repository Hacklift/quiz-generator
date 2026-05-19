from .constants import (
    FOLDER_ITEMS_V2_COLLECTION,
    FOLDERS_V2_COLLECTION,
    QUIZ_HISTORY_V2_COLLECTION,
    QUIZZES_V2_COLLECTION,
    SAVED_QUIZZES_V2_COLLECTION,
)


def get_v2_collection_validators() -> dict[str, dict]:
    return {
        QUIZZES_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": [
                    "title",
                    "quiz_type",
                    "questions",
                    "visibility",
                    "status",
                    "source",
                    "schema_version",
                    "created_at",
                    "updated_at",
                ],
                "properties": {
                    "title": {"bsonType": "string", "minLength": 1},
                    "description": {"bsonType": ["string", "null"]},
                    "owner_user_id": {"bsonType": ["string", "null"]},
                    "quiz_type": {"enum": ["multichoice", "true-false", "open-ended"]},
                    "visibility": {"enum": ["private", "public", "unlisted"]},
                    "status": {"enum": ["active", "archived", "deleted"]},
                    "source": {"enum": ["ai", "manual", "seed", "legacy"]},
                    "tags": {"bsonType": "array"},
                    "legacy_source_collection": {"bsonType": ["string", "null"]},
                    "legacy_quiz_id": {"bsonType": ["string", "null"]},
                    "content_fingerprint": {"bsonType": ["string", "null"]},
                    "structure_fingerprint": {"bsonType": ["string", "null"]},
                    "schema_version": {"bsonType": "int"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                    "deleted_at": {"bsonType": ["date", "null"]},
                    "questions": {
                        "bsonType": "array",
                        "minItems": 1,
                        "items": {
                            "bsonType": "object",
                            "required": ["question", "correct_answer"],
                            "properties": {
                                "question": {"bsonType": "string", "minLength": 1},
                                "correct_answer": {"bsonType": "string", "minLength": 1},
                                "options": {
                                    "bsonType": ["array", "null"],
                                    "items": {"bsonType": "string"},
                                },
                            },
                        },
                    },
                },
            }
        },
        FOLDERS_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "name", "created_at", "updated_at"],
                "properties": {
                    "user_id": {"bsonType": "string", "minLength": 1},
                    "name": {"bsonType": "string", "minLength": 1},
                    "description": {"bsonType": ["string", "null"]},
                    "legacy_folder_id": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                    "deleted_at": {"bsonType": ["date", "null"]},
                },
            }
        },
        FOLDER_ITEMS_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["folder_id", "quiz_id", "created_at"],
                "properties": {
                    "folder_id": {"bsonType": "string", "minLength": 1},
                    "quiz_id": {"bsonType": "string", "minLength": 1},
                    "added_by": {"bsonType": ["string", "null"]},
                    "position": {"bsonType": ["int", "null"]},
                    "display_title": {"bsonType": ["string", "null"]},
                    "legacy_folder_item_id": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "deleted_at": {"bsonType": ["date", "null"]},
                },
            }
        },
        SAVED_QUIZZES_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "quiz_id", "saved_at"],
                "properties": {
                    "user_id": {"bsonType": "string", "minLength": 1},
                    "quiz_id": {"bsonType": "string", "minLength": 1},
                    "display_title": {"bsonType": ["string", "null"]},
                    "legacy_saved_quiz_id": {"bsonType": ["string", "null"]},
                    "saved_at": {"bsonType": "date"},
                    "deleted_at": {"bsonType": ["date", "null"]},
                },
            }
        },
        QUIZ_HISTORY_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "quiz_id", "action", "created_at"],
                "properties": {
                    "user_id": {"bsonType": "string", "minLength": 1},
                    "quiz_id": {"bsonType": "string", "minLength": 1},
                    "action": {"bsonType": "string", "minLength": 1},
                    "metadata": {"bsonType": ["object", "null"]},
                    "legacy_history_id": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "deleted_at": {"bsonType": ["date", "null"]},
                },
            }
        },
    }
