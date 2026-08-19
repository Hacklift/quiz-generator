from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Any, List, Literal, Optional
from datetime import datetime, timezone
from bson import ObjectId
from .validators import PyObjectId
from server.app.users.identity import DEFAULT_AVATAR_COLOR
from server.app.users.persona import persona_pair_is_valid


# Literal members are pinned against persona.PERSONA_USER_TYPES_BY_CATEGORY by
# tests/test_persona_taxonomy.py — Literal cannot be built from a runtime tuple.
PersonaCategoryField = Literal["school", "corporate"]
PersonaUserTypeField = Literal[
    "teacher", "lecturer", "student", "parent", "business", "employee", "hr"
]


class UserPersona(BaseModel):
    category: Optional[PersonaCategoryField] = None
    user_type: Optional[PersonaUserTypeField] = None
    set_at: Optional[datetime] = None
    source: Optional[str] = "unset"

    @model_validator(mode="after")
    def validate_pair(self):
        if not persona_pair_is_valid(self.category, self.user_type):
            raise ValueError(
                "persona user_type must belong to persona category, "
                "and both must be set together"
            )
        return self


class UserProfile(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar_color: Optional[str] = DEFAULT_AVATAR_COLOR
    persona: Optional[UserPersona] = None

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v):
        if v and len(v) > 500:
            raise ValueError("Bio must not exceed 500 characters")
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Website must be a valid URL starting with http:// or https://")
        return v


class UserDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    username_normalized: Optional[str] = None
    email: EmailStr
    email_normalized: Optional[str] = None
    hashed_password: str
    profile: UserProfile = Field(default_factory=UserProfile)
    quizzes: Optional[List[str]] = []  # List of quiz IDs associated with the user
    is_active: bool = True
    is_verified: bool 
    status: str = "pending_verification"
    role: str = "user"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_plan: Optional[str] = "free"
    subscription_status: Optional[str] = "inactive"
    current_period_end: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    deletion_reason: Optional[str] = None
    schema_version: int = 1

    @property
    def full_name(self) -> Optional[str]:
        return self.profile.full_name

    @property
    def bio(self) -> Optional[str]:
        return self.profile.bio

    @property
    def location(self) -> Optional[str]:
        return self.profile.location

    @property
    def website(self) -> Optional[str]:
        return self.profile.website

    @property
    def avatar_color(self) -> Optional[str]:
        return self.profile.avatar_color

    @property
    def persona(self) -> Optional[UserPersona]:
        return self.profile.persona

    class Config:
        populate_by_name = True
        from_attributes = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class SeedUser(BaseModel):
    username: str
    username_normalized: Optional[str] = None
    email: EmailStr
    email_normalized: Optional[str] = None
    profile: UserProfile = Field(default_factory=UserProfile)
    quizzes: Optional[List[str]] = []  # List of quiz IDs associated with the user
    hashed_password: str
    is_active: bool 
    is_verified: bool = False
    status: str = "pending_verification"
    role: str = "user"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_plan: Optional[str] = "free"
    subscription_status: Optional[str] = "inactive"
    current_period_end: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    deletion_reason: Optional[str] = None
    schema_version: int = 1
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
    persona_category: Optional[str] = None
    persona_user_type: Optional[str] = None
    persona_set_at: Optional[str] = None
    role: Optional[str] = "user"
    status: Optional[str] = "pending_verification"
    is_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_plan: Optional[str] = "free"
    subscription_status: Optional[str] = "inactive"
    current_period_end: Optional[str] = None
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
    persona_category: Optional[str] = None
    persona_user_type: Optional[str] = None

    @model_validator(mode="after")
    def validate_persona(self):
        if self.persona_category is None and self.persona_user_type is None:
            return self
        if not persona_pair_is_valid(self.persona_category, self.persona_user_type):
            raise ValueError(
                "persona_user_type must belong to persona_category, "
                "and both must be provided together"
            )
        return self

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


class UpdatePersonaRequest(BaseModel):
    """The only profile fields an authenticated user may change pre-verification."""

    persona_category: PersonaCategoryField
    persona_user_type: PersonaUserTypeField

    @model_validator(mode="after")
    def validate_persona(self):
        if not persona_pair_is_valid(
            self.persona_category, self.persona_user_type
        ):
            raise ValueError("persona_user_type must belong to persona_category")
        return self


class UpdateProfileResponse(BaseModel):
    message: str
    user: UserOut


class UserSession(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    session_id: str
    jti: str
    refresh_token_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    device_info: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AuthEvent(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: Optional[str] = None
    event_type: str
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
