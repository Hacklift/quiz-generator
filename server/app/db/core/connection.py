from dotenv import load_dotenv

import os

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from server.app.quiz.repositories.v2.setup import ensure_v2_collections_and_validators, ensure_v2_indexes
from server.app.users.validators import ensure_user_collections

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "quizApp_db")
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY is not set in .env")

fernet = Fernet(FERNET_KEY)

client = AsyncIOMotorClient(MONGO_URI)

database = client[DB_NAME]

quizzes_collection = database["quizzes"]
users_collection = database["users"]
user_sessions_collection = database["user_sessions"]
auth_events_collection = database["auth_events"]
quiz_history_collection = database["quiz_history"]
ai_generated_quizzes_collection = database["ai_generated_quizzes"]
live_quiz_sessions_collection = database["live_quiz_sessions"]


folders_collection = database["folders"]
saved_quizzes_collection = database["saved_quizzes"]
notifications_collection = database["notifications"]
ai_generated_quizzes_collection = database["ai_generated_quizzes"]
user_tokens_collection = database["user_tokens"]
quizzes_v2_collection = database["quizzes_v2"]
folders_v2_collection = database["folders_v2"]
folder_items_v2_collection = database["folder_items_v2"]
saved_quizzes_v2_collection = database["saved_quizzes_v2"]
quiz_history_v2_collection = database["quiz_history_v2"]
document_rag_cache_collection = database["document_rag_cache"]


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


async def ensure_notification_indexes(notifications_collection: AsyncIOMotorCollection):
    await notifications_collection.create_index([("user_id", 1), ("created_at", -1)])
    await notifications_collection.create_index([("user_id", 1), ("read", 1)])
    index_info = await notifications_collection.index_information()
    expires_index = index_info.get("expires_at_1")
    if expires_index and expires_index.get("expireAfterSeconds") != 0:
        await notifications_collection.drop_index("expires_at_1")
    await notifications_collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="expires_at_1",
    )


async def ensure_live_quiz_session_indexes(
    live_quiz_sessions_collection: AsyncIOMotorCollection,
):
    """Indexes for participant live quiz sessions."""
    await live_quiz_sessions_collection.create_index("quiz_id")
    await live_quiz_sessions_collection.create_index("guest_id")
    await live_quiz_sessions_collection.create_index("status")
    await live_quiz_sessions_collection.create_index("expires_at")


async def ensure_document_rag_cache_indexes(
    document_rag_cache_collection: AsyncIOMotorCollection,
):
    await document_rag_cache_collection.create_index(
        [
            ("document_fingerprint", 1),
            ("embedding_model", 1),
            ("chunk_size_chars", 1),
            ("chunk_overlap_chars", 1),
            ("chunk_limit", 1),
        ],
        unique=True,
        name="document_rag_cache_key",
    )
    await document_rag_cache_collection.create_index(
        [("last_accessed_at", -1)],
        name="document_rag_cache_last_accessed_at",
    )
    await document_rag_cache_collection.create_index(
        [("updated_at", -1)],
        name="document_rag_cache_updated_at",
    )


async def drop_removed_collections():
    if "blacklisted_tokens" in await database.list_collection_names():
        await database.drop_collection("blacklisted_tokens")
    if "quizzes_category" in await database.list_collection_names():
        await database.drop_collection("quizzes_category")


async def startUp():
    await ensure_user_collections(
        database,
        users_collection,
        user_sessions_collection,
        auth_events_collection,
        backfill_limit=100_000,
    )
    await drop_removed_collections()
    await ensure_ai_quiz_indexes(ai_generated_quizzes_collection)
    await ensure_user_tokens_indexes(user_tokens_collection)
    await ensure_notification_indexes(notifications_collection)
    await ensure_live_quiz_session_indexes(live_quiz_sessions_collection)
    await ensure_document_rag_cache_indexes(document_rag_cache_collection)
    await ensure_v2_collections_and_validators(database)
    await ensure_v2_indexes(
        quizzes_v2_collection,
        folders_v2_collection,
        folder_items_v2_collection,
        saved_quizzes_v2_collection,
        quiz_history_v2_collection,
    )

def get_users_collection() -> AsyncIOMotorCollection:
    if users_collection is None:
        raise RuntimeError("[DB Error] users_collection has not been initialized properly.")
    return users_collection


def get_user_sessions_collection() -> AsyncIOMotorCollection:
    if user_sessions_collection is None:
        raise RuntimeError("[DB Error] user_sessions_collection has not been initialized properly.")
    return user_sessions_collection


def get_auth_events_collection() -> AsyncIOMotorCollection:
    if auth_events_collection is None:
        raise RuntimeError("[DB Error] auth_events_collection has not been initialized properly.")
    return auth_events_collection

def get_quizzes_collection() -> AsyncIOMotorCollection:
    if quizzes_collection is None:
        raise RuntimeError("[DB Error] quizzes_collection has not been initialized properly.")
    return quizzes_collection

def get_ai_generated_quizzes_collection() -> AsyncIOMotorCollection:
    return ai_generated_quizzes_collection

def get_notifications_collection() -> AsyncIOMotorCollection:
    if notifications_collection is None:
        raise RuntimeError("[DB Error] notifications_collection has not been initialized properly.")
    return notifications_collection

def get_folders_collection() -> AsyncIOMotorCollection:
    if folders_collection is None:
        raise RuntimeError("[DB Error] folders_collection has not been initialized properly.")
    return folders_collection

def get_saved_quizzes_collection() -> AsyncIOMotorCollection:
    if saved_quizzes_collection is None:
        raise RuntimeError("[DB Error] saved_quizzes_collection has not been initialized properly.")
    return saved_quizzes_collection

def get_quiz_history_collection() -> AsyncIOMotorCollection:
    if quiz_history_collection is None:
        raise RuntimeError("[DB Error] quiz_history_collection has not been initialized properly.")
    return quiz_history_collection

def get_user_tokens_collection() -> AsyncIOMotorCollection:
    if user_tokens_collection is None:
        raise RuntimeError("[DB Error] user_tokens_collection has not been initialized properly.")
    return user_tokens_collection


def get_live_quiz_sessions_collection() -> AsyncIOMotorCollection:
    if live_quiz_sessions_collection is None:
        raise RuntimeError("[DB Error] live_quiz_sessions_collection has not been initialized properly.")
    return live_quiz_sessions_collection


def get_quizzes_v2_collection() -> AsyncIOMotorCollection:
    if quizzes_v2_collection is None:
        raise RuntimeError("[DB Error] quizzes_v2_collection has not been initialized properly.")
    return quizzes_v2_collection


def get_folders_v2_collection() -> AsyncIOMotorCollection:
    if folders_v2_collection is None:
        raise RuntimeError("[DB Error] folders_v2_collection has not been initialized properly.")
    return folders_v2_collection


def get_folder_items_v2_collection() -> AsyncIOMotorCollection:
    if folder_items_v2_collection is None:
        raise RuntimeError("[DB Error] folder_items_v2_collection has not been initialized properly.")
    return folder_items_v2_collection


def get_saved_quizzes_v2_collection() -> AsyncIOMotorCollection:
    if saved_quizzes_v2_collection is None:
        raise RuntimeError("[DB Error] saved_quizzes_v2_collection has not been initialized properly.")
    return saved_quizzes_v2_collection


def get_quiz_history_v2_collection() -> AsyncIOMotorCollection:
    if quiz_history_v2_collection is None:
        raise RuntimeError("[DB Error] quiz_history_v2_collection has not been initialized properly.")
    return quiz_history_v2_collection


def get_document_rag_cache_collection() -> AsyncIOMotorCollection:
    if document_rag_cache_collection is None:
        raise RuntimeError("[DB Error] document_rag_cache_collection has not been initialized properly.")
    return document_rag_cache_collection
