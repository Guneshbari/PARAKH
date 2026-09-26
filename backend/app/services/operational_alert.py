"""Operational alert business service managing system incident lifecycle and alerts."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.operational_alert import (
    OperationalAlert,
    OperationalAlertSeverity,
    OperationalAlertStatus,
    OperationalAlertType,
)
from app.repositories.operational_alert import OperationalAlertRepository
from app.schemas.operational_alert import OperationalAlertCreate
from app.services.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__)

PROHIBITED_METADATA_KEYS = {
    "password",
    "secret",
    "token",
    "pan",
    "aadhaar",
    "ssn",
    "bank_account",
    "account_number",
    "gps",
    "coordinates",
    "raw_transactions",
    "gender",
    "religion",
    "caste",
}


def sanitize_alert_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Sanitize metadata to guarantee zero PII or prohibited sensitive fields are stored."""
    if not metadata:
        return None
    sanitized: Dict[str, Any] = {}
    for k, v in metadata.items():
        if k.lower() in PROHIBITED_METADATA_KEYS:
            continue
        if isinstance(v, dict):
            sanitized[k] = sanitize_alert_metadata(v)
        else:
            sanitized[k] = v
    return sanitized


class OperationalAlertService:
    """Service orchestrating operational alerts, deduplication, and status transitions."""

    def __init__(
        self,
        db: Session,
        alert_repo: Optional[OperationalAlertRepository] = None,
    ) -> None:
        """Initialize OperationalAlertService with database session and repository."""
        self.db = db
        self.alert_repo = alert_repo or OperationalAlertRepository(db=db)

    def create_alert(
        self,
        alert_in: OperationalAlertCreate,
        deduplicate: bool = True,
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Create or update an operational alert with automatic deduplication.

        If deduplicate is True and an active (OPEN or ACKNOWLEDGED) alert exists for the same
        application_id and alert_type, the existing alert is updated instead of creating a duplicate.
        """
        clean_metadata = sanitize_alert_metadata(alert_in.alert_metadata)

        if deduplicate and alert_in.application_id:
            existing = self.alert_repo.find_open_by_type_and_app(
                alert_type=alert_in.alert_type,
                application_id=alert_in.application_id,
                db=self.db,
            )
            if existing:
                existing.title = alert_in.title
                existing.message = alert_in.message
                existing.severity = alert_in.severity
                if alert_in.assessment_id:
                    existing.assessment_id = alert_in.assessment_id
                if clean_metadata:
                    existing.alert_metadata = clean_metadata
                existing.created_at = datetime.now(timezone.utc)
                if auto_commit:
                    self.db.commit()
                    self.db.refresh(existing)
                logger.info("Updated existing operational alert '%s' for app '%s'", existing.id, alert_in.application_id)
                return existing

        alert = OperationalAlert(
            alert_type=alert_in.alert_type,
            severity=alert_in.severity,
            title=alert_in.title,
            message=alert_in.message,
            status=alert_in.status,
            application_id=alert_in.application_id,
            assessment_id=alert_in.assessment_id,
            alert_metadata=clean_metadata,
        )
        created = self.alert_repo.create(alert, commit=auto_commit, db=self.db)
        logger.info("Created new operational alert '%s' (%s - %s)", created.id, created.alert_type, created.severity)
        return created

    def get_alert(self, alert_id: Union[uuid.UUID, str]) -> OperationalAlert:
        """Retrieve an operational alert by ID or raise EntityNotFoundError."""
        alert = self.alert_repo.get_by_id(alert_id, db=self.db)
        if not alert:
            raise EntityNotFoundError(f"OperationalAlert with id '{alert_id}' not found.")
        return alert

    def list_alerts(
        self,
        status: Optional[OperationalAlertStatus] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> List[OperationalAlert]:
        """Fetch operational alerts ordered by created_at descending."""
        return self.alert_repo.list_alerts(
            status=status,
            limit=limit,
            skip=skip,
            db=self.db,
        )

    def acknowledge_alert(
        self,
        alert_id: Union[uuid.UUID, str],
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Mark an open alert as acknowledged."""
        alert = self.get_alert(alert_id)
        if alert.status == OperationalAlertStatus.OPEN:
            alert.status = OperationalAlertStatus.ACKNOWLEDGED
            if auto_commit:
                self.db.commit()
                self.db.refresh(alert)
        return alert

    def resolve_alert(
        self,
        alert_id: Union[uuid.UUID, str],
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Mark an alert as resolved and record resolved_at timestamp."""
        alert = self.get_alert(alert_id)
        alert.status = OperationalAlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        if auto_commit:
            self.db.commit()
            self.db.refresh(alert)
        return alert

    def create_insufficient_data_alert(
        self,
        application_id: uuid.UUID,
        assessment_id: Optional[uuid.UUID] = None,
        missing_reasons: Optional[List[str]] = None,
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Helper to create an alert when refuse-to-score is triggered due to insufficient data."""
        reasons_text = f" Reasons: {', '.join(missing_reasons)}." if missing_reasons else ""
        schema = OperationalAlertCreate(
            alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
            severity=OperationalAlertSeverity.WARNING,
            title="Insufficient Data: Manual Review Required",
            message=(
                f"Application '{application_id}' lacked minimum required telemetry evidence "
                f"to perform automated ML risk assessment.{reasons_text} Application diverted to manual review."
            ),
            application_id=application_id,
            assessment_id=assessment_id,
            alert_metadata={"missing_reasons": missing_reasons} if missing_reasons else None,
        )
        return self.create_alert(schema, deduplicate=True, auto_commit=auto_commit)

    def create_consent_blocked_alert(
        self,
        application_id: uuid.UUID,
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Helper to create an alert when assessment evaluation is blocked by consent revocation or absence."""
        schema = OperationalAlertCreate(
            alert_type=OperationalAlertType.CONSENT_BLOCKED,
            severity=OperationalAlertSeverity.WARNING,
            title="Assessment Blocked: Active Consent Required",
            message=(
                f"Automated evaluation for application '{application_id}' was prevented because active "
                f"applicant DPDP consent is missing or revoked."
            ),
            application_id=application_id,
        )
        return self.create_alert(schema, deduplicate=True, auto_commit=auto_commit)

    def create_assessment_failure_alert(
        self,
        application_id: uuid.UUID,
        error_message: str,
        auto_commit: bool = True,
    ) -> OperationalAlert:
        """Helper to create an alert when assessment engine execution encounters an unexpected failure."""
        schema = OperationalAlertCreate(
            alert_type=OperationalAlertType.ASSESSMENT_FAILURE,
            severity=OperationalAlertSeverity.CRITICAL,
            title="Assessment Engine Execution Failure",
            message=(
                f"Credit assessment pipeline encountered an unexpected execution error while processing "
                f"application '{application_id}': {error_message[:200]}"
            ),
            application_id=application_id,
        )
        return self.create_alert(schema, deduplicate=True, auto_commit=auto_commit)
