"""Unit tests for Phase 3 Dataset Validation against the Frozen ML Contract.

Verifies:
1. Schema & column completeness (52 canonical columns, 40 derived features)
2. Target semantics & null handling (0/1 binary, null only for Insufficient Data)
3. Categorical domain compliance
4. Numerical feature ranges & non-negativity
5. Missingness semantics (0 missing in feature columns)
6. Temporal monotonicity & anti-leakage
7. Grouped 70/15/15 split applicant isolation
8. Impossible combination detection
"""
from datetime import datetime
import numpy as np
import pandas as pd
import pytest

from src.ml.data.dataset_validator import (
    CANONICAL_COLUMNS,
    DERIVED_FEATURES,
    MANDATORY_FEATURES,
    OPTIONAL_FEATURES,
    Phase3DatasetValidator,
)
from src.ml.data.splitting import GroupedDatasetSplitter


@pytest.fixture(scope="module")
def canonical_dataset():
    """Load canonical synthetic credit applications dataset."""
    df = pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")
    return df


def test_canonical_dataset_full_validation(canonical_dataset):
    """Verify that the actual synthetic dataset passes all Phase 3 validator checks."""
    report = Phase3DatasetValidator.validate_dataframe(canonical_dataset)
    assert report.is_valid is True
    assert report.status == "PASS"
    assert len(report.errors) == 0
    assert report.diagnostics.total_rows == 12000
    assert report.diagnostics.unique_applicants == 10000
    assert report.diagnostics.scored_rows == 11407
    assert report.diagnostics.insufficient_data_rows == 593
    assert report.diagnostics.default_count == 1486
    assert 0.10 <= report.diagnostics.scored_default_rate <= 0.15


def test_schema_completeness(canonical_dataset):
    """Verify exact 52 canonical columns and 40 derived ML features."""
    assert len(canonical_dataset.columns) == 52
    assert list(canonical_dataset.columns) == CANONICAL_COLUMNS

    derived = [c for c in canonical_dataset.columns if c.startswith("feat_")]
    assert len(derived) == 40
    assert set(derived) == set(DERIVED_FEATURES)
    assert len(MANDATORY_FEATURES) == 19
    assert len(OPTIONAL_FEATURES) == 21


def test_target_semantics_and_null_integrity(canonical_dataset):
    """Verify target_default_flag is binary {0, 1} on scored and null only on insufficient data."""
    target_series = canonical_dataset["target_default_flag"]
    insuf_mask = canonical_dataset["cohort_archetype"] == "Insufficient Data"

    # Scored records must have non-null targets strictly in {0, 1}
    scored_targets = target_series[~insuf_mask]
    assert scored_targets.notnull().all()
    assert set(scored_targets.unique()) == {0.0, 1.0}

    # Insufficient Data records must have null target
    unscored_targets = target_series[insuf_mask]
    assert unscored_targets.isnull().all()

    # Repayment risk probability must be in [0, 1] on scored and null on unscored
    prob_series = canonical_dataset["repayment_risk_probability"]
    assert prob_series[~insuf_mask].notnull().all()
    assert (prob_series[~insuf_mask] >= 0.0).all()
    assert (prob_series[~insuf_mask] <= 1.0).all()
    assert prob_series[insuf_mask].isnull().all()


def test_feature_ranges_and_non_negativity(canonical_dataset):
    """Verify numerical feature values comply with documented physical bounds."""
    # Check non-negativity on mandatory features that cannot be negative
    assert (canonical_dataset["feat_inc_median_90d"] >= 0.0).all()
    assert (canonical_dataset["feat_inc_p25_90d"] >= 0.0).all()
    assert (canonical_dataset["feat_inc_cv_90d"] >= 0.0).all()
    assert (canonical_dataset["feat_act_active_days_ratio"] >= 0.0).all()
    assert (canonical_dataset["feat_act_active_days_ratio"] <= 1.0).all()
    assert (canonical_dataset["feat_act_zero_earn_weeks"] >= 0).all()
    assert (canonical_dataset["feat_act_zero_earn_weeks"] <= 13).all()
    assert (canonical_dataset["feat_rec_bounceback_ratio"] >= 0.0).all()
    assert (canonical_dataset["feat_rec_days_to_recover"] >= 0.0).all()
    assert (canonical_dataset["feat_liq_buffer_to_loan"] >= 0.0).all()
    assert (canonical_dataset["feat_suf_observed_days"] >= 0).all()
    assert (canonical_dataset["feat_suf_observed_days"] <= 90).all()
    assert (canonical_dataset["feat_suf_missing_ratio"] >= 0.0).all()
    assert (canonical_dataset["feat_suf_missing_ratio"] <= 1.0).all()

    # Net margin can be negative, but bounded in [-2.0, 1.0]
    assert (canonical_dataset["feat_liq_net_margin"] >= -2.0).all()
    assert (canonical_dataset["feat_liq_net_margin"] <= 1.0).all()


def test_categorical_domains(canonical_dataset):
    """Verify categorical columns contain only authorized values."""
    assert set(canonical_dataset["cohort_archetype"].unique()) == {
        "Healthy Volatile",
        "Stable",
        "Declining",
        "Irregular",
        "High Obligation",
        "Insufficient Data",
    }
    assert set(canonical_dataset["gig_work_type"].unique()).issubset({
        "DELIVERY",
        "RIDE_HAILING",
        "LOGISTICS",
        "HOME_SERVICES",
        "FREELANCE_MICRO",
        "OTHER",
    })
    assert set(canonical_dataset["loan_purpose"].unique()).issubset({
        "VEHICLE_MAINTENANCE",
        "WORKING_CAPITAL",
        "EQUIPMENT_PURCHASE",
        "PERSONAL_EMERGENCY",
        "OTHER",
    })
    assert set(canonical_dataset["loan_tenure_months"].unique()).issubset({6, 9, 12})


def test_missing_value_semantics(canonical_dataset):
    """Verify no feature columns contain missing values in canonical dataset."""
    feature_cols = [c for c in canonical_dataset.columns if c.startswith("feat_")]
    assert canonical_dataset[feature_cols].isna().sum().sum() == 0

    metadata_cols = [
        "applicant_profile_id",
        "application_id",
        "cutoff_timestamp",
        "cohort_archetype",
        "gig_work_type",
        "requested_loan_amount",
        "loan_tenure_months",
        "loan_purpose",
    ]
    assert canonical_dataset[metadata_cols].isna().sum().sum() == 0


def test_temporal_monotonicity_for_repeat_applicants(canonical_dataset):
    """Verify repeated applications from the same applicant have increasing timestamps >= 30 days apart."""
    repeat_counts = canonical_dataset["applicant_profile_id"].value_counts()
    repeat_ids = repeat_counts[repeat_counts > 1].index

    for app_id in repeat_ids[:100]:  # Sample check 100 repeat applicants
        sub = canonical_dataset[canonical_dataset["applicant_profile_id"] == app_id].sort_values("cutoff_timestamp")
        ts = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in sub["cutoff_timestamp"]]
        for i in range(len(ts) - 1):
            diff = ts[i + 1] - ts[i]
            assert diff.total_seconds() > 0, f"Timestamp not monotonic for applicant {app_id}"
            assert diff.days >= 30, f"Application spacing < 30 days for applicant {app_id}"


def test_impossible_combination_detection(canonical_dataset):
    """Verify validator catches corrupted impossible combinations."""
    # Start from a valid sample record
    corrupt_df = canonical_dataset.iloc[[0]].copy()
    # Introduce violation: 0 active days ratio but positive median income
    corrupt_df["feat_act_active_days_ratio"] = 0.0
    corrupt_df["feat_inc_median_90d"] = 5000.0

    report = Phase3DatasetValidator.validate_dataframe(corrupt_df)
    assert report.is_valid is False
    assert any("0 active days but positive median income" in e for e in report.errors)


def test_grouped_split_isolation(canonical_dataset):
    """Verify 70/15/15 grouped split by applicant_profile_id preserves 0 applicant leakage."""
    split_res = GroupedDatasetSplitter.split(canonical_dataset)
    assert split_res.leakage_audit.leakage_detected is False
    assert len(split_res.train_applicants & split_res.val_applicants) == 0
    assert len(split_res.train_applicants & split_res.test_applicants) == 0
    assert len(split_res.val_applicants & split_res.test_applicants) == 0

    assert split_res.train_summary.unique_applicants == 7000
    assert split_res.val_summary.unique_applicants == 1500
    assert split_res.test_summary.unique_applicants == 1500

    # Default rates in each partition must be within 10% - 15% range
    assert 0.10 <= split_res.train_summary.default_rate <= 0.15
    assert 0.10 <= split_res.val_summary.default_rate <= 0.15
    assert 0.10 <= split_res.test_summary.default_rate <= 0.15
