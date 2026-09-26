"""Model version service for algorithm provenance and active scoring models."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.core.config import settings
from app.models.model_version import ModelVersion
from app.repositories.model_version import ModelVersionRepository
from app.schemas.model_version import (
    FairnessAuditRequest,
    FairnessAuditResponse,
    GlobalSHAPFeatureItem,
    GlobalSHAPResponse,
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

    # ------------------------------------------------------------------
    # P2-10: Global SHAP Feature Importance Aggregation
    # ------------------------------------------------------------------

    def compute_global_shap(
        self,
        model_version_id: Union[uuid.UUID, str],
        actor: Optional[Any] = None,
    ) -> GlobalSHAPResponse:
        """Compute global/model-level mean absolute SHAP feature importance.

        Uses the existing TreeShapExplainer against the offline evaluation dataset
        (data/synthetic/synthetic_credit_applications.parquet).  Does NOT execute
        during live assessment requests and does NOT expose individual applicant records.

        The frozen model artifact is loaded read-only; its SHA-256 hash is unmodified.

        Args:
            model_version_id: Primary key UUID of the model version to evaluate.
            actor: User executing the aggregation (for audit logging).

        Returns:
            GlobalSHAPResponse: Feature importance entries ordered by mean_abs_shap desc.

        Raises:
            EntityNotFoundError: If model version is not found.
            ValidationError: If evaluation dataset is missing, incompatible, or the model
                             artifact cannot be loaded.
        """
        import joblib

        mv = self.get_model_version(model_version_id)

        # Resolve model artifact path -----------------------------------------------
        # Only the volatility-aware LightGBM model supports TreeSHAP.
        _EXPECTED_MODEL_NAME = "volatility-aware-risk-model"
        if mv.model_name != _EXPECTED_MODEL_NAME:
            raise ValidationError(
                f"Model '{mv.model_name}' does not support TreeSHAP global aggregation. "
                f"Global TreeSHAP is only supported for '{_EXPECTED_MODEL_NAME}'."
            )

        artifact_path = (
            Path(settings.ML_MODEL_PATH)
            if getattr(settings, "ML_MODEL_PATH", None)
            else Path(__file__).resolve().parents[3]
            / "models"
            / "artifacts"
            / "volatility_aware_risk_model.joblib"
        )
        if not artifact_path.exists():
            raise ValidationError(
                f"Frozen model artifact not found at '{artifact_path}'. "
                "Cannot execute global SHAP aggregation."
            )

        try:
            frozen_model = joblib.load(artifact_path)
        except Exception as exc:
            raise ValidationError(
                f"Failed to load frozen model artifact: {exc}"
            ) from exc

        if not getattr(frozen_model, "is_fitted", False):
            raise ValidationError("Loaded model artifact is not fitted. Cannot compute SHAP values.")

        if hasattr(frozen_model, "model_version") and mv.version != frozen_model.model_version:
            raise ValidationError(
                f"Registered model version '{mv.version}' does not match loaded artifact version "
                f"'{frozen_model.model_version}'. Cannot compute global SHAP for mismatched versions."
            )

        # Resolve evaluation dataset -------------------------------------------------
        dataset_path = (
            Path(settings.ML_DATASET_PATH)
            if getattr(settings, "ML_DATASET_PATH", None)
            else Path(__file__).resolve().parents[3]
            / "data"
            / "synthetic"
            / "synthetic_credit_applications.parquet"
        )
        if not dataset_path.exists():
            raise ValidationError(
                f"Offline evaluation dataset not found at '{dataset_path}'. "
                "Cannot execute global SHAP aggregation."
            )

        try:
            df = pd.read_parquet(dataset_path)
        except Exception as exc:
            raise ValidationError(
                f"Failed to load offline evaluation dataset: {exc}"
            ) from exc

        # Resolve preprocessor artifact -------------------------------------------
        # The persisted preprocessor encapsulates all feature engineering (feat_eng_*
        # interactions, one-hot encoding) required to produce the 64-column model
        # input matrix.  We MUST use it rather than raw dataset columns to avoid
        # missing features like feat_eng_vol_to_baseline, gig_work_type_DELIVERY, etc.
        preprocessor_path = (
            Path(__file__).resolve().parents[3]
            / "models"
            / "artifacts"
            / "credit_risk_preprocessor.joblib"
        )
        if not preprocessor_path.exists():
            raise ValidationError(
                f"Preprocessor artifact not found at '{preprocessor_path}'. "
                "Cannot derive engineered features for global SHAP aggregation."
            )

        try:
            preprocessor = joblib.load(preprocessor_path)
        except Exception as exc:
            raise ValidationError(
                f"Failed to load preprocessor artifact: {exc}"
            ) from exc

        # Transform raw dataset through the frozen preprocessor to get all 64 features.
        try:
            X_transformed = preprocessor.transform(df)
        except Exception as exc:
            raise ValidationError(
                f"Preprocessor failed to transform evaluation dataset: {exc}"
            ) from exc

        # Validate that the transformed output aligns with model expectations.
        feature_names = list(frozen_model.feature_names_in_ or [])
        if not feature_names:
            raise ValidationError(
                "Frozen model artifact does not expose feature_names_in_. "
                "Cannot deterministically align the evaluation dataset."
            )

        missing_cols = [f for f in feature_names if f not in X_transformed.columns]
        if missing_cols:
            raise ValidationError(
                f"Preprocessor output is missing {len(missing_cols)} model features. "
                f"Incompatible dataset/preprocessor. Missing: {sorted(missing_cols)}"
            )

        # Select features in exact model order; drop rows with NaN without imputing.
        df_clean = X_transformed[feature_names].dropna()
        if len(df_clean) == 0:
            raise ValidationError(
                "No complete rows found in preprocessed evaluation dataset. "
                "Cannot compute global SHAP values."
            )

        X_eval = df_clean[feature_names]  # DataFrame aligned to model feature order


        # Compute SHAP values via existing TreeShapExplainer -------------------------
        try:
            from src.ml.explainability.shap_explainer import TreeShapExplainer
            explainer = TreeShapExplainer(frozen_model)
            global_explanation = explainer.explain_global(X_eval)
        except Exception as exc:
            raise ValidationError(
                f"TreeSHAP global aggregation failed: {exc}"
            ) from exc

        # Compute signed mean SHAP (mean over all samples, preserving direction) ----
        X_arr = X_eval.values
        shap_vals_raw = explainer.explainer.shap_values(X_arr)
        if isinstance(shap_vals_raw, list):
            sample_shap = shap_vals_raw[1] if len(shap_vals_raw) > 1 else shap_vals_raw[0]
        else:
            sample_shap = shap_vals_raw
        mean_shap_signed = np.mean(sample_shap, axis=0)  # shape: (n_features,)

        # Build ordered feature list ------------------------------------------------
        # Primary sort: mean_abs_shap descending.
        # Secondary sort: feature_name ascending (deterministic tie-breaking).
        abs_importances = global_explanation.mean_absolute_attributions  # dict: name -> float
        ranked_features = sorted(
            feature_names,
            key=lambda n: (-abs_importances.get(n, 0.0), n),
        )

        feature_name_to_idx = {name: i for i, name in enumerate(feature_names)}
        features_out: List[GlobalSHAPFeatureItem] = []
        for rank, fname in enumerate(ranked_features, start=1):
            idx = feature_name_to_idx[fname]
            features_out.append(
                GlobalSHAPFeatureItem(
                    feature_name=fname,
                    mean_abs_shap=round(float(abs_importances.get(fname, 0.0)), 6),
                    mean_shap=round(float(mean_shap_signed[idx]), 6),
                    rank=rank,
                )
            )

        now_utc = datetime.now(timezone.utc)
        response = GlobalSHAPResponse(
            model_version_id=mv.id,
            model_version=mv.version,
            model_name=mv.model_name,
            evaluated_at=now_utc,
            sample_count=int(df_clean.shape[0]),
            dataset_source=(
                "Offline synthetic evaluation dataset (data/synthetic/synthetic_credit_applications.parquet). "
                "No individual applicant records are included in this aggregation."
            ),
            features=features_out,
        )

        # Audit log the computation ---------------------------------------------------
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
                        "operation": "global_shap_aggregation",
                        "model_name": mv.model_name,
                        "version": mv.version,
                        "sample_count": response.sample_count,
                        "feature_count": len(features_out),
                        "features": [
                            {
                                "feature_name": f.feature_name,
                                "mean_abs_shap": f.mean_abs_shap,
                                "mean_shap": f.mean_shap,
                                "rank": f.rank,
                            }
                            for f in features_out
                        ],
                    },
                    commit=False,
                )
                self.db.commit()
            except Exception:
                pass

        return response

