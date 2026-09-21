"""Pydantic schemas for Consent entity."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.consent import ConsentDataSource


class ConsentCreate(BaseModel):
    """Schema for granting consent to access a data source."""

    data_source: ConsentDataSource
    purpose: str = Field(..., min_length=3, max_length=255, description="Purpose of data access")
    application_id: Optional[UUID] = None
    applicant_profile_id: Optional[UUID] = None
    granted: bool = Field(default=True, description="Explicit grant indicator (must be true)")


class ConsentResponse(BaseModel):
    """Response schema representing an explicit consent record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: Optional[UUID]
    applicant_profile_id: Optional[UUID]
    data_source: ConsentDataSource
    purpose: str
    granted: bool
    granted_at: datetime
    revoked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
