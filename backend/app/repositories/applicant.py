"""Applicant repository for persistence and retrieval of gig worker profiles."""
import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.applicant import ApplicantProfile
from app.repositories.base import BaseRepository, _parse_id


class ApplicantRepository(BaseRepository[ApplicantProfile]):
    """Repository handling persistence operations for ApplicantProfile records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize ApplicantRepository with ApplicantProfile model."""
        super().__init__(ApplicantProfile, db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[ApplicantProfile]:
        """Fetch an ApplicantProfile by primary key UUID.

        Args:
            id: UUID or string representation.
            db: Optional session override.

        Returns:
            Optional[ApplicantProfile]: Matching profile or None.
        """
        return super().get_by_id(id, db=db)

    def get_by_user_id(
        self,
        user_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[ApplicantProfile]:
        """Fetch an ApplicantProfile associated with a specific User ID.

        Args:
            user_id: User account UUID.
            db: Optional session override.

        Returns:
            Optional[ApplicantProfile]: Associated profile or None.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(user_id)
        stmt = select(ApplicantProfile).where(ApplicantProfile.user_id == parsed_id)
        return session.scalars(stmt).first()

    def create(
        self,
        obj_in: Union[ApplicantProfile, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ApplicantProfile:
        """Create a new ApplicantProfile record.

        Args:
            obj_in: ApplicantProfile instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            ApplicantProfile: Persisted profile instance.
        """
        return super().create(obj_in, commit=commit, db=db)

    def update(
        self,
        db_obj: ApplicantProfile,
        obj_in: Union[Dict[str, Any], Any],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ApplicantProfile:
        """Update an existing ApplicantProfile record.

        Args:
            db_obj: Existing ApplicantProfile instance.
            obj_in: Dictionary or object containing updated attributes.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            ApplicantProfile: Updated profile instance.
        """
        return super().update(db_obj, obj_in, commit=commit, db=db)


ApplicantProfileRepository = ApplicantRepository
