from bson import ObjectId

from pymongo import MongoClient



MONGO_URI = "mongodb://localhost:27017"

DB_NAME = "quizApp_db"

COLLECTION_NAME = "quiz_folders"



client = MongoClient(MONGO_URI)

db = client[DB_NAME]

folders = db[COLLECTION_NAME]



count = 0

for folder in folders.find():

    quizzes = folder.get("quizzes", [])

    updated_quizzes = []


    for q in quizzes:


        if isinstance(q, str):

            try:

                updated_quizzes.append(ObjectId(q))

            except Exception:

                updated_quizzes.append(q)

        else:

            updated_quizzes.append(q)



    if updated_quizzes != quizzes:

        folders.update_one({"_id": folder["_id"]}, {"$set": {"quizzes": updated_quizzes}})

        count += 1


print(f"✅ Cleanup complete! Updated {count} folder(s).")

