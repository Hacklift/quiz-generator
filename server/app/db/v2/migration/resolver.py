from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.db.crud.quiz_write_service import CanonicalQuizWriteService
from server.app.db.services.legacy_quiz_resolution_service import (
    LegacyQuizResolutionService,
)


class LegacyQuizResolver:
    def __init__(
        self,
        *,
        canonical_service: CanonicalQuizWriteService,
        ai_generated_quizzes_collection: AsyncIOMotorCollection,
        quizzes_collection: AsyncIOMotorCollection,
        saved_quizzes_collection: AsyncIOMotorCollection,
    ):
        self.canonical_service = canonical_service
        self.ai_generated_quizzes_collection = ai_generated_quizzes_collection
        self.quizzes_collection = quizzes_collection
        self.saved_quizzes_collection = saved_quizzes_collection
        self.legacy_resolution_service = LegacyQuizResolutionService(
            canonical_service=canonical_service,
            ai_generated_quizzes_collection=ai_generated_quizzes_collection,
            quizzes_collection=quizzes_collection,
        )

    def _build_structure_fingerprint(self, *, title: str, quiz_type: str, questions: list[Any]) -> str:
        normalized_questions = self.canonical_service.normalize_questions(questions)
        structure_payload = {
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
        return self.canonical_service.build_content_fingerprint(structure_payload)

    async def resolve_from_canonical_backref(self, canonical_quiz_id: str | None):
        return await self.legacy_resolution_service.resolve_from_canonical_backref(canonical_quiz_id)

    async def resolve_from_source_quiz_id(self, source_quiz_id: str | None):
        return await self.legacy_resolution_service.resolve_from_source_quiz_id(source_quiz_id)

    async def resolve_from_payload(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
        description: str | None = None,
        allow_create: bool = False,
    ):
        normalized_questions = self.canonical_service.normalize_questions(questions)
        has_complete_answers = all(question.get("correct_answer") for question in normalized_questions)
        if not has_complete_answers:
            canonical_quiz = await self.legacy_resolution_service.resolve_from_legacy_structure(
                title=title,
                quiz_type=quiz_type,
                questions=questions,
                allow_create=allow_create,
            )
            if canonical_quiz:
                return canonical_quiz
            canonical_quiz = await self.legacy_resolution_service.resolve_existing_v2_from_question_structure(
                title=title,
                quiz_type=quiz_type,
                questions=questions,
            )
            if canonical_quiz:
                return canonical_quiz
            structure_fingerprint = self._build_structure_fingerprint(
                title=title,
                quiz_type=quiz_type,
                questions=questions,
            )
            return await self.canonical_service.repository.find_by_structure_fingerprint(structure_fingerprint)

        quiz_document = self.canonical_service.build_quiz_document(
            title=title,
            description=description,
            quiz_type=quiz_type,
            questions=questions,
            source="legacy",
        )
        existing = await self.canonical_service.repository.find_by_content_fingerprint(
            quiz_document.content_fingerprint
        )
        if existing:
            return existing
        existing = await self.legacy_resolution_service.resolve_existing_v2_from_question_structure(
            title=title,
            quiz_type=quiz_type,
            questions=questions,
        )
        if existing:
            return existing
        existing = await self.canonical_service.repository.find_by_structure_fingerprint(
            quiz_document.structure_fingerprint
        )
        if existing:
            return existing
        if allow_create:
            return await self.canonical_service.find_or_create_quiz_v2_by_fingerprint(quiz_document)
        return None

    async def resolve_saved_quiz(self, legacy_saved_doc: dict, *, allow_create: bool = False):
        canonical_quiz = await self.resolve_from_canonical_backref(
            legacy_saved_doc.get("canonical_quiz_id")
        )
        if canonical_quiz:
            return canonical_quiz
        canonical_quiz = await self.resolve_from_source_quiz_id(legacy_saved_doc.get("quiz_id"))
        if canonical_quiz:
            return canonical_quiz
        canonical_quiz = await self.legacy_resolution_service.resolve_from_legacy_structure(
            title=legacy_saved_doc["title"],
            quiz_type=legacy_saved_doc["question_type"],
            questions=legacy_saved_doc["questions"],
            allow_create=allow_create,
        )
        if canonical_quiz:
            return canonical_quiz
        return await self.resolve_from_payload(
            title=legacy_saved_doc["title"],
            quiz_type=legacy_saved_doc["question_type"],
            questions=legacy_saved_doc["questions"],
            allow_create=False,
        )

    async def resolve_quiz_history(self, legacy_history_doc: dict, *, allow_create: bool = True):
        canonical_quiz = await self.resolve_from_canonical_backref(
            legacy_history_doc.get("canonical_quiz_id")
        )
        if canonical_quiz:
            return canonical_quiz
        canonical_quiz = await self.resolve_from_source_quiz_id(legacy_history_doc.get("quiz_id"))
        if canonical_quiz:
            return canonical_quiz
        return await self.resolve_from_payload(
            title=self.legacy_resolution_service.choose_preferred_title(
                title=legacy_history_doc.get("quiz_name"),
                fallback_title=legacy_history_doc.get("profession"),
                quiz_type=legacy_history_doc.get("question_type"),
                default="Quiz History",
            ),
            description=legacy_history_doc.get("custom_instruction"),
            quiz_type=legacy_history_doc["question_type"],
            questions=legacy_history_doc["questions"],
            allow_create=allow_create,
        )

    async def resolve_folder_item(self, legacy_folder_item: dict, *, allow_create: bool = False):
        canonical_quiz = await self.resolve_from_canonical_backref(
            legacy_folder_item.get("canonical_quiz_id")
        )
        if canonical_quiz:
            return canonical_quiz

        for source_id in (
            legacy_folder_item.get("quiz_id"),
            legacy_folder_item.get("quiz_data", {}).get("quiz_id"),
        ):
            canonical_quiz = await self.resolve_from_source_quiz_id(source_id)
            if canonical_quiz:
                return canonical_quiz

        original_saved_quiz_id = legacy_folder_item.get("original_quiz_id")
        if original_saved_quiz_id:
            from bson import ObjectId
            try:
                saved_doc = await self.saved_quizzes_collection.find_one(
                    {"_id": ObjectId(original_saved_quiz_id)}
                )
            except Exception:
                saved_doc = None
            if saved_doc:
                canonical_quiz = await self.resolve_saved_quiz(saved_doc, allow_create=allow_create)
                if canonical_quiz:
                    return canonical_quiz

        quiz_payload = legacy_folder_item.get("quiz_data", {})
        return await self.resolve_from_payload(
            title=legacy_folder_item.get("title") or quiz_payload.get("title") or "Untitled Quiz",
            quiz_type=legacy_folder_item.get("question_type")
            or quiz_payload.get("question_type")
            or "multichoice",
            questions=legacy_folder_item.get("questions")
            or quiz_payload.get("questions", []),
            allow_create=allow_create,
        )
