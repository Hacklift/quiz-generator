from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ....app.db.models.ai_generated_quiz_model import AIGeneratedQuiz
from ....app.db.models.canonical_quiz_models import (
    CanonicalQuizDocument,
    adapt_ai_quiz_to_canonical,
    adapt_seed_quiz_to_canonical,
)
from ....app.db.models.folder_model import FolderQuizRef, UserFolderRecord
from ....app.db.models.quiz_event_model import QuizEventRecord
from ....app.db.models.saved_quiz_model import SavedQuizRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dump_model(payload: Any) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if hasattr(payload, "dict"):
        return payload.dict()
    if isinstance(payload, dict):
        return dict(payload)
    raise TypeError("Payload must be a dict or Pydantic model")


def _canonical_to_mongo_doc(payload: CanonicalQuizDocument) -> dict[str, Any]:
    doc = _dump_model(payload)
    return jsonable_encoder(doc)


async def _ensure_quiz_exists(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
) -> bool:
    return await quizzes_collection.find_one(
        {"_id": ObjectId(quiz_id), "is_deleted": {"$ne": True}},
        projection={"_id": 1},
    ) is not None


async def create_quiz_document(
    quizzes_collection: AsyncIOMotorCollection,
    payload: Any,
) -> tuple[str, dict[str, Any]]:
    quiz_data = _dump_model(payload)
    quiz_data.setdefault("source", "manual")

    if "quiz_type" in quiz_data and isinstance(quiz_data["quiz_type"], str):
        quiz_data["quiz_type"] = quiz_data["quiz_type"].strip().lower()

    if "questions" in quiz_data and isinstance(quiz_data["questions"], list):
        normalized_questions = []
        for question in quiz_data["questions"]:
            q = _dump_model(question)
            if "answer" not in q and "correct_answer" in q:
                q["answer"] = q["correct_answer"]
            if "question_type" not in q and quiz_data.get("quiz_type"):
                q["question_type"] = quiz_data["quiz_type"]
            normalized_questions.append(q)
        quiz_data["questions"] = normalized_questions

    canonical_quiz = CanonicalQuizDocument(**quiz_data)
    quiz_doc = _canonical_to_mongo_doc(canonical_quiz)
    result = await quizzes_collection.insert_one(quiz_doc)
    return str(result.inserted_id), quiz_doc


async def create_seed_quiz_document(
    quizzes_collection: AsyncIOMotorCollection,
    seed_payload: Any,
) -> tuple[str, dict[str, Any]]:
    canonical_quiz = adapt_seed_quiz_to_canonical(seed_payload)
    return await create_quiz_document(quizzes_collection, canonical_quiz)


async def create_ai_quiz_document(
    quizzes_collection: AsyncIOMotorCollection,
    ai_payload: Any,
) -> tuple[str, dict[str, Any]]:
    canonical_quiz = adapt_ai_quiz_to_canonical(ai_payload)
    return await create_quiz_document(quizzes_collection, canonical_quiz)


async def update_quiz_document(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
    update_payload: Any,
) -> Optional[dict[str, Any]]:
    update_doc = _dump_model(update_payload)
    update_doc.pop("id", None)
    update_doc.pop("_id", None)
    update_doc.pop("source", None)
    update_doc.pop("generation", None)
    update_doc.pop("is_deleted", None)
    update_doc.pop("deleted_at", None)
    update_doc.pop("deleted_by", None)
    update_doc.pop("created_at", None)

    if "questions" in update_doc and isinstance(update_doc["questions"], list):
        normalized_questions = []
        for question in update_doc["questions"]:
            q = _dump_model(question)
            if "answer" not in q and "correct_answer" in q:
                q["answer"] = q["correct_answer"]
            if "question_type" not in q and update_doc.get("quiz_type"):
                q["question_type"] = update_doc["quiz_type"]
            normalized_questions.append(q)
        update_doc["questions"] = normalized_questions

    if "quiz_type" in update_doc and isinstance(update_doc["quiz_type"], str):
        update_doc["quiz_type"] = update_doc["quiz_type"].strip().lower()

    update_doc["updated_at"] = _utcnow()

    return await quizzes_collection.find_one_and_update(
        {"_id": ObjectId(quiz_id), "is_deleted": {"$ne": True}},
        {"$set": jsonable_encoder(update_doc)},
        return_document=ReturnDocument.AFTER,
    )


async def soft_delete_quiz_document(
    quizzes_collection: AsyncIOMotorCollection,
    quiz_id: str,
    *,
    deleted_by: Optional[str] = None,
) -> int:
    result = await quizzes_collection.update_one(
        {"_id": ObjectId(quiz_id), "is_deleted": {"$ne": True}},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": _utcnow(),
                "deleted_by": deleted_by,
                "updated_at": _utcnow(),
            }
        },
    )
    return result.modified_count


async def create_ai_quiz_with_legacy_mirror(
    quizzes_collection: AsyncIOMotorCollection,
    legacy_ai_collection: AsyncIOMotorCollection,
    ai_payload: Any,
) -> dict[str, Any]:
    new_ai_quiz = AIGeneratedQuiz(**_dump_model(ai_payload))
    questions_serialized = jsonable_encoder(new_ai_quiz.questions)

    existing_quiz = await legacy_ai_collection.find_one({"questions": questions_serialized})
    if existing_quiz:
        return {
            "message": "Quiz with these exact questions already exists",
            "id": existing_quiz["id"],
        }

    try:
        await create_ai_quiz_document(quizzes_collection, ai_payload)
        await legacy_ai_collection.insert_one(jsonable_encoder(new_ai_quiz.dict()))
        return {"message": "Quiz saved successfully", "id": new_ai_quiz.id}
    except DuplicateKeyError:
        return {
            "message": "Duplicate quiz detected",
            "duplicate": True,
        }


def parse_quiz_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise


async def create_saved_quiz_record(
    saved_quizzes_collection: AsyncIOMotorCollection,
    quizzes_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    quiz_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any]]:
    if not await _ensure_quiz_exists(quizzes_collection, quiz_id):
        raise ValueError("Referenced quiz does not exist or has been deleted")
    return await _create_saved_quiz_record_in_collection(
        saved_quizzes_collection=saved_quizzes_collection,
        user_id=user_id,
        quiz_id=quiz_id,
        metadata=metadata,
    )


async def soft_delete_saved_quiz_record(
    saved_quizzes_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    quiz_id: str,
) -> int:
    return await _soft_delete_saved_quiz_in_collection(
        saved_quizzes_collection=saved_quizzes_collection,
        user_id=user_id,
        quiz_id=quiz_id,
    )


async def create_user_folder_record(
    folders_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    name: str,
) -> tuple[str, dict[str, Any]]:
    return await _create_user_folder_in_collection(
        folders_collection=folders_collection,
        user_id=user_id,
        name=name,
    )


async def add_quiz_ref_to_folder_record(
    folders_collection: AsyncIOMotorCollection,
    quizzes_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
    quiz_id: str,
) -> Optional[dict[str, Any]]:
    if not await _ensure_quiz_exists(quizzes_collection, quiz_id):
        raise ValueError("Referenced quiz does not exist or has been deleted")
    return await _add_quiz_ref_to_folder_in_collection(
        folders_collection=folders_collection,
        folder_id=folder_id,
        quiz_id=quiz_id,
    )


async def remove_quiz_ref_from_folder_record(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
    quiz_id: str,
) -> Optional[dict[str, Any]]:
    return await _remove_quiz_ref_from_folder_in_collection(
        folders_collection=folders_collection,
        folder_id=folder_id,
        quiz_id=quiz_id,
    )


async def rename_user_folder_record(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
    name: str,
) -> Optional[dict[str, Any]]:
    return await folders_collection.find_one_and_update(
        {"_id": ObjectId(folder_id), "is_deleted": {"$ne": True}},
        {"$set": {"name": name, "updated_at": _utcnow()}},
        return_document=ReturnDocument.AFTER,
    )


async def soft_delete_user_folder_record(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
) -> int:
    return await _soft_delete_user_folder_in_collection(
        folders_collection=folders_collection,
        folder_id=folder_id,
    )


async def record_quiz_event(
    quiz_events_collection: AsyncIOMotorCollection,
    quizzes_collection: AsyncIOMotorCollection,
    *,
    quiz_id: str,
    event_type: str,
    user_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any]]:
    if not await _ensure_quiz_exists(quizzes_collection, quiz_id):
        raise ValueError("Referenced quiz does not exist or has been deleted")

    event = QuizEventRecord(
        quiz_id=quiz_id,
        event_type=event_type,
        user_id=user_id,
        metadata=metadata,
    )
    doc = jsonable_encoder(_dump_model(event))
    result = await quiz_events_collection.insert_one(doc)
    return str(result.inserted_id), doc


async def _create_saved_quiz_record_in_collection(
    saved_quizzes_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    quiz_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any]]:
    existing = await saved_quizzes_collection.find_one(
        {"user_id": user_id, "quiz_id": quiz_id, "is_deleted": {"$ne": True}}
    )
    if existing:
        return str(existing["_id"]), jsonable_encoder(existing)

    record = SavedQuizRecord(user_id=user_id, quiz_id=quiz_id, metadata=metadata)
    doc = jsonable_encoder(_dump_model(record))
    result = await saved_quizzes_collection.insert_one(doc)
    return str(result.inserted_id), doc


async def _soft_delete_saved_quiz_in_collection(
    saved_quizzes_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    quiz_id: str,
) -> int:
    result = await saved_quizzes_collection.update_one(
        {"user_id": user_id, "quiz_id": quiz_id, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "deleted_at": _utcnow(), "updated_at": _utcnow()}},
    )
    return result.modified_count


async def _create_user_folder_in_collection(
    folders_collection: AsyncIOMotorCollection,
    *,
    user_id: str,
    name: str,
) -> tuple[str, dict[str, Any]]:
    folder = UserFolderRecord(user_id=user_id, name=name)
    doc = jsonable_encoder(_dump_model(folder))
    result = await folders_collection.insert_one(doc)
    return str(result.inserted_id), doc


async def _add_quiz_ref_to_folder_in_collection(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
    quiz_id: str,
) -> Optional[dict[str, Any]]:
    folder_object_id = ObjectId(folder_id)
    existing = await folders_collection.find_one(
        {"_id": folder_object_id, "is_deleted": {"$ne": True}, "quiz_refs.quiz_id": quiz_id},
        projection={"_id": 1},
    )
    if existing:
        return await folders_collection.find_one({"_id": folder_object_id, "is_deleted": {"$ne": True}})

    quiz_ref = FolderQuizRef(quiz_id=quiz_id)
    await folders_collection.update_one(
        {"_id": folder_object_id, "is_deleted": {"$ne": True}},
        {
            "$push": {"quiz_refs": jsonable_encoder(_dump_model(quiz_ref))},
            "$set": {"updated_at": _utcnow()},
        },
    )
    return await folders_collection.find_one({"_id": folder_object_id, "is_deleted": {"$ne": True}})


async def _remove_quiz_ref_from_folder_in_collection(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
    quiz_id: str,
) -> Optional[dict[str, Any]]:
    folder_object_id = ObjectId(folder_id)
    await folders_collection.update_one(
        {"_id": folder_object_id, "is_deleted": {"$ne": True}},
        {
            "$pull": {"quiz_refs": {"quiz_id": quiz_id}},
            "$set": {"updated_at": _utcnow()},
        },
    )
    return await folders_collection.find_one({"_id": folder_object_id, "is_deleted": {"$ne": True}})


async def _soft_delete_user_folder_in_collection(
    folders_collection: AsyncIOMotorCollection,
    *,
    folder_id: str,
) -> int:
    result = await folders_collection.update_one(
        {"_id": ObjectId(folder_id), "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "deleted_at": _utcnow(), "updated_at": _utcnow()}},
    )
    return result.modified_count


async def dual_write_saved_quiz_record(
    *,
    legacy_saved_quizzes_collection: AsyncIOMotorCollection,
    saved_quizzes_v2_collection: AsyncIOMotorCollection,
    quizzes_collection: AsyncIOMotorCollection,
    user_id: str,
    quiz_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if not await _ensure_quiz_exists(quizzes_collection, quiz_id):
        raise ValueError("Referenced quiz does not exist or has been deleted")

    legacy_id, legacy_doc = await _create_saved_quiz_record_in_collection(
        saved_quizzes_collection=legacy_saved_quizzes_collection,
        user_id=user_id,
        quiz_id=quiz_id,
        metadata=metadata,
    )
    v2_id, _ = await _create_saved_quiz_record_in_collection(
        saved_quizzes_collection=saved_quizzes_v2_collection,
        user_id=user_id,
        quiz_id=quiz_id,
        metadata=metadata,
    )
    return {"legacy_id": legacy_id, "v2_id": v2_id, "record": legacy_doc}


async def dual_write_saved_quiz_delete(
    *,
    legacy_saved_quizzes_collection: AsyncIOMotorCollection,
    saved_quizzes_v2_collection: AsyncIOMotorCollection,
    user_id: str,
    quiz_id: str,
) -> dict[str, int]:
    legacy_count = await _soft_delete_saved_quiz_in_collection(
        saved_quizzes_collection=legacy_saved_quizzes_collection,
        user_id=user_id,
        quiz_id=quiz_id,
    )
    v2_count = await _soft_delete_saved_quiz_in_collection(
        saved_quizzes_collection=saved_quizzes_v2_collection,
        user_id=user_id,
        quiz_id=quiz_id,
    )
    return {"legacy_count": legacy_count, "v2_count": v2_count}


async def dual_write_user_folder_create(
    *,
    legacy_folders_collection: AsyncIOMotorCollection,
    folders_v2_collection: AsyncIOMotorCollection,
    user_id: str,
    name: str,
) -> dict[str, Any]:
    legacy_id, legacy_doc = await _create_user_folder_in_collection(
        folders_collection=legacy_folders_collection,
        user_id=user_id,
        name=name,
    )
    v2_id, _ = await _create_user_folder_in_collection(
        folders_collection=folders_v2_collection,
        user_id=user_id,
        name=name,
    )
    return {"legacy_id": legacy_id, "v2_id": v2_id, "record": legacy_doc}


async def dual_write_user_folder_add_quiz_ref(
    *,
    legacy_folders_collection: AsyncIOMotorCollection,
    folders_v2_collection: AsyncIOMotorCollection,
    quizzes_collection: AsyncIOMotorCollection,
    folder_id: str,
    v2_folder_id: str,
    quiz_id: str,
) -> dict[str, Any]:
    if not await _ensure_quiz_exists(quizzes_collection, quiz_id):
        raise ValueError("Referenced quiz does not exist or has been deleted")

    legacy_folder = await _add_quiz_ref_to_folder_in_collection(
        folders_collection=legacy_folders_collection,
        folder_id=folder_id,
        quiz_id=quiz_id,
    )
    v2_folder = await _add_quiz_ref_to_folder_in_collection(
        folders_collection=folders_v2_collection,
        folder_id=v2_folder_id,
        quiz_id=quiz_id,
    )
    return {"legacy_folder": legacy_folder, "v2_folder": v2_folder}


async def dual_write_user_folder_remove_quiz_ref(
    *,
    legacy_folders_collection: AsyncIOMotorCollection,
    folders_v2_collection: AsyncIOMotorCollection,
    folder_id: str,
    v2_folder_id: str,
    quiz_id: str,
) -> dict[str, Any]:
    legacy_folder = await _remove_quiz_ref_from_folder_in_collection(
        folders_collection=legacy_folders_collection,
        folder_id=folder_id,
        quiz_id=quiz_id,
    )
    v2_folder = await _remove_quiz_ref_from_folder_in_collection(
        folders_collection=folders_v2_collection,
        folder_id=v2_folder_id,
        quiz_id=quiz_id,
    )
    return {"legacy_folder": legacy_folder, "v2_folder": v2_folder}


async def dual_write_user_folder_rename(
    *,
    legacy_folders_collection: AsyncIOMotorCollection,
    folders_v2_collection: AsyncIOMotorCollection,
    folder_id: str,
    v2_folder_id: str,
    name: str,
) -> dict[str, Any]:
    legacy_folder = await rename_user_folder_record(
        folders_collection=legacy_folders_collection,
        folder_id=folder_id,
        name=name,
    )
    v2_folder = await rename_user_folder_record(
        folders_collection=folders_v2_collection,
        folder_id=v2_folder_id,
        name=name,
    )
    return {"legacy_folder": legacy_folder, "v2_folder": v2_folder}


async def dual_write_user_folder_delete(
    *,
    legacy_folders_collection: AsyncIOMotorCollection,
    folders_v2_collection: AsyncIOMotorCollection,
    folder_id: str,
    v2_folder_id: str,
) -> dict[str, int]:
    legacy_count = await _soft_delete_user_folder_in_collection(
        folders_collection=legacy_folders_collection,
        folder_id=folder_id,
    )
    v2_count = await _soft_delete_user_folder_in_collection(
        folders_collection=folders_v2_collection,
        folder_id=v2_folder_id,
    )
    return {"legacy_count": legacy_count, "v2_count": v2_count}
