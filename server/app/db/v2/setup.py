from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from .constants import (
    FOLDER_ITEMS_V2_COLLECTION,
    FOLDERS_V2_COLLECTION,
    QUIZ_HISTORY_V2_COLLECTION,
    QUIZZES_V2_COLLECTION,
    SAVED_QUIZZES_V2_COLLECTION,
)
from .indexes import (
    ensure_folder_items_v2_indexes,
    ensure_folders_v2_indexes,
    ensure_quiz_history_v2_indexes,
    ensure_quizzes_v2_indexes,
    ensure_saved_quizzes_v2_indexes,
)
from .validators import get_v2_collection_validators


V2_COLLECTION_INDEXERS = {
    QUIZZES_V2_COLLECTION: ensure_quizzes_v2_indexes,
    FOLDERS_V2_COLLECTION: ensure_folders_v2_indexes,
    FOLDER_ITEMS_V2_COLLECTION: ensure_folder_items_v2_indexes,
    SAVED_QUIZZES_V2_COLLECTION: ensure_saved_quizzes_v2_indexes,
    QUIZ_HISTORY_V2_COLLECTION: ensure_quiz_history_v2_indexes,
}


async def ensure_collection_with_validator(
    database: AsyncIOMotorDatabase,
    collection_name: str,
    validator: dict,
):
    existing = await database.list_collection_names()
    if collection_name not in existing:
        await database.create_collection(collection_name)

    try:
        await database.command(
            {
                "collMod": collection_name,
                "validator": validator,
                "validationLevel": "strict",
                "validationAction": "error",
            }
        )
    except OperationFailure as exc:
        if "ns does not exist" in str(exc):
            await database.create_collection(collection_name, validator=validator)
            return
        raise


async def ensure_v2_collections_and_validators(database: AsyncIOMotorDatabase):
    validators = get_v2_collection_validators()
    for collection_name, validator in validators.items():
        await ensure_collection_with_validator(database, collection_name, validator)


async def ensure_v2_indexes(
    quizzes_collection: AsyncIOMotorCollection,
    folders_collection: AsyncIOMotorCollection,
    folder_items_collection: AsyncIOMotorCollection,
    saved_quizzes_collection: AsyncIOMotorCollection,
    quiz_history_collection: AsyncIOMotorCollection,
):
    await ensure_quizzes_v2_indexes(quizzes_collection)
    await ensure_folders_v2_indexes(folders_collection)
    await ensure_folder_items_v2_indexes(folder_items_collection)
    await ensure_saved_quizzes_v2_indexes(saved_quizzes_collection)
    await ensure_quiz_history_v2_indexes(quiz_history_collection)
