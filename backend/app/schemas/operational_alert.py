"""Pydantic schemas for OperationalAlert entity."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.operational_alert import (
    OperationalAlertSeverity,
    OperationalAlertStatus,
    OperationalAlertType,
)


class OperationalAlertBase(BaseModel):
    """Base fields representing an operational event or incident."""

    alert_type: OperationalAlertType = Field(
        ...,
        description="Type of operational event (INSUFFICIENT_DATA_REVIEW, ASSESSMENT_FAILURE, CONSENT_BLOCKED, SYSTEM_HEALTH)",
    )
    severity: OperationalAlertSeverity = Field(
        ...,
        description="Severity classification (INFO, WARNING, CRITICAL)",
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Concise human-readable incident headline",
    )
    message: str = Field(
        ...,
        description="Detailed description of operational condition (sanitized, zero PII)",
    )
    application_id: Optional[UUID] = Field(
        None,
        description="Optional associated application UUID",
    )
    assessment_id: Optional[UUID] = Field(
        None,
        description="Optional associated assessment UUID",
    )
    alert_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Sanitized non-sensitive contextual metadata",
    )


class OperationalAlertCreate(OperationalAlertBase):
    """Schema for creating a new operational alert."""

    status: OperationalAlertStatus = Field(
        default=OperationalAlertStatus.OPEN,
        description="Initial lifecycle status",
    )


class OperationalAlertUpdate(BaseModel):
    """Schema for updating operational alert status."""

    status: OperationalAlertStatus = Field(
        ...,
        description="Updated lifecycle status (OPEN, ACKNOWLEDGED, RESOLVED)",
    )


class OperationalAlertResponse(OperationalAlertBase):
    """API response model for operational alerts."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Unique alert identifier",
    )
    status: OperationalAlertStatus = Field(
        ...,
        description="Current status (OPEN, ACKNOWLEDGED, RESOLVED)",
    )
    created_at: datetime = Field(
        ...,
        description="Time the operational event was recorded",
    )
    resolved_at: Optional[datetime] = Field(
        None,
        description="Time the incident was marked resolved, if applicable",
    )
