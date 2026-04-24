import re
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from server.app.db.core.connection import (
    get_folder_items_v2_collection,
    get_folders_v2_collection,
    get_quiz_history_v2_collection,
    get_saved_quizzes_collection,
    get_saved_quizzes_v2_collection,
)
from server.app.db.crud.quiz_write_service import CanonicalQuizWriteService
from server.app.db.services.quiz_dual_write_service import QuizDualWriteService
from server.app.db.v2.models.quiz_models import QuizCreateV2
from server.app.db.v2.models.reference_models import SavedQuizDocumentV2
from server.app.db.v2.repositories.reference_repository import ReferenceV2Repository


class SavedQuizManagementService:
    def __init__(
        self,
        *,
        legacy_collection: AsyncIOMotorCollection | None = None,
        canonical_service: CanonicalQuizWriteService | None = None,
        reference_repository: ReferenceV2Repository | None = None,
        dual_write_service: QuizDualWriteService | None = None,
    ):
        self.legacy_collection = legacy_collection or get_saved_quizzes_collection()
        self.canonical_service = canonical_service or CanonicalQuizWriteService()
        self.reference_repository = reference_repository or ReferenceV2Repository(
            get_folders_v2_collection(),
            get_folder_items_v2_collection(),
            get_saved_quizzes_v2_collection(),
            get_quiz_history_v2_collection(),
        )
        self.dual_write_service = dual_write_service or QuizDualWriteService(
            canonical_service=self.canonical_service,
            reference_repository=self.reference_repository,
        )

    @staticmethod
    def _normalize_legacy_saved_quiz(document: dict | None) -> dict | None:
        if not document:
            return None
        normalized = dict(document)
        normalized["_id"] = str(normalized["_id"])
        return normalized

    @staticmethod
    def _serialize_saved_quiz(legacy_saved_quiz: dict, canonical_quiz) -> dict:
        return {
            "_id": legacy_saved_quiz["_id"],
            "user_id": legacy_saved_quiz["user_id"],
            "quiz_id": str(canonical_quiz.id),
            "title": legacy_saved_quiz["title"],
            "question_type": legacy_saved_quiz["question_type"],
            "canonical_quiz_id": str(canonical_quiz.id),
            "is_deleted": False,
            "questions": [
                {
                    "question": question.question,
                    "options": question.options,
                    "question_type": legacy_saved_quiz["question_type"],
                }
                for question in canonical_quiz.questions
            ],
            "created_at": legacy_saved_quiz["created_at"],
        }

    async def _get_legacy_saved_quiz(self, quiz_id: str, user_id: str) -> dict | None:
        legacy_quiz = await self.legacy_collection.find_one(
            {"_id": ObjectId(quiz_id), "user_id": user_id}
        )
        return self._normalize_legacy_saved_quiz(legacy_quiz)

    async def _ensure_canonical_quiz(self, legacy_saved_quiz: dict):
        canonical_quiz_id = legacy_saved_quiz.get("canonical_quiz_id")
        if canonical_quiz_id:
            canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(canonical_quiz_id)
            if canonical_quiz:
                return canonical_quiz

        mirrored = await self.dual_write_service.mirror_saved_quiz(
            {
                **legacy_saved_quiz,
                "_id": ObjectId(legacy_saved_quiz["_id"]),
            }
        )
        if not mirrored:
            raise ValueError("Unable to resolve canonical quiz")

        await self.legacy_collection.update_one(
            {"_id": ObjectId(legacy_saved_quiz["_id"])},
            {
                "$set": {
                    "canonical_quiz_id": str(mirrored.id),
                }
            },
        )
        return mirrored

    async def _resolve_canonical_for_create(
        self,
        *,
        title: str,
        question_type: str,
        questions: list,
        source_quiz_id: str | None,
        user_id: str,
    ):
        canonical_quiz = None
        if source_quiz_id:
            canonical_quiz = await self.dual_write_service._resolve_canonical_from_source_quiz_id(
                source_quiz_id
            )
            if not canonical_quiz:
                canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(source_quiz_id)

        if canonical_quiz:
            return await self._create_canonical_copy(
                canonical_quiz,
                title=title.strip(),
                owner_user_id=user_id,
            )

        normalized_questions = self.canonical_service.normalize_questions(questions)
        if any(not question.get("correct_answer") for question in normalized_questions):
            return None

        quiz_create = QuizCreateV2(
            title=title.strip(),
            quiz_type=question_type,
            owner_user_id=user_id,
            source="manual",
            questions=normalized_questions,
        )
        return await self.canonical_service.create_quiz_v2(quiz_create)

    async def _build_duplicate_title(self, user_id: str, original_title: str) -> str:
        base_title = f"Copy of {original_title.strip()}"
        title_pattern = re.compile(
            rf"^{re.escape(base_title)}(?: (\d+))?$",
            re.IGNORECASE,
        )
        existing_titles = await self.legacy_collection.distinct("title", {"user_id": user_id})

        highest_suffix = 0
        base_exists = False
        for existing_title in existing_titles:
            if not isinstance(existing_title, str):
                continue
            match = title_pattern.match(existing_title.strip())
            if not match:
                continue
            if match.group(1):
                highest_suffix = max(highest_suffix, int(match.group(1)))
            else:
                base_exists = True

        if not base_exists:
            return base_title
        return f"{base_title} {highest_suffix + 1}"

    async def _create_canonical_copy(self, canonical_quiz, *, title: str, owner_user_id: str):
        quiz_create = QuizCreateV2(
            title=title,
            description=canonical_quiz.description,
            quiz_type=canonical_quiz.quiz_type,
            owner_user_id=owner_user_id,
            visibility=canonical_quiz.visibility,
            status=canonical_quiz.status,
            source="manual",
            tags=list(canonical_quiz.tags),
            questions=[
                {
                    "question": question.question,
                    "options": question.options,
                    "correct_answer": question.correct_answer,
                }
                for question in canonical_quiz.questions
            ],
        )
        return await self.canonical_service.create_quiz_v2(quiz_create)

    async def _insert_legacy_saved_quiz(
        self,
        *,
        user_id: str,
        title: str,
        question_type: str,
        canonical_quiz,
    ):
        now = datetime.utcnow()
        legacy_payload = {
            "user_id": user_id,
            "quiz_id": str(canonical_quiz.id),
            "title": title,
            "question_type": question_type,
            "canonical_quiz_id": str(canonical_quiz.id),
            "is_deleted": False,
            "questions": [
                {
                    "question": question.question,
                    "options": question.options,
                    "question_type": question_type,
                }
                for question in canonical_quiz.questions
            ],
            "created_at": now,
        }
        result = await self.legacy_collection.insert_one(legacy_payload)
        legacy_payload["_id"] = str(result.inserted_id)
        return legacy_payload, now

    async def create_saved_quiz(
        self,
        *,
        user_id: str,
        title: str,
        question_type: str,
        questions: list,
        quiz_id: str | None = None,
    ):
        canonical_quiz = await self._resolve_canonical_for_create(
            title=title,
            question_type=question_type,
            questions=questions,
            source_quiz_id=quiz_id,
            user_id=user_id,
        )
        if canonical_quiz is None:
            return None

        legacy_saved_quiz, saved_at = await self._insert_legacy_saved_quiz(
            user_id=user_id,
            title=title.strip(),
            question_type=question_type,
            canonical_quiz=canonical_quiz,
        )
        await self.reference_repository.insert_saved_quiz(
            SavedQuizDocumentV2(
                user_id=user_id,
                quiz_id=str(canonical_quiz.id),
                legacy_saved_quiz_id=legacy_saved_quiz["_id"],
                saved_at=saved_at,
            )
        )
        return legacy_saved_quiz

    async def list_saved_quizzes(self, user_id: str):
        cursor = self.reference_repository.saved_quizzes_collection.find(
            {"user_id": user_id}
        ).sort("saved_at", -1)
        saved_references = await cursor.to_list(length=100)
        quizzes = []

        for reference in saved_references:
            legacy_id = reference.get("legacy_saved_quiz_id")
            legacy_saved_quiz = None
            if legacy_id:
                legacy_saved_quiz = await self._get_legacy_saved_quiz(legacy_id, user_id)
                if legacy_saved_quiz:
                    quizzes.append(legacy_saved_quiz)
                    continue

            canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(reference["quiz_id"])
            if not canonical_quiz:
                continue

            synthesized = {
                "_id": legacy_id or str(ObjectId()),
                "user_id": user_id,
                "title": canonical_quiz.title,
                "question_type": canonical_quiz.quiz_type.value,
                "created_at": reference.get("saved_at", datetime.utcnow()),
            }
            quizzes.append(self._serialize_saved_quiz(synthesized, canonical_quiz))

        return quizzes

    async def get_saved_quiz(self, quiz_id: str, user_id: str):
        legacy_saved_quiz = await self._get_legacy_saved_quiz(quiz_id, user_id)
        if legacy_saved_quiz:
            return legacy_saved_quiz

        reference = await self.reference_repository.saved_quizzes_collection.find_one(
            {"legacy_saved_quiz_id": quiz_id, "user_id": user_id}
        )
        if not reference:
            return None

        canonical_quiz = await self.canonical_service.get_quiz_v2_by_id(reference["quiz_id"])
        if not canonical_quiz:
            return None

        synthesized = {
            "_id": quiz_id,
            "user_id": user_id,
            "title": canonical_quiz.title,
            "question_type": canonical_quiz.quiz_type.value,
            "created_at": reference.get("saved_at", datetime.utcnow()),
        }
        return self._serialize_saved_quiz(synthesized, canonical_quiz)

    async def delete_saved_quiz(self, quiz_id: str, user_id: str):
        legacy_saved_quiz = await self._get_legacy_saved_quiz(quiz_id, user_id)
        if not legacy_saved_quiz:
            return False

        reference = await self.reference_repository.saved_quizzes_collection.find_one_and_delete(
            {"legacy_saved_quiz_id": quiz_id, "user_id": user_id}
        )
        await self.legacy_collection.delete_one(
            {"_id": ObjectId(quiz_id), "user_id": user_id}
        )
        return reference is not None or legacy_saved_quiz is not None

    async def duplicate_saved_quiz(self, quiz_id: str, user_id: str):
        legacy_saved_quiz = await self._get_legacy_saved_quiz(quiz_id, user_id)
        if not legacy_saved_quiz:
            return None

        canonical_quiz = await self._ensure_canonical_quiz(legacy_saved_quiz)
        duplicate_title = await self._build_duplicate_title(user_id, legacy_saved_quiz["title"])
        duplicated_canonical = await self._create_canonical_copy(
            canonical_quiz,
            title=duplicate_title,
            owner_user_id=user_id,
        )
        legacy_duplicate, saved_at = await self._insert_legacy_saved_quiz(
            user_id=user_id,
            title=duplicate_title,
            question_type=legacy_saved_quiz["question_type"],
            canonical_quiz=duplicated_canonical,
        )
        await self.reference_repository.insert_saved_quiz(
            SavedQuizDocumentV2(
                user_id=user_id,
                quiz_id=str(duplicated_canonical.id),
                legacy_saved_quiz_id=legacy_duplicate["_id"],
                saved_at=saved_at,
            )
        )
        return legacy_duplicate

    async def rename_saved_quiz(self, quiz_id: str, user_id: str, new_title: str):
        sanitized_title = new_title.strip()
        if not sanitized_title:
            raise ValueError("Quiz title cannot be empty")

        legacy_saved_quiz = await self._get_legacy_saved_quiz(quiz_id, user_id)
        if not legacy_saved_quiz:
            return None

        canonical_quiz = await self._ensure_canonical_quiz(legacy_saved_quiz)
        renamed_canonical = await self._create_canonical_copy(
            canonical_quiz,
            title=sanitized_title,
            owner_user_id=user_id,
        )
        await self.reference_repository.update_saved_quiz_by_legacy_id(
            legacy_saved_quiz["_id"],
            quiz_id=str(renamed_canonical.id),
        )
        await self.legacy_collection.update_one(
            {"_id": ObjectId(legacy_saved_quiz["_id"]), "user_id": user_id},
            {
                "$set": {
                    "title": sanitized_title,
                    "quiz_id": str(renamed_canonical.id),
                    "canonical_quiz_id": str(renamed_canonical.id),
                    "questions": [
                        {
                            "question": question.question,
                            "options": question.options,
                            "question_type": legacy_saved_quiz["question_type"],
                        }
                        for question in renamed_canonical.questions
                    ],
                }
            },
        )
        updated_legacy = await self._get_legacy_saved_quiz(quiz_id, user_id)
        return updated_legacy
