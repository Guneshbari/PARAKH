"""Financial signal repository for aggregated alternative credit metrics."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.financial_signal import FinancialSignal
from app.repositories.base import BaseRepository, _parse_id


class FinancialSignalRepository(BaseRepository[FinancialSignal]):
    """Repository handling persistence operations for FinancialSignal records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize FinancialSignalRepository with FinancialSignal model."""
        super().__init__(FinancialSignal, db)

    def create(
        self,
        obj_in: Union[FinancialSignal, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> FinancialSignal:
        """Create a new FinancialSignal record.

        Args:
            obj_in: FinancialSignal instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            FinancialSignal: Persisted financial signal.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[FinancialSignal]:
        """Fetch all financial signals for an application ordered by creation date descending.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[FinancialSignal]: Matching signals.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(FinancialSignal)
            .where(FinancialSignal.application_id == parsed_id)
            .order_by(FinancialSignal.created_at.desc())
        )
        return list(session.scalars(stmt).all())

    def get_latest(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[FinancialSignal]:
        """Fetch the most recent financial signal for an application.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            Optional[FinancialSignal]: Latest signal or None.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(FinancialSignal)
            .where(FinancialSignal.application_id == parsed_id)
            .order_by(FinancialSignal.created_at.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()
