from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum
import re


class UserRegisterSchema(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str

    @field_validator('password')
    def validate_password(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[!@\$%\^&\*\(\)\-_,\.\?":\{\}\|<>]', value):
            raise ValueError('Password must contain at least one special character.')
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        return value


class UserResponseSchema(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    role: str
    quizzes: Optional[List[str]] = []
    created_at: datetime
    updated_at: Optional[datetime]


class UserBaseSchema(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    
  

class NewUserSchema(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    role: str
    created_at: datetime
    updated_at: Optional[datetime]


class UserSchema(UserBase):
    id: str
    quizzes: Optional[List[str]] = [] 
    is_active: bool
    is_verified: Optional[bool] = False
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified: Optional[bool] = None


class UpdateUserSchema(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    quizzes: Optional[List[str]] = [] 
    password: Optional[str] = None 
    is_active: Optional[bool] = True
    role:  Optional[str] = None 
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

   
class CreateUserRequest(UserRegisterSchema):
    pass


class DeleteUserResponse(BaseModel):
    message: str
    delete_count: int



class SeedUserSchema(UserBaseSchema):
    quizzes: Optional[List[str]] = [] 
    hashed_password: str
    is_active: bool 
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResetMethod(str, Enum):
    OTP = "otp"
    TOKEN = "token"

class PasswordResetRequest(BaseModel):
    email: EmailStr
    reset_method: ResetMethod
    otp: str | None = None
    token: str | None = None
    new_password: str

    @field_validator('new_password')
    def validate_password(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter.')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[!@\$%\^&\*\(\)\-_,\.\?":\{\}\|<>]', value):
            raise ValueError('Password must contain at least one special character.')
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        return value

    @model_validator(mode="after")
    def check_required_fields(cls, values):
            if values.reset_method == ResetMethod.OTP and not values.otp:
                raise ValueError("OTP is required when reset method is 'otp'")
            if values.reset_method == ResetMethod.TOKEN and not values.token:
                raise ValueError("Token is required when reset method is 'token'")
            return values

class ResendVerificationRequest(BaseModel):
    email: EmailStr
    #method: str

class PasswordResetResponse(BaseModel):
    message: str
    success: bool

class RequestPasswordReset(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    message: str