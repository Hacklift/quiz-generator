from server.app.db.core.connection import (
    get_ai_generated_quizzes_collection,
    get_quizzes_collection,
)
from .quiz_write_service import create_ai_quiz_with_legacy_mirror
import logging

logger = logging.getLogger(__name__)

async def save_ai_generated_quiz(quiz_data: dict):
    """
    Save an AI-generated quiz to the database immediately after generation.
    Prevents saving duplicate quizzes with identical questions.
    """
    collection = get_ai_generated_quizzes_collection()
    canonical_quizzes_collection = get_quizzes_collection()

    try:
        result = await create_ai_quiz_with_legacy_mirror(
            canonical_quizzes_collection,
            collection,
            quiz_data,
        )
        logger.info("AI quiz write completed through centralized write service.")
        return result
    except Exception as e:
        logger.error(f"Error saving quiz: {str(e)}")
        raise
