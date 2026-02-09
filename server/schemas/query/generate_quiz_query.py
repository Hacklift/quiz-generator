from fastapi import Query

from pydantic import BaseModel, Field

from .query_patterns import QueryPattern


class GenerateQuizQuery(BaseModel):

    pattern: str = Field(QueryPattern.GENERATE_QUIZ)

    user_id: str = Query(..., description="User's id")

    question_type: str = Query("multichoice", description="Type of questions requested (multichoice, true-false, open-ended)")

    num_question: int = Query(..., description="Number of questions to include in the download", ge=1)

