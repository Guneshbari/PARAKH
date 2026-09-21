"""Audit repository for immutable audit log persistence and retrieval."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository, _parse_id


class AuditRepository(BaseRepository[AuditLog]):
    """Repository handling persistence operations for AuditLog records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize AuditRepository with AuditLog model."""
        super().__init__(AuditLog, db)

    def create(
        self,
        obj_in: Union[AuditLog, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> AuditLog:
        """Create a new AuditLog record.

        Args:
            obj_in: AuditLog instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            AuditLog: Persisted audit record.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[AuditLog]:
        """Fetch audit events related to an application, ordered by creation date descending.

        Args:
            application_id: Application UUID.
            skip: Pagination offset.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[AuditLog]: Audit records for application.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(AuditLog)
            .where(AuditLog.application_id == parsed_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def get_by_user(
        self,
        user_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[AuditLog]:
        """Fetch audit events related to a user, ordered by creation date descending.

        Args:
            user_id: User UUID.
            skip: Pagination offset.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[AuditLog]: Audit records for user.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(user_id)
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == parsed_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def list_audit_logs(
        self,
        user_id: Optional[Union[uuid.UUID, str]] = None,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[AuditLog]:
        """Fetch audit events with optional filters, ordered by creation date descending.

        Args:
            user_id: Optional user ID filter.
            application_id: Optional application ID filter.
            action: Optional action identifier filter.
            entity_type: Optional entity type filter.
            skip: Pagination offset.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[AuditLog]: Filtered audit records.
        """
        session = self._get_db(db)
        stmt = select(AuditLog)

        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == _parse_id(user_id))
        if application_id is not None:
            stmt = stmt.where(AuditLog.application_id == _parse_id(application_id))
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        return list(session.scalars(stmt).all())


AuditLogRepository = AuditRepository
