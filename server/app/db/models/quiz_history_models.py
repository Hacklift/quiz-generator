from pydantic import BaseModel, Field

from typing import List, Optional

from datetime import datetime

from bson import ObjectId


class QuizQuestionModel(BaseModel):

    question: str

    options: Optional[List[str]] = None

    answer: str

    question_type: str


class QuizHistoryModel(BaseModel):

    id: Optional[str] = Field(alias="_id", default=None)


    user_id: Optional[str] = None


    quiz_name: Optional[str] = None

    question_type: str

    num_questions: Optional[int] = None

    difficulty_level: Optional[str] = None

    profession: Optional[str] = None

    audience_type: Optional[str] = None

    custom_instruction: Optional[str] = None


    questions: List[QuizQuestionModel]


    created_at: datetime = Field(default_factory=datetime.utcnow)


    class Config:

        arbitrary_types_allowed = True

        json_encoders = {ObjectId: str}

        allow_population_by_field_name = True

