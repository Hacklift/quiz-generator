from __future__ import annotations

from datetime import datetime
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

    async def create_shared_organization(
        self,
        *,
        kind: str,
        name: str,
        created_by_user_id: str,
    ) -> dict[str, Any]:
        """Create a customer workspace; personal tenants are implicit only."""
        document = OrganizationDocument(
            kind=kind,
            name=name,
            created_by_user_id=created_by_user_id,
        ).model_dump(by_alias=True)
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

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

    async def create_owner_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Create the initial owner of a newly-created shared organization."""
        now = utcnow()
        document = OrganizationMembershipDocument(
            organization_id=organization_id,
            user_id=user_id,
            role="owner",
            status="active",
            joined_at=now,
        ).model_dump(by_alias=True)
        document.pop("_id", None)
        result = await self.collection.find_one_and_update(
            {"organization_id": organization_id, "user_id": user_id},
            {"$setOnInsert": document},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            raise RuntimeError("organization owner membership creation did not return a document")
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

    async def list_for_organization(self, organization_id: str) -> list[dict[str, Any]]:
        """List members for administrators without exposing another tenant's rows."""
        return await self.collection.find(
            {"organization_id": organization_id}
        ).sort("created_at", 1).to_list(length=2_000)

    async def invite_known_user(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        invited_by_user_id: str,
    ) -> dict[str, Any]:
        """Create an invitation membership without downgrading active access."""
        now = utcnow()
        existing = await self.collection.find_one(
            {"organization_id": organization_id, "user_id": user_id}
        )
        if existing and existing.get("status") == "active":
            return existing
        return await self.collection.find_one_and_update(
            {"organization_id": organization_id, "user_id": user_id},
            {
                "$set": {
                    "role": role,
                    "status": "invited",
                    "invited_by_user_id": invited_by_user_id,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "joined_at": None,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def activate_invitation(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
        invited_by_user_id: str,
    ) -> dict[str, Any]:
        now = utcnow()
        try:
            membership = await self.collection.find_one_and_update(
                {
                    "organization_id": organization_id,
                    "user_id": user_id,
                    # An invitation must never rewrite the role of an active
                    # member. The unique membership index turns this into a
                    # DuplicateKeyError in the concurrent-active case below.
                    "status": {"$ne": "active"},
                },
                {
                    "$set": {
                        "role": role,
                        "status": "active",
                        "joined_at": now,
                        "invited_by_user_id": invited_by_user_id,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "organization_id": organization_id,
                        "user_id": user_id,
                        "created_at": now,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            membership = await self.collection.find_one(
                {"organization_id": organization_id, "user_id": user_id}
            )
        if membership is None:
            raise RuntimeError("organization invitation activation did not return a membership")
        return membership

    async def set_status(
        self,
        *,
        organization_id: str,
        user_id: str,
        status: str,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "role": {"$ne": "owner"},
                # Only an active member can be suspended or removed. A pending
                # invitation becomes active exclusively through token acceptance.
                "status": "active",
            },
            {"$set": {"status": status, "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def remove_pending_invitation(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Remove only the pending row created for an e-mail invitation."""
        return await self.collection.find_one_and_update(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "status": "invited",
                "role": {"$ne": "owner"},
            },
            {"$set": {"status": "removed", "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )


class OrganizationInvitationRepository:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def replace_open_invitation(
        self,
        invitation: dict[str, Any],
    ) -> dict[str, Any]:
        """Rotate a prior invitation rather than leaving multiple valid links."""
        updates = dict(invitation)
        created_at = updates.pop("created_at")
        return await self.collection.find_one_and_update(
            {
                "organization_id": invitation["organization_id"],
                "email_normalized": invitation["email_normalized"],
            },
            {
                "$set": updates,
                "$setOnInsert": {"created_at": created_at},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def list_for_organization(self, organization_id: str) -> list[dict[str, Any]]:
        now = utcnow()
        await self.collection.update_many(
            {
                "organization_id": organization_id,
                "status": "invited",
                "expires_at": {"$lte": now},
            },
            {"$set": {"status": "expired", "updated_at": now}},
        )
        return await self.collection.find(
            {"organization_id": organization_id}
        ).sort("created_at", -1).to_list(length=500)

    async def consume_token(
        self,
        *,
        token_hash: str,
        email_normalized: str,
        accepted_by_user_id: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "email_normalized": email_normalized,
                "status": "invited",
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "status": "accepted",
                    "accepted_by_user_id": accepted_by_user_id,
                    "accepted_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def decline_token(
        self,
        *,
        token_hash: str,
        email_normalized: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "email_normalized": email_normalized,
                "status": "invited",
                "expires_at": {"$gt": now},
            },
            {"$set": {"status": "declined", "declined_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )

    async def restore_consumed_invitation(
        self,
        *,
        invitation_id: ObjectId,
        accepted_by_user_id: str,
    ) -> None:
        """Make a transient post-consume failure safely retryable."""
        await self.collection.update_one(
            {
                "_id": invitation_id,
                "status": "accepted",
                "accepted_by_user_id": accepted_by_user_id,
            },
            {
                "$set": {
                    "status": "invited",
                    "accepted_by_user_id": None,
                    "accepted_at": None,
                    "updated_at": utcnow(),
                }
            },
        )

    async def revoke(self, invitation_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {"_id": invitation_id, "status": "invited"},
            {"$set": {"status": "revoked", "revoked_at": utcnow(), "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def get_for_organization(self, invitation_id: ObjectId, organization_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": invitation_id, "organization_id": organization_id})
