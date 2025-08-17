from pydantic import BaseModel


class UserAnswer(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    question_type: str
