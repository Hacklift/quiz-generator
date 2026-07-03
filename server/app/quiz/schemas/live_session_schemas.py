from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class LiveQuizAnswer(BaseModel):
    question_index: int = Field(ge=0)
    selected_answer: str
    answered_at: datetime


class StartLiveQuizSessionRequest(BaseModel):
    participant_name: str = Field(min_length=1, max_length=120)
    participant_email: Optional[EmailStr] = None


class StartLiveQuizSessionResponse(BaseModel):
    session_id: str
    participant_token: str
    started_at: datetime
    expires_at: datetime
    server_now: datetime
    time_limit_minutes: int
    duration_seconds: int
    remaining_seconds: int
    redirect_url: str


class LiveQuizQuestion(BaseModel):
    question_index: int
    question: str
    options: Optional[List[Any]] = None
    question_type: Optional[str] = None
    selected_answer: Optional[str] = None


class LiveQuizSessionState(BaseModel):
    session_id: str
    quiz_id: str
    title: str
    participant_name: str
    participant_email: Optional[EmailStr] = None
    started_at: datetime
    expires_at: datetime
    server_now: datetime
    submitted_at: Optional[datetime] = None
    status: Literal["active", "joined", "disconnected", "submitted", "expired"]
    current_question_index: int
    total_questions: int
    time_limit_minutes: int
    duration_seconds: int
    remaining_seconds: int
    question: Optional[LiveQuizQuestion] = None
    answers: List[LiveQuizAnswer] = []
    score: Optional[int] = None
    percentage: Optional[float] = None
    auto_submitted: bool = False


class SaveLiveQuizAnswerRequest(BaseModel):
    question_index: int = Field(ge=0)
    selected_answer: str
    next_question_index: Optional[int] = Field(default=None, ge=0)


class SaveLiveQuizAnswerResponse(BaseModel):
    status: str
    current_question_index: int
    remaining_seconds: int


class SubmitLiveQuizSessionResponse(BaseModel):
    status: Literal["submitted", "already_submitted"]
    score: int
    total_questions: int
    percentage: float
    submitted_at: datetime
    auto_submitted: bool = False


class LiveQuizAnalyticsRow(BaseModel):
    session_id: str
    participant_name: str
    participant_email: Optional[EmailStr] = None
    score: Optional[int] = None
    total_questions: int
    percentage: Optional[float] = None
    joined_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    progress: Optional[int] = None
    current_question_number: Optional[int] = None
    progress_percentage: Optional[float] = None
    status: str
    auto_submitted: bool = False


class LiveQuizSummaryRow(BaseModel):
    quiz_id: str
    title: str
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None
    time_limit_minutes: Optional[int] = None
    participant_access_mode: str = "public"
    invited_emails: List[str] = []
    status: str
    created_at: Optional[datetime] = None
    participant_count: int = 0
    completed_count: int = 0
    average_score: Optional[float] = None
