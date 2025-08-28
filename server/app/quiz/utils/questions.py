import logging
import random
from fastapi import HTTPException
from typing import Dict

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.huggingface_utils import generate_quiz_with_huggingface
from server.app.quiz.utils.mock_quiz_generator import get_mock_questions_by_type
from server.api.v1.crud.update_quiz_history import update_quiz_history


def get_questions(request: QuizRequest, user_id: str = "defaultUserId") -> Dict:
    try:
        ai_payload = request.dict()
        response = generate_quiz_with_huggingface(ai_payload)
        questions = response.get("questions")

        if isinstance(questions, dict) and "error" in questions:
            raise ValueError("Hugging Face returned an error")

        if not questions or len(questions) < request.num_questions:
            raise ValueError("Not enough questions from Hugging Face")

        final_questions = questions[:request.num_questions]

        for q in final_questions:
            q["question_type"] = request.question_type

        source = "huggingface"

    except Exception as e:
        logging.warning(f"Hugging Face fallback triggered: {e}")
        question_type = request.question_type
        num_questions = request.num_questions

        mock_data = get_mock_questions_by_type(question_type, num_questions)
        if not mock_data:
            raise HTTPException(
                status_code=400,
                detail=f"No mock data for question type: {question_type}"
            )

        if num_questions > len(mock_data):
            raise HTTPException(
                status_code=400,
                detail=f"Requested {num_questions} questions, but only {len(mock_data)} available in mock data."
            )

        final_questions = random.sample(mock_data, num_questions)

        for q in final_questions:
            q["question_type"] = question_type

        source = "mock"

    update_quiz_history(user_id, final_questions)

    return {
        "source": source,
        "questions": final_questions
    }
