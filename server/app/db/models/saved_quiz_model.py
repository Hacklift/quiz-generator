# models/quiz_history_model.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

class QuizQuestionModel(BaseModel):
    question: str
    options: Optional[List[str]] = None  
    question_type: str  

class SavedQuizModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str  
    title: str
    question_type: str
    questions: List[QuizQuestionModel]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
