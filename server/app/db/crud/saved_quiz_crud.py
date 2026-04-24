from datetime import datetime
import logging
import re

from bson import ObjectId
from pydantic import ValidationError
from pymongo import ReturnDocument

from ....app.db.core.connection import get_saved_quizzes_collection
from ....app.db.models.saved_quiz_model import QuizQuestionModel, SavedQuizModel
from ....app.db.services.quiz_dual_write_service import QuizDualWriteService


collection = get_saved_quizzes_collection()
dual_write_service = QuizDualWriteService()
logger = logging.getLogger(__name__)


def model_to_dict(model):
    dump_fn = getattr(model, "model_dump", None)
    if callable(dump_fn):
        return model.model_dump(by_alias=True, exclude_none=True)
    return model.dict(by_alias=True, exclude_none=True)


async def save_quiz(
    user_id: str,
    title: str,
    question_type: str,
    questions: list,
    quiz_id: str | None = None,
):
    try:
        parsed_questions = []
        for question in questions:
            if isinstance(question, dict):
                question_payload = {
                    **question,
                    "question_type": question.get("question_type") or question_type,
                }
                parsed_questions.append(QuizQuestionModel(**question_payload))
            else:
                if not getattr(question, "question_type", None):
                    question.question_type = question_type
                parsed_questions.append(question)
        quiz = SavedQuizModel(
            user_id=user_id,
            quiz_id=quiz_id or str(ObjectId()),
            title=title,
            question_type=question_type,
            is_deleted=False,
            questions=parsed_questions,
            created_at=datetime.utcnow(),
        )

        doc = model_to_dict(quiz)
        if "_id" in doc and doc["_id"] is None:
            doc.pop("_id")

        result = await collection.insert_one(doc)
        try:
            legacy_saved_quiz = await collection.find_one({"_id": result.inserted_id})
            mirrored = await dual_write_service.mirror_saved_quiz(legacy_saved_quiz)
            if mirrored:
                await collection.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"canonical_quiz_id": str(mirrored.id)}},
                )
        except Exception as exc:
            logger.exception(
                "Saved quiz dual-write failed after legacy insert for saved_quiz_id=%s: %s",
                result.inserted_id,
                exc,
            )

        return str(result.inserted_id)
    except ValidationError as exc:
        raise Exception(f"Validation error: {exc}") from exc


def _normalize_saved_quiz_document(quiz: dict) -> dict:
    quiz["_id"] = str(quiz["_id"])
    return quiz


async def _build_duplicate_title(user_id: str, original_title: str) -> str:
    base_title = f"Copy of {original_title.strip()}"
    title_pattern = re.compile(
        rf"^{re.escape(base_title)}(?: (\d+))?$",
        re.IGNORECASE,
    )
    existing_titles = await collection.distinct("title", {"user_id": user_id})

    highest_suffix = 0
    base_exists = False
    for existing_title in existing_titles:
        if not isinstance(existing_title, str):
            continue
        match = title_pattern.match(existing_title.strip())
        if not match:
            continue
        if match.group(1):
            highest_suffix = max(highest_suffix, int(match.group(1)))
        else:
            base_exists = True

    if not base_exists:
        return base_title

    return f"{base_title} {highest_suffix + 1}"


async def get_saved_quizzes(user_id: str):
    quizzes = await collection.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    for quiz in quizzes:
        _normalize_saved_quiz_document(quiz)
    return quizzes


async def delete_saved_quiz(quiz_id: str, user_id: str):
    legacy_quiz = await collection.find_one({"_id": ObjectId(quiz_id), "user_id": user_id})
    result = await collection.delete_one({"_id": ObjectId(quiz_id), "user_id": user_id})
    if result.deleted_count and legacy_quiz and legacy_quiz.get("canonical_quiz_id"):
        await dual_write_service.reference_repository.delete_saved_quiz(
            user_id,
            legacy_quiz["canonical_quiz_id"],
        )
    return result.deleted_count > 0


async def get_saved_quiz_by_id(quiz_id: str, user_id: str):
    quiz = await collection.find_one({"_id": ObjectId(quiz_id), "user_id": user_id})
    if quiz:
        _normalize_saved_quiz_document(quiz)
    return quiz


async def duplicate_saved_quiz(quiz_id: str, user_id: str):
    original_quiz = await collection.find_one(
        {"_id": ObjectId(quiz_id), "user_id": user_id}
    )
    if not original_quiz:
        return None

    duplicated_title = await _build_duplicate_title(user_id, original_quiz["title"])
    duplicated_quiz_id = await save_quiz(
        user_id=user_id,
        title=duplicated_title,
        question_type=original_quiz["question_type"],
        questions=original_quiz["questions"],
    )
    duplicated_quiz = await collection.find_one(
        {"_id": ObjectId(duplicated_quiz_id), "user_id": user_id}
    )
    if duplicated_quiz:
        _normalize_saved_quiz_document(duplicated_quiz)
    return duplicated_quiz


async def rename_saved_quiz(quiz_id: str, user_id: str, new_title: str):
    sanitized_title = new_title.strip()
    if not sanitized_title:
        raise ValueError("Quiz title cannot be empty")

    updated_quiz = await collection.find_one_and_update(
        {"_id": ObjectId(quiz_id), "user_id": user_id},
        {"$set": {"title": sanitized_title}},
        return_document=ReturnDocument.AFTER,
    )
    if updated_quiz:
        _normalize_saved_quiz_document(updated_quiz)
    return updated_quiz
