from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from .validators import PyObjectId



class UserDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    quizzes: Optional[List[str]] = []  
    is_active: bool
    is_verified: bool 
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        from_attributes = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class SeedUser(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    quizzes: Optional[List[str]] = []  
    hashed_password: str
    is_active: bool 
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        from_attributes = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    created_at: Optional[str] = None

    class Config:
        from_attributes = True