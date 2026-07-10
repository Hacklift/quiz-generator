from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


InvitationStatus = Literal["pending", "delivered", "joined", "completed", "expired"]


class LiveQuizInvitationCreate(BaseModel):
    quiz_id: str
    creator_user_id: str
    access_code: str
    email: EmailStr
    name: Optional[str] = None


class LiveQuizInvitationUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[InvitationStatus] = None
    session_id: Optional[str] = None
    email_sent: Optional[bool] = None
    email_sent_at: Optional[datetime] = None


class LiveQuizInvitationRecord(BaseModel):
    id: str = Field(alias="_id")
    quiz_id: str
    creator_user_id: str
    access_code: str
    email: str
    name: Optional[str] = None
    status: InvitationStatus = "invited"
    session_id: Optional[str] = None
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    invitation_sent_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
