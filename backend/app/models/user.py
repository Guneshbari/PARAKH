"""User model representing a PARAKH account."""
import enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.applicant import ApplicantProfile
    from app.models.review import ReviewOutcome
    from app.models.audit import AuditLog


class UserRole(str, enum.Enum):
    """Supported roles in PARAKH."""

    APPLICANT = "APPLICANT"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=50),
        nullable=False,
        default=UserRole.APPLICANT,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    applicant_profile: Mapped[Optional["ApplicantProfile"]] = relationship(
        "ApplicantProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    review_outcomes: Mapped[List["ReviewOutcome"]] = relationship(
        "ReviewOutcome",
        back_populates="reviewer",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )
