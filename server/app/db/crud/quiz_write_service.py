import hashlib
import json
from datetime import datetime
from typing import Any, Optional

from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.db.v2.constants import QUIZ_SCHEMA_VERSION
from server.app.db.v2.models.quiz_models import (
    QuizCreateV2,
    QuizDocumentV2,
    QuizMetadataUpdateV2,
    QuizQuestionsUpdateV2,
)
from server.app.db.v2.repositories.quiz_repository import QuizV2Repository


class CanonicalQuizWriteService:
    def __init__(self, repository: Optional[QuizV2Repository] = None):
        self.repository = repository or QuizV2Repository(get_quizzes_v2_collection())

    @staticmethod
    def normalize_questions(questions: list[Any]) -> list[dict[str, Any]]:
        normalized_questions = []
        for question in questions:
            if hasattr(question, "model_dump"):
                raw_question = question.model_dump(exclude_none=True)
            elif hasattr(question, "dict"):
                raw_question = question.dict(exclude_none=True)
            else:
                raw_question = dict(question)

            normalized_questions.append(
                {
                    "question": raw_question.get("question"),
                    "options": raw_question.get("options"),
                    "correct_answer": raw_question.get("correct_answer") or raw_question.get("answer"),
                }
            )
        return normalized_questions

    @staticmethod
    def build_content_fingerprint(payload: dict[str, Any]) -> str:
        serializable = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serializable.encode("utf-8")).hexdigest()

    def build_quiz_document(
        self,
        *,
        title: str,
        quiz_type: str,
        questions: list[Any],
        description: str | None = None,
        owner_user_id: str | None = None,
        visibility: str = "private",
        status: str = "active",
        source: str = "legacy",
        tags: list[str] | None = None,
        legacy_source_collection: str | None = None,
        legacy_quiz_id: str | None = None,
    ) -> QuizDocumentV2:
        normalized_questions = self.normalize_questions(questions)
        quiz_create = QuizCreateV2(
            title=title.strip(),
            description=description,
            quiz_type=quiz_type,
            owner_user_id=owner_user_id,
            visibility=visibility,
            status=status,
            source=source,
            tags=tags or [],
            questions=normalized_questions,
        )
        fingerprint_payload = {
            "title": quiz_create.title,
            "description": quiz_create.description,
            "quiz_type": quiz_create.quiz_type,
            "questions": [question.model_dump(exclude_none=True) for question in quiz_create.questions],
        }
        structure_payload = {
            "title": quiz_create.title,
            "quiz_type": quiz_create.quiz_type,
            "questions": [
                {
                    "question": question.question,
                    "options": question.options,
                }
                for question in quiz_create.questions
            ],
        }
        now = datetime.utcnow()
        return QuizDocumentV2(
            title=quiz_create.title,
            description=quiz_create.description,
            quiz_type=quiz_create.quiz_type,
            owner_user_id=quiz_create.owner_user_id,
            visibility=quiz_create.visibility,
            status=quiz_create.status,
            source=quiz_create.source,
            questions=quiz_create.questions,
            tags=[tag.strip() for tag in quiz_create.tags if tag.strip()],
            legacy_source_collection=legacy_source_collection,
            legacy_quiz_id=legacy_quiz_id,
            content_fingerprint=self.build_content_fingerprint(fingerprint_payload),
            structure_fingerprint=self.build_content_fingerprint(structure_payload),
            schema_version=QUIZ_SCHEMA_VERSION,
            created_at=now,
            updated_at=now,
        )

    async def create_quiz_v2(self, quiz_data: QuizCreateV2) -> QuizDocumentV2:
        quiz_document = self.build_quiz_document(
            title=quiz_data.title,
            description=quiz_data.description,
            quiz_type=quiz_data.quiz_type,
            owner_user_id=quiz_data.owner_user_id,
            visibility=quiz_data.visibility,
            status=quiz_data.status,
            source=quiz_data.source,
            questions=quiz_data.questions,
            tags=quiz_data.tags,
        )
        return await self.repository.insert_quiz(quiz_document)

    async def upsert_quiz_v2_by_legacy_mapping(self, quiz_document: QuizDocumentV2) -> QuizDocumentV2:
        return await self.repository.upsert_by_legacy_mapping(quiz_document)

    async def find_or_create_quiz_v2_by_fingerprint(self, quiz_document: QuizDocumentV2) -> QuizDocumentV2:
        return await self.repository.find_or_create_by_fingerprint(quiz_document)

    async def update_quiz_metadata_v2(
        self,
        quiz_id: str,
        update_data: QuizMetadataUpdateV2,
    ) -> Optional[QuizDocumentV2]:
        return await self.repository.update_metadata(quiz_id, update_data)

    async def update_quiz_questions_v2(
        self,
        quiz_id: str,
        update_data: QuizQuestionsUpdateV2,
    ) -> Optional[QuizDocumentV2]:
        return await self.repository.update_questions(quiz_id, update_data)

    async def get_quiz_v2_by_id(self, quiz_id: str) -> Optional[QuizDocumentV2]:
        return await self.repository.find_by_id(quiz_id)

    async def soft_delete_quiz_v2(self, quiz_id: str) -> Optional[QuizDocumentV2]:
        return await self.repository.soft_delete(quiz_id)

    async def soft_delete_quiz_v2_by_legacy_mapping(
        self,
        legacy_source_collection: str,
        legacy_quiz_id: str,
    ) -> Optional[QuizDocumentV2]:
        return await self.repository.soft_delete_by_legacy_mapping(
            legacy_source_collection,
            legacy_quiz_id,
        )
