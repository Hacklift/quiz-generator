from pydantic import BaseModel, Field
from typing import Optional

from .query_patterns import QueryPattern


class DownloadQuizQuery(BaseModel):
    pattern: Optional[str] = Field(QueryPattern.DOWNLOAD_QUIZ)
    user_id: Optional[str] = Field(..., description="User's id")
    format: str = Field("txt", description="File format for the quiz data (txt, csv, pdf, docx)")
    quiz_id: Optional[str] = Field(
        None,
        description="MongoDB quiz ID. If provided, download real quiz instead of mock."
    )
    
    question_type: Optional[str] = Field(
        "multichoice", description="Used only when quiz_id is not provided"
    )
    
    num_question: Optional[int] = Field(
        1,
        description="Used only when quiz_id is not provided",
        ge=1
    )
