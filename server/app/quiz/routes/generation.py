from fastapi import APIRouter, Depends, HTTPException, status

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


router = APIRouter()


@router.post("/get-questions", response_model=QuizResponse)

async def get_quiz(

    request: QuizRequest,

    current_user=Depends(get_current_user_optional),
    email_service: EmailService = Depends(get_email_service),

):
    if settings.QUIZ_GENERATION_REQUIRES_AUTH and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to generate quizzes.",
        )

    request.num_questions = validate_generation_question_count(request.num_questions)

    user_id = str(current_user.id) if current_user else None
    invitation_repository = LiveQuizInvitationRepository(
        get_live_quiz_invitations_collection()
    )

    return await get_questions(
        request,
        user_id=user_id,
        invitation_repository=invitation_repository,
        email_service=email_service,
    )
