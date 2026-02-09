from pydantic import BaseModel, Field
from typing import Optional
from .query_patterns import QueryPattern

class DownloadQuizQuery(BaseModel):
    pattern: str = Field(QueryPattern.DOWNLOAD_QUIZ)
    user_id: Optional[str] = Field(None, description="User's id")
    format: str = Field("txt", description="File format for the quiz data (txt, csv, pdf, etc.)")
    question_type: str = Field("multichoice", description="Type of questions requested (multichoice, true-false, open-ended)")
    num_question: int = Field(..., description="Number of questions to include in the download", ge=1)
  
