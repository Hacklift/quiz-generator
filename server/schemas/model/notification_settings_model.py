from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class NotificationDuration(BaseModel):
    short: int = Field(default=2000, ge=1000, le=5000)
    medium: int = Field(default=4000, ge=2000, le=8000)
    long: int = Field(default=6000, ge=3000, le=10000)


class NotificationTypes(BaseModel):
    success: bool = True
    error: bool = True
    warning: bool = True
    info: bool = True
    quiz: bool = True


class NotificationSettingsModel(BaseModel):
    user_id: str
    enabled: bool = True
    theme: str = Field(default="dark", pattern="^(dark|light)$")
    position: str = Field(
        default="top-right",
        pattern="^(top-right|top-left|bottom-right|bottom-left)$"
    )
    sound: bool = False
    duration: NotificationDuration = Field(default_factory=NotificationDuration)
    types: NotificationTypes = Field(default_factory=NotificationTypes)


class NotificationSettingsResponse(NotificationSettingsModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateNotificationSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    theme: Optional[str] = None
    position: Optional[str] = None
    sound: Optional[bool] = None
    duration: Optional[NotificationDuration] = None
    types: Optional[NotificationTypes] = None
