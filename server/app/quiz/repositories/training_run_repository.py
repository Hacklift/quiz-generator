from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError


class TrainingRunRepository:
    """Persistence for delivery events, their obligations, and audit snapshots."""

    def __init__(
        self,
        quizzes_collection: AsyncIOMotorCollection,
        runs_collection: AsyncIOMotorCollection,
        assignments_collection: AsyncIOMotorCollection,
        audit_events_collection: AsyncIOMotorCollection,
        sessions_collection: Optional[AsyncIOMotorCollection] = None,
        email_deliveries_collection: Optional[AsyncIOMotorCollection] = None,
    ):
        self.quizzes_collection = quizzes_collection
        self.runs_collection = runs_collection
        self.assignments_collection = assignments_collection
        self.audit_events_collection = audit_events_collection
        self.sessions_collection = sessions_collection
        self.email_deliveries_collection = email_deliveries_collection

    @staticmethod
    def _object_id(value: str) -> Optional[ObjectId]:
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None

    async def get_owned_quiz(self, quiz_id: str, owner_user_id: str) -> Optional[dict]:
        object_id = self._object_id(quiz_id)
        if not object_id:
            return None
        return await self.quizzes_collection.find_one(
            {
                "_id": object_id,
                "owner_user_id": owner_user_id,
                "status": {"$ne": "deleted"},
            }
        )

    async def list_owned_quizzes(self, owner_user_id: str, limit: int = 100) -> list[dict]:
        cursor = self.quizzes_collection.find(
            {"owner_user_id": owner_user_id, "status": {"$ne": "deleted"}},
            {"title": 1, "created_at": 1, "quiz_type": 1},
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def access_code_exists_on_quiz(self, access_code: str) -> bool:
        return bool(await self.quizzes_collection.find_one({"access_code": access_code}, {"_id": 1}))

    async def access_code_exists_on_run(self, access_code: str) -> bool:
        return bool(await self.runs_collection.find_one({"access_code": access_code}, {"_id": 1}))

    async def create_run(self, payload: dict) -> dict:
        result = await self.runs_collection.insert_one(payload)
        return {**payload, "_id": result.inserted_id}

    async def get_run_by_idempotency_key(
        self, owner_user_id: str, idempotency_key: str
    ) -> Optional[dict]:
        return await self.runs_collection.find_one(
            {"owner_user_id": owner_user_id, "idempotency_key": idempotency_key}
        )

    async def mark_run_open(self, run_id: str, now: datetime) -> Optional[dict]:
        object_id = self._object_id(run_id)
        if not object_id:
            return None
        return await self.runs_collection.find_one_and_update(
            {"_id": object_id, "status": "provisioning"},
            {"$set": {"status": "open", "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def mark_provisioning_complete(self, run_id: str, now: datetime) -> None:
        object_id = self._object_id(run_id)
        if not object_id:
            return
        await self.runs_collection.update_one(
            {"_id": object_id, "status": "open"},
            {
                "$set": {
                    "provisioning_complete": True,
                    "updated_at": now,
                }
            },
        )

    async def get_run(self, run_id: str) -> Optional[dict]:
        object_id = self._object_id(run_id)
        return await self.runs_collection.find_one({"_id": object_id}) if object_id else None

    async def get_run_by_access_code(self, access_code: str) -> Optional[dict]:
        return await self.runs_collection.find_one({"access_code": access_code.strip().upper()})

    async def list_runs_for_owner(self, owner_user_id: str, limit: int = 100) -> list[dict]:
        cursor = self.runs_collection.find(
            {"owner_user_id": owner_user_id, "status": {"$in": ["open", "closed"]}}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def claim_run_closure(
        self, run_id: str, owner_user_id: Optional[str], started_at: datetime
    ) -> Optional[dict]:
        """Claim finalization before changing the visible run status."""
        object_id = self._object_id(run_id)
        if not object_id:
            return None
        query: dict[str, Any] = {
            "_id": object_id,
            "status": "open",
            "closure_in_progress": {"$ne": True},
        }
        if owner_user_id:
            query["owner_user_id"] = owner_user_id
        return await self.runs_collection.find_one_and_update(
            query,
            {
                "$set": {
                    "closure_in_progress": True,
                    "closure_started_at": started_at,
                    "closure_mode": "manual" if owner_user_id else "scheduled",
                    "closure_actor_user_id": owner_user_id,
                    "updated_at": started_at,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def finalize_run_closure(
        self, run_id: str, owner_user_id: Optional[str], closed_at: datetime
    ) -> Optional[dict]:
        object_id = self._object_id(run_id)
        if not object_id:
            return None
        query: dict[str, Any] = {
            "_id": object_id,
            "status": "open",
            "closure_in_progress": True,
        }
        if owner_user_id:
            query["owner_user_id"] = owner_user_id
        return await self.runs_collection.find_one_and_update(
            query,
            {
                "$set": {
                    "status": "closed",
                    "closed_at": closed_at,
                    "updated_at": closed_at,
                },
                "$unset": {
                    "closure_in_progress": "",
                    "closure_started_at": "",
                    "closure_mode": "",
                    "closure_actor_user_id": "",
                },
            },
            return_document=ReturnDocument.AFTER,
        )

    async def create_assignments(self, assignments: list[dict]) -> None:
        if assignments:
            await self.assignments_collection.bulk_write(
                [
                    UpdateOne(
                        {
                            "training_run_id": assignment["training_run_id"],
                            "recipient_email": assignment["recipient_email"],
                        },
                        {"$setOnInsert": assignment},
                        upsert=True,
                    )
                    for assignment in assignments
                ],
                ordered=False,
            )

    async def create_invitation_deliveries(self, deliveries: list[dict]) -> None:
        if not deliveries:
            return
        if self.email_deliveries_collection is None:
            raise RuntimeError("Training email deliveries collection is not configured")
        await self.email_deliveries_collection.bulk_write(
            [
                UpdateOne(
                    {"delivery_key": delivery["delivery_key"]},
                    {"$setOnInsert": delivery},
                    upsert=True,
                )
                for delivery in deliveries
            ],
            ordered=False,
        )

    async def activate_invitation_deliveries(self, run_id: str, now: datetime) -> None:
        if self.email_deliveries_collection is None:
            raise RuntimeError("Training email deliveries collection is not configured")
        await self.email_deliveries_collection.update_many(
            {"training_run_id": run_id, "status": "staged"},
            {
                "$set": {
                    "status": "pending",
                    "next_attempt_at": now,
                    "updated_at": now,
                }
            },
        )

    async def list_assignments_for_run(self, run_id: str) -> list[dict]:
        cursor = self.assignments_collection.find({"training_run_id": run_id}).sort("recipient_email", 1)
        return await cursor.to_list(length=2_000)

    async def list_sessions_for_run(self, run_id: str) -> list[dict]:
        if self.sessions_collection is None:
            return []
        cursor = self.sessions_collection.find({"training_run_id": run_id}).sort("created_at", 1)
        return await cursor.to_list(length=2_000)

    async def mark_in_progress_assignments_incomplete(
        self, run_id: str, closed_at: datetime
    ) -> None:
        """Make an owner-initiated early closure terminal for active assignees."""
        await self.assignments_collection.update_many(
            {"training_run_id": run_id, "status": {"$in": ["in_progress", "submitting"]}},
            {
                "$set": {
                    "status": "incomplete",
                    "updated_at": closed_at,
                }
            },
        )

    async def abandon_active_sessions_for_run(
        self, run_id: str, closed_at: datetime
    ) -> None:
        if self.sessions_collection is None:
            return
        await self.sessions_collection.update_many(
            {
                "training_run_id": run_id,
                "status": {"$in": ["active", "joined", "disconnected"]},
            },
            {
                "$set": {
                    "status": "abandoned",
                    "abandoned_at": closed_at,
                    "updated_at": closed_at,
                }
            },
        )

    async def get_assignment(self, assignment_id: str) -> Optional[dict]:
        object_id = self._object_id(assignment_id)
        return await self.assignments_collection.find_one({"_id": object_id}) if object_id else None

    async def bind_assignments_to_user(self, recipient_email: str, user_id: str) -> list[dict]:
        """Bind only previously-unclaimed assignments and return those newly bound."""
        bound = []
        now = datetime.now(timezone.utc)
        while True:
            pending = await self.assignments_collection.find(
                {"recipient_email": recipient_email, "recipient_user_id": None}
            ).limit(500).to_list(length=500)
            if not pending:
                return bound
            for assignment in pending:
                updated = await self.assignments_collection.find_one_and_update(
                    {"_id": assignment["_id"], "recipient_user_id": None},
                    {"$set": {"recipient_user_id": user_id, "updated_at": now}},
                    return_document=ReturnDocument.AFTER,
                )
                if updated:
                    bound.append(updated)
        return bound

    async def list_assignments_for_recipient(self, recipient_email: str, user_id: str, limit: int = 100) -> list[dict]:
        cursor = self.assignments_collection.find(
            {
                "$or": [
                    {"recipient_user_id": user_id},
                    {
                        "recipient_email": recipient_email,
                        "recipient_user_id": None,
                    },
                ]
            }
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def reserve_attempt(self, assignment_id: str, user_id: str, now: datetime) -> Optional[dict]:
        assignment = await self.get_assignment(assignment_id)
        if not assignment or assignment.get("recipient_user_id") != user_id:
            return None
        max_attempts = assignment.get("max_attempts")
        attempts_used = int(assignment.get("attempts_used", 0))
        if max_attempts is not None and attempts_used >= max_attempts:
            return None
        return await self.assignments_collection.find_one_and_update(
            {
                "_id": assignment["_id"],
                "recipient_user_id": user_id,
                "attempts_used": attempts_used,
                # A retry is allowed only once the preceding attempt has a
                # terminal result. This prevents two browser tabs from
                # creating concurrent sessions for the same assignment.
                "status": {"$in": ["assigned", "completed"]},
            },
            {"$inc": {"attempts_used": 1}, "$set": {"status": "in_progress", "started_at": now, "active_session_id": None, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def attach_session_to_attempt(
        self, assignment_id: str, user_id: str, session_id: str, now: datetime
    ) -> Optional[dict]:
        object_id = self._object_id(assignment_id)
        if not object_id:
            return None
        return await self.assignments_collection.find_one_and_update(
            {
                "_id": object_id,
                "recipient_user_id": user_id,
                "status": "in_progress",
                "active_session_id": None,
            },
            {"$set": {"active_session_id": session_id, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def claim_submission(
        self, assignment_id: str, session_id: str, now: datetime
    ) -> Optional[dict]:
        """Reserve the one completion transition before grading a session.

        Manual closure competes on this assignment state, giving both paths a
        single Mongo write that determines whether the attempt is counted.
        """
        object_id = self._object_id(assignment_id)
        if not object_id:
            return None
        return await self.assignments_collection.find_one_and_update(
            {
                "_id": object_id,
                "status": "in_progress",
                # Runs created before session fencing did not persist an active
                # session id. Preserve those in-flight attempts while keeping
                # all newly-created attempts bound to their exact session.
                "$or": [
                    {"active_session_id": session_id},
                    {"active_session_id": {"$exists": False}},
                ],
            },
            {
                "$set": {
                    "status": "submitting",
                    "submission_session_id": session_id,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def release_submission(
        self, assignment_id: str, session_id: str, now: datetime
    ) -> None:
        object_id = self._object_id(assignment_id)
        if not object_id:
            return
        await self.assignments_collection.update_one(
            {
                "_id": object_id,
                "status": "submitting",
                "submission_session_id": session_id,
            },
            {
                "$set": {"status": "in_progress", "updated_at": now},
                "$unset": {"submission_session_id": ""},
            },
        )

    async def release_attempt(
        self,
        assignment_id: str,
        user_id: str,
        *,
        previous_status: str,
        previous_started_at: Optional[datetime],
        now: datetime,
    ) -> None:
        object_id = self._object_id(assignment_id)
        if not object_id:
            return
        await self.assignments_collection.update_one(
            {
                "_id": object_id,
                "recipient_user_id": user_id,
                "status": "in_progress",
                "attempts_used": {"$gt": 0},
            },
            {
                "$inc": {"attempts_used": -1},
                "$set": {
                    "status": previous_status,
                    "started_at": previous_started_at,
                    "updated_at": now,
                },
            },
        )

    async def record_submission(self, assignment_id: str, session_id: str, score: int, percentage: float, submitted_at: datetime) -> Optional[dict]:
        object_id = self._object_id(assignment_id)
        if not object_id:
            return None
        return await self.assignments_collection.find_one_and_update(
            {
                "_id": object_id,
                "status": "submitting",
                "submission_session_id": session_id,
            },
            {
                "$set": {
                    "status": "completed", "latest_session_id": session_id,
                    "latest_score": score, "latest_percentage": percentage,
                    "completed_at": submitted_at, "updated_at": submitted_at,
                },
                "$unset": {"submission_session_id": ""},
            },
            return_document=ReturnDocument.AFTER,
        )

    async def create_audit_event(self, event: dict) -> None:
        try:
            await self.audit_events_collection.insert_one(event)
        except DuplicateKeyError:
            # Closure retries must be able to complete after the immutable
            # snapshot was written but before the run status was finalized.
            existing = await self.audit_events_collection.find_one(
                {
                    "training_run_id": event["training_run_id"],
                    "event_type": event["event_type"],
                },
                {"_id": 1},
            )
            if not existing:
                raise
            # The event is immutable and uniquely keyed by its run/type. A
            # successful prior insert means this retry has no further work.
            return
