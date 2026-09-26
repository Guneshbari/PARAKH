"""Model version service for algorithm provenance and active scoring models."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.core.config import settings
from app.models.model_version import ModelVersion
from app.repositories.model_version import ModelVersionRepository
from app.schemas.model_version import (
    FairnessAuditRequest,
    FairnessAuditResponse,
    ModelVersionCreate,
    SubgroupFairnessMetricsResponse,
)
from app.services.audit import AuditService
from app.services.exceptions import EntityNotFoundError, ValidationError
from src.ml.evaluation.fairness import GroupedFairnessAuditor


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ModelVersionService:
    """Business service managing algorithmic model registry and versions."""

    def __init__(
        self,
        db: Session,
        model_version_repo: Optional[ModelVersionRepository] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize ModelVersionService with ModelVersionRepository and audit service."""
        self.db = db
        self.model_version_repo = model_version_repo or ModelVersionRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)

    def create_model_version(
        self,
        model_version_in: Union[ModelVersionCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> ModelVersion:
        """Register a new algorithmic model version in the registry.

        Args:
            model_version_in: Model metadata.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ModelVersion: Registered model version entity.

        Raises:
            ValidationError: If model_name or version is missing.
        """
        data = _extract_dict(model_version_in)
        if not data.get("model_name"):
            raise ValidationError("model_name is required.")
        if not data.get("version"):
            raise ValidationError("version string is required.")

        try:
            mv = self.model_version_repo.create(data, commit=False, db=self.db)
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.MODEL_VERSION_CREATED,
                        entity_type="ModelVersion",
                        entity_id=getattr(mv, "id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "model_name": getattr(mv, "model_name", None),
                            "version": getattr(mv, "version", None),
                            "is_active": getattr(mv, "is_active", None),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(mv)
            return mv
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_model_version(
        self,
        model_version_id: Union[uuid.UUID, str],
    ) -> ModelVersion:
        """Retrieve a model version by ID.

        Args:
            model_version_id: Primary key UUID.

        Returns:
            ModelVersion: Matching entity.

        Raises:
            EntityNotFoundError: If model version is not found.
        """
        mv = self.model_version_repo.get_by_id(model_version_id, db=self.db)
        if not mv:
            raise EntityNotFoundError(
                f"ModelVersion with id '{model_version_id}' not found."
            )
        return mv

    def get_active_model(
        self,
        model_name: Optional[str] = None,
    ) -> Optional[ModelVersion]:
        """Fetch the currently active model version for scoring.

        Args:
            model_name: Optional model identifier filter.

        Returns:
            Optional[ModelVersion]: Active model version or None.
        """
        return self.model_version_repo.get_active(model_name=model_name, db=self.db)

    def list_versions(
        self,
        model_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelVersion]:
        """List registered model versions with optional name filter.

        Args:
            model_name: Optional filter by model identifier.
            skip: Pagination offset.
            limit: Maximum items to return.

        Returns:
            List[ModelVersion]: List of model versions.
        """
        return self.model_version_repo.list_versions(
            model_name=model_name, skip=skip, limit=limit, db=self.db
        )

    def activate_model_version(
        self,
        model_version_id: Union[uuid.UUID, str],
        actor: Optional[Any] = None,
        auto_commit: bool = True,
    ) -> ModelVersion:
        """Promote and activate a model version, deactivating any prior active version in its family.

        Args:
            model_version_id: Primary key UUID of model version to activate.
            actor: User performing the activation.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ModelVersion: Activated model version.

        Raises:
            EntityNotFoundError: If model version is not found.
        """
        mv = self.get_model_version(model_version_id)
        current_active = self.model_version_repo.get_active(
            model_name=mv.model_name, db=self.db
        )
        prev_version = (
            current_active.version
            if (current_active and current_active.id != mv.id)
            else (mv.version if mv.is_active else None)
        )

        try:
            self.model_version_repo.activate(mv, commit=False, db=self.db)
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.MODEL_VERSION_ACTIVATED,
                        entity_type="ModelVersion",
                        entity_id=getattr(mv, "id", None),
                        user_id=getattr(actor, "id", None),
                        actor_role=getattr(actor, "role", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "model_name": mv.model_name,
                            "version": mv.version,
                            "previous_active_version": prev_version,
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(mv)
            return mv
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def evaluate_fairness(
        self,
        model_version_id: Union[uuid.UUID, str],
        audit_request: Optional[FairnessAuditRequest] = None,
        actor: Optional[Any] = None,
        auto_commit: bool = True,
    ) -> FairnessAuditResponse:
        """Execute offline demographic parity and equal opportunity fairness evaluation.

        Args:
            model_version_id: Primary key UUID of model version to evaluate.
            audit_request: Evaluation parameters and optional records.
            actor: User executing the audit.
            auto_commit: Whether to commit audit events to database.

        Returns:
            FairnessAuditResponse: Disparity metrics, subgroup stats, and disclaimers.

        Raises:
            EntityNotFoundError: If model version is not found.
            ValidationError: If inputs are invalid or dataset cannot be evaluated.
        """
        mv = self.get_model_version(model_version_id)
        if audit_request is None:
            audit_request = FairnessAuditRequest()

        if audit_request.records is not None:
            if len(audit_request.records) == 0:
                raise ValidationError("records list cannot be empty when provided.")
            y_true = [r.y_true for r in audit_request.records]
            y_prob = [r.y_prob for r in audit_request.records]
            subgroups = [r.subgroup for r in audit_request.records]
        else:
            dataset_path = (
                Path(settings.ML_DATASET_PATH)
                if settings.ML_DATASET_PATH
                else Path(__file__).resolve().parents[3]
                / "data"
                / "synthetic"
                / "synthetic_credit_applications.parquet"
            )
            if not dataset_path.exists():
                raise ValidationError(
                    f"Offline benchmark dataset not found at '{dataset_path}'."
                )

            try:
                df = pd.read_parquet(dataset_path)
            except Exception as exc:
                raise ValidationError(
                    f"Failed to load offline benchmark dataset: {exc}"
                ) from exc

            if audit_request.subgroup_field not in df.columns:
                raise ValidationError(
                    f"Subgroup field '{audit_request.subgroup_field}' is not present in the offline benchmark dataset. "
                    "Approved operational fields include: 'gig_work_type', 'cohort_archetype', 'loan_purpose'."
                )

            df_clean = df.dropna(
                subset=[
                    "target_default_flag",
                    "repayment_risk_probability",
                    audit_request.subgroup_field,
                ]
            )
            if len(df_clean) == 0:
                raise ValidationError(
                    f"No valid records found in benchmark dataset for subgroup field '{audit_request.subgroup_field}'."
                )

            y_true = df_clean["target_default_flag"].to_numpy(dtype=int)
            y_prob = df_clean["repayment_risk_probability"].to_numpy(dtype=float)
            subgroups = [str(x) for x in df_clean[audit_request.subgroup_field].tolist()]

        try:
            auditor = GroupedFairnessAuditor(
                subgroup_field_name=audit_request.subgroup_field,
                threshold=audit_request.threshold,
            )
            report = auditor.audit(
                y_true=y_true,
                y_prob=y_prob,
                subgroups=subgroups,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        subgroup_responses = {
            k: SubgroupFairnessMetricsResponse(
                subgroup_name=v.subgroup_name,
                sample_count=v.sample_count,
                positive_actual_count=v.positive_actual_count,
                negative_actual_count=v.negative_actual_count,
                empirical_default_rate=v.empirical_default_rate,
                favorable_prediction_rate=v.favorable_prediction_rate,
                true_positive_rate=v.true_positive_rate,
                false_positive_rate=v.false_positive_rate,
                precision=v.precision,
            )
            for k, v in report.subgroups.items()
        }

        now_utc = datetime.now(timezone.utc)
        response = FairnessAuditResponse(
            model_version_id=mv.id,
            model_name=mv.model_name,
            version=mv.version,
            evaluation_timestamp=now_utc,
            subgroup_field=report.subgroup_field,
            threshold=audit_request.threshold,
            sample_count=len(y_true),
            subgroups=subgroup_responses,
            demographic_parity_ratio=report.demographic_parity_ratio,
            equal_opportunity_difference=report.equal_opportunity_difference,
            limitations_disclaimer=report.limitations_disclaimer,
            audit_notes=report.audit_notes,
        )

        if self.audit_service:
            try:
                self.audit_service.record_event(
                    action=AuditAction.MODEL_FAIRNESS_EVALUATED,
                    entity_type="ModelVersion",
                    entity_id=getattr(mv, "id", None),
                    user_id=getattr(actor, "id", None),
                    actor_role=getattr(actor, "role", None),
                    outcome=AuditOutcome.SUCCESS,
                    metadata={
                        "subgroup_field": report.subgroup_field,
                        "threshold": audit_request.threshold,
                        "sample_count": len(y_true),
                        "demographic_parity_ratio": report.demographic_parity_ratio,
                        "equal_opportunity_difference": report.equal_opportunity_difference,
                    },
                    commit=False,
                )
            except Exception:
                pass

        if auto_commit:
            self.db.commit()

        return response
