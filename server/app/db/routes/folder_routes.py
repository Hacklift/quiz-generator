from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime
from bson import ObjectId

from ....app.db.crud.folder_crud import (
    create_folder,
    get_user_folders,
    add_quiz_to_folder,
    remove_quiz_from_folder,
    rename_folder,
    delete_folder,
    get_folder_by_id,
    move_quiz_between_folders,
    bulk_delete_folders,
    bulk_remove_quizzes_from_folder,
)
from ....app.db.core.connection import get_saved_quizzes_collection
from ....app.db.models.folder_model import FolderCreate, BulkDeleteFoldersRequest, BulkRemoveRequest
from ....app.auth.dependencies import get_current_user

router = APIRouter(tags=["Folders"])

saved_quizzes_collection = get_saved_quizzes_collection()


class QuizData(BaseModel):
    quiz_id: str  


class MoveQuizRequest(BaseModel):
    quiz_id: str
    from_folder_id: str
    to_folder_id: str


class RenameFolderRequest(BaseModel):
    new_name: str


# -------------------- Folder CRUD --------------------

@router.post("/create")
async def create_new_folder(folder: FolderCreate, user = Depends(get_current_user)):
    folder.user_id = user.id
    new_folder = await create_folder(folder.dict())
    return {"message": "Folder created successfully", "folder": new_folder}


@router.get("/")
async def get_folders_for_user(user = Depends(get_current_user)):
    folders = await get_user_folders(user.id)
    return folders


@router.get("/view/{folder_id}")
async def get_folder_by_id_route(folder_id: str, user = Depends(get_current_user)):
    folder = await get_folder_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")
    return folder


@router.put("/{folder_id}/rename")
async def rename_existing_folder(
    folder_id: str,
    payload: RenameFolderRequest,
    user = Depends(get_current_user),
):
    folder = await get_folder_by_id(folder_id)
    if not folder or folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")
    await rename_folder(folder_id, payload.new_name)
    return {"message": "Folder renamed successfully"}


@router.delete("/{folder_id}")
async def delete_existing_folder(folder_id: str, user = Depends(get_current_user)):
    folder = await get_folder_by_id(folder_id)
    if not folder or folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")
    await delete_folder(folder_id)
    return {"message": "Folder deleted successfully"}


@router.delete("/bulk_delete")
async def bulk_delete_folders_route(req: BulkDeleteFoldersRequest = Body(...), user = Depends(get_current_user)):
    deleted_count = 0
    for fid in req.folder_ids:
        folder = await get_folder_by_id(fid)
        if folder and folder["user_id"] == user.id:
            await bulk_delete_folders(fid)
            deleted_count += 1
    return {"deleted": deleted_count}


# -------------------- Quiz Management --------------------

@router.post("/{folder_id}/add_quiz")
async def add_quiz_to_folder_route(folder_id: str, quiz_data: QuizData, user = Depends(get_current_user)):
    folder = await get_folder_by_id(folder_id)
    if not folder or folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")

    quiz_id = quiz_data.quiz_id
    quiz = await saved_quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found in saved quizzes")

    def convert_object_ids(doc):
        if isinstance(doc, dict):
            return {k: convert_object_ids(v) for k, v in doc.items()}
        elif isinstance(doc, list):
            return [convert_object_ids(i) for i in doc]
        elif isinstance(doc, ObjectId):
            return str(doc)
        return doc

    quiz_entry = {
        "_id": str(ObjectId()),
        "original_quiz_id": str(quiz["_id"]),
        "title": quiz.get("title", "Untitled Quiz"),
        "question_type": quiz.get("question_type", "N/A"),
        "questions": quiz.get("questions", []),
        "created_at": quiz.get("created_at"),
        "added_on": datetime.utcnow(),
        "quiz_data": convert_object_ids(quiz),
    }

    await add_quiz_to_folder(folder_id, quiz_entry)
    return {"message": "Quiz added to folder successfully", "quiz": quiz_entry}


@router.post("/{folder_id}/remove/{quiz_id}")
async def remove_quiz(folder_id: str, quiz_id: str, user = Depends(get_current_user)):
    folder = await get_folder_by_id(folder_id)
    if not folder or folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to folder")

    await remove_quiz_from_folder(folder_id, quiz_id)
    return {"message": "Quiz removed from folder"}


@router.patch("/move_quiz")
async def move_quiz_between_folders_route(request: MoveQuizRequest, user = Depends(get_current_user)):
    source = await get_folder_by_id(request.from_folder_id)
    target = await get_folder_by_id(request.to_folder_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Folder not found")
    if source["user_id"] != user.id or target["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    result = await move_quiz_between_folders(
        request.from_folder_id, request.to_folder_id, request.quiz_id
    )
    return {"message": "Quiz moved successfully", "result": result}


@router.post("/{folder_id}/bulk_remove")
async def bulk_remove_quizzes(folder_id: str, request: BulkRemoveRequest, user = Depends(get_current_user)):
    folder = await get_folder_by_id(folder_id)
    if not folder or folder["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    await bulk_remove_quizzes_from_folder(folder_id, request.quiz_ids)
    return {"message": "Quizzes removed successfully"}
