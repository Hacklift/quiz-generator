from server.app.db.core.connection import get_ai_generated_quizzes_collection
from server.app.db.models.ai_generated_quiz_model import AIGeneratedQuiz
from pymongo.errors import DuplicateKeyError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def save_ai_generated_quiz(quiz_data: dict):
    """
    Save an AI-generated quiz to the database immediately after generation.
    Ensures uniqueness using the quiz's UUID and logs errors properly.
    """
    collection = get_ai_generated_quizzes_collection()

    try:
        # ✅ Convert to Pydantic model
        new_quiz = AIGeneratedQuiz(**quiz_data)

        # ✅ Check for duplicate by UUID
        existing_quiz = await collection.find_one({"id": new_quiz.id})
        if existing_quiz:
            logger.info(f"Duplicate quiz detected. Skipping save. Quiz ID: {new_quiz.id}")
            return {"message": "Quiz already exists", "id": existing_quiz["id"]}

        # ✅ Insert into MongoDB
        await collection.insert_one(new_quiz.dict())

        logger.info(f"Quiz saved successfully with id: {new_quiz.id}")
        return {"message": "Quiz saved successfully", "id": new_quiz.id}

    except DuplicateKeyError:
        logger.error("Duplicate key error while saving quiz.")
        return {"message": "Duplicate key error"}

    except Exception as e:
        logger.error(f"Error saving quiz: {str(e)}")
        raise
