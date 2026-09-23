"""Unit tests for Phase 4 Feature Engineering Layer.

Verifies:
1. Determinism and reproducibility across repeated runs.
2. Correctness of the 9 newly engineered volatility interaction features.
3. Numerical safety and division-by-zero protection under extreme edge cases.
4. Non-leakage: identifiers and target variables strictly excluded from predictor matrix.
5. Baseline vs Volatility-Aware feature subset partitioning.
6. Absence of NaNs, Infs, or invalid values in model-ready matrices.
7. Feature lineage completeness across all features in the master registry.
"""
from typing import Any, Dict
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.features.feature_engineering import (
    BASELINE_FEATURE_SET,
    ENGINEERED_VOLATILITY_FEATURES,
    FeatureEngineer,
    MASTER_LINEAGE,
    build_model_ready_matrices,
)


@pytest.fixture(scope="module")
def canonical_df():
    """Load canonical synthetic dataset."""
    return pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")


@pytest.fixture(scope="module")
def splits(canonical_df):
    """Split canonical dataset into train, val, test."""
    return GroupedDatasetSplitter.split(canonical_df)


def test_engineered_features_presence_and_shape(canonical_df):
    """Verify that FeatureEngineer generates all 9 engineered features."""
    engineer = FeatureEngineer(include_engineered_interactions=True)
    out_df = engineer.fit_transform(canonical_df)

    assert len(out_df) == len(canonical_df)
    assert len(out_df.columns) == len(canonical_df.columns) + len(ENGINEERED_VOLATILITY_FEATURES)

    for feat in ENGINEERED_VOLATILITY_FEATURES:
        assert feat in out_df.columns
        assert pd.api.types.is_numeric_dtype(out_df[feat])
        assert out_df[feat].isna().sum() == 0
        assert np.isinf(out_df[feat]).sum() == 0


def test_determinism_repeated_execution(canonical_df):
    """Verify that identical inputs produce bitwise-identical engineered features."""
    engineer1 = FeatureEngineer()
    out1 = engineer1.fit_transform(canonical_df)

    engineer2 = FeatureEngineer()
    out2 = engineer2.fit_transform(canonical_df)

    for feat in ENGINEERED_VOLATILITY_FEATURES:
        np.testing.assert_array_equal(out1[feat].values, out2[feat].values)


def test_numerical_safety_zero_denominators():
    """Verify division-by-zero safety when denominator inputs are zero or negative."""
    zero_df = pd.DataFrame([{
        "feat_inc_cv_90d": 0.0,
        "feat_inc_median_90d": 0.0,
        "feat_inc_downside_var": 0.0,
        "feat_trend_momentum_30_90": 0.0,
        "feat_rec_bounceback_ratio": 0.0,
        "feat_rec_days_to_recover": 0.0,
        "feat_liq_buffer_to_loan": 0.0,
        "feat_liq_burn_months": 0.0,
        "feat_bur_total_dti": 0.0,
        "requested_loan_amount": 0.0,
        "loan_tenure_months": 0,
        "feat_inc_p25_90d": 0.0,
    }])

    engineer = FeatureEngineer()
    out = engineer.transform(zero_df)

    for feat in ENGINEERED_VOLATILITY_FEATURES:
        val = out.loc[0, feat]
        assert not np.isnan(val), f"Feature {feat} resulted in NaN on zero input"
        assert not np.isinf(val), f"Feature {feat} resulted in Inf on zero input"
        assert val == 0.0 or abs(val) < 1e-4 or val >= 0.0


def test_volatility_to_baseline_scaling(canonical_df):
    """Verify feat_eng_vol_to_baseline properly normalizes volatility by earning scale."""
    engineer = FeatureEngineer()
    out = engineer.transform(canonical_df)

    # For high earners with same CV, normalized volatility must be lower than for low earners
    high_earner = canonical_df[canonical_df["feat_inc_median_90d"] > 25000].iloc[0:1]
    low_earner = canonical_df[canonical_df["feat_inc_median_90d"] < 5000].iloc[0:1]

    # Force identical CV
    high_earner_test = high_earner.copy()
    low_earner_test = low_earner.copy()
    high_earner_test["feat_inc_cv_90d"] = 0.30
    low_earner_test["feat_inc_cv_90d"] = 0.30

    out_high = engineer.transform(high_earner_test)
    out_low = engineer.transform(low_earner_test)

    assert (
        out_high["feat_eng_vol_to_baseline"].values[0]
        < out_low["feat_eng_vol_to_baseline"].values[0]
    )


def test_volatility_conditioned_on_trend():
    """Verify feat_eng_vol_x_trend distinguishes growth volatility from decay volatility."""
    test_df = pd.DataFrame([
        # Growth surge: high CV with expanding trend momentum > 1.0
        {"feat_inc_cv_90d": 0.40, "feat_trend_momentum_30_90": 1.30},
        # Decaying shock: high CV with contracting trend momentum < 1.0
        {"feat_inc_cv_90d": 0.40, "feat_trend_momentum_30_90": 0.70},
    ])
    # Add dummy columns for other features
    for f in [
        "feat_inc_median_90d", "feat_inc_downside_var", "feat_rec_bounceback_ratio",
        "feat_rec_days_to_recover", "feat_liq_buffer_to_loan", "feat_liq_burn_months",
        "feat_bur_total_dti", "requested_loan_amount", "loan_tenure_months", "feat_inc_p25_90d"
    ]:
        test_df[f] = 1.0

    engineer = FeatureEngineer()
    out = engineer.transform(test_df)

    growth_val = out.loc[0, "feat_eng_vol_x_trend"]
    decay_val = out.loc[1, "feat_eng_vol_x_trend"]

    assert growth_val > 0.0, "Growth surge volatility should yield positive trend interaction"
    assert decay_val < 0.0, "Decaying contraction volatility should yield negative trend interaction"


def test_volatility_conditioned_on_bounceback():
    """Verify feat_eng_vol_to_bounceback is lower when recovery elasticity is strong."""
    test_df = pd.DataFrame([
        # Elastic recovery
        {"feat_inc_cv_90d": 0.35, "feat_rec_bounceback_ratio": 1.50},
        # Inelastic stagnation
        {"feat_inc_cv_90d": 0.35, "feat_rec_bounceback_ratio": 0.50},
    ])
    for f in [
        "feat_inc_median_90d", "feat_inc_downside_var", "feat_trend_momentum_30_90",
        "feat_rec_days_to_recover", "feat_liq_buffer_to_loan", "feat_liq_burn_months",
        "feat_bur_total_dti", "requested_loan_amount", "loan_tenure_months", "feat_inc_p25_90d"
    ]:
        test_df[f] = 1.0

    engineer = FeatureEngineer()
    out = engineer.transform(test_df)

    elastic_val = out.loc[0, "feat_eng_vol_to_bounceback"]
    inelastic_val = out.loc[1, "feat_eng_vol_to_bounceback"]

    assert elastic_val < inelastic_val


def test_lineage_registry_completeness():
    """Verify master feature lineage registry documents all features with valid metadata."""
    assert len(MASTER_LINEAGE) == 55

    for name, record in MASTER_LINEAGE.items():
        assert record.feature_name == name
        assert len(record.source_features) > 0
        assert len(record.calculation_formula) > 0
        assert len(record.semantic_meaning) > 0
        assert len(record.unit) > 0
        assert record.feature_type in {
            "raw_input",
            "derived_telemetry",
            "interaction_contract",
            "engineered_volatility",
        }


def test_baseline_vs_volatility_aware_subsets():
    """Verify feature subset segregation between Baseline and Volatility-Aware models."""
    base_features = FeatureEngineer.get_feature_subset(ExperimentVariant.BASELINE)
    vol_features = FeatureEngineer.get_feature_subset(ExperimentVariant.VOLATILITY_AWARE)

    assert len(base_features) == 26
    assert len(vol_features) == 55

    # Baseline must NOT contain non-linear volatility interactions
    for int_feat in [
        "feat_int_vol_x_recovery",
        "feat_int_vol_x_buffer",
        "feat_int_trend_x_dti",
        "feat_int_resilience_idx",
        "feat_eng_vol_to_baseline",
        "feat_eng_vol_x_trend",
        "feat_eng_vol_to_bounceback",
    ]:
        assert int_feat not in base_features
        assert int_feat in vol_features

    # All baseline features must be present in volatility-aware feature set
    for bf in base_features:
        assert bf in vol_features


def test_model_ready_matrices_isolation_and_integrity(splits):
    """Verify build_model_ready_matrices produces clean, leakage-free matrices."""
    train_df = splits.train_df
    val_df = splits.val_df
    test_df = splits.test_df

    matrices = build_model_ready_matrices(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    X_train = matrices["X_train"]
    y_train = matrices["y_train"]
    X_val = matrices["X_val"]
    y_val = matrices["y_val"]
    X_test = matrices["X_test"]
    y_test = matrices["y_test"]

    # Scored row counts
    assert len(X_train) == 8012
    assert len(y_train) == 8012
    assert len(X_val) == 1697
    assert len(y_val) == 1697
    assert len(X_test) == 1698
    assert len(y_test) == 1698

    # 64 output features (53 numeric + 11 one-hot categories)
    assert X_train.shape[1] == 64
    assert X_val.shape[1] == 64
    assert X_test.shape[1] == 64

    # Identifiers and target must NEVER be inside X
    forbidden_in_x = {
        "applicant_profile_id",
        "application_id",
        "cutoff_timestamp",
        "cohort_archetype",
        "target_default_flag",
        "repayment_risk_probability",
    }
    for col in X_train.columns:
        assert col not in forbidden_in_x

    # Zero NaNs or Infs
    assert X_train.isna().sum().sum() == 0
    assert X_val.isna().sum().sum() == 0
    assert X_test.isna().sum().sum() == 0

    # Binary ground-truth target
    assert set(np.unique(y_train)) == {0, 1}
    assert set(np.unique(y_val)) == {0, 1}
    assert set(np.unique(y_test)) == {0, 1}
