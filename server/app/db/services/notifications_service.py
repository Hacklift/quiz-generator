from fastapi import HTTPException

from server.app.db.crud.notifications_crud import (
    create_notification,
    create_notifications_for_users,
    delete_notification,
    list_notification_target_user_ids,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from server.app.db.models.notification_model import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    NotificationCreate,
)


def _ensure_admin(user) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


async def get_user_notifications_service(user_id: str, limit: int, skip: int):
    return await list_user_notifications(user_id, limit=limit, skip=skip)


async def create_admin_notification_service(payload: AdminNotificationCreate, user):
    _ensure_admin(user)
    return await create_notification(NotificationCreate(**payload.model_dump()))


async def create_broadcast_notification_service(payload: BroadcastNotificationCreate, user):
    _ensure_admin(user)
    user_ids = await list_notification_target_user_ids(
        active_users_only=payload.active_users_only,
    )
    created_count = await create_notifications_for_users(
        NotificationCreate(
            user_id=user.id,
            **payload.model_dump(exclude={"active_users_only"}),
        ),
        user_ids,
    )
    return {
        "message": "Broadcast notification created",
        "created_count": created_count,
    }


async def mark_notification_read_service(notification_id: str, user_id: str):
    updated = await mark_notification_read(notification_id, user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


async def mark_all_notifications_read_service(user_id: str):
    modified_count = await mark_all_notifications_read(user_id)
    return {"message": "Notifications marked as read", "updated": modified_count}


async def delete_notification_service(notification_id: str, user_id: str):
    deleted = await delete_notification(notification_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}
