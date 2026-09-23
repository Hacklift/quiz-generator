from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


TrainingRunKind = Literal["business", "compliance"]
TrainingPurpose = Literal[
    "onboarding",
    "product_knowledge",
    "harassment_prevention",
    "health_and_safety",
    "custom",
]
TrainingAccessMode = Literal["public", "assigned_only"]


class CreateTrainingRunRequest(BaseModel):
    quiz_id: str = Field(min_length=1)
    kind: TrainingRunKind = "business"
    purpose: TrainingPurpose = "custom"
    title: Optional[str] = Field(default=None, max_length=180)
    time_limit_minutes: int = Field(default=20, ge=1, le=1440)
    closes_at: datetime
    due_at: Optional[datetime] = None
    access_mode: TrainingAccessMode = "assigned_only"
    recipient_emails: list[EmailStr] = Field(default_factory=list, max_length=1_000)
    # None is the explicit, supported representation for unlimited retries.
    max_attempts: Optional[Literal[1, 2]] = 1
    send_email_invitations: bool = False

    @field_validator("title")
    @classmethod
    def reject_header_characters_in_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and ("\r" in value or "\n" in value):
            raise ValueError("title must not contain carriage returns or newlines")
        return value

    @field_validator("recipient_emails")
    @classmethod
    def normalize_recipient_emails(cls, emails: list[EmailStr]) -> list[EmailStr]:
        unique: dict[str, EmailStr] = {}
        for email in emails:
            unique[str(email).strip().casefold()] = email
        return list(unique.values())

    @field_validator("closes_at", "due_at")
    @classmethod
    def normalize_schedule_to_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("schedule timestamps must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_schedule_and_access(self):
        if self.due_at and self.due_at > self.closes_at:
            raise ValueError("due_at must be on or before closes_at")
        if self.access_mode == "assigned_only" and not self.recipient_emails:
            raise ValueError("assigned-only training requires at least one recipient")
        if self.access_mode == "public" and self.recipient_emails:
            raise ValueError("shareable-link training cannot include assigned recipients")
        if self.access_mode == "public" and self.send_email_invitations:
            raise ValueError("shareable-link training does not send assignment invitations")
        if self.kind == "business" and self.purpose in {
            "harassment_prevention",
            "health_and_safety",
        }:
            raise ValueError("compliance purposes require a compliance training run")
        if self.kind == "compliance" and self.purpose in {
            "onboarding",
            "product_knowledge",
        }:
            raise ValueError("business purposes require a business training run")
        # Compliance evidence must be attributable to a verified recipient.
        if self.kind == "compliance" and self.access_mode != "assigned_only":
            raise ValueError("compliance training must be assigned to recipients")
        return self


class TrainingRunSummary(BaseModel):
    id: str
    quiz_id: str
    title: str
    kind: TrainingRunKind
    purpose: TrainingPurpose
    status: Literal["open", "closed"]
    access_mode: TrainingAccessMode
    access_code: Optional[str] = None
    access_url: Optional[str] = None
    time_limit_minutes: int
    due_at: Optional[datetime] = None
    closes_at: datetime
    closed_at: Optional[datetime] = None
    created_at: datetime
    assigned_count: int = 0
    started_count: int = 0
    completed_count: int = 0
    average_score: Optional[float] = None


class TrainingAssignmentSummary(BaseModel):
    id: str
    training_run_id: str
    quiz_id: str
    title: str
    kind: TrainingRunKind
    purpose: TrainingPurpose
    status: Literal["assigned", "in_progress", "incomplete", "completed"]
    due_at: Optional[datetime] = None
    closes_at: datetime
    latest_start_at: datetime
    is_overdue: bool = False
    max_attempts: Optional[int] = None
    attempts_used: int = 0
    can_retry: bool = False
    latest_score: Optional[int] = None
    latest_percentage: Optional[float] = None
    completed_at: Optional[datetime] = None


class TrainingCompletionRow(BaseModel):
    assignment_id: str
    recipient_email: Optional[EmailStr] = None
    recipient_name: Optional[str] = None
    status: Literal["assigned", "in_progress", "incomplete", "completed"]
    due_at: Optional[datetime] = None
    attempts_used: int
    max_attempts: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    latest_score: Optional[int] = None
    latest_percentage: Optional[float] = None


class TrainingRunDetail(TrainingRunSummary):
    completion_register: list[TrainingCompletionRow] = Field(default_factory=list)


class TrainingRunAccessPreview(BaseModel):
    title: str
    total_questions: int
    time_limit_minutes: int
    closes_at: datetime


class StartTrainingSessionRequest(BaseModel):
    participant_name: str = Field(min_length=1, max_length=120)
    participant_email: Optional[EmailStr] = None


class CloseTrainingRunRequest(BaseModel):
    confirm: Literal[True]
