import re
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.core.dependencies import get_training_manager_user, get_verified_user
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.quiz.repositories.live_session_repository import LiveQuizSessionRepository
from server.app.quiz.repositories.training_run_repository import TrainingRunRepository
from server.app.quiz.schemas.live_session_schemas import StartLiveQuizSessionResponse
from server.app.quiz.schemas.training_runs import (
    CreateTrainingRunRequest,
    CloseTrainingRunRequest,
    StartTrainingSessionRequest,
    TrainingAssignmentSummary,
    TrainingRunAccessPreview,
    TrainingRunDetail,
    TrainingRunSummary,
)
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.services.live_quiz_realtime import live_quiz_realtime_broadcaster
from server.app.quiz.services.training_run_service import TrainingRunService
from server.app.quiz.services.training_notification_service import TrainingNotificationService
from server.app.db.core.connection import (
    get_live_quiz_sessions_collection,
    get_quizzes_v2_collection,
    get_training_assignments_collection,
    get_training_audit_events_collection,
    get_training_email_deliveries_collection,
    get_training_runs_collection,
    get_notifications_collection,
    get_users_collection,
)
from server.app.users.models import UserOut


router = APIRouter()


def get_training_run_service(
    quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_v2_collection),
    sessions_collection: AsyncIOMotorCollection = Depends(get_live_quiz_sessions_collection),
    runs_collection: AsyncIOMotorCollection = Depends(get_training_runs_collection),
    assignments_collection: AsyncIOMotorCollection = Depends(get_training_assignments_collection),
    audit_events_collection: AsyncIOMotorCollection = Depends(get_training_audit_events_collection),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
    email_deliveries_collection: AsyncIOMotorCollection = Depends(
        get_training_email_deliveries_collection
    ),
) -> TrainingRunService:
    repository = TrainingRunRepository(
        quizzes_collection,
        runs_collection,
        assignments_collection,
        audit_events_collection,
        sessions_collection,
        email_deliveries_collection,
    )
    notification_service = TrainingNotificationService(
        users_collection,
        notifications_collection,
        runs_collection,
    )
    live_service = LiveQuizSessionService(
        LiveQuizSessionRepository(quizzes_collection, sessions_collection),
        broadcaster=live_quiz_realtime_broadcaster,
        assignment_repository=repository,
        assignment_completion_notifier=notification_service.notify_completion,
        training_owner_completion_notifier=notification_service.notify_run_owner_of_completion,
    )
    return TrainingRunService(
        repository,
        live_service,
        notification_service=notification_service,
    )


@router.get("/training-runs/owned-quizzes")
async def list_owned_training_quizzes(
    current_user: UserOut = Depends(get_training_manager_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.list_owned_quizzes(str(current_user.id))


@router.post("/training-runs", response_model=TrainingRunSummary)
@limiter.limit("10/hour")
async def create_training_run(
    payload: CreateTrainingRunRequest,
    request: Request,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: UserOut = Depends(get_training_manager_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    normalized_key = idempotency_key.strip() if idempotency_key else ""
    if not (
        8 <= len(normalized_key) <= 200
        and re.fullmatch(r"[A-Za-z0-9._:-]+", normalized_key)
    ):
        raise HTTPException(
            status_code=400,
            detail="A valid Idempotency-Key header is required to create a training run",
        )
    return await service.create_run(
        payload, str(current_user.id), normalized_key
    )


@router.get("/training-runs", response_model=List[TrainingRunSummary])
async def list_training_runs(
    current_user: UserOut = Depends(get_training_manager_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.list_owner_runs(str(current_user.id))


@router.get("/training-runs/{run_id}", response_model=TrainingRunDetail)
async def get_training_run(
    run_id: str,
    current_user: UserOut = Depends(get_training_manager_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.get_owner_run(run_id, str(current_user.id))


@router.post("/training-runs/{run_id}/close", response_model=TrainingRunSummary)
async def close_training_run(
    run_id: str,
    payload: CloseTrainingRunRequest,
    current_user: UserOut = Depends(get_training_manager_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.close_owner_run(run_id, str(current_user.id))


@router.get("/training-assignments/mine", response_model=List[TrainingAssignmentSummary])
async def list_my_training_assignments(
    current_user: UserOut = Depends(get_verified_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.list_my_assignments(str(current_user.id), str(current_user.email))


@router.post("/training-assignments/{assignment_id}/start", response_model=StartLiveQuizSessionResponse)
async def start_training_assignment(
    assignment_id: str,
    current_user: UserOut = Depends(get_verified_user),
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.start_assignment(assignment_id, current_user)


@router.get("/training-runs/access/{access_code}", response_model=TrainingRunAccessPreview)
@limiter.limit(RateLimits.PUBLIC)
async def preview_public_training_run(
    access_code: str,
    request: Request,
    response: Response,
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.access_preview(access_code)


@router.post("/training-runs/access/{access_code}/start", response_model=StartLiveQuizSessionResponse)
@limiter.limit("10/minute")
async def start_public_training_run(
    access_code: str,
    payload: StartTrainingSessionRequest,
    request: Request,
    response: Response,
    service: TrainingRunService = Depends(get_training_run_service),
):
    return await service.start_shared_session(
        access_code,
        payload.participant_name,
        str(payload.participant_email) if payload.participant_email else None,
    )
