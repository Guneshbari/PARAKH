"""Pydantic schemas for ApplicantProfile entity."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ApplicantProfileBase(BaseModel):
    """Base fields for gig worker profile."""

    gig_work_type: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Type of platform/gig work (e.g. food delivery, ride hailing)",
    )
    years_working: Optional[Decimal] = Field(
        None,
        ge=0,
        le=50,
        description="Experience in platform work in years",
    )
    average_working_days: Optional[int] = Field(
        None,
        ge=0,
        le=31,
        description="Average active working days per month",
    )
    business_or_loan_purpose: Optional[str] = Field(
        None,
        max_length=255,
        description="Primary commercial or operational purpose for seeking credit",
    )


class ApplicantProfileCreate(ApplicantProfileBase):
    """Schema for creating an applicant profile."""

    user_id: Optional[UUID] = Field(
        None,
        description="Associated User account primary key UUID",
    )


class ApplicantProfileUpdate(BaseModel):
    """Schema for updating an applicant profile."""

    gig_work_type: Optional[str] = Field(None, min_length=2, max_length=100)
    years_working: Optional[Decimal] = Field(None, ge=0, le=50)
    average_working_days: Optional[int] = Field(None, ge=0, le=31)
    business_or_loan_purpose: Optional[str] = Field(None, max_length=255)


class ApplicantProfileResponse(ApplicantProfileBase):
    """Response schema for applicant profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
