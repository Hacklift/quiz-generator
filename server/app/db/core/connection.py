from dotenv import load_dotenv
load_dotenv()   

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import os
from pathlib import Path

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URI)

database = client["quizApp_db"]

quizzes_collection = database["quizzes"]
users_collection = database["users"]
quiz_history_collection = database["quiz_history"]
quiz_categories_collection = database["quizzes_category"]

async def ensure_user_indexes(users_collection: AsyncIOMotorCollection):
    await users_collection.create_index("email", unique=True) 
    await users_collection.create_index("username", unique=True) 
    await users_collection.create_index("created_at") 
    await users_collection.create_index("is_active") 



async def startUp():
    await ensure_user_indexes(users_collection)

def get_users_collection() -> AsyncIOMotorCollection:
    if users_collection is None:
        raise RuntimeError("[DB Error] users_collection has not been initialized properly.")
    return users_collection

def get_quizzes_collection() -> AsyncIOMotorCollection:
    if quizzes_collection is None:
        raise RuntimeError("[DB Error] quizzes_collection has not been initialized properly.")
    return quizzes_collection