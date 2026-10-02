from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


class InvitationMembershipStateError(RuntimeError):
    """An invitation cannot override an administrator-controlled member state."""


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
            status="provisioning",
            created_by_user_id=created_by_user_id,
        ).model_dump(by_alias=True)
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def activate_provisioned_shared_organization(
        self,
        *,
        organization_id: str,
        owner_user_id: str,
    ) -> dict[str, Any] | None:
        """Promote only the organization created for this owner lifecycle."""
        try:
            object_id = ObjectId(organization_id)
        except Exception:
            return None
        return await self.collection.find_one_and_update(
            {
                "_id": object_id,
                "status": "provisioning",
                "created_by_user_id": owner_user_id,
                "personal_owner_user_id": None,
                "system_key": None,
                "kind": {"$ne": "personal"},
            },
            {"$set": {"status": "active", "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def list_provisioning_shared_organizations(self, *, limit: int = 500) -> list[dict[str, Any]]:
        """Return only inaccessible shared tenants left by an interrupted create."""
        return await self.collection.find(
            {
                "status": "provisioning",
                "kind": {"$ne": "personal"},
                "personal_owner_user_id": None,
                "system_key": None,
                "created_by_user_id": {"$type": "string"},
            }
        ).sort("_id", 1).to_list(length=limit)

    async def get_active(self, organization_id: str) -> dict[str, Any] | None:
        try:
            object_id = ObjectId(organization_id)
        except Exception:
            return None
        return await self.collection.find_one(
            {"_id": object_id, "status": "active"}
        )

    async def list_active_by_ids(self, organization_ids: list[str]) -> list[dict[str, Any]]:
        object_ids = [ObjectId(value) for value in organization_ids if ObjectId.is_valid(value)]
        if not object_ids:
            return []
        return await self.collection.find(
            {"_id": {"$in": object_ids}, "status": "active"}
        ).to_list(length=len(object_ids))

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

    async def get_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"organization_id": organization_id, "user_id": user_id}
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

    async def list_for_organization(
        self,
        organization_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Page members within one organization using a stable `_id` cursor."""
        query: dict[str, Any] = {"organization_id": organization_id}
        if cursor:
            try:
                query["_id"] = {"$lt": ObjectId(cursor)}
            except Exception as exc:
                raise ValueError("Invalid member cursor") from exc
        memberships = await self.collection.find(query).sort("_id", -1).limit(limit + 1).to_list(
            length=limit + 1
        )
        page = memberships[:limit]
        next_cursor = str(page[-1]["_id"]) if len(memberships) > limit else None
        return page, next_cursor

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
        if existing and existing.get("status") in {"active", "suspended"}:
            return existing
        if existing:
            updated = await self.collection.find_one_and_update(
                {
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "status": {"$in": ["invited", "removed"]},
                },
                {
                    "$set": {
                        "role": role,
                        "status": "invited",
                        "invited_by_user_id": invited_by_user_id,
                        "updated_at": now,
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if updated is not None:
                return updated
            return await self.get_membership(
                organization_id=organization_id,
                user_id=user_id,
            )
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
                    # A recipient may activate only a pending invitation.
                    # Suspension is an administrator decision and cannot be
                    # bypassed with a new or previously issued token.
                    "status": "invited",
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
                upsert=False,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            membership = None
        if membership is None:
            existing = await self.get_membership(
                organization_id=organization_id,
                user_id=user_id,
            )
            if existing is not None:
                if existing.get("status") == "active":
                    return existing
                raise InvitationMembershipStateError(
                    f"Membership is {existing.get('status')} and cannot accept invitations"
                )
            document = OrganizationMembershipDocument(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                status="active",
                joined_at=now,
                invited_by_user_id=invited_by_user_id,
            ).model_dump(by_alias=True)
            document.pop("_id", None)
            try:
                await self.collection.insert_one(document)
                membership = document
            except DuplicateKeyError:
                membership = await self.get_membership(
                    organization_id=organization_id,
                    user_id=user_id,
                )
                if membership is None or membership.get("status") != "active":
                    raise InvitationMembershipStateError(
                        "Membership changed while the invitation was accepted"
                    )
        return membership

    async def set_status(
        self,
        *,
        organization_id: str,
        user_id: str,
        status: str,
        expected_role: str | None = None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {
            "organization_id": organization_id,
            "user_id": user_id,
            "role": {"$ne": "owner"},
        }
        if status == "active":
            # Reactivation is an explicit organization-manager action, never
            # a side effect of invitation acceptance.
            query["status"] = "suspended"
        elif status == "suspended":
            query["status"] = "active"
        elif status == "removed":
            query["status"] = {"$in": ["active", "suspended"]}
        else:
            raise ValueError(f"Unsupported membership status transition: {status}")
        if expected_role is not None:
            query["role"] = expected_role
        return await self.collection.find_one_and_update(
            query,
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

    async def mark_email_delivery(
        self,
        *,
        invitation_id: ObjectId,
        token_hash: str,
        delivery_status: str,
    ) -> dict[str, Any] | None:
        """Record dispatch for this exact token without racing a replacement.

        Re-inviting an address rotates the token on the same invitation row.
        Matching the token hash prevents a delayed first dispatch from
        overwriting the delivery state of the newer invitation.
        """
        if delivery_status not in {"sent", "failed"}:
            raise ValueError("Unsupported invitation delivery status")
        now = utcnow()
        return await self.collection.find_one_and_update(
            {"_id": invitation_id, "token_hash": token_hash},
            {
                "$set": {
                    "email_delivery_status": delivery_status,
                    "email_delivery_attempted_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def list_for_organization(
        self,
        organization_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        query: dict[str, Any] = {"organization_id": organization_id}
        if cursor:
            try:
                query["_id"] = {"$lt": ObjectId(cursor)}
            except Exception as exc:
                raise ValueError("Invalid invitation cursor") from exc
        invitations = await self.collection.find(query).sort("_id", -1).limit(limit + 1).to_list(
            length=limit + 1
        )
        page = invitations[:limit]
        next_cursor = str(page[-1]["_id"]) if len(invitations) > limit else None
        now = utcnow()
        # Expiry is an effective read-time state. Consumption already checks
        # `expires_at`, so this avoids an unbounded write on every GET.
        for invitation in page:
            expires_at = invitation.get("expires_at")
            if (
                invitation.get("status") == "invited"
                and isinstance(expires_at, datetime)
                and _as_utc(expires_at) <= now
            ):
                invitation["status"] = "expired"
        return page, next_cursor

    async def claim_token(
        self,
        *,
        token_hash: str,
        email_normalized: str,
        accepted_by_user_id: str,
        claim_id: str,
        now: datetime,
        lease_seconds: int = 60,
    ) -> dict[str, Any] | None:
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        invitation = await self.collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "email_normalized": email_normalized,
                "status": "invited",
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "status": "accepting",
                    "accepted_by_user_id": accepted_by_user_id,
                    "acceptance_claim_id": claim_id,
                    "acceptance_lease_expires_at": lease_expires_at,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if invitation is not None:
            return invitation
        # Recover after a process crash while retaining exclusive ownership of
        # the acceptance work. A still-live claim remains unavailable.
        return await self.collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "email_normalized": email_normalized,
                "status": "accepting",
                "accepted_by_user_id": accepted_by_user_id,
                "acceptance_lease_expires_at": {"$lte": now},
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "acceptance_claim_id": claim_id,
                    "acceptance_lease_expires_at": lease_expires_at,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def finalize_claim(
        self,
        *,
        invitation_id: ObjectId,
        claim_id: str,
        accepted_by_user_id: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {
                "_id": invitation_id,
                "status": "accepting",
                "accepted_by_user_id": accepted_by_user_id,
                "acceptance_claim_id": claim_id,
            },
            {
                "$set": {
                    "status": "accepted",
                    "accepted_at": now,
                    "acceptance_claim_id": None,
                    "acceptance_lease_expires_at": None,
                    "updated_at": now,
                },
            },
            return_document=ReturnDocument.AFTER,
        )

    async def get_for_token_and_recipient(
        self,
        *,
        token_hash: str,
        email_normalized: str,
    ) -> dict[str, Any] | None:
        """Inspect only a recipient-bound invitation after a claim race."""
        return await self.collection.find_one(
            {
                "token_hash": token_hash,
                "email_normalized": email_normalized,
            }
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
        claim_id: str,
    ) -> None:
        """Make a transient post-consume failure safely retryable."""
        await self.collection.update_one(
            {
                "_id": invitation_id,
                "status": "accepting",
                "accepted_by_user_id": accepted_by_user_id,
                "acceptance_claim_id": claim_id,
            },
            {
                "$set": {
                    "status": "invited",
                    "accepted_by_user_id": None,
                    "acceptance_claim_id": None,
                    "acceptance_lease_expires_at": None,
                    "accepted_at": None,
                    "updated_at": utcnow(),
                }
            },
        )

    async def revoke(
        self,
        invitation_id: ObjectId,
        *,
        expected_role: str | None = None,
    ) -> dict[str, Any] | None:
        query: dict[str, Any] = {"_id": invitation_id, "status": "invited"}
        if expected_role is not None:
            query["role"] = expected_role
        return await self.collection.find_one_and_update(
            query,
            {"$set": {"status": "revoked", "revoked_at": utcnow(), "updated_at": utcnow()}},
            return_document=ReturnDocument.AFTER,
        )

    async def get_for_organization(self, invitation_id: ObjectId, organization_id: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": invitation_id, "organization_id": organization_id})


def _as_utc(value: datetime) -> datetime:
    """Mongo's default codec returns UTC datetimes without tzinfo."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
