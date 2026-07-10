import logging
import random
from fastapi import HTTPException
from typing import Dict
from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.huggingface_utils import generate_quiz_with_huggingface
from server.app.quiz.utils.mock_quiz_generator import get_mock_questions_by_type
from server.app.quiz.repositories.ai_generated_quiz_repository import save_ai_generated_quiz
from server.app.db.core.connection import (
    get_live_quiz_sessions_collection,
    get_quizzes_v2_collection,
)
from server.app.quiz.repositories.live_session_repository import LiveQuizSessionRepository
from server.app.quiz.services.live_session_service import LiveQuizSessionService


async def get_questions(
    request: QuizRequest,
    user_id: str | None = None,
    invitation_repository=None,
    email_service=None,
    frontend_origin: str | None = None,
) -> Dict:

    ai_down = False
    notification_message = None
    ai_quiz_payload = None
    final_questions = []
    quiz_id = None  
    live_access_code = None
    live_access_code_expires_at = None
    live_time_limit_minutes = None
    category_metadata = {
        "category": None,
        "category_slug": None,
        "subcategory": None,
        "subcategory_slug": None,
        "tags": [],
        "classification": None,
    }
    live_participant_access_mode = None
    live_invited_emails = []
    live_invitations_created = 0
    live_invitations_delivered = 0

    base_quiz_payload = {
        "profession": request.profession,
        "question_type": request.question_type,
        "difficulty_level": request.difficulty_level,
        "num_questions": request.num_questions,
        "audience_type": request.audience_type,
        "custom_instruction": request.custom_instruction,
        "token": request.token,
        "user_id": user_id,
    }

    try:
        ai_payload = request.model_dump()
        if user_id:
            ai_payload["user_id"] = user_id

        response = await generate_quiz_with_huggingface(ai_payload)
        questions = response.get("questions") if response else None

        if not questions or (isinstance(questions, dict) and "error" in questions):

            raise ValueError("Invalid Hugging Face response")

        if len(questions) < request.num_questions:
            raise ValueError("Not enough questions returned by Hugging Face")

        final_questions = questions[:request.num_questions]

        for q in final_questions:
            q["question_type"] = request.question_type
        source = "huggingface"

        ai_quiz_payload = {
            **base_quiz_payload,
            "questions": final_questions,

        }

    except Exception as e:
        ai_down = True
        notification_message = "AI model is currently unavailable. Using mock questions instead."
        logging.warning(f"Hugging Face fallback triggered: {e}")

        mock_data = get_mock_questions_by_type(request.question_type, request.num_questions)

        if not mock_data:
            raise HTTPException(
                status_code=400,
                detail=f"No mock data for question type: {request.question_type}"
            )

        if request.num_questions > len(mock_data):
            raise HTTPException(
                status_code=400,
                detail=f"Requested {request.num_questions} but only {len(mock_data)} available."
            )

        final_questions = random.sample(mock_data, request.num_questions)
        for q in final_questions:
            q["question_type"] = request.question_type
        source = "mock"

    if user_id:
        try:
            save_result = await save_ai_generated_quiz(
                ai_quiz_payload
                or {
                    **base_quiz_payload,
                    "questions": final_questions,
                }
            )
            if save_result and "quiz_id" in save_result:
                quiz_id = save_result.get("quiz_id")
                category_metadata = {
                    "category": save_result.get("category"),
                    "category_slug": save_result.get("category_slug"),
                    "subcategory": save_result.get("subcategory"),
                    "subcategory_slug": save_result.get("subcategory_slug"),
                    "tags": save_result.get("tags") or [],
                    "classification": save_result.get("classification"),
                }
        except Exception as db_error:
            logging.error(f"Failed to save generated quiz to DB: {db_error}")

    if request.live_quiz_enabled:
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Login is required to generate a live quiz access code",
            )
        if not quiz_id:
            try:
                save_result = await save_ai_generated_quiz(
                    {
                        **base_quiz_payload,
                        "questions": final_questions,
                    }
                )
                if save_result and "quiz_id" in save_result:
                    quiz_id = save_result.get("quiz_id")
                    category_metadata = {
                        "category": save_result.get("category"),
                        "category_slug": save_result.get("category_slug"),
                        "subcategory": save_result.get("subcategory"),
                        "subcategory_slug": save_result.get("subcategory_slug"),
                        "tags": save_result.get("tags") or [],
                        "classification": save_result.get("classification"),
                    }
            except Exception as db_error:
                logging.error(f"Failed to save live quiz before access-code generation: {db_error}")
        if not quiz_id:
            raise HTTPException(
                status_code=400,
                detail="Live quiz access code could not be generated because the quiz was not saved",
            )
        if not request.time_limit_minutes or not request.access_code_expires_at:
            raise HTTPException(
                status_code=400,
                detail="Live quiz duration and access code expiration are required",
            )

        live_service = LiveQuizSessionService(
            LiveQuizSessionRepository(
                get_quizzes_v2_collection(),
                get_live_quiz_sessions_collection(),
            )
        )
        live_config = await live_service.generate_access_code(
            quiz_id=quiz_id,
            access_code_expires_at=request.access_code_expires_at,
            creator_id=user_id,
            time_limit_minutes=request.time_limit_minutes,
            participant_access_mode=request.participant_access_mode,
            invited_emails=request.invited_emails,
            send_email_invitations=request.send_email_invitations,
            invitation_repository=invitation_repository,
            email_service=email_service,
            frontend_origin=frontend_origin,
        )
        live_access_code = live_config["access_code"]
        live_access_code_expires_at = live_config["access_code_expires_at"]
        live_time_limit_minutes = live_config["time_limit_minutes"]
        live_participant_access_mode = live_config["participant_access_mode"]
        live_invited_emails = live_config["invited_emails"]
        live_invitations_created = live_config["invitations_created"]
        live_invitations_delivered = live_config["invitations_delivered"]

    result = {
        "source": source,
        "questions": final_questions,
        "ai_down": ai_down,
        "notification_message": notification_message,
        "quiz_id": quiz_id,
        "live_quiz_enabled": bool(live_access_code),
        "access_code": live_access_code,
        "time_limit_minutes": live_time_limit_minutes,
        "access_code_expires_at": live_access_code_expires_at,
        **category_metadata,
        "participant_access_mode": live_participant_access_mode,
        "invited_emails": live_invited_emails,
        "invitations_created": live_invitations_created,
        "invitations_delivered": live_invitations_delivered,
    }

    logging.warning(f"Final API Response: {result}")
    return result
