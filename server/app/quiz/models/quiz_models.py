


from datetime import datetime

from pydantic import BaseModel, Field

from typing import Literal, Optional, List


class QuizRequest(BaseModel):

    profession: str

    num_questions: int

    question_type: str

    difficulty_level: str

    audience_type: str

    custom_instruction: Optional[str] = None
    token: Optional[str] = None
    live_quiz_enabled: bool = False
    time_limit_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    access_code_expires_at: Optional[datetime] = None
    participant_access_mode: Literal["public", "restricted", "invited_only"] = "public"
    invited_emails: List[str] = []
    send_email_invitations: bool = False



class QuizQuestion(BaseModel):

    question: str

    options: Optional[List[str]] = None

    question_type: str

    answer: str
    explanation: Optional[str] = None


class QuizResponse(BaseModel):

    source: str

    questions: List[QuizQuestion]

    ai_down: Optional[bool] = False

    notification_message: Optional[str] = None
    quiz_id: Optional[str] = None
    live_quiz_enabled: Optional[bool] = False
    access_code: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    access_code_expires_at: Optional[datetime] = None
    category: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_slug: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    classification: Optional[dict] = None
    participant_access_mode: Optional[str] = None
    invited_emails: List[str] = Field(default_factory=list)
    invitations_created: int = 0
    invitations_delivered: int = 0
    invitations_queued: int = 0
