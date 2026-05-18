import logging
import inspect
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.db.core.config import settings
from server.app.db.core.connection import (
    get_ai_generated_quizzes_collection,
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_history_v2_collection,
    get_quizzes_collection,
    get_quizzes_v2_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.db.crud.quiz_write_service import CanonicalQuizWriteService
from server.app.db.services.legacy_quiz_resolution_service import LegacyQuizResolutionService
from server.app.db.v2.models.reference_models import (
    FolderDocumentV2,
    FolderItemDocumentV2,
    QuizHistoryDocumentV2,
    SavedQuizDocumentV2,
)
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository


logger = logging.getLogger(__name__)


class QuizDualWriteService:
    def __init__(
        self,
        *,
        canonical_service: Optional[CanonicalQuizWriteService] = None,
        reference_repository: Optional[ReferenceV2Repository] = None,
        ai_generated_quizzes_collection: Optional[AsyncIOMotorCollection] = None,
        quizzes_collection: Optional[AsyncIOMotorCollection] = None,
    ):
        self.canonical_service = canonical_service or CanonicalQuizWriteService()
        self.reference_repository = reference_repository or ReferenceV2Repository(
            get_folders_v2_collection(),
            get_folder_items_v2_collection(),
            get_saved_quizzes_v2_collection(),
            get_quiz_history_v2_collection(),
        )
        self.ai_generated_quizzes_collection = (
            ai_generated_quizzes_collection
            if ai_generated_quizzes_collection is not None
            else get_ai_generated_quizzes_collection()
        )
        self.quizzes_collection = (
            quizzes_collection
            if quizzes_collection is not None
            else get_quizzes_collection()
        )
        self.legacy_resolution_service = LegacyQuizResolutionService(
            canonical_service=self.canonical_service,
            ai_generated_quizzes_collection=self.ai_generated_quizzes_collection,
            quizzes_collection=self.quizzes_collection,
        )

    @property
    def write_mode(self) -> str:
        return settings.QUIZ_V2_WRITE_MODE

    @property
    def dual_write_enabled(self) -> bool:
        return self.write_mode == "dual_write"

    @property
    def v2_only_enabled(self) -> bool:
        return self.write_mode == "v2_only"

    def _log(self, event: str, **fields):
        if not settings.QUIZ_V2_STRUCTURED_LOGGING:
            return
        logger.info("%s | %s", event, fields)

    def _extract_log_fields(self, result):
        if result is None:
            return {}

        if isinstance(result, tuple):
            canonical_quiz = result[0] if len(result) > 0 else None
            reference_record = result[1] if len(result) > 1 else None
            fields = {}
            if canonical_quiz is not None and hasattr(canonical_quiz, "id"):
                fields["v2_quiz_id"] = str(canonical_quiz.id)
            if reference_record is not None and hasattr(reference_record, "id"):
                fields["v2_reference_id"] = str(reference_record.id)
            if reference_record is not None and hasattr(reference_record, "quiz_id"):
                fields["referenced_quiz_id"] = str(reference_record.quiz_id)
            return fields

        fields = {}
        if hasattr(result, "id"):
            fields["v2_record_id"] = str(result.id)
        if hasattr(result, "quiz_id"):
            fields["referenced_quiz_id"] = str(result.quiz_id)
            fields.setdefault("v2_quiz_id", str(result.quiz_id))
        elif hasattr(result, "id"):
            fields["v2_quiz_id"] = str(result.id)
        return fields

    async def _mirror_quiz_document(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
        description: str | None = None,
        owner_user_id: str | None = None,
        source: str = "legacy",
        legacy_source_collection: str | None = None,
        legacy_quiz_id: str | None = None,
    ):
        normalized_questions = self.canonical_service.normalize_questions(questions)
        if any(not question.get("correct_answer") for question in normalized_questions):
            structure_fingerprint = self.canonical_service.build_content_fingerprint(
                {
                    "title": title.strip(),
                    "quiz_type": quiz_type,
                    "questions": [
                        {
                            "question": question.get("question"),
                            "options": question.get("options"),
                        }
                        for question in normalized_questions
                    ],
                }
            )
            existing = await self.canonical_service.repository.find_by_structure_fingerprint(
                structure_fingerprint
            )
            if existing:
                return existing
            matched_legacy_quiz = await self.legacy_resolution_service.resolve_from_legacy_structure(
                title=title,
                quiz_type=quiz_type,
                questions=questions,
                allow_create=True,
            )
            if matched_legacy_quiz:
                return matched_legacy_quiz
            existing_v2 = await self.legacy_resolution_service.resolve_existing_v2_from_question_structure(
                title=title,
                quiz_type=quiz_type,
                questions=questions,
            )
            if existing_v2:
                return existing_v2
            raise ValueError("Cannot create canonical quiz without answer data")
        quiz_document = self.canonical_service.build_quiz_document(
            title=title,
            description=description,
            quiz_type=quiz_type,
            owner_user_id=owner_user_id,
            source=source,
            questions=normalized_questions,
            legacy_source_collection=legacy_source_collection,
            legacy_quiz_id=legacy_quiz_id,
        )
        existing = await self.legacy_resolution_service.resolve_existing_v2_from_question_structure(
            title=title,
            quiz_type=quiz_type,
            questions=normalized_questions,
        )
        if existing:
            return existing
        if legacy_source_collection and legacy_quiz_id:
            return await self.canonical_service.upsert_quiz_v2_by_legacy_mapping(quiz_document)
        return await self.canonical_service.find_or_create_quiz_v2_by_fingerprint(quiz_document)

    async def _resolve_canonical_from_source_quiz_id(self, source_quiz_id: str | None):
        return await self.legacy_resolution_service.resolve_from_source_quiz_id(source_quiz_id)

    async def _resolve_canonical_from_any_quiz_id(self, quiz_id: str | None):
        if not quiz_id:
            return None
        canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(quiz_id)
        if canonical_quiz:
            return canonical_quiz
        return await self._resolve_canonical_from_source_quiz_id(quiz_id)


    async def mirror_legacy_manual_quiz(self, legacy_quiz_id: str, legacy_quiz_doc: dict):
        return await self._run_fail_open(
            operation="manual_quiz_create_or_update",
            legacy_collection="quizzes",
            legacy_id=legacy_quiz_id,
            coroutine_factory=lambda: self._mirror_quiz_document(
                title=legacy_quiz_doc["title"],
                description=legacy_quiz_doc.get("description"),
                quiz_type=legacy_quiz_doc["quiz_type"],
                owner_user_id=legacy_quiz_doc.get("owner_id"),
                source="legacy",
                questions=legacy_quiz_doc["questions"],
                legacy_source_collection="quizzes",
                legacy_quiz_id=legacy_quiz_id,
            ),
        )

    async def mirror_ai_generated_quiz(self, legacy_quiz_id: str, legacy_quiz_doc: dict):
        mirrored = await self._run_fail_open(
            operation="ai_generated_quiz_create",
            legacy_collection="ai_generated_quizzes",
            legacy_id=legacy_quiz_id,
            coroutine_factory=lambda: self._mirror_quiz_document(
                title=legacy_quiz_doc.get("profession") or "General Knowledge",
                description=legacy_quiz_doc.get("custom_instruction"),
                quiz_type=legacy_quiz_doc.get("question_type", "multichoice"),
                owner_user_id=legacy_quiz_doc.get("user_id"),
                source="ai",
                questions=legacy_quiz_doc["questions"],
                legacy_source_collection="ai_generated_quizzes",
                legacy_quiz_id=legacy_quiz_id,
            ),
        )
        if mirrored:
            await self.ai_generated_quizzes_collection.update_one(
                {"_id": legacy_quiz_doc["_id"]},
                {"$set": {"canonical_quiz_id": str(mirrored.id)}},
            )
        return mirrored

    async def mirror_saved_quiz(self, legacy_saved_doc: dict):
        async def action():
            canonical_quiz = None
            if legacy_saved_doc.get("canonical_quiz_id"):
                canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(
                    legacy_saved_doc["canonical_quiz_id"]
                )
            if not canonical_quiz:
                canonical_quiz = await self._resolve_canonical_from_any_quiz_id(
                    legacy_saved_doc.get("quiz_id")
                )
            if not canonical_quiz:
                canonical_quiz = await self._mirror_quiz_document(
                    title=legacy_saved_doc["title"],
                    quiz_type=legacy_saved_doc["question_type"],
                    owner_user_id=None,
                    source="legacy",
                    questions=legacy_saved_doc["questions"],
                )
            saved_reference = await self.reference_repository.upsert_saved_quiz(
                SavedQuizDocumentV2(
                    user_id=legacy_saved_doc["user_id"],
                    quiz_id=str(canonical_quiz.id),
                    display_title=legacy_saved_doc.get("title") or canonical_quiz.title,
                    legacy_saved_quiz_id=str(legacy_saved_doc["_id"]),
                    saved_at=legacy_saved_doc.get("created_at", datetime.utcnow()),
                )
            )
            return canonical_quiz, saved_reference

        result = await self._run_fail_open(
            operation="saved_quiz_create",
            legacy_collection="saved_quizzes",
            legacy_id=str(legacy_saved_doc["_id"]),
            coroutine_factory=action,
        )
        if result:
            canonical_quiz, _saved_reference = result
            return canonical_quiz
        return None

    async def create_saved_quiz_v2(
        self,
        *,
        user_id: str,
        title: str,
        question_type: str,
        questions: list[Any],
        quiz_id: str | None = None,
        saved_at: datetime | None = None,
    ) -> SavedQuizDocumentV2:
        canonical_quiz = await self._resolve_canonical_from_any_quiz_id(quiz_id)
        if not canonical_quiz:
            canonical_quiz = await self._mirror_quiz_document(
                title=title,
                quiz_type=question_type,
                owner_user_id=None,
                source="legacy",
                questions=questions,
            )
        reference = await self.reference_repository.upsert_saved_quiz(
            SavedQuizDocumentV2(
                user_id=user_id,
                quiz_id=str(canonical_quiz.id),
                display_title=title or canonical_quiz.title,
                saved_at=saved_at or datetime.utcnow(),
            ),
            revive_deleted=True,
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="saved_quiz_create",
            write_mode=self.write_mode,
            user_id=user_id,
            saved_quiz_id=str(reference.id),
            canonical_quiz_id=str(canonical_quiz.id),
        )
        return reference

    async def delete_saved_quiz_v2(self, *, saved_quiz_id: str, user_id: str) -> bool:
        saved_reference = await self.reference_repository.get_saved_quiz_by_public_id(
            saved_quiz_id,
            user_id=user_id,
        )
        if saved_reference is None:
            return False
        deleted_count = await self.reference_repository.delete_saved_quiz_by_id(
            str(saved_reference.id),
            user_id=user_id,
        )
        deleted = deleted_count > 0
        self._log(
            "quiz_v2_only_write_served",
            operation="saved_quiz_delete",
            write_mode=self.write_mode,
            user_id=user_id,
            saved_quiz_id=saved_quiz_id,
            deleted=deleted,
        )
        return deleted

    async def mirror_quiz_history(self, legacy_history_doc: dict):
        async def action():
            canonical_quiz = None
            if legacy_history_doc.get("canonical_quiz_id"):
                canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(
                    legacy_history_doc["canonical_quiz_id"]
                )
            if not canonical_quiz:
                canonical_quiz = await self._resolve_canonical_from_any_quiz_id(
                    legacy_history_doc.get("quiz_id")
                )
            if not canonical_quiz:
                canonical_quiz = await self._mirror_quiz_document(
                    title=self.legacy_resolution_service.choose_preferred_title(
                        title=legacy_history_doc.get("quiz_name"),
                        fallback_title=legacy_history_doc.get("profession"),
                        quiz_type=legacy_history_doc.get("question_type"),
                        default="Quiz History",
                    ),
                    description=legacy_history_doc.get("custom_instruction"),
                    quiz_type=legacy_history_doc["question_type"],
                    owner_user_id=None,
                    source="legacy",
                    questions=legacy_history_doc["questions"],
                )
            history_reference = await self.reference_repository.upsert_quiz_history(
                QuizHistoryDocumentV2(
                    user_id=legacy_history_doc["user_id"],
                    quiz_id=str(canonical_quiz.id),
                    action="generated",
                    metadata={
                        "source": canonical_quiz.source,
                        "topic": legacy_history_doc.get("profession") or canonical_quiz.title,
                        "difficulty_level": legacy_history_doc.get("difficulty_level"),
                        "audience_type": legacy_history_doc.get("audience_type"),
                    },
                    legacy_history_id=str(legacy_history_doc["_id"]),
                    created_at=legacy_history_doc.get("created_at", datetime.utcnow()),
                )
            )
            return canonical_quiz, history_reference

        result = await self._run_fail_open(
            operation="quiz_history_create",
            legacy_collection="quiz_history",
            legacy_id=str(legacy_history_doc["_id"]),
            coroutine_factory=action,
        )
        if result:
            canonical_quiz, _history_reference = result
            return canonical_quiz
        return None

    async def create_quiz_history_v2(self, quiz_data: dict[str, Any]) -> QuizHistoryDocumentV2:
        canonical_quiz = None
        if quiz_data.get("canonical_quiz_id"):
            canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(
                quiz_data["canonical_quiz_id"]
            )
        if not canonical_quiz:
            canonical_quiz = await self._resolve_canonical_from_any_quiz_id(quiz_data.get("quiz_id"))
        if not canonical_quiz:
            canonical_quiz = await self._mirror_quiz_document(
                title=self.legacy_resolution_service.choose_preferred_title(
                    title=quiz_data.get("quiz_name"),
                    fallback_title=quiz_data.get("profession"),
                    quiz_type=quiz_data.get("question_type"),
                    default="Quiz History",
                ),
                description=quiz_data.get("custom_instruction"),
                quiz_type=quiz_data["question_type"],
                owner_user_id=None,
                source="legacy",
                questions=quiz_data["questions"],
            )
        reference = await self.reference_repository.insert_quiz_history(
            QuizHistoryDocumentV2(
                user_id=quiz_data["user_id"],
                quiz_id=str(canonical_quiz.id),
                action="generated",
                metadata={
                    "source": canonical_quiz.source,
                    "topic": quiz_data.get("profession") or canonical_quiz.title,
                    "difficulty_level": quiz_data.get("difficulty_level"),
                    "audience_type": quiz_data.get("audience_type"),
                },
                created_at=quiz_data.get("created_at", datetime.utcnow()),
            )
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="quiz_history_create",
            write_mode=self.write_mode,
            user_id=quiz_data["user_id"],
            history_id=str(reference.id),
            canonical_quiz_id=str(canonical_quiz.id),
        )
        return reference

    async def delete_quiz_history_v2(self, *, history_id: str, user_id: str) -> bool:
        deleted_count = await self.reference_repository.soft_delete_quiz_history_by_id(
            history_id,
            user_id=user_id,
        )
        deleted = deleted_count > 0
        self._log(
            "quiz_v2_only_write_served",
            operation="quiz_history_delete",
            write_mode=self.write_mode,
            user_id=user_id,
            history_id=history_id,
            deleted=deleted,
        )
        return deleted

    async def mirror_folder_create(self, legacy_folder_doc: dict):
        return await self._run_fail_open(
            operation="folder_create_or_update",
            legacy_collection="folders",
            legacy_id=str(legacy_folder_doc["_id"]),
            coroutine_factory=lambda: self.reference_repository.upsert_folder_by_legacy_id(
                FolderDocumentV2(
                    user_id=legacy_folder_doc["user_id"],
                    name=legacy_folder_doc["name"],
                    description=legacy_folder_doc.get("description"),
                    legacy_folder_id=str(legacy_folder_doc["_id"]),
                    created_at=legacy_folder_doc.get("created_at", datetime.utcnow()),
                    updated_at=legacy_folder_doc.get("updated_at", datetime.utcnow()),
                )
            ),
        )

    async def create_folder_v2(
        self,
        *,
        user_id: str,
        name: str,
        description: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> FolderDocumentV2:
        folder = await self.reference_repository.insert_folder(
            FolderDocumentV2(
                user_id=user_id,
                name=name,
                description=description,
                created_at=created_at or datetime.utcnow(),
                updated_at=updated_at or datetime.utcnow(),
            )
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_create",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_id=str(folder.id),
        )
        return folder

    async def rename_folder_v2(
        self,
        *,
        folder_id: str,
        user_id: str,
        new_name: str,
    ) -> FolderDocumentV2 | None:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return None
        updated = await self.reference_repository.update_folder(
            str(folder.id),
            name=new_name,
            updated_at=datetime.utcnow(),
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_rename",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_id=folder_id,
            updated=updated is not None,
        )
        return updated

    async def mirror_folder_delete(self, legacy_folder_id: str):
        return await self._run_fail_open(
            operation="folder_delete",
            legacy_collection="folders",
            legacy_id=legacy_folder_id,
            coroutine_factory=lambda: self.reference_repository.delete_folder_by_legacy_id(
                legacy_folder_id
            ),
        )

    async def delete_folder_v2(self, *, folder_id: str, user_id: str) -> bool:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return False
        await self.reference_repository.delete_folder_by_id(str(folder.id))
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_delete",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_id=folder_id,
            deleted=True,
        )
        return True

    async def mirror_folder_item_add(self, legacy_folder_doc: dict, legacy_folder_item: dict):
        async def action():
            folder_v2 = await self.reference_repository.get_folder_by_legacy_id(
                str(legacy_folder_doc["_id"])
            )
            if not folder_v2:
                folder_v2 = await self.reference_repository.upsert_folder_by_legacy_id(
                    FolderDocumentV2(
                        user_id=legacy_folder_doc["user_id"],
                        name=legacy_folder_doc["name"],
                        description=legacy_folder_doc.get("description"),
                        legacy_folder_id=str(legacy_folder_doc["_id"]),
                        created_at=legacy_folder_doc.get("created_at", datetime.utcnow()),
                        updated_at=legacy_folder_doc.get("updated_at", datetime.utcnow()),
                    )
                )
            canonical_quiz_id = legacy_folder_item.get("canonical_quiz_id")
            if not canonical_quiz_id:
                quiz_payload = legacy_folder_item.get("quiz_data", {})
                canonical_quiz = await self._resolve_canonical_from_source_quiz_id(
                    legacy_folder_item.get("quiz_id")
                    or quiz_payload.get("quiz_id")
                )
                if not canonical_quiz:
                    canonical_quiz = await self._resolve_canonical_from_any_quiz_id(
                        legacy_folder_item.get("canonical_quiz_id")
                    )
                if not canonical_quiz:
                    canonical_quiz = await self._mirror_quiz_document(
                        title=legacy_folder_item.get("title") or quiz_payload.get("title") or "Untitled Quiz",
                        quiz_type=legacy_folder_item.get("question_type")
                        or quiz_payload.get("question_type")
                        or "multichoice",
                        questions=legacy_folder_item.get("questions")
                        or quiz_payload.get("questions", []),
                        source="legacy",
                    )
                canonical_quiz_id = str(canonical_quiz.id)
            position = None
            for index, item in enumerate(legacy_folder_doc.get("quizzes", [])):
                if str(item.get("_id")) == str(legacy_folder_item.get("_id")):
                    position = index
                    break
            return await self.reference_repository.upsert_folder_item_by_legacy_id(
                FolderItemDocumentV2(
                    folder_id=str(folder_v2.id),
                    quiz_id=canonical_quiz_id,
                    added_by=legacy_folder_doc.get("user_id"),
                    position=position,
                    display_title=legacy_folder_item.get("title")
                    or quiz_payload.get("title")
                    or None,
                    legacy_folder_item_id=legacy_folder_item["_id"],
                    created_at=legacy_folder_item.get("added_on", datetime.utcnow()),
                )
            )

        return await self._run_fail_open(
            operation="folder_item_add",
            legacy_collection="folders",
            legacy_id=str(legacy_folder_doc["_id"]),
            coroutine_factory=action,
        )

    async def add_saved_quiz_to_folder_v2(
        self,
        *,
        folder_id: str,
        saved_quiz_id: str,
        user_id: str,
    ) -> tuple[FolderDocumentV2, FolderItemDocumentV2]:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            raise PermissionError("Unauthorized access to folder")

        saved_reference = await self.reference_repository.get_saved_quiz_by_public_id(
            saved_quiz_id,
            user_id=user_id,
        )
        if saved_reference is None:
            raise ValueError("Saved quiz not found")

        canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(saved_reference.quiz_id)
        if canonical_quiz is None:
            raise ValueError("Canonical quiz not found")

        existing_items = await self.reference_repository.list_folder_items_for_folder(str(folder.id))
        folder_item = await self.reference_repository.upsert_folder_item_by_legacy_id(
            FolderItemDocumentV2(
                folder_id=str(folder.id),
                quiz_id=str(canonical_quiz.id),
                added_by=user_id,
                position=len(existing_items),
                display_title=saved_reference.display_title or canonical_quiz.title,
                created_at=datetime.utcnow(),
            ),
            revive_deleted=True,
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_item_add",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_id=folder_id,
            folder_item_id=str(folder_item.id),
            canonical_quiz_id=str(canonical_quiz.id),
        )
        return folder, folder_item

    async def mirror_folder_item_remove(self, legacy_folder_item_id: str):
        return await self._run_fail_open(
            operation="folder_item_remove",
            legacy_collection="folders",
            legacy_id=legacy_folder_item_id,
            coroutine_factory=lambda: self.reference_repository.delete_folder_item_by_legacy_id(
                legacy_folder_item_id
            ),
        )

    async def remove_folder_item_v2(
        self,
        *,
        folder_id: str,
        folder_item_id: str,
        user_id: str,
    ) -> bool:
        folder = await self.reference_repository.get_folder_by_public_id(folder_id)
        if folder is None or folder.user_id != user_id:
            return False
        folder_item = await self.reference_repository.get_folder_item_by_public_id(folder_item_id)
        if folder_item is None or folder_item.folder_id != str(folder.id):
            return False
        await self.reference_repository.delete_folder_item_by_id(str(folder_item.id))
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_item_remove",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_id=folder_id,
            folder_item_id=folder_item_id,
            deleted=True,
        )
        return True

    async def mirror_folder_item_move(
        self,
        legacy_folder_item_id: str,
        target_legacy_folder_doc: dict,
    ):
        async def action():
            folder_item = await self.reference_repository.get_folder_item_by_legacy_id(
                legacy_folder_item_id
            )
            if not folder_item:
                return None
            target_folder = await self.reference_repository.get_folder_by_legacy_id(
                str(target_legacy_folder_doc["_id"])
            )
            if not target_folder:
                target_folder = await self.reference_repository.upsert_folder_by_legacy_id(
                    FolderDocumentV2(
                        user_id=target_legacy_folder_doc["user_id"],
                        name=target_legacy_folder_doc["name"],
                        description=target_legacy_folder_doc.get("description"),
                        legacy_folder_id=str(target_legacy_folder_doc["_id"]),
                        created_at=target_legacy_folder_doc.get("created_at", datetime.utcnow()),
                        updated_at=target_legacy_folder_doc.get("updated_at", datetime.utcnow()),
                    )
                )
            position = None
            for index, item in enumerate(target_legacy_folder_doc.get("quizzes", [])):
                if str(item.get("_id")) == str(legacy_folder_item_id):
                    position = index
                    break
            return await self.reference_repository.upsert_folder_item_by_legacy_id(
                FolderItemDocumentV2(
                    folder_id=str(target_folder.id),
                    quiz_id=folder_item.quiz_id,
                    added_by=folder_item.added_by,
                    position=position if position is not None else folder_item.position,
                    display_title=folder_item.display_title,
                    legacy_folder_item_id=legacy_folder_item_id,
                    created_at=folder_item.created_at,
                )
            )

        return await self._run_fail_open(
            operation="folder_item_move",
            legacy_collection="folders",
            legacy_id=legacy_folder_item_id,
            coroutine_factory=action,
        )

    async def move_folder_item_v2(
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

        folder_item = await self.reference_repository.get_folder_item_by_public_id(folder_item_id)
        if folder_item is None or folder_item.folder_id != str(source_folder.id):
            return False

        target_items = await self.reference_repository.list_folder_items_for_folder(str(target_folder.id))
        updated = await self.reference_repository.update_folder_item(
            str(folder_item.id),
            folder_id=str(target_folder.id),
            position=len(target_items),
        )
        self._log(
            "quiz_v2_only_write_served",
            operation="folder_item_move",
            write_mode=self.write_mode,
            user_id=user_id,
            folder_item_id=folder_item_id,
            source_folder_id=source_folder_id,
            target_folder_id=target_folder_id,
            updated=updated is not None,
        )
        return updated is not None

    async def _run_fail_open(
        self,
        *,
        operation: str,
        legacy_collection: str,
        legacy_id: str,
        coroutine_factory,
    ):
        self._log(
            "quiz_dual_write_started",
            operation=operation,
            legacy_collection=legacy_collection,
            legacy_id=legacy_id,
            write_mode=self.write_mode,
        )
        if not self.dual_write_enabled:
            self._log(
                "quiz_dual_write_completed",
                operation=operation,
                legacy_collection=legacy_collection,
                legacy_id=legacy_id,
                write_mode=self.write_mode,
                dual_write_skipped=True,
            )
            return None
        try:
            coroutine = coroutine_factory() if callable(coroutine_factory) else coroutine_factory
            if inspect.isawaitable(coroutine):
                result = await coroutine
            else:
                result = coroutine
            self._log(
                "quiz_dual_write_v2_succeeded",
                operation=operation,
                legacy_collection=legacy_collection,
                legacy_id=legacy_id,
                write_mode=self.write_mode,
                **self._extract_log_fields(result),
            )
            return result
        except Exception as exc:
            extra_fields = exc.to_log_fields() if hasattr(exc, "to_log_fields") else {}
            self._log(
                "quiz_dual_write_v2_failed",
                operation=operation,
                legacy_collection=legacy_collection,
                legacy_id=legacy_id,
                write_mode=self.write_mode,
                error=str(exc),
                **extra_fields,
            )
            if settings.QUIZ_V2_FAIL_OPEN:
                return None
            raise
