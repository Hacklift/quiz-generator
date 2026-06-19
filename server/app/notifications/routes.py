from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorCollection

from server.app.db.core.connection import (
    get_notifications_collection,
    get_users_collection,
)
from server.app.notifications.schemas import (
    AdminNotificationCreate,
    BroadcastNotificationCreate,
    BroadcastNotificationResponse,
    NotificationListResponse,
    NotificationMutationResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from server.app.users.models import UserOut
from server.app.notifications.services import (
    broadcast_admin_notification,
    create_admin_notification,
    delete_user_notification,
    get_notifications_for_user,
    get_unread_count_for_user,
    mark_user_notification_read,
    mark_user_notifications_read,
)
from server.app.core.dependencies import get_current_user


router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=50),
    skip: int = Query(default=0, ge=0),
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
):
    return await get_notifications_for_user(
        notifications_collection=notifications_collection,
        user=current_user,
        limit=limit,
        skip=skip,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
):
    return await get_unread_count_for_user(
        notifications_collection=notifications_collection,
        user=current_user,
    )


@router.post("/", response_model=NotificationResponse)
async def create_notification_for_user(
    payload: AdminNotificationCreate,
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
):
    return await create_admin_notification(
        notifications_collection=notifications_collection,
        users_collection=users_collection,
        payload=payload,
        user=current_user,
    )


@router.post("/broadcast", response_model=BroadcastNotificationResponse)
async def broadcast_notification(
    payload: BroadcastNotificationCreate,
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
    users_collection: AsyncIOMotorCollection = Depends(get_users_collection),
):
    return await broadcast_admin_notification(
        notifications_collection=notifications_collection,
        users_collection=users_collection,
        payload=payload,
        user=current_user,
    )


@router.patch("/read-all", response_model=NotificationMutationResponse)
async def mark_all_read(
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
):
    return await mark_user_notifications_read(
        notifications_collection=notifications_collection,
        user=current_user,
    )


@router.patch("/{notification_id}/read", response_model=NotificationMutationResponse)
async def mark_one_read(
    notification_id: str,
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
):
    return await mark_user_notification_read(
        notifications_collection=notifications_collection,
        notification_id=notification_id,
        user=current_user,
    )


@router.delete("/{notification_id}", response_model=NotificationMutationResponse)
async def delete_one_notification(
    notification_id: str,
    current_user: UserOut = Depends(get_current_user),
    notifications_collection: AsyncIOMotorCollection = Depends(get_notifications_collection),
):
    return await delete_user_notification(
        notifications_collection=notifications_collection,
        notification_id=notification_id,
        user=current_user,
    )
