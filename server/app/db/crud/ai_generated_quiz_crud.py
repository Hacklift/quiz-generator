import logging

from fastapi.encoders import jsonable_encoder
from pymongo.errors import DuplicateKeyError

from server.app.db.core.connection import get_ai_generated_quizzes_collection
from server.app.db.models.ai_generated_quiz_model import AIGeneratedQuiz
from server.app.db.services.quiz_dual_write_service import QuizDualWriteService


logger = logging.getLogger(__name__)
dual_write_service = QuizDualWriteService()


async def save_ai_generated_quiz(quiz_data: dict):
    """
    Save an AI-generated quiz to the legacy collection, then mirror it into V2
    when dual-write is enabled.
    """

    collection = get_ai_generated_quizzes_collection()

    try:
        new_quiz = AIGeneratedQuiz(**quiz_data)
        questions_serialized = jsonable_encoder(new_quiz.questions)

        existing_quiz = await collection.find_one({"questions": questions_serialized})
        if existing_quiz:
            await dual_write_service.mirror_ai_generated_quiz(str(existing_quiz["_id"]), existing_quiz)
            logger.info("Duplicate quiz detected based on identical questions. Skipping save.")
            return {
                "message": "Quiz with these exact questions already exists",
                "quiz_id": str(existing_quiz["_id"]),
                "duplicate": True,
            }

        quiz_to_save = jsonable_encoder(new_quiz.dict())
        insert_result = await collection.insert_one(quiz_to_save)

        try:
            mirrored = await dual_write_service.mirror_ai_generated_quiz(
                str(insert_result.inserted_id),
                {**quiz_to_save, "_id": insert_result.inserted_id},
            )
            if mirrored:
                await collection.update_one(
                    {"_id": insert_result.inserted_id},
                    {"$set": {"canonical_quiz_id": str(mirrored.id)}},
                )
        except Exception as exc:
            logger.exception(
                "AI quiz dual-write failed after legacy insert for ai_quiz_id=%s: %s",
                insert_result.inserted_id,
                exc,
            )

        logger.info("Quiz saved successfully with MongoDB _id: %s", insert_result.inserted_id)
        return {
            "message": "Quiz saved successfully",
            "quiz_id": str(insert_result.inserted_id),
            "duplicate": False,
        }
    except DuplicateKeyError:
        logger.warning("Duplicate quiz detected by MongoDB index. Skipping save.")
        return {
            "message": "Duplicate quiz detected",
            "duplicate": True,
        }
    except Exception as exc:
        logger.error("Error saving quiz: %s", exc)
        raise
