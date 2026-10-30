from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from server.app.cohorts.dependencies import get_cohort_service
from server.app.cohorts.models import CohortStatus
from server.app.cohorts.schemas import (
    CohortMemberOptionsResponse, CohortMemberPageResponse, CohortMemberResponse,
    CohortPageResponse, CohortResponse, CreateCohortRequest,
    SetCohortMemberRequest, UpdateCohortRequest,
)
from server.app.cohorts.service import CohortService
from server.app.core.dependencies import get_verified_user
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext


router = APIRouter(prefix="/cohorts", tags=["Cohorts"], dependencies=[Depends(get_verified_user)])


@router.get("", response_model=CohortPageResponse)
@limiter.limit(RateLimits.API_READ)
async def list_cohorts(
    request: Request, response: Response,
    cursor: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    status: CohortStatus | None = "active",
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.list_cohorts(context, cursor=cursor, limit=limit, status=status)


@router.post("", response_model=CohortResponse, status_code=201)
@limiter.limit(RateLimits.API_WRITE)
async def create_cohort(
    request: Request, response: Response, payload: CreateCohortRequest,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.create_cohort(payload, context)


@router.get("/member-options", response_model=CohortMemberOptionsResponse)
@limiter.limit(RateLimits.API_READ)
async def member_options(
    request: Request, response: Response,
    cursor: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.member_options(context, cursor=cursor, limit=limit)


@router.get("/{cohort_id}", response_model=CohortResponse)
@limiter.limit(RateLimits.API_READ)
async def get_cohort(
    request: Request, response: Response, cohort_id: str,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.get_cohort(cohort_id, context)


@router.patch("/{cohort_id}", response_model=CohortResponse)
@limiter.limit(RateLimits.API_WRITE)
async def update_cohort(
    request: Request, response: Response, cohort_id: str, payload: UpdateCohortRequest,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.update_cohort(cohort_id, payload, context)


@router.delete("/{cohort_id}", response_model=CohortResponse)
@limiter.limit(RateLimits.API_WRITE)
async def archive_cohort(
    request: Request, response: Response, cohort_id: str,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.archive_cohort(cohort_id, context)


@router.get("/{cohort_id}/members", response_model=CohortMemberPageResponse)
@limiter.limit(RateLimits.API_READ)
async def list_members(
    request: Request, response: Response, cohort_id: str,
    cursor: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=50, ge=1, le=100),
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.list_members(cohort_id, context, cursor=cursor, limit=limit)


@router.post("/{cohort_id}/members", response_model=CohortMemberResponse)
@limiter.limit(RateLimits.API_WRITE)
async def set_member(
    request: Request, response: Response, cohort_id: str, payload: SetCohortMemberRequest,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    return await service.set_member(cohort_id, payload, context)


@router.delete("/{cohort_id}/members/{user_id}", status_code=204)
@limiter.limit(RateLimits.API_WRITE)
async def remove_member(
    request: Request, response: Response, cohort_id: str, user_id: str,
    context: OrganizationContext = Depends(get_active_organization_context),
    service: CohortService = Depends(get_cohort_service),
):
    await service.remove_member(cohort_id, user_id, context)
    response.status_code = 204
    return response
