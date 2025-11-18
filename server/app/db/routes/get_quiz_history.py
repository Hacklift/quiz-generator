from fastapi import APIRouter, Depends
from ....app.auth.dependencies import get_current_user
from ....app.db.crud.update_quiz_history import get_quiz_history

router = APIRouter()

@router.get("/quiz-history")
async def get_user_quiz_history(current_user=Depends(get_current_user)):
    """
    Returns quiz history for the currently authenticated user.
    JWT token required in Authorization header.
    """
    user_id = current_user.id
    quizzes = await get_quiz_history(user_id)
    return quizzes
