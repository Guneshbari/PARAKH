"""Applicant profile model for gig worker details."""
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.consent import Consent
    from app.models.user import User


class ApplicantProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Applicant profile for gig workers seeking alternative credit assessment.

    Stores strictly non-sensitive profile information. Avoids contact books,
    GPS location history, or raw transaction logs.
    """

    __tablename__ = "applicant_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    gig_work_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    years_working: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 1),
        nullable=True,
    )
    average_working_days: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )
    business_or_loan_purpose: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="applicant_profile",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="applicant_profile",
        cascade="all, delete-orphan",
    )
    consents: Mapped[List["Consent"]] = relationship(
        "Consent",
        back_populates="applicant_profile",
        cascade="all, delete-orphan",
    )
