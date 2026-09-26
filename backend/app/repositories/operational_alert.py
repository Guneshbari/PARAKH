"""Operational alert repository for persistent system incident records."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.operational_alert import (
    OperationalAlert,
    OperationalAlertStatus,
    OperationalAlertType,
)
from app.repositories.base import BaseRepository, _parse_id


class OperationalAlertRepository(BaseRepository[OperationalAlert]):
    """Repository handling persistence operations for OperationalAlert records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize OperationalAlertRepository with OperationalAlert model."""
        super().__init__(OperationalAlert, db)

    def create(
        self,
        obj_in: Union[OperationalAlert, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> OperationalAlert:
        """Create a new OperationalAlert record."""
        return super().create(obj_in, commit=commit, db=db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[OperationalAlert]:
        """Fetch an OperationalAlert by primary key UUID."""
        return super().get_by_id(id, db=db)

    def list_alerts(
        self,
        status: Optional[OperationalAlertStatus] = None,
        limit: int = 50,
        skip: int = 0,
        db: Optional[Session] = None,
    ) -> List[OperationalAlert]:
        """List operational alerts ordered by creation date descending with optional status filter."""
        s = self._get_db(db)
        stmt = select(OperationalAlert)
        if status is not None:
            stmt = stmt.where(OperationalAlert.status == status)
        stmt = stmt.order_by(OperationalAlert.created_at.desc()).offset(skip).limit(limit)
        return list(s.scalars(stmt).all())

    def find_open_by_type_and_app(
        self,
        alert_type: OperationalAlertType,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[OperationalAlert]:
        """Find an existing OPEN or ACKNOWLEDGED alert for a given application and alert type (for deduplication)."""
        s = self._get_db(db)
        app_uuid = _parse_id(application_id)
        stmt = (
            select(OperationalAlert)
            .where(
                OperationalAlert.alert_type == alert_type,
                OperationalAlert.application_id == app_uuid,
                OperationalAlert.status.in_([OperationalAlertStatus.OPEN, OperationalAlertStatus.ACKNOWLEDGED]),
            )
            .order_by(OperationalAlert.created_at.desc())
        )
        return s.scalars(stmt).first()

    def update_status(
        self,
        id: Union[uuid.UUID, str],
        status: OperationalAlertStatus,
        resolved_at: Optional[datetime] = None,
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[OperationalAlert]:
        """Update lifecycle status of an operational alert."""
        s = self._get_db(db)
        alert = self.get_by_id(id, db=s)
        if not alert:
            return None
        alert.status = status
        if status == OperationalAlertStatus.RESOLVED:
            alert.resolved_at = resolved_at or datetime.now(timezone.utc)
        elif status == OperationalAlertStatus.OPEN:
            alert.resolved_at = None
        if commit:
            s.commit()
            s.refresh(alert)
        return alert
