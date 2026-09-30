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
        await self.set_default_organization(
            user_id=user_id,
            organization_id=organization_id,
            expected_default_organization_id=existing_default,
        )
        return organization

    async def set_default_organization(
        self,
        *,
        user_id: str,
        organization_id: str,
        expected_default_organization_id: str | None,
    ) -> None:
        """Set a default only when the observed state has not changed.

        A default organization is a server-owned selector. Compare-and-set
        prevents a login or provisioning retry from overwriting a concurrent
        organization switch.
        """
        default_filter: dict[str, Any]
        if expected_default_organization_id is None:
            default_filter = {
                "$or": [
                    {"default_organization_id": {"$exists": False}},
                    {"default_organization_id": None},
                ]
            }
        else:
            default_filter = {"default_organization_id": expected_default_organization_id}

        result = await self.users_collection.update_one(
            {"_id": ObjectId(user_id), **default_filter},
            {
                "$set": {
                    "default_organization_id": organization_id,
                    "updated_at": now_utc(),
                }
            },
        )
        if result.matched_count == 1:
            return

        user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
        if user and user.get("default_organization_id") == organization_id:
            return
        raise OrganizationProvisioningConflictError(
            "User default organization changed while being provisioned"
        )

    async def find_active_organization_for_user(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Find a deterministic active membership fallback for login recovery."""
        memberships = await self.memberships.list_active_for_user(user_id)
        for membership in sorted(memberships, key=lambda item: item["organization_id"]):
            organization = await self.organizations.get_active(membership["organization_id"])
            if organization is not None:
                return organization
        return None
