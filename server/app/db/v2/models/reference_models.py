from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

class FolderCreateV2(BaseModel):
    user_id: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FolderDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: str
    name: str
    description: Optional[str] = None
    legacy_folder_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )


class FolderItemCreateV2(BaseModel):
    folder_id: str
    quiz_id: str
    added_by: Optional[str] = None
    position: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class FolderItemDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    folder_id: str
    quiz_id: str
    added_by: Optional[str] = None
    position: Optional[int] = None
    display_title: Optional[str] = None
    legacy_folder_item_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )


class SavedQuizCreateV2(BaseModel):
    user_id: str
    quiz_id: str

    model_config = ConfigDict(extra="forbid")


class SavedQuizDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: str
    quiz_id: str
    display_title: Optional[str] = None
    legacy_saved_quiz_id: Optional[str] = None
    saved_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )


class QuizHistoryCreateV2(BaseModel):
    user_id: str
    quiz_id: str
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class QuizHistoryDocumentV2(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    user_id: str
    quiz_id: str
    action: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    legacy_history_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )
