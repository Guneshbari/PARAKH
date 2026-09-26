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


class ConsentPreferenceItem(BaseModel):
    """Detailed individual DPDP consent preference."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    granted: bool
    consented_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConsentPreferencesUpdate(BaseModel):
    """Schema for updating applicant DPDP consent preferences."""

    model_config = ConfigDict(populate_by_name=True)

    consent_benchmark: Optional[bool] = Field(
        None,
        alias="consentBenchmark",
        description="Allow anonymized rebound speeds to train local gig economy resilience baselines.",
    )
    consent_realtime: Optional[bool] = Field(
        None,
        alias="consentRealtime",
        description="Periodically update weekly inflow stability indicators as new platform payouts settle.",
    )
    consent_alerts: Optional[bool] = Field(
        None,
        alias="consentAlerts",
        description="Receive proactive notifications when 10-day recovery velocity qualifies for better credit limits.",
    )


class ConsentPreferencesResponse(BaseModel):
    """Authoritative applicant DPDP consent preferences response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: UUID
    consent_benchmark: bool = Field(
        default=False,
        description="Anonymized Industry Volatility Benchmarking",
    )
    consent_realtime: bool = Field(
        default=False,
        description="Continuous Telemetry Refresh / Real-Time Telemetry Ingestion",
    )
    consent_alerts: bool = Field(
        default=False,
        description="Volatile Shock Rebound Alerts / Automated Downside Shock Alerts",
    )
    preferences: list[ConsentPreferenceItem] = Field(
        default_factory=list,
        description="Granular preference audit records",
    )
    updated_at: Optional[datetime] = None

