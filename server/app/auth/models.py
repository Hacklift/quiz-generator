from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator

from typing import List, Optional

from datetime import datetime, timezone

from enum import Enum

import re


class LoginRequestModel(BaseModel):

    identifier: str = Field(..., description="Email or username of the user")

    password: str = Field(..., min_length=6, description="User's password")


class LoginResponse(BaseModel):

    message: str

    access_token: str

    refresh_token: str

    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):

    refresh_token: str


class RefreshTokenResponse(BaseModel):

    access_token: str

    token_type: str

    refresh_token: str
