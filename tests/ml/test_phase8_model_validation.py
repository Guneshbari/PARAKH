"""Automated test suite for Phase 8 — Final Model Validation & Selection.

Verifies:
1. Both candidate artifacts load successfully.
2. Exact test partition is reproduced with zero applicant leakage.
3. Expected test row count (1,698 scored) and default count (248) are verified.
4. Predicted probabilities are strictly bounded in [0.0, 1.0].
5. Required test metrics (ROC-AUC, PR-AUC, Brier, ECE, confusion matrix) are produced.
6. Calibration statistics (10 bins, ECE, MCE) are produced.
7. Cohort metrics for all 5 cohorts are produced.
8. Zero target, identifier, or post-t0 leakage into feature matrices.
9. Final model manifest (FINAL_MODEL.json) is valid and complete.
10. Final artifact reload produces identical bitwise predictions.
11. Test evaluation pipeline is deterministic.
"""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.features.feature_engineering import build_model_ready_matrices
from src.ml.models.base import BaseRiskModel
from src.ml.models.baseline import LogisticRegressionBaseline
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


@pytest.fixture(scope="module")
def canonical_dataset() -> pd.DataFrame:
    """Load canonical Phase 2 synthetic dataset."""
    path = Path("data/synthetic/synthetic_credit_applications.parquet")
    assert path.exists(), f"Canonical dataset not found at {path}"
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def dataset_splits(canonical_dataset: pd.DataFrame):
    """Generate grouped splits using frozen seed 42."""
    return GroupedDatasetSplitter.split(canonical_dataset, seed=DEFAULT_RANDOM_SEED)


@pytest.fixture(scope="module")
def baseline_artifact() -> LogisticRegressionBaseline:
    """Load Phase 5 baseline model artifact."""
    path = Path("models/artifacts/logistic_regression_baseline.joblib")
    assert path.exists(), f"Baseline artifact not found at {path}"
    model = joblib.load(path)
    return model


@pytest.fixture(scope="module")
def volatility_aware_artifact() -> VolatilityAwareRiskModel:
    """Load Phase 6 volatility-aware model artifact."""
    path = Path("models/artifacts/volatility_aware_risk_model.joblib")
    assert path.exists(), f"Volatility-aware artifact not found at {path}"
    model = joblib.load(path)
    return model


def test_both_candidate_artifacts_load(
    baseline_artifact: LogisticRegressionBaseline,
    volatility_aware_artifact: VolatilityAwareRiskModel,
):
    """Verify both candidate artifacts load and adhere to the BaseRiskModel contract."""
    assert isinstance(baseline_artifact, BaseRiskModel)
    assert isinstance(volatility_aware_artifact, BaseRiskModel)
    assert baseline_artifact.is_fitted
    assert volatility_aware_artifact.is_fitted

    assert len(baseline_artifact.feature_names_in_) == 35
    assert len(volatility_aware_artifact.feature_names_in_) == 64
    assert baseline_artifact.model_name == "baseline-logistic-regression"
    assert volatility_aware_artifact.model_name == "volatility-aware-risk-model"


def test_exact_test_partition_reproduced(dataset_splits):
    """Verify the Phase 3 grouped test partition is reproduced with zero leakage."""
    assert not dataset_splits.leakage_audit.leakage_detected

    train_apps = set(dataset_splits.train_df["applicant_profile_id"])
    val_apps = set(dataset_splits.val_df["applicant_profile_id"])
    test_apps = set(dataset_splits.test_df["applicant_profile_id"])

    assert len(train_apps.intersection(test_apps)) == 0, "Train-Test applicant leakage!"
    assert len(val_apps.intersection(test_apps)) == 0, "Val-Test applicant leakage!"
    assert len(train_apps.intersection(val_apps)) == 0, "Train-Val applicant leakage!"


def test_expected_test_row_and_default_counts(dataset_splits):
    """Verify test partition row counts, scored rows, and default counts match specification."""
    test_df = dataset_splits.test_df
    assert len(test_df) == 1785

    scored_test_df = test_df[test_df["target_default_flag"].notnull()]
    assert len(scored_test_df) == 1698

    insufficient_data_df = test_df[test_df["target_default_flag"].isnull()]
    assert len(insufficient_data_df) == 87

    defaults = scored_test_df["target_default_flag"].sum()
    assert int(defaults) == 248

    default_rate = defaults / len(scored_test_df)
    assert abs(default_rate - 0.146054) < 1e-4


def test_no_target_or_identifier_leakage(dataset_splits):
    """Verify target and identifier columns are quarantined and never enter model inputs."""
    matrices = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )
    X_test = matrices["X_test"]

    forbidden = [
        "applicant_profile_id",
        "application_id",
        "cutoff_timestamp",
        "cohort_archetype",
        "target_default_flag",
        "future_actual_defaults",
    ]
    for col in forbidden:
        assert col not in X_test.columns, f"Forbidden column '{col}' found in X_test!"


def test_predicted_probabilities_bounded(
    dataset_splits,
    baseline_artifact: LogisticRegressionBaseline,
    volatility_aware_artifact: VolatilityAwareRiskModel,
):
    """Verify predicted default probabilities for both models are strictly in [0.0, 1.0]."""
    mat_base = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )
    mat_vol = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    X_base = mat_base["X_test"][baseline_artifact.feature_names_in_]
    X_vol = mat_vol["X_test"][volatility_aware_artifact.feature_names_in_]

    p_base = baseline_artifact.predict_proba(X_base)
    p_vol = volatility_aware_artifact.predict_proba(X_vol)

    assert len(p_base) == 1698
    assert len(p_vol) == 1698
    assert np.all(p_base >= 0.0) and np.all(p_base <= 1.0)
    assert np.all(p_vol >= 0.0) and np.all(p_vol <= 1.0)


def test_required_test_metrics_produced():
    """Verify phase8_test_metrics.json contains all required metrics for both models."""
    path = Path("experiments/reports/phase8_test_metrics.json")
    assert path.exists(), f"Report file not found: {path}"

    with open(path, "r") as f:
        data = json.load(f)

    assert data["sample_count"] == 1698
    assert data["positive_count"] == 248

    for model_key in ["baseline_logistic_regression", "volatility_aware_lightgbm"]:
        assert model_key in data
        m = data[model_key]
        assert "roc_auc" in m and m["roc_auc"] > 0.90
        assert "pr_auc" in m and m["pr_auc"] > 0.80
        assert "brier_score" in m and m["brier_score"] < 0.10
        assert "expected_calibration_error" in m
        assert "threshold_0_5" in m
        t05 = m["threshold_0_5"]
        for metric in ["precision", "recall", "f1", "true_positives", "false_positives", "true_negatives", "false_negatives"]:
            assert metric in t05
        assert "threshold_sweep" in m
        assert len(m["threshold_sweep"]) >= 9


def test_calibration_statistics_produced():
    """Verify phase8_calibration.json contains 10 bins, ECE, and MCE for both models."""
    path = Path("experiments/reports/phase8_calibration.json")
    assert path.exists(), f"Calibration file not found: {path}"

    with open(path, "r") as f:
        data = json.load(f)

    for cal_key in ["baseline_calibration", "volatility_aware_calibration"]:
        assert cal_key in data
        c = data[cal_key]
        assert "brier_score" in c
        assert "expected_calibration_error" in c
        assert "maximum_calibration_error" in c
        assert "bins" in c
        assert len(c["bins"]) == 10
        for b in c["bins"]:
            assert "bin_index" in b
            assert "sample_count" in b
            assert "mean_predicted_prob" in b
            assert "empirical_fraction_positives" in b
            assert "absolute_error" in b


def test_cohort_metrics_produced():
    """Verify phase8_cohort_validation.json covers all 5 predefined cohorts."""
    path = Path("experiments/reports/phase8_cohort_validation.json")
    assert path.exists(), f"Cohort validation file not found: {path}"

    with open(path, "r") as f:
        data = json.load(f)

    expected_cohorts = {"Declining", "Healthy Volatile", "High Obligation", "Irregular", "Stable"}
    assert set(data["cohorts"].keys()) == expected_cohorts

    for c_name, c_data in data["cohorts"].items():
        assert c_data["sample_count"] > 0
        assert "default_count" in c_data
        assert "empirical_default_rate" in c_data
        assert "baseline_model" in c_data
        assert "volatility_aware_model" in c_data
        assert "deltas_volatility_minus_baseline" in c_data


def test_model_comparison_report_valid():
    """Verify phase8_model_comparison.json contains validation-to-test stability and deltas."""
    path = Path("experiments/reports/phase8_model_comparison.json")
    assert path.exists(), f"Model comparison file not found: {path}"

    with open(path, "r") as f:
        data = json.load(f)

    assert "model_comparison_on_test" in data
    assert "validation_to_test_stability" in data
    assert "hypothesis_evidence_on_test" in data


def test_test_predictions_parquet_valid():
    """Verify phase8_test_predictions.parquet has 1,698 scored rows and all required columns."""
    path = Path("experiments/reports/phase8_test_predictions.parquet")
    assert path.exists(), f"Parquet file not found: {path}"

    df = pd.read_parquet(path)
    assert len(df) == 1698
    required_cols = [
        "application_id",
        "applicant_profile_id",
        "cohort_archetype",
        "target_default_flag",
        "baseline_predicted_probability",
        "baseline_predicted_class_threshold_0_5",
        "baseline_risk_level",
        "baseline_presentation_score",
        "volatility_aware_predicted_probability",
        "volatility_aware_predicted_class_threshold_0_5",
        "volatility_aware_risk_level",
        "volatility_aware_presentation_score",
        "predicted_probability",
        "predicted_class_threshold_0_5",
        "risk_level",
        "presentation_score",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column '{col}' in test predictions parquet!"

    assert (df["predicted_probability"] >= 0.0).all() and (df["predicted_probability"] <= 1.0).all()
    assert (df["presentation_score"] >= 300).all() and (df["presentation_score"] <= 850).all()


def test_final_model_manifest_valid():
    """Verify models/artifacts/FINAL_MODEL.json contains all required schema keys."""
    path = Path("models/artifacts/FINAL_MODEL.json")
    assert path.exists(), f"Manifest file not found: {path}"

    with open(path, "r") as f:
        data = json.load(f)

    required_keys = [
        "selected_model_name",
        "model_class",
        "artifact_path",
        "model_version",
        "feature_variant",
        "feature_count",
        "training_commit",
        "selection_phase",
        "selection_timestamp",
        "required_preprocessing",
        "required_feature_engineering",
        "expected_input_schema",
        "expected_output_schema",
        "diagnostic_threshold",
        "production_threshold_status",
        "limitations",
    ]
    for key in required_keys:
        assert key in data, f"Missing key '{key}' in FINAL_MODEL.json"

    assert data["selected_model_name"] == "volatility-aware-risk-model"
    assert data["feature_variant"] == "VOLATILITY_AWARE"
    assert data["feature_count"] == 64
    assert Path(data["artifact_path"]).exists()


def test_final_artifact_reload_identical_predictions(dataset_splits):
    """Verify reloading the model artifact specified in FINAL_MODEL.json produces identical predictions."""
    with open("models/artifacts/FINAL_MODEL.json", "r") as f:
        manifest = json.load(f)

    artifact_path = manifest["artifact_path"]
    reloaded_model: VolatilityAwareRiskModel = joblib.load(artifact_path)

    mat_vol = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )
    X_test = mat_vol["X_test"][reloaded_model.feature_names_in_]

    preds1 = reloaded_model.predict_proba(X_test)
    preds2 = reloaded_model.predict_proba(X_test)

    np.testing.assert_array_equal(preds1, preds2)

    # Check parity with saved parquet predictions
    parquet_df = pd.read_parquet("experiments/reports/phase8_test_predictions.parquet")
    np.testing.assert_allclose(np.round(preds1, 4), parquet_df["predicted_probability"].values, atol=1e-5)


def test_deterministic_reproducibility(
    dataset_splits, volatility_aware_artifact: VolatilityAwareRiskModel
):
    """Verify deterministic predictability across independent calls."""
    mat_vol = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )
    X_test = mat_vol["X_test"][volatility_aware_artifact.feature_names_in_]

    p1 = volatility_aware_artifact.predict_proba(X_test)
    p2 = volatility_aware_artifact.predict_proba(X_test)

    np.testing.assert_array_equal(p1, p2)
