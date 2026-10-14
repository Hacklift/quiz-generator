from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from server.app.organizations.models import (
    OrganizationDocument,
    OrganizationMembershipDocument,
    utcnow,
)


class OrganizationRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def ensure_personal_organization(
        self,
        *,
        user_id: str,
        name: str,
    ) -> dict[str, Any]:
        document = OrganizationDocument(
            kind="personal",
            name=name,
            personal_owner_user_id=user_id,
            created_by_user_id=user_id,
        ).model_dump(by_alias=True)
        return await self._upsert_once(
            {"kind": "personal", "personal_owner_user_id": user_id},
            document,
        )

    async def ensure_platform_library_organization(self) -> dict[str, Any]:
        # The accepted kind vocabulary is customer-facing. system_key makes
        # this an explicit platform tenant without adding a fifth kind that UI
        # and policy consumers might accidentally treat as a customer org.
        document = OrganizationDocument(
            kind="personal",
            name="Quizwerk Library",
            system_key="platform_library",
        ).model_dump(by_alias=True)
        return await self._upsert_once({"system_key": "platform_library"}, document)

    async def get_active(self, organization_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(organization_id)
        except Exception:
            return None
        return await self.collection.find_one(
            {"_id": object_id, "status": "active"}
        )

    async def _upsert_once(
        self,
        query: dict[str, Any],
        document: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            result = await self.collection.find_one_and_update(
                query,
                {"$setOnInsert": document},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            # Matching concurrent provisioning is a successful idempotent
            # outcome, not a user-visible registration failure.
            result = await self.collection.find_one(query)
        if result is None:
            raise RuntimeError("organization upsert did not return a document")
        return result


class OrganizationMembershipRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def ensure_personal_owner_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Create or repair the sole active owner membership of a personal tenant.

        This is intentionally not a general organization-role upsert. Personal
        organizations have exactly one owner: their personal owner. Future
        invitation and role-management flows must use dedicated operations.
        """
        query = {"organization_id": organization_id, "user_id": user_id}
        document = OrganizationMembershipDocument(
            organization_id=organization_id,
            user_id=user_id,
            role="owner",
            status="active",
            joined_at=utcnow(),
        ).model_dump(by_alias=True)
        # MongoDB rejects a field targeted by both operators. Membership role
        # and state must be repaired on every retry, while timestamps and the
        # immutable relationship fields belong only to initial insertion.
        insert_fields = {
            key: value
            for key, value in document.items()
            if key not in {"role", "status", "updated_at"}
        }
        try:
            result = await self.collection.find_one_and_update(
                query,
                {
                    "$setOnInsert": insert_fields,
                    # A personal organization's sole member is always its
                    # owner. This repairs an interrupted migration/retry that
                    # left that membership invited, suspended, or removed.
                    "$set": {"role": "owner", "status": "active", "updated_at": utcnow()},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            result = await self.collection.find_one(query)
        if result is None:
            raise RuntimeError("organization membership upsert did not return a document")
        return result

    async def ensure_personal_owner_membership_if_missing(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Create the personal-owner membership without reviving existing state."""
        document = OrganizationMembershipDocument(
            organization_id=organization_id,
            user_id=user_id,
            role="owner",
            status="active",
            joined_at=utcnow(),
        ).model_dump(by_alias=True)
        result = await self.collection.find_one_and_update(
            {"organization_id": organization_id, "user_id": user_id},
            {"$setOnInsert": document},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise RuntimeError("organization membership upsert did not return a document")
        return result

    async def get_active_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "status": "active",
            }
        )

    async def get_active_owner_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Return the required owner membership for a personal organization."""
        return await self.collection.find_one(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "role": "owner",
                "status": "active",
            }
        )

    async def list_active_for_user(self, user_id: str) -> list[dict[str, Any]]:
        return await self.collection.find(
            {"user_id": user_id, "status": "active"}
        ).to_list(length=None)
