import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.db.core.config import settings
from server.app.db.core.connection import (
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.db.v2.models.quiz_models import QuizDocumentV2
from server.app.db.v2.repositories.quiz_repository import QuizV2Repository
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository


logger = logging.getLogger(__name__)


def build_default_description(topic: str) -> str:
    return f"A quiz to test your knowledge on {topic}"


class SharedQuizReadService:
    def __init__(
        self,
        *,
        quizzes_collection: Optional[AsyncIOMotorCollection] = None,
        ai_generated_quizzes_collection: Optional[AsyncIOMotorCollection] = None,
        saved_quizzes_collection: Optional[AsyncIOMotorCollection] = None,
        quiz_repository: Optional[QuizV2Repository] = None,
        reference_repository: Optional[ReferenceV2Repository] = None,
    ):
        self.quiz_repository = (
            quiz_repository if quiz_repository is not None else QuizV2Repository(get_quizzes_v2_collection())
        )
        self.reference_repository = (
            reference_repository
            if reference_repository is not None
            else ReferenceV2Repository(
                get_folders_v2_collection(),
                get_folder_items_v2_collection(),
                get_saved_quizzes_v2_collection(),
                get_quiz_history_v2_collection(),
            )
        )

    def _log(self, event: str, **fields):
        if not settings.QUIZ_V2_STRUCTURED_LOGGING:
            return
        logger.info("%s | %s", event, fields)

    @staticmethod
    def _normalize_v2_quiz(quiz_doc: QuizDocumentV2) -> dict[str, Any]:
        topic = quiz_doc.title or "General Knowledge"
        return {
            "id": str(quiz_doc.id),
            "title": quiz_doc.title,
            "description": quiz_doc.description or build_default_description(topic),
            "quiz_type": quiz_doc.quiz_type.value,
            "questions": [
                {
                    "question": question.question,
                    "options": question.options,
                    "correct_answer": question.correct_answer,
                }
                for question in quiz_doc.questions
            ],
        }

    async def resolve_shared_quiz(self, quiz_id: str) -> Optional[dict[str, Any]]:
        quiz_doc = await self.quiz_repository.find_by_id(quiz_id)
        if not quiz_doc:
            quiz_doc = await self.quiz_repository.find_by_legacy_mapping("quizzes", quiz_id)
        if not quiz_doc:
            quiz_doc = await self.quiz_repository.find_by_legacy_mapping("ai_generated_quizzes", quiz_id)
        if not quiz_doc:
            saved_reference = await self.reference_repository.get_saved_quiz_by_legacy_id(quiz_id)
            if saved_reference:
                quiz_doc = await self.quiz_repository.find_by_id(saved_reference.quiz_id)

        payload = self._normalize_v2_quiz(quiz_doc) if quiz_doc else None
        self._log("quiz_read_v2_served", operation="shared_quiz_detail", read_mode="v2_only", quiz_id=quiz_id)
        return payload
