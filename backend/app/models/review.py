"""Review outcome entity capturing human evaluation of assessments."""
import enum
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class ReviewOutcomeType(str, enum.Enum):
    """Supported human review decisions."""

    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"
    ADDITIONAL_INFORMATION_REQUIRED = "ADDITIONAL_INFORMATION_REQUIRED"


class ReviewOutcome(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Human oversight record for decision support."""

    __tablename__ = "review_outcomes"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    outcome: Mapped[ReviewOutcomeType] = mapped_column(
        Enum(ReviewOutcomeType, native_enum=False, length=50),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="review_outcomes",
    )
    reviewer: Mapped["User"] = relationship(
        "User",
        back_populates="review_outcomes",
    )
