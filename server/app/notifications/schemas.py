from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    PAYMENT = "payment"
    SECURITY = "security"
    SYSTEM = "system"
    ADMIN = "admin"


class NotificationCreate(BaseModel):
    user_id: str
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=1000)
    type: NotificationType = NotificationType.SYSTEM
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class AdminNotificationCreate(NotificationCreate):
    pass


class BroadcastNotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=1000)
    type: NotificationType = NotificationType.ADMIN
    action_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    active_users_only: bool = True


class NotificationDB(NotificationCreate):
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: NotificationType
    read: bool
    action_url: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    has_more: bool


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationMutationResponse(BaseModel):
    message: str


class BroadcastNotificationResponse(BaseModel):
    message: str
    created_count: int
