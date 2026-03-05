from pydantic import BaseModel, Field
from typing import Any, List, Optional
from datetime import datetime
from bson import ObjectId


class FolderModel(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    name: str
    quizzes: List[Any] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        orm_mode = True
        json_encoders = {ObjectId: str}


class FolderCreate(BaseModel):
    user_id: Optional[str] = None
    name: str


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    quizzes: Optional[List[str]] = None


class BulkDeleteFoldersRequest(BaseModel):
    folder_ids: List[str]


class BulkRemoveRequest(BaseModel):
    quiz_ids: List[str]


class FolderQuizRef(BaseModel):
    quiz_id: str
    added_at: datetime = Field(default_factory=datetime.utcnow)


class UserFolderRecord(BaseModel):
    user_id: str
    name: str
    quiz_refs: List[FolderQuizRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
