from dotenv import load_dotenv

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from cryptography.fernet import Fernet
import os
from datetime import datetime

load_dotenv()   

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY is not set in .env")

fernet = Fernet(FERNET_KEY)

client = AsyncIOMotorClient(MONGO_URI)

database = client["quizApp_db"]

quizzes_collection = database["quizzes"]
users_collection = database["users"]
quiz_history_collection = database["quiz_history"]
ai_generated_quizzes_collection = database["ai_generated_quizzes"]


quiz_categories_collection = database["quizzes_category"]
folders_collection = database["folders"]
saved_quizzes_collection = database["saved_quizzes"]
blacklisted_tokens_collection = database["blacklisted_tokens"]
ai_generated_quizzes_collection = database["ai_generated_quizzes"]
user_tokens_collection = database["user_tokens"]


async def ensure_user_indexes(users_collection: AsyncIOMotorCollection):
    await users_collection.create_index("email", unique=True) 
    await users_collection.create_index("username", unique=True) 
    await users_collection.create_index("created_at") 
    await users_collection.create_index("is_active") 

async def ensure_blacklist_indexes(blacklisted_tokens_collection: AsyncIOMotorCollection):
    await blacklisted_tokens_collection.create_index("jti", unique=True)
    index_info = await blacklisted_tokens_collection.index_information()
    expires_index = index_info.get("expires_at_1")
    if expires_index and "expireAfterSeconds" not in expires_index:
        await blacklisted_tokens_collection.drop_index("expires_at_1")
    await blacklisted_tokens_collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="expires_at_1",
    )
async def ensure_ai_quiz_indexes(ai_generated_quizzes_collection: AsyncIOMotorCollection):
    """Indexes for the AI-generated quizzes collection."""
    # Compound unique index: no two identical quizzes with same title and questions
    await ai_generated_quizzes_collection.create_index(
        [("title", 1), ("questions", 1)],
        unique=True
    )


async def ensure_user_tokens_indexes(user_tokens_collection: AsyncIOMotorCollection):
    """Indexes for user tokens collection."""
    await user_tokens_collection.create_index("user_id", unique=True)


async def startUp():
    await ensure_user_indexes(users_collection)
    await ensure_blacklist_indexes(blacklisted_tokens_collection)
    await ensure_ai_quiz_indexes(ai_generated_quizzes_collection)
    await ensure_user_tokens_indexes(user_tokens_collection)

def get_users_collection() -> AsyncIOMotorCollection:
    if users_collection is None:
        raise RuntimeError("[DB Error] users_collection has not been initialized properly.")
    return users_collection

def get_quizzes_collection() -> AsyncIOMotorCollection:
    if quizzes_collection is None:
        raise RuntimeError("[DB Error] quizzes_collection has not been initialized properly.")
    return quizzes_collection

def get_ai_generated_quizzes_collection() -> AsyncIOMotorCollection:
    return ai_generated_quizzes_collection
def get_blacklisted_tokens_collection() -> AsyncIOMotorCollection:
    return blacklisted_tokens_collection
def get_folders_collection() -> AsyncIOMotorCollection:
    if folders_collection is None:
        raise RuntimeError("[DB Error] folders_collection has not been initialized properly.")
    return folders_collection

def get_saved_quizzes_collection() -> AsyncIOMotorCollection:
    if saved_quizzes_collection is None:
        raise RuntimeError("[DB Error] saved_quizzes_collection has not been initialized properly.")
    return saved_quizzes_collection

def get_user_tokens_collection() -> AsyncIOMotorCollection:
    if user_tokens_collection is None:
        raise RuntimeError("[DB Error] user_tokens_collection has not been initialized properly.")
    return user_tokens_collection
