"""Persistence for an individual delivery of a live quiz.

A quiz is reusable content; a run is the time-bounded delivery whose results
form the compliance record.  Runs deliberately snapshot the pass threshold.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection


class LiveQuizRunRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def create(self, run: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {**run, "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(payload)
        return str(result.inserted_id)

    async def get(self, run_id: str) -> Optional[dict[str, Any]]:
        try:
            return await self.collection.find_one({"_id": ObjectId(run_id)})
        except InvalidId:
            return None

    async def get_by_access_code(self, access_code: str) -> Optional[dict[str, Any]]:
        # Codes can be reused after expiry. The active delivery is always the
        # newest run with this code, while older records remain auditable.
        return await self.collection.find_one(
            {"access_code": access_code.strip().upper()},
            sort=[("created_at", -1)],
        )

    async def latest_for_quiz(self, quiz_id: str, creator_user_id: str) -> Optional[dict[str, Any]]:
        return await self.collection.find_one(
            {"quiz_id": quiz_id, "creator_user_id": creator_user_id},
            sort=[("created_at", -1)],
        )
