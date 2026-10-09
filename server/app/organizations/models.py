from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

from server.app.i18n.locales import SupportedLocale


OrganizationRole = Literal["owner", "admin", "member"]


class CreateOrganizationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    default_locale: SupportedLocale = "en"


class UpdateOrganizationSettingsRequest(BaseModel):
    default_locale: SupportedLocale


class OrganizationSettingsResponse(BaseModel):
    id: str
    name: str
    default_locale: SupportedLocale
    role: OrganizationRole
    created_at: datetime
    updated_at: datetime


class SetActiveOrganizationResponse(BaseModel):
    active_organization_id: str


class OrganizationMemberResponse(BaseModel):
    user_id: str
    role: OrganizationRole
    created_at: datetime


class OrganizationMemberListResponse(BaseModel):
    members: list[OrganizationMemberResponse]
