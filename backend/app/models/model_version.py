"""Model version entity for assessment algorithm traceability."""
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.assessment import CreditAssessment


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Metadata record for algorithmic models producing credit assessments."""

    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    algorithm: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    credit_assessments: Mapped[List["CreditAssessment"]] = relationship(
        "CreditAssessment",
        back_populates="model_version",
    )
