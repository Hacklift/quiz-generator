from pydantic import BaseModel, Field

from typing import List, Optional

from datetime import datetime

from bson import ObjectId
from server.app.i18n.locales import SupportedLocale


class QuizQuestionModel(BaseModel):

    question: str

    options: Optional[List[str]] = None

    answer: str
    explanation: Optional[str] = None
    correct_option_index: Optional[int] = None
    correct_boolean: Optional[bool] = None

    question_type: str


class QuizHistoryModel(BaseModel):

    id: Optional[str] = Field(alias="_id", default=None)


    user_id: Optional[str] = None
    quiz_id: Optional[str] = None
    content_locale: SupportedLocale = "en"
    description: Optional[str] = None
    is_sample: bool = False


    quiz_name: Optional[str] = None

    question_type: str
    canonical_quiz_id: Optional[str] = None

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

        validate_by_name = True
