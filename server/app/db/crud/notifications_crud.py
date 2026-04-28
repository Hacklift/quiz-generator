from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException

from ....app.db.core.connection import get_notifications_collection
from ....app.db.models.notification_model import NotificationCreate, NotificationDB


def _serialize_notification(notification: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(notification["_id"]),
        "user_id": notification["user_id"],
        "title": notification["title"],
        "message": notification["message"],
        "type": notification["type"],
        "priority": notification.get("priority", "medium"),
        "read": notification.get("read", False),
        "action_url": notification.get("action_url"),
        "created_at": notification["created_at"],
        "read_at": notification.get("read_at"),
        "expires_at": notification.get("expires_at"),
    }


def _active_notification_query(user_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
    }


async def create_notification(notification_data: NotificationCreate) -> dict[str, Any]:
    collection = get_notifications_collection()
    notification = NotificationDB(**notification_data.model_dump())
    result = await collection.insert_one(notification.model_dump())
    created = await collection.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(status_code=500, detail="Notification creation failed")
    return _serialize_notification(created)


async def create_notifications_for_users(
    notification_data: NotificationCreate,
    user_ids: list[str],
) -> int:
    if not user_ids:
        return 0

    collection = get_notifications_collection()
    payload = notification_data.model_dump(exclude={"user_id"})
    notifications = [
        NotificationDB(user_id=user_id, **payload).model_dump()
        for user_id in user_ids
    ]
    result = await collection.insert_many(notifications)
    return len(result.inserted_ids)


async def list_user_notifications(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
) -> dict[str, Any]:
    collection = get_notifications_collection()
    bounded_limit = min(max(limit, 1), 50)
    query = _active_notification_query(user_id)

    cursor = (
        collection.find(query)
        .sort("created_at", -1)
        .skip(max(skip, 0))
        .limit(bounded_limit + 1)
    )
    rows = await cursor.to_list(length=bounded_limit + 1)
    unread_count = await collection.count_documents({**query, "read": False})

    return {
        "notifications": [_serialize_notification(row) for row in rows[:bounded_limit]],
        "unread_count": unread_count,
        "has_more": len(rows) > bounded_limit,
    }


async def mark_notification_read(notification_id: str, user_id: str) -> bool:
    collection = get_notifications_collection()
    try:
        object_id = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await collection.update_one(
        {"_id": object_id, "user_id": user_id},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}},
    )
    return result.matched_count > 0


async def mark_all_notifications_read(user_id: str) -> int:
    collection = get_notifications_collection()
    result = await collection.update_many(
        {**_active_notification_query(user_id), "read": False},
        {"$set": {"read": True, "read_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count


async def delete_notification(notification_id: str, user_id: str) -> bool:
    collection = get_notifications_collection()
    try:
        object_id = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await collection.delete_one({"_id": object_id, "user_id": user_id})
    return result.deleted_count > 0
