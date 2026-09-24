"""Unit tests for model data validation and leakage detection."""
import pandas as pd
import pytest

from src.ml.data.validation import ModelDataValidator


def test_validate_training_dataframe_valid():
    df = pd.DataFrame({
        "applicant_profile_id": ["app_1", "app_2", "app_3"],
        "target_default_flag": [0, 1, 0],
        "feat_inc_median": [35000.0, 22000.0, 41000.0],
        "feat_inc_cv": [0.25, 0.45, 0.18],
    })

    report = ModelDataValidator.validate_training_dataframe(
        df=df,
        target_column="target_default_flag",
        expected_features=["feat_inc_median", "feat_inc_cv"],
        applicant_id_column="applicant_profile_id",
    )

    assert report.is_valid is True
    assert report.total_rows == 3
    assert len(report.missing_columns) == 0
    assert report.null_target_count == 0
    assert len(report.validation_errors) == 0


def test_validate_training_dataframe_errors():
    # DataFrame with missing target, missing feature, and non-numeric feature
    df = pd.DataFrame({
        "target_default_flag": [0, None, 5],  # Contains null and non-binary 5
        "feat_inc_median": [35000.0, 22000.0, 41000.0],
        "feat_inc_cv": ["high", "medium", "low"],  # String instead of numeric
    })

    report = ModelDataValidator.validate_training_dataframe(
        df=df,
        target_column="target_default_flag",
        expected_features=["feat_inc_median", "feat_inc_cv", "feat_missing"],
    )

    assert report.is_valid is False
    assert report.null_target_count == 1
    assert 5 in report.invalid_target_values
    assert "feat_missing" in report.missing_columns
    assert "feat_inc_cv" in report.non_numeric_features


def test_audit_split_leakage():
    # Clean splits
    train_df = pd.DataFrame({"applicant_profile_id": ["app_1", "app_2", "app_3"]})
    val_df = pd.DataFrame({"applicant_profile_id": ["app_4", "app_5"]})
    test_df = pd.DataFrame({"applicant_profile_id": ["app_6", "app_7"]})

    clean_report = ModelDataValidator.audit_split_leakage(train_df, val_df, test_df)
    assert clean_report.leakage_detected is False
    assert len(clean_report.overlapping_train_val) == 0
    assert len(clean_report.overlapping_train_test) == 0

    # Leaky splits (app_2 appears in both train and test)
    leaky_test_df = pd.DataFrame({"applicant_profile_id": ["app_2", "app_6"]})
    leaky_report = ModelDataValidator.audit_split_leakage(train_df, val_df, leaky_test_df)
    assert leaky_report.leakage_detected is True
    assert "app_2" in leaky_report.overlapping_train_test
