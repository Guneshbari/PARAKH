"""Pydantic schemas for user authentication and JWT tokens."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Credentials required for password-based user authentication."""

    email: str = Field(..., description="Registered user email address")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Authentication response returning signed JWT access token and user metadata."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., description="JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token schema type")
    expires_in: int = Field(..., description="Token validity lifetime in seconds")
    user_id: UUID = Field(..., description="Authenticated user identifier")
    email: str = Field(..., description="Authenticated user email")
    role: UserRole = Field(..., description="Role assigned to authenticated user")


class TokenPayload(BaseModel):
    """Internal decoded JWT access token claims."""

    sub: UUID
    role: UserRole
    type: str = "access"
    exp: int
    iat: int
    nbf: int
