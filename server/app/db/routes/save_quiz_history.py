from fastapi import APIRouter, Depends

from ....app.dependancies import get_current_user

from ....app.db.models.quiz_history_models import QuizHistoryModel

from ....app.db.crud.update_quiz_history import update_quiz_history


router = APIRouter()


@router.post("/save-quiz")

async def save_quiz(quiz: QuizHistoryModel, current_user=Depends(get_current_user)):

    quiz.user_id = str(current_user.id)

    quiz_dict = quiz.model_dump(by_alias=True, exclude_none=True)

    history_reference = await update_quiz_history(quiz_dict)

    return {
        "message": "Quiz saved",
        "id": str(history_reference.id),
        "quiz_id": history_reference.quiz_id,
    }
