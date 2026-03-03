# models/quiz_history_model.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId

class QuizQuestionModel(BaseModel):
    question: str
    options: Optional[List[str]] = None  
    question_type: str  # e.g., "multichoice", "open-ended"

class SavedQuizModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: Optional[str] = None  # <-- Optional for now, will be required when auth is added
    title: str
    question_type: str
    questions: List[QuizQuestionModel]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True


class SavedQuizRecord(BaseModel):
    user_id: str
    quiz_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
