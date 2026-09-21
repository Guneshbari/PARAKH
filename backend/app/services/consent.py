"""Consent service managing explicit applicant data access permissions and verification."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.consent import Consent, ConsentDataSource
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.repositories.base import _parse_id
from app.repositories.consent import ConsentRepository
from app.schemas.consent import ConsentCreate
from app.services.exceptions import (
    ConsentRequiredError,
    EntityNotFoundError,
    ValidationError,
)


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ConsentService:
    """Business service orchestrating user consent management and lifecycle states.

    Enforces data-source-specific consent verification, application/applicant
    ownership integrity, and historical revocation tracking.
    """

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

        Requires an application and validates that the applicant profile matches
        the application's ownership.

        Args:
            consent_in: Consent details.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Consent: Created consent record.

        Raises:
            ValidationError: If application_id is missing, applicant profile does not match,
                             purpose is empty, data source is invalid, or grant is not True.
            EntityNotFoundError: If specified application or applicant profile does not exist.
        """
        data = _extract_dict(consent_in)

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required to create consent.")

        # Validate existence of referenced application
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Validate applicant/profile relationship
        provided_profile_id = data.get("applicant_profile_id")
        if provided_profile_id is not None:
            if _parse_id(provided_profile_id) != _parse_id(app.applicant_profile_id):
                raise ValidationError(
                    f"ApplicantProfile id '{provided_profile_id}' does not match "
                    f"the application's applicant profile '{app.applicant_profile_id}'."
                )

        # Enforce consistency: ensure profile id matches application owner
        data["applicant_profile_id"] = app.applicant_profile_id

        # Verify applicant profile actually exists
        profile = self.applicant_repo.get_by_id(app.applicant_profile_id, db=self.db)
        if not profile:
            raise EntityNotFoundError(
                f"ApplicantProfile with id '{app.applicant_profile_id}' not found."
            )

        # Validate data source
        raw_source = data.get("data_source")
        if not raw_source:
            raise ValidationError("data_source is required.")
        if isinstance(raw_source, str):
            try:
                data["data_source"] = ConsentDataSource(raw_source)
            except ValueError:
                raise ValidationError(f"Invalid consent data source: '{raw_source}'.")

        # Validate purpose
        purpose = data.get("purpose")
        if not purpose or not str(purpose).strip():
            raise ValidationError("Consent purpose must not be empty.")

        # Consent must be explicitly granted; do not silently imply consent
        granted = data.get("granted", True)
        if granted is not True:
            raise ValidationError("Consent must be explicitly granted.")
        data["granted"] = True

        # Timestamp grant
        if not data.get("granted_at"):
            data["granted_at"] = datetime.now(timezone.utc)
        data["revoked_at"] = None

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

        Raises:
            EntityNotFoundError: If application does not exist.
        """
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")
        return self.consent_repo.get_by_application(application_id, db=self.db)

    def get_active_consents(
        self,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        applicant_profile_id: Optional[Union[uuid.UUID, str]] = None,
        data_source: Optional[Union[ConsentDataSource, str]] = None,
    ) -> List[Consent]:
        """Fetch active consents matching application, profile, and/or data source filters.

        Args:
            application_id: Optional Application UUID filter.
            applicant_profile_id: Optional ApplicantProfile UUID filter.
            data_source: Optional ConsentDataSource category filter.

        Returns:
            List[Consent]: List of active, unrevoked consents.
        """
        return self.consent_repo.get_active_consents(
            application_id=application_id,
            applicant_profile_id=applicant_profile_id,
            data_source=data_source,
            db=self.db,
        )

    def get_active_consent(
        self,
        application_id: Union[uuid.UUID, str],
        data_source: Union[ConsentDataSource, str],
    ) -> Optional[Consent]:
        """Fetch the active consent record for a specific application and data source.

        Args:
            application_id: Application UUID.
            data_source: Data category.

        Returns:
            Optional[Consent]: Active consent entity if authorized, else None.
        """
        return self.consent_repo.get_active_consent(
            application_id=application_id,
            data_source=data_source,
            db=self.db,
        )

    def has_active_consent(
        self,
        application_id: Union[uuid.UUID, str],
        data_source: Union[ConsentDataSource, str],
        applicant_profile_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> bool:
        """Check whether an application has valid, active consent for a specific data source.

        Active consent requires:
        - granted == True
        - revoked_at IS NULL
        - Strictly scoped to the specified application_id.

        Args:
            application_id: Application UUID.
            data_source: ConsentDataSource category.
            applicant_profile_id: Optional ApplicantProfile UUID to verify ownership.

        Returns:
            bool: True if authorized, False otherwise.
        """
        if applicant_profile_id is not None:
            app = self.app_repo.get_by_id(application_id, db=self.db)
            if not app or _parse_id(app.applicant_profile_id) != _parse_id(applicant_profile_id):
                return False

        consent = self.get_active_consent(application_id, data_source)
        return consent is not None

    def require_active_consent(
        self,
        application_id: Union[uuid.UUID, str],
        data_source: Union[ConsentDataSource, str],
        applicant_profile_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Consent:
        """Require and return active consent for an application and data source.

        Args:
            application_id: Application UUID.
            data_source: ConsentDataSource category.
            applicant_profile_id: Optional ApplicantProfile UUID to verify ownership.

        Returns:
            Consent: The active authorization record.

        Raises:
            ValidationError: If ownership verification fails.
            ConsentRequiredError: If active consent is missing or has been revoked.
        """
        if applicant_profile_id is not None:
            app = self.app_repo.get_by_id(application_id, db=self.db)
            if not app or _parse_id(app.applicant_profile_id) != _parse_id(applicant_profile_id):
                raise ValidationError(
                    f"Application '{application_id}' does not belong to profile '{applicant_profile_id}'."
                )

        consent = self.get_active_consent(application_id, data_source)
        if not consent:
            source_name = (
                data_source.value if hasattr(data_source, "value") else str(data_source)
            )
            raise ConsentRequiredError(
                f"Active consent required for data source '{source_name}' on application '{application_id}'."
            )
        return consent

    def revoke_consent(
        self,
        consent_id: Union[uuid.UUID, str],
        revoked_at: Optional[datetime] = None,
        auto_commit: bool = True,
    ) -> Consent:
        """Revoke a previously granted consent record.

        Immediately changes effective state so subsequent authorization checks fail.
        Historical record is preserved with revocation timestamp.

        Args:
            consent_id: Consent primary key UUID.
            revoked_at: Optional timestamp override.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Consent: Updated consent entity with revoked_at timestamp.

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

    def revoke_application_consent(
        self,
        application_id: Union[uuid.UUID, str],
        data_source: Union[ConsentDataSource, str],
        revoked_at: Optional[datetime] = None,
        auto_commit: bool = True,
    ) -> Optional[Consent]:
        """Revoke the currently active consent for an application and data source.

        Args:
            application_id: Application UUID.
            data_source: Data category.
            revoked_at: Optional timestamp override.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Optional[Consent]: Revoked consent entity or None if no active consent was found.
        """
        active = self.get_active_consent(application_id, data_source)
        if not active:
            return None
        return self.revoke_consent(active.id, revoked_at=revoked_at, auto_commit=auto_commit)
