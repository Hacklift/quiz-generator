from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from datetime import datetime
from ..schemas.notification_settings_model import (
    NotificationSettingsModel,
    UpdateNotificationSettingsRequest,
)


async def get_notification_settings(
    settings_collection: AsyncIOMotorCollection, user_id: str
) -> dict:
    """Fetch notification settings for a user, return defaults if not found"""
    settings = await settings_collection.find_one({"user_id": user_id})
    
    if not settings:
        # Return default settings if user has never set custom preferences
        return {
            "user_id": user_id,
            "enabled": True,
            "theme": "dark",
            "position": "top-right",
            "sound": False,
            "duration": {"short": 2000, "medium": 4000, "long": 6000},
            "types": {
                "success": True,
                "error": True,
                "warning": True,
                "info": True,
                "quiz": True,
            },
        }
    
    # Remove MongoDB _id from response
    settings.pop("_id", None)
    return settings


async def create_notification_settings(
    settings_collection: AsyncIOMotorCollection, settings: NotificationSettingsModel
) -> dict:
    """Create default notification settings for a new user"""
    now = datetime.utcnow()
    settings_dict = settings.dict()
    settings_dict["created_at"] = now
    settings_dict["updated_at"] = now
    
    result = await settings_collection.insert_one(settings_dict)
    
    settings_dict["_id"] = result.inserted_id
    return settings_dict


async def update_notification_settings(
    settings_collection: AsyncIOMotorCollection,
    user_id: str,
    update_data: UpdateNotificationSettingsRequest,
) -> dict:
    """Update notification settings for a user"""
    update_dict = update_data.dict(exclude_unset=True)
    
    if not update_dict:
        return await get_notification_settings(settings_collection, user_id)
    
    update_dict["updated_at"] = datetime.utcnow()
    
    result = await settings_collection.find_one_and_update(
        {"user_id": user_id},
        {"$set": update_dict},
        return_document=True,
    )
    
    if not result:
        # If settings don't exist, create them with the updates
        settings = NotificationSettingsModel(user_id=user_id, **update_dict)
        return await create_notification_settings(settings_collection, settings)
    
    result.pop("_id", None)
    return result


async def delete_notification_settings(
    settings_collection: AsyncIOMotorCollection, user_id: str
) -> bool:
    """Delete notification settings for a user (reset to defaults)"""
    result = await settings_collection.delete_one({"user_id": user_id})
    return result.deleted_count > 0
