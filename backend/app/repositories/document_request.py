"""DocumentRequest repository for document verification workflows."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.document_request import DocumentRequest, DocumentRequestStatus
from app.repositories.base import BaseRepository, _parse_id


class DocumentRequestRepository(BaseRepository[DocumentRequest]):
    """Repository handling persistence operations for DocumentRequest records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize DocumentRequestRepository with DocumentRequest model."""
        super().__init__(DocumentRequest, db)

    def create(
        self,
        obj_in: Union[DocumentRequest, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> DocumentRequest:
        """Create a new DocumentRequest record.

        Args:
            obj_in: DocumentRequest instance or attribute dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            DocumentRequest: Persisted document request entity.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[DocumentRequest]:
        """Fetch all document requests for an application ordered by creation date descending.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[DocumentRequest]: Matching document requests.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(DocumentRequest)
            .where(DocumentRequest.application_id == parsed_id)
            .order_by(DocumentRequest.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    def get_by_review(
        self,
        review_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[DocumentRequest]:
        """Fetch document requests associated with a specific review outcome.

        Args:
            review_id: ReviewOutcome UUID.
            db: Optional session override.

        Returns:
            List[DocumentRequest]: Associated document requests.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(review_id)
        stmt = (
            select(DocumentRequest)
            .where(DocumentRequest.review_id == parsed_id)
            .order_by(DocumentRequest.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    def has_pending_document_requests(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> bool:
        """Determine whether an application has unresolved evidence requests.

        Treats PENDING and SUBMITTED as unresolved.
        Treats ACCEPTED as resolved.
        Treats REJECTED as unresolved unless an ACCEPTED request exists for the same document_type.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            bool: True if application has unresolved requests, False otherwise.
        """
        requests = self.get_by_application(application_id, db=db)
        if not requests:
            return False

        # Any request currently PENDING or SUBMITTED is unresolved
        for r in requests:
            if r.status in (DocumentRequestStatus.PENDING, DocumentRequestStatus.SUBMITTED):
                return True

        # Check if any REJECTED request lacks an ACCEPTED replacement
        accepted_types = {r.document_type for r in requests if r.status == DocumentRequestStatus.ACCEPTED}
        for r in requests:
            if r.status == DocumentRequestStatus.REJECTED:
                if r.document_type not in accepted_types:
                    return True

        return False
