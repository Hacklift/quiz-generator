from pydantic import BaseModel, Field

from typing import List, Optional

from datetime import datetime, timezone





class NewQuizSchema(BaseModel):

    title: str

    description: str

    quiz_type: str

    owner_id: Optional[str] = None

    created_at: Optional[datetime]  = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: Optional[datetime]  = None

    questions: List



class QuizSchema(NewQuizSchema):

    id: str



class UpdateQuiz(BaseModel):

    title: Optional[str] = None

    description: Optional[str] = None

    quiz_type: Optional[str] = None

    questions: Optional[List[dict]] = None

    updated_at: datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))




class NewQuizResponse(BaseModel):

    id: str

    title: str

    description: str


class DeleteQuizResponse(BaseModel):

    message: str

    delete_count: int

