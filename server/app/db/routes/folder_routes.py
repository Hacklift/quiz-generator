from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from ....app.db.models.folder_model import BulkDeleteFoldersRequest, BulkRemoveRequest, FolderCreate
from ....app.db.services.quiz_dual_write_service import QuizDualWriteService
from ....app.db.services.quiz_user_library_read_service import QuizUserLibraryReadService
from ....app.dependancies import get_current_user


router = APIRouter(tags=["Folders"])
read_service = QuizUserLibraryReadService()
write_service = QuizDualWriteService()


class QuizData(BaseModel):
    quiz_id: str


class MoveQuizRequest(BaseModel):
    quiz_id: str
    from_folder_id: str
    to_folder_id: str


class RenameFolderRequest(BaseModel):
    new_name: str


@router.post("/create")
async def create_new_folder(folder: FolderCreate, user=Depends(get_current_user)):
    new_folder = await write_service.create_folder_v2(
        user_id=user.id,
        name=folder.name,
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
async def get_folders_for_user(user=Depends(get_current_user)):
    return await read_service.get_user_folders(user.id)


@router.get("/view/{folder_id}")
async def get_folder_by_id_route(folder_id: str, user=Depends(get_current_user)):
    try:
        folder = await read_service.get_folder_by_id(folder_id, user.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    return folder


@router.put("/{folder_id}/rename")
async def rename_existing_folder(
    folder_id: str,
    payload: RenameFolderRequest,
    user=Depends(get_current_user),
):
    updated = await write_service.rename_folder_v2(
        folder_id=folder_id,
        user_id=user.id,
        new_name=payload.new_name,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder renamed successfully"}


@router.delete("/{folder_id}")
async def delete_existing_folder(folder_id: str, user=Depends(get_current_user)):
    deleted = await write_service.delete_folder_v2(folder_id=folder_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder deleted successfully"}


@router.delete("/bulk_delete")
async def bulk_delete_folders_route(req: BulkDeleteFoldersRequest = Body(...), user=Depends(get_current_user)):
    deleted_count = 0
    for folder_id in req.folder_ids:
        if await write_service.delete_folder_v2(folder_id=folder_id, user_id=user.id):
            deleted_count += 1
    return {"deleted": deleted_count}


@router.post("/{folder_id}/add_quiz")
async def add_quiz_to_folder_route(folder_id: str, quiz_data: QuizData, user=Depends(get_current_user)):
    try:
        _folder_v2, folder_item = await write_service.add_saved_quiz_to_folder_v2(
            folder_id=folder_id,
            saved_quiz_id=quiz_data.quiz_id,
            user_id=user.id,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "message": "Quiz added to folder successfully",
        "quiz": {
            "id": str(folder_item.id),
            "title": folder_item.display_title,
            "quiz_id": folder_item.quiz_id,
        },
    }


@router.post("/{folder_id}/remove/{quiz_id}")
async def remove_quiz(folder_id: str, quiz_id: str, user=Depends(get_current_user)):
    removed = await write_service.remove_folder_item_v2(
        folder_id=folder_id,
        folder_item_id=quiz_id,
        user_id=user.id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Quiz not found in folder")
    return {"message": "Quiz removed from folder"}


@router.patch("/move_quiz")
async def move_quiz_between_folders_route(request: MoveQuizRequest, user=Depends(get_current_user)):
    moved = await write_service.move_folder_item_v2(
        folder_item_id=request.quiz_id,
        source_folder_id=request.from_folder_id,
        target_folder_id=request.to_folder_id,
        user_id=user.id,
    )
    if not moved:
        raise HTTPException(status_code=404, detail="Quiz not found in source folder")
    return {"message": "Quiz moved successfully"}


@router.post("/{folder_id}/bulk_remove")
async def bulk_remove_quizzes(folder_id: str, request: BulkRemoveRequest, user=Depends(get_current_user)):
    removed = 0
    for quiz_id in request.quiz_ids:
        if await write_service.remove_folder_item_v2(
            folder_id=folder_id,
            folder_item_id=quiz_id,
            user_id=user.id,
        ):
            removed += 1
    return {"message": "Quizzes removed successfully", "removed": removed}
