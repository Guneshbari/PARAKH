"""Pydantic schemas for ApplicantProfile entity."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


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

    @model_validator(mode="before")
    @classmethod
    def map_incoming_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Accept work_type if gig_work_type is omitted
            if not data.get("gig_work_type") and data.get("work_type"):
                data["gig_work_type"] = str(data["work_type"])
            # Map experience_months to years_working if years_working is omitted
            if data.get("years_working") is None and data.get("experience_months") is not None:
                try:
                    exp = float(data["experience_months"])
                    data["years_working"] = Decimal(str(round(exp / 12.0, 1)))
                except (ValueError, TypeError):
                    pass
            # Map preferred_loan_purpose to business_or_loan_purpose if omitted
            if not data.get("business_or_loan_purpose") and data.get("preferred_loan_purpose"):
                data["business_or_loan_purpose"] = str(data["preferred_loan_purpose"])[:255]
            # Map average_working_days_per_week to average_working_days if omitted
            if data.get("average_working_days") is None and data.get("average_working_days_per_week") is not None:
                try:
                    days = float(data["average_working_days_per_week"])
                    data["average_working_days"] = min(31, max(0, int(round(days * 4.33))))
                except (ValueError, TypeError):
                    pass
        return data


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

    @model_validator(mode="before")
    @classmethod
    def map_incoming_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("gig_work_type") and data.get("work_type"):
                data["gig_work_type"] = str(data["work_type"])
            if data.get("years_working") is None and data.get("experience_months") is not None:
                try:
                    exp = float(data["experience_months"])
                    data["years_working"] = Decimal(str(round(exp / 12.0, 1)))
                except (ValueError, TypeError):
                    pass
            if not data.get("business_or_loan_purpose") and data.get("preferred_loan_purpose"):
                data["business_or_loan_purpose"] = str(data["preferred_loan_purpose"])[:255]
        return data


class ApplicantProfileResponse(ApplicantProfileBase):
    """Response schema for applicant profile."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def work_type(self) -> str:
        return self.gig_work_type

