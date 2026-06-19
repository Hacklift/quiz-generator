from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.notifications.repository import (
    count_unread_notifications,
    create_notification,
    create_notifications_for_users,
    delete_notification,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from server.app.notifications.schemas import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    BroadcastNotificationResponse,
    NotificationCreate,
    NotificationListResponse,
    NotificationMutationResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from server.app.users.models import UserOut


def _ensure_admin(user: UserOut) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


async def get_notifications_for_user(
    notifications_collection: AsyncIOMotorCollection,
    user: UserOut,
    limit: int,
    skip: int,
) -> NotificationListResponse:
    notifications, has_more = await list_user_notifications(
        notifications_collection=notifications_collection,
        user_id=user.id,
        limit=limit,
        skip=skip,
    )
    unread_count = await count_unread_notifications(notifications_collection, user.id)
    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
        has_more=has_more,
    )


async def get_unread_count_for_user(
    notifications_collection: AsyncIOMotorCollection,
    user: UserOut,
) -> NotificationUnreadCountResponse:
    unread_count = await count_unread_notifications(notifications_collection, user.id)
    return NotificationUnreadCountResponse(unread_count=unread_count)


async def create_admin_notification(
    notifications_collection: AsyncIOMotorCollection,
    users_collection: AsyncIOMotorCollection,
    payload: AdminNotificationCreate,
    user: UserOut,
) -> NotificationResponse:
    _ensure_admin(user)
    if not ObjectId.is_valid(payload.user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
    target_user = await users_collection.find_one({"_id": ObjectId(payload.user_id)})
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return await create_notification(notifications_collection, payload)


async def broadcast_admin_notification(
    notifications_collection: AsyncIOMotorCollection,
    users_collection: AsyncIOMotorCollection,
    payload: BroadcastNotificationCreate,
    user: UserOut,
) -> BroadcastNotificationResponse:
    _ensure_admin(user)

    user_query = {}
    if payload.active_users_only:
        user_query["is_active"] = True

    users = await users_collection.find(user_query, projection={"_id": 1}).to_list(
        length=None
    )
    user_ids = [str(target["_id"]) for target in users]
    notification = NotificationCreate(
        user_id="",
        title=payload.title,
        message=payload.message,
        type=payload.type,
        action_url=payload.action_url,
        expires_at=payload.expires_at,
    )
    created_count = await create_notifications_for_users(
        notifications_collection=notifications_collection,
        user_ids=user_ids,
        notification=notification,
    )
    return BroadcastNotificationResponse(
        message="Broadcast notification created",
        created_count=created_count,
    )


async def mark_user_notification_read(
    notifications_collection: AsyncIOMotorCollection,
    notification_id: str,
    user: UserOut,
) -> NotificationMutationResponse:
    updated = await mark_notification_read(notifications_collection, notification_id, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationMutationResponse(message="Notification marked as read")


async def mark_user_notifications_read(
    notifications_collection: AsyncIOMotorCollection,
    user: UserOut,
) -> NotificationMutationResponse:
    await mark_all_notifications_read(notifications_collection, user.id)
    return NotificationMutationResponse(message="Notifications marked as read")


async def delete_user_notification(
    notifications_collection: AsyncIOMotorCollection,
    notification_id: str,
    user: UserOut,
) -> NotificationMutationResponse:
    deleted = await delete_notification(notifications_collection, notification_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationMutationResponse(message="Notification deleted")
