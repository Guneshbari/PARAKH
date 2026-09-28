"""Consent service managing explicit applicant data access permissions and verification."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.consent import Consent, ConsentDataSource, ConsentPreference
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.repositories.base import _parse_id
from app.repositories.consent import ConsentRepository
from app.schemas.consent import (
    ConsentCreate,
    ConsentPreferenceItem,
    ConsentPreferencesResponse,
    ConsentPreferencesUpdate,
)
from app.services.audit import AuditService
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
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize ConsentService with required repositories and audit service."""
        self.db = db
        self.consent_repo = consent_repo or ConsentRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.applicant_repo = applicant_repo or ApplicantRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)

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
            if self.audit_service:
                try:
                    data_source = getattr(consent, "data_source", None)
                    source_str = data_source.value if hasattr(data_source, "value") else str(data_source)
                    self.audit_service.record_event(
                        action=AuditAction.CONSENT_GRANTED,
                        entity_type="Consent",
                        entity_id=getattr(consent, "id", None),
                        application_id=getattr(consent, "application_id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "data_source": source_str,
                            "purpose": getattr(consent, "purpose", None),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
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
            if self.audit_service:
                try:
                    data_source = getattr(revoked, "data_source", None)
                    source_str = data_source.value if hasattr(data_source, "value") else str(data_source)
                    self.audit_service.record_event(
                        action=AuditAction.CONSENT_REVOKED,
                        entity_type="Consent",
                        entity_id=getattr(revoked, "id", None),
                        application_id=getattr(revoked, "application_id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "data_source": source_str,
                            "revoked_at": str(getattr(revoked, "revoked_at", "")),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
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

    # -------------------------------------------------------------------------
    # DPDP Applicant Consent Preferences (P2-04)
    # -------------------------------------------------------------------------

    CANONICAL_PREFERENCE_KEYS = [
        "consent_benchmark",
        "consent_realtime",
        "consent_alerts",
    ]

    PREFERENCE_KEY_ALIASES = {
        "consent_benchmark": "consent_benchmark",
        "consentbenchmark": "consent_benchmark",
        "anonymized_benchmarking": "consent_benchmark",
        "anonymized_industry_volatility_benchmarking": "consent_benchmark",
        "consent_realtime": "consent_realtime",
        "consentrealtime": "consent_realtime",
        "realtime_telemetry": "consent_realtime",
        "continuous_telemetry_refresh": "consent_realtime",
        "consent_alerts": "consent_alerts",
        "consentalerts": "consent_alerts",
        "shock_alerts": "consent_alerts",
        "volatile_shock_rebound_alerts": "consent_alerts",
    }

    def _normalize_preference_key(self, key: str) -> str:
        """Normalize a preference key using recognized aliases."""
        clean = key.strip().lower()
        if clean in self.PREFERENCE_KEY_ALIASES:
            return self.PREFERENCE_KEY_ALIASES[clean]
        return key.strip()

    def get_consent_preferences(
        self,
        user_id: Union[uuid.UUID, str],
    ) -> ConsentPreferencesResponse:
        """Fetch authoritative DPDP consent preferences for an applicant user.

        If a preference record has not yet been established, defaults to False
        (missing consent is never defaulted to granted).

        Args:
            user_id: User UUID.

        Returns:
            ConsentPreferencesResponse: Consolidated preferences and individual audit records.
        """
        parsed_user_id = _parse_id(user_id)
        records = self.consent_repo.get_preferences_by_user(parsed_user_id, db=self.db)
        record_map = {r.preference_key: r for r in records}

        items: List[ConsentPreferenceItem] = []
        latest_updated_at: Optional[datetime] = None

        flags = {
            "consent_benchmark": False,
            "consent_realtime": False,
            "consent_alerts": False,
        }

        for key in self.CANONICAL_PREFERENCE_KEYS:
            rec = record_map.get(key)
            if rec is not None:
                flags[key] = bool(rec.granted)
                if rec.updated_at:
                    if latest_updated_at is None or rec.updated_at > latest_updated_at:
                        latest_updated_at = rec.updated_at
                items.append(
                    ConsentPreferenceItem(
                        key=key,
                        granted=bool(rec.granted),
                        consented_at=rec.consented_at,
                        revoked_at=rec.revoked_at,
                        updated_at=rec.updated_at,
                    )
                )
            else:
                items.append(
                    ConsentPreferenceItem(
                        key=key,
                        granted=False,
                        consented_at=None,
                        revoked_at=None,
                        updated_at=None,
                    )
                )

        return ConsentPreferencesResponse(
            user_id=parsed_user_id,
            consent_benchmark=flags["consent_benchmark"],
            consent_realtime=flags["consent_realtime"],
            consent_alerts=flags["consent_alerts"],
            preferences=items,
            updated_at=latest_updated_at,
        )

    def update_consent_preferences(
        self,
        user_id: Union[uuid.UUID, str],
        preferences_in: Union[ConsentPreferencesUpdate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> ConsentPreferencesResponse:
        """Update and persist DPDP consent preferences for an applicant user.

        Explicitly records consent grants and revocations with audit tracking.

        Args:
            user_id: User UUID.
            preferences_in: Update payload with one or more preference fields.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ConsentPreferencesResponse: Updated authoritative preferences state.
        """
        parsed_user_id = _parse_id(user_id)
        data = _extract_dict(preferences_in)

        # Look up applicant profile if one exists for user
        profile = self.applicant_repo.get_by_user_id(parsed_user_id, db=self.db)
        profile_id = profile.id if profile else None

        # Resolve field values
        updates: Dict[str, bool] = {}
        for key, val in data.items():
            if val is not None:
                norm_key = self._normalize_preference_key(key)
                if norm_key in self.CANONICAL_PREFERENCE_KEYS:
                    updates[norm_key] = bool(val)

        try:
            for pref_key, is_granted in updates.items():
                existing = self.consent_repo.get_preference(
                    parsed_user_id, pref_key, db=self.db
                )
                prev_granted = existing.granted if existing else False

                pref = self.consent_repo.upsert_preference(
                    user_id=parsed_user_id,
                    preference_key=pref_key,
                    granted=is_granted,
                    applicant_profile_id=profile_id,
                    commit=False,
                    db=self.db,
                )

                # Record audit event on state transition or initial explicit preference creation
                if existing is None or prev_granted != is_granted:
                    if self.audit_service:
                        try:
                            action = (
                                AuditAction.CONSENT_GRANTED
                                if is_granted
                                else AuditAction.CONSENT_REVOKED
                            )
                            self.audit_service.record_event(
                                action=action,
                                entity_type="ConsentPreference",
                                entity_id=pref.id,
                                user_id=parsed_user_id,
                                outcome=AuditOutcome.SUCCESS,
                                metadata={
                                    "preference_key": pref_key,
                                    "granted": is_granted,
                                    "applicant_profile_id": str(profile_id) if profile_id else None,
                                },
                                commit=False,
                            )
                        except Exception:
                            pass

            if auto_commit:
                self.db.commit()

            return self.get_consent_preferences(parsed_user_id)
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def revoke_consent_preference(
        self,
        user_id: Union[uuid.UUID, str],
        preference_key: str,
        auto_commit: bool = True,
    ) -> ConsentPreferencesResponse:
        """Revoke a specific DPDP consent preference.

        Sets granted=False, stamps revoked_at, and records an audit event.

        Args:
            user_id: User UUID.
            preference_key: Canonical key or recognized alias.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ConsentPreferencesResponse: Updated authoritative preferences state.
        """
        norm_key = self._normalize_preference_key(preference_key)
        if norm_key not in self.CANONICAL_PREFERENCE_KEYS:
            raise ValidationError(f"Invalid consent preference key: '{preference_key}'.")

        return self.update_consent_preferences(
            user_id=user_id,
            preferences_in={norm_key: False},
            auto_commit=auto_commit,
        )

