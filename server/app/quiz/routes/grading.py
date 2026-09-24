from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from server.app.core.dependencies import get_current_user_optional
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.quiz.services.quiz_grading_service import (
    QuizGradingService,
    SubmissionMismatchError,
)


router = APIRouter()


class SubmittedAnswer(BaseModel):
    question: str
    user_answer: Union[str, int]


class GradeQuizRequest(BaseModel):
    answers: List[SubmittedAnswer]


@router.post("/quizzes/{quiz_id}/grade")
@limiter.limit(RateLimits.API_WRITE)
async def grade_quiz_submission(
    request: Request,
    response: Response,
    quiz_id: str,
    payload: GradeQuizRequest,
    source: str = Query("mock", enum=["mock", "ai"]),
    current_user=Depends(get_current_user_optional),
):
    """Grade a submission against the stored quiz.

    The client sends only the user's answers; correct answers come from the
    stored quiz document and are revealed in the response after submission.
    """
    service = QuizGradingService()
    try:
        graded = await service.grade_submission(
            quiz_id,
            [answer.model_dump() for answer in payload.answers],
            source=source,
            user_id=str(current_user.id) if current_user is not None else None,
        )
    except SubmissionMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error grading answers: {str(exc)}") from exc

    if graded is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return graded
