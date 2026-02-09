from pydantic import BaseModel, Field

from typing import List, Optional

from datetime import datetime, timezone

from bson import ObjectId

from .validators import PyObjectId




class QuizDB(BaseModel):

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    title: str

    description: str

    quiz_type: str

    owner_id: Optional [str] = None

    created_at: Optional[datetime]  = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    questions: List


    class Config:

        populate_by_name = True

        arbitrary_types_allowed = True

        json_encoders = {ObjectId: str}



class SeedQuiz(BaseModel):

    title: str

    description: str

    quiz_type: str

    owner_id: Optional [str] = None

    created_at: Optional[datetime]  = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: Optional[datetime]  = None

    questions: List


    class Config:

        populate_by_name = True

        arbitrary_types_allowed = True


