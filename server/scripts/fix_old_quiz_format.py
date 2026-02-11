from pymongo import MongoClient
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017")
db = client["quizApp_db"]
folders = db["quiz_folders"]

updated_count = 0

for folder in folders.find():
    updated = False
    quizzes = folder.get("quizzes", [])

    for quiz in quizzes:
        # Old format: {"quiz_id": "..."}
        if "quiz_id" in quiz and "_id" not in quiz:
            quiz["_id"] = str(quiz["quiz_id"])  # copy old ID to new key
            del quiz["quiz_id"]
            updated = True

    if updated:
        folders.update_one(
            {"_id": folder["_id"]},
            {"$set": {"quizzes": quizzes}}
        )
        updated_count += 1

print(f"✅ Updated {updated_count} folder(s) to new quiz format.")
