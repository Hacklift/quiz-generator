from datetime import datetime
from typing import Any

from rapidfuzz import fuzz

from server.app.db.core.connection import (
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.quiz.repositories.v2.models.quiz_models import QuizDocumentV2
from server.app.quiz.repositories.v2.models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)
from server.app.quiz.repositories.v2.repositories.quiz_repository import QuizV2Repository
from server.app.quiz.repositories.v2.repositories.reference_repository import ReferenceV2Repository
from server.app.quiz.schemas.quiz_management_schemas import (
    QuizHistoryDetailResponse,
    QuizHistoryQuestionResponse,
    SavedQuizResponse,
)
from server.app.quiz.services.canonical_quiz_service import CanonicalQuizWriteService


class QuizUserLibraryService:
    def __init__(
        self,
        *,
        canonical_service: CanonicalQuizWriteService | None = None,
        quiz_repository: QuizV2Repository | None = None,
        reference_repository: ReferenceV2Repository | None = None,
    ):
        self.quiz_repository = quiz_repository or QuizV2Repository(get_quizzes_v2_collection())
        self.canonical_service = canonical_service or CanonicalQuizWriteService(self.quiz_repository)
        self.reference_repository = reference_repository or ReferenceV2Repository(
            get_folders_v2_collection(),
            get_folder_items_v2_collection(),
            get_saved_quizzes_v2_collection(),
            get_quiz_history_v2_collection(),
        )

    @staticmethod
    def _isoformat(value: Any) -> Any:
        return value.isoformat() if isinstance(value, datetime) else value

    @staticmethod
    def _quiz_type(quiz: QuizDocumentV2) -> str:
        return quiz.quiz_type.value if hasattr(quiz.quiz_type, "value") else str(quiz.quiz_type)

    @staticmethod
    def _saved_questions(quiz: QuizDocumentV2) -> list[dict[str, Any]]:
        return [
            {
                "question": question.question,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "question_type": quiz.quiz_type.value if hasattr(quiz.quiz_type, "value") else quiz.quiz_type,
            }
            for question in quiz.questions
        ]

    @staticmethod
    def _history_questions(quiz: QuizDocumentV2) -> list[dict[str, Any]]:
        return [
            {
                "question": question.question,
                "options": question.options,
                "answer": question.correct_answer,
            }
            for question in quiz.questions
        ]

    async def _get_quizzes_by_ids(self, quiz_ids: list[str]) -> dict[str, QuizDocumentV2]:
        quizzes = await self.quiz_repository.find_many_by_ids(quiz_ids)
        return {str(quiz.id): quiz for quiz in quizzes}

    async def _get_saved_quizzes_by_ids(
        self,
        saved_quiz_ids: list[str],
        *,
        user_id: str | None = None,
    ) -> dict[str, SavedQuizDocumentV2]:
        references = await self.reference_repository.list_saved_quizzes_by_ids(
            saved_quiz_ids,
            user_id=user_id,
        )
        return {str(reference.id): reference for reference in references}

    async def _resolve_or_create_quiz(
        self,
        *,
        quiz_id: str | None,
        title: str,
        question_type: str,
        questions: list[Any],
        description: str | None = None,
        owner_user_id: str | None = None,
        source: str = "manual",
    ) -> QuizDocumentV2:
        if quiz_id:
            quiz = await self.quiz_repository.find_by_id(quiz_id)
            if quiz:
                return quiz

        quiz_document = self.canonical_service.build_quiz_document(
            title=title,
            description=description,
            quiz_type=question_type,
            owner_user_id=owner_user_id,
            source=source,
            questions=questions,
        )
        return await self.canonical_service.find_or_create_quiz_v2_by_fingerprint(quiz_document)

    def _build_saved_payload(
        self,
        reference: SavedQuizDocumentV2,
        quiz: QuizDocumentV2,
    ) -> dict[str, Any]:
        return {
            "_id": str(reference.id),
            "id": str(reference.id),
            "user_id": reference.user_id,
            "quiz_id": str(quiz.id),
            "title": reference.display_title or quiz.title,
            "question_type": self._quiz_type(quiz),
            "is_deleted": False,
            "questions": self._saved_questions(quiz),
            "created_at": self._isoformat(reference.saved_at),
        }

    async def create_saved_quiz(
        self,
        *,
        user_id: str,
        title: str,
        question_type: str,
        questions: list[Any],
        quiz_id: str | None = None,
    ) -> SavedQuizDocumentV2:
        quiz = await self._resolve_or_create_quiz(
            quiz_id=quiz_id,
            title=title,
            question_type=question_type,
            questions=questions,
            source="manual",
        )
        return await self.reference_repository.upsert_saved_quiz(
            SavedQuizDocumentV2(
                user_id=user_id,
                quiz_id=str(quiz.id),
                display_title=title or quiz.title,
                saved_at=datetime.utcnow(),
            ),
            revive_deleted=True,
        )

    async def list_saved_quizzes(self, *, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        references = await self.reference_repository.list_saved_quizzes_for_user(user_id, limit=limit)
        references = sorted(references, key=lambda reference: reference.saved_at, reverse=True)
        quizzes_by_id = await self._get_quizzes_by_ids([reference.quiz_id for reference in references])
        return [
            self._build_saved_payload(reference, quizzes_by_id[reference.quiz_id])
            for reference in references
            if reference.quiz_id in quizzes_by_id
        ]

    async def get_saved_quiz(self, *, user_id: str, saved_quiz_id: str) -> dict[str, Any] | None:
        reference = await self.reference_repository.get_saved_quiz_for_user(user_id, saved_quiz_id)
        if reference is None:
            return None
        quiz = await self.quiz_repository.find_by_id(reference.quiz_id)
        if quiz is None:
            return None
        return self._build_saved_payload(reference, quiz)

    async def get_saved_quiz_by_id(self, saved_quiz_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.get_saved_quiz(user_id=user_id, saved_quiz_id=saved_quiz_id)

    async def find_saved_quiz_by_title(self, *, user_id: str, title: str, limit: int = 10) -> dict[str, Any]:
        normalized_title = title.strip().casefold()
        saved_quizzes = await self.list_saved_quizzes(user_id=user_id, limit=500)
        matches: list[dict[str, Any]] = []
        for saved_quiz in saved_quizzes:
            saved_title = str(saved_quiz.get("title") or "")
            normalized_saved_title = saved_title.casefold()
            similarity = max(
                fuzz.partial_ratio(normalized_title, normalized_saved_title),
                fuzz.token_set_ratio(normalized_title, normalized_saved_title),
            )
            if normalized_title in normalized_saved_title or similarity >= 85:
                matches.append({**saved_quiz, "match_score": similarity})
        matches = sorted(matches, key=lambda item: item.get("match_score", 0), reverse=True)
        best_match = matches[0] if matches else None
        return {
            "query": title,
            "found": bool(matches),
            "saved_quiz_id": best_match.get("id") if best_match else None,
            "quiz_id": best_match.get("quiz_id") if best_match else None,
            "title": best_match.get("title") if best_match else None,
            "question_type": best_match.get("question_type") if best_match else None,
            "matches": matches[:limit],
        }

    async def delete_saved_quiz(self, *, user_id: str, saved_quiz_id: str) -> bool:
        return await self.reference_repository.delete_saved_quiz_for_user(user_id, saved_quiz_id)

    async def rename_saved_quiz(
        self,
        *,
        user_id: str,
        saved_quiz_id: str,
        title: str,
    ) -> SavedQuizResponse | None:
        reference = await self.reference_repository.update_saved_quiz_display_title(
            user_id,
            saved_quiz_id,
            title,
        )
        if reference is None:
            return None
        quiz = await self.quiz_repository.find_by_id(reference.quiz_id)
        return SavedQuizResponse(
            id=str(reference.id),
            quiz_id=reference.quiz_id,
            title=title,
            created_at=reference.saved_at,
            question_type=self._quiz_type(quiz) if quiz else None,
        )

    async def create_quiz_history(self, quiz_data: dict[str, Any]) -> QuizHistoryDocumentV2:
        quiz = await self._resolve_or_create_quiz(
            quiz_id=quiz_data.get("canonical_quiz_id") or quiz_data.get("quiz_id"),
            title=quiz_data.get("quiz_name") or quiz_data.get("profession") or "Quiz History",
            description=quiz_data.get("custom_instruction"),
            question_type=quiz_data["question_type"],
            owner_user_id=quiz_data.get("user_id"),
            source="ai",
            questions=quiz_data["questions"],
        )
        return await self.reference_repository.insert_quiz_history(
            QuizHistoryDocumentV2(
                user_id=quiz_data["user_id"],
                quiz_id=str(quiz.id),
                action="generated",
                metadata={
                    "quiz_name": quiz_data.get("quiz_name") or quiz.title,
                    "topic": quiz_data.get("profession") or quiz.title,
                    "difficulty_level": quiz_data.get("difficulty_level"),
                    "audience_type": quiz_data.get("audience_type"),
                    "custom_instruction": quiz_data.get("custom_instruction"),
                },
                created_at=quiz_data.get("created_at", datetime.utcnow()),
            )
        )

    async def list_quiz_history_items(self, *, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        references = await self.reference_repository.list_quiz_history_for_user(user_id, limit=limit)
        references = sorted(references, key=lambda reference: reference.created_at, reverse=True)
        quizzes_by_id = await self._get_quizzes_by_ids([reference.quiz_id for reference in references])
        items: list[dict[str, Any]] = []
        for reference in references:
            quiz = quizzes_by_id.get(reference.quiz_id)
            if quiz is None:
                continue
            metadata = reference.metadata or {}
            items.append(
                {
                    "_id": str(reference.id),
                    "id": str(reference.id),
                    "created_at": self._isoformat(reference.created_at),
                    "quiz_id": str(quiz.id),
                    "quiz_name": metadata.get("quiz_name") or quiz.title,
                    "question_type": self._quiz_type(quiz),
                    "difficulty_level": metadata.get("difficulty_level"),
                    "profession": metadata.get("topic") or quiz.title,
                    "audience_type": metadata.get("audience_type"),
                    "custom_instruction": metadata.get("custom_instruction"),
                    "questions": self._history_questions(quiz),
                }
            )
        return items

    async def get_quiz_history_detail(
        self,
        *,
        user_id: str,
        history_id: str,
    ) -> QuizHistoryDetailResponse | None:
        reference = await self.reference_repository.get_quiz_history_for_user(user_id, history_id)
        if reference is None:
            return None
        quiz = await self.quiz_repository.find_by_id(reference.quiz_id)
        if quiz is None:
            return None
        metadata = reference.metadata or {}
        return QuizHistoryDetailResponse(
            id=str(reference.id),
            created_at=reference.created_at,
            quiz_name=metadata.get("quiz_name") or quiz.title,
            question_type=self._quiz_type(quiz),
            difficulty_level=metadata.get("difficulty_level"),
            profession=metadata.get("topic") or quiz.title,
            audience_type=metadata.get("audience_type"),
            custom_instruction=metadata.get("custom_instruction"),
            questions=[
                QuizHistoryQuestionResponse(
                    question=question.question,
                    options=question.options,
                    answer=question.correct_answer,
                )
                for question in quiz.questions
            ],
        )

    async def delete_quiz_history_entry(self, *, user_id: str, history_id: str) -> bool:
        return await self.reference_repository.delete_quiz_history_for_user(user_id, history_id)

    async def create_folder(self, *, user_id: str, name: str) -> FolderDocumentV2:
        return await self.reference_repository.insert_folder(
            FolderDocumentV2(
                user_id=user_id,
                name=name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    async def list_folders(self, *, user_id: str) -> list[dict[str, Any]]:
        folders = await self.reference_repository.list_folders_for_user(user_id)
        payloads: list[dict[str, Any]] = []
        for folder in sorted(folders, key=lambda item: (item.created_at, str(item.id))):
            items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
            payloads.append(
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
        return payloads

    async def get_folder(self, *, folder_id: str, user_id: str) -> dict[str, Any] | None:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None:
            return None
        if folder.user_id != user_id:
            raise PermissionError("Unauthorized access to folder")
        items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
        quizzes_by_id = await self._get_quizzes_by_ids([item.quiz_id for item in items])
        saved_quizzes_by_id = await self._get_saved_quizzes_by_ids(
            [
                item.saved_quiz_id
                for item in items
                if item.saved_quiz_id
            ],
            user_id=user_id,
        )
        quiz_items = []
        for item in sorted(items, key=lambda value: (value.position if value.position is not None else 10**9, value.created_at)):
            quiz = quizzes_by_id.get(item.quiz_id)
            if quiz is None:
                continue
            saved_reference = saved_quizzes_by_id.get(item.saved_quiz_id or "")
            quiz_items.append(
                {
                    "id": str(item.id),
                    "quiz_id": str(quiz.id),
                    "saved_quiz_id": item.saved_quiz_id,
                    "title": (
                        saved_reference.display_title
                        if saved_reference and saved_reference.display_title
                        else item.display_title or quiz.title
                    ),
                    "question_type": self._quiz_type(quiz),
                    "questions": self._saved_questions(quiz),
                    "created_at": self._isoformat(item.created_at),
                    "added_on": self._isoformat(item.created_at),
                }
            )
        return {
            "id": str(folder.id),
            "user_id": folder.user_id,
            "name": folder.name,
            "created_at": self._isoformat(folder.created_at),
            "updated_at": self._isoformat(folder.updated_at),
            "quizzes": quiz_items,
        }

    async def get_folder_by_name(self, *, user_id: str, name: str) -> dict[str, Any] | None:
        normalized_name = name.strip().casefold()
        folders = await self.reference_repository.list_folders_for_user(user_id)
        for folder in folders:
            if folder.name.strip().casefold() == normalized_name:
                return await self.get_folder(folder_id=str(folder.id), user_id=user_id)
        return None

    async def find_quiz_in_folders_by_title(self, *, user_id: str, title: str) -> dict[str, Any]:
        normalized_title = title.strip().casefold()
        matches: list[dict[str, Any]] = []
        folders = await self.reference_repository.list_folders_for_user(user_id)
        for folder in folders:
            folder_payload = await self.get_folder(folder_id=str(folder.id), user_id=user_id)
            if not folder_payload:
                continue
            for quiz in folder_payload.get("quizzes", []):
                quiz_title = str(quiz.get("title") or "")
                normalized_quiz_title = quiz_title.casefold()
                similarity = max(
                    fuzz.partial_ratio(normalized_title, normalized_quiz_title),
                    fuzz.token_set_ratio(normalized_title, normalized_quiz_title),
                )
                if normalized_title in normalized_quiz_title or similarity >= 85:
                    matches.append(
                        {
                            "folder_id": folder_payload["id"],
                            "folder_name": folder_payload["name"],
                            "folder_item_id": quiz.get("id"),
                            "quiz_id": quiz.get("quiz_id"),
                            "title": quiz_title,
                            "question_type": quiz.get("question_type"),
                            "questions": quiz.get("questions") or [],
                            "match_score": similarity,
                        }
                    )
        return {
            "query": title,
            "found": bool(matches),
            "matches": matches,
        }

    async def get_folder_by_id(self, folder_id: str, user_id: str) -> dict[str, Any] | None:
        return await self.get_folder(folder_id=folder_id, user_id=user_id)

    async def rename_folder(self, *, folder_id: str, user_id: str, new_name: str) -> FolderDocumentV2 | None:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return None
        return await self.reference_repository.update_folder(
            str(folder.id),
            name=new_name,
            updated_at=datetime.utcnow(),
        )

    async def delete_folder(self, *, folder_id: str, user_id: str) -> bool:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return False
        await self.reference_repository.delete_folder_by_id(str(folder.id))
        return True

    async def add_saved_quiz_to_folder(
        self,
        *,
        folder_id: str,
        saved_quiz_id: str,
        user_id: str,
    ) -> tuple[FolderDocumentV2, FolderItemDocumentV2]:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            raise PermissionError("Unauthorized access to folder")
        saved_quiz = await self.reference_repository.get_saved_quiz_for_user(user_id, saved_quiz_id)
        if saved_quiz is None:
            raise ValueError("Saved quiz not found")
        quiz = await self.quiz_repository.find_by_id(saved_quiz.quiz_id)
        if quiz is None:
            raise ValueError("Canonical quiz not found")
        existing_items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
        item = await self.reference_repository.upsert_folder_item(
            FolderItemDocumentV2(
                folder_id=str(folder.id),
                quiz_id=str(quiz.id),
                saved_quiz_id=str(saved_quiz.id),
                added_by=user_id,
                position=len(existing_items),
                display_title=saved_quiz.display_title or quiz.title,
                created_at=datetime.utcnow(),
            ),
            revive_deleted=True,
        )
        return folder, item

    async def remove_folder_item(self, *, folder_id: str, folder_item_id: str, user_id: str) -> bool:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return False
        item = await self.reference_repository.get_folder_item_by_public_id(folder_item_id)
        if item is None or item.folder_id != str(folder.id):
            return False
        await self.reference_repository.delete_folder_item_by_id(str(item.id))
        return True

    async def move_folder_item(
        self,
        *,
        folder_item_id: str,
        source_folder_id: str,
        target_folder_id: str,
        user_id: str,
    ) -> bool:
        source_folder = await self.reference_repository.get_folder_by_public_id(source_folder_id)
        target_folder = await self.reference_repository.get_folder_by_public_id(target_folder_id)
        if (
            source_folder is None
            or target_folder is None
            or source_folder.user_id != user_id
            or target_folder.user_id != user_id
        ):
            return False
        item = await self.reference_repository.get_folder_item_by_public_id(folder_item_id)
        if item is None or item.folder_id != str(source_folder.id):
            return False
        target_items = await self.reference_repository.list_folder_items_for_folder(str(target_folder.id))
        updated = await self.reference_repository.update_folder_item(
            str(item.id),
            folder_id=str(target_folder.id),
            position=len(target_items),
        )
        return updated is not None

    async def backfill_folder_item_saved_quiz_ids(self, *, limit: int = 100_000) -> int:
        return await self.reference_repository.backfill_folder_item_saved_quiz_ids(limit=limit)
