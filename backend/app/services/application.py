"""Application service for credit assessment request lifecycle and status transitions."""
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.application import Application, ApplicationStatus
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.audit import AuditService
from app.services.exceptions import (
    EntityNotFoundError,
    InvalidStateTransitionError,
    ValidationError,
)


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


# Formal pipeline transitions for decision-support applications
VALID_STATUS_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DRAFT: {ApplicationStatus.SUBMITTED},
    ApplicationStatus.SUBMITTED: {ApplicationStatus.UNDER_REVIEW},
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.ASSESSED,
        ApplicationStatus.MANUAL_REVIEW,
    },
    ApplicationStatus.MANUAL_REVIEW: {
        ApplicationStatus.ASSESSED,
        ApplicationStatus.COMPLETED,
    },
    ApplicationStatus.ASSESSED: {
        ApplicationStatus.COMPLETED,
        ApplicationStatus.MANUAL_REVIEW,
    },
    ApplicationStatus.COMPLETED: set(),
}


class ApplicationService:
    """Business service orchestrating application lifecycle and workflow transitions."""

    def __init__(
        self,
        db: Session,
        app_repo: Optional[ApplicationRepository] = None,
        applicant_repo: Optional[ApplicantRepository] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize ApplicationService with required repositories and audit service."""
        self.db = db
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.applicant_repo = applicant_repo or ApplicantRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)

    def create_application(
        self,
        application_in: Union[ApplicationCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> Application:
        """Create a new credit assessment application.

        Args:
            application_in: Application details including applicant_profile_id and requested_loan_amount.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Application: Created application entity.

        Raises:
            ValidationError: If applicant_profile_id or loan amount is invalid.
            EntityNotFoundError: If the associated ApplicantProfile does not exist.
        """
        data = _extract_dict(application_in)
        applicant_profile_id = data.get("applicant_profile_id")
        if not applicant_profile_id:
            raise ValidationError("applicant_profile_id is required to create an application.")

        # Ensure applicant profile exists
        profile = self.applicant_repo.get_by_id(applicant_profile_id, db=self.db)
        if not profile:
            raise EntityNotFoundError(
                f"ApplicantProfile with id '{applicant_profile_id}' does not exist."
            )

        # Validate requested loan amount
        loan_amount = data.get("requested_loan_amount")
        if loan_amount is None:
            raise ValidationError("requested_loan_amount is required.")
        if Decimal(str(loan_amount)) <= Decimal("0"):
            raise ValidationError("requested_loan_amount must be greater than 0.")

        # Ensure default status is DRAFT
        if not data.get("status"):
            data["status"] = ApplicationStatus.DRAFT

        try:
            app = self.app_repo.create(data, commit=False, db=self.db)
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.APPLICATION_CREATED,
                        entity_type="Application",
                        entity_id=getattr(app, "id", None),
                        application_id=getattr(app, "id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "applicant_profile_id": str(getattr(app, "applicant_profile_id", "")),
                            "status": getattr(app.status, "value", str(app.status)),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(app)
            return app
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_application(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> Application:
        """Retrieve an application by ID.

        Args:
            application_id: Primary key UUID.

        Returns:
            Application: Matching application entity.

        Raises:
            EntityNotFoundError: If application does not exist.
        """
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")
        return app

    def list_applications(
        self,
        applicant_profile_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[Application]:
        """List applications belonging to an applicant profile.

        Args:
            applicant_profile_id: Profile primary key UUID.
            skip: Offset count.
            limit: Maximum items to return.

        Returns:
            List[Application]: Matching applications.
        """
        return self.app_repo.list_by_applicant(
            applicant_profile_id, skip=skip, limit=limit, db=self.db
        )

    def list_all_applications(
        self,
        status: Optional[Union[ApplicationStatus, str]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Application]:
        """List all applications with optional status filtering for reviewers and administrators.

        Args:
            status: Optional ApplicationStatus enum or string to filter by.
            skip: Offset count.
            limit: Maximum items to return.

        Returns:
            List[Application]: Matching applications.
        """
        return self.app_repo.list_all(status=status, skip=skip, limit=limit, db=self.db)

    def update_application(
        self,
        application_id: Union[uuid.UUID, str],
        app_update: Union[ApplicationUpdate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> Application:
        """Update fields on an application.

        Args:
            application_id: Primary key UUID.
            app_update: Fields to update.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Application: Updated application entity.

        Raises:
            EntityNotFoundError: If application does not exist.
            ValidationError: If updated loan amount is invalid.
            InvalidStateTransitionError: If status change violates workflow rules.
        """
        app = self.get_application(application_id)
        data = _extract_dict(app_update)

        if "requested_loan_amount" in data and data["requested_loan_amount"] is not None:
            if Decimal(str(data["requested_loan_amount"])) <= Decimal("0"):
                raise ValidationError("requested_loan_amount must be greater than 0.")

        if "status" in data and data["status"] is not None:
            new_status = data["status"]
            if isinstance(new_status, str):
                new_status = ApplicationStatus(new_status)
            self._validate_transition(app.status, new_status)
            data["status"] = new_status

        old_status = app.status
        try:
            updated_app = self.app_repo.update(app, data, commit=False, db=self.db)
            if self.audit_service:
                try:
                    metadata: Dict[str, Any] = {"updated_fields": list(data.keys())}
                    if "status" in data and updated_app.status != old_status:
                        metadata["previous_status"] = old_status.value if hasattr(old_status, "value") else str(old_status)
                        metadata["new_status"] = updated_app.status.value if hasattr(updated_app.status, "value") else str(updated_app.status)
                        self.audit_service.record_event(
                            action=AuditAction.APPLICATION_STATUS_CHANGED,
                            entity_type="Application",
                            entity_id=getattr(updated_app, "id", None),
                            application_id=getattr(updated_app, "id", None),
                            outcome=AuditOutcome.SUCCESS,
                            metadata=metadata,
                            commit=False,
                        )
                    self.audit_service.record_event(
                        action=AuditAction.APPLICATION_UPDATED,
                        entity_type="Application",
                        entity_id=getattr(updated_app, "id", None),
                        application_id=getattr(updated_app, "id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata=metadata,
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(updated_app)
            return updated_app
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def update_status(
        self,
        application_id: Union[uuid.UUID, str],
        new_status: Union[ApplicationStatus, str],
        auto_commit: bool = True,
    ) -> Application:
        """Advance an application to a new status following valid state transitions.

        Args:
            application_id: Primary key UUID.
            new_status: Next ApplicationStatus or string equivalent.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            Application: Updated application entity.

        Raises:
            EntityNotFoundError: If application does not exist.
            InvalidStateTransitionError: If the status transition is prohibited.
        """
        app = self.get_application(application_id)
        if isinstance(new_status, str):
            new_status = ApplicationStatus(new_status)

        old_status = app.status
        self._validate_transition(app.status, new_status)

        try:
            updated_app = self.app_repo.update_status(
                app, new_status, commit=False, db=self.db
            )
            if updated_app is None:
                raise EntityNotFoundError(f"Application with id '{application_id}' not found.")
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.APPLICATION_STATUS_CHANGED,
                        entity_type="Application",
                        entity_id=getattr(updated_app, "id", None),
                        application_id=getattr(updated_app, "id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "previous_status": old_status.value if hasattr(old_status, "value") else str(old_status),
                            "new_status": new_status.value if hasattr(new_status, "value") else str(new_status),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(updated_app)
            return updated_app
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    transition_status = update_status

    def _validate_transition(
        self,
        current_status: ApplicationStatus,
        new_status: ApplicationStatus,
    ) -> None:
        """Verify that transitioning from current_status to new_status is permitted.

        Raises:
            InvalidStateTransitionError: If transition is invalid.
        """
        if current_status == new_status:
            return  # No-op transition is allowed

        permitted = VALID_STATUS_TRANSITIONS.get(current_status, set())
        if new_status not in permitted:
            allowed_str = ", ".join(f"'{s.value}'" for s in permitted) or "None (terminal state)"
            raise InvalidStateTransitionError(
                f"Invalid status transition from '{current_status.value}' to '{new_status.value}'. "
                f"Allowed transitions: {allowed_str}."
            )
