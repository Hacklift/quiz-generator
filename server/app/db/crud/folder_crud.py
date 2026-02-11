from ....app.db.core.connection import get_folders_collection
from ....app.db.models.folder_model import FolderModel
from bson import ObjectId
from datetime import datetime

folders_collection = get_folders_collection()


# ✅ Helper function to serialize MongoDB documents
def serialize_folder(folder):
    if not folder:
        return None
    folder["_id"] = str(folder["_id"])
    if "quizzes" in folder:
        # Ensure all nested quiz IDs (if any) are strings
        folder["quizzes"] = [
            str(q) if isinstance(q, ObjectId) else q for q in folder["quizzes"]
        ]
    return folder


# 🟢 Create Folder
async def create_folder(folder_data: dict):
    folder = FolderModel(**folder_data)
    result = await folders_collection.insert_one(folder.dict())
    folder_dict = folder.dict()
    folder_dict["_id"] = str(result.inserted_id)
    return folder_dict


# 🟡 Get All Folders for a User
async def get_user_folders(user_id: str):
    folders = await folders_collection.find({"user_id": user_id}).to_list(100)
    return [serialize_folder(folder) for folder in folders]


# 🟢 Add Quiz to Folder
async def add_quiz_to_folder(folder_id: str, quiz: dict):
    quiz_entry = {
        "_id": str(ObjectId()),
        "title": quiz.get("title", "Untitled Quiz"),
        "quiz_data": quiz.get("quiz_data", {}),
        "saved_at": quiz.get("created_at", datetime.utcnow()),
        "added_on": datetime.utcnow(),
    }

    await folders_collection.update_one(
        {"_id": ObjectId(folder_id)},
        {
            "$push": {"quizzes": quiz_entry},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    updated_folder = await get_folder_by_id(folder_id)
    return serialize_folder(updated_folder)



# 🟠 Remove Quiz from Folder
async def remove_quiz_from_folder(folder_id: str, quiz_id: str):
    await folders_collection.update_one(
        {"_id": ObjectId(folder_id)},
        {
            "$pull": {"quizzes": {"_id": quiz_id}},  # match object inside array
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
    updated_folder = await get_folder_by_id(folder_id)
    return serialize_folder(updated_folder)



# 🟣 Bulk Remove Quizzes from Folder
async def bulk_remove_quizzes_from_folder(folder_id: str, quiz_ids: list[str]):
    await folders_collection.update_one(
        {"_id": ObjectId(folder_id)},
        {
            "$pull": {"quizzes": {"_id": {"$in": quiz_ids}}},  # match by _id field
            "$set": {"updated_at": datetime.utcnow()},
        },
    )
    updated_folder = await get_folder_by_id(folder_id)
    return serialize_folder(updated_folder)


# 🟢 Move Quiz Between Folders
async def move_quiz_between_folders(source_folder_id: str, target_folder_id: str, quiz_id: str):
    # 🧩 Validate IDs
    if not source_folder_id or not target_folder_id or not quiz_id:
        raise ValueError("Missing required folder or quiz IDs for move operation.")

    # ✅ Fetch quiz to move *before* removing it
    source_folder = await folders_collection.find_one(
        {"_id": ObjectId(source_folder_id), "quizzes._id": quiz_id},
        {"quizzes.$": 1}
    )

    if not source_folder or "quizzes" not in source_folder:
        raise ValueError("Quiz not found in source folder.")

    quiz_to_move = source_folder["quizzes"][0]

    # 🟠 Remove from source
    await folders_collection.update_one(
        {"_id": ObjectId(source_folder_id)},
        {
            "$pull": {"quizzes": {"_id": quiz_id}},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    # 🟢 Add to target
    await folders_collection.update_one(
        {"_id": ObjectId(target_folder_id)},
        {
            "$push": {"quizzes": quiz_to_move},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    # ✅ Return updated target folder
    updated_target = await get_folder_by_id(target_folder_id)
    return serialize_folder(updated_target)


# 🔵 Rename Folder
async def rename_folder(folder_id: str, new_name: str):
    await folders_collection.update_one(
        {"_id": ObjectId(folder_id)},
        {"$set": {"name": new_name, "updated_at": datetime.utcnow()}},
    )
    updated_folder = await get_folder_by_id(folder_id)
    return serialize_folder(updated_folder)


# 🔴 Delete Folder
async def delete_folder(folder_id: str):
    await folders_collection.delete_one({"_id": ObjectId(folder_id)})
    return {"message": "Folder deleted", "folder_id": folder_id}


# 🔍 Get Folder by ID
async def get_folder_by_id(folder_id: str):
    folder = await folders_collection.find_one({"_id": ObjectId(folder_id)})
    return serialize_folder(folder)


# 🔴 Bulk Delete Folders
async def bulk_delete_folders(folder_ids: list[str]):
    result = await folders_collection.delete_many({
        "_id": {"$in": [ObjectId(fid) for fid in folder_ids]}
    })
    return result.deleted_count
