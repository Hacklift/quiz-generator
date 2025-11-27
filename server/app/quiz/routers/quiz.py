from fastapi import APIRouter, HTTPException, Query
from typing import List

from server.app.quiz.models.quiz_models import QuizRequest, QuizResponse
from server.app.quiz.models.grading_models import UserAnswer
from server.app.quiz.utils.questions import get_questions
from server.app.quiz.utils.grading import grade_answers

router = APIRouter()

@router.post("/get-questions", response_model=QuizResponse)
async def get_quiz(request: QuizRequest):
    return await get_questions(request)  

@router.post("/grade-answers")
async def grade_user_answers(
    user_answers: List[UserAnswer],
    source: str = Query("mock", enum=["mock", "ai"])
):
    try:
        graded_result = grade_answers([ua.dict() for ua in user_answers], source)
        return graded_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error grading answers: {str(e)}")
