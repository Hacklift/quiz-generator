from datetime import datetime, timedelta, timezone
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CreateAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz_id: str
    cohort_id: str | None = None
    recipient_user_ids: list[str] = Field(default_factory=list, max_length=1000)
    title: str | None = Field(default=None, min_length=1, max_length=180)
    available_from: datetime | None = None
    due_at: datetime | None = None
    closes_at: datetime
    time_limit_minutes: int = Field(default=20, ge=1, le=1440, strict=True)
    max_attempts: Literal[1, 2] | None = 1
    passing_threshold_percentage: float = Field(default=80, ge=0, le=100, allow_inf_nan=False, strict=True)
    send_email_invitations: bool = False

    @field_validator("quiz_id", "cohort_id")
    @classmethod
    def valid_identifier(cls, value):
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError("Invalid identifier")
        return str(ObjectId(value)) if value is not None else None

    @field_validator("recipient_user_ids")
    @classmethod
    def valid_recipients(cls, values):
        if any(not ObjectId.is_valid(value) for value in values):
            raise ValueError("Invalid recipient identifier")
        return sorted({str(ObjectId(value)) for value in values})

    @field_validator("available_from", "due_at", "closes_at")
    @classmethod
    def aware_schedule(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("Schedule timestamps must include a timezone")
            return value.astimezone(timezone.utc)
        return value

    @field_validator("title")
    @classmethod
    def safe_title(cls, value):
        if value is not None:
            value = value.strip()
            if not value or "\n" in value or "\r" in value:
                raise ValueError("Invalid assignment title")
        return value

    @field_validator("max_attempts", mode="before")
    @classmethod
    def strict_attempt_limit(cls, value):
        if value is not None and type(value) is not int:
            raise ValueError("Retry policy must be 1, 2, or null")
        return value

    @model_validator(mode="after")
    def valid_target_and_schedule(self):
        if bool(self.cohort_id) == bool(self.recipient_user_ids):
            raise ValueError("Choose a cohort or named recipients, not both")
        if self.available_from and self.closes_at - self.available_from <= timedelta(minutes=self.time_limit_minutes):
            raise ValueError("Availability must allow one full attempt")
        if self.due_at and (self.due_at > self.closes_at or (self.available_from and self.due_at < self.available_from)):
            raise ValueError("Due time must fall within the availability window")
        return self


class CloseAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: Literal[True]


class QuizRevisionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    quiz_type: str
    questions: list[dict] = Field(min_length=1)


class QuizRevisionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True, populate_by_name=True)
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    organization_id: str = Field(min_length=1)
    quiz_id: str = Field(min_length=1)
    content_hash: str = Field(min_length=64, max_length=64)
    snapshot: QuizRevisionSnapshot
    created_by_user_id: str = Field(min_length=1)
    created_at: datetime
    schema_version: Literal[1] = 1


class AssignmentSummary(BaseModel):
    id: str
    organization_id: str
    title: str
    quiz_id: str
    quiz_revision_id: str
    cohort_id: str | None = None
    delivery_kind: Literal["quiz"] = "quiz"
    status: Literal["open", "closed"]
    available_from: datetime | None = None
    due_at: datetime | None = None
    closes_at: datetime
    closed_at: datetime | None = None
    created_at: datetime
    time_limit_minutes: int
    max_attempts: int | None = None
    passing_threshold_percentage: float
    participant_count: int | None = None
    completed_count: int | None = None
    outstanding_count: int | None = None
    completion_percentage: float | None = None
    average_percentage: float | None = None
    summary_availability: Literal["available", "unavailable"] | None = None


class RecipientProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_id: str
    user_id: str | None = None
    recipient_name: str | None = None
    recipient_status: Literal["assigned", "in_progress", "submitting", "incomplete", "completed"]
    attempts_used: int = Field(ge=0, strict=True)
    max_attempts: int | None = None
    latest_score: int | None = None
    latest_percentage: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False, strict=True)
    completed_at: datetime | None = None
    has_completed: bool
    active_session_id: str | None = None
    can_start: bool
    can_resume: bool = False
    available: bool
    latest_start_at: datetime

    @field_validator("recipient_id", "user_id")
    @classmethod
    def valid_recipient_id(cls, value):
        if value is not None and not ObjectId.is_valid(value):
            raise ValueError("Invalid completion recipient identity")
        return value


class AssignmentProgressStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    participant_count: int = Field(ge=0, strict=True)
    completed_count: int = Field(ge=0, strict=True)
    outstanding_count: int = Field(ge=0, strict=True)
    completion_percentage: float = Field(ge=0, le=100, allow_inf_nan=False, strict=True)
    average_percentage: float | None = Field(ge=0, le=100, allow_inf_nan=False, strict=True)

    @model_validator(mode="after")
    def consistent(self):
        if self.completed_count + self.outstanding_count != self.participant_count:
            raise ValueError("Inconsistent completion counts")
        expected = round(100 * self.completed_count / self.participant_count, 2) if self.participant_count else 0
        if self.completion_percentage != expected:
            raise ValueError("Inconsistent completion percentage")
        if self.completed_count == 0 and self.average_percentage is not None:
            raise ValueError("A score average requires completed recipients")
        return self


class AssignmentDetail(AssignmentSummary):
    can_manage: bool
    can_report: bool
    recipients: list[RecipientProgress] = Field(default_factory=list)
    my_assignment: RecipientProgress | None = None
    next_cursor: str | None = None


class MyAssignment(AssignmentSummary, RecipientProgress):
    pass


class AssignmentPage(BaseModel):
    items: list[AssignmentSummary]
    next_cursor: str | None = None


class MyAssignmentPage(BaseModel):
    items: list[MyAssignment]
    next_cursor: str | None = None


class AttemptSummary(BaseModel):
    id: str
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    score: int | None = None
    percentage: float | None = None
    quiz_revision_id: str
    expires_at: datetime


class AttemptPage(BaseModel):
    items: list[AttemptSummary]
    next_cursor: str | None = None


class AttemptDetail(BaseModel):
    id: str
    assignment_id: str
    user_id: str
    status: Literal["submitted"]
    started_at: datetime
    submitted_at: datetime
    score: int
    percentage: float
    quiz_revision_id: str
    graded_answers: list[dict]
    questions: list[dict]


class AssignableQuiz(BaseModel):
    id: str
    title: str
    quiz_type: str


class AssignableQuizPage(BaseModel):
    items: list[AssignableQuiz]
    next_cursor: str | None = None


class RecipientOption(BaseModel):
    user_id: str
    name: str


class RecipientOptionsPage(BaseModel):
    items: list[RecipientOption]
    next_cursor: str | None = None
