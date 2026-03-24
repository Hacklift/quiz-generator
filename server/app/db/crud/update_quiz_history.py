import logging
from datetime import datetime
from typing import Any, Dict

from ....app.db.core.connection import quiz_history_collection
from ....app.db.services.quiz_dual_write_service import QuizDualWriteService


logger = logging.getLogger(__name__)
dual_write_service = QuizDualWriteService()


async def update_quiz_history(quiz_data: Dict[str, Any]):
    quiz_data["created_at"] = datetime.utcnow()
    result = await quiz_history_collection.insert_one(quiz_data)

    try:
        legacy_history = await quiz_history_collection.find_one({"_id": result.inserted_id})
        mirrored = await dual_write_service.mirror_quiz_history(legacy_history)
        if mirrored:
            await quiz_history_collection.update_one(
                {"_id": result.inserted_id},
                {"$set": {"canonical_quiz_id": str(mirrored.id)}},
            )
    except Exception as exc:
        logger.exception(
            "Quiz history dual-write failed after legacy insert for history_id=%s: %s",
            result.inserted_id,
            exc,
        )

    logger.info("Quiz saved for user %s: %s", quiz_data.get("user_id"), str(result.inserted_id))
    return str(result.inserted_id)


async def get_quiz_history(user_id: str, limit: int = 100):
    cursor = quiz_history_collection.find({"user_id": user_id}).sort("created_at", -1)
    quizzes = await cursor.to_list(length=limit)

    for quiz in quizzes:
        quiz["_id"] = str(quiz["_id"])
        if isinstance(quiz.get("created_at"), datetime):
            quiz["created_at"] = quiz["created_at"].isoformat()
    return quizzes
