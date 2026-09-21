"""Pydantic schemas for FinancialSignal entity."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.financial_signal import SignalSource


class FinancialSignalBase(BaseModel):
    """Base fields for aggregated financial indicators (data-minimization compliant)."""

    source: SignalSource
    measurement_period_start: Optional[datetime] = None
    measurement_period_end: Optional[datetime] = None

    average_income: Optional[Decimal] = Field(None, ge=0, description="Average income over measurement window")
    median_income: Optional[Decimal] = Field(None, ge=0, description="Median income over measurement window")
    income_volatility: Optional[Decimal] = Field(None, ge=0, description="Income volatility metric")
    income_trend: Optional[str] = Field(None, max_length=50, description="Trajectory direction (growing/stable/etc)")
    active_days: Optional[int] = Field(None, ge=0, description="Total active working days recorded")
    payment_regularity: Optional[Decimal] = Field(None, ge=0, le=1, description="Regularity index between 0 and 1")
    cashflow_buffer: Optional[Decimal] = Field(None, ge=0, description="Average reserve/buffer amount")
    existing_obligation: Optional[Decimal] = Field(None, ge=0, description="Known ongoing debt commitments")
    platform_rating: Optional[Decimal] = Field(None, ge=0, le=5, description="Composite customer/platform rating")
    repayment_reliability: Optional[Decimal] = Field(None, ge=0, le=1, description="Reliability metric between 0 and 1")
    signal_metadata: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive structured summary attributes")


class FinancialSignalCreate(FinancialSignalBase):
    """Schema for ingesting aggregated signals for an application."""

    model_config = ConfigDict(extra="allow")

    application_id: Optional[UUID] = None
    applicant_profile_id: Optional[UUID] = None


class FinancialSignalResponse(FinancialSignalBase):
    """Response schema for financial signal evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    applicant_profile_id: Optional[UUID]
    created_at: datetime
