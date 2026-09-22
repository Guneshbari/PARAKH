"""Application repository for credit assessment requests."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus
from app.repositories.base import BaseRepository, _parse_id


class ApplicationRepository(BaseRepository[Application]):
    """Repository handling persistence operations for Application requests."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize ApplicationRepository with Application model."""
        super().__init__(Application, db)

    def create(
        self,
        obj_in: Union[Application, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Application:
        """Create a new Application record.

        Args:
            obj_in: Application instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            Application: Persisted application instance.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[Application]:
        """Fetch an Application by primary key UUID.

        Args:
            id: Application UUID or string representation.
            db: Optional session override.

        Returns:
            Optional[Application]: Matching application or None.
        """
        return super().get_by_id(id, db=db)

    def list_by_applicant(
        self,
        applicant_profile_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[Application]:
        """List applications associated with an applicant profile, ordered by creation date descending.

        Args:
            applicant_profile_id: ApplicantProfile UUID.
            skip: Offset count.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[Application]: Matching applications.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(applicant_profile_id)
        stmt = (
            select(Application)
            .where(Application.applicant_profile_id == parsed_id)
            .order_by(Application.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(session.scalars(stmt).all())

    def update(
        self,
        db_obj: Application,
        obj_in: Union[Dict[str, Any], Any],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Application:
        """Update fields on an existing Application record.

        Args:
            db_obj: Existing Application instance.
            obj_in: Dictionary or model of updated attributes.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            Application: Updated application instance.
        """
        return super().update(db_obj, obj_in, commit=commit, db=db)

    def update_status(
        self,
        application_or_id: Union[Application, uuid.UUID, str],
        status: Union[ApplicationStatus, str],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[Application]:
        """Update the status of an Application.

        Args:
            application_or_id: Application instance or application UUID.
            status: New ApplicationStatus enum value or string name.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            Optional[Application]: Updated application or None if not found.
        """
        session = self._get_db(db)
        if isinstance(application_or_id, Application):
            app_obj = application_or_id
        else:
            app_obj = self.get_by_id(application_or_id, db=session)

        if app_obj is None:
            return None

        if isinstance(status, str):
            status = ApplicationStatus(status)

        app_obj.status = status
        session.add(app_obj)
        if commit:
            session.commit()
            session.refresh(app_obj)
        else:
            session.flush()
        return app_obj
