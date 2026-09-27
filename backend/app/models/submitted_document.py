"""Submitted document entity capturing applicant file uploads for document requests."""
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.document_request import DocumentRequest
    from app.models.user import User


class SubmittedDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Applicant submitted document associated with a document request."""

    __tablename__ = "submitted_documents"

    application_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="submitted_documents",
    )
    document_request: Mapped["DocumentRequest"] = relationship(
        "DocumentRequest",
        back_populates="submitted_document",
    )
    uploader: Mapped["User"] = relationship(
        "User",
    )

    @property
    def storage_path(self) -> str:
        """Canonical alias for file_path."""
        return self.file_path
