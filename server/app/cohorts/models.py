from __future__ import annotations

from datetime import datetime
from typing import Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from server.app.organizations.models import utcnow

CohortKind = Literal["class", "course", "team", "department", "campaign"]
CohortStatus = Literal["active", "archived"]
CohortMemberRole = Literal["facilitator", "member", "guardian"]


def object_id_string(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("must be a valid ObjectId")
    return str(ObjectId(value))


def cohort_name(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("cohort name must not be blank")
    return value


class CohortDocument(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    organization_id: str
    kind: CohortKind
    name: str = Field(min_length=1, max_length=160)
    parent_cohort_id: str | None = None
    status: CohortStatus = "active"
    created_by_user_id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    _name = field_validator("name")(cohort_name)
    _ids = field_validator("organization_id", "created_by_user_id")(object_id_string)

    @field_validator("parent_cohort_id")
    @classmethod
    def valid_parent(cls, value: str | None) -> str | None:
        return object_id_string(value) if value is not None else None


class CohortMembershipDocument(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    organization_id: str
    cohort_id: str
    user_id: str
    role: CohortMemberRole
    status: Literal["active", "removed"] = "active"
    can_assign: bool = False
    can_report: bool = False
    created_by_user_id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    _ids = field_validator(
        "organization_id", "cohort_id", "user_id", "created_by_user_id"
    )(object_id_string)

    @model_validator(mode="after")
    def facilitator_only_delegation(self):
        if self.role != "facilitator" and (self.can_assign or self.can_report):
            raise ValueError("only facilitators can receive delegation")
        return self
