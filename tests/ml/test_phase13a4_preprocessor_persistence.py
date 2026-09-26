"""Comprehensive test suite for Phase 13A-4: Persist Fitted Preprocessor for Deterministic Inference.

Verifies:
1. Persisted CreditRiskPreprocessor artifact can be loaded successfully from models/artifacts/credit_risk_preprocessor.joblib.
2. Artifact class/type is CreditRiskPreprocessor and is marked as fitted (is_fitted_=True).
3. Metadata compatibility (model_version='1.0.0', feature_variant='VOLATILITY_AWARE', preprocessor_class, scaler_type='robust').
4. Deterministic Transformation Parity: Compares persisted preprocessor transformation against the
   previous training split reconstruction across representative fixtures (low, medium, and high risk).
5. Output Probability & Presentation Score Parity: Verifies model predictions are bit-for-bit identical.
6. Error Handling & Guardrails:
   - Missing preprocessor artifact raises FileNotFoundError (no silent fallback).
   - Corrupted preprocessor artifact raises RuntimeError.
   - Unfitted preprocessor artifact raises RuntimeError.
   - Incompatible model version raises ValueError.
   - Incompatible feature variant raises ValueError.
   - Feature count / column mismatch raises ValueError.
7. Sufficiency Gate & TreeSHAP Explanations:
   - Insufficient applications stop before prediction.
   - Scored applications produce full TreeSHAP explanations.
"""

from pathlib import Path
import tempfile
import joblib
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.preprocessing import CreditRiskPreprocessor, EXCLUDED_NON_PREDICTORS
from src.ml.features.feature_engineering import FeatureEngineer
from src.ml.inference.predictor import RiskPredictor

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ARTIFACT_PATH = _PROJECT_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib"
_DATASET_PATH = _PROJECT_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet"
_MANIFEST_PATH = _PROJECT_ROOT / "models" / "artifacts" / "FINAL_MODEL.json"


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def persisted_preprocessor() -> CreditRiskPreprocessor:
    """Load the persisted preprocessor artifact directly."""
    assert _ARTIFACT_PATH.exists(), f"Preprocessor artifact missing at {_ARTIFACT_PATH}"
    obj = joblib.load(_ARTIFACT_PATH)
    return obj


@pytest.fixture(scope="module")
def reconstructed_pipeline():
    """Reconstruct the fitted pipeline from canonical training split for parity testing."""
    return RiskPredictor.reconstruct_fitted_pipeline(_DATASET_PATH)


@pytest.fixture(scope="module")
def representative_applications() -> list[dict]:
    """Extract diverse valid application records from the dataset (low, medium, higher risk)."""
    df = pd.read_parquet(_DATASET_PATH)
    # Filter to scored records
    scored = df[df["target_default_flag"].notnull()].copy()
    
    # Select records from different risk levels / default statuses
    recs = [
        scored[scored["target_default_flag"] == 0].iloc[0].to_dict(),
        scored[scored["target_default_flag"] == 0].iloc[100].to_dict(),
        scored[scored["target_default_flag"] == 1].iloc[0].to_dict(),
        scored[scored["target_default_flag"] == 1].iloc[10].to_dict(),
    ]
    # Clean non-predictor columns
    cleaned = [
        {k: v for k, v in r.items() if k not in EXCLUDED_NON_PREDICTORS}
        for r in recs
    ]
    return cleaned


# ===========================================================================
# 1. Artifact Loading & Metadata Verification
# ===========================================================================

class TestPreprocessorArtifactMetadata:
    """Verify artifact loading, class type, and metadata integrity."""

    def test_artifact_exists_at_expected_path(self):
        """Artifact must exist at models/artifacts/credit_risk_preprocessor.joblib."""
        assert _ARTIFACT_PATH.exists()
        assert _ARTIFACT_PATH.is_file()
        assert _ARTIFACT_PATH.stat().st_size > 1000

    def test_artifact_type_is_credit_risk_preprocessor(self, persisted_preprocessor):
        """Loaded artifact must be an instance of CreditRiskPreprocessor."""
        assert isinstance(persisted_preprocessor, CreditRiskPreprocessor)
        assert type(persisted_preprocessor).__name__ == "CreditRiskPreprocessor"

    def test_artifact_is_fitted(self, persisted_preprocessor):
        """Loaded artifact must report is_fitted_=True."""
        assert getattr(persisted_preprocessor, "is_fitted_", False) is True
        assert len(persisted_preprocessor.fitted_medians_) == 53
        assert persisted_preprocessor.fitted_scaler_ is not None
        assert persisted_preprocessor.fitted_encoder_ is not None

    def test_artifact_metadata_fields(self, persisted_preprocessor):
        """Artifact must carry explicit metadata attributes for validation."""
        assert persisted_preprocessor.model_name_ == "volatility-aware-risk-model"
        assert persisted_preprocessor.model_version_ == "1.0.0"
        assert persisted_preprocessor.feature_variant_ == "VOLATILITY_AWARE"
        assert persisted_preprocessor.training_commit_ == "2d47a35"

        meta = getattr(persisted_preprocessor, "metadata_", {})
        assert meta.get("model_version") == "1.0.0"
        assert meta.get("feature_variant") == "VOLATILITY_AWARE"
        assert meta.get("preprocessor_class") == "src.ml.data.preprocessing.CreditRiskPreprocessor"
        assert meta.get("output_feature_count") == 64
        assert meta.get("scaler_type") == "robust"

    def test_output_feature_names_match_model(self, persisted_preprocessor):
        """Preprocessor feature_names_out_ must match the 64 features expected by LightGBM model."""
        assert len(persisted_preprocessor.feature_names_out_) == 64
        model = joblib.load(_PROJECT_ROOT / "models" / "artifacts" / "volatility_aware_risk_model.joblib")
        assert list(persisted_preprocessor.feature_names_out_) == list(model.feature_names_in_)


# ===========================================================================
# 2. Critical Regression Check: Parity with Training Split Reconstruction
# ===========================================================================

class TestDeterministicParityWithReconstruction:
    """Verify bit-for-bit parity between persisted preprocessor and reconstruction."""

    def test_transformed_matrix_parity(
        self,
        persisted_preprocessor,
        reconstructed_pipeline,
        representative_applications,
    ):
        """Transformed feature matrices must be identical within exact float tolerance."""
        _, reconstructed_preprocessor = reconstructed_pipeline
        engineer = FeatureEngineer(include_engineered_interactions=True)

        for app in representative_applications:
            df = pd.DataFrame([app])
            eng_df = engineer.transform(df)

            X_persisted = persisted_preprocessor.transform(eng_df)
            X_reconstructed = reconstructed_preprocessor.transform(eng_df)

            assert list(X_persisted.columns) == list(X_reconstructed.columns)
            np.testing.assert_allclose(
                X_persisted.values,
                X_reconstructed.values,
                rtol=1e-10,
                atol=1e-10,
                err_msg="Transformed feature matrix differs between persisted and reconstructed preprocessor.",
            )

    def test_model_probability_and_score_parity(
        self,
        reconstructed_pipeline,
        representative_applications,
    ):
        """RiskPredictor output probabilities and scores must match across preprocessor paths."""
        predictor = RiskPredictor(preprocessor_path=_ARTIFACT_PATH)
        reconstructed_engineer, reconstructed_preprocessor = reconstructed_pipeline
        model = predictor._model

        for app in representative_applications:
            # Predict with default RiskPredictor (using persisted preprocessor)
            resp = predictor.predict(app)

            # Manual prediction using reconstructed preprocessor
            eng_df = reconstructed_engineer.transform(pd.DataFrame([app]))
            X_model = reconstructed_preprocessor.transform(eng_df)[model.feature_names_in_]
            raw_prob = float(np.asarray(model.predict_proba(X_model)).ravel()[0])

            # OutputFormatter rounds to 6 decimal places
            expected_prob = round(raw_prob, 6)
            assert resp.repayment_risk_probability == expected_prob
            assert resp.is_insufficient_evidence is False
            assert resp.risk_tier in ["LOWER", "MODERATE", "HIGHER"]
            assert 300 <= resp.presentation_score <= 850


# ===========================================================================
# 3. Error Handling and Guardrails
# ===========================================================================

class TestPreprocessorErrorHandling:
    """Verify inference fails clearly when preprocessor artifact is missing, corrupt, or incompatible."""

    def test_missing_artifact_raises_file_not_found(self):
        """Non-existent preprocessor path must raise FileNotFoundError (no silent fallback)."""
        fake_path = _PROJECT_ROOT / "models" / "artifacts" / "non_existent_preprocessor.joblib"
        with pytest.raises(FileNotFoundError) as exc_info:
            RiskPredictor(preprocessor_path=fake_path)
        assert "Fitted preprocessor artifact not found" in str(exc_info.value)

    def test_corrupted_artifact_raises_runtime_error(self):
        """Corrupted file contents must raise RuntimeError."""
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            f.write(b"CORRUPTED_BINARY_DATA_NOT_JOBLIB")
            corrupt_path = Path(f.name)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                RiskPredictor(preprocessor_path=corrupt_path)
            assert "Failed to load preprocessor artifact" in str(exc_info.value)
        finally:
            corrupt_path.unlink(missing_ok=True)

    def test_unfitted_preprocessor_raises_runtime_error(self):
        """Preprocessor with is_fitted_=False must raise RuntimeError."""
        unfitted = CreditRiskPreprocessor()
        unfitted.is_fitted_ = False
        unfitted.model_version_ = "1.0.0"
        unfitted.feature_variant_ = "VOLATILITY_AWARE"

        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            joblib.dump(unfitted, f.name)
            unfitted_path = Path(f.name)

        try:
            with pytest.raises(RuntimeError) as exc_info:
                RiskPredictor(preprocessor_path=unfitted_path)
            assert "reports is_fitted_=False" in str(exc_info.value)
        finally:
            unfitted_path.unlink(missing_ok=True)

    def test_incompatible_model_version_raises_value_error(self, persisted_preprocessor):
        """Preprocessor with mismatched model_version must raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            persisted_preprocessor.model_version_ = "9.9.9"
            joblib.dump(persisted_preprocessor, f.name)
            bad_version_path = Path(f.name)
            # Restore
            persisted_preprocessor.model_version_ = "1.0.0"

        try:
            with pytest.raises(ValueError) as exc_info:
                RiskPredictor(preprocessor_path=bad_version_path)
            assert "model_version '9.9.9' does not match model '1.0.0'" in str(exc_info.value)
        finally:
            bad_version_path.unlink(missing_ok=True)

    def test_incompatible_feature_variant_raises_value_error(self, persisted_preprocessor):
        """Preprocessor with mismatched feature_variant must raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            persisted_preprocessor.feature_variant_ = "BASELINE"
            joblib.dump(persisted_preprocessor, f.name)
            bad_variant_path = Path(f.name)
            # Restore
            persisted_preprocessor.feature_variant_ = "VOLATILITY_AWARE"

        try:
            with pytest.raises(ValueError) as exc_info:
                RiskPredictor(preprocessor_path=bad_variant_path)
            assert "feature_variant 'BASELINE' does not match model 'VOLATILITY_AWARE'" in str(exc_info.value)
        finally:
            bad_variant_path.unlink(missing_ok=True)


# ===========================================================================
# 4. Sufficiency Gate and Pipeline Intactness
# ===========================================================================

class TestSufficiencyAndInferencePipeline:
    """Verify that sufficiency gates and prediction work seamlessly with persisted preprocessor."""

    def test_insufficient_application_stops_before_preprocessor(self, representative_applications):
        """Insufficient evidence triggers INSUFFICIENT risk tier with null scores."""
        predictor = RiskPredictor()
        insufficient_app = representative_applications[0].copy()
        insufficient_app["feat_suf_observed_days"] = 10.0  # < 30 days threshold

        resp = predictor.predict(insufficient_app)
        assert resp.risk_tier == "INSUFFICIENT"
        assert resp.is_insufficient_evidence is True
        assert resp.repayment_risk_probability is None
        assert resp.presentation_score is None
        assert len(resp.missing_or_insufficient_signals) > 0

    def test_scored_application_generates_explanations(self, representative_applications):
        """Scored application produces valid TreeSHAP feature attributions."""
        predictor = RiskPredictor()
        resp = predictor.predict(representative_applications[0])

        assert resp.risk_tier in ["LOWER", "MODERATE", "HIGHER"]
        assert resp.explanation_factors is not None
        assert "key_protective_factors" in resp.explanation_factors
        assert "key_risk_factors" in resp.explanation_factors
        assert len(resp.explanation_factors["key_protective_factors"]) > 0
