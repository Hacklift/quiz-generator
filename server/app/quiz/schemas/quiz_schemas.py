from pydantic import BaseModel, Field

from typing import List, Literal, Optional

from datetime import datetime, timezone


class NewQuizSchema(BaseModel):

    title: str

    description: str

    quiz_type: str

    owner_id: Optional[str] = None
    canonical_quiz_id: Optional[str] = None
    created_by: Optional[str] = None
    live_quiz_enabled: bool = False
    time_limit_minutes: Optional[int] = None
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None

    created_at: Optional[datetime]  = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: Optional[datetime]  = None

    questions: List



class QuizSchema(NewQuizSchema):

    id: str



class UpdateQuiz(BaseModel):

    title: Optional[str] = None

    description: Optional[str] = None

    quiz_type: Optional[str] = None
    canonical_quiz_id: Optional[str] = None
    created_by: Optional[str] = None
    live_quiz_enabled: Optional[bool] = None
    time_limit_minutes: Optional[int] = None
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None

    questions: Optional[List[dict]] = None

    updated_at: datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))




class NewQuizResponse(BaseModel):

    id: str

    title: str

    description: str


class DeleteQuizResponse(BaseModel):

    message: str

    delete_count: int


class AccessCodeCreateRequest(BaseModel):
    time_limit_minutes: int = Field(gt=0, le=1440)
    access_code_expires_at: datetime
    participant_access_mode: Literal["public", "restricted", "invited_only"] = "public"
    invited_emails: List[str] = []
    send_email_invitations: bool = False


class AccessCodeResponse(BaseModel):
    quiz_id: str
    access_code: str
    live_quiz_enabled: bool
    time_limit_minutes: int
    access_code_expires_at: datetime
    participant_access_mode: str = "public"
    invited_emails: List[str] = []
    invitations_created: int = 0
    invitations_delivered: int = 0
    invitations_queued: int = 0


class QuizAccessPreview(BaseModel):
    quiz_id: str
    title: str
    total_questions: int
    time_limit_minutes: int
    access_code_expires_at: datetime
    participant_access_mode: str = "public"
