from fastapi import APIRouter, Depends, HTTPException, Query

from server.app.core.dependencies import get_current_user
from server.app.quiz.schemas.quiz_management_schemas import (
    DeleteResourceResponse,
    QuizAttemptResponse,
)
from server.app.quiz.services.quiz_attempt_service import QuizAttemptService


router = APIRouter()
quiz_attempt_service = QuizAttemptService()


@router.get("/quiz-attempts", response_model=list[QuizAttemptResponse])
async def get_quiz_attempts(
    quiz_id: str | None = Query(default=None),
    current_user=Depends(get_current_user),
):
    return await quiz_attempt_service.list_attempts(
        user_id=str(current_user.id),
        quiz_id=quiz_id,
    )


@router.get("/quiz-attempts/{attempt_id}", response_model=QuizAttemptResponse)
async def get_quiz_attempt(
    attempt_id: str,
    current_user=Depends(get_current_user),
):
    attempt = await quiz_attempt_service.get_attempt(
        user_id=str(current_user.id),
        attempt_id=attempt_id,
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    return attempt


@router.delete("/quiz-attempts/{attempt_id}", response_model=DeleteResourceResponse)
async def delete_quiz_attempt(
    attempt_id: str,
    current_user=Depends(get_current_user),
):
    deleted = await quiz_attempt_service.delete_attempt(
        user_id=str(current_user.id),
        attempt_id=attempt_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    return {"message": "Quiz attempt deleted successfully"}
