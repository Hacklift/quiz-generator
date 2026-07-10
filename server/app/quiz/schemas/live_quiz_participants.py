from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ParticipantSummary(BaseModel):
    total_invited: int = 0
    total_started: int = 0
    total_submitted: int = 0
    total_expired: int = 0
    average_score: Optional[float] = None


class LiveQuizParticipantRow(BaseModel):
    participant_name: str
    participant_email: Optional[str] = None
    status: str
    score: Optional[int] = None
    total_questions: int = 0
    percentage: Optional[float] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    duration_used_seconds: Optional[int] = None
    auto_submitted: bool = False


class LiveQuizParticipantsResponse(BaseModel):
    quiz_id: str
    quiz_title: str
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None
    time_limit_minutes: Optional[int] = None
    summary: ParticipantSummary
    participants: List[LiveQuizParticipantRow]


class LiveQuizSettingsRequest(BaseModel):
    time_limit_minutes: int
    access_code_expires_at: datetime
    participant_access_mode: str = "public"  # "public" or "restricted"
    invited_emails: List[str] = []
    send_email_invitations: bool = False


class LiveQuizSettingsResponse(BaseModel):
    quiz_id: str
    access_code: str
    live_quiz_enabled: bool
    time_limit_minutes: int
    access_code_expires_at: datetime
    participant_access_mode: str
    total_invited: int
    invitation_status: str