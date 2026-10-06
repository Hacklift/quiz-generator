from motor.motor_asyncio import AsyncIOMotorCollection

from ..models.attempt_models import QuizAttemptDocumentV2


class QuizAttemptV2Repository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def insert_attempt(
        self, attempt: QuizAttemptDocumentV2
    ) -> QuizAttemptDocumentV2:
        payload = attempt.model_dump(by_alias=True)
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return QuizAttemptDocumentV2(**payload)
