"""Consent service managing explicit applicant data access permissions."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.consent import Consent
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.repositories.consent import ConsentRepository
from app.schemas.consent import ConsentCreate
from app.services.exceptions import EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ConsentService:
    """Business service orchestrating user consent management and lifecycle states."""

    def __init__(
        self,
        db: Session,
        consent_repo: Optional[ConsentRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
        applicant_repo: Optional[ApplicantRepository] = None,
    ) -> None:
        """Initialize ConsentService with required repositories."""
        self.db = db
        self.consent_repo = consent_repo or ConsentRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.applicant_repo = applicant_repo or ApplicantRepository(db=db)

    def create_consent(
        self,
        consent_in: Union[ConsentCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> Consent:
        """Record explicit applicant consent for a permitted external data category.

        Args:
            consent_in: Consent details.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Consent: Created consent record.

        Raises:
            ValidationError: If neither application_id nor applicant_profile_id is provided, or purpose is missing.
            EntityNotFoundError: If specified application or applicant profile does not exist.
        """
        data = _extract_dict(consent_in)

        application_id = data.get("application_id")
        applicant_profile_id = data.get("applicant_profile_id")

        if not application_id and not applicant_profile_id:
            raise ValidationError(
                "Either application_id or applicant_profile_id must be provided for consent."
            )

        purpose = data.get("purpose")
        if not purpose or not str(purpose).strip():
            raise ValidationError("Consent purpose must not be empty.")

        # Validate existence of referenced application
        if application_id:
            app = self.app_repo.get_by_id(application_id, db=self.db)
            if not app:
                raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Validate existence of referenced applicant profile
        if applicant_profile_id:
            profile = self.applicant_repo.get_by_id(applicant_profile_id, db=self.db)
            if not profile:
                raise EntityNotFoundError(
                    f"ApplicantProfile with id '{applicant_profile_id}' not found."
                )

        try:
            consent = self.consent_repo.create(data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(consent)
            return consent
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_application_consents(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> List[Consent]:
        """Fetch all consents granted for an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            List[Consent]: List of consents for application.
        """
        return self.consent_repo.get_by_application(application_id, db=self.db)

    def get_active_consents(
        self,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        applicant_profile_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> List[Consent]:
        """Fetch active consents matching application and/or profile filters.

        Args:
            application_id: Optional Application UUID filter.
            applicant_profile_id: Optional ApplicantProfile UUID filter.

        Returns:
            List[Consent]: List of active, unrevoked consents.
        """
        return self.consent_repo.get_active_consents(
            application_id=application_id,
            applicant_profile_id=applicant_profile_id,
            db=self.db,
        )

    def revoke_consent(
        self,
        consent_id: Union[uuid.UUID, str],
        revoked_at: Optional[datetime] = None,
        auto_commit: bool = True,
    ) -> Consent:
        """Revoke a previously granted consent record.

        Args:
            consent_id: Consent primary key UUID.
            revoked_at: Optional timestamp override.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Consent: Updated consent entity.

        Raises:
            EntityNotFoundError: If consent does not exist.
        """
        existing = self.consent_repo.get_by_id(consent_id, db=self.db)
        if not existing:
            raise EntityNotFoundError(f"Consent with id '{consent_id}' not found.")

        try:
            revoked = self.consent_repo.revoke(
                existing, revoked_at=revoked_at, commit=False, db=self.db
            )
            if auto_commit:
                self.db.commit()
                self.db.refresh(revoked)
            return revoked
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise
