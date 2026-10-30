from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from server.app.cohorts.models import CohortDocument, CohortMembershipDocument
from server.app.organizations.models import utcnow

logger = logging.getLogger(__name__)
HIERARCHY_LEASE = timedelta(seconds=60)
HIERARCHY_OPERATION_TIMEOUT = 10


def cursor_object_id(value: str | None) -> ObjectId | None:
    if value is None:
        return None
    if not ObjectId.is_valid(value):
        raise HTTPException(422, "Invalid pagination cursor")
    return ObjectId(value)


def page_result(rows: list[dict], limit: int) -> tuple[list[dict], str | None]:
    return rows[:limit], str(rows[limit - 1]["_id"]) if len(rows) > limit else None


class CohortRepository:
    def __init__(self, cohorts_collection, memberships_collection, hierarchy_locks_collection=None):
        self.cohorts = cohorts_collection
        self.memberships = memberships_collection
        self.hierarchy_locks = (
            hierarchy_locks_collection if hierarchy_locks_collection is not None
            else cohorts_collection.database["cohort_hierarchy_locks"]
        )

    @asynccontextmanager
    async def hierarchy_mutation(self, organization_id: str):
        """Serialize shallow hierarchy mutations across API processes, not tabs.

        The critical section is bounded well inside its lease; the token guards
        release and writes against an expired/reclaimed holder. No Redis polling
        or process-local lock is used for cross-document hierarchy invariants.
        """
        token = uuid4().hex
        now = utcnow()
        try:
            lock = await self.hierarchy_locks.find_one_and_update(
                {"_id": organization_id, "expires_at": {"$lte": now}},
                {"$set": {"token": token, "expires_at": now + HIERARCHY_LEASE}},
                upsert=True, return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            raise HTTPException(409, "Cohort is being updated; retry shortly") from None
        if lock is None:
            raise HTTPException(409, "Cohort is being updated; retry shortly")
        try:
            async with asyncio.timeout(HIERARCHY_OPERATION_TIMEOUT):
                yield token
        except TimeoutError:
            raise HTTPException(503, "Cohort update timed out; refresh before retrying") from None
        finally:
            try:
                await self.hierarchy_locks.update_one(
                    {"_id": organization_id, "token": token},
                    {"$set": {"expires_at": utcnow()}},
                )
            except PyMongoError:
                logger.exception("Could not release cohort hierarchy lease for %s", organization_id)

    async def _check_lease(self, organization_id: str, token: str) -> None:
        lock = await self.hierarchy_locks.find_one({
            "_id": organization_id, "token": token,
            "expires_at": {"$gt": utcnow() + timedelta(seconds=HIERARCHY_OPERATION_TIMEOUT)},
        })
        if lock is None:
            raise HTTPException(409, "Cohort update lease lost; refresh before retrying")

    async def get(self, organization_id: str, cohort_id: str) -> dict | None:
        if not isinstance(cohort_id, str) or not ObjectId.is_valid(cohort_id):
            return None
        return await self.cohorts.find_one({
            "organization_id": organization_id, "_id": ObjectId(cohort_id),
        })

    async def has_active_children(self, organization_id: str, cohort_id: str) -> bool:
        return await self.cohorts.find_one({
            "organization_id": organization_id,
            "parent_cohort_id": cohort_id, "status": "active",
        }, {"_id": 1}) is not None

    async def has_children(self, organization_id: str, cohort_id: str) -> bool:
        # Archived children retain their hierarchy for historical evidence.
        return await self.cohorts.find_one({
            "organization_id": organization_id, "parent_cohort_id": cohort_id,
        }, {"_id": 1}) is not None

    async def create(self, document: CohortDocument, *, token: str) -> dict:
        await self._check_lease(document.organization_id, token)
        row = document.model_dump(by_alias=True)
        await self.cohorts.insert_one(row)
        return row

    async def update(self, organization_id: str, cohort_id: str, changes: dict, *, token: str) -> dict | None:
        await self._check_lease(organization_id, token)
        return await self.cohorts.find_one_and_update(
            {"organization_id": organization_id, "_id": ObjectId(cohort_id), "status": "active"},
            {"$set": {**changes, "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def get_membership(self, organization_id: str, cohort_id: str, user_id: str) -> dict | None:
        return await self.memberships.find_one({
            "organization_id": organization_id, "cohort_id": cohort_id,
            "user_id": user_id, "status": "active",
        })

    async def list_page(
        self, organization_id: str, *, limit: int, cursor: str | None,
        status: str | None, user_id: str | None,
    ) -> tuple[list[dict], str | None]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if status is not None:
            query["status"] = status
        object_id = cursor_object_id(cursor)
        if object_id is not None:
            query["_id"] = {"$lt": object_id}
        pipeline: list[dict] = [{"$match": query}, {"$sort": {"_id": -1}}]
        if user_id is not None:
            pipeline.extend([
                {"$lookup": {
                    "from": self.memberships.name,
                    "let": {"cohort": {"$toString": "$_id"}},
                    "pipeline": [{"$match": {
                        "organization_id": organization_id, "user_id": user_id, "status": "active",
                        "$expr": {"$eq": ["$cohort_id", "$$cohort"]},
                    }}, {"$limit": 1}],
                    "as": "_membership",
                }},
                {"$match": {"_membership.0": {"$exists": True}}},
            ])
        pipeline.extend([{"$limit": limit + 1}, {"$project": {"_membership": 0}}])
        rows = await self.cohorts.aggregate(pipeline).to_list(length=limit + 1)
        return page_result(rows, limit)

    async def list_members_page(
        self, organization_id: str, cohort_id: str, *, limit: int, cursor: str | None,
        organization_memberships_collection,
    ) -> tuple[list[dict], str | None]:
        query: dict[str, Any] = {
            "organization_id": organization_id, "cohort_id": cohort_id, "status": "active",
        }
        object_id = cursor_object_id(cursor)
        if object_id is not None:
            query["_id"] = {"$lt": object_id}
        rows = await self.memberships.aggregate([
            {"$match": query}, {"$sort": {"_id": -1}},
            self.active_organization_member_lookup(organization_id, organization_memberships_collection.name),
            {"$match": {"_organization_membership.0": {"$exists": True}}},
            {"$limit": limit + 1}, {"$project": {"_organization_membership": 0}},
        ]).to_list(length=limit + 1)
        return page_result(rows, limit)

    @staticmethod
    def active_organization_member_lookup(organization_id: str, collection_name: str) -> dict:
        return {"$lookup": {
            "from": collection_name, "let": {"member_user_id": "$user_id"},
            "pipeline": [{"$match": {
                "organization_id": organization_id, "status": "active",
                "$expr": {"$eq": ["$user_id", "$$member_user_id"]},
            }}, {"$limit": 1}],
            "as": "_organization_membership",
        }}

    async def snapshot_member_rows(self, organization_id: str, cohort_id: str, *, limit: int, organization_memberships_collection) -> list[dict]:
        return await self.memberships.aggregate([
            {"$match": {
                "organization_id": organization_id, "cohort_id": cohort_id,
                "role": "member", "status": "active",
            }}, {"$sort": {"_id": 1}},
            self.active_organization_member_lookup(organization_id, organization_memberships_collection.name),
            {"$match": {"_organization_membership.0": {"$exists": True}}},
            {"$limit": limit + 1}, {"$project": {"_organization_membership": 0}},
        ]).to_list(length=limit + 1)

    async def set_member(self, document: CohortMembershipDocument, *, token: str) -> dict:
        await self._check_lease(document.organization_id, token)
        row = document.model_dump(by_alias=True)
        identity = {key: row[key] for key in ("organization_id", "cohort_id", "user_id")}
        immutable = {key: row[key] for key in ("_id", "created_at", "created_by_user_id")}
        updates = {key: value for key, value in row.items() if key not in immutable}
        result = await self.memberships.find_one_and_update(
            identity, {"$setOnInsert": immutable, "$set": updates},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise RuntimeError("Cohort membership update returned no document")
        return result

    async def remove_member(self, organization_id: str, cohort_id: str, user_id: str, *, token: str) -> None:
        await self._check_lease(organization_id, token)
        await self.memberships.update_one(
            {"organization_id": organization_id, "cohort_id": cohort_id, "user_id": user_id, "status": "active"},
            {"$set": {"status": "removed", "updated_at": utcnow()}},
        )
