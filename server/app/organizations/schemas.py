from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from server.app.organizations.models import MembershipRole, MembershipStatus, OrganizationKind


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: OrganizationKind

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("organization name must not be blank")
        return normalized

    @field_validator("kind")
    @classmethod
    def shared_organizations_only(cls, value: OrganizationKind) -> OrganizationKind:
        if value == "personal":
            raise ValueError("personal organizations are implicit")
        return value


class CreateOrganizationInvitationRequest(BaseModel):
    email: EmailStr
    role: MembershipRole
    expires_in_days: int = Field(default=7, ge=1, le=30)

    model_config = ConfigDict(extra="forbid")

    @field_validator("role")
    @classmethod
    def invitations_cannot_grant_owner(cls, value: MembershipRole) -> MembershipRole:
        if value == "owner":
            raise ValueError("owner role cannot be granted by invitation")
        return value


class InvitationDecisionRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)

    model_config = ConfigDict(extra="forbid")


class UpdateOrganizationMembershipRequest(BaseModel):
    status: MembershipStatus

    model_config = ConfigDict(extra="forbid")

    @field_validator("status")
    @classmethod
    def owner_membership_cannot_be_managed_here(cls, value: MembershipStatus) -> MembershipStatus:
        if value not in {"active", "suspended", "removed"}:
            raise ValueError(
                "membership management may reactivate a suspended member, or suspend or remove a member"
            )
        return value


class OrganizationMembershipResponse(BaseModel):
    organization_id: str
    organization_name: str
    organization_kind: str
    role: MembershipRole
    status: MembershipStatus
    is_active: bool
    # True only when the session selector was stale and the server selected
    # this proven default membership for the current request.
    active_scope_recovered: bool = False


class OrganizationMemberResponse(BaseModel):
    user_id: str
    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    role: MembershipRole
    status: MembershipStatus


class OrganizationMemberPageResponse(BaseModel):
    items: list[OrganizationMemberResponse]
    next_cursor: str | None = None


class OrganizationInvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: EmailStr
    role: MembershipRole
    status: str
    expires_at: datetime
    created_at: datetime


class OrganizationInvitationPageResponse(BaseModel):
    items: list[OrganizationInvitationResponse]
    next_cursor: str | None = None


class ActiveOrganizationSelectionRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(extra="forbid")


class ActiveOrganizationResponse(BaseModel):
    organization_id: str
    organization_name: str
    organization_kind: str
    role: MembershipRole
