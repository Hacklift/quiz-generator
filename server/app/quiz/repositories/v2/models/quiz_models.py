from datetime import datetime
from enum import Enum
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..constants import QUIZ_SCHEMA_VERSION


class QuizTypeV2(str, Enum):
    MULTICHOICE = "multichoice"
    TRUE_FALSE = "true-false"
    OPEN_ENDED = "open-ended"
    SHORT_ANSWER = "short-answer"


class QuizVisibilityV2(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class QuizStatusV2(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class QuizSourceV2(str, Enum):
    AI = "ai"
    MANUAL = "manual"
    SEED = "seed"
    LEGACY = "legacy"


class QuizClassificationMethodV2(str, Enum):
    SEED_PATH = "seed_path"
    DETERMINISTIC = "deterministic"
    AI = "ai"
    MANUAL = "manual"


class QuizClassificationV2(BaseModel):
    method: QuizClassificationMethodV2
    confidence: float = Field(ge=0, le=1)

    model_config = ConfigDict(extra="forbid")


class QuizQuestionV2(BaseModel):
    question: str
    correct_answer: str
    options: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_answers(cls, data):
        if isinstance(data, dict) and "correct_answer" not in data and "answer" in data:
            normalized = dict(data)
            normalized["correct_answer"] = normalized.pop("answer")
            return normalized
        return data


class QuizCreateV2(BaseModel):
    title: str
    quiz_type: QuizTypeV2
    questions: List[QuizQuestionV2]
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    visibility: QuizVisibilityV2 = QuizVisibilityV2.PRIVATE
    status: QuizStatusV2 = QuizStatusV2.ACTIVE
    source: QuizSourceV2 = QuizSourceV2.MANUAL
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_slug: Optional[str] = None
    classification: Optional[QuizClassificationV2] = None

    model_config = ConfigDict(extra="forbid")


class QuizMetadataUpdateV2(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[QuizVisibilityV2] = None
    status: Optional[QuizStatusV2] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_slug: Optional[str] = None
    classification: Optional[QuizClassificationV2] = None

    model_config = ConfigDict(extra="forbid")


class QuizQuestionsUpdateV2(BaseModel):
    questions: List[QuizQuestionV2]

    model_config = ConfigDict(extra="forbid")

class ParticipantAccessModeV2(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    INVITED_ONLY = "invited_only"

class QuizDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    title: str
    quiz_type: QuizTypeV2
    questions: List[QuizQuestionV2]
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    visibility: QuizVisibilityV2 = QuizVisibilityV2.PRIVATE
    status: QuizStatusV2 = QuizStatusV2.ACTIVE
    source: QuizSourceV2 = QuizSourceV2.MANUAL
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory: Optional[str] = None
    subcategory_slug: Optional[str] = None
    classification: Optional[QuizClassificationV2] = None
    legacy_source_collection: Optional[str] = None
    legacy_quiz_id: Optional[str] = None
    content_fingerprint: Optional[str] = None
    structure_fingerprint: Optional[str] = None
    live_quiz_enabled: bool = False
    time_limit_minutes: Optional[int] = None
    access_code: Optional[str] = None
    access_code_expires_at: Optional[datetime] = None
    participant_access_mode: ParticipantAccessModeV2 = ParticipantAccessModeV2.PUBLIC
    invited_participant_emails: List[str] = Field(default_factory=list)
    schema_version: int = QUIZ_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )
