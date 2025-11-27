from fastapi import APIRouter, HTTPException, Body
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

router = APIRouter(tags=["Folders"])

saved_quizzes_collection = get_saved_quizzes_collection()


class QuizData(BaseModel):
    quiz_id: str  


class MoveQuizRequest(BaseModel):
    quiz_id: str
    from_folder_id: str
    to_folder_id: str


class BulkDeleteRequest(BaseModel):
    folder_ids: List[str]



@router.post("/create")
async def create_new_folder(folder: FolderCreate):
    new_folder = await create_folder(folder.dict())
    return {"message": "Folder created successfully", "folder": new_folder}


def convert_object_ids(doc):
    if isinstance(doc, dict):
        return {k: convert_object_ids(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [convert_object_ids(i) for i in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    else:
        return doc

@router.get("/{user_id}")
async def get_folders_for_user(user_id: str):
    folders = await get_user_folders(user_id)
    safe_folders = convert_object_ids(folders)
    return safe_folders

@router.post("/{folder_id}/add_quiz")
async def add_quiz_to_folder_route(folder_id: str, quiz_data: QuizData):
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
        else:
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

    return {
        "message": "Quiz added to folder successfully",
        "quiz": quiz_entry,
    }


@router.post("/{folder_id}/remove/{quiz_id}")
async def remove_quiz(folder_id: str, quiz_id: str):
    await remove_quiz_from_folder(folder_id, quiz_id)
    return {"message": "Quiz removed from folder"}


@router.put("/{folder_id}/rename")
async def rename_existing_folder(folder_id: str, new_name: str):
    await rename_folder(folder_id, new_name)
    return {"message": "Folder renamed successfully"}

@router.delete("/bulk_delete")
async def bulk_delete_folder(req: BulkDeleteFoldersRequest = Body(...)):
    try:
        deleted_count = await bulk_delete_folders(req.folder_ids)  
        return {"deleted": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{folder_id}")
async def delete_existing_folder(folder_id: str):
    await delete_folder(folder_id)
    return {"message": "Folder deleted successfully"}


@router.get("/view/{folder_id}")
async def get_folder_by_id_route(folder_id: str):
    folder = await get_folder_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if "quizzes" in folder:
        for quiz in folder["quizzes"]:
            quiz["_id"] = str(quiz.get("_id", ObjectId()))
            quiz["title"] = quiz.get("title") or quiz.get("quiz_data", {}).get("title") or "Untitled Quiz"
            quiz["question_type"] = quiz.get("question_type") or quiz.get("quiz_data", {}).get("question_type") or "N/A"
            quiz["questions"] = quiz.get("questions") or quiz.get("quiz_data", {}).get("questions") or []

    return folder

@router.patch("/move_quiz")
async def move_quiz(request: MoveQuizRequest):
    result = await move_quiz_between_folders(
        request.from_folder_id, request.to_folder_id, request.quiz_id
    )
    return {"message": "Quiz moved successfully", "result": result}

@router.post("/{folder_id}/bulk_remove")
async def bulk_remove_quizzes(folder_id: str, request: BulkRemoveRequest):
    await bulk_remove_quizzes_from_folder(folder_id, request.quiz_ids)
    return {"message": "Quizzes removed successfully"}

