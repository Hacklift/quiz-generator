from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from bson import ObjectId

from server.app.core.dependencies import get_current_user, get_verified_user
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.db.core.connection import (
    get_organization_invitations_collection,
    get_organization_memberships_collection,
    get_organizations_collection,
    get_user_sessions_collection,
    get_users_collection,
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.organizations.dependencies import (
    choose_active_organization_id,
    get_active_organization_context,
)
from server.app.organizations.invitation_service import (
    OrganizationInvitationService,
    OrganizationLifecycleService,
)
from server.app.organizations.models import OrganizationContext
from server.app.organizations.policy import OrganizationAction, OrganizationPolicy
from server.app.organizations.repository import (
    OrganizationInvitationRepository,
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from server.app.organizations.schemas import (
    ActiveOrganizationResponse,
    ActiveOrganizationSelectionRequest,
    CreateOrganizationRequest,
    CreateOrganizationInvitationRequest,
    InvitationDecisionRequest,
    OrganizationInvitationResponse,
    OrganizationInvitationPageResponse,
    OrganizationMemberResponse,
    OrganizationMemberPageResponse,
    OrganizationMembershipResponse,
    UpdateOrganizationMembershipRequest,
)
from server.app.users.identity import now_utc
from server.app.users.models import UserOut
from server.app.users.repository import get_active_session


router = APIRouter(prefix="/organizations", tags=["Organizations"])
policy = OrganizationPolicy()


def _invitation_response(invitation: dict) -> OrganizationInvitationResponse:
    return OrganizationInvitationResponse(
        id=str(invitation["_id"]),
        organization_id=invitation["organization_id"],
        email=invitation["email"],
        role=invitation["role"],
        status=invitation["status"],
        email_delivery_status=invitation.get("email_delivery_status"),
        expires_at=invitation["expires_at"],
        created_at=invitation["created_at"],
    )


def _invitation_service() -> OrganizationInvitationService:
    return OrganizationInvitationService(
        organizations_collection=get_organizations_collection(),
        memberships_collection=get_organization_memberships_collection(),
        invitations_collection=get_organization_invitations_collection(),
        users_collection=get_users_collection(),
    )


@router.post("", response_model=ActiveOrganizationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.API_WRITE)
async def create_organization(
    request: Request,
    payload: CreateOrganizationRequest,
    current_user: UserOut = Depends(get_verified_user),
):
    # Tenant creation is a platform-level capability of a verified account;
    # it is not administration of whichever organization happens to be active.
    organization, membership = await OrganizationLifecycleService(
        organizations_collection=get_organizations_collection(),
        memberships_collection=get_organization_memberships_collection(),
        users_collection=get_users_collection(),
    ).create_shared_organization(
        kind=payload.kind,
        name=payload.name,
        owner_user_id=current_user.id,
    )
    return ActiveOrganizationResponse(
        organization_id=str(organization["_id"]),
        organization_name=organization["name"],
        organization_kind=organization["kind"],
        role=membership["role"],
    )


@router.get("/memberships", response_model=list[OrganizationMembershipResponse])
@limiter.limit(RateLimits.API_READ)
async def list_my_memberships(
    request: Request,
    current_user: UserOut = Depends(get_current_user),
):
    memberships = await OrganizationMembershipRepository(
        get_organization_memberships_collection()
    ).list_active_for_user(current_user.id)
    organizations_by_id = {
        str(organization["_id"]): organization
        for organization in await OrganizationRepository(
            get_organizations_collection()
        ).list_active_by_ids([membership["organization_id"] for membership in memberships])
    }
    session_id = current_user.session_id
    session = (
        await get_active_session(
            get_user_sessions_collection(),
            session_id=session_id,
            user_id=current_user.id,
        )
        if session_id
        else None
    )
    selected_id = session.get("active_organization_id") if session else None
    membership_ids = {membership["organization_id"] for membership in memberships}
    selected_is_active = selected_id in membership_ids and selected_id in organizations_by_id
    default_id = current_user.default_organization_id
    default_is_active = default_id in membership_ids and default_id in organizations_by_id
    effective_active_id, active_scope_recovered = choose_active_organization_id(
        selected_organization_id=selected_id,
        default_organization_id=default_id,
        selected_is_active=selected_is_active,
        default_is_active=default_is_active,
    )
    responses: list[OrganizationMembershipResponse] = []
    for membership in memberships:
        organization = organizations_by_id.get(membership["organization_id"])
        if organization is None:
            continue
        responses.append(
            OrganizationMembershipResponse(
                organization_id=membership["organization_id"],
                organization_name=organization["name"],
                organization_kind=organization["kind"],
                role=membership["role"],
                status=membership["status"],
                is_active=membership["organization_id"] == effective_active_id,
                active_scope_recovered=(
                    active_scope_recovered and membership["organization_id"] == effective_active_id
                ),
            )
        )
    return sorted(responses, key=lambda item: (not item.is_active, item.organization_name.casefold()))


@router.put("/active", response_model=ActiveOrganizationResponse)
@limiter.limit(RateLimits.API_WRITE)
async def select_active_organization(
    request: Request,
    payload: ActiveOrganizationSelectionRequest,
    current_user: UserOut = Depends(get_current_user),
):
    membership = await OrganizationMembershipRepository(
        get_organization_memberships_collection()
    ).get_active_membership(organization_id=payload.organization_id, user_id=current_user.id)
    organization = await OrganizationRepository(get_organizations_collection()).get_active(
        payload.organization_id
    )
    if membership is None or organization is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied")
    if not current_user.session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session context is missing")
    result = await get_user_sessions_collection().update_one(
        {"session_id": current_user.session_id, "user_id": current_user.id, "revoked_at": None},
        {"$set": {"active_organization_id": payload.organization_id, "updated_at": now_utc()}},
    )
    if result.matched_count != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")
    return ActiveOrganizationResponse(
        organization_id=payload.organization_id,
        organization_name=organization["name"],
        organization_kind=organization["kind"],
        role=membership["role"],
    )


@router.post("/invitations", response_model=OrganizationInvitationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.API_WRITE)
async def create_invitation(
    request: Request,
    payload: CreateOrganizationInvitationRequest,
    email_service: EmailService = Depends(get_email_service),
    _current_user: UserOut = Depends(get_verified_user),
    context: OrganizationContext = Depends(get_active_organization_context),
):
    if not policy.can(context.principal, OrganizationAction.MEMBERSHIP_MANAGE, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization invitation access denied")
    if payload.role == "admin" and not policy.can(
        context.principal,
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE,
        None,
        context,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an organization owner may invite an administrator")
    invitation = await _invitation_service().invite(
        organization_id=context.organization_id,
        inviter_user_id=context.principal.user_id,
        email=str(payload.email),
        role=payload.role,
        expires_in_days=payload.expires_in_days,
        email_service=email_service,
    )
    return _invitation_response(invitation)


@router.get("/invitations", response_model=OrganizationInvitationPageResponse)
@limiter.limit(RateLimits.API_READ)
async def list_invitations(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, min_length=24, max_length=24),
    _current_user: UserOut = Depends(get_verified_user),
    context: OrganizationContext = Depends(get_active_organization_context),
):
    if not policy.can(context.principal, OrganizationAction.MEMBERSHIP_MANAGE, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization invitation access denied")
    try:
        invitations, next_cursor = await OrganizationInvitationRepository(
            get_organization_invitations_collection()
        ).list_for_organization(
            context.organization_id,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return OrganizationInvitationPageResponse(
        items=[_invitation_response(invitation) for invitation in invitations],
        next_cursor=next_cursor,
    )


@router.get("/members", response_model=OrganizationMemberPageResponse)
@limiter.limit(RateLimits.API_READ)
async def list_organization_members(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, min_length=24, max_length=24),
    _current_user: UserOut = Depends(get_verified_user),
    context: OrganizationContext = Depends(get_active_organization_context),
):
    if not policy.can(context.principal, OrganizationAction.MEMBERSHIP_MANAGE, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization member access denied")

    try:
        memberships, next_cursor = await OrganizationMembershipRepository(
            get_organization_memberships_collection()
        ).list_for_organization(
            context.organization_id,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    member_ids = [
        ObjectId(membership["user_id"])
        for membership in memberships
        if ObjectId.is_valid(membership.get("user_id"))
    ]
    users_by_id = {
        str(user["_id"]): user
        for user in await get_users_collection().find(
            {"_id": {"$in": member_ids}, "status": {"$ne": "deleted"}},
            projection={"email": 1, "username": 1, "profile.full_name": 1},
        ).to_list(length=len(member_ids))
    } if member_ids else {}
    return OrganizationMemberPageResponse(
        items=[
            OrganizationMemberResponse(
            user_id=membership["user_id"],
            email=users_by_id.get(membership["user_id"], {}).get("email"),
            username=users_by_id.get(membership["user_id"], {}).get("username"),
            full_name=(users_by_id.get(membership["user_id"], {}).get("profile") or {}).get("full_name"),
            role=membership["role"],
            status=membership["status"],
        )
            for membership in memberships
        ],
        next_cursor=next_cursor,
    )


@router.post("/invitations/accept")
@limiter.limit(RateLimits.API_WRITE)
async def accept_invitation(
    request: Request,
    payload: InvitationDecisionRequest,
    current_user: UserOut = Depends(get_verified_user),
):
    result = await _invitation_service().accept(
        token=payload.token,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    return {"message": "Invitation accepted", "organization_id": result["membership"]["organization_id"]}


@router.post("/invitations/decline")
@limiter.limit(RateLimits.API_WRITE)
async def decline_invitation(
    request: Request,
    payload: InvitationDecisionRequest,
    current_user: UserOut = Depends(get_verified_user),
):
    await _invitation_service().decline(token=payload.token, user_email=current_user.email)
    return {"message": "Invitation declined"}


@router.post("/invitations/{invitation_id}/revoke", response_model=OrganizationInvitationResponse)
@limiter.limit(RateLimits.API_WRITE)
async def revoke_invitation(
    invitation_id: str,
    request: Request,
    _current_user: UserOut = Depends(get_verified_user),
    context: OrganizationContext = Depends(get_active_organization_context),
):
    if not policy.can(context.principal, OrganizationAction.MEMBERSHIP_MANAGE, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization invitation access denied")
    service = _invitation_service()
    invitation = await service.get_for_revoke(
        invitation_id=invitation_id,
        organization_id=context.organization_id,
    )
    action = (
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE
        if invitation["role"] == "admin"
        else OrganizationAction.MEMBERSHIP_MANAGE
    )
    if not policy.can(context.principal, action, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization invitation access denied")
    invitation = await service.revoke(
        invitation_id=invitation_id,
        organization_id=context.organization_id,
        expected_role=invitation["role"],
    )
    return _invitation_response(invitation)


@router.patch("/memberships/{user_id}")
@limiter.limit(RateLimits.API_WRITE)
async def update_membership_status(
    user_id: str,
    payload: UpdateOrganizationMembershipRequest,
    request: Request,
    _current_user: UserOut = Depends(get_verified_user),
    context: OrganizationContext = Depends(get_active_organization_context),
):
    if not policy.can(context.principal, OrganizationAction.MEMBERSHIP_MANAGE, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership access denied")
    if user_id == context.principal.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use organization transfer to change your own access")
    memberships = OrganizationMembershipRepository(get_organization_memberships_collection())
    target_membership = await memberships.get_membership(
        organization_id=context.organization_id,
        user_id=user_id,
    )
    if target_membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    if target_membership["role"] == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner membership cannot be managed here")
    action = (
        OrganizationAction.MEMBERSHIP_ADMIN_MANAGE
        if target_membership["role"] == "admin"
        else OrganizationAction.MEMBERSHIP_MANAGE
    )
    if not policy.can(context.principal, action, None, context):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization membership access denied")
    membership = await memberships.set_status(
        organization_id=context.organization_id,
        user_id=user_id,
        status=payload.status,
        expected_role=target_membership["role"],
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership changed; refresh and retry")
    return {"message": "Membership updated", "status": membership["status"]}
