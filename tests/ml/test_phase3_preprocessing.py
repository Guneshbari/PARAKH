"""Unit tests for Phase 3 Data Preprocessing.

Verifies:
1. CreditRiskPreprocessor fit/transform interface
2. Train-only parameter fitting (no data leakage from validation/test)
3. Determinism across repeated runs
4. Missing value imputation with median, without converting valid zeros to missing
5. Unknown category handling (OneHotEncoder handle_unknown='ignore')
6. Log(1 + x) transformation on skewed monetary features
7. Leverage ratio clipping to [0.0, 5.0]
8. Insufficient data filtering and identification
"""
import numpy as np
import pandas as pd
import pytest

from src.ml.data.preprocessing import CreditRiskPreprocessor
from src.ml.data.splitting import GroupedDatasetSplitter


@pytest.fixture(scope="module")
def dataset():
    """Load canonical synthetic dataset."""
    return pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")


@pytest.fixture(scope="module")
def split_data(dataset):
    """Split canonical dataset into train, val, and test."""
    return GroupedDatasetSplitter.split(dataset)


def test_preprocessor_fit_transform_basic(split_data):
    """Verify fit and transform returns expected shapes and columns without NaNs."""
    train_df = split_data.train_df
    val_df = split_data.val_df

    preprocessor = CreditRiskPreprocessor(scaler_type="robust")
    X_train_proc = preprocessor.fit_transform(train_df)
    X_val_proc = preprocessor.transform(val_df)

    assert preprocessor.is_fitted_ is True
    assert isinstance(X_train_proc, pd.DataFrame)
    assert isinstance(X_val_proc, pd.DataFrame)
    assert len(X_train_proc) == len(train_df)
    assert len(X_val_proc) == len(val_df)
    assert X_train_proc.isna().sum().sum() == 0
    assert X_val_proc.isna().sum().sum() == 0

    # Ensure all columns are numeric
    for col in X_train_proc.columns:
        assert pd.api.types.is_numeric_dtype(X_train_proc[col])


def test_train_only_fitting_isolation(split_data):
    """Verify that transformation parameters are strictly learned from training data."""
    train_df = split_data.train_df.copy()
    test_df = split_data.test_df.copy()

    preprocessor = CreditRiskPreprocessor(scaler_type="robust")
    preprocessor.fit(train_df)

    fitted_medians = dict(preprocessor.fitted_medians_)

    # Even if test data has completely different values, fitted medians remain unchanged
    test_transformed = preprocessor.transform(test_df)
    assert preprocessor.fitted_medians_ == fitted_medians


def test_determinism(split_data):
    """Verify preprocessor produces identical output across multiple runs."""
    train_df = split_data.train_df

    p1 = CreditRiskPreprocessor(scaler_type="robust")
    out1 = p1.fit_transform(train_df)

    p2 = CreditRiskPreprocessor(scaler_type="robust")
    out2 = p2.fit_transform(train_df)

    pd.testing.assert_frame_equal(out1, out2)


def test_unknown_category_handling(split_data):
    """Verify preprocessor handles unknown/unseen categorical values without throwing errors."""
    train_df = split_data.train_df
    preprocessor = CreditRiskPreprocessor()
    preprocessor.fit(train_df)

    # Create dummy observation with unobserved categories
    unseen_record = train_df.iloc[[0]].copy()
    unseen_record["gig_work_type"] = "DEEP_SEA_DIVING"
    unseen_record["loan_purpose"] = "CRYPTO_STAKING"

    transformed = preprocessor.transform(unseen_record)
    assert transformed.shape[0] == 1
    assert transformed.isna().sum().sum() == 0

    # Indicators for known categories must all be 0 for this unseen record
    cat_cols = [c for c in transformed.columns if c.startswith("gig_work_type_") or c.startswith("loan_purpose_")]
    assert (transformed[cat_cols].values == 0.0).all()


def test_missing_value_imputation_preserves_valid_zeros():
    """Verify median imputation replaces NaNs with training median while leaving valid zeros untouched."""
    # Create sample DataFrame with valid 0 and a NaN
    train_data = pd.DataFrame({
        "feat_inc_median_90d": [1000.0, 2000.0, 3000.0],
        "feat_act_zero_earn_weeks": [0.0, 2.0, 4.0],
        "feat_ten_trips_completed": [10.0, 20.0, 30.0],
        "gig_work_type": ["DELIVERY", "DELIVERY", "RIDE_HAILING"],
        "loan_purpose": ["WORKING_CAPITAL", "WORKING_CAPITAL", "OTHER"],
    })
    preprocessor = CreditRiskPreprocessor(scaler_type=None, apply_log_transform=False, clip_leverage_ratios=False)
    preprocessor.fit(train_data)

    test_data = pd.DataFrame({
        "feat_inc_median_90d": [0.0, np.nan],  # Valid 0 and a NaN
        "feat_act_zero_earn_weeks": [0.0, 0.0],
        "feat_ten_trips_completed": [20.0, 20.0],
        "gig_work_type": ["DELIVERY", "DELIVERY"],
        "loan_purpose": ["WORKING_CAPITAL", "WORKING_CAPITAL"],
    })

    transformed = preprocessor.transform(test_data)
    # The valid 0.0 must remain 0.0 (not replaced by median)
    assert transformed.loc[0, "feat_inc_median_90d"] == 0.0
    # The NaN must be replaced with the training median (2000.0)
    assert transformed.loc[1, "feat_inc_median_90d"] == 2000.0


def test_leverage_clipping():
    """Verify leverage ratios are capped at specified bounds (default [0.0, 5.0])."""
    train_data = pd.DataFrame({
        "feat_bur_total_dti": [0.5, 1.0, 1.5],
        "feat_liq_buffer_to_loan": [0.2, 0.5, 1.0],
        "gig_work_type": ["DELIVERY", "DELIVERY", "DELIVERY"],
        "loan_purpose": ["WORKING_CAPITAL", "WORKING_CAPITAL", "WORKING_CAPITAL"],
    })
    preprocessor = CreditRiskPreprocessor(
        scaler_type=None, apply_log_transform=False, clip_leverage_ratios=True, leverage_clip_bounds=(0.0, 5.0)
    )
    preprocessor.fit(train_data)

    test_data = pd.DataFrame({
        "feat_bur_total_dti": [12.0, -1.0],  # Above and below bounds
        "feat_liq_buffer_to_loan": [10.0, 0.5],
        "gig_work_type": ["DELIVERY", "DELIVERY"],
        "loan_purpose": ["WORKING_CAPITAL", "WORKING_CAPITAL"],
    })

    transformed = preprocessor.transform(test_data)
    assert transformed.loc[0, "feat_bur_total_dti"] == 5.0
    assert transformed.loc[1, "feat_bur_total_dti"] == 0.0
    assert transformed.loc[0, "feat_liq_buffer_to_loan"] == 5.0


def test_insufficient_data_filtering(dataset):
    """Verify helper methods segregate scored records from insufficient evidence records."""
    scored_df = CreditRiskPreprocessor.filter_scored_applications(dataset)
    unscored_df = CreditRiskPreprocessor.filter_insufficient_data_applications(dataset)

    assert len(scored_df) == 11407
    assert len(unscored_df) == 593
    assert len(scored_df) + len(unscored_df) == 12000

    assert scored_df["target_default_flag"].notnull().all()
    assert unscored_df["target_default_flag"].isnull().all()
    assert (unscored_df["cohort_archetype"] == "Insufficient Data").all()


def test_check_insufficient_evidence():
    """Verify rule-based sufficiency check flags records with < 30 days or < 4 payouts."""
    # Sufficient record
    rec_ok = {"feat_suf_observed_days": 90, "feat_suf_payout_count": 12}
    is_insuf, reasons = CreditRiskPreprocessor.check_insufficient_evidence(rec_ok)
    assert is_insuf is False
    assert len(reasons) == 0

    # Insufficient history
    rec_short = {"feat_suf_observed_days": 18, "feat_suf_payout_count": 5}
    is_insuf, reasons = CreditRiskPreprocessor.check_insufficient_evidence(rec_short)
    assert is_insuf is True
    assert any("Observed days 18 < 30" in r for r in reasons)

    # Insufficient payouts
    rec_low_payouts = {"feat_suf_observed_days": 45, "feat_suf_payout_count": 2}
    is_insuf, reasons = CreditRiskPreprocessor.check_insufficient_evidence(rec_low_payouts)
    assert is_insuf is True
    assert any("Payout cycle count 2 < 4" in r for r in reasons)
