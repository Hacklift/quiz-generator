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

    async def find_by_access_code(self, access_code: str) -> Optional[QuizDocumentV2]:
        document = await self.collection.find_one({"access_code": access_code})
        return QuizDocumentV2(**document) if document else None

    async def access_code_exists(self, access_code: str) -> bool:
        return await self.collection.count_documents({"access_code": access_code}, limit=1) > 0

    async def list_by_title_and_quiz_type(self, title: str, quiz_type: str) -> list[QuizDocumentV2]:
        cursor = self.collection.find({"title": title, "quiz_type": quiz_type, "status": {"$ne": "deleted"}})
        documents = await cursor.to_list(length=20)
        return [QuizDocumentV2(**document) for document in documents]

    async def list_category_values(self) -> list[str]:
        values = await self.collection.distinct(
            "category",
            {
                "category": {"$type": "string", "$ne": ""},
                "category_slug": {"$type": "string", "$ne": ""},
                "status": "active",
                "visibility": "public",
            },
        )
        return sorted(value for value in values if value)

    async def list_subcategory_values(self, category_slug: str) -> list[str]:
        values = await self.collection.distinct(
            "subcategory",
            {
                "category_slug": category_slug,
                "subcategory": {"$type": "string", "$ne": ""},
                "subcategory_slug": {"$type": "string", "$ne": ""},
                "status": "active",
                "visibility": "public",
            },
        )
        return sorted(value for value in values if value)

    async def list_quiz_types_for_category(
        self,
        *,
        category_slug: str,
        subcategory_slug: str,
    ) -> list[str]:
        values = await self.collection.distinct(
            "quiz_type",
            {
                "category_slug": category_slug,
                "subcategory_slug": subcategory_slug,
                "status": "active",
                "visibility": "public",
            },
        )
        return sorted(value for value in values if value)

    async def list_category_questions(
        self,
        *,
        category_slug: str,
        subcategory_slug: str,
        quiz_type: str,
        skip: int,
        limit: int,
    ) -> list[dict]:
        pipeline = [
            {
                "$match": {
                    "category_slug": category_slug,
                    "subcategory_slug": subcategory_slug,
                    "quiz_type": quiz_type,
                    "status": "active",
                    "visibility": "public",
                }
            },
            {"$sort": {"source": -1, "created_at": -1}},
            {"$unwind": "$questions"},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "question": "$questions.question",
                    "options": "$questions.options",
                    "answer": "$questions.correct_answer",
                    "subcategory": "$subcategory",
                    "question_type": "$quiz_type",
                }
            },
        ]
        return await self.collection.aggregate(pipeline).to_list(length=limit)

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

    async def upsert_by_legacy_mapping_with_status(
        self,
        quiz: QuizDocumentV2,
    ) -> tuple[QuizDocumentV2, str]:
        payload = quiz.model_dump(by_alias=True)
        payload.pop("_id", None)
        lookup = {
            "legacy_source_collection": quiz.legacy_source_collection,
            "legacy_quiz_id": quiz.legacy_quiz_id,
        }
        existing = await self.collection.find_one(lookup)
        if existing:
            existing_payload = dict(existing)
            existing_payload.pop("_id", None)
            existing_payload.pop("created_at", None)
            existing_payload.pop("updated_at", None)
            comparable_payload = dict(payload)
            comparable_payload.pop("created_at", None)
            comparable_payload.pop("updated_at", None)
            if existing_payload == comparable_payload:
                return QuizDocumentV2(**existing), "unchanged"
            if existing.get("created_at") is not None:
                payload["created_at"] = existing["created_at"]

        updated = await self.collection.find_one_and_update(
            lookup,
            {"$set": payload},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if updated:
            return QuizDocumentV2(**updated), "updated" if existing else "created"

        stored = await self.collection.find_one(lookup)
        return QuizDocumentV2(**stored), "updated" if existing else "created"

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

    async def find_many_by_ids(self, quiz_ids: list[str]) -> list[QuizDocumentV2]:
        object_ids: list[ObjectId] = []
        order: list[ObjectId] = []
        for quiz_id in quiz_ids:
            try:
                object_id = ObjectId(quiz_id)
            except InvalidId:
                continue
            object_ids.append(object_id)
            order.append(object_id)
        if not object_ids:
            return []
        documents = await self.collection.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
        by_id = {document["_id"]: document for document in documents}
        return [QuizDocumentV2(**by_id[object_id]) for object_id in order if object_id in by_id]

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

    async def enable_live_quiz(
        self,
        quiz_id: str,
        *,
        access_code: str,
        time_limit_minutes: int,
        access_code_expires_at: datetime,
        participant_access_mode: str = "public",
        invited_participant_emails: Optional[list[str]] = None,
    ) -> Optional[QuizDocumentV2]:
        try:
            updated = await self.collection.find_one_and_update(
                {"_id": ObjectId(quiz_id), "status": {"$ne": "deleted"}},
                {
                    "$set": {
                        "live_quiz_enabled": True,
                        "time_limit_minutes": time_limit_minutes,
                        "access_code": access_code,
                        "access_code_expires_at": access_code_expires_at,
                        "participant_access_mode": participant_access_mode,
                        "invited_participant_emails": invited_participant_emails or [],
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
