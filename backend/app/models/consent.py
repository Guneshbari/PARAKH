"""Consent entity capturing explicit applicant permissions."""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfile
    from app.models.application import Application
    from app.models.user import User


class ConsentDataSource(str, enum.Enum):
    """Permitted external behavioral and platform data source categories."""

    PLATFORM = "PLATFORM"
    FINANCIAL_ACTIVITY = "FINANCIAL_ACTIVITY"
    UTILITY = "UTILITY"


class Consent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit applicant consent record for credit assessment.

    Supports lifecycle states including granted and revoked. Strictly avoids
    storing raw financial data.
    """

    __tablename__ = "consents"

    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    applicant_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    data_source: Mapped[ConsentDataSource] = mapped_column(
        Enum(ConsentDataSource, native_enum=False, length=50),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    granted: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    application: Mapped[Optional["Application"]] = relationship(
        "Application",
        back_populates="consents",
    )
    applicant_profile: Mapped[Optional["ApplicantProfile"]] = relationship(
        "ApplicantProfile",
        back_populates="consents",
    )


class ConsentPreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit applicant DPDP consent preferences.

    Captures persistent preferences for auxiliary features:
    - Anonymized volatility benchmarking (consent_benchmark)
    - Real-time continuous telemetry ingestion (consent_realtime)
    - Downside shock alerts (consent_alerts)

    Strictly decoupled from assessment data-source consents.
    """

    __tablename__ = "applicant_consent_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_preference_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    applicant_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    preference_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    granted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    consented_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="consent_preferences",
    )
    applicant_profile: Mapped[Optional["ApplicantProfile"]] = relationship(
        "ApplicantProfile",
    )

