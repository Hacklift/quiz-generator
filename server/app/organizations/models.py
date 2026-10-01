from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


OrganizationKind = Literal["personal", "school", "tutoring", "corporate"]
OrganizationStatus = Literal["active", "suspended", "archived"]
MembershipRole = Literal[
    "owner",
    "admin",
    "author",
    "facilitator",
    "learner",
    "guardian",
    "auditor",
]
MembershipStatus = Literal["invited", "active", "suspended", "removed"]
InvitationStatus = Literal[
    "invited",
    "accepting",
    "accepted",
    "declined",
    "revoked",
    "expired",
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationSettings(BaseModel):
    """Reserved typed settings surface; tenant features add fields deliberately."""

    model_config = ConfigDict(extra="forbid")


class OrganizationDocument(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    kind: OrganizationKind
    name: str = Field(min_length=1, max_length=160)
    status: OrganizationStatus = "active"
    settings: OrganizationSettings = Field(default_factory=OrganizationSettings)
    personal_owner_user_id: str | None = Field(default=None, min_length=1)
    system_key: Literal["platform_library"] | None = None
    created_by_user_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("organization name must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_personal_owner(self):
        if self.system_key is not None:
            if (
                self.kind != "personal"
                or self.personal_owner_user_id is not None
                or self.created_by_user_id is not None
            ):
                raise ValueError(
                    "platform library must be an ownerless system personal organization"
                )
            return self
        if self.kind == "personal" and not self.personal_owner_user_id and self.system_key is None:
            raise ValueError("personal organizations require a personal owner")
        if self.personal_owner_user_id and self.kind != "personal":
            raise ValueError("personal owner is only valid for personal organizations")
        return self


class OrganizationMembershipDocument(BaseModel):
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    organization_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    role: MembershipRole
    status: MembershipStatus = "active"
    joined_at: datetime | None = None
    invited_by_user_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )


class OrganizationInvitationDocument(BaseModel):
    """One-time email invitation; the raw token is never persisted."""

    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    organization_id: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)
    email_normalized: str = Field(min_length=3, max_length=320)
    role: MembershipRole
    status: InvitationStatus = "invited"
    token_hash: str = Field(min_length=64, max_length=64)
    invited_by_user_id: str = Field(min_length=1)
    accepted_by_user_id: str | None = None
    acceptance_claim_id: str | None = None
    acceptance_lease_expires_at: datetime | None = None
    expires_at: datetime
    accepted_at: datetime | None = None
    declined_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        extra="forbid",
    )

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: MembershipRole) -> MembershipRole:
        if value == "owner":
            raise ValueError("owner role cannot be granted by invitation")
        return value


class OrganizationPrincipal(BaseModel):
    """Validated authenticated identity used by organization policy checks."""

    user_id: str
    session_id: str
    platform_role: str = "user"

    model_config = ConfigDict(extra="forbid")


class OrganizationContext(BaseModel):
    """A principal's server-validated active organization membership."""

    organization_id: str
    organization_kind: OrganizationKind
    membership_role: MembershipRole
    principal: OrganizationPrincipal
    membership: dict[str, Any]
    active_scope_recovered: bool = False

    model_config = ConfigDict(extra="forbid")
