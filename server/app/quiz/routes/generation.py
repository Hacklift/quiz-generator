from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from server.app.core.rate_limiter import RateLimits, limiter
from server.app.quiz.models.quiz_models import QuizRequest, QuizResponse
from server.app.quiz.services.generation_policy import validate_generation_question_count
from server.app.quiz.utils.questions import get_questions
from server.app.core.dependencies import get_current_user_optional
from server.app.core.config import settings
from server.app.db.core.connection import get_live_quiz_invitations_collection
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService
from server.app.quiz.repositories.v2.repositories.live_quiz_invitation_repository import (
    LiveQuizInvitationRepository,
)
from server.app.i18n.locales import DEFAULT_LOCALE
from server.app.organizations.services import resolve_user_effective_locale


router = APIRouter()


@router.post("/get-questions", response_model=QuizResponse)
@limiter.limit(RateLimits.QUIZ_GENERATE)
async def get_quiz(

    request: Request,
    response: Response,
    payload: QuizRequest,

    current_user=Depends(get_current_user_optional),
    email_service: EmailService = Depends(get_email_service),

):
    if settings.QUIZ_GENERATION_REQUIRES_AUTH and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to generate quizzes.",
        )

    payload.num_questions = validate_generation_question_count(payload.num_questions)

    if not settings.MULTILINGUAL_ENABLED:
        payload.content_locale = DEFAULT_LOCALE

    if current_user:
        payload.content_locale = await resolve_user_effective_locale(
            current_user,
            request.app.state.organizations_collection,
            request.app.state.organization_memberships_collection,
        )
    else:
        payload.content_locale = payload.content_locale or DEFAULT_LOCALE

    if payload.content_locale != DEFAULT_LOCALE and not settings.MULTILINGUAL_GENERATION_ENABLED:
        raise HTTPException(status_code=503, detail="Multilingual generation is temporarily disabled")

    user_id = str(current_user.id) if current_user else None
    invitation_repository = LiveQuizInvitationRepository(
        get_live_quiz_invitations_collection()
    )

    return await get_questions(
        payload,
        user_id=user_id,
        invitation_repository=invitation_repository,
        email_service=email_service,
    )
