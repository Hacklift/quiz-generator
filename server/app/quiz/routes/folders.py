from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from server.app.quiz.models.folder_model import BulkDeleteFoldersRequest, BulkRemoveRequest, FolderCreate
from server.app.quiz.services.quiz_user_library_service import QuizUserLibraryService
from server.app.core.dependencies import get_current_user
from server.app.organizations.dependencies import get_active_organization_context
from server.app.organizations.models import OrganizationContext


router = APIRouter(tags=["Folders"])
quiz_user_library_service = QuizUserLibraryService()


class QuizData(BaseModel):
    quiz_id: str


class MoveQuizRequest(BaseModel):
    quiz_id: str
    from_folder_id: str
    to_folder_id: str


class RenameFolderRequest(BaseModel):
    new_name: str


@router.post("/create")
async def create_new_folder(
    folder: FolderCreate,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    new_folder = await quiz_user_library_service.create_folder(
        user_id=user.id,
        name=folder.name,
        organization_id=organization.organization_id,
    )
    return {
        "message": "Folder created successfully",
        "folder": {
            "id": str(new_folder.id),
            "user_id": new_folder.user_id,
            "name": new_folder.name,
            "quizzes": [],
            "quiz_count": 0,
            "created_at": new_folder.created_at.isoformat(),
            "updated_at": new_folder.updated_at.isoformat(),
        },
    }


@router.get("/")
async def get_folders_for_user(
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    return await quiz_user_library_service.list_folders(
        user_id=user.id,
        organization_id=organization.organization_id,
        allow_legacy_personal=organization.organization_kind == "personal",
    )


@router.get("/view/{folder_id}")
async def get_folder_by_id_route(
    folder_id: str,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    try:
        folder = await quiz_user_library_service.get_folder(
            folder_id=folder_id,
            user_id=user.id,
            organization_id=organization.organization_id,
            allow_legacy_personal=organization.organization_kind == "personal",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    return folder


@router.delete("/bulk_delete")
async def bulk_delete_folders_route(
    req: BulkDeleteFoldersRequest = Body(...),
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    deleted_count = 0
    for folder_id in req.folder_ids:
        if await quiz_user_library_service.delete_folder(
            folder_id=folder_id,
            user_id=user.id,
            organization_id=organization.organization_id,
            allow_legacy_personal=organization.organization_kind == "personal",
        ):
            deleted_count += 1
    return {"deleted": deleted_count}


@router.put("/{folder_id}/rename")
async def rename_existing_folder(
    folder_id: str,
    payload: RenameFolderRequest,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    updated = await quiz_user_library_service.rename_folder(
        folder_id=folder_id,
        user_id=user.id,
        new_name=payload.new_name,
        organization_id=organization.organization_id,
        allow_legacy_personal=organization.organization_kind == "personal",
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder renamed successfully"}


@router.delete("/{folder_id}")
async def delete_existing_folder(
    folder_id: str,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    deleted = await quiz_user_library_service.delete_folder(
        folder_id=folder_id,
        user_id=user.id,
        organization_id=organization.organization_id,
        allow_legacy_personal=organization.organization_kind == "personal",
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder deleted successfully"}


@router.post("/{folder_id}/add_quiz")
async def add_quiz_to_folder_route(
    folder_id: str,
    quiz_data: QuizData,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    try:
        _folder_v2, folder_item = await quiz_user_library_service.add_saved_quiz_to_folder(
            folder_id=folder_id,
            saved_quiz_id=quiz_data.quiz_id,
            user_id=user.id,
            organization_id=organization.organization_id,
            allow_legacy_personal=organization.organization_kind == "personal",
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "message": "Quiz added to folder successfully",
        "quiz": {
            "id": str(folder_item.id),
            "saved_quiz_id": folder_item.saved_quiz_id,
            "title": folder_item.display_title,
            "quiz_id": folder_item.quiz_id,
        },
    }


@router.post("/{folder_id}/remove/{quiz_id}")
async def remove_quiz(
    folder_id: str,
    quiz_id: str,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    removed = await quiz_user_library_service.remove_folder_item(
        folder_id=folder_id,
        folder_item_id=quiz_id,
        user_id=user.id,
        organization_id=organization.organization_id,
        allow_legacy_personal=organization.organization_kind == "personal",
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Quiz not found in folder")
    return {"message": "Quiz removed from folder"}


@router.patch("/move_quiz")
async def move_quiz_between_folders_route(
    request: MoveQuizRequest,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    moved = await quiz_user_library_service.move_folder_item(
        folder_item_id=request.quiz_id,
        source_folder_id=request.from_folder_id,
        target_folder_id=request.to_folder_id,
        user_id=user.id,
        organization_id=organization.organization_id,
        allow_legacy_personal=organization.organization_kind == "personal",
    )
    if not moved:
        raise HTTPException(status_code=404, detail="Quiz not found in source folder")
    return {"message": "Quiz moved successfully"}


@router.post("/{folder_id}/bulk_remove")
async def bulk_remove_quizzes(
    folder_id: str,
    request: BulkRemoveRequest,
    user=Depends(get_current_user),
    organization: OrganizationContext = Depends(get_active_organization_context),
):
    removed = 0
    for quiz_id in request.quiz_ids:
        if await quiz_user_library_service.remove_folder_item(
            folder_id=folder_id,
            folder_item_id=quiz_id,
            user_id=user.id,
            organization_id=organization.organization_id,
            allow_legacy_personal=organization.organization_kind == "personal",
        ):
            removed += 1
    return {"message": "Quizzes removed successfully", "removed": removed}
