from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from ....app.db.crud.saved_quiz_crud import (
    save_quiz,
    get_saved_quizzes,
    delete_saved_quiz,
    get_saved_quiz_by_id,
)
from ....app.db.models.saved_quiz_model import SavedQuizModel
from ....app.auth.dependencies import get_current_user
from ....app.db.schemas.user_schemas import UserResponseSchema

router = APIRouter(prefix="/saved-quizzes", tags=["Saved Quizzes"])

# ✅ Create (Save quiz)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_saved_quiz(
    quiz: SavedQuizModel,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    print("Received quiz payload:", quiz.dict())
    try:
        quiz_id = await save_quiz(
            user_id=str(current_user.id),
            title=quiz.title,
            question_type=quiz.question_type,
            questions=quiz.questions,
        )
        return {"message": "Quiz saved successfully", "quiz_id": quiz_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Get all saved quizzes for user
@router.get("/", status_code=status.HTTP_200_OK)
async def list_saved_quizzes(
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        quizzes = await get_saved_quizzes(user_id=str(current_user.id))
        return quizzes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Delete saved quiz
@router.delete("/{quiz_id}", status_code=status.HTTP_200_OK)
async def remove_saved_quiz(
    quiz_id: str,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        deleted = await delete_saved_quiz(user_id=str(current_user.id), quiz_id=quiz_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return {"message": "Quiz deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Get a specific saved quiz by ID
@router.get("/{quiz_id}", status_code=status.HTTP_200_OK)
async def get_saved_quiz(
    quiz_id: str,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        if not ObjectId.is_valid(quiz_id):
            raise HTTPException(status_code=400, detail="Invalid quiz ID")

        quiz = await get_saved_quiz_by_id(quiz_id)
        if not quiz or quiz.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=404, detail="Quiz not found or unauthorized")

        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
