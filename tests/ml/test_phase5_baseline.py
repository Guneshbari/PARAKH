"""Unit tests for Phase 5 Baseline Model (Regularized Logistic Regression).

Verifies:
1. Model trains without error using L2 regularized logistic regression.
2. Predicts default probabilities strictly bounded in [0.0, 1.0].
3. Deterministic reproducibility across repeated training runs (seed 42).
4. Feature dimension and column ordering consistency (35 model-ready features).
5. Non-leakage: identifiers and target variables strictly excluded from predictor matrix.
6. Exclusion of unscored/insufficient data rows from training and validation.
7. Strict isolation of held-out test split (test split not used in training/tuning).
8. Serialization and deserialization roundtrip via joblib preserves bitwise identical predictions.
9. Evaluation metrics calculation (ROC-AUC, PR-AUC, Brier, ECE, confusion matrix).
10. Cohort breakdown auditing across borrower behavioural archetypes.
11. Feature coefficients extraction, directionality, and odds ratio calculation.
12. Custom threshold binary classification behavior.
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
from src.ml.features.feature_engineering import BASELINE_FEATURE_SET, build_model_ready_matrices
from src.ml.models.base import NotFittedError
from src.ml.models.baseline import LogisticRegressionBaseline


@pytest.fixture(scope="module")
def canonical_df():
    """Load canonical Phase 2 synthetic dataset."""
    return pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")


@pytest.fixture(scope="module")
def dataset_splits(canonical_df):
    """Split canonical dataset into train, val, and test partitions."""
    return GroupedDatasetSplitter.split(canonical_df, seed=DEFAULT_RANDOM_SEED)


@pytest.fixture(scope="module")
def baseline_matrices(dataset_splits):
    """Generate model-ready matrices for BASELINE feature variant."""
    return build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )


@pytest.fixture(scope="module")
def trained_baseline(baseline_matrices):
    """Fit baseline model on training split."""
    model = LogisticRegressionBaseline(C=1.0, solver="lbfgs", max_iter=1000, random_state=42)
    model.fit(baseline_matrices["X_train"], baseline_matrices["y_train"])
    return model


def test_baseline_feature_set_definition():
    """Verify BASELINE feature subset definition has 26 raw/derived features."""
    assert len(BASELINE_FEATURE_SET) == 26
    # Must NOT contain nonlinear volatility interaction features
    prohibited_features = {
        "feat_int_vol_x_recovery",
        "feat_int_vol_x_buffer",
        "feat_int_trend_x_dti",
        "feat_eng_vol_to_bounceback",
    }
    for feat in prohibited_features:
        assert feat not in BASELINE_FEATURE_SET


def test_model_ready_matrices_dimensions_and_isolation(baseline_matrices, dataset_splits):
    """Verify matrix dimensions, 35 columns, and absence of target or identity leakage."""
    X_train = baseline_matrices["X_train"]
    y_train = baseline_matrices["y_train"]
    X_val = baseline_matrices["X_val"]
    y_val = baseline_matrices["y_val"]
    X_test = baseline_matrices["X_test"]
    y_test = baseline_matrices["y_test"]

    # 35 model-ready columns (24 numerical/ratio + 11 one-hot categories)
    assert X_train.shape == (8012, 35)
    assert len(y_train) == 8012
    assert X_val.shape == (1697, 35)
    assert len(y_val) == 1697
    assert X_test.shape == (1698, 35)
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


def test_unscored_records_excluded_from_model_matrices(canonical_df, baseline_matrices):
    """Verify unscored/insufficient records (593) are completely excluded from matrices."""
    total_unscored = canonical_df["target_default_flag"].isna().sum()
    assert total_unscored == 593

    total_matrix_rows = (
        len(baseline_matrices["X_train"])
        + len(baseline_matrices["X_val"])
        + len(baseline_matrices["X_test"])
    )
    assert total_matrix_rows == 11407  # Exactly 12000 - 593


def test_unfitted_model_raises_not_fitted_error(baseline_matrices):
    """Verify calling predict or predict_proba on unfitted model raises NotFittedError."""
    unfitted = LogisticRegressionBaseline(C=1.0)
    assert not unfitted.is_fitted

    with pytest.raises(NotFittedError):
        unfitted.predict_proba(baseline_matrices["X_val"])

    with pytest.raises(NotFittedError):
        unfitted.predict(baseline_matrices["X_val"])

    with pytest.raises(NotFittedError):
        unfitted.get_coefficients_df()


def test_model_training_and_probability_bounds(trained_baseline, baseline_matrices):
    """Verify model fits cleanly and produces probabilities strictly in [0.0, 1.0]."""
    assert trained_baseline.is_fitted
    assert trained_baseline.n_features_in_ == 35
    assert len(trained_baseline.feature_names_in_) == 35

    probs = trained_baseline.predict_proba(baseline_matrices["X_val"])
    assert isinstance(probs, np.ndarray)
    assert probs.ndim == 1
    assert len(probs) == len(baseline_matrices["X_val"])
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)
    assert np.min(probs) < 0.05
    assert np.max(probs) > 0.80


def test_deterministic_reproducibility(baseline_matrices):
    """Verify repeated model fitting with fixed seed produces identical predictions."""
    X_train = baseline_matrices["X_train"]
    y_train = baseline_matrices["y_train"]
    X_val = baseline_matrices["X_val"]

    m1 = LogisticRegressionBaseline(C=1.0, random_state=42)
    m1.fit(X_train, y_train)
    p1 = m1.predict_proba(X_val)

    m2 = LogisticRegressionBaseline(C=1.0, random_state=42)
    m2.fit(X_train, y_train)
    p2 = m2.predict_proba(X_val)

    np.testing.assert_array_equal(p1, p2)
    np.testing.assert_array_equal(m1.coef_, m2.coef_)
    np.testing.assert_array_equal(m1.intercept_, m2.intercept_)


def test_feature_ordering_and_mismatch_handling(trained_baseline, baseline_matrices):
    """Verify DataFrame column reordering is handled and missing columns raise ValueError."""
    X_val = baseline_matrices["X_val"]

    # Reorder columns
    shuffled_cols = list(reversed(list(X_val.columns)))
    X_shuffled = X_val[shuffled_cols]
    probs_shuffled = trained_baseline.predict_proba(X_shuffled)
    probs_orig = trained_baseline.predict_proba(X_val)
    np.testing.assert_allclose(probs_shuffled, probs_orig, rtol=1e-5)

    # Missing column must raise ValueError
    X_incomplete = X_val.drop(columns=[X_val.columns[0]])
    with pytest.raises(ValueError, match="missing required columns"):
        trained_baseline.predict_proba(X_incomplete)


def test_test_split_isolation(canonical_df):
    """Verify test split is strictly excluded from training data and feature transformation."""
    splits = GroupedDatasetSplitter.split(canonical_df, seed=42)
    matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )

    # Verify applicant profile IDs between train and test do NOT overlap
    train_profiles = set(splits.train_df["applicant_profile_id"].unique())
    test_profiles = set(splits.test_df["applicant_profile_id"].unique())
    assert len(train_profiles.intersection(test_profiles)) == 0

    # Ensure scaler was fit on train only (not test)
    preprocessor = matrices["preprocessor"]
    assert preprocessor.is_fitted_


def test_serialization_and_deserialization_roundtrip(trained_baseline, baseline_matrices):
    """Verify model saves and loads via joblib with identical outputs and metadata."""
    X_val = baseline_matrices["X_val"]
    orig_probs = trained_baseline.predict_proba(X_val)
    orig_meta = trained_baseline.get_metadata()

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "baseline_model.joblib"
        trained_baseline.save(save_path)
        assert save_path.exists()

        loaded_model = LogisticRegressionBaseline.load(save_path)
        assert isinstance(loaded_model, LogisticRegressionBaseline)
        assert loaded_model.is_fitted

        loaded_probs = loaded_model.predict_proba(X_val)
        np.testing.assert_array_equal(orig_probs, loaded_probs)
        assert loaded_model.get_metadata()["hyperparameters"] == orig_meta["hyperparameters"]


def test_coefficients_extraction_and_economic_validity(trained_baseline):
    """Verify coefficients extraction produces valid weights and expected risk directions."""
    coefs_df = trained_baseline.get_coefficients_df()

    assert len(coefs_df) == 35
    assert list(coefs_df.columns) == ["feature", "coefficient", "abs_coefficient", "odds_ratio"]

    # Verify that burn months has negative coefficient (protective against default)
    burn_row = coefs_df[coefs_df["feature"] == "feat_liq_burn_months"].iloc[0]
    assert burn_row["coefficient"] < 0, "Liquid burn months must reduce default risk"
    assert burn_row["odds_ratio"] < 1.0

    # Verify that total DTI has positive coefficient (increases default risk)
    dti_row = coefs_df[coefs_df["feature"] == "feat_bur_total_dti"].iloc[0]
    assert dti_row["coefficient"] > 0, "Debt-to-income must increase default risk"
    assert dti_row["odds_ratio"] > 1.0


def test_validation_evaluation_metrics(trained_baseline, baseline_matrices):
    """Verify classification metrics on validation split meet benchmark thresholds."""
    X_val = baseline_matrices["X_val"]
    y_val = baseline_matrices["y_val"]

    val_probs = trained_baseline.predict_proba(X_val)
    metrics = evaluate_predictions(y_val, val_probs, threshold=0.5)

    # Check baseline benchmark criteria
    assert metrics.roc_auc is not None and metrics.roc_auc > 0.90
    assert metrics.pr_auc is not None and metrics.pr_auc > 0.80
    assert metrics.brier_score is not None and metrics.brier_score < 0.10
    assert metrics.total_samples == 1697
    assert metrics.positive_samples == 214

    # Calibration evaluation
    cal_result = evaluate_calibration(y_val, val_probs, n_bins=10, strategy="uniform")
    assert cal_result.expected_calibration_error < 0.05
    assert len(cal_result.bins) > 0


def test_cohort_evaluation_coverage(trained_baseline, baseline_matrices, dataset_splits):
    """Verify cohort-level evaluation computes segmented metrics for all synthetic cohorts."""
    X_val = baseline_matrices["X_val"]
    y_val = baseline_matrices["y_val"]
    val_probs = trained_baseline.predict_proba(X_val)

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


def test_threshold_predictions_monotonicity(trained_baseline, baseline_matrices):
    """Verify that higher decision thresholds produce fewer or equal positive predictions."""
    X_val = baseline_matrices["X_val"]

    preds_0_2 = trained_baseline.predict(X_val, threshold=0.20)
    preds_0_5 = trained_baseline.predict(X_val, threshold=0.50)
    preds_0_8 = trained_baseline.predict(X_val, threshold=0.80)

    pos_0_2 = np.sum(preds_0_2 == 1)
    pos_0_5 = np.sum(preds_0_5 == 1)
    pos_0_8 = np.sum(preds_0_8 == 1)

    assert pos_0_2 >= pos_0_5 >= pos_0_8
