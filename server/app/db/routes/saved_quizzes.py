from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ....app.db.crud.saved_quiz_crud import delete_saved_quiz, save_quiz
from ....app.db.models.saved_quiz_model import SavedQuizModel
from ....app.db.schemas.user_schemas import UserResponseSchema
from ....app.db.services.quiz_user_library_read_service import QuizUserLibraryReadService
from ....app.db.services.saved_quiz_management_service import SavedQuizManagementService
from ....app.dependancies import get_current_user


router = APIRouter(prefix="/saved-quizzes", tags=["Saved Quizzes"])
read_service = QuizUserLibraryReadService()
saved_quiz_management_service = SavedQuizManagementService()


class RenameSavedQuizRequest(BaseModel):
    title: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_saved_quiz(
    quiz: SavedQuizModel,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        quiz.user_id = str(current_user.id)
        saved_quiz = await save_quiz(
            user_id=quiz.user_id,
            title=quiz.title,
            question_type=quiz.question_type,
            questions=quiz.questions,
            quiz_id=quiz.quiz_id,
        )
        return {
            "message": "Quiz saved successfully",
            "id": str(saved_quiz.id),
            "quiz_id": saved_quiz.quiz_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", status_code=status.HTTP_200_OK)
async def list_saved_quizzes(
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        return await read_service.get_saved_quizzes_for_user(user_id=str(current_user.id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}", status_code=status.HTTP_200_OK)
async def get_saved_quiz(
    quiz_id: str,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        quiz = await read_service.get_saved_quiz_by_id(quiz_id, user_id=str(current_user.id))
        if not quiz or quiz.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=404, detail="Quiz not found or unauthorized")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{quiz_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_saved_quiz_route(
    quiz_id: str,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        duplicated_quiz = await saved_quiz_management_service.duplicate_saved_quiz(
            quiz_id=quiz_id,
            user_id=str(current_user.id),
        )
        if not duplicated_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return {
            "message": "Quiz duplicated successfully",
            "quiz": duplicated_quiz,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{quiz_id}/rename", status_code=status.HTTP_200_OK)
async def rename_saved_quiz_route(
    quiz_id: str,
    payload: RenameSavedQuizRequest,
    current_user: UserResponseSchema = Depends(get_current_user),
):
    try:
        renamed_quiz = await saved_quiz_management_service.rename_saved_quiz(
            quiz_id=quiz_id,
            user_id=str(current_user.id),
            new_title=payload.title,
        )
        if not renamed_quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return {
            "message": "Quiz renamed successfully",
            "quiz": renamed_quiz,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
