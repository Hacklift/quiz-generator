from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.db.crud.quiz_write_service import CanonicalQuizWriteService


@dataclass
class LegacySourceQuizMatch:
    source_collection: str
    legacy_quiz_id: str
    document: dict[str, Any]


class LegacyQuizStructureConflictError(ValueError):
    def __init__(
        self,
        *,
        title: str,
        quiz_type: str,
        candidates: list[dict[str, Any]],
    ):
        self.title = title
        self.quiz_type = quiz_type
        self.candidates = candidates
        candidate_ids = ", ".join(
            candidate.get("legacy_quiz_id") or candidate.get("canonical_quiz_id") or "unknown"
            for candidate in candidates
        )
        super().__init__(
            f"Multiple legacy source matches for '{title}' ({quiz_type}): {candidate_ids}"
        )

    def to_log_fields(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "quiz_type": self.quiz_type,
            "candidate_ids": [
                candidate.get("legacy_quiz_id") or candidate.get("canonical_quiz_id")
                for candidate in self.candidates
            ],
            "candidates": self.candidates,
        }


class LegacyQuizResolutionService:
    def __init__(
        self,
        *,
        canonical_service: CanonicalQuizWriteService,
        ai_generated_quizzes_collection: AsyncIOMotorCollection,
        quizzes_collection: AsyncIOMotorCollection,
    ):
        self.canonical_service = canonical_service
        self.ai_generated_quizzes_collection = ai_generated_quizzes_collection
        self.quizzes_collection = quizzes_collection

    @staticmethod
    def _coerce_object_id(value: str | None):
        if not value:
            return None
        try:
            return ObjectId(value)
        except Exception:
            return None

    @staticmethod
    def _normalize_title(value: str | None) -> str:
        if not value:
            return ""
        normalized = re.sub(r"\s+", " ", value.strip().casefold())
        if normalized.endswith(" quiz"):
            normalized = normalized[:-5].strip()
        return normalized

    @staticmethod
    def _candidate_display_title(document: dict[str, Any]) -> str:
        return document.get("profession") or document.get("title") or "Untitled Quiz"

    @classmethod
    def is_generic_quiz_title(cls, title: str | None, quiz_type: str | None = None) -> bool:
        normalized_title = cls._normalize_title(title)
        if not normalized_title:
            return True
        generic_titles = {"quiz history"}
        if quiz_type:
            generic_titles.add(cls._normalize_title(f"{quiz_type} Quiz"))
        return normalized_title in generic_titles

    @classmethod
    def choose_preferred_title(
        cls,
        *,
        title: str | None,
        fallback_title: str | None = None,
        quiz_type: str | None = None,
        default: str = "Untitled Quiz",
    ) -> str:
        if title and not cls.is_generic_quiz_title(title, quiz_type):
            return title.strip()
        if fallback_title and fallback_title.strip():
            return fallback_title.strip()
        if title and title.strip():
            return title.strip()
        return default

    def _build_question_structure_fingerprint(self, *, quiz_type: str, questions: list[Any]) -> str:
        normalized_questions = self.canonical_service.normalize_questions(questions)
        structure_payload = {
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
        if not canonical_quiz_id:
            return None
        return await self.canonical_service.get_quiz_v2_by_id(canonical_quiz_id)

    async def resolve_from_source_quiz_id(self, source_quiz_id: str | None):
        if not source_quiz_id:
            return None

        for collection_name in ("ai_generated_quizzes", "quizzes"):
            canonical_quiz = await self.canonical_service.repository.find_by_legacy_mapping(
                collection_name,
                source_quiz_id,
            )
            if canonical_quiz:
                return canonical_quiz

        object_id = self._coerce_object_id(source_quiz_id)

        legacy_ai = await self.ai_generated_quizzes_collection.find_one(
            {"_id": object_id if object_id is not None else source_quiz_id}
        )
        if legacy_ai and legacy_ai.get("canonical_quiz_id"):
            canonical_quiz = await self.resolve_from_canonical_backref(legacy_ai["canonical_quiz_id"])
            if canonical_quiz:
                return canonical_quiz

        legacy_manual = await self.quizzes_collection.find_one(
            {"_id": object_id if object_id is not None else source_quiz_id}
        )
        if legacy_manual and legacy_manual.get("canonical_quiz_id"):
            return await self.resolve_from_canonical_backref(legacy_manual["canonical_quiz_id"])

        return None

    async def _find_structure_candidates(
        self,
        *,
        collection_name: str,
        collection: AsyncIOMotorCollection,
        target_fingerprint: str,
        quiz_type: str,
    ) -> list[LegacySourceQuizMatch]:
        candidates: list[LegacySourceQuizMatch] = []
        async for document in collection.find(
            {"question_type": quiz_type},
            {
                "_id": 1,
                "profession": 1,
                "title": 1,
                "question_type": 1,
                "quiz_type": 1,
                "questions": 1,
                "custom_instruction": 1,
                "description": 1,
                "user_id": 1,
                "owner_id": 1,
                "canonical_quiz_id": 1,
            },
        ):
            candidate_type = document.get("question_type") or document.get("quiz_type") or "multichoice"
            candidate_fingerprint = self._build_question_structure_fingerprint(
                quiz_type=candidate_type,
                questions=document.get("questions", []),
            )
            if candidate_fingerprint != target_fingerprint:
                continue
            candidates.append(
                LegacySourceQuizMatch(
                    source_collection=collection_name,
                    legacy_quiz_id=str(document["_id"]),
                    document=document,
                )
            )
        return candidates

    def _candidate_log_payload(self, match: LegacySourceQuizMatch) -> dict[str, Any]:
        return {
            "legacy_source_collection": match.source_collection,
            "legacy_quiz_id": match.legacy_quiz_id,
            "title": self._candidate_display_title(match.document),
        }

    def _v2_candidate_log_payload(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "canonical_quiz_id": str(document["_id"]),
            "title": document.get("title"),
        }

    def _select_preferred_candidate(
        self,
        *,
        title: str,
        candidates: list[LegacySourceQuizMatch],
    ) -> LegacySourceQuizMatch | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        normalized_title = self._normalize_title(title)
        if normalized_title:
            title_matches = [
                candidate
                for candidate in candidates
                if self._normalize_title(self._candidate_display_title(candidate.document)) == normalized_title
            ]
            if len(title_matches) == 1:
                return title_matches[0]
            if len(title_matches) > 1:
                raise LegacyQuizStructureConflictError(
                    title=title,
                    quiz_type=candidates[0].document.get("question_type")
                    or candidates[0].document.get("quiz_type")
                    or "multichoice",
                    candidates=[self._candidate_log_payload(candidate) for candidate in title_matches],
                )

        raise LegacyQuizStructureConflictError(
            title=title,
            quiz_type=candidates[0].document.get("question_type")
            or candidates[0].document.get("quiz_type")
            or "multichoice",
            candidates=[self._candidate_log_payload(candidate) for candidate in candidates],
        )

    async def find_legacy_source_match_by_structure(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
    ) -> LegacySourceQuizMatch | None:
        target_fingerprint = self._build_question_structure_fingerprint(
            quiz_type=quiz_type,
            questions=questions,
        )
        ai_candidates = await self._find_structure_candidates(
            collection_name="ai_generated_quizzes",
            collection=self.ai_generated_quizzes_collection,
            target_fingerprint=target_fingerprint,
            quiz_type=quiz_type,
        )
        selected = self._select_preferred_candidate(title=title, candidates=ai_candidates)
        if selected:
            return selected

        manual_candidates = await self._find_structure_candidates(
            collection_name="quizzes",
            collection=self.quizzes_collection,
            target_fingerprint=target_fingerprint,
            quiz_type=quiz_type,
        )
        return self._select_preferred_candidate(title=title, candidates=manual_candidates)

    async def resolve_or_build_from_legacy_source_match(
        self,
        match: LegacySourceQuizMatch,
        *,
        allow_create: bool,
    ):
        existing = await self.canonical_service.repository.find_by_legacy_mapping(
            match.source_collection,
            match.legacy_quiz_id,
        )
        if existing:
            return existing

        if match.document.get("canonical_quiz_id"):
            canonical_quiz = await self.resolve_from_canonical_backref(match.document["canonical_quiz_id"])
            if canonical_quiz:
                return canonical_quiz

        quiz_document = self.canonical_service.build_quiz_document(
            title=self._candidate_display_title(match.document),
            description=match.document.get("custom_instruction") or match.document.get("description"),
            quiz_type=match.document.get("question_type") or match.document.get("quiz_type") or "multichoice",
            owner_user_id=match.document.get("user_id") or match.document.get("owner_id"),
            source="ai" if match.source_collection == "ai_generated_quizzes" else "legacy",
            questions=match.document.get("questions", []),
            legacy_source_collection=match.source_collection,
            legacy_quiz_id=match.legacy_quiz_id,
        )
        if allow_create:
            return await self.canonical_service.upsert_quiz_v2_by_legacy_mapping(quiz_document)
        return quiz_document

    async def resolve_from_legacy_structure(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
        allow_create: bool,
    ):
        match = await self.find_legacy_source_match_by_structure(
            title=title,
            quiz_type=quiz_type,
            questions=questions,
        )
        if not match:
            return None
        return await self.resolve_or_build_from_legacy_source_match(
            match,
            allow_create=allow_create,
        )

    async def resolve_existing_v2_from_question_structure(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
    ):
        target_fingerprint = self._build_question_structure_fingerprint(
            quiz_type=quiz_type,
            questions=questions,
        )
        candidates: list[dict[str, Any]] = []
        async for document in self.canonical_service.repository.collection.find(
            {"quiz_type": quiz_type, "status": {"$ne": "deleted"}},
            {"_id": 1, "title": 1, "quiz_type": 1, "questions": 1},
        ):
            candidate_fingerprint = self._build_question_structure_fingerprint(
                quiz_type=document.get("quiz_type") or "multichoice",
                questions=document.get("questions", []),
            )
            if candidate_fingerprint != target_fingerprint:
                continue
            candidates.append(document)

        if not candidates:
            return None
        if len(candidates) == 1:
            return await self.canonical_service.get_quiz_v2_by_id(str(candidates[0]["_id"]))

        normalized_title = self._normalize_title(title)
        if normalized_title:
            title_matches = [
                candidate
                for candidate in candidates
                if self._normalize_title(candidate.get("title")) == normalized_title
            ]
            if len(title_matches) == 1:
                return await self.canonical_service.get_quiz_v2_by_id(str(title_matches[0]["_id"]))
            if len(title_matches) > 1:
                raise LegacyQuizStructureConflictError(
                    title=title,
                    quiz_type=quiz_type,
                    candidates=[self._v2_candidate_log_payload(candidate) for candidate in title_matches],
                )

        raise LegacyQuizStructureConflictError(
            title=title,
            quiz_type=quiz_type,
            candidates=[self._v2_candidate_log_payload(candidate) for candidate in candidates],
        )
