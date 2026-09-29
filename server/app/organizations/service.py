from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.organizations.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from server.app.users.identity import now_utc


class OrganizationProvisioningService:
    """Idempotently establishes the personal tenant required for a user."""

    def __init__(
        self,
        *,
        organizations_collection: AsyncIOMotorCollection,
        memberships_collection: AsyncIOMotorCollection,
        users_collection: AsyncIOMotorCollection,
    ):
        self.organizations = OrganizationRepository(organizations_collection)
        self.memberships = OrganizationMembershipRepository(memberships_collection)
        self.users_collection = users_collection

    async def ensure_personal_organization(
        self,
        *,
        user_id: str,
        organization_name: str,
    ) -> dict[str, Any]:
        organization = await self.organizations.ensure_personal_organization(
            user_id=user_id,
            name=organization_name,
        )
        organization_id = str(organization["_id"])
        await self.memberships.ensure_owner_membership(
            organization_id=organization_id,
            user_id=user_id,
        )
        await self.users_collection.update_one(
            {
                "_id": ObjectId(user_id),
                "$or": [
                    {"default_organization_id": {"$exists": False}},
                    {"default_organization_id": None},
                ],
            },
            {
                "$set": {
                    "default_organization_id": organization_id,
                    "updated_at": now_utc(),
                }
            },
        )
        return organization
