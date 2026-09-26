"""Pydantic schemas for FinancialSignal entity and structured runtime telemetry."""
import datetime as dt
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.financial_signal import SignalSource


class WeeklyPayoutRecord(BaseModel):
    """Granular settlement payout cycle in trailing observation window."""

    model_config = ConfigDict(extra="ignore")

    payout_timestamp: Union[dt.datetime, str] = Field(
        ...,
        description="Settlement event timestamp (ISO-8601 string or datetime)",
    )
    net_amount: Decimal = Field(
        ...,
        ge=0,
        description="Net payout amount in INR received by worker (must be non-negative)",
    )
    gross_amount: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Gross earnings prior to platform commission deductions",
    )
    active_days: Optional[int] = Field(
        None,
        ge=0,
        le=7,
        description="Active delivery or shift days in payout cycle",
    )
    payout_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Unique payout transaction identifier",
    )
    cycle_index: Optional[int] = Field(
        None,
        ge=1,
        le=52,
        description="Sequential index of payout cycle within observation horizon",
    )
    is_settled: bool = Field(
        default=True,
        description="Flag indicating confirmed settlement",
    )


class DailyShiftRecord(BaseModel):
    """Daily platform engagement and shift activity record."""

    model_config = ConfigDict(extra="ignore")

    date: Union[dt.date, dt.datetime, str] = Field(
        ...,
        description="Calendar date of shift",
    )
    hours_worked: float = Field(
        default=0.0,
        ge=0.0,
        le=24.0,
        description="Active working hours on shift (0.0 to 24.0)",
    )
    is_active: bool = Field(
        default=True,
        description="Flag indicating logged platform shift",
    )
    is_weekend: Optional[bool] = Field(
        None,
        description="Flag for weekend shifts (auto-derived if omitted)",
    )
    gross_earnings: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Gross platform earnings for shift",
    )
    net_earnings: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Net shift earnings after platform deductions",
    )
    platform_fee: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Platform commission fee deducted",
    )


class TelemetrySeries(BaseModel):
    """Structured runtime time-series telemetry contract for ML feature derivation."""

    model_config = ConfigDict(extra="ignore")

    observed_days: Optional[int] = Field(
        None,
        ge=0,
        le=365,
        description="Observed observation depth in days",
    )
    weekly_payouts: List[WeeklyPayoutRecord] = Field(
        default_factory=list,
        description="Chronological weekly payout records",
    )
    daily_activity: List[DailyShiftRecord] = Field(
        default_factory=list,
        description="Chronological daily activity records",
    )
    active_signal_groups: Optional[List[str]] = Field(
        None,
        description="Optional explicit list of active alternative signal groups",
    )


class FinancialSignalBase(BaseModel):
    """Base fields for aggregated financial indicators (data-minimization compliant)."""

    source: SignalSource
    measurement_period_start: Optional[dt.datetime] = None
    measurement_period_end: Optional[dt.datetime] = None

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
    telemetry_series: Optional[Union[TelemetrySeries, Dict[str, Any]]] = Field(
        None,
        description="Granular time-series telemetry records (weekly payouts, daily shifts)",
    )


class FinancialSignalCreate(FinancialSignalBase):
    """Schema for ingesting aggregated signals and telemetry for an application."""

    model_config = ConfigDict(extra="allow")

    application_id: Optional[UUID] = None
    applicant_profile_id: Optional[UUID] = None


class FinancialSignalResponse(FinancialSignalBase):
    """Response schema for financial signal evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    applicant_profile_id: Optional[UUID]
    created_at: dt.datetime
