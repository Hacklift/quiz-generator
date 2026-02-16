# quiz_models.py

from pydantic import BaseModel
from typing import Optional, List

class QuizRequest(BaseModel):
    profession: str
    num_questions: int
    question_type: str
    difficulty_level: str
    audience_type: str
    custom_instruction: Optional[str] = None
    token: str


class QuizQuestion(BaseModel):
    question: str
    options: Optional[List[str]] = None
    question_type: str
    answer: str

class QuizResponse(BaseModel):
    source: str
    questions: List[QuizQuestion]
    ai_down: Optional[bool] = False
    notification_message: Optional[str] = None
    quiz_id: Optional[str] = None

