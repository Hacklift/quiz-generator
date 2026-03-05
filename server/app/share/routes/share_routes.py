from fastapi import APIRouter, HTTPException, Depends, status

import random

from motor.motor_asyncio import AsyncIOMotorCollection

import os

import logging

from dotenv import load_dotenv

from ...db.core.connection import get_quizzes_collection

from ...db.crud.quiz_crud import list_quizzes, get_quiz

from ...db.schemas.quiz_schemas import QuizSchema

from .share_schemas import (

    ShareQuizResponse,

    ShareEmailRequest,

    ShareEmailResponse)



from server.app.email_platform.service import EmailService

from server.app.email_platform.deps import get_email_service



logger = logging.getLogger(__name__)

load_dotenv()


share_url = os.getenv("SHARE_URL")

if not share_url:

    raise EnvironmentError("[Config Error] 'SHARE_URL' is not defined in environment")


router = APIRouter()



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



@router.post("/share-email", response_model=ShareEmailResponse)

async def share_quiz_via_email(

    query: ShareEmailRequest,

    email_svc: EmailService = Depends(get_email_service),

):

    try:

        collection = get_quizzes_collection()

        quiz = await get_quiz(collection, query.quiz_id)



        await email_svc.send_email(

            to=query.recipient_email,

            template_id="quiz_link",

            template_vars={

                "title": quiz.title,

                "description": quiz.description,

                "link": query.shareableLink,

            },

            purpose="quiz_link",

            priority="default",

        )

        logger.info(f"[API] Share email pipeline triggered for {query.recipient_email} and quiz ID {query.quiz_id}")

        return {"message": "Email sent successfully!"}


    except Exception as e:

        logger.error(f"[API Error] Share email pipeline failed: {e}", exc_info=True)

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Failed to send email. Please try again later."

        )

