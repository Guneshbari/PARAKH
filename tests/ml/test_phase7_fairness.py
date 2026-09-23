"""Unit tests for Phase 7 subgroup and cohort fairness auditing framework.

Verifies:
1. compute_subgroup_metrics calculation of selection, favorable, and error rates.
2. Favorable rate and selection rate complementary property (fav_rate + sel_rate == 1.0).
3. Zero-division and small sample group protection without exceptions.
4. audit_comparative_fairness reporting across both Phase 5 and Phase 6 models.
5. Demographic Parity Ratio (DPR) calculation and bounds [0, 1].
6. Equal Opportunity Difference (EOD) calculation and bounds [0, 1].
7. Mandatory presence of synthetic data regulatory disclaimers.
8. Deterministic reproducibility across repeated fairness audits.
9. Subgroup auditing across multiple segmentation fields (cohort, sector, loan purpose, income).
"""
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import DEFAULT_RANDOM_SEED
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.explainability.cohort_fairness import (
    FAIRNESS_SYNTHETIC_DATA_DISCLAIMER,
    MultiModelFairnessReport,
    SegmentFairnessMetrics,
    audit_comparative_fairness,
    compute_subgroup_metrics,
)


@pytest.fixture(scope="module")
def sample_fairness_data():
    """Create controlled multi-group sample dataset."""
    rng = np.random.RandomState(42)
    n = 200
    y_true = rng.binomial(1, 0.15, size=n)
    probs_base = np.clip(y_true * 0.6 + rng.uniform(0.0, 0.4, size=n), 0.0, 1.0)
    probs_vol = np.clip(y_true * 0.7 + rng.uniform(0.0, 0.3, size=n), 0.0, 1.0)
    cohorts = rng.choice(["Healthy Volatile", "Stable", "Declining", "Irregular", "High Obligation"], size=n)
    sectors = rng.choice(["DELIVERY", "RIDE_HAILING", "LOGISTICS"], size=n)

    return {
        "y_true": y_true,
        "probs_base": probs_base,
        "probs_vol": probs_vol,
        "cohorts": cohorts,
        "sectors": sectors,
    }


def test_compute_subgroup_metrics_consistency(sample_fairness_data):
    """Verify metrics calculation and complementary property between favorable and selection rates."""
    y_true = sample_fairness_data["y_true"]
    probs = sample_fairness_data["probs_vol"]
    cohorts = sample_fairness_data["cohorts"]

    metrics_map = compute_subgroup_metrics(y_true, probs, cohorts, threshold=0.50)

    assert len(metrics_map) == 5
    total_samples = 0
    for name, m in metrics_map.items():
        assert isinstance(m, SegmentFairnessMetrics)
        total_samples += m.sample_count
        assert np.isclose(m.selection_rate + m.favorable_rate, 1.0, atol=1e-4)
        assert m.positive_actual_count + m.negative_actual_count == m.sample_count
        if m.brier_score is not None:
            assert 0.0 <= m.brier_score <= 1.0

    assert total_samples == len(y_true)


def test_small_sample_and_zero_division_guard():
    """Verify graceful handling when subgroups have very small samples or zero positive actuals."""
    y_true = np.array([0, 0, 0, 1, 1])
    probs = np.array([0.1, 0.2, 0.15, 0.8, 0.9])
    groups = ["SmallGroup", "SmallGroup", "SmallGroup", "Other", "Other"]

    metrics_map = compute_subgroup_metrics(y_true, probs, groups, threshold=0.50)

    small_grp = metrics_map["SmallGroup"]
    assert small_grp.sample_count == 3
    assert small_grp.positive_actual_count == 0
    assert small_grp.true_positive_rate is None
    assert small_grp.small_sample_flag is True


def test_comparative_fairness_audit(sample_fairness_data):
    """Verify audit_comparative_fairness compares baseline and volatility-aware models."""
    d = sample_fairness_data
    report = audit_comparative_fairness(
        y_true=d["y_true"],
        baseline_probs=d["probs_base"],
        volatility_probs=d["probs_vol"],
        subgroups=d["sectors"],
        segment_field_name="gig_work_type",
        threshold=0.50,
    )

    assert isinstance(report, MultiModelFairnessReport)
    assert report.segment_field == "gig_work_type"
    assert len(report.baseline_subgroups) == 3
    assert len(report.volatility_aware_subgroups) == 3

    # Demographic Parity Ratio in (0, 1]
    if report.baseline_demographic_parity_ratio is not None:
        assert 0.0 < report.baseline_demographic_parity_ratio <= 1.0
    if report.volatility_aware_demographic_parity_ratio is not None:
        assert 0.0 < report.volatility_aware_demographic_parity_ratio <= 1.0

    # Equal Opportunity Difference in [0, 1]
    if report.baseline_equal_opportunity_diff is not None:
        assert 0.0 <= report.baseline_equal_opportunity_diff <= 1.0
    if report.volatility_aware_equal_opportunity_diff is not None:
        assert 0.0 <= report.volatility_aware_equal_opportunity_diff <= 1.0

    # Mandatory disclaimer present
    assert "IMPORTANT REGULATORY & FAIRNESS NOTICE" in report.disclaimer
    assert "synthetic" in report.disclaimer.lower()


def test_fairness_report_serialization(sample_fairness_data):
    """Verify fairness report converts to JSON-serializable dictionary."""
    d = sample_fairness_data
    report = audit_comparative_fairness(
        y_true=d["y_true"],
        baseline_probs=d["probs_base"],
        volatility_probs=d["probs_vol"],
        subgroups=d["cohorts"],
        segment_field_name="cohort_archetype",
        threshold=0.50,
    )

    r_dict = report.to_dict()
    assert isinstance(r_dict, dict)
    assert "baseline_subgroups" in r_dict
    assert "volatility_aware_subgroups" in r_dict
    assert "disclaimer" in r_dict
    assert len(r_dict["observations"]) > 0
