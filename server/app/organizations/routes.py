from fastapi import APIRouter, Depends, Request, Response
from urllib.parse import urlencode
from server.app.core.config import settings
from server.app.core.rate_limiter import limiter
from server.app.i18n.locales import resolve_effective_locale

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
from server.app.organizations.models import OrganizationInvitationRequest, OrganizationOnboardingRequest
from server.app.organizations.onboarding import issue_onboarding_token, accept_onboarding_token, validate_onboarding_token


router = APIRouter(tags=["Organizations"])


@router.post("/onboarding/preview")
@limiter.limit("30/minute")
async def preview_organization_invitation(payload: OrganizationOnboardingRequest, request: Request, response: Response):
    organization = await validate_onboarding_token(payload.token, request.app.state.organizations_collection)
    return {"organization_id": str(organization["_id"]), "name": organization.get("name", ""),
            "default_locale": resolve_effective_locale(organization.get("default_locale"))}


@router.post("/{organization_id}/onboarding-invitations")
async def invite_organization_learner(
    organization_id: str, payload: OrganizationInvitationRequest, request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    token = await issue_onboarding_token(organization_id, payload.email, current_user,
        request.app.state.organizations_collection, request.app.state.organization_memberships_collection)
    # Fragments are not sent in HTTP requests or referrer headers.
    signup_url = settings.FRONTEND_BASE_URL.rstrip("/") + "/auth/register#" + urlencode({"organization_invite": token})
    return {"token": token, "signup_url": signup_url}


@router.post("/onboarding")
async def onboard_organization_learner(
    payload: OrganizationOnboardingRequest, request: Request,
    current_user: UserOut = Depends(get_verified_user),
):
    return await accept_onboarding_token(payload.token, current_user,
        request.app.state.organizations_collection, request.app.state.organization_memberships_collection,
        request.app.state.users_collection)


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
