from pydantic import BaseModel, Field, EmailStr, field_validator
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
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_color: Optional[str] = "#143E6F"
    quizzes: Optional[List[str]] = []  # List of quiz IDs associated with the user
    is_active: bool
    is_verified: bool 
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v):
        if v and len(v) > 500:
            raise ValueError('Bio must not exceed 500 characters')
        return v

    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Website must be a valid URL starting with http:// or https://')
        return v


    class Config:
        populate_by_name = True
        from_attributes = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class SeedUser(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_color: Optional[str] = "#143E6F"
    quizzes: Optional[List[str]] = []  # List of quiz IDs associated with the user
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
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_color: Optional[str] = "#143E6F"
    role: Optional[str] = "user"
    is_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    created_at: Optional[str] = None
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_color: Optional[str] = None

    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v):
        if v and len(v) > 500:
            raise ValueError('Bio must not exceed 500 characters')
        return v

    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Website must be a valid URL starting with http:// or https://')
        return v


class UpdateProfileResponse(BaseModel):
    message: str
    user: UserOut
