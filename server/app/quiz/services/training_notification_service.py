from datetime import datetime, timezone
import logging
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne

from server.app.notifications.repository import create_notification
from server.app.notifications.schemas import NotificationCreate, NotificationType
from server.app.users.identity import normalize_email
from server.app.users.repository import active_user_query


logger = logging.getLogger(__name__)


class TrainingNotificationService:
    """Creates idempotent in-app notifications for accountable training events."""

    def __init__(
        self,
        users_collection: AsyncIOMotorCollection,
        notifications_collection: AsyncIOMotorCollection,
        runs_collection: AsyncIOMotorCollection,
    ):
        self.users_collection = users_collection
        self.notifications_collection = notifications_collection
        self.runs_collection = runs_collection

    async def verified_user_ids_by_email(self, emails: list[str]) -> dict[str, str]:
        normalized = sorted({normalize_email(email) for email in emails if email})
        if not normalized:
            return {}
        cursor = self.users_collection.find(
            active_user_query(
                {"email_normalized": {"$in": normalized}, "is_verified": True}
            ),
            {"email_normalized": 1},
        )
        users = await cursor.to_list(length=len(normalized))
        return {
            normalize_email(user["email_normalized"]): str(user["_id"])
            for user in users
        }

    async def notify_assignment(self, assignment: dict, run: dict, user_id: str) -> None:
        await create_notification(
            self.notifications_collection,
            NotificationCreate(
                user_id=user_id,
                title="Training assigned",
                message=(
                    f"{run['title']} is assigned to you. "
                    f"Complete it before {run['closes_at'].strftime('%d %b %Y, %H:%M UTC')}."
                ),
                type=NotificationType.TRAINING,
                action_url="/assigned-training",
                dedupe_key=f"training-assignment:{assignment['_id']}:assigned",
            ),
        )

    async def notify_assignments(self, assignments: list[dict], run: dict) -> None:
        """Create known-recipient assignment notifications in one idempotent write."""
        now = datetime.now(timezone.utc)
        operations = []
        for assignment in assignments:
            user_id = assignment.get("recipient_user_id")
            if not user_id:
                continue
            document = {
                "user_id": user_id,
                "title": "Training assigned",
                "message": (
                    f"{run['title']} is assigned to you. "
                    f"Complete it before {run['closes_at'].strftime('%d %b %Y, %H:%M UTC')}."
                ),
                "type": NotificationType.TRAINING.value,
                "action_url": "/assigned-training",
                "dedupe_key": f"training-assignment:{assignment['_id']}:assigned",
                "expires_at": None,
                "read": False,
                "created_at": now,
            }
            operations.append(
                UpdateOne(
                    {"dedupe_key": document["dedupe_key"]},
                    {"$setOnInsert": document},
                    upsert=True,
                )
            )
        if operations:
            try:
                await self.notifications_collection.bulk_write(operations, ordered=False)
            except Exception:
                # In-app alerts supplement the durable assignment and must not
                # make a successfully-created training run appear to have failed.
                logger.exception("Could not create training assignment notifications")

    async def notify_completion(self, assignment: dict) -> None:
        user_id = assignment.get("recipient_user_id")
        if not user_id:
            return
        run = await self.runs_collection.find_one({"_id": self._object_id(assignment["training_run_id"])})
        if not run:
            return
        percentage = assignment.get("latest_percentage")
        score = f" Your score: {percentage}%" if percentage is not None else ""
        await create_notification(
            self.notifications_collection,
            NotificationCreate(
                user_id=user_id,
                title="Training completed",
                message=f"You completed {run['title']}.{score}",
                type=NotificationType.TRAINING,
                action_url="/assigned-training",
                dedupe_key=f"training-assignment:{assignment['_id']}:completed",
            ),
        )

    async def notify_run_owner_of_completion(
        self, session: dict, assignment: Optional[dict] = None
    ) -> None:
        run_id = session.get("training_run_id")
        run_object_id = self._object_id(run_id)
        if not run_id or not run_object_id:
            return
        run = await self.runs_collection.find_one({"_id": run_object_id})
        owner_user_id = run.get("owner_user_id") if run else None
        if not owner_user_id:
            return

        participant = (
            assignment.get("recipient_email")
            if assignment
            else session.get("participant_name") or session.get("participant_email")
        )
        participant = participant or "A participant"
        percentage = session.get("percentage")
        score = f" Score: {percentage}%" if percentage is not None else ""
        await create_notification(
            self.notifications_collection,
            NotificationCreate(
                user_id=owner_user_id,
                title="Training completed",
                message=f"{participant} completed {run['title']}.{score}",
                type=NotificationType.TRAINING,
                action_url=f"/training-runs/{run_id}",
                dedupe_key=f"training-run:{run_id}:session:{session['_id']}:owner-completed",
            ),
        )

    @staticmethod
    def _object_id(value: Optional[str]) -> Optional[ObjectId]:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None
