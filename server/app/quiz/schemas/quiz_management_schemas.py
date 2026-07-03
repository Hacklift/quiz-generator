from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RenameSavedQuizRequest(BaseModel):
    title: str


class SavedQuizResponse(BaseModel):
    id: str = Field(alias="_id")
    quiz_id: str
    title: str
    created_at: Optional[datetime] = None
    question_type: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SavedQuizRenameResponse(BaseModel):
    message: str
    quiz: SavedQuizResponse


class QuizHistoryQuestionResponse(BaseModel):
    question: str
    options: list[str] | None = None
    answer: str


class LiveQuizStatsResponse(BaseModel):
    invited_participants: int = 0
    joined_participants: int = 0
    completed_participants: int = 0
    average_score: Optional[float] = None
    best_score: Optional[int] = None
    quiz_status: str = "not_live"


class QuizHistoryDetailResponse(BaseModel):
    id: str = Field(alias="_id")
    quiz_id: Optional[str] = None
    created_at: Optional[datetime] = None
    quiz_name: Optional[str] = None
    question_type: str
    difficulty_level: Optional[str] = None
    profession: Optional[str] = None
    audience_type: Optional[str] = None
    custom_instruction: Optional[str] = None
    live_quiz_enabled: bool = False
    live_quiz_stats: Optional[LiveQuizStatsResponse] = None
    questions: list[QuizHistoryQuestionResponse]

    model_config = ConfigDict(populate_by_name=True)


class DeleteResourceResponse(BaseModel):
    message: str
