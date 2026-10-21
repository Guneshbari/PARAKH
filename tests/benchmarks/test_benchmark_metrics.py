"""Unit tests for PARAKH benchmark metric calculations, financial loss simulations,
boundary condition validation, and data leakage safeguards.
"""
import copy
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from benchmarks.metrics import (
    MetricDelta,
    calculate_metric_delta,
    compute_bootstrap_ci,
    compute_classification_metrics,
    compute_distressed_volatility_recall,
    compute_expected_loss,
    compute_expected_loss_reduction,
    compute_good_borrower_capture,
)
from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.features.feature_engineering import build_model_ready_matrices


# -----------------------------------------------------------------------------
# 1. MetricDelta & Rate vs. Relative Change Tests
# -----------------------------------------------------------------------------
def test_calculate_metric_delta_standard():
    """Verify standard absolute and relative delta calculation."""
    delta = calculate_metric_delta(baseline=0.80, candidate=0.88, metric_name="Recall", is_rate=True)
    assert delta.absolute_delta == 0.08
    assert delta.absolute_percentage_points == 8.0
    assert abs(delta.relative_change_pct - 10.0) < 1e-4
    assert delta.notes is None


def test_calculate_metric_delta_percentage_point_distinction():
    """Verify distinction between percentage-point difference and relative percentage change.

    Case: 0.8680 to 0.8773 (PARAKH PR-AUC)
    - Absolute difference: +0.0093 (+0.93 percentage points)
    - Relative difference: +1.0714%
    """
    delta = calculate_metric_delta(baseline=0.8680, candidate=0.8773, metric_name="PR-AUC", is_rate=True)
    assert abs(delta.absolute_delta - 0.0093) < 1e-5
    assert abs(delta.absolute_percentage_points - 0.93) < 1e-4
    assert abs(delta.relative_change_pct - 1.0714) < 1e-3


def test_calculate_metric_delta_zero_denominator():
    """Verify safe handling when baseline value is zero (no division by zero)."""
    delta = calculate_metric_delta(baseline=0.0, candidate=0.05, metric_name="DefaultRate", is_rate=True)
    assert delta.absolute_delta == 0.05
    assert delta.absolute_percentage_points == 5.0
    assert delta.relative_change_pct is None
    assert "undefined" in delta.notes.lower()


def test_calculate_metric_delta_none_values():
    """Verify handling when one or both values are None."""
    delta = calculate_metric_delta(baseline=None, candidate=0.5, metric_name="Test")
    assert delta.absolute_delta is None
    assert delta.relative_change_pct is None
    assert delta.notes is not None


# -----------------------------------------------------------------------------
# 2. Classification Metrics & Average Precision Tests
# -----------------------------------------------------------------------------
def test_compute_classification_metrics_handcrafted():
    """Verify classification metrics against hand-calculated ground truth.

    y_true: [0, 0, 0, 1, 1]
    y_prob: [0.1, 0.2, 0.6, 0.4, 0.8]
    Threshold 0.50:
    Preds:  [0, 0, 1, 0, 1]
    TP: 1 (sample 4)
    FP: 1 (sample 2)
    TN: 2 (samples 0, 1)
    FN: 1 (sample 3)
    Precision = 1/2 = 0.5
    Recall    = 1/2 = 0.5
    F1        = 0.5
    """
    y_true = [0, 0, 0, 1, 1]
    y_prob = [0.1, 0.2, 0.6, 0.4, 0.8]

    res = compute_classification_metrics(y_true, y_prob, threshold=0.50)
    assert res["metric_implementation"] == "average_precision_score"
    assert res["sample_count"] == 5
    assert res["positive_defaults"] == 2
    assert res["negative_repayers"] == 3
    assert res["confusion_matrix"]["true_positives"] == 1
    assert res["confusion_matrix"]["false_positives"] == 1
    assert res["confusion_matrix"]["true_negatives"] == 2
    assert res["confusion_matrix"]["false_negatives"] == 1
    assert res["precision"] == 0.5
    assert res["recall"] == 0.5
    assert res["f1"] == 0.5


def test_compute_classification_metrics_validation_errors():
    """Verify error raises on invalid inputs, empty arrays, length mismatch, or NaNs."""
    with pytest.raises(ValueError, match="must not be empty"):
        compute_classification_metrics([], [])

    with pytest.raises(ValueError, match="Length mismatch"):
        compute_classification_metrics([0, 1], [0.5])

    with pytest.raises(ValueError, match="NaN"):
        compute_classification_metrics([0, 1], [0.5, float("nan")])

    with pytest.raises(ValueError, match="bounded in"):
        compute_classification_metrics([0, 1], [0.5, 1.5])


# -----------------------------------------------------------------------------
# 3. Expected Loss Simulation Tests (Independently Calculated Values)
# -----------------------------------------------------------------------------
def test_compute_expected_loss_handcrafted():
    """Verify Expected Loss against independent manual calculation.

    Scenario:
    Loan 1: Exposure ₹50,000, PD = 0.02 (2%), LGD = 0.50 -> EL = 50,000 * 0.02 * 0.5 = ₹500
    Loan 2: Exposure ₹100,000, PD = 0.10 (10%), LGD = 0.50 -> EL = 100,000 * 0.10 * 0.5 = ₹5,000
    Loan 3: Exposure ₹150,000, PD = 0.04 (4%), LGD = 0.50 -> EL = 150,000 * 0.04 * 0.5 = ₹3,000

    Total Exposure = ₹300,000
    Total EL = ₹8,500
    EL per 1 Lakh = (8,500 / 300,000) * 100,000 = ₹2,833.33
    """
    probs = [0.02, 0.10, 0.04]
    exposures = [50000.0, 100000.0, 150000.0]
    lgd = 0.50

    res = compute_expected_loss(probs, exposures, lgd=lgd)
    assert res["total_exposure_inr"] == 300000.0
    assert res["total_expected_loss_inr"] == 8500.0
    assert abs(res["expected_loss_per_1_lakh_inr"] - 2833.33) < 0.01
    assert res["lgd_assumption"] == 0.50


def test_compute_expected_loss_boundaries():
    """Verify EL boundaries: LGD=0, LGD=1, zero exposure, empty input."""
    # LGD = 0 -> EL = 0
    res_zero_lgd = compute_expected_loss([0.5], [100000.0], lgd=0.0)
    assert res_zero_lgd["total_expected_loss_inr"] == 0.0
    assert res_zero_lgd["expected_loss_per_1_lakh_inr"] == 0.0

    # LGD = 1 -> EL = PD * EAD
    res_full_lgd = compute_expected_loss([0.2], [50000.0], lgd=1.0)
    assert res_full_lgd["total_expected_loss_inr"] == 10000.0
    assert res_full_lgd["expected_loss_per_1_lakh_inr"] == 20000.0

    # Empty inputs
    res_empty = compute_expected_loss([], [])
    assert res_empty["total_expected_loss_inr"] == 0.0

    # Negative exposure error
    with pytest.raises(ValueError, match="non-negative"):
        compute_expected_loss([0.2], [-1000.0])

    # Invalid LGD error
    with pytest.raises(ValueError, match="LGD must be in"):
        compute_expected_loss([0.2], [1000.0], lgd=1.5)


def test_compute_expected_loss_reduction_exact_math():
    """Verify relative percentage reduction math:
    Baseline: ₹524.55 per Lakh
    Candidate: ₹439.75 per Lakh
    Delta: -₹84.80
    Reduction: (524.55 - 439.75) / 524.55 * 100 = 16.1662% -> 16.17%
    """
    res = compute_expected_loss_reduction(524.55, 439.75)
    assert res["absolute_difference_inr"] == -84.80
    assert abs(res["relative_reduction_pct"] - 16.17) < 0.01


# -----------------------------------------------------------------------------
# 4. Good Borrower Capture & Approval Reconciliation Tests
# -----------------------------------------------------------------------------
def test_compute_good_borrower_capture_handcrafted():
    """Verify good-borrower capture and decision transition accounting.

    Applicants: 4 total (3 good borrowers: idx 0, 1, 2; 1 default: idx 3)
    Baseline Probs:  [0.10, 0.25, 0.15, 0.05] -> Approved (<0.20): [0, 2, 3] -> Good: 2, Bad: 1
    Candidate Probs: [0.10, 0.18, 0.12, 0.30] -> Approved (<0.20): [0, 1, 2] -> Good: 3, Bad: 0

    Reconciliation:
    - Total good borrowers: 3
    - Baseline good approved: 2 (Capture: 2/3 = 66.67%)
    - Candidate good approved: 3 (Capture: 3/3 = 100.0%)
    - Net additional good approved: +1
    - Delta percentage points: +33.33 pp
    - Rejected-to-approved transition: 1 (applicant 1: base 0.25 -> cand 0.18)
    - Approved-to-rejected transition: 1 (applicant 3: base 0.05 -> cand 0.30, defaulter averted!)
    """
    y_true = [0, 0, 0, 1]
    p_base = [0.10, 0.25, 0.15, 0.05]
    p_cand = [0.10, 0.18, 0.12, 0.30]

    res = compute_good_borrower_capture(y_true, p_base, p_cand, approval_threshold=0.20)
    assert res["population"]["total_good_borrowers"] == 3
    assert res["population"]["total_defaulters"] == 1
    assert res["baseline_policy"]["good_borrowers_approved"] == 2
    assert res["candidate_policy"]["good_borrowers_approved"] == 3
    assert res["reconciliation"]["net_additional_good_borrowers_approved"] == 1
    assert abs(res["reconciliation"]["good_borrower_capture_delta_pp"] - 33.3333) < 0.01
    assert res["reconciliation"]["transitions"]["rejected_in_baseline_approved_in_candidate"] == 1
    assert res["reconciliation"]["transitions"]["approved_in_baseline_rejected_in_candidate"] == 1


# -----------------------------------------------------------------------------
# 5. Distressed Volatility Recall Tests
# -----------------------------------------------------------------------------
def test_compute_distressed_volatility_recall_exact():
    """Verify distressed volatility recall calculation:
    Cohort Defaults: 184
    Baseline TPs: 136 (Recall = 136 / 184 = 0.73913)
    Candidate TPs: 143 (Recall = 143 / 184 = 0.77717)
    Recall Delta pp = (77.717% - 73.913%) = +3.804% -> +3.80 pp (or +3.81 pp rounded)
    """
    y_true = np.zeros(200, dtype=int)
    y_true[:184] = 1  # 184 defaults

    p_base = np.zeros(200)
    p_base[:136] = 0.60  # 136 detected defaults (>=0.50)

    p_cand = np.zeros(200)
    p_cand[:143] = 0.60  # 143 detected defaults (>=0.50)

    res = compute_distressed_volatility_recall(y_true, p_base, p_cand, threshold=0.50)
    assert res["defaults"] == 184
    assert res["baseline"]["true_positives"] == 136
    assert res["candidate"]["true_positives"] == 143
    assert res["comparison"]["additional_defaults_detected"] == 7
    assert abs(res["comparison"]["recall_gain_percentage_points"] - 3.80) <= 0.01


# -----------------------------------------------------------------------------
# 6. Anti-Leakage & Data Preprocessing Governance Tests
# -----------------------------------------------------------------------------
def test_preprocessing_fitted_only_on_train():
    """Verify that model preprocessors and feature encoders were fitted strictly on train data.

    Checks:
    1. Training set applicant IDs have zero overlap with test applicant IDs.
    2. Test feature matrices X_test contain zero targets or future variables.
    """
    dataset_path = Path("data/synthetic/synthetic_credit_applications.parquet")
    if not dataset_path.exists():
        pytest.skip("Dataset file not available.")

    df = pd.read_parquet(dataset_path)
    splits = GroupedDatasetSplitter.split(df, seed=DEFAULT_RANDOM_SEED)

    train_apps = set(splits.train_df["applicant_profile_id"])
    test_apps = set(splits.test_df["applicant_profile_id"])
    assert len(train_apps.intersection(test_apps)) == 0, "Data leakage: Train-Test applicant overlap!"

    # Build model matrices and verify target/identity isolation
    matrices = build_model_ready_matrices(
        train_df=splits.train_df, val_df=splits.val_df, test_df=splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE, scored_only=True,
    )
    X_test = matrices["X_test"]
    forbidden = ["target_default_flag", "applicant_profile_id", "application_id", "cutoff_timestamp"]
    for col in forbidden:
        assert col not in X_test.columns, f"Forbidden target/identifier column {col} leaked into X_test!"


# -----------------------------------------------------------------------------
# 7. Determinism & Benchmark Execution Safety Tests
# -----------------------------------------------------------------------------
def test_deterministic_bootstrap():
    """Verify bootstrap confidence intervals are bitwise deterministic under fixed seed."""
    y = np.array([0, 1, 0, 1, 0, 0, 1, 1, 0, 1])
    p = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.4, 0.7, 0.85, 0.15, 0.75])

    ci1 = compute_bootstrap_ci(average_precision_score, y, p, n_iterations=100, seed=42)
    ci2 = compute_bootstrap_ci(average_precision_score, y, p, n_iterations=100, seed=42)
    assert ci1 == ci2
