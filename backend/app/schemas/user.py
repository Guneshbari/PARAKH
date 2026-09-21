"""Pydantic schemas for User entity."""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.user import UserRole

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserBase(BaseModel):
    """Base user properties."""

    email: str = Field(
        ...,
        max_length=255,
        description="Unique user email address",
    )
    role: UserRole = UserRole.APPLICANT

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate and normalize email string without third-party dependencies."""
        normalized = v.strip().lower()
        if not re.match(EMAIL_REGEX, normalized):
            raise ValueError("Invalid email address format")
        return normalized


class UserCreate(UserBase):
    """Schema for user registration / creation.

    Password is required on creation, but password_hash is never exposed in response models.
    """

    password: str = Field(
        ...,
        min_length=8,
        description="Plaintext password provided during registration (never stored plaintext)",
    )


class UserUpdate(BaseModel):
    """Schema for updating user details."""

    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None:
            return None
        normalized = v.strip().lower()
        if not re.match(EMAIL_REGEX, normalized):
            raise ValueError("Invalid email address format")
        return normalized


class UserSummary(BaseModel):
    """Minimal user summary representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole


class UserResponse(UserBase):
    """Full user response schema. Strictly excludes password / password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
