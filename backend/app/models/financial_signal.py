"""Financial signal entity storing derived, aggregated metrics."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfile
    from app.models.application import Application


class SignalSource(str, enum.Enum):
    """Taxonomy of signal sources."""

    PLATFORM = "PLATFORM"
    FINANCIAL_ACTIVITY = "FINANCIAL_ACTIVITY"
    UTILITY = "UTILITY"
    DERIVED = "DERIVED"


class FinancialSignal(Base, UUIDPrimaryKeyMixin):
    """Aggregated and derived financial information for assessment.

    Follows strict data minimization principles: stores derived indicators and
    summary metrics without raw transaction descriptions, merchant names,
    contacts, or bank credentials.
    """

    __tablename__ = "financial_signals"
    __table_args__ = (
        CheckConstraint(
            "average_income IS NULL OR average_income >= 0",
            name="check_positive_avg_income",
        ),
        CheckConstraint(
            "median_income IS NULL OR median_income >= 0",
            name="check_positive_median_income",
        ),
        CheckConstraint(
            "existing_obligation IS NULL OR existing_obligation >= 0",
            name="check_positive_existing_obligation",
        ),
        CheckConstraint(
            "cashflow_buffer IS NULL OR cashflow_buffer >= 0",
            name="check_positive_cashflow_buffer",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source: Mapped[SignalSource] = mapped_column(
        Enum(SignalSource, native_enum=False, length=50),
        nullable=False,
        index=True,
    )

    # Measurement period
    measurement_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    measurement_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Aggregated Financial Metrics (Fixed precision numeric)
    average_income: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    median_income: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    income_volatility: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4),
        nullable=True,
    )
    income_trend: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    active_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    payment_regularity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    cashflow_buffer: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    existing_obligation: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    platform_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    repayment_reliability: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    # Structured metadata for extensible derived features
    signal_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="financial_signals",
    )
    applicant_profile: Mapped[Optional["ApplicantProfile"]] = relationship(
        "ApplicantProfile",
    )
