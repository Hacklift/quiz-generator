from .constants import (
    FOLDER_ITEMS_V2_COLLECTION,
    FOLDERS_V2_COLLECTION,
    QUIZ_HISTORY_V2_COLLECTION,
    QUIZ_ATTEMPTS_V2_COLLECTION,
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
                    "quiz_type": {"enum": ["multichoice", "true-false", "open-ended", "short-answer", "matching"]},
                    "visibility": {"enum": ["private", "public", "unlisted"]},
                    "status": {"enum": ["active", "archived", "deleted"]},
                    "source": {"enum": ["ai", "manual", "seed", "legacy"]},
                    "tags": {"bsonType": "array"},
                    "category": {"bsonType": ["string", "null"]},
                    "category_slug": {"bsonType": ["string", "null"]},
                    "subcategory": {"bsonType": ["string", "null"]},
                    "subcategory_slug": {"bsonType": ["string", "null"]},
                    "persona_category": {"enum": ["school", "corporate", None]},
                    "classification": {
                        "bsonType": ["object", "null"],
                        "required": ["method", "confidence"],
                        "properties": {
                            "method": {"enum": ["seed_path", "deterministic", "ai", "manual"]},
                            "confidence": {"bsonType": ["double", "int", "long", "decimal", "null"]},
                        },
                    },
                    "legacy_source_collection": {"bsonType": ["string", "null"]},
                    "legacy_quiz_id": {"bsonType": ["string", "null"]},
                    "content_fingerprint": {"bsonType": ["string", "null"]},
                    "structure_fingerprint": {"bsonType": ["string", "null"]},
                    "live_quiz_enabled": {"bsonType": "bool"},
                    "time_limit_minutes": {"bsonType": ["int", "null"]},
                    "access_code": {"bsonType": ["string", "null"]},
                    "access_code_expires_at": {"bsonType": ["date", "null"]},
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
                                "correct_answer": {"bsonType": ["string", "object"]},
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
                    "saved_quiz_id": {"bsonType": ["string", "null"]},
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
        QUIZ_ATTEMPTS_V2_COLLECTION: {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "quiz_id", "status", "score", "total_questions", "percentage", "question_results", "submitted_at", "graded_at", "created_at", "updated_at", "grading_policy_version"],
                "properties": {
                    "user_id": {"bsonType": "string", "minLength": 1},
                    "quiz_id": {"bsonType": "string", "minLength": 1},
                    "status": {"enum": ["completed"]},
                    "score": {"bsonType": ["int", "long"]},
                    "total_questions": {"bsonType": ["int", "long"]},
                    "percentage": {"bsonType": ["double", "int", "long", "decimal"]},
                    "submitted_at": {"bsonType": "date"},
                    "graded_at": {"bsonType": "date"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                    "grading_policy_version": {"bsonType": "string", "minLength": 1},
                    "question_results": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "object",
                            "required": ["question_index", "question", "question_type", "is_correct", "result"],
                            "properties": {
                                "question_index": {"bsonType": ["int", "long"]},
                                "question": {"bsonType": "string"},
                                "question_type": {"bsonType": "string"},
                                "user_answer": {},
                                "correct_answer": {},
                                "is_correct": {"bsonType": "bool"},
                                "result": {"bsonType": "string"},
                                "accuracy_percentage": {"bsonType": ["double", "int", "long", "decimal", "null"]},
                            },
                        },
                    },
                },
            }
        },
    }
