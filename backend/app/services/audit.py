"""Centralized audit service for reliable, privacy-safe event tracking."""
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Set, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.audit import AuditLog
from app.models.user import UserRole
from app.repositories.audit import AuditRepository
from app.services.exceptions import AuditLoggingError, EntityNotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Keys that must NEVER appear in audit logs under any circumstance
PROHIBITED_AUDIT_KEYS: Set[str] = {
    # Credentials & authentication secrets
    "password",
    "password_hash",
    "hashed_password",
    "plain_password",
    "raw_password",
    "secret",
    "secret_key",
    "jwt",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "credentials",
    "api_key",
    "bearer",
    # Financial accounts & credentials
    "bank_account_number",
    "account_number",
    "bank_credentials",
    "banking_login_credentials",
    "raw_transactions",
    "raw_bank_statements",
    "raw_upi_transactions",
    "raw_upi_logs",
    "upi_vpa",
    "upi_id",
    "vpa",
    "merchant_name",
    "merchant_description",
    "merchant_details",
    # PII & surveillance data
    "gps_coordinates",
    "location_history",
    "coordinates",
    "location",
    "latitude",
    "longitude",
    "contact_list",
    "contacts",
    "address_book",
}

# Regex pattern for detecting JWT-like strings (header.payload.signature)
JWT_PATTERN = re.compile(r"^eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*$")


def _is_prohibited_key(key: str) -> bool:
    """Check whether a key matches any prohibited key pattern."""
    normalized = key.lower().strip().replace("-", "_")
    if normalized in PROHIBITED_AUDIT_KEYS:
        return True
    for prohibited in PROHIBITED_AUDIT_KEYS:
        if normalized == prohibited or normalized.endswith(f"_{prohibited}") or normalized.startswith(f"{prohibited}_"):
            return True
    return False


def sanitize_audit_metadata(data: Any) -> Any:
    """Recursively filter and remove prohibited sensitive keys and values from audit metadata.

    Removes passwords, credentials, tokens, raw financial statements,
    UPI identifiers, GPS data, and contact lists.
    """
    if data is None:
        return None

    if hasattr(data, "model_dump"):
        data = data.model_dump(exclude_unset=True)
    elif hasattr(data, "__dict__") and not isinstance(data, type):
        data = {k: v for k, v in vars(data).items() if not k.startswith("_")}

    if isinstance(data, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in data.items():
            if _is_prohibited_key(str(k)):
                continue
            sanitized[k] = sanitize_audit_metadata(v)
        return sanitized

    if isinstance(data, (list, tuple, set)):
        return [sanitize_audit_metadata(item) for item in data]

    if isinstance(data, str):
        # Redact raw JWT tokens or bearer strings
        if data.lower().startswith("bearer "):
            return "[REDACTED_TOKEN]"
        if JWT_PATTERN.match(data.strip()):
            return "[REDACTED_TOKEN]"
        return data

    if isinstance(data, uuid.UUID):
        return str(data)

    return data


def _safe_uuid(val: Any) -> Optional[uuid.UUID]:
    """Safely convert a value to UUID, returning None if conversion is not possible."""
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError, TypeError):
        return None


class AuditService:
    """Centralized service for creating and retrieving privacy-safe audit trail records."""

    def __init__(
        self,
        db: Session,
        audit_repo: Optional[AuditRepository] = None,
    ) -> None:
        """Initialize AuditService with database session and repository."""
        self.db = db
        self.audit_repo = audit_repo or AuditRepository(db=db)

    def record_event(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[Union[uuid.UUID, str]] = None,
        user_id: Optional[Union[uuid.UUID, str]] = None,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        actor_role: Optional[Union[UserRole, str]] = None,
        outcome: str = AuditOutcome.SUCCESS,
        metadata: Optional[Dict[str, Any]] = None,
        commit: bool = False,
    ) -> AuditLog:
        """Record an immutable, privacy-sanitized audit log event.

        Args:
            action: Standardized action identifier.
            entity_type: Category of the affected resource/entity.
            entity_id: Identifier of the affected entity.
            user_id: Actor or target User UUID.
            application_id: Associated Application UUID if applicable.
            actor_role: Role of the actor performing the operation.
            outcome: Outcome status ('SUCCESS', 'FAILURE', 'DENIED').
            metadata: Additional contextual structured details to sanitize and record.
            commit: Whether to commit immediately (used for standalone security events).

        Returns:
            AuditLog: The persisted audit record.

        Raises:
            ValidationError: If action or entity_type is missing.
            AuditLoggingError: If the audit record fails to persist.
        """
        if not action or not str(action).strip():
            raise ValidationError("Audit action identifier is required.")
        if not entity_type or not str(entity_type).strip():
            raise ValidationError("Audit entity_type is required.")

        # Prepare and sanitize metadata
        meta = metadata.copy() if metadata and isinstance(metadata, dict) else {}
        clean_meta = sanitize_audit_metadata(meta) or {}

        # Enrich metadata with outcome and role
        clean_meta["outcome"] = outcome
        if actor_role is not None:
            clean_meta["actor_role"] = (
                actor_role.value if hasattr(actor_role, "value") else str(actor_role)
            )

        # Parse foreign keys safely
        parsed_user_id = _safe_uuid(user_id)
        parsed_app_id = _safe_uuid(application_id)

        # Build audit log entity
        audit_entry = AuditLog(
            user_id=parsed_user_id,
            application_id=parsed_app_id,
            action=str(action).strip(),
            entity_type=str(entity_type).strip(),
            entity_id=str(entity_id) if entity_id is not None else None,
            audit_metadata=clean_meta,
        )

        try:
            record = self.audit_repo.create(audit_entry, commit=commit, db=self.db)
            return record
        except Exception as exc:
            logger.error(f"Failed to persist audit event '{action}': {exc}", exc_info=True)
            raise AuditLoggingError(f"Failed to persist audit log: {exc}") from exc

    def get_event(
        self,
        audit_id: Union[uuid.UUID, str],
    ) -> AuditLog:
        """Retrieve a specific audit event by ID.

        Args:
            audit_id: AuditLog UUID.

        Returns:
            AuditLog: The audit record.

        Raises:
            EntityNotFoundError: If audit event is not found.
        """
        parsed_id = _safe_uuid(audit_id)
        record = self.audit_repo.get_by_id(parsed_id or audit_id, db=self.db)
        if not record:
            raise EntityNotFoundError(f"Audit log with id '{audit_id}' not found.")
        return record

    def list_events(
        self,
        user_id: Optional[Union[uuid.UUID, str]] = None,
        application_id: Optional[Union[uuid.UUID, str]] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """List audit events with optional filtering.

        Args:
            user_id: Optional user filter.
            application_id: Optional application filter.
            action: Optional action filter.
            entity_type: Optional entity type filter.
            skip: Pagination offset.
            limit: Maximum items to return.

        Returns:
            List[AuditLog]: Filtered audit events.
        """
        return self.audit_repo.list_audit_logs(
            user_id=user_id,
            application_id=application_id,
            action=action,
            entity_type=entity_type,
            skip=skip,
            limit=limit,
            db=self.db,
        )

    def get_by_application(
        self,
        application_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Fetch audit events related to an application."""
        return self.audit_repo.get_by_application(
            application_id=application_id,
            skip=skip,
            limit=limit,
            db=self.db,
        )

    def get_by_user(
        self,
        user_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Fetch audit events related to a user."""
        return self.audit_repo.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
            db=self.db,
        )
