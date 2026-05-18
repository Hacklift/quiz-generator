import logging
from datetime import datetime
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
from server.app.db.v2.models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)
from server.app.db.v2.repositories.quiz_repository import QuizV2Repository
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository


logger = logging.getLogger(__name__)


class QuizUserLibraryReadService:
    def __init__(
        self,
        *,
        saved_quizzes_collection: Optional[AsyncIOMotorCollection] = None,
        quiz_history_collection: Optional[AsyncIOMotorCollection] = None,
        folders_collection: Optional[AsyncIOMotorCollection] = None,
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
    def _isoformat(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def _sort_folder_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(item: dict[str, Any]):
            position = item.get("_position")
            if position is None:
                position = 10**9
            return (position, item.get("added_on") or item.get("created_at") or "", item.get("id") or "")

        return sorted(items, key=sort_key)

    async def _get_quizzes_by_ids(self, quiz_ids: list[str]) -> dict[str, QuizDocumentV2]:
        quizzes = await self.quiz_repository.find_many_by_ids(quiz_ids)
        return {str(quiz.id): quiz for quiz in quizzes}

    @staticmethod
    def _serialize_saved_questions(quiz: QuizDocumentV2) -> list[dict[str, Any]]:
        return [
            {
                "question": question.question,
                "options": question.options,
                "question_type": quiz.quiz_type.value,
                "correct_answer": question.correct_answer,
            }
            for question in quiz.questions
        ]

    @staticmethod
    def _serialize_history_questions(quiz: QuizDocumentV2) -> list[dict[str, Any]]:
        return [
            {
                "question": question.question,
                "options": question.options,
                "answer": question.correct_answer,
                "question_type": quiz.quiz_type.value,
            }
            for question in quiz.questions
        ]

    async def get_quiz_history_for_user(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        references = await self.reference_repository.list_quiz_history_for_user(user_id)
        references = sorted(references, key=lambda reference: reference.created_at, reverse=True)[:limit]
        quizzes_by_id = await self._get_quizzes_by_ids([reference.quiz_id for reference in references])
        payload: list[dict[str, Any]] = []
        for reference in references:
            quiz = quizzes_by_id.get(reference.quiz_id)
            if quiz is None:
                continue
            payload.append(
                {
                    "id": str(reference.id),
                    "user_id": reference.user_id,
                    "quiz_id": str(quiz.id),
                    "quiz_name": quiz.title,
                    "question_type": quiz.quiz_type.value,
                    "profession": reference.metadata.get("topic") or quiz.title,
                    "difficulty_level": reference.metadata.get("difficulty_level"),
                    "audience_type": reference.metadata.get("audience_type"),
                    "questions": self._serialize_history_questions(quiz),
                    "created_at": self._isoformat(reference.created_at),
                }
            )
        self._log("quiz_read_v2_served", operation="quiz_history_list", user_id=user_id, read_mode="v2_only")
        return payload

    def _build_saved_payload(self, reference: SavedQuizDocumentV2, quiz: QuizDocumentV2) -> dict[str, Any]:
        return {
            "id": str(reference.id),
            "user_id": reference.user_id,
            "quiz_id": str(quiz.id),
            "title": reference.display_title or quiz.title,
            "question_type": quiz.quiz_type.value,
            "is_deleted": False,
            "questions": self._serialize_saved_questions(quiz),
            "created_at": self._isoformat(reference.saved_at),
        }

    async def get_saved_quizzes_for_user(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        references = await self.reference_repository.list_saved_quizzes_for_user(user_id)
        references = sorted(references, key=lambda reference: reference.saved_at, reverse=True)[:limit]
        quizzes_by_id = await self._get_quizzes_by_ids([reference.quiz_id for reference in references])
        payload: list[dict[str, Any]] = []
        for reference in references:
            quiz = quizzes_by_id.get(reference.quiz_id)
            if quiz is None:
                continue
            payload.append(self._build_saved_payload(reference, quiz))
        self._log("quiz_read_v2_served", operation="saved_quiz_list", user_id=user_id, read_mode="v2_only")
        return payload

    async def get_saved_quiz_by_id(self, saved_quiz_id: str, user_id: str) -> Optional[dict[str, Any]]:
        reference = await self.reference_repository.get_saved_quiz_by_public_id(saved_quiz_id, user_id=user_id)
        if reference is None:
            return None
        quiz = await self.quiz_repository.find_by_id(reference.quiz_id)
        if quiz is None:
            return None
        payload = self._build_saved_payload(reference, quiz)
        self._log("quiz_read_v2_served", operation="saved_quiz_detail", user_id=user_id, read_mode="v2_only")
        return payload

    def _build_folder_item_payload(
        self,
        *,
        item: FolderItemDocumentV2,
        quiz: QuizDocumentV2,
    ) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "quiz_id": str(quiz.id),
            "title": item.display_title or quiz.title,
            "question_type": quiz.quiz_type.value,
            "questions": self._serialize_saved_questions(quiz),
            "created_at": self._isoformat(item.created_at),
            "added_on": self._isoformat(item.created_at),
            "_position": item.position,
        }

    async def get_user_folders(self, user_id: str) -> list[dict[str, Any]]:
        folders = await self.reference_repository.list_folders_for_user(user_id)
        folders = sorted(folders, key=lambda folder: (folder.created_at, str(folder.id)))
        folder_payloads: list[dict[str, Any]] = []
        for folder in folders:
            items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
            folder_payloads.append(
                {
                    "id": str(folder.id),
                    "user_id": folder.user_id,
                    "name": folder.name,
                    "created_at": self._isoformat(folder.created_at),
                    "updated_at": self._isoformat(folder.updated_at),
                    "quizzes": [{"id": str(item.id)} for item in items],
                    "quiz_count": len(items),
                }
            )
        self._log("quiz_read_v2_served", operation="folder_list", user_id=user_id, read_mode="v2_only")
        return folder_payloads

    async def get_folder_by_id(self, folder_id: str, user_id: str) -> Optional[dict[str, Any]]:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None:
            return None
        if folder.user_id != user_id:
            raise PermissionError("Unauthorized access to folder")
        items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
        quiz_map = await self._get_quizzes_by_ids([item.quiz_id for item in items])
        payload_items: list[dict[str, Any]] = []
        for item in items:
            quiz = quiz_map.get(item.quiz_id)
            if quiz is None:
                continue
            payload_items.append(self._build_folder_item_payload(item=item, quiz=quiz))
        payload_items = self._sort_folder_items(payload_items)
        for payload_item in payload_items:
            payload_item.pop("_position", None)
        payload = {
            "id": str(folder.id),
            "user_id": folder.user_id,
            "name": folder.name,
            "created_at": self._isoformat(folder.created_at),
            "updated_at": self._isoformat(folder.updated_at),
            "quizzes": payload_items,
        }
        self._log("quiz_read_v2_served", operation="folder_detail", user_id=user_id, read_mode="v2_only")
        return payload
