"""Assessment repository for credit evaluation outputs."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.assessment import CreditAssessment
from app.repositories.base import BaseRepository, _parse_id


class AssessmentRepository(BaseRepository[CreditAssessment]):
    """Repository handling persistence operations for CreditAssessment outputs."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize AssessmentRepository with CreditAssessment model."""
        super().__init__(CreditAssessment, db)

    def create(
        self,
        obj_in: Union[CreditAssessment, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> CreditAssessment:
        """Create a new CreditAssessment record.

        Args:
            obj_in: CreditAssessment instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            CreditAssessment: Persisted credit assessment.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[CreditAssessment]:
        """Fetch a CreditAssessment by primary key UUID.

        Args:
            id: Assessment UUID.
            db: Optional session override.

        Returns:
            Optional[CreditAssessment]: Matching assessment or None.
        """
        return super().get_by_id(id, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[CreditAssessment]:
        """Fetch all credit assessments for an application ordered by creation date descending.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[CreditAssessment]: Matching assessments.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(CreditAssessment)
            .where(CreditAssessment.application_id == parsed_id)
            .order_by(CreditAssessment.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    def get_latest(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[CreditAssessment]:
        """Fetch the most recent credit assessment for an application.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            Optional[CreditAssessment]: Latest assessment or None.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(CreditAssessment)
            .where(CreditAssessment.application_id == parsed_id)
            .order_by(CreditAssessment.created_at.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()


CreditAssessmentRepository = AssessmentRepository
