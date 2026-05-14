from fastapi import APIRouter, Depends, Query, status

from ....app.db.models.notification_model import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    BroadcastNotificationResponse,
    NotificationListResponse,
    NotificationOut,
)
from ....app.db.services.notifications_service import (
    create_admin_notification_service,
    create_broadcast_notification_service,
    delete_notification_service,
    get_user_notifications_service,
    mark_all_notifications_read_service,
    mark_notification_read_service,
)
from ....app.dependancies import get_current_user


router = APIRouter(tags=["Notifications"])


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=50),
    skip: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    return await get_user_notifications_service(user.id, limit=limit, skip=skip)


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_admin_notification(
    payload: AdminNotificationCreate,
    user=Depends(get_current_user),
):
    return await create_admin_notification_service(payload, user)


@router.post(
    "/broadcast",
    response_model=BroadcastNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_broadcast_notification(
    payload: BroadcastNotificationCreate,
    user=Depends(get_current_user),
):
    return await create_broadcast_notification_service(payload, user)


@router.patch("/{notification_id}/read")
async def read_notification(notification_id: str, user=Depends(get_current_user)):
    return await mark_notification_read_service(notification_id, user.id)


@router.patch("/read-all")
async def read_all_notifications(user=Depends(get_current_user)):
    return await mark_all_notifications_read_service(user.id)


@router.delete("/{notification_id}")
async def remove_notification(notification_id: str, user=Depends(get_current_user)):
    return await delete_notification_service(notification_id, user.id)
