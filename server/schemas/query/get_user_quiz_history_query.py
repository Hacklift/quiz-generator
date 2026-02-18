from fastapi import Query

from pydantic import BaseModel, Field

from .query_patterns import QueryPattern


class GetUserQuizHistoryQuery(BaseModel):

    pattern: str = Field(QueryPattern.GET_USER_QUIZ_HISTORY)

    user_id: str = Query(..., description="User's id")

