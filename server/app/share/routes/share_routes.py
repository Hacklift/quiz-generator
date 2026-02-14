from fastapi import APIRouter, HTTPException, Depends, status
import random
from motor.motor_asyncio import AsyncIOMotorCollection
import os
import logging
from typing import Any, Dict, Optional
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from ...db.core.connection import (
    get_quizzes_collection,
    get_ai_generated_quizzes_collection,
    get_saved_quizzes_collection,
)
from ...db.crud.quiz_crud import list_quizzes
from ...db.schemas.quiz_schemas import QuizSchema
from .share_schemas import (
    ShareQuizResponse,
    ShareEmailRequest,
    ShareEmailResponse,
    SharedQuizDataResponse,
)

from server.app.email_platform.service import EmailService
from server.app.email_platform.deps import get_email_service


logger = logging.getLogger(__name__)
load_dotenv()  

share_url = os.getenv("SHARE_URL")
if not share_url:
    raise EnvironmentError("[Config Error] 'SHARE_URL' is not defined in environment")

router = APIRouter()

def build_default_description(topic: str) -> str:
    return f"A quiz to test your knowledge on {topic}"


def normalize_shared_quiz(
    quiz_doc: Dict[str, Any],
    quiz_id: str,
    source: str,
) -> Dict[str, Any]:
    if source == "quizzes":
        title = quiz_doc.get("title") or "General Knowledge"
        description = quiz_doc.get("description") or build_default_description(title)
        quiz_type = quiz_doc.get("quiz_type") or "multichoice"
    elif source == "ai_generated_quizzes":
        profession = quiz_doc.get("profession") or "General Knowledge"
        title = profession
        description = quiz_doc.get("description") or build_default_description(profession)
        quiz_type = quiz_doc.get("question_type") or "multichoice"
    elif source == "saved_quizzes":
        title = quiz_doc.get("title") or "General Knowledge"
        topic = quiz_doc.get("profession") or title
        description = quiz_doc.get("description") or build_default_description(topic)
        quiz_type = quiz_doc.get("question_type") or "multichoice"
    else:
        raise ValueError(f"Unsupported source for shared quiz normalization: {source}")

    return {
        "id": quiz_id,
        "title": title,
        "description": description,
        "quiz_type": quiz_type,
        "questions": quiz_doc.get("questions", []),
    }


async def resolve_shared_quiz(quiz_id: str) -> Optional[Dict[str, Any]]:
    try:
        object_id = ObjectId(quiz_id)
    except InvalidId:
        return None

    quizzes_collection = get_quizzes_collection()
    ai_collection = get_ai_generated_quizzes_collection()
    saved_collection = get_saved_quizzes_collection()

    regular_quiz = await quizzes_collection.find_one({"_id": object_id}, projection={"_id": 0})
    if regular_quiz:
        return normalize_shared_quiz(regular_quiz, quiz_id, "quizzes")

    ai_quiz = await ai_collection.find_one({"_id": object_id}, projection={"_id": 0})
    if ai_quiz:
        return normalize_shared_quiz(ai_quiz, quiz_id, "ai_generated_quizzes")

    saved_quiz = await saved_collection.find_one({"_id": object_id}, projection={"_id": 0})
    if saved_quiz:
        return normalize_shared_quiz(saved_quiz, quiz_id, "saved_quizzes")

    return None


@router.get("/get-quiz-id", response_model=QuizSchema)
async def get_random_quiz_id(quizzes_collection: AsyncIOMotorCollection = Depends(get_quizzes_collection)):
    try:
        quiz_List = await list_quizzes(quizzes_collection)
        selected_quiz = random.choice(quiz_List)
        return selected_quiz
    except Exception as e:
        logger.info(f"Error occured while fetching quiz from database: {e}")
        raise HTTPException(detail=f"Unable to fetch from database!", status_code=404)


@router.get("/share-quiz/{quiz_id}", response_model=ShareQuizResponse)
async def get_share_link(quiz_id: str):
    try:
        shareable_link = f"{share_url}/share/{quiz_id}"
        logger.info(f"shareable link generated successfully")
        return {"link": shareable_link}
    except Exception as e:
        logger.info(f"Unable to generate shareable link: {e}")
        raise HTTPException(detail="Failed to generate shareable link", status_code=500)


@router.get("/shared-quiz/{quiz_id}", response_model=SharedQuizDataResponse)
async def get_shared_quiz_data(quiz_id: str):
    try:
        shared_quiz = await resolve_shared_quiz(quiz_id)
        if not shared_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return shared_quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unable to fetch shared quiz data for {quiz_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch shared quiz data.",
        )


@router.post("/share-email", response_model=ShareEmailResponse)
async def share_quiz_via_email(
    query: ShareEmailRequest,
    email_svc: EmailService = Depends(get_email_service),
):
    try:
        shared_quiz = await resolve_shared_quiz(query.quiz_id)
        if not shared_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        
        await email_svc.send_email(
            to=query.recipient_email,
            template_id="quiz_link",
            template_vars={
                "title": shared_quiz["title"],
                "description": shared_quiz["description"],
                "link": query.shareableLink,
            },
            purpose="quiz_link",
            priority="default",
        )
        logger.info(f"[API] Share email pipeline triggered for {query.recipient_email} and quiz ID {query.quiz_id}")
        return {"message": "Email sent successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API Error] Share email pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later."
        )
