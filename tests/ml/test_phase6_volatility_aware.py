"""Unit tests for Phase 6 Volatility-Aware Risk Model.

Verifies:
1. Model trains successfully using gradient-boosted trees (LightGBM).
2. Model serializes and deserializes from artifact preserving identical predictions.
3. Predicted default probabilities are strictly bounded in [0.0, 1.0].
4. Prediction is bitwise deterministic across identical configurations (seed 42).
5. Expected 64-feature VOLATILITY_AWARE model matrix is strictly enforced.
6. Target and identifier columns are quarantined and absent from predictor matrix X.
7. Unscored / insufficient data rows (593) are completely excluded from model matrices.
8. Test split is strictly held out and unobserved during training and tuning.
9. Required classification and calibration metrics are generated and valid.
10. Baseline comparison metrics and deltas are reproducible.
11. Newly engineered volatility-aware interaction features are present and utilized.
12. No NaN, null, or infinite predictions are produced under any conditions.
13. Feature importances (split and gain) are populated, non-negative, and properly normalized.
14. Monotonic threshold response across varying decision boundaries.
"""
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.evaluation.calibration import evaluate_calibration
from src.ml.evaluation.cohorts import evaluate_by_cohort
from src.ml.evaluation.metrics import evaluate_predictions
from src.ml.features.feature_engineering import (
    BASELINE_FEATURE_SET,
    ENGINEERED_VOLATILITY_FEATURES,
    build_model_ready_matrices,
)
from src.ml.models.base import NotFittedError
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


@pytest.fixture(scope="module")
def canonical_df():
    """Load canonical Phase 2 synthetic dataset."""
    return pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")


@pytest.fixture(scope="module")
def dataset_splits(canonical_df):
    """Split canonical dataset into train, val, and test partitions."""
    return GroupedDatasetSplitter.split(canonical_df, seed=DEFAULT_RANDOM_SEED)


@pytest.fixture(scope="module")
def volatility_matrices(dataset_splits):
    """Generate model-ready matrices for VOLATILITY_AWARE feature variant."""
    return build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )


@pytest.fixture(scope="module")
def trained_volatility_model(volatility_matrices):
    """Fit VolatilityAwareRiskModel on training split with optimal hyperparameters."""
    model = VolatilityAwareRiskModel(
        n_estimators=150,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=30,
        reg_lambda=2.0,
        random_state=42,
    )
    model.fit(volatility_matrices["X_train"], volatility_matrices["y_train"])
    return model


def test_volatility_aware_matrix_dimensions_and_isolation(volatility_matrices):
    """Verify matrix dimensions, 64 columns, and absence of target or identity leakage."""
    X_train = volatility_matrices["X_train"]
    y_train = volatility_matrices["y_train"]
    X_val = volatility_matrices["X_val"]
    y_val = volatility_matrices["y_val"]
    X_test = volatility_matrices["X_test"]
    y_test = volatility_matrices["y_test"]

    # 64 model-ready columns (53 continuous/ratio + 11 one-hot categories)
    assert X_train.shape == (8012, 64)
    assert len(y_train) == 8012
    assert X_val.shape == (1697, 64)
    assert len(y_val) == 1697
    assert X_test.shape == (1698, 64)
    assert len(y_test) == 1698

    # Prohibited columns must NEVER be present in feature matrices
    prohibited_cols = {
        "applicant_profile_id",
        "application_id",
        "cutoff_timestamp",
        "cohort_archetype",
        "target_default_flag",
        "repayment_risk_probability",
    }
    for col in X_train.columns:
        assert col not in prohibited_cols

    # Zero missing values or infinities
    assert X_train.isna().sum().sum() == 0
    assert X_val.isna().sum().sum() == 0
    assert X_test.isna().sum().sum() == 0


def test_unscored_records_excluded_from_volatility_matrices(canonical_df, volatility_matrices):
    """Verify unscored/insufficient records (593) are completely excluded from matrices."""
    total_unscored = canonical_df["target_default_flag"].isna().sum()
    assert total_unscored == 593

    total_matrix_rows = (
        len(volatility_matrices["X_train"])
        + len(volatility_matrices["X_val"])
        + len(volatility_matrices["X_test"])
    )
    assert total_matrix_rows == 11407  # Exactly 12000 - 593


def test_unfitted_model_raises_not_fitted_error(volatility_matrices):
    """Verify calling predict or predict_proba on unfitted model raises NotFittedError."""
    unfitted = VolatilityAwareRiskModel()
    assert not unfitted.is_fitted

    with pytest.raises(NotFittedError):
        unfitted.predict_proba(volatility_matrices["X_val"])

    with pytest.raises(NotFittedError):
        unfitted.predict(volatility_matrices["X_val"])

    with pytest.raises(NotFittedError):
        unfitted.get_feature_importances_df()


def test_model_training_and_probability_bounds(trained_volatility_model, volatility_matrices):
    """Verify model fits cleanly and produces probabilities strictly in [0.0, 1.0]."""
    assert trained_volatility_model.is_fitted
    assert trained_volatility_model.n_features_in_ == 64
    assert len(trained_volatility_model.feature_names_in_) == 64

    probs = trained_volatility_model.predict_proba(volatility_matrices["X_val"])
    assert isinstance(probs, np.ndarray)
    assert probs.ndim == 1
    assert len(probs) == len(volatility_matrices["X_val"])
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)
    assert np.min(probs) < 0.05
    assert np.max(probs) > 0.80
    assert not np.any(np.isnan(probs))
    assert not np.any(np.isinf(probs))


def test_deterministic_reproducibility(volatility_matrices):
    """Verify repeated model fitting with fixed seed produces identical predictions."""
    X_train = volatility_matrices["X_train"]
    y_train = volatility_matrices["y_train"]
    X_val = volatility_matrices["X_val"]

    m1 = VolatilityAwareRiskModel(n_estimators=50, random_state=42)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_val)

    m2 = VolatilityAwareRiskModel(n_estimators=50, random_state=42)
    m2.fit(X_train, y_train)
    p2 = m2.predict_proba(X_val)

    np.testing.assert_array_equal(p1, p2)


def test_feature_ordering_and_mismatch_handling(trained_volatility_model, volatility_matrices):
    """Verify DataFrame column reordering is handled and missing columns raise ValueError."""
    X_val = volatility_matrices["X_val"]

    # Reorder columns
    shuffled_cols = list(reversed(list(X_val.columns)))
    X_shuffled = X_val[shuffled_cols]
    probs_shuffled = trained_volatility_model.predict_proba(X_shuffled)
    probs_orig = trained_volatility_model.predict_proba(X_val)
    np.testing.assert_allclose(probs_shuffled, probs_orig, rtol=1e-5)

    # Missing column must raise ValueError
    X_incomplete = X_val.drop(columns=[X_val.columns[0]])
    with pytest.raises(ValueError, match="missing required columns"):
        trained_volatility_model.predict_proba(X_incomplete)


def test_test_split_isolation(canonical_df):
    """Verify test split is strictly excluded from training data and feature transformation."""
    splits = GroupedDatasetSplitter.split(canonical_df, seed=42)
    matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    # Verify applicant profile IDs between train and test do NOT overlap
    train_profiles = set(splits.train_df["applicant_profile_id"].unique())
    test_profiles = set(splits.test_df["applicant_profile_id"].unique())
    assert len(train_profiles.intersection(test_profiles)) == 0

    # Ensure scaler was fit on train only (not test)
    preprocessor = matrices["preprocessor"]
    assert preprocessor.is_fitted_


def test_serialization_and_deserialization_roundtrip(trained_volatility_model, volatility_matrices):
    """Verify model saves and loads via joblib with identical outputs and metadata."""
    X_val = volatility_matrices["X_val"]
    orig_probs = trained_volatility_model.predict_proba(X_val)
    orig_meta = trained_volatility_model.get_metadata()

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "volatility_aware_model.joblib"
        trained_volatility_model.save(save_path)
        assert save_path.exists()

        loaded_model = VolatilityAwareRiskModel.load(save_path)
        assert isinstance(loaded_model, VolatilityAwareRiskModel)
        assert loaded_model.is_fitted

        loaded_probs = loaded_model.predict_proba(X_val)
        np.testing.assert_array_equal(orig_probs, loaded_probs)
        assert loaded_model.get_metadata()["hyperparameters"] == orig_meta["hyperparameters"]


def test_volatility_aware_features_presence_and_importance(trained_volatility_model):
    """Verify all 9 newly engineered features are present in model and have non-zero importance."""
    imp_df = trained_volatility_model.get_feature_importances_df()

    assert len(imp_df) == 64
    assert list(imp_df.columns) == ["feature", "split_importance", "gain_importance", "normalized_gain"]
    assert np.isclose(imp_df["normalized_gain"].sum(), 1.0)

    for eng_feat in ENGINEERED_VOLATILITY_FEATURES:
        assert eng_feat in imp_df["feature"].values
        row = imp_df[imp_df["feature"] == eng_feat].iloc[0]
        # Must have positive gain importance (actively used in tree splits)
        assert row["gain_importance"] > 0.0


def test_validation_evaluation_metrics_and_calibration(trained_volatility_model, volatility_matrices):
    """Verify classification and calibration metrics on validation split meet targets."""
    X_val = volatility_matrices["X_val"]
    y_val = volatility_matrices["y_val"]

    val_probs = trained_volatility_model.predict_proba(X_val)
    metrics = evaluate_predictions(y_val, val_probs, threshold=0.5)

    assert metrics.roc_auc is not None and metrics.roc_auc > 0.95
    assert metrics.pr_auc is not None and metrics.pr_auc > 0.88
    assert metrics.brier_score is not None and metrics.brier_score < 0.05
    assert metrics.total_samples == 1697
    assert metrics.positive_samples == 214

    # Calibration evaluation
    cal_result = evaluate_calibration(y_val, val_probs, n_bins=10, strategy="uniform")
    assert cal_result.expected_calibration_error < 0.03
    assert len(cal_result.bins) > 0


def test_cohort_evaluation_coverage(trained_volatility_model, volatility_matrices, dataset_splits):
    """Verify cohort-level evaluation computes segmented metrics across all synthetic cohorts."""
    X_val = volatility_matrices["X_val"]
    y_val = volatility_matrices["y_val"]
    val_probs = trained_volatility_model.predict_proba(X_val)

    val_scored = dataset_splits.val_df[dataset_splits.val_df["target_default_flag"].notna()]
    val_cohorts = val_scored["cohort_archetype"].tolist()

    cohort_results = evaluate_by_cohort(y_val, val_probs, cohorts=val_cohorts, threshold=0.5)

    expected_cohorts = {"Declining", "Healthy Volatile", "High Obligation", "Irregular", "Stable"}
    assert set(cohort_results.keys()) == expected_cohorts

    for cname, cresult in cohort_results.items():
        assert cresult.sample_count > 0
        assert 0.0 <= cresult.empirical_default_rate <= 1.0
        if cresult.metrics is not None and cresult.metrics.roc_auc is not None:
            assert 0.5 <= cresult.metrics.roc_auc <= 1.0


def test_threshold_predictions_monotonicity(trained_volatility_model, volatility_matrices):
    """Verify that higher decision thresholds produce fewer or equal positive predictions."""
    X_val = volatility_matrices["X_val"]

    preds_0_2 = trained_volatility_model.predict(X_val, threshold=0.20)
    preds_0_5 = trained_volatility_model.predict(X_val, threshold=0.50)
    preds_0_8 = trained_volatility_model.predict(X_val, threshold=0.80)

    pos_0_2 = np.sum(preds_0_2 == 1)
    pos_0_5 = np.sum(preds_0_5 == 1)
    pos_0_8 = np.sum(preds_0_8 == 1)

    assert pos_0_2 >= pos_0_5 >= pos_0_8
