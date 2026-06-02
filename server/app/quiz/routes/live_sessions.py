from typing import List, Optional

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorCollection
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from server.app.db.core.connection import (
    get_live_quiz_invitations_collection,
    get_live_quiz_sessions_collection,
    get_quizzes_v2_collection,
    get_user_sessions_collection,
    get_users_collection,
)
from server.app.core.config import settings
from server.app.users.models import UserOut
from server.app.quiz.schemas.quiz_schemas import (
    AccessCodeCreateRequest,
    AccessCodeResponse,
    QuizAccessPreview,
)
from server.app.core.dependencies import get_verified_user
from server.app.quiz.repositories.live_session_repository import (
    LiveQuizSessionRepository,
)
from server.app.quiz.repositories.v2.repositories.live_quiz_invitation_repository import (
    LiveQuizInvitationRepository,
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.users.identity import ACTIVE_USER_STATUSES, coerce_user_status, now_utc
from server.app.users.repository import build_user_out_payload, get_active_session
from server.app.quiz.schemas.live_session_schemas import (
    LiveQuizAnalyticsRow,
    LiveQuizSessionState,
    SaveLiveQuizAnswerRequest,
    SaveLiveQuizAnswerResponse,
    StartLiveQuizSessionRequest,
    StartLiveQuizSessionResponse,
    SubmitLiveQuizSessionResponse,
)
from server.app.quiz.services.live_session_service import LiveQuizSessionService
from server.app.quiz.services.live_quiz_realtime import live_quiz_realtime_broadcaster


router = APIRouter()


def get_live_quiz_service(
    quizzes_v2_collection: AsyncIOMotorCollection = Depends(get_quizzes_v2_collection),
    sessions_collection: AsyncIOMotorCollection = Depends(
        get_live_quiz_sessions_collection
    ),
) -> LiveQuizSessionService:
    repository = LiveQuizSessionRepository(
        quizzes_v2_collection,
        sessions_collection,
    )
    return LiveQuizSessionService(repository, broadcaster=live_quiz_realtime_broadcaster)


def get_live_quiz_invitation_repository(
    invitations_collection: AsyncIOMotorCollection = Depends(
        get_live_quiz_invitations_collection
    ),
) -> LiveQuizInvitationRepository:
    return LiveQuizInvitationRepository(invitations_collection)


def get_participant_token(
    authorization: Optional[str] = Header(default=None),
    x_participant_token: Optional[str] = Header(default=None),
) -> str:
    if x_participant_token:
        return x_participant_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    raise HTTPException(status_code=401, detail="Participant token missing")


@router.post(
    "/quizzes/{quiz_id}/access-code",
    response_model=AccessCodeResponse,
)
async def generate_quiz_access_code(
    quiz_id: str,
    payload: AccessCodeCreateRequest,
    request: Request,
    current_user: UserOut = Depends(get_verified_user),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
    invitation_repository: LiveQuizInvitationRepository = Depends(
        get_live_quiz_invitation_repository
    ),
    email_service: EmailService = Depends(get_email_service),
):
    return await service.generate_access_code(
        quiz_id=quiz_id,
        access_code_expires_at=payload.access_code_expires_at,
        creator_id=current_user.id,
        time_limit_minutes=payload.time_limit_minutes,
        participant_access_mode=payload.participant_access_mode,
        invited_emails=payload.invited_emails,
        send_email_invitations=payload.send_email_invitations,
        invitation_repository=invitation_repository,
        email_service=email_service,
        frontend_origin=request.headers.get("origin"),
    )


@router.get("/quizzes/access/{code}", response_model=QuizAccessPreview)
async def validate_quiz_access_code(
    code: str,
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.validate_access_code(code)


@router.post(
    "/quizzes/access/{code}/start",
    response_model=StartLiveQuizSessionResponse,
)
async def start_live_quiz_session(
    code: str,
    payload: StartLiveQuizSessionRequest,
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
    invitation_repository: LiveQuizInvitationRepository = Depends(
        get_live_quiz_invitation_repository
    ),
):
    return await service.start_session(
        code=code,
        participant_name=payload.participant_name,
        participant_email=str(payload.participant_email)
        if payload.participant_email
        else None,
        invitation_repository=invitation_repository,
    )


@router.get(
    "/live-quiz-sessions/{session_id}",
    response_model=LiveQuizSessionState,
)
async def get_live_quiz_session(
    session_id: str,
    participant_token: str = Depends(get_participant_token),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.get_session_state(session_id, participant_token)


@router.post(
    "/live-quiz-sessions/{session_id}/answers",
    response_model=SaveLiveQuizAnswerResponse,
)
async def save_live_quiz_answer(
    session_id: str,
    payload: SaveLiveQuizAnswerRequest,
    participant_token: str = Depends(get_participant_token),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.save_answer(
        session_id=session_id,
        participant_token=participant_token,
        question_index=payload.question_index,
        selected_answer=payload.selected_answer,
        next_question_index=payload.next_question_index,
    )


@router.post(
    "/live-quiz-sessions/{session_id}/submit",
    response_model=SubmitLiveQuizSessionResponse,
)
async def submit_live_quiz_session(
    session_id: str,
    auto_submitted: bool = False,
    participant_token: str = Depends(get_participant_token),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
    invitation_repository: LiveQuizInvitationRepository = Depends(
        get_live_quiz_invitation_repository
    ),
):
    return await service.submit_session(
        session_id=session_id,
        participant_token=participant_token,
        auto_submitted=auto_submitted,
        invitation_repository=invitation_repository,
    )


@router.post("/live-quiz-sessions/{session_id}/disconnect")
async def disconnect_live_quiz_session(
    session_id: str,
    participant_token: str = Depends(get_participant_token),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.mark_disconnected(
        session_id=session_id,
        participant_token=participant_token,
    )


@router.get(
    "/quizzes/{quiz_id}/live-sessions",
    response_model=List[LiveQuizAnalyticsRow],
)
async def list_live_quiz_sessions(
    quiz_id: str,
    current_user: UserOut = Depends(get_verified_user),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.list_analytics(quiz_id, current_user.id)


@router.get(
    "/quizzes/{quiz_id}/live-sessions/participants",
    response_model=List[LiveQuizAnalyticsRow],
)
async def list_live_quiz_participants(
    quiz_id: str,
    current_user: UserOut = Depends(get_verified_user),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
):
    return await service.list_analytics(quiz_id, current_user.id)


async def _get_verified_user_from_websocket_token(
    token: str,
    users_collection: AsyncIOMotorCollection,
    sessions_collection: AsyncIOMotorCollection,
) -> UserOut:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        session_id: str = payload.get("sid")
        token_type: str = payload.get("type")
        if not user_id or not jti or not session_id or token_type != "access":
            raise ValueError("Invalid token")
    except (ExpiredSignatureError, InvalidTokenError, DecodeError, ValueError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    if not user:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    if coerce_user_status(user) not in ACTIVE_USER_STATUSES:
        raise HTTPException(status_code=403, detail="Account is not active")

    session = await get_active_session(
        sessions_collection,
        session_id=session_id,
        user_id=user_id,
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Session has been revoked")

    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_seen_at": now_utc()}},
    )

    user_payload = build_user_out_payload(user)
    created_at = user_payload.get("created_at")
    if hasattr(created_at, "isoformat"):
        user_payload["created_at"] = created_at.isoformat()
    return UserOut(**user_payload)


@router.websocket("/quizzes/{quiz_id}/live-sessions/ws")
async def live_quiz_participants_ws(
    websocket: WebSocket,
    quiz_id: str,
    token: str = Query(default=""),
    service: LiveQuizSessionService = Depends(get_live_quiz_service),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
    sessions_collection: AsyncIOMotorCollection = Depends(get_user_sessions_collection),
):
    try:
        current_user = await _get_verified_user_from_websocket_token(
            token,
            users_collection,
            sessions_collection,
        )
        rows = await service.list_analytics(quiz_id, current_user.id)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await live_quiz_realtime_broadcaster.connect(quiz_id, websocket)
    try:
        await websocket.send_json(
            {
                "type": "participants_snapshot",
                "quiz_id": quiz_id,
                "participants": rows,
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        live_quiz_realtime_broadcaster.disconnect(quiz_id, websocket)
