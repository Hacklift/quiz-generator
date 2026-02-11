import logging
import random
from fastapi import HTTPException
from typing import Dict

from server.app.quiz.models.quiz_models import QuizRequest
from server.app.quiz.utils.huggingface_utils import generate_quiz_with_huggingface
from server.app.quiz.utils.mock_quiz_generator import get_mock_questions_by_type
from server.app.db.crud.update_quiz_history import update_quiz_history
from server.app.db.crud.ai_generated_quiz_crud import save_ai_generated_quiz


async def get_questions(request: QuizRequest, user_id: str = "defaultUserId") -> Dict:
    """
    Generate quiz questions using Hugging Face AI.
    Falls back to mock data if AI generation fails.
    Notifies frontend when AI is down via 'ai_down' flag and message.
    Automatically saves AI-generated quizzes to the database.
    """
    ai_down = False
    notification_message = None
    ai_quiz_payload = None
    final_questions = []
    quiz_id = None  

    try:
        # === 1. Attempt Hugging Face AI generation ===
        ai_payload = request.dict()
        response = await generate_quiz_with_huggingface(ai_payload)
        
        questions = response.get("questions") if response else None

        # Validate Hugging Face response
        if not questions or isinstance(questions, dict) and "error" in questions:
            raise ValueError("Invalid Hugging Face response")

        if len(questions) < request.num_questions:
            raise ValueError("Not enough questions returned by Hugging Face")

        final_questions = questions[:request.num_questions]

        # Ensure question_type is added to each question
        for q in final_questions:
            q["question_type"] = request.question_type

        source = "huggingface"

        # Prepare payload for saving to DB
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
        # === 2. Notify UI that AI is down ===
        ai_down = True
        notification_message = "AI model is currently unavailable. Using mock questions instead."
        logging.warning(f"Hugging Face fallback triggered: {e}")

        # === 3. Fallback to mock quiz generation ===
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

    # === 4. Update quiz history ===
    update_quiz_history(user_id, final_questions)

    # === 5. Save AI-generated quiz if successful ===
    if source == "huggingface" and ai_quiz_payload:
        try:
            save_result = await save_ai_generated_quiz(ai_quiz_payload)
            if save_result and "quiz_id" in save_result:
                quiz_id = save_result.get("quiz_id")
        except Exception as db_error:
            logging.error(f"Failed to save AI-generated quiz to DB: {db_error}")

    # === 6. Final response ===
    result = {
        "source": source,
        "questions": final_questions,
        "ai_down": ai_down,
        "notification_message": notification_message,
        "quiz_id": quiz_id  
    }

    logging.warning(f"Final API Response: {result}")
    return result
