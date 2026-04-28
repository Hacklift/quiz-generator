from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


NotificationType = Literal["payment", "security", "system", "admin"]
NotificationPriority = Literal["high", "medium", "low"]


class NotificationCreate(BaseModel):
    user_id: str
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=500)
    type: NotificationType
    priority: NotificationPriority = "medium"
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class AdminNotificationCreate(BaseModel):
    user_id: str
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=500)
    type: NotificationType = "admin"
    priority: NotificationPriority = "medium"
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class BroadcastNotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=500)
    type: NotificationType = "admin"
    priority: NotificationPriority = "medium"
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    active_users_only: bool = True


class BroadcastNotificationResponse(BaseModel):
    message: str
    created_count: int


class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority
    read: bool
    action_url: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int
    has_more: bool


class NotificationDB(NotificationCreate):
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read_at: Optional[datetime] = None
