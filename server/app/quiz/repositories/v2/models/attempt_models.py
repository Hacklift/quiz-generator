from datetime import datetime, timezone
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class QuizAttemptQuestionResultV2(BaseModel):
    question_index: int = Field(ge=0)
    question: str
    question_type: str
    user_answer: Any = None
    correct_answer: Any = None
    is_correct: bool
    result: str
    accuracy_percentage: float | None = None

    model_config = ConfigDict(extra="forbid")


class QuizAttemptDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: str
    quiz_id: str
    status: Literal["completed"] = "completed"
    score: int = Field(ge=0)
    total_questions: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    question_results: list[QuizAttemptQuestionResultV2]
    submitted_at: datetime = Field(default_factory=utc_now)
    graded_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    grading_policy_version: str = "objective-v1"

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )

    @model_validator(mode="after")
    def validate_aggregate(self):
        if self.score > self.total_questions:
            raise ValueError("score cannot exceed total_questions")
        if len(self.question_results) != self.total_questions:
            raise ValueError("question_results must match total_questions")
        expected = (
            round((self.score / self.total_questions) * 100, 2)
            if self.total_questions
            else 0.0
        )
        if self.percentage != expected:
            raise ValueError("percentage must match score and total_questions")
        return self
