"""Document request entity capturing structured document verification requests."""
import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.review import ReviewOutcome
    from app.models.submitted_document import SubmittedDocument
    from app.models.user import User


class DocumentType(str, enum.Enum):
    """Supported document types requested for verification."""

    BANK_STATEMENT = "BANK_STATEMENT"
    INCOME_PROOF = "INCOME_PROOF"
    TRANSACTION_STATEMENT = "TRANSACTION_STATEMENT"
    BUSINESS_RECORD = "BUSINESS_RECORD"
    OTHER = "OTHER"


class AllowedFileType(str, enum.Enum):
    """Controlled allowable file formats."""

    PDF = "PDF"
    XLS = "XLS"
    XLSX = "XLSX"


class DocumentRequestStatus(str, enum.Enum):
    """Lifecycle statuses for document verification requests."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"


class DocumentRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured request for applicant verification documentation."""

    __tablename__ = "document_requests"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("review_outcomes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, native_enum=False, length=50),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    allowed_file_types: Mapped[List[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    status: Mapped[DocumentRequestStatus] = mapped_column(
        Enum(DocumentRequestStatus, native_enum=False, length=50),
        default=DocumentRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="document_requests",
    )
    review: Mapped[Optional["ReviewOutcome"]] = relationship(
        "ReviewOutcome",
        back_populates="document_requests",
    )
    requester: Mapped["User"] = relationship(
        "User",
    )
    submitted_documents: Mapped[List["SubmittedDocument"]] = relationship(
        "SubmittedDocument",
        back_populates="document_request",
        cascade="all, delete-orphan",
        order_by="desc(SubmittedDocument.created_at)",
    )
    submitted_document: Mapped[Optional["SubmittedDocument"]] = relationship(
        "SubmittedDocument",
        back_populates="document_request",
        uselist=False,
        order_by="desc(SubmittedDocument.created_at)",
        viewonly=True,
    )
