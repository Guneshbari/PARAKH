"""Consent repository for applicant explicit permission records."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.consent import Consent
from app.repositories.base import BaseRepository, _parse_id


class ConsentRepository(BaseRepository[Consent]):
    """Repository handling persistence operations for Consent records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize ConsentRepository with Consent model."""
        super().__init__(Consent, db)

    def create(
        self,
        obj_in: Union[Consent, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Consent:
        """Create a new Consent record.

        Args:
            obj_in: Consent instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            Consent: Persisted consent record.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> List[Consent]:
        """Fetch all consents linked to an application, ordered by granted_at descending.

        Args:
            application_id: Application UUID.
            db: Optional session override.

        Returns:
            List[Consent]: Matching consents.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(application_id)
        stmt = (
            select(Consent)
            .where(Consent.application_id == parsed_id)
            .order_by(Consent.granted_at.desc())
        )
        return list(session.scalars(stmt).all())

    def get_active_consents(
        self,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        applicant_profile_id: Optional[Union[uuid.UUID, str]] = None,
        db: Optional[Session] = None,
    ) -> List[Consent]:
        """Fetch active (granted=True and revoked_at is None) consents.

        Args:
            application_id: Optional Application UUID filter.
            applicant_profile_id: Optional ApplicantProfile UUID filter.
            db: Optional session override.

        Returns:
            List[Consent]: Active consents matching criteria.
        """
        session = self._get_db(db)
        stmt = select(Consent).where(
            Consent.granted.is_(True),
            Consent.revoked_at.is_(None),
        )
        if application_id is not None:
            stmt = stmt.where(Consent.application_id == _parse_id(application_id))
        if applicant_profile_id is not None:
            stmt = stmt.where(
                Consent.applicant_profile_id == _parse_id(applicant_profile_id)
            )

        stmt = stmt.order_by(Consent.granted_at.desc())
        return list(session.scalars(stmt).all())

    def revoke(
        self,
        consent_or_id: Union[Consent, uuid.UUID, str],
        revoked_at: Optional[datetime] = None,
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[Consent]:
        """Revoke a consent by setting granted=False and stamping revoked_at.

        Args:
            consent_or_id: Consent instance or Consent UUID.
            revoked_at: Optional timestamp of revocation (defaults to UTC now).
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            Optional[Consent]: Updated consent instance or None if not found.
        """
        session = self._get_db(db)
        if isinstance(consent_or_id, Consent):
            consent = consent_or_id
        else:
            consent = self.get_by_id(consent_or_id, db=session)

        if consent is None:
            return None

        consent.granted = False
        consent.revoked_at = revoked_at or datetime.now(timezone.utc)
        session.add(consent)
        if commit:
            session.commit()
            session.refresh(consent)
        else:
            session.flush()
        return consent
