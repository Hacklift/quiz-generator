from fastapi import APIRouter, Depends
from ....app.auth.dependencies import get_current_user
from ....app.db.models.quiz_history_models import QuizHistoryModel
from ....app.db.crud.update_quiz_history import update_quiz_history

router = APIRouter()

@router.post("/save-quiz")
async def save_quiz(quiz: QuizHistoryModel, current_user=Depends(get_current_user)):
    quiz.user_id = current_user.id 
    quiz_dict = quiz.model_dump(by_alias=True) 
    inserted_id = await update_quiz_history(quiz_dict)
    return {"message": "Quiz saved", "quiz_id": inserted_id}


