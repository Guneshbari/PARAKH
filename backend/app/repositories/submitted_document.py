"""SubmittedDocument repository for applicant document upload persistence."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.submitted_document import SubmittedDocument
from app.repositories.base import BaseRepository, _parse_id


class SubmittedDocumentRepository(BaseRepository[SubmittedDocument]):
    """Repository handling persistence operations for SubmittedDocument records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize SubmittedDocumentRepository with SubmittedDocument model."""
        super().__init__(SubmittedDocument, db)

    def create(
        self,
        obj_in: Union[SubmittedDocument, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> SubmittedDocument:
        """Create a new SubmittedDocument record."""
        return super().create(obj_in, commit=commit, db=db)

    def get_by_document_request(
        self,
        document_request_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[SubmittedDocument]:
        """Fetch submitted document for a specific document request.

        Args:
            document_request_id: DocumentRequest UUID.
            db: Optional session override.

        Returns:
            Optional[SubmittedDocument]: Submitted document if exists.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(document_request_id)
        stmt = (
            select(SubmittedDocument)
            .where(SubmittedDocument.document_request_id == parsed_id)
            .order_by(SubmittedDocument.created_at.desc())
        )
        return session.scalars(stmt).first()

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[SubmittedDocument]:
        """Fetch all submitted documents for an application.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[SubmittedDocument]: Matching submitted documents.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(SubmittedDocument)
            .where(SubmittedDocument.application_id == parsed_id)
            .order_by(SubmittedDocument.created_at.desc())
        )
        return list(session.scalars(stmt).all())
