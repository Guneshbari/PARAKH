"""Review repository for human oversight and adjudication outcomes."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.review import ReviewOutcome
from app.repositories.base import BaseRepository, _parse_id


class ReviewRepository(BaseRepository[ReviewOutcome]):
    """Repository handling persistence operations for ReviewOutcome records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize ReviewRepository with ReviewOutcome model."""
        super().__init__(ReviewOutcome, db)

    def create(
        self,
        obj_in: Union[ReviewOutcome, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ReviewOutcome:
        """Create a new ReviewOutcome record.

        Args:
            obj_in: ReviewOutcome instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            ReviewOutcome: Persisted review outcome.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[ReviewOutcome]:
        """Fetch all human review outcomes for an application ordered by creation date descending.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[ReviewOutcome]: Matching review outcomes.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(ReviewOutcome)
            .where(ReviewOutcome.application_id == parsed_id)
            .order_by(ReviewOutcome.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    def get_by_reviewer(
        self,
        reviewer_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[ReviewOutcome]:
        """Fetch review outcomes conducted by a specific reviewer, ordered by creation date descending.

        Args:
            reviewer_id: User UUID of the reviewer.
            skip: Pagination offset.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[ReviewOutcome]: Review outcomes by reviewer.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(reviewer_id)
        stmt = (
            select(ReviewOutcome)
            .where(ReviewOutcome.reviewer_id == parsed_id)
            .order_by(ReviewOutcome.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())


ReviewOutcomeRepository = ReviewRepository
