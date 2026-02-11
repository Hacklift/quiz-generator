from server.app.db.core.connection import get_ai_generated_quizzes_collection
from server.app.db.models.ai_generated_quiz_model import AIGeneratedQuiz
from pymongo.errors import DuplicateKeyError
from fastapi.encoders import jsonable_encoder
import logging

logger = logging.getLogger(__name__)

async def save_ai_generated_quiz(quiz_data: dict):
    """
    Save an AI-generated quiz to the database immediately after generation.
    Prevents saving duplicate quizzes with identical questions.
    Returns MongoDB-assigned _id for later use.
    """
    collection = get_ai_generated_quizzes_collection()

    try:
        # ✅ Convert to Pydantic model
        new_quiz = AIGeneratedQuiz(**quiz_data)

        # ✅ Serialize questions for safe querying
        questions_serialized = jsonable_encoder(new_quiz.questions)

        # ✅ Check for duplicate quiz by questions
        existing_quiz = await collection.find_one({"questions": questions_serialized})
        if existing_quiz:
            logger.info("Duplicate quiz detected based on identical questions. Skipping save.")
            return {
                "message": "Quiz with these exact questions already exists",
                "quiz_id": str(existing_quiz["_id"]),
                "duplicate": True
            }

        # ✅ Prepare full quiz for saving
        quiz_to_save = jsonable_encoder(new_quiz.dict())

        insert_result = await collection.insert_one(quiz_to_save)

        logger.info(f"Quiz saved successfully with MongoDB _id: {insert_result.inserted_id}")
        return {
            "message": "Quiz saved successfully",
            "quiz_id": str(insert_result.inserted_id),
            "duplicate": False
        }

    except DuplicateKeyError:
        logger.warning("Duplicate quiz detected by MongoDB index. Skipping save.")
        return {
            "message": "Duplicate quiz detected",
            "duplicate": True
        }

    except Exception as e:
        logger.error(f"Error saving quiz: {str(e)}")
        raise
