from __future__ import annotations

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.organizations.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from server.app.users.identity import now_utc


_PERSONAL_WORKSPACE_SUFFIX = "'s workspace"
_MAX_ORGANIZATION_NAME_LENGTH = 160


class OrganizationProvisioningConflictError(RuntimeError):
    """A user default points at a tenant other than their personal tenant."""


class PersonalOrganizationMembershipInactiveError(RuntimeError):
    """A personal membership exists but was deliberately disabled."""


def personal_workspace_name(display_name: str | None) -> str:
    """Build a valid, stable personal-tenant name from untrusted profile data."""

    normalized_name = " ".join((display_name or "").split())
    if not normalized_name:
        return "Personal workspace"
    max_identity_length = _MAX_ORGANIZATION_NAME_LENGTH - len(_PERSONAL_WORKSPACE_SUFFIX)
    return f"{normalized_name[:max_identity_length].rstrip()}{_PERSONAL_WORKSPACE_SUFFIX}"


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
        repair_membership: bool = False,
        replace_conflicting_default: bool = False,
    ) -> dict[str, Any]:
        organization = await self.organizations.ensure_personal_organization(
            user_id=user_id,
            name=personal_workspace_name(organization_name),
        )
        organization_id = str(organization["_id"])
        if repair_membership:
            membership = await self.memberships.ensure_personal_owner_membership(
                organization_id=organization_id,
                user_id=user_id,
            )
        else:
            membership = await self.memberships.ensure_personal_owner_membership_if_missing(
                organization_id=organization_id,
                user_id=user_id,
            )
        if membership.get("role") != "owner" or membership.get("status") != "active":
            raise PersonalOrganizationMembershipInactiveError(
                "Personal organization membership is not active"
            )
        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise OrganizationProvisioningConflictError("User no longer exists")
        existing_default = user.get("default_organization_id")
        if existing_default not in {None, organization_id} and not replace_conflicting_default:
            raise OrganizationProvisioningConflictError(
                "User default organization does not match personal organization"
            )
        await self.users_collection.update_one(
            {
                "_id": ObjectId(user_id),
                "default_organization_id": (
                    {"$in": [None, organization_id]}
                    if not replace_conflicting_default
                    else {"$exists": True}
                ),
            },
            {
                "$set": {
                    "default_organization_id": organization_id,
                    "updated_at": now_utc(),
                }
            },
        )
        return organization
