from pydantic import BaseModel, Field

from typing import List, Optional

from datetime import datetime

from bson import ObjectId


class QuizQuestionModel(BaseModel):

    question: str

    options: Optional[List[str]] = None

    question_type: Optional[str] = None


class SavedQuizModel(BaseModel):

    id: Optional[str] = Field(alias="_id", default=None)

    user_id: Optional[str] = None
    quiz_id: Optional[str] = None

    title: str

    question_type: str
    canonical_quiz_id: Optional[str] = None
    is_deleted: Optional[bool] = False

    questions: List[QuizQuestionModel]

    created_at: datetime = Field(default_factory=datetime.utcnow)


    class Config:

        arbitrary_types_allowed = True

        json_encoders = {ObjectId: str}

        allow_population_by_field_name = True
