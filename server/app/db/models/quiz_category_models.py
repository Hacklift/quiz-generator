from pydantic import BaseModel, Field

from typing import List, Literal, Optional

from datetime import datetime

from bson import ObjectId


class QuizQuestionModel(BaseModel):

    question: str

    options: Optional[List[str]] = None

    answer: str

    question_type: Literal["multiple choice", "true or false", "open ended", "short answer"]

    subcategory: Optional[str] = None


class QuizCategoryModel(BaseModel):

    id: Optional[str] = Field(alias="_id", default=None)

    category: str

    subcategory: str

    question_type: Literal["multiple choice", "true or false", "open ended", "short answer"]

    questions: List[QuizQuestionModel]

    created_at: datetime = Field(default_factory=datetime.utcnow)


    class Config:

        arbitrary_types_allowed = True

        json_encoders = {ObjectId: str}

