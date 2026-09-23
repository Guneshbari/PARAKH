"""RiskPredictor — Main orchestrator for PARAKH credit risk inference (Phase 9).

Implements a deterministic, single-applicant inference pipeline around the frozen
Phase 8 Volatility-Aware LightGBM model without retraining, re-fitting the preprocessor
on inference data, or creating any API endpoint.

Pipeline steps (for a scored application):
  1. InputValidator.validate(application_dict)          — contract compliance
  2. InputValidator.check_data_sufficiency(...)          — evidence gate
  3. FeatureEngineer.transform(single_row_df)            — 9 engineered features
  4. preprocessor.transform(engineered_df)[64 cols]      — scaling/encoding (training-fitted)
  5. model.predict_proba(X_64)                           — default probability
  6. OutputFormatter._map_risk_tier + _compute_score     — risk tier + score
  7. TreeShapExplainer.explain_instance(X_64)            — SHAP attributions
  8. PlainLanguageExplainer.generate_borrower_summary()  — human-readable factors
  9. OutputFormatter.format_scored(...)                  — final PredictionResponse

For INSUFFICIENT applications, steps 3-8 are skipped; OutputFormatter.format_insufficient
is called directly.

Preprocessor construction strategy (prototype):
  The fitted preprocessor cannot be re-fitted on inference data (leakage).
  No serialised preprocessor artifact exists yet from Phase 3/6 training runs.
  At predictor initialisation, this module deterministically re-runs the training
  split with seed=42 and fits the preprocessor on the training partition only —
  identical to what was done during model training.  This is acceptable for a
  prototype; a production system would serialise the fitted preprocessor once and
  load it here instead.
"""
import json
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.explainability.plain_language import PlainLanguageExplainer
from src.ml.explainability.shap_explainer import TreeShapExplainer
from src.ml.features.feature_engineering import FeatureEngineer, build_model_ready_matrices
from src.ml.inference.input_validator import InputValidator, InputValidationError
from src.ml.inference.output_formatter import OutputFormatter, PredictionResponse

logger = logging.getLogger(__name__)

# Default paths resolved relative to the project root (one level above src/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MANIFEST_PATH = _PROJECT_ROOT / "models" / "artifacts" / "FINAL_MODEL.json"
_DEFAULT_DATASET_PATH = (
    _PROJECT_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet"
)


class RiskPredictor:
    """Deterministic credit risk predictor for a single PARAKH application assessment.

    Usage:
        predictor = RiskPredictor()           # loads frozen model + builds preprocessor
        response = predictor.predict(app_dict)
        print(response.to_dict())

    Args:
        manifest_path: Path to FINAL_MODEL.json.  Defaults to the project-root location.
        dataset_path: Path to the canonical Phase 2 Parquet dataset used only for fitting
                      the preprocessor on the training partition.  Defaults to the canonical
                      synthetic dataset.
    """

    def __init__(
        self,
        manifest_path: Optional[Path] = None,
        dataset_path: Optional[Path] = None,
    ) -> None:
        self._manifest_path = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
        self._dataset_path = Path(dataset_path) if dataset_path else _DEFAULT_DATASET_PATH

        logger.info("Initialising RiskPredictor from manifest: %s", self._manifest_path)

        # --- Load frozen model manifest ---
        self._manifest = self._load_manifest()
        self._model_name: str = self._manifest["selected_model_name"]
        self._model_version: str = self._manifest["model_version"]
        self._feature_variant: str = self._manifest["feature_variant"]
        artifact_rel: str = self._manifest["artifact_path"]
        artifact_path = _PROJECT_ROOT / artifact_rel

        # --- Load frozen model artifact ---
        logger.info("Loading model artifact: %s", artifact_path)
        self._model = joblib.load(artifact_path)
        if not getattr(self._model, "is_fitted", False):
            raise RuntimeError(
                f"Loaded model artifact at '{artifact_path}' reports is_fitted=False. "
                "The model artifact may be corrupt or incomplete."
            )
        logger.info(
            "Model loaded: name=%s version=%s features=%d",
            self._model.model_name,
            self._model.model_version,
            len(self._model.feature_names_in_),
        )

        # --- Build fitted preprocessor and feature engineer ---
        self._engineer, self._preprocessor = self._build_fitted_pipeline()

        # --- Initialise TreeSHAP explainer ---
        logger.info("Initialising TreeSHAP explainer...")
        try:
            self._explainer: Optional[TreeShapExplainer] = TreeShapExplainer(self._model)
        except Exception as exc:
            logger.warning(
                "TreeSHAP explainer initialisation failed (%s). "
                "Explanations will be unavailable for this session.",
                exc,
            )
            self._explainer = None

        logger.info("RiskPredictor ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, application: Dict[str, Any]) -> PredictionResponse:
        """Run the complete inference pipeline for a single application dict.

        Args:
            application: Raw application assessment dict.  Must contain all 46
                         pre-encoding input fields and must NOT contain excluded
                         non-predictor columns or prohibited fields.

        Returns:
            PredictionResponse: Structured inference output.

        Raises:
            InputValidationError: If the input dict fails the frozen data contract.
        """
        # Step 1 — Validate input contract compliance
        InputValidator.validate(application)

        # Step 2 — Data sufficiency gate
        is_insufficient, reasons = InputValidator.check_data_sufficiency(application)
        if is_insufficient:
            logger.info(
                "Application routed to INSUFFICIENT: %s", reasons
            )
            return OutputFormatter.format_insufficient(
                reasons=reasons,
                model_name=self._model_name,
                model_version=self._model_version,
                feature_variant=self._feature_variant,
            )

        # Step 3 — Feature engineering (transform only — never fit on inference data)
        raw_df = pd.DataFrame([application])
        try:
            engineered_df = self._engineer.transform(raw_df)
        except Exception as exc:
            raise RuntimeError(
                f"Feature engineering failed for the submitted application: {exc}"
            ) from exc

        # Step 4 — Preprocessing (transform only — fitted on training data only)
        try:
            X_preprocessed = self._preprocessor.transform(engineered_df)
            # Align to exact 64-column model input order
            X_model = X_preprocessed[self._model.feature_names_in_]
        except Exception as exc:
            raise RuntimeError(
                f"Preprocessing failed for the submitted application: {exc}"
            ) from exc

        # Step 5 — Predict default probability
        prob_array = self._model.predict_proba(X_model)
        probability = float(np.asarray(prob_array).ravel()[0])

        # Step 6 + 7 + 8 — Explain (SHAP + plain language)
        explanation_factors = self._build_explanation(X_model, engineered_df)

        # Step 9 — Format structured response
        return OutputFormatter.format_scored(
            probability=probability,
            explanation_factors=explanation_factors,
            model_name=self._model_name,
            model_version=self._model_version,
            feature_variant=self._feature_variant,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_manifest(self) -> Dict[str, Any]:
        """Load and return the FINAL_MODEL.json manifest."""
        if not self._manifest_path.exists():
            raise FileNotFoundError(
                f"FINAL_MODEL.json not found at '{self._manifest_path}'. "
                "Ensure Phase 8 has been completed and the manifest is committed."
            )
        with open(self._manifest_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _build_fitted_pipeline(
        self,
    ) -> Tuple[FeatureEngineer, Any]:
        """Build a fitted FeatureEngineer + CreditRiskPreprocessor from the canonical dataset.

        Deterministically reproduces the training pipeline with seed=42 so that the
        fitted preprocessor parameters (medians, scaler stats, OHE categories) are
        identical to those used during model training.

        Returns:
            Tuple[FeatureEngineer, CreditRiskPreprocessor]: Both fitted on the training split.
        """
        logger.info(
            "Building fitted preprocessing pipeline from dataset: %s", self._dataset_path
        )
        if not self._dataset_path.exists():
            raise FileNotFoundError(
                f"Canonical dataset not found at '{self._dataset_path}'. "
                "Ensure Phase 2 synthetic data is present."
            )

        df = pd.read_parquet(self._dataset_path)

        # Deterministic 70/15/15 grouped split — seed=42, scored_only=True
        # (matches training protocol in all Phase 5/6 training scripts)
        split = GroupedDatasetSplitter.split(df, seed=DEFAULT_RANDOM_SEED, scored_only=True)

        # Suppress any sklearn/pandas warnings during fitting
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipeline_result = build_model_ready_matrices(
                train_df=split.train_df,
                variant=ExperimentVariant.VOLATILITY_AWARE,
                scaler_type="robust",
                add_missing_indicators=True,
                scored_only=True,
            )

        engineer: FeatureEngineer = pipeline_result["feature_engineer"]
        preprocessor = pipeline_result["preprocessor"]

        logger.info(
            "Pipeline built: %d training rows, %d output features.",
            len(split.train_df),
            len(preprocessor.feature_names_out_),
        )
        return engineer, preprocessor

    def _build_explanation(
        self,
        X_model: pd.DataFrame,
        engineered_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Generate plain-language explanation factors for a scored application.

        Args:
            X_model: 64-column, model-ready DataFrame row (post preprocessing).
            engineered_df: Single-row DataFrame after feature engineering (pre preprocessing).

        Returns:
            Dict from PlainLanguageExplainer.generate_borrower_explanation_summary.
        """
        if self._explainer is None:
            return {
                "key_protective_factors": [],
                "key_risk_factors": [],
                "disclaimer": (
                    "Explanation unavailable: the SHAP explainer could not be initialised "
                    "for this predictor session."
                ),
            }

        try:
            local_explanation = self._explainer.explain_instance(X_model, top_n=5)

            # Build contribution dicts expected by PlainLanguageExplainer
            contributions = [
                {
                    "feature": c.feature_name,
                    "attribution": c.attribution_value,
                    "value": c.feature_value,
                }
                for c in local_explanation.contributions
            ]

            explanation = PlainLanguageExplainer.generate_borrower_explanation_summary(
                contributions=contributions,
                top_k=4,
            )
            return explanation

        except Exception as exc:
            logger.warning(
                "SHAP explanation generation failed for this application (%s). "
                "Returning empty explanation.",
                exc,
            )
            return {
                "key_protective_factors": [],
                "key_risk_factors": [],
                "disclaimer": (
                    f"Explanation temporarily unavailable for this application ({type(exc).__name__}). "
                    "The risk score and tier remain valid."
                ),
            }
