from datetime import datetime, timezone
from typing import Iterable

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from server.app.notifications.schemas import (
    NotificationCreate,
    NotificationDB,
    NotificationResponse,
)


def _object_id(notification_id: str) -> ObjectId:
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=400, detail="Invalid notification ID")
    return ObjectId(notification_id)


def _active_notification_query(user_id: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
    }


def _to_response(notification: dict) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification["_id"]),
        user_id=notification["user_id"],
        title=notification["title"],
        message=notification["message"],
        type=notification["type"],
        read=notification.get("read", False),
        action_url=notification.get("action_url"),
        created_at=notification["created_at"],
        expires_at=notification.get("expires_at"),
    )


async def create_notification(
    notifications_collection: AsyncIOMotorCollection,
    notification: NotificationCreate,
) -> NotificationResponse:
    document = NotificationDB(**notification.model_dump()).model_dump()
    try:
        result = await notifications_collection.insert_one(document)
        created = await notifications_collection.find_one({"_id": result.inserted_id})
    except DuplicateKeyError:
        if not notification.dedupe_key:
            raise
        created = await notifications_collection.find_one(
            {"dedupe_key": notification.dedupe_key}
        )
        if created is None:
            raise
    return _to_response(created)


async def create_notifications_for_users(
    notifications_collection: AsyncIOMotorCollection,
    user_ids: Iterable[str],
    notification: NotificationCreate,
) -> int:
    documents = []
    for user_id in user_ids:
        payload = notification.model_copy(update={"user_id": user_id})
        documents.append(NotificationDB(**payload.model_dump()).model_dump())

    if not documents:
        return 0

    result = await notifications_collection.insert_many(documents)
    return len(result.inserted_ids)


async def list_user_notifications(
    notifications_collection: AsyncIOMotorCollection,
    user_id: str,
    limit: int,
    skip: int,
) -> tuple[list[NotificationResponse], bool]:
    cursor = (
        notifications_collection.find(_active_notification_query(user_id))
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit + 1)
    )
    documents = await cursor.to_list(length=limit + 1)
    has_more = len(documents) > limit
    return [_to_response(doc) for doc in documents[:limit]], has_more


async def count_unread_notifications(
    notifications_collection: AsyncIOMotorCollection,
    user_id: str,
) -> int:
    query = _active_notification_query(user_id)
    query["read"] = False
    return await notifications_collection.count_documents(query)


async def mark_notification_read(
    notifications_collection: AsyncIOMotorCollection,
    notification_id: str,
    user_id: str,
) -> bool:
    result = await notifications_collection.update_one(
        {"_id": _object_id(notification_id), **_active_notification_query(user_id)},
        {"$set": {"read": True}},
    )
    return result.modified_count > 0 or result.matched_count > 0


async def mark_all_notifications_read(
    notifications_collection: AsyncIOMotorCollection,
    user_id: str,
) -> int:
    query = _active_notification_query(user_id)
    query["read"] = False
    result = await notifications_collection.update_many(query, {"$set": {"read": True}})
    return result.modified_count


async def delete_notification(
    notifications_collection: AsyncIOMotorCollection,
    notification_id: str,
    user_id: str,
) -> bool:
    result = await notifications_collection.delete_one(
        {"_id": _object_id(notification_id), "user_id": user_id}
    )
    return result.deleted_count > 0
