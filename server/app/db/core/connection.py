from dotenv import load_dotenv
load_dotenv()   

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import os
from datetime import datetime



MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

client = AsyncIOMotorClient(MONGO_URI)

database = client["quizApp_db"]

quizzes_collection = database["quizzes"]
users_collection = database["users"]
quiz_history_collection = database["quiz_history"]
blacklisted_tokens_collection = database["blacklisted_tokens"]

async def ensure_user_indexes(users_collection: AsyncIOMotorCollection):
    await users_collection.create_index("email", unique=True) 
    await users_collection.create_index("username", unique=True) 
    await users_collection.create_index("created_at") 
    await users_collection.create_index("is_active") 

async def ensure_blacklist_indexes(blacklisted_tokens_collection: AsyncIOMotorCollection):
    await blacklisted_tokens_collection.create_index("jti", unique=True)
    await blacklisted_tokens_collection.create_index("expires_at")

async def startUp():
    await ensure_user_indexes(users_collection)

def get_users_collection() -> AsyncIOMotorCollection:
    return users_collection

def get_quizzes_collection() -> AsyncIOMotorCollection:
    return quizzes_collection

def get_blacklisted_tokens_collection() -> AsyncIOMotorCollection:
    return blacklisted_tokens_collection