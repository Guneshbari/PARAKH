"""Review service for human adjudication outcomes and officer oversight."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.application import ApplicationStatus
from app.models.review import ReviewOutcome, ReviewOutcomeType
from app.repositories.application import ApplicationRepository
from app.repositories.review import ReviewRepository
from app.repositories.user import UserRepository
from app.schemas.review import ReviewOutcomeCreate
from app.services.audit import AuditService
from app.services.exceptions import EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ReviewService:
    """Business service orchestrating human review outcomes and decision oversight."""

    def __init__(
        self,
        db: Session,
        review_repo: Optional[ReviewRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
        user_repo: Optional[UserRepository] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize ReviewService with required repositories and audit service."""
        self.db = db
        self.review_repo = review_repo or ReviewRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.user_repo = user_repo or UserRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)

    def create_review(
        self,
        review_in: Union[ReviewOutcomeCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> ReviewOutcome:
        """Record a human officer review outcome on an application.

        Args:
            review_in: Review outcome details.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ReviewOutcome: Created review outcome entity.

        Raises:
            ValidationError: If application_id, reviewer_id, or outcome is missing.
            EntityNotFoundError: If the application or reviewer user does not exist.
        """
        data = _extract_dict(review_in)

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required to record a review.")

        reviewer_id = data.get("reviewer_id")
        if not reviewer_id:
            raise ValidationError("reviewer_id is required to record a review.")

        if not data.get("outcome"):
            raise ValidationError("outcome is required.")

        notes = data.get("notes")
        if notes is not None and isinstance(notes, str) and len(notes.strip()) > 0 and len(notes.strip()) < 10:
            raise ValidationError("Review decision notes must contain at least 10 characters.")

        # Validate existence of application
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Validate existence of reviewer
        reviewer = self.user_repo.get_by_id(reviewer_id, db=self.db)
        if not reviewer:
            raise EntityNotFoundError(f"Reviewer User with id '{reviewer_id}' not found.")

        try:
            review = self.review_repo.create(data, commit=False, db=self.db)

            # Map review outcome to target application status
            outcome_val = getattr(review, "outcome", None)
            target_status: Optional[ApplicationStatus] = None
            if outcome_val == ReviewOutcomeType.REVIEWED:
                target_status = ApplicationStatus.COMPLETED
            elif outcome_val == ReviewOutcomeType.ESCALATED:
                target_status = ApplicationStatus.MANUAL_REVIEW
            elif outcome_val == ReviewOutcomeType.ADDITIONAL_INFORMATION_REQUIRED:
                target_status = ApplicationStatus.UNDER_REVIEW

            if target_status and app.status != target_status:
                old_status = app.status
                self.app_repo.update_status(app, target_status, commit=False, db=self.db)
                if self.audit_service:
                    try:
                        self.audit_service.record_event(
                            action=AuditAction.APPLICATION_STATUS_CHANGED,
                            entity_type="Application",
                            entity_id=getattr(app, "id", None),
                            application_id=getattr(app, "id", None),
                            user_id=getattr(review, "reviewer_id", None),
                            outcome=AuditOutcome.SUCCESS,
                            metadata={
                                "previous_status": old_status.value if hasattr(old_status, "value") else str(old_status),
                                "new_status": target_status.value if hasattr(target_status, "value") else str(target_status),
                                "trigger": "REVIEW_OUTCOME_RECORDED",
                            },
                            commit=False,
                        )
                    except Exception:
                        pass

            if self.audit_service:
                try:
                    outcome_str = outcome_val.value if hasattr(outcome_val, "value") else str(outcome_val)
                    self.audit_service.record_event(
                        action=AuditAction.REVIEW_CREATED,
                        entity_type="ReviewOutcome",
                        entity_id=getattr(review, "id", None),
                        application_id=getattr(review, "application_id", None),
                        user_id=getattr(review, "reviewer_id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "review_outcome": outcome_str,
                            "notes_present": bool(getattr(review, "notes", None)),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(review)
            return review
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_application_reviews(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> List[ReviewOutcome]:
        """Fetch all human review outcomes conducted on an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            List[ReviewOutcome]: Review outcomes in reverse chronological order.
        """
        return self.review_repo.get_by_application(application_id, db=self.db)

    def get_reviewer_reviews(
        self,
        reviewer_id: Union[uuid.UUID, str],
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReviewOutcome]:
        """Fetch all review outcomes submitted by a particular reviewer.

        Args:
            reviewer_id: Reviewer User primary key UUID.
            skip: Pagination offset.
            limit: Maximum items to return.

        Returns:
            List[ReviewOutcome]: Review outcomes by reviewer.
        """
        return self.review_repo.get_by_reviewer(
            reviewer_id, skip=skip, limit=limit, db=self.db
        )
