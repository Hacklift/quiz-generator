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
    """
    collection = get_ai_generated_quizzes_collection()

    try:
        new_quiz = AIGeneratedQuiz(**quiz_data)

        questions_serialized = jsonable_encoder(new_quiz.questions)

        existing_quiz = await collection.find_one({"questions": questions_serialized})
        if existing_quiz:
            logger.info("Duplicate quiz detected based on identical questions. Skipping save.")
            return {
                "message": "Quiz with these exact questions already exists",
                "id": existing_quiz["id"],
            }

        quiz_to_save = jsonable_encoder(new_quiz.dict())

        await collection.insert_one(quiz_to_save)

        logger.info(f"Quiz saved successfully with id: {new_quiz.id}")
        return {"message": "Quiz saved successfully", "id": new_quiz.id}
    
    
    except DuplicateKeyError:
        logger.warning("Duplicate quiz detected by MongoDB index. Skipping save.")
        return {
            "message": "Duplicate quiz detected",
            "duplicate": True
            }


    except Exception as e:
        logger.error(f"Error saving quiz: {str(e)}")
        raise
