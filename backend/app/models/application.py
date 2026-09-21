"""Application model representing credit assessment requests."""
import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfile
    from app.models.assessment import CreditAssessment
    from app.models.audit import AuditLog
    from app.models.consent import Consent
    from app.models.financial_signal import FinancialSignal
    from app.models.review import ReviewOutcome


class ApplicationStatus(str, enum.Enum):
    """Assessment pipeline statuses for a decision-support application."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ASSESSED = "ASSESSED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    COMPLETED = "COMPLETED"


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Credit assessment application submitted by an applicant."""

    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("requested_loan_amount > 0", name="check_positive_loan_amount"),
    )

    applicant_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applicant_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_loan_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    loan_purpose: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    preferred_repayment_period: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=50),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Relationships
    applicant_profile: Mapped["ApplicantProfile"] = relationship(
        "ApplicantProfile",
        back_populates="applications",
    )
    consents: Mapped[List["Consent"]] = relationship(
        "Consent",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    financial_signals: Mapped[List["FinancialSignal"]] = relationship(
        "FinancialSignal",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    credit_assessments: Mapped[List["CreditAssessment"]] = relationship(
        "CreditAssessment",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    review_outcomes: Mapped[List["ReviewOutcome"]] = relationship(
        "ReviewOutcome",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="application",
    )
