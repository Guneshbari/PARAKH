"""Operational alert model for system incidents and governance monitoring."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.assessment import CreditAssessment


class OperationalAlertType(str, enum.Enum):
    """Categorical type of operational alert."""

    INSUFFICIENT_DATA_REVIEW = "INSUFFICIENT_DATA_REVIEW"
    ASSESSMENT_FAILURE = "ASSESSMENT_FAILURE"
    CONSENT_BLOCKED = "CONSENT_BLOCKED"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"


class OperationalAlertSeverity(str, enum.Enum):
    """Severity classification for operational events."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class OperationalAlertStatus(str, enum.Enum):
    """Lifecycle status of an operational alert."""

    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class OperationalAlert(Base, UUIDPrimaryKeyMixin):
    """Persistent operational alert tracking system events, pipeline failures, and sufficiency flags.

    Operational alerts indicate process or system level conditions requiring human review
    or awareness, completely decoupled from predictive credit risk outcomes.
    """

    __tablename__ = "operational_alerts"

    alert_type: Mapped[OperationalAlertType] = mapped_column(
        Enum(OperationalAlertType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    severity: Mapped[OperationalAlertSeverity] = mapped_column(
        Enum(OperationalAlertSeverity, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[OperationalAlertStatus] = mapped_column(
        Enum(OperationalAlertStatus, native_enum=False, length=20),
        default=OperationalAlertStatus.OPEN,
        nullable=False,
        index=True,
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("credit_assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alert_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    application: Mapped[Optional["Application"]] = relationship(
        "Application",
        back_populates="operational_alerts",
    )
    assessment: Mapped[Optional["CreditAssessment"]] = relationship(
        "CreditAssessment",
    )
