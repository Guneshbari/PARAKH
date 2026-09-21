"""Assessment service for credit evaluation outcomes and provenance."""
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.models.assessment import CreditAssessment
from app.repositories.application import ApplicationRepository
from app.repositories.assessment import AssessmentRepository
from app.repositories.model_version import ModelVersionRepository
from app.schemas.assessment import CreditAssessmentCreate
from app.services.exceptions import EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class AssessmentService:
    """Business service orchestrating credit assessment output recording and retrieval."""

    def __init__(
        self,
        db: Session,
        assessment_repo: Optional[AssessmentRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
        model_version_repo: Optional[ModelVersionRepository] = None,
    ) -> None:
        """Initialize AssessmentService with required repositories."""
        self.db = db
        self.assessment_repo = assessment_repo or AssessmentRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.model_version_repo = model_version_repo or ModelVersionRepository(db=db)

    def create_assessment(
        self,
        assessment_in: Union[CreditAssessmentCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> CreditAssessment:
        """Persist a credit assessment decision output.

        Does not compute or alter ML predictions. Enforces foreign key relationships
        and bounds on risk probabilities.

        Args:
            assessment_in: Assessment payload.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            CreditAssessment: Created assessment entity.

        Raises:
            ValidationError: If application_id or model_version_id is missing, or numeric ranges are violated.
            EntityNotFoundError: If application or model version does not exist.
        """
        data = _extract_dict(assessment_in)

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required for credit assessment.")

        model_version_id = data.get("model_version_id")
        if not model_version_id:
            raise ValidationError("model_version_id is required for credit assessment.")

        # Validate existence of application
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Validate existence of model version
        mv = self.model_version_repo.get_by_id(model_version_id, db=self.db)
        if not mv:
            raise EntityNotFoundError(
                f"ModelVersion with id '{model_version_id}' not found."
            )

        # Validate numeric ranges
        risk_prob = data.get("risk_probability")
        if risk_prob is not None:
            val = Decimal(str(risk_prob))
            if val < Decimal("0") or val > Decimal("1"):
                raise ValidationError("risk_probability must be between 0 and 1.")

        confidence = data.get("confidence")
        if confidence is not None:
            val = Decimal(str(confidence))
            if val < Decimal("0") or val > Decimal("1"):
                raise ValidationError("confidence must be between 0 and 1.")

        try:
            assessment = self.assessment_repo.create(data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(assessment)
            return assessment
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_assessment(
        self,
        assessment_id: Union[uuid.UUID, str],
    ) -> CreditAssessment:
        """Retrieve a credit assessment by ID.

        Args:
            assessment_id: Primary key UUID.

        Returns:
            CreditAssessment: Matching assessment entity.

        Raises:
            EntityNotFoundError: If assessment does not exist.
        """
        assessment = self.assessment_repo.get_by_id(assessment_id, db=self.db)
        if not assessment:
            raise EntityNotFoundError(
                f"CreditAssessment with id '{assessment_id}' not found."
            )
        return assessment

    def get_application_assessments(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> List[CreditAssessment]:
        """Fetch all assessments performed for an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            List[CreditAssessment]: List of assessments in reverse chronological order.
        """
        return self.assessment_repo.get_by_application(application_id, db=self.db)

    def get_latest_assessment(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> Optional[CreditAssessment]:
        """Fetch the most recent credit assessment for an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            Optional[CreditAssessment]: Most recent assessment or None.
        """
        return self.assessment_repo.get_latest(application_id, db=self.db)
