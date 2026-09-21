"""Financial signal service for derived and aggregated alternative credit indicators."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.financial_signal import FinancialSignal
from app.repositories.application import ApplicationRepository
from app.repositories.financial_signal import FinancialSignalRepository
from app.schemas.financial_signal import FinancialSignalCreate
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
    "raw_transactions",
    "raw_upi_logs",
    "upi_vpa",
    "merchant_name",
    "merchant_description",
    "gps_coordinates",
    "location_history",
    "contact_list",
}


class FinancialSignalService:
    """Business service managing aggregated and derived financial metrics."""

    def __init__(
        self,
        db: Session,
        signal_repo: Optional[FinancialSignalRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
    ) -> None:
        """Initialize FinancialSignalService with required repositories."""
        self.db = db
        self.signal_repo = signal_repo or FinancialSignalRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)

    def create_signal(
        self,
        signal_in: Union[FinancialSignalCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> FinancialSignal:
        """Persist aggregated behavioral/financial metrics for an application.

        Enforces privacy data-minimization rules by ensuring no raw transactional,
        location, or contact data is stored.

        Args:
            signal_in: Aggregated signal payload.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            FinancialSignal: Created signal entity.

        Raises:
            ValidationError: If application_id is missing or prohibited raw fields are detected.
            EntityNotFoundError: If application does not exist.
        """
        data = _extract_dict(signal_in)

        # Enforce strict data-minimization boundary
        violations = PROHIBITED_FIELDS.intersection(data.keys())
        if violations:
            raise ValidationError(
                f"Prohibited privacy-invasive raw data fields rejected: {', '.join(violations)}."
            )

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required to create a financial signal.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        try:
            signal = self.signal_repo.create(data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(signal)
            return signal
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

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
