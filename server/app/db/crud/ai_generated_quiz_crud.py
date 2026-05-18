import logging

from server.app.db.services.quiz_dual_write_service import QuizDualWriteService


logger = logging.getLogger(__name__)
dual_write_service = QuizDualWriteService()


async def save_ai_generated_quiz(quiz_data: dict):
    try:
        canonical_quiz = await dual_write_service._mirror_quiz_document(
            title=quiz_data.get("profession") or "General Knowledge",
            description=quiz_data.get("custom_instruction"),
            quiz_type=quiz_data.get("question_type", "multichoice"),
            owner_user_id=quiz_data.get("user_id"),
            source="ai",
            questions=quiz_data["questions"],
        )
        return {
            "message": "Quiz saved successfully",
            "quiz_id": str(canonical_quiz.id),
            "duplicate": False,
        }
    except Exception as exc:
        logger.error("Error saving quiz: %s", exc)
        raise
