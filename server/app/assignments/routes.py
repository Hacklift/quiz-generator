import re

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

from server.app.assignments.models import (
    CloseAssignmentRequest, CreateAssignmentRequest, AssignmentDetail,
    AssignmentPage, MyAssignmentPage, AttemptPage, AttemptDetail, AssignableQuizPage, RecipientOptionsPage,
)
from server.app.quiz.schemas.live_session_schemas import StartLiveQuizSessionResponse
from server.app.core.dependencies import get_verified_user
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext
from server.app.users.models import UserOut
from server.app.assignments.dependencies import get_assignment_service


router = APIRouter(prefix="/api/v1/assignments", tags=["assignments"])
progress_router = APIRouter(prefix="/api/cohorts", tags=["cohort progress"])


@router.post("", status_code=201, response_model=AssignmentDetail)
@limiter.limit("10/hour")
async def create_assignment(
    payload: CreateAssignmentRequest,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    key = (idempotency_key or "").strip()
    if not 8 <= len(key) <= 200 or not re.fullmatch(r"[A-Za-z0-9._:-]+", key):
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key header is required")
    return await service.create(organization, payload, key)


@router.get("", response_model=AssignmentPage)
async def list_assignments(
    cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.list(organization, cursor=cursor, limit=limit)


@router.get("/mine", response_model=MyAssignmentPage)
async def my_assignments(
    cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.mine(organization, cursor=cursor, limit=limit)


@router.get("/quizzes", response_model=AssignableQuizPage)
async def assignable_quizzes(
    cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.quizzes(organization, cursor=cursor, limit=limit)


@router.get("/recipient-options", response_model=RecipientOptionsPage)
async def recipient_options(
    cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.recipient_options(organization, cursor=cursor, limit=limit)


@router.get("/{assignment_id}", response_model=AssignmentDetail)
async def assignment_detail(
    assignment_id: str, cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.detail(organization, assignment_id, cursor=cursor, limit=limit)


@router.post("/{assignment_id}/start", response_model=StartLiveQuizSessionResponse)
@limiter.limit(RateLimits.API_WRITE)
async def start_assignment(
    assignment_id: str, request: Request, response: Response,
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.start(organization, assignment_id, current_user)


@router.post("/{assignment_id}/close", response_model=AssignmentDetail)
@limiter.limit(RateLimits.API_WRITE)
async def close_assignment(
    assignment_id: str, payload: CloseAssignmentRequest, request: Request, response: Response,
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.close(organization, assignment_id)


@router.get("/{assignment_id}/recipients/{user_id}/attempts", response_model=AttemptPage)
async def recipient_attempts(
    assignment_id: str, user_id: str,
    cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.attempts(organization, assignment_id, user_id, cursor=cursor, limit=limit)


@router.get("/{assignment_id}/recipients/{user_id}/attempts/{session_id}", response_model=AttemptDetail)
async def recipient_attempt_detail(
    assignment_id: str, user_id: str, session_id: str,
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.attempt_detail(organization, assignment_id, user_id, session_id)


@progress_router.get("/{cohort_id}/progress", response_model=AssignmentPage)
async def cohort_progress(
    cohort_id: str, cursor: str | None = None, limit: int = Query(default=25, ge=1, le=100),
    current_user: UserOut = Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
    service=Depends(get_assignment_service),
):
    return await service.list(organization, cohort_id=cohort_id, cursor=cursor, limit=limit)
