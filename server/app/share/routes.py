from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import logging
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.core.dependencies import get_current_user
from server.app.core.rate_limiter import limiter
from server.app.db.core.connection import get_quizzes_v2_collection
from server.app.quiz.schemas.quiz_schemas import QuizSchema
from server.app.share.services import SharedQuizReadService
from server.app.share.schemas import (
    ShareEmailRequest,
    ShareEmailResponse,
    ShareQuizResponse,
    SharedQuizDataResponse,
)
from server.app.email_platform.deps import get_email_service
from server.app.email_platform.service import EmailService


logger = logging.getLogger(__name__)

load_dotenv()

share_url = os.getenv("SHARE_URL")

if not share_url:
    raise EnvironmentError("[Config Error] 'SHARE_URL' is not defined in environment")


router = APIRouter()
shared_quiz_read_service = SharedQuizReadService()


@router.get("/get-quiz-id", response_model=QuizSchema)
async def get_random_quiz_id(
    quizzes_v2_collection: AsyncIOMotorCollection = Depends(get_quizzes_v2_collection),
):
    try:
        # Only curated seed quizzes are eligible: user-generated quizzes must
        # never be handed out to anonymous callers.
        quiz_list = await quizzes_v2_collection.aggregate([
            {"$match": {"status": {"$ne": "deleted"}, "source": "seed"}},
            {"$sample": {"size": 1}},
        ]).to_list(length=1)
        if not quiz_list:
            raise HTTPException(detail="Unable to fetch from database!", status_code=404)
        selected_quiz = quiz_list[0]
        return QuizSchema(
            id=str(selected_quiz["_id"]),
            title=selected_quiz["title"],
            description=selected_quiz.get("description"),
            quiz_type=selected_quiz["quiz_type"],
            owner_id=selected_quiz.get("owner_user_id"),
            canonical_quiz_id=str(selected_quiz["_id"]),
            created_at=selected_quiz["created_at"],
            updated_at=selected_quiz["updated_at"],
            questions=selected_quiz["questions"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Error occured while fetching quiz from database: %s", exc)
        raise HTTPException(detail="Unable to fetch from database!", status_code=404)


@router.get("/share-quiz/{quiz_id}", response_model=ShareQuizResponse)
async def get_share_link(quiz_id: str):
    try:
        shareable_link = f"{share_url}/share/{quiz_id}"
        logger.info("shareable link generated successfully")
        return {"link": shareable_link}
    except Exception as exc:
        logger.info("Unable to generate shareable link: %s", exc)
        raise HTTPException(detail="Failed to generate shareable link", status_code=500)


@router.get("/shared-quiz/{quiz_id}", response_model=SharedQuizDataResponse)
async def get_shared_quiz_data(quiz_id: str):
    try:
        shared_quiz = await shared_quiz_read_service.resolve_shared_quiz(quiz_id)
        if not shared_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return shared_quiz
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unable to fetch shared quiz data for %s: %s", quiz_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch shared quiz data.",
        )


@router.post("/share-email", response_model=ShareEmailResponse)
@limiter.limit("5/hour")
async def share_quiz_via_email(
    request: Request,
    response: Response,
    query: ShareEmailRequest,
    email_svc: EmailService = Depends(get_email_service),
    current_user=Depends(get_current_user),
):
    try:
        shared_quiz = await shared_quiz_read_service.resolve_shared_quiz(query.quiz_id)
        if not shared_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        await email_svc.send_email(
            to=query.recipient_email,
            template_id="quiz_link",
            template_vars={
                "title": shared_quiz["title"],
                "description": shared_quiz["description"],
                # Always build the link server-side; never trust a client URL.
                "link": f"{share_url}/share/{query.quiz_id}",
            },
            purpose="quiz_link",
            priority="default",
        )
        logger.info("[API] Share email pipeline triggered for %s and quiz ID %s", query.recipient_email, query.quiz_id)
        return {"message": "Email sent successfully!"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[API Error] Share email pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later.",
        )
