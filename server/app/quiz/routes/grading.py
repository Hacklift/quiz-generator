import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from server.app.core.dependencies import get_current_user_optional
from server.app.core.rate_limiter import RateLimits, limiter
from server.app.organizations.dependencies import get_optional_active_organization_context
from server.app.organizations.models import OrganizationContext
from server.app.quiz.services.quiz_grading_service import (
    QuizGradingService,
    SubmissionMismatchError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class SubmittedAnswer(BaseModel):
    question_index: int | None = Field(default=None, ge=0)
    question: str | None = None
    user_answer: str | int | bool | dict[str, str]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def require_question_locator(self):
        if self.question_index is None and not self.question:
            raise ValueError("question_index or question is required")
        return self


class GradeQuizRequest(BaseModel):
    answers: list[SubmittedAnswer]

    model_config = ConfigDict(extra="forbid")


@router.post("/quizzes/{quiz_id}/grade")
@limiter.limit(RateLimits.API_WRITE)
async def grade_quiz_submission(
    request: Request,
    response: Response,
    quiz_id: str,
    payload: GradeQuizRequest,
    source: str = Query("mock", enum=["mock", "ai"]),
    current_user=Depends(get_current_user_optional),
    organization: OrganizationContext | None = Depends(get_optional_active_organization_context),
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
            organization_id=organization.organization_id if organization else None,
            organization=organization,
        )
    except SubmissionMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to grade quiz submission", extra={"quiz_id": quiz_id})
        raise HTTPException(status_code=500, detail="Could not grade quiz") from exc

    if graded is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    response.headers["X-Quiz-Attempt-Status"] = (
        "not-requested" if graded.attempt_saved is None
        else "saved" if graded.attempt_saved else "failed"
    )
    return graded.results
