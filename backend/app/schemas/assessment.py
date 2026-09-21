"""Pydantic schemas for CreditAssessment entity."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.assessment import RiskLevel


class CreditAssessmentBase(BaseModel):
    """Base fields representing assessment outputs."""

    credit_score: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Assigned alternative credit score (nullable if insufficient evidence)",
    )
    risk_probability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Estimated probability of default bounded [0, 1]",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Categorical risk tier (LOWER, MODERATE, HIGHER, INSUFFICIENT)",
    )
    confidence: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Model confidence level bounded [0, 1]",
    )
    debt_to_income: Optional[Decimal] = Field(
        None,
        description="Estimated debt-to-income ratio",
    )
    utilization: Optional[Decimal] = Field(
        None,
        description="Credit utilization proxy indicator",
    )
    income_stability: Optional[Decimal] = Field(
        None,
        description="Income stability index",
    )
    repayment_reliability: Optional[Decimal] = Field(
        None,
        description="Historical or platform repayment consistency",
    )
    assessment_status: str = Field(
        default="COMPLETED",
        description="Status of assessment generation process",
    )


class CreditAssessmentCreate(CreditAssessmentBase):
    """Schema for recording an assessment output."""

    application_id: UUID
    model_version_id: UUID


class CreditAssessmentResponse(CreditAssessmentBase):
    """Response schema returning credit assessment outputs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    model_version_id: UUID
    assessed_at: datetime
    created_at: datetime
