from fastapi import APIRouter, Depends, HTTPException

from server.app.quiz.models.quiz_history_models import QuizHistoryModel
from server.app.quiz.schemas.quiz_management_schemas import (
    DeleteResourceResponse,
    QuizHistoryDetailResponse,
)
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService
from server.app.core.dependencies import get_verified_user
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext


router = APIRouter()
quiz_user_library_service = QuizUserLibraryService()


@router.post("/save-quiz")
async def save_quiz(
    quiz: QuizHistoryModel,
    current_user=Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    quiz.user_id = str(current_user.id)
    quiz_dict = quiz.model_dump(by_alias=True, exclude_none=True)
    quiz_dict["organization_id"] = organization.organization_id
    quiz_dict["created_by_user_id"] = str(current_user.id)
    history_reference = await quiz_user_library_service.create_quiz_history(
        quiz_dict,
        allow_legacy_personal=False,
    )
    return {
        "message": "Quiz saved",
        "id": str(history_reference.id),
        "quiz_id": history_reference.quiz_id,
    }


@router.get("/quiz-history")
async def get_user_quiz_history(
    current_user=Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    """
    Returns quiz history for the currently authenticated user.
    JWT token required in Authorization header.
    """

    user_id = str(current_user.id)
    quizzes = await quiz_user_library_service.list_quiz_history_items(
        user_id=user_id,
        organization_id=organization.organization_id,
        allow_legacy_personal=False,
    )
    return quizzes


@router.get("/quiz-history/{history_id}", response_model=QuizHistoryDetailResponse)
async def get_quiz_history_details(
    history_id: str,
    current_user=Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    quiz = await quiz_user_library_service.get_quiz_history_detail(
        user_id=str(current_user.id),
        history_id=history_id,
        organization_id=organization.organization_id,
        allow_legacy_personal=False,
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz history item not found")
    return quiz


@router.delete("/quiz-history/{history_id}", response_model=DeleteResourceResponse)
async def delete_quiz_history_entry(
    history_id: str,
    current_user=Depends(get_verified_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    deleted = await quiz_user_library_service.delete_quiz_history_entry(
        user_id=str(current_user.id),
        history_id=history_id,
        organization_id=organization.organization_id,
        allow_legacy_personal=False,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Quiz history item not found")
    return {"message": "Quiz history item deleted successfully"}
