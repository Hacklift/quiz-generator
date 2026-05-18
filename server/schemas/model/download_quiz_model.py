from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DownloadQuizQuestionModel(BaseModel):
    question: str
    options: Optional[list[str]] = None
    answer: Optional[str] = None
    correct_answer: Optional[str] = None

    @model_validator(mode="after")
    def validate_answer(self):
        if not self.answer and not self.correct_answer:
            raise ValueError("Each question must include answer or correct_answer")
        return self


class DownloadQuizRequestModel(BaseModel):
    format: str = Field(..., description="File format for the quiz data (txt, json, pdf, docx)")
    title: Optional[str] = None
    description: Optional[str] = None
    quiz_type: Optional[str] = None
    questions: list[DownloadQuizQuestionModel]
