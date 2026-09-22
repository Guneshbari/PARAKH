"""Pydantic schemas for Application entity."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.application import ApplicationStatus


class ApplicationBase(BaseModel):
    """Base fields for an assessment application."""

    requested_loan_amount: Decimal = Field(
        ...,
        gt=0,
        description="Requested financing amount in INR (must be strictly positive)",
    )
    loan_purpose: Optional[str] = Field(
        None,
        max_length=255,
        description="Specific purpose of loan request",
    )
    preferred_repayment_period: Optional[int] = Field(
        None,
        gt=0,
        le=120,
        description="Preferred repayment duration in months",
    )


class ApplicationCreate(ApplicationBase):
    """Schema for creating a credit assessment application."""

    applicant_profile_id: UUID


class ApplicationUpdate(BaseModel):
    """Schema for updating application details or status."""

    requested_loan_amount: Optional[Decimal] = Field(None, gt=0)
    loan_purpose: Optional[str] = Field(None, max_length=255)
    preferred_repayment_period: Optional[int] = Field(None, gt=0, le=120)
    status: Optional[ApplicationStatus] = None


class ApplicationStatusUpdate(BaseModel):
    """Schema for advancing application lifecycle status."""

    status: ApplicationStatus = Field(
        ...,
        description="Target lifecycle status (e.g. SUBMITTED, UNDER_REVIEW)",
    )


class ApplicationSummary(BaseModel):
    """Lightweight summary schema for listing applications."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requested_loan_amount: Decimal
    status: ApplicationStatus
    created_at: datetime


class ApplicationResponse(ApplicationBase):
    """Full application response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    applicant_profile_id: UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
