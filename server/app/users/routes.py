from fastapi import APIRouter, Depends, HTTPException, Request, Response

from server.app.core.config import settings
from server.app.core.dependencies import get_current_user, get_verified_user
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.users.models import (
    UpdatePersonaRequest,
    UpdateProfileRequest,
    UpdateProfileResponse,
    UserOut,
)
from server.app.users.schemas import (
    EmailChangeRequest,
    EmailChangeVerifyRequest,
    MessageResponse,
)
from server.app.users.services import (
    delete_account_service,
    get_user_profile_service,
    request_email_change_service,
    update_user_persona_service,
    update_user_profile_service,
    verify_email_change_service,
)
from server.app.users.repository import build_user_out_payload


router = APIRouter(tags=["Users"])


@router.get("/users")
@limiter.limit("30/minute")
async def get_users(
    request: Request,
    response: Response,
    current_user: UserOut = Depends(get_current_user),
):
    if not settings.ENABLE_PUBLIC_USER_LIST and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = await request.app.state.users_collection.find(
        {"status": {"$ne": "deleted"}},
        projection={
            "hashed_password": 0,
        },
    ).to_list(length=100)
    return [build_user_out_payload(user) for user in users]


@router.get("/auth/profile")
@limiter.limit(RateLimits.API_READ)
async def get_profile(
    request: Request,
    response: Response,
    current_user: UserOut = Depends(get_current_user),
):
    return get_user_profile_service(current_user)


@router.put("/auth/profile", response_model=UpdateProfileResponse)
@limiter.limit(RateLimits.API_WRITE)
async def update_profile(
    request: Request,
    response: Response,
    profile_data: UpdateProfileRequest,
    current_user: UserOut = Depends(get_verified_user),
):
    return await update_user_profile_service(
        profile_data,
        current_user,
        request.app.state.users_collection,
    )


@router.put("/auth/profile/persona", response_model=UpdateProfileResponse)
@limiter.limit(RateLimits.API_WRITE)
async def update_persona(
    request: Request,
    response: Response,
    persona_data: UpdatePersonaRequest,
    current_user: UserOut = Depends(get_current_user),
):
    return await update_user_persona_service(
        persona_data,
        current_user,
        request.app.state.users_collection,
    )


@router.post("/auth/email-change/request", response_model=MessageResponse)
@limiter.limit(RateLimits.API_WRITE)
async def request_email_change(
    request: Request,
    response: Response,
    payload: EmailChangeRequest,
    current_user: UserOut = Depends(get_verified_user),
    email_svc: EmailService = Depends(get_email_service),
):
    return await request_email_change_service(
        payload.new_email,
        current_user,
        request.app.state.users_collection,
        email_svc,
    )


@router.post("/auth/email-change/verify", response_model=MessageResponse)
@limiter.limit(RateLimits.API_WRITE)
async def verify_email_change(
    request: Request,
    response: Response,
    payload: EmailChangeVerifyRequest,
    current_user: UserOut = Depends(get_verified_user),
):
    return await verify_email_change_service(
        payload.otp,
        current_user,
        request.app.state.users_collection,
    )


@router.delete("/auth/account", response_model=MessageResponse)
@limiter.limit(RateLimits.API_WRITE)
async def delete_account(
    request: Request,
    response: Response,
    current_user: UserOut = Depends(get_current_user),
):
    return await delete_account_service(
        current_user,
        request.app.state.users_collection,
    )
