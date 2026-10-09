from fastapi import APIRouter, Depends, Request

from server.app.core.dependencies import get_verified_user
from server.app.organizations.models import (
    CreateOrganizationRequest,
    OrganizationSettingsResponse,
    SetActiveOrganizationResponse,
    OrganizationMemberListResponse,
    UpdateOrganizationSettingsRequest,
)
from server.app.organizations.services import (
    create_organization,
    get_organization_settings,
    set_active_organization,
    list_organization_members,
    update_organization_settings,
)
from server.app.users.models import UserOut


router = APIRouter(tags=["Organizations"])


@router.post("", response_model=OrganizationSettingsResponse)
async def create_organization_route(
    payload: CreateOrganizationRequest,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    return await create_organization(
        payload,
        current_user,
        request.app.state.organizations_collection,
        request.app.state.organization_memberships_collection,
        request.app.state.users_collection,
    )


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def read_organization_settings(
    organization_id: str,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    return await get_organization_settings(
        organization_id,
        current_user,
        request.app.state.organizations_collection,
        request.app.state.organization_memberships_collection,
    )


@router.put("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def write_organization_settings(
    organization_id: str,
    payload: UpdateOrganizationSettingsRequest,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    return await update_organization_settings(
        organization_id,
        payload,
        current_user,
        request.app.state.organizations_collection,
        request.app.state.organization_memberships_collection,
    )


@router.put("/{organization_id}/active", response_model=SetActiveOrganizationResponse)
async def set_active_organization_route(
    organization_id: str,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    active_organization_id = await set_active_organization(
        organization_id,
        current_user,
        request.app.state.organization_memberships_collection,
        request.app.state.users_collection,
    )
    return SetActiveOrganizationResponse(active_organization_id=active_organization_id)


@router.get("/{organization_id}/members", response_model=OrganizationMemberListResponse)
async def list_organization_members_route(
    organization_id: str,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    members = await list_organization_members(
        organization_id, current_user, request.app.state.organization_memberships_collection
    )
    return OrganizationMemberListResponse(members=members)
