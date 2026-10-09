from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ReturnDocument

from server.app.i18n.locales import DEFAULT_LOCALE, SupportedLocale, resolve_effective_locale
from server.app.organizations.models import (
    CreateOrganizationRequest,
    OrganizationSettingsResponse,
    UpdateOrganizationSettingsRequest,
)
from server.app.users.identity import now_utc
from server.app.users.models import UserOut


def _organization_object_id(organization_id: str) -> ObjectId:
    try:
        return ObjectId(organization_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid organization ID format",
        ) from exc


async def _membership_for_user(
    memberships_collection: AsyncIOMotorCollection,
    *,
    organization_id: str,
    user_id: str,
) -> dict | None:
    return await memberships_collection.find_one(
        {"organization_id": organization_id, "user_id": user_id}
    )


async def resolve_user_effective_locale(
    current_user: UserOut,
    organizations_collection: AsyncIOMotorCollection,
    memberships_collection: AsyncIOMotorCollection,
) -> SupportedLocale:
    """Resolve a user override first, then their active organisation default."""

    if current_user.preferred_locale:
        return resolve_effective_locale(current_user.preferred_locale)

    organization_id = current_user.active_organization_id
    if not organization_id or not ObjectId.is_valid(organization_id):
        return DEFAULT_LOCALE

    membership = await _membership_for_user(
        memberships_collection,
        organization_id=organization_id,
        user_id=current_user.id,
    )
    if not membership:
        return DEFAULT_LOCALE

    organization = await organizations_collection.find_one(
        {"_id": _organization_object_id(organization_id)}
    )
    if not organization:
        return DEFAULT_LOCALE

    return resolve_effective_locale(organization.get("default_locale"))


async def create_organization(
    payload: CreateOrganizationRequest,
    current_user: UserOut,
    organizations_collection: AsyncIOMotorCollection,
    memberships_collection: AsyncIOMotorCollection,
    users_collection: AsyncIOMotorCollection,
) -> OrganizationSettingsResponse:
    now = now_utc()
    organization = {
        "name": payload.name.strip(),
        "default_locale": payload.default_locale,
        "created_at": now,
        "updated_at": now,
    }
    result = await organizations_collection.insert_one(organization)
    organization_id = str(result.inserted_id)
    await memberships_collection.insert_one(
        {
            "organization_id": organization_id,
            "user_id": current_user.id,
            "role": "owner",
            "created_at": now,
            "updated_at": now,
        }
    )
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"profile.active_organization_id": organization_id, "updated_at": now}},
    )
    return OrganizationSettingsResponse(
        id=organization_id,
        name=organization["name"],
        default_locale=payload.default_locale,
        role="owner",
        created_at=now,
        updated_at=now,
    )


async def get_organization_settings(
    organization_id: str,
    current_user: UserOut,
    organizations_collection: AsyncIOMotorCollection,
    memberships_collection: AsyncIOMotorCollection,
) -> OrganizationSettingsResponse:
    membership = await _membership_for_user(
        memberships_collection,
        organization_id=organization_id,
        user_id=current_user.id,
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    organization = await organizations_collection.find_one(
        {"_id": _organization_object_id(organization_id)}
    )
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationSettingsResponse(
        id=str(organization["_id"]),
        name=organization["name"],
        default_locale=resolve_effective_locale(organization.get("default_locale")),
        role=membership["role"],
        created_at=organization["created_at"],
        updated_at=organization["updated_at"],
    )


async def update_organization_settings(
    organization_id: str,
    payload: UpdateOrganizationSettingsRequest,
    current_user: UserOut,
    organizations_collection: AsyncIOMotorCollection,
    memberships_collection: AsyncIOMotorCollection,
) -> OrganizationSettingsResponse:
    membership = await _membership_for_user(
        memberships_collection,
        organization_id=organization_id,
        user_id=current_user.id,
    )
    if not membership or membership.get("role") not in {"owner", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization owner or admin access required",
        )
    now = now_utc()
    organization = await organizations_collection.find_one_and_update(
        {"_id": _organization_object_id(organization_id)},
        {"$set": {"default_locale": payload.default_locale, "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationSettingsResponse(
        id=str(organization["_id"]),
        name=organization["name"],
        default_locale=payload.default_locale,
        role=membership["role"],
        created_at=organization["created_at"],
        updated_at=organization["updated_at"],
    )


async def set_active_organization(
    organization_id: str,
    current_user: UserOut,
    memberships_collection: AsyncIOMotorCollection,
    users_collection: AsyncIOMotorCollection,
) -> str:
    membership = await _membership_for_user(
        memberships_collection,
        organization_id=organization_id,
        user_id=current_user.id,
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"profile.active_organization_id": organization_id, "updated_at": now_utc()}},
    )
    return organization_id


async def list_organization_members(
    organization_id: str,
    current_user: UserOut,
    memberships_collection: AsyncIOMotorCollection,
) -> list[dict]:
    membership = await _membership_for_user(
        memberships_collection, organization_id=organization_id, user_id=current_user.id
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership required")
    cursor = memberships_collection.find({"organization_id": organization_id}).sort("created_at", 1)
    return await cursor.to_list(length=500)
