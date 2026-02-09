import logging
import random
from fastapi import HTTPException
from typing import Dict

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.huggingface_utils import generate_quiz_with_huggingface
from server.app.quiz.utils.mock_quiz_generator import get_mock_questions_by_type
from server.app.db.crud.ai_generated_quiz_crud import save_ai_generated_quiz


async def get_questions(request: QuizRequest, user_id: str | None = None) -> Dict:
    ai_down = False
    notification_message = None
    ai_quiz_payload = None
    final_questions = []

    try:
        ai_payload = request.dict()
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
            "profession": request.profession,
            "question_type": request.question_type,
            "difficulty_level": request.difficulty_level,
            "num_questions": request.num_questions,
            "audience_type": request.audience_type,
            "custom_instruction": request.custom_instruction,
            "questions": final_questions
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

    if source == "huggingface" and ai_quiz_payload:
        try:
            await save_ai_generated_quiz(ai_quiz_payload)
        except Exception as db_error:
            logging.error(f"Failed to save AI-generated quiz: {db_error}")

    result = {
        "source": source,
        "questions": final_questions,
        "ai_down": ai_down,
        "notification_message": notification_message
    }

    logging.warning(f"Final API Response: {result}")
    return result
