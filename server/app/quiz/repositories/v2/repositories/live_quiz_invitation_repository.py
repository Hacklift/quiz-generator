from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection


class LiveQuizInvitationRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def upsert_invitation(self, invitation: dict) -> str:
        existing = await self.collection.find_one({
            "quiz_id": invitation["quiz_id"],
            "email": invitation["email"],
        })
        if existing:
            await self.collection.update_one(
                {"_id": existing["_id"]},
                {"$set": {**invitation, "updated_at": datetime.now(timezone.utc)}},
            )
            return str(existing["_id"])
        invitation["created_at"] = datetime.now(timezone.utc)
        invitation["updated_at"] = datetime.now(timezone.utc)
        result = await self.collection.insert_one(invitation)
        return str(result.inserted_id)

    async def find_by_quiz_and_email(
        self, quiz_id: str, email: str
    ) -> Optional[dict]:
        return await self.collection.find_one({
            "quiz_id": quiz_id,
            "email": email.strip().lower(),
        })

    async def find_by_id(self, invitation_id: str) -> Optional[dict]:
        try:
            return await self.collection.find_one({"_id": ObjectId(invitation_id)})
        except InvalidId:
            return None

    async def update_status(
        self,
        quiz_id: str,
        email: str,
        status: str,
        session_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[dict]:
        update = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if session_id:
            update["session_id"] = session_id
        if name:
            update["name"] = name
        return await self.collection.find_one_and_update(
            {"quiz_id": quiz_id, "email": email.strip().lower()},
            {"$set": update},
        )

    async def update_email_delivery(
        self,
        invitation_id: str,
        *,
        email_sent: bool,
        invitation_sent_status: str,
        status: Optional[str] = None,
    ) -> None:
        update = {
            "email_sent": email_sent,
            "invitation_sent_status": invitation_sent_status,
            "updated_at": datetime.now(timezone.utc),
        }
        if email_sent:
            update["email_sent_at"] = datetime.now(timezone.utc)
        if status:
            update["status"] = status
        await self.collection.update_one(
            {"_id": ObjectId(invitation_id)},
            {"$set": update},
        )

    async def list_by_quiz(self, quiz_id: str) -> List[dict]:
        cursor = self.collection.find({"quiz_id": quiz_id}).sort("created_at", 1)
        return await cursor.to_list(length=1000)

    async def delete_by_quiz(self, quiz_id: str) -> int:
        result = await self.collection.delete_many({"quiz_id": quiz_id})
        return result.deleted_count

    async def count_by_quiz(self, quiz_id: str) -> int:
        return await self.collection.count_documents({"quiz_id": quiz_id})

    async def invitation_exists_for_quiz(self, quiz_id: str, email: str) -> bool:
        count = await self.collection.count_documents(
            {"quiz_id": quiz_id, "email": email.strip().lower()}, limit=1
        )
        return count > 0

    async def mark_email_sent(self, invitation_id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(invitation_id)},
            {
                "$set": {
                    "status": "delivered",
                    "email_sent": True,
                    "email_sent_at": datetime.now(timezone.utc),
                    "invitation_sent_status": "delivered",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

    async def ensure_indexes(self):
        await self.collection.create_index("quiz_id")
        await self.collection.create_index([("quiz_id", 1), ("email", 1)], unique=True)
        await self.collection.create_index("creator_user_id")
