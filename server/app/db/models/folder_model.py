from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from typing import Any

class FolderModel(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    name: str
    quizzes: List[Any] = []  # <-- allow full quiz objects, not just IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    class Config:
        orm_mode = True
        json_encoders = {ObjectId: str}

class FolderCreate(BaseModel):
    user_id: str
    name: str

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    quizzes: Optional[List[str]] = None

class BulkDeleteFoldersRequest(BaseModel):
    folder_ids: List[str]

class BulkRemoveRequest(BaseModel):
    quiz_ids: List[str]