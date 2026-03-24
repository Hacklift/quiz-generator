from datetime import datetime
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ..models.quiz_models import QuizDocumentV2, QuizMetadataUpdateV2, QuizQuestionsUpdateV2


class QuizV2Repository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def insert_quiz(self, quiz: QuizDocumentV2) -> QuizDocumentV2:
        payload = quiz.model_dump(by_alias=True)
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return QuizDocumentV2(**payload)

    async def find_by_legacy_mapping(
        self,
        legacy_source_collection: str,
        legacy_quiz_id: str,
    ) -> Optional[QuizDocumentV2]:
        document = await self.collection.find_one(
            {
                "legacy_source_collection": legacy_source_collection,
                "legacy_quiz_id": legacy_quiz_id,
            }
        )
        return QuizDocumentV2(**document) if document else None

    async def find_by_content_fingerprint(self, content_fingerprint: str) -> Optional[QuizDocumentV2]:
        document = await self.collection.find_one({"content_fingerprint": content_fingerprint})
        return QuizDocumentV2(**document) if document else None

    async def find_by_structure_fingerprint(self, structure_fingerprint: str) -> Optional[QuizDocumentV2]:
        document = await self.collection.find_one({"structure_fingerprint": structure_fingerprint})
        return QuizDocumentV2(**document) if document else None

    async def list_by_title_and_quiz_type(self, title: str, quiz_type: str) -> list[QuizDocumentV2]:
        cursor = self.collection.find({"title": title, "quiz_type": quiz_type, "status": {"$ne": "deleted"}})
        documents = await cursor.to_list(length=20)
        return [QuizDocumentV2(**document) for document in documents]

    async def upsert_by_legacy_mapping(self, quiz: QuizDocumentV2) -> QuizDocumentV2:
        payload = quiz.model_dump(by_alias=True)
        payload.pop("_id", None)
        updated = await self.collection.find_one_and_update(
            {
                "legacy_source_collection": quiz.legacy_source_collection,
                "legacy_quiz_id": quiz.legacy_quiz_id,
            },
            {"$set": payload},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            return QuizDocumentV2(**updated)

        stored = await self.collection.find_one(
            {
                "legacy_source_collection": quiz.legacy_source_collection,
                "legacy_quiz_id": quiz.legacy_quiz_id,
            }
        )
        return QuizDocumentV2(**stored)

    async def find_or_create_by_fingerprint(self, quiz: QuizDocumentV2) -> QuizDocumentV2:
        existing = await self.find_by_content_fingerprint(quiz.content_fingerprint)
        if existing:
            return existing
        try:
            return await self.insert_quiz(quiz)
        except DuplicateKeyError:
            existing = await self.find_by_content_fingerprint(quiz.content_fingerprint)
            if existing:
                return existing
            raise

    async def find_by_id(self, quiz_id: str) -> Optional[QuizDocumentV2]:
        try:
            document = await self.collection.find_one({"_id": ObjectId(quiz_id)})
        except InvalidId:
            return None
        return QuizDocumentV2(**document) if document else None

    async def update_metadata(
        self,
        quiz_id: str,
        update: QuizMetadataUpdateV2,
    ) -> Optional[QuizDocumentV2]:
        try:
            updated = await self.collection.find_one_and_update(
                {"_id": ObjectId(quiz_id)},
                {
                    "$set": {
                        **update.model_dump(exclude_unset=True),
                        "updated_at": datetime.utcnow(),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None
        return QuizDocumentV2(**updated) if updated else None

    async def update_questions(
        self,
        quiz_id: str,
        update: QuizQuestionsUpdateV2,
    ) -> Optional[QuizDocumentV2]:
        try:
            updated = await self.collection.find_one_and_update(
                {"_id": ObjectId(quiz_id)},
                {
                    "$set": {
                        "questions": [
                            question.model_dump() for question in update.questions
                        ],
                        "updated_at": datetime.utcnow(),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None
        return QuizDocumentV2(**updated) if updated else None

    async def soft_delete(self, quiz_id: str) -> Optional[QuizDocumentV2]:
        try:
            updated = await self.collection.find_one_and_update(
                {"_id": ObjectId(quiz_id), "status": {"$ne": "deleted"}},
                {
                    "$set": {
                        "status": "deleted",
                        "updated_at": datetime.utcnow(),
                        "deleted_at": datetime.utcnow(),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            return None
        return QuizDocumentV2(**updated) if updated else None

    async def soft_delete_by_legacy_mapping(
        self,
        legacy_source_collection: str,
        legacy_quiz_id: str,
    ) -> Optional[QuizDocumentV2]:
        updated = await self.collection.find_one_and_update(
            {
                "legacy_source_collection": legacy_source_collection,
                "legacy_quiz_id": legacy_quiz_id,
                "status": {"$ne": "deleted"},
            },
            {
                "$set": {
                    "status": "deleted",
                    "updated_at": datetime.utcnow(),
                    "deleted_at": datetime.utcnow(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return QuizDocumentV2(**updated) if updated else None
