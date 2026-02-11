from fastapi import APIRouter, HTTPException
from bson import ObjectId
from ....app.db.crud.saved_quiz_crud import (
    save_quiz,
    get_saved_quizzes,
    delete_saved_quiz,
    get_saved_quiz_by_id,
)
from ....app.db.models.saved_quiz_model import SavedQuizModel

router = APIRouter(prefix="/saved-quizzes", tags=["Saved Quizzes"])

# Dummy user ID (until authentication is added)
DUMMY_USER_ID = "user_123"

# ✅ Create (Save quiz)
@router.post("/")
async def create_saved_quiz(quiz: SavedQuizModel):
    print("Received quiz payload:", quiz.dict())
    try:
        quiz_id = await save_quiz(
            user_id=DUMMY_USER_ID,
            title=quiz.title,
            question_type=quiz.question_type,
            questions=quiz.questions,
        )
        return {"message": "Quiz saved successfully", "quiz_id": quiz_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Get all saved quizzes for user
@router.get("/")
async def list_saved_quizzes():
    try:
        quizzes = await get_saved_quizzes(DUMMY_USER_ID)
        return quizzes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Delete saved quiz
@router.delete("/{quiz_id}")
async def remove_saved_quiz(quiz_id: str):
    try:
        deleted = await delete_saved_quiz(quiz_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return {"message": "Quiz deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}")
async def get_saved_quiz(quiz_id: str):
    try:
        if not ObjectId.is_valid(quiz_id):
            raise HTTPException(status_code=400, detail="Invalid quiz ID")
        
        quiz = await get_saved_quiz_by_id(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))