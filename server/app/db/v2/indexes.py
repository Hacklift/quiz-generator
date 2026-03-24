from motor.motor_asyncio import AsyncIOMotorCollection


async def ensure_quizzes_v2_indexes(collection: AsyncIOMotorCollection):
    await collection.create_index([("owner_user_id", 1), ("created_at", -1)])
    await collection.create_index([("visibility", 1), ("created_at", -1)])
    await collection.create_index("status")
    await collection.create_index([("source", 1), ("created_at", -1)])
    await collection.create_index(
        [("legacy_source_collection", 1), ("legacy_quiz_id", 1)],
        unique=True,
        partialFilterExpression={
            "legacy_source_collection": {"$exists": True, "$type": "string"},
            "legacy_quiz_id": {"$exists": True, "$type": "string"},
        },
    )
    await collection.create_index("content_fingerprint")
    await collection.create_index("structure_fingerprint")


async def ensure_folders_v2_indexes(collection: AsyncIOMotorCollection):
    await collection.create_index([("user_id", 1), ("name", 1)], unique=True)
    await collection.create_index(
        "legacy_folder_id",
        unique=True,
        partialFilterExpression={"legacy_folder_id": {"$exists": True, "$type": "string"}},
    )


async def ensure_folder_items_v2_indexes(collection: AsyncIOMotorCollection):
    await collection.create_index([("folder_id", 1), ("quiz_id", 1)], unique=True)
    await collection.create_index([("folder_id", 1), ("position", 1)])
    await collection.create_index(
        "legacy_folder_item_id",
        unique=True,
        partialFilterExpression={"legacy_folder_item_id": {"$exists": True, "$type": "string"}},
    )


async def ensure_saved_quizzes_v2_indexes(collection: AsyncIOMotorCollection):
    await collection.create_index([("user_id", 1), ("quiz_id", 1)], unique=True)
    await collection.create_index([("user_id", 1), ("saved_at", -1)])
    await collection.create_index(
        "legacy_saved_quiz_id",
        partialFilterExpression={"legacy_saved_quiz_id": {"$exists": True, "$type": "string"}},
    )


async def ensure_quiz_history_v2_indexes(collection: AsyncIOMotorCollection):
    await collection.create_index([("user_id", 1), ("created_at", -1)])
    await collection.create_index([("quiz_id", 1), ("created_at", -1)])
    await collection.create_index([("action", 1), ("created_at", -1)])
    await collection.create_index(
        "legacy_history_id",
        unique=True,
        partialFilterExpression={"legacy_history_id": {"$exists": True, "$type": "string"}},
    )
