import logging
from datetime import datetime
from typing import Any, Dict

from ....app.db.services.quiz_dual_write_service import QuizDualWriteService


logger = logging.getLogger(__name__)
dual_write_service = QuizDualWriteService()
quiz_history_collection = None


async def update_quiz_history(quiz_data: Dict[str, Any]):
    quiz_data["created_at"] = datetime.utcnow()
    history_reference = await dual_write_service.create_quiz_history_v2(quiz_data)
    logger.info("Quiz history saved for user %s: %s", quiz_data.get("user_id"), str(history_reference.id))
    return history_reference
