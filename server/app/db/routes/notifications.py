from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....app.db.crud.notifications_crud import (
    create_notification,
    create_notifications_for_users,
    delete_notification,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from ....app.db.core.connection import get_users_collection
from ....app.db.models.notification_model import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    BroadcastNotificationResponse,
    NotificationCreate,
    NotificationListResponse,
    NotificationOut,
)
from ....app.dependancies import get_current_user


router = APIRouter(tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=50),
    skip: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return await list_user_notifications(user.id, limit=limit, skip=skip)


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_admin_notification(
    payload: AdminNotificationCreate,
    user=Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return await create_notification(NotificationCreate(**payload.model_dump()))


@router.post(
    "/broadcast",
    response_model=BroadcastNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_broadcast_notification(
    payload: BroadcastNotificationCreate,
    user=Depends(get_current_user),
    users_collection=Depends(get_users_collection),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    user_query = {"is_active": True} if payload.active_users_only else {}
    cursor = users_collection.find(user_query, {"_id": 1})
    user_ids = [str(row["_id"]) for row in await cursor.to_list(length=None)]
    created_count = await create_notifications_for_users(
        NotificationCreate(user_id=user.id, **payload.model_dump(exclude={"active_users_only"})),
        user_ids,
    )
    return {
        "message": "Broadcast notification created",
        "created_count": created_count,
    }


@router.patch("/{notification_id}/read")
async def read_notification(notification_id: str, user=Depends(get_current_user)):
    updated = await mark_notification_read(notification_id, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}


@router.patch("/read-all")
async def read_all_notifications(user=Depends(get_current_user)):
    modified_count = await mark_all_notifications_read(user.id)
    return {"message": "Notifications marked as read", "updated": modified_count}


@router.delete("/{notification_id}")
async def remove_notification(notification_id: str, user=Depends(get_current_user)):
    deleted = await delete_notification(notification_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}
