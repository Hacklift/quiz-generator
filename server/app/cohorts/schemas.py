from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from server.app.cohorts.models import (
    CohortKind, CohortMemberRole, CohortStatus, cohort_name, object_id_string,
)


class CreateCohortRequest(BaseModel):
    kind: CohortKind
    name: str = Field(min_length=1, max_length=160)
    parent_cohort_id: str | None = None

    model_config = ConfigDict(extra="forbid")
    _name = field_validator("name")(cohort_name)

    @field_validator("parent_cohort_id")
    @classmethod
    def valid_parent(cls, value: str | None) -> str | None:
        return object_id_string(value) if value is not None else None


class UpdateCohortRequest(BaseModel):
    kind: CohortKind | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    parent_cohort_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name must not be null")
        return cohort_name(value)

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("kind must not be null")
        return value

    @field_validator("parent_cohort_id")
    @classmethod
    def valid_parent(cls, value: str | None) -> str | None:
        return object_id_string(value) if value is not None else None


class SetCohortMemberRequest(BaseModel):
    user_id: str
    role: CohortMemberRole = "member"
    can_assign: StrictBool | None = None
    can_report: StrictBool | None = None

    model_config = ConfigDict(extra="forbid")
    _id = field_validator("user_id")(object_id_string)

    @field_validator("can_assign", "can_report")
    @classmethod
    def explicit_flags_must_be_boolean(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("delegation flags must be booleans when supplied")
        return value

    @model_validator(mode="after")
    def resolve_delegation(self):
        if self.role != "facilitator" and (self.can_assign or self.can_report):
            raise ValueError("only facilitators can receive delegation")
        for field in ("can_assign", "can_report"):
            if getattr(self, field) is None:
                setattr(self, field, self.role == "facilitator")
        return self


class CohortResponse(BaseModel):
    id: str
    organization_id: str
    kind: CohortKind
    name: str
    parent_cohort_id: str | None = None
    status: CohortStatus
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime
    can_manage: bool = False
    can_assign: bool = False
    can_report: bool = False


class CohortMemberResponse(BaseModel):
    user_id: str
    role: CohortMemberRole
    name: str
    can_assign: bool = False
    can_report: bool = False


class CohortMemberOption(BaseModel):
    user_id: str
    name: str


class CohortPageResponse(BaseModel):
    items: list[CohortResponse]
    next_cursor: str | None = None


class CohortMemberPageResponse(BaseModel):
    items: list[CohortMemberResponse]
    next_cursor: str | None = None


class CohortMemberOptionsResponse(BaseModel):
    items: list[CohortMemberOption]
    next_cursor: str | None = None
