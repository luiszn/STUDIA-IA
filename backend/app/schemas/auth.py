"""Authentication and profile schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

PASSWORD_MIN_LENGTH = 8


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    university: str | None = Field(default=None, max_length=160)
    career: str | None = Field(default=None, max_length=160)
    academic_year: str | None = Field(default=None, max_length=40)
    daily_study_goal_minutes: int = Field(default=120, ge=15, le=960)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if value.strip() != value:
            raise ValueError("Password must not start or end with whitespace.")
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one number.")
        return value

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Please enter your full name.")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None = None
    university: str | None = None
    career: str | None = None
    academic_year: str | None = None
    timezone: str
    daily_study_goal_minutes: int
    locale: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime
    initials: str = ""


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    university: str | None = Field(default=None, max_length=160)
    career: str | None = Field(default=None, max_length=160)
    academic_year: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=64)
    daily_study_goal_minutes: int | None = Field(default=None, ge=15, le=960)
    locale: str | None = Field(default=None, max_length=10)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


TokenResponse.model_rebuild()