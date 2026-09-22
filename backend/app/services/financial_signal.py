"""Financial signal service for derived and aggregated alternative credit indicators."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.consent import ConsentDataSource
from app.models.financial_signal import FinancialSignal, SignalSource
from app.repositories.application import ApplicationRepository
from app.repositories.financial_signal import FinancialSignalRepository
from app.schemas.financial_signal import FinancialSignalCreate
from app.services.audit import AuditService
from app.services.consent import ConsentService
from app.services.exceptions import EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


# Prohibited privacy-invasive data attributes under the PARAKH privacy framework
PROHIBITED_FIELDS = {
    "bank_account_number",
    "bank_credentials",
    "banking_login_credentials",
    "raw_transactions",
    "raw_bank_statements",
    "raw_upi_transactions",
    "raw_upi_logs",
    "upi_vpa",
    "merchant_name",
    "merchant_description",
    "merchant_details",
    "gps_coordinates",
    "location_history",
    "contact_list",
    "contacts",
    "password",
    "password_hash",
}

# Mapping between SignalSource and ConsentDataSource
SIGNAL_TO_CONSENT_SOURCE = {
    SignalSource.PLATFORM: ConsentDataSource.PLATFORM,
    SignalSource.FINANCIAL_ACTIVITY: ConsentDataSource.FINANCIAL_ACTIVITY,
    SignalSource.UTILITY: ConsentDataSource.UTILITY,
}


class FinancialSignalService:
    """Business service managing aggregated and derived financial metrics.

    Enforces data minimization and privacy boundaries. Prohibits storage of
    raw transactions, credentials, or location tracking.
    """

    def __init__(
        self,
        db: Session,
        signal_repo: Optional[FinancialSignalRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
        consent_service: Optional[ConsentService] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize FinancialSignalService with required repositories and audit service."""
        self.db = db
        self.signal_repo = signal_repo or FinancialSignalRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.consent_service = consent_service
        self.audit_service = audit_service or AuditService(db=db)

    def create_signal(
        self,
        signal_in: Union[FinancialSignalCreate, Dict[str, Any]],
        enforce_consent: bool = False,
        auto_commit: bool = True,
    ) -> FinancialSignal:
        """Persist aggregated behavioral/financial metrics for an application.

        Enforces privacy data-minimization rules by ensuring no raw transactional,
        location, or contact data is stored. Optionally verifies active applicant consent.

        Args:
            signal_in: Aggregated signal payload.
            enforce_consent: Whether to verify active applicant consent before saving.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            FinancialSignal: Created signal entity.

        Raises:
            ValidationError: If application_id is missing or prohibited raw fields are detected.
            EntityNotFoundError: If application does not exist.
            ConsentRequiredError: If enforce_consent is True and active consent is missing or revoked.
        """
        data = _extract_dict(signal_in)

        # Enforce strict data-minimization boundary
        violations = PROHIBITED_FIELDS.intersection(data.keys())
        if violations:
            raise ValidationError(
                f"Prohibited privacy-invasive raw data fields rejected: {', '.join(sorted(violations))}."
            )

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required to create a financial signal.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Optional consent verification
        if enforce_consent and self.consent_service is not None:
            source = data.get("source")
            if isinstance(source, str):
                source = SignalSource(source)
            consent_source = SIGNAL_TO_CONSENT_SOURCE.get(source)
            if consent_source is not None:
                self.consent_service.require_active_consent(application_id, consent_source)

        try:
            signal = self.signal_repo.create(data, commit=False, db=self.db)
            if self.audit_service:
                try:
                    source = getattr(signal, "source", None)
                    source_str = source.value if hasattr(source, "value") else str(source)
                    self.audit_service.record_event(
                        action=AuditAction.FINANCIAL_SIGNAL_CREATED,
                        entity_type="FinancialSignal",
                        entity_id=getattr(signal, "id", None),
                        application_id=getattr(signal, "application_id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "source": source_str,
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(signal)
            return signal
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def create_signal_with_consent(
        self,
        signal_in: Union[FinancialSignalCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> FinancialSignal:
        """Convenience method to persist a financial signal with mandatory active consent check.

        Args:
            signal_in: Aggregated signal payload.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            FinancialSignal: Created signal entity.
        """
        if self.consent_service is None:
            self.consent_service = ConsentService(db=self.db, app_repo=self.app_repo)
        return self.create_signal(
            signal_in=signal_in,
            enforce_consent=True,
            auto_commit=auto_commit,
        )

    def get_application_signals(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> List[FinancialSignal]:
        """Fetch all signals recorded for an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            List[FinancialSignal]: Matching signals in reverse chronological order.
        """
        return self.signal_repo.get_by_application(application_id, db=self.db)

    def get_latest_signal(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> Optional[FinancialSignal]:
        """Fetch the most recently generated signal for an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            Optional[FinancialSignal]: Most recent signal or None.
        """
        return self.signal_repo.get_latest(application_id, db=self.db)
