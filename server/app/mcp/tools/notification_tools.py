from server.app.db.core.connection import get_notifications_collection
from server.app.mcp.auth import get_mcp_request_context
from server.app.notifications.repository import (
    count_unread_notifications,
    delete_notification,
    list_user_notifications,
    mark_notification_read,
)


async def notification_list(limit: int = 20, skip: int = 0) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    notifications, has_more = await list_user_notifications(
        notifications_collection=get_notifications_collection(),
        user_id=context.user_id,
        limit=limit,
        skip=skip,
    )
    unread_count = await count_unread_notifications(get_notifications_collection(), context.user_id)
    return {
        "items": [notification.model_dump(mode="json") for notification in notifications],
        "unread_count": unread_count,
        "has_more": has_more,
        "limit": limit,
        "skip": skip,
        "next_skip": skip + limit if has_more else None,
    }


async def notification_mark_read(notification_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    marked = await mark_notification_read(
        get_notifications_collection(),
        notification_id,
        context.user_id,
    )
    if not marked:
        raise ValueError("Notification not found")
    return {
        "message": "Notification marked as read.",
        "notification_id": notification_id,
        "read": True,
    }


async def notification_delete(notification_id: str) -> dict:
    context = await get_mcp_request_context(require_auth=True)
    deleted = await delete_notification(
        get_notifications_collection(),
        notification_id,
        context.user_id,
    )
    if not deleted:
        raise ValueError("Notification not found")
    return {
        "message": "Notification deleted.",
        "notification_id": notification_id,
        "deleted": True,
    }
