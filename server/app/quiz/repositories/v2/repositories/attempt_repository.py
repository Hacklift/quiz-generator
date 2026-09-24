from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection

from ..models.reference_models import QuizAttemptDocumentV2


class QuizAttemptV2Repository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    @staticmethod
    def _active_query() -> dict:
        return {"$or": [{"deleted_at": {"$exists": False}}, {"deleted_at": None}]}

    async def insert_attempt(self, attempt: QuizAttemptDocumentV2) -> QuizAttemptDocumentV2:
        payload = attempt.model_dump(by_alias=True)
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return QuizAttemptDocumentV2(**payload)

    async def list_attempts_for_user(
        self,
        user_id: str,
        *,
        quiz_id: str | None = None,
        limit: int = 100,
    ) -> list[QuizAttemptDocumentV2]:
        query: dict[str, object] = {"user_id": user_id}
        if quiz_id is not None:
            query["quiz_id"] = quiz_id
        documents = await self.collection.find(
            {"$and": [query, self._active_query()]}
        ).sort([("submitted_at", -1), ("_id", -1)]).to_list(length=limit)
        return [QuizAttemptDocumentV2(**document) for document in documents]

    async def get_attempt_by_id(
        self,
        attempt_id: str,
        *,
        user_id: str | None = None,
    ) -> QuizAttemptDocumentV2 | None:
        query: dict[str, object] = {}
        try:
            query["_id"] = ObjectId(attempt_id)
        except InvalidId:
            return None
        if user_id is not None:
            query["user_id"] = user_id
        document = await self.collection.find_one({"$and": [query, self._active_query()]})
        return QuizAttemptDocumentV2(**document) if document else None

    async def soft_delete_attempt_by_id(
        self,
        attempt_id: str,
        *,
        user_id: str | None = None,
    ) -> int:
        query: dict[str, object] = {}
        try:
            query["_id"] = ObjectId(attempt_id)
        except InvalidId:
            return 0
        if user_id is not None:
            query["user_id"] = user_id
        result = await self.collection.update_one(
            {"$and": [query, self._active_query()]},
            {"$set": {"deleted_at": datetime.utcnow()}},
        )
        return result.modified_count
