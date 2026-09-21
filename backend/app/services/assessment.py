"""Assessment service for credit evaluation outcomes and provenance."""
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import AssessmentEngineError, AssessmentOutputError
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.models.assessment import CreditAssessment
from app.repositories.application import ApplicationRepository
from app.repositories.assessment import AssessmentRepository
from app.repositories.financial_signal import FinancialSignalRepository
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
        signal_repo: Optional[FinancialSignalRepository] = None,
        engine: Optional[AssessmentEngine] = None,
    ) -> None:
        """Initialize AssessmentService with required repositories and optional engine."""
        self.db = db
        self.assessment_repo = assessment_repo or AssessmentRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.model_version_repo = model_version_repo or ModelVersionRepository(db=db)
        self.signal_repo = signal_repo or FinancialSignalRepository(db=db)
        self.engine = engine

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

    def assess_application(
        self,
        application_id: Union[uuid.UUID, str],
        model_version_id: Optional[Union[uuid.UUID, str]] = None,
        engine: Optional[AssessmentEngine] = None,
        auto_commit: bool = True,
    ) -> CreditAssessment:
        """Execute an assessment on an application using the configured engine.

        Constructs AssessmentInput, invokes the engine's assess() method, validates the
        resulting AssessmentResult, and persists the credit assessment record.

        Args:
            application_id: Target application UUID.
            model_version_id: Optional specific model version to associate. If omitted,
                resolves the active model version or first registered model version.
            engine: Optional override for the assessment engine.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            CreditAssessment: Created assessment entity.

        Raises:
            AssessmentEngineError: If no engine is configured or engine execution fails.
            AssessmentOutputError: If engine returns unexpected result type.
            EntityNotFoundError: If application or model version does not exist.
        """
        active_engine = engine or self.engine
        if active_engine is None:
            raise AssessmentEngineError("No assessment engine configured for AssessmentService.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Resolve model_version_id if not explicitly provided
        mv_id = model_version_id
        if mv_id is None:
            active_mv = self.model_version_repo.get_active(db=self.db)
            if active_mv:
                mv_id = active_mv.id
            else:
                mvs = self.model_version_repo.list_versions(active_only=False, db=self.db)
                if mvs:
                    mv_id = mvs[0].id
                else:
                    raise EntityNotFoundError(
                        "No active or registered ModelVersion found to associate with assessment."
                    )

        # Build AssessmentInput via adapter
        profile = getattr(app, "applicant_profile", None)
        latest_signal = self.signal_repo.get_latest(app.id, db=self.db) if self.signal_repo else None
        if latest_signal is None:
            signals = getattr(app, "financial_signals", None)
            latest_signal = signals[-1] if signals else None

        input_data = AssessmentInput.from_domain_objects(
            application=app,
            applicant_profile=profile,
            financial_signal=latest_signal,
        )

        # Invoke engine
        result = active_engine.assess(input_data)
        if not isinstance(result, AssessmentResult):
            raise AssessmentOutputError(
                f"Assessment engine returned {type(result).__name__}, expected AssessmentResult."
            )

        # Map to CreditAssessmentCreate schema
        create_schema = result.to_credit_assessment_create(
            application_id=app.id,
            model_version_id=mv_id,
        )

        assessment = self.create_assessment(create_schema, auto_commit=auto_commit)
        setattr(assessment, "_transient_model_name", result.model_name)
        setattr(assessment, "_transient_model_version", result.model_version)
        setattr(assessment, "_transient_key_factors", result.key_factors)
        setattr(assessment, "_transient_explanation", result.explanation)
        return assessment

