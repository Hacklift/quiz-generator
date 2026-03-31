from fastapi import APIRouter, HTTPException, Depends, status
from motor.motor_asyncio import AsyncIOMotorCollection
from ....app.db.core.connection import get_current_user_from_token
from ....app.db.crud.notification_settings_crud import (
    get_notification_settings,
    update_notification_settings,
)
from ....schemas.model.notification_settings_model import (
    UpdateNotificationSettingsRequest,
    NotificationSettingsResponse,
)


router = APIRouter()


@router.get(
    "/api/v1/user/notification-settings",
    response_model=NotificationSettingsResponse,
)
async def fetch_notification_settings(
    user_id: str = Depends(get_current_user_from_token),
    settings_collection: AsyncIOMotorCollection = Depends(
        lambda: __import__("server.app.db.core.connection", fromlist=["notification_settings_collection"]).notification_settings_collection
    ),
):
    """Fetch user's notification settings or return defaults"""
    try:
        settings = await get_notification_settings(settings_collection, user_id)
        return NotificationSettingsResponse(**settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notification settings: {str(e)}",
        )


@router.put(
    "/api/v1/user/notification-settings",
    response_model=NotificationSettingsResponse,
)
async def update_user_notification_settings(
    update_request: UpdateNotificationSettingsRequest,
    user_id: str = Depends(get_current_user_from_token),
    settings_collection: AsyncIOMotorCollection = Depends(
        lambda: __import__("server.app.db.core.connection", fromlist=["notification_settings_collection"]).notification_settings_collection
    ),
):
    """Update user's notification settings"""
    try:
        updated_settings = await update_notification_settings(
            settings_collection, user_id, update_request
        )
        return NotificationSettingsResponse(**updated_settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification settings: {str(e)}",
        )
