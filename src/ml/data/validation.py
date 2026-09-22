"""Model input validation boundary for PARAKH credit risk datasets.

Validates that feature matrices and targets delivered by Person 2's pipeline
conform to the Phase 1 Data Contract before ingestion into model training.
Detects applicant identity leakage across train/validation/test partitions.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union
import numpy as np
import pandas as pd


@dataclass
class ValidationReport:
    """Report detailing data contract validation checks on a model input DataFrame."""

    is_valid: bool
    total_rows: int
    total_columns: int
    missing_columns: List[str] = field(default_factory=list)
    null_target_count: int = 0
    invalid_target_values: List[Any] = field(default_factory=list)
    non_numeric_features: List[str] = field(default_factory=list)
    duplicate_applicant_count: int = 0
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "is_valid": self.is_valid,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "missing_columns": self.missing_columns,
            "null_target_count": self.null_target_count,
            "invalid_target_values": self.invalid_target_values,
            "non_numeric_features": self.non_numeric_features,
            "duplicate_applicant_count": self.duplicate_applicant_count,
            "validation_errors": self.validation_errors,
            "warnings": self.warnings,
        }


@dataclass
class LeakageAuditReport:
    """Report checking for applicant identity leakage across dataset splits."""

    leakage_detected: bool
    train_applicant_count: int
    val_applicant_count: int
    test_applicant_count: int
    overlapping_train_val: List[str] = field(default_factory=list)
    overlapping_train_test: List[str] = field(default_factory=list)
    overlapping_val_test: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert leakage report to dictionary."""
        return {
            "leakage_detected": self.leakage_detected,
            "train_applicant_count": self.train_applicant_count,
            "val_applicant_count": self.val_applicant_count,
            "test_applicant_count": self.test_applicant_count,
            "overlapping_train_val_count": len(self.overlapping_train_val),
            "overlapping_train_test_count": len(self.overlapping_train_test),
            "overlapping_val_test_count": len(self.overlapping_val_test),
        }


class ModelDataValidator:
    """Validates model training matrices against the PARAKH Phase 1 data contract."""

    @staticmethod
    def validate_training_dataframe(
        df: pd.DataFrame,
        target_column: str,
        expected_features: List[str],
        applicant_id_column: Optional[str] = None,
        allow_continuous_target: bool = False,
    ) -> ValidationReport:
        """Validate that a training feature DataFrame satisfies the model ingestion contract.

        Args:
            df: Training DataFrame containing features and target.
            target_column: Name of the binary default target column.
            expected_features: List of required feature names that must be present.
            applicant_id_column: Optional column tracking worker identity.
            allow_continuous_target: Whether continuous probabilities [0, 1] are permitted.

        Returns:
            ValidationReport: Summary of schema conformance and data integrity checks.
        """
        errors: List[str] = []
        warnings: List[str] = []
        missing_cols: List[str] = []
        non_numeric: List[str] = []
        invalid_targets: List[Any] = []

        total_rows = len(df)
        total_cols = len(df.columns)

        if total_rows == 0:
            errors.append("DataFrame is empty (0 rows).")
            return ValidationReport(
                is_valid=False,
                total_rows=0,
                total_columns=total_cols,
                validation_errors=errors,
            )

        # 1. Target column presence & validity
        if target_column not in df.columns:
            errors.append(f"Target column '{target_column}' is missing from DataFrame.")
            null_targets = 0
        else:
            target_series = df[target_column]
            null_targets = int(target_series.isna().sum())
            if null_targets > 0:
                errors.append(
                    f"Target column '{target_column}' contains {null_targets} null values."
                )

            # Check valid values
            valid_targets = target_series.dropna()
            if not allow_continuous_target:
                # Binary targets must be 0 or 1
                unique_vals = set(valid_targets.unique())
                disallowed = unique_vals - {0, 1, 0.0, 1.0}
                if disallowed:
                    invalid_targets = list(disallowed)[:10]
                    errors.append(
                        f"Target column contains non-binary values: {invalid_targets}"
                    )
            else:
                # Continuous probabilities must be in [0, 1]
                out_of_bounds = valid_targets[(valid_targets < 0.0) | (valid_targets > 1.0)]
                if len(out_of_bounds) > 0:
                    invalid_targets = list(out_of_bounds.unique())[:10]
                    errors.append(
                        f"Target column contains probabilities outside [0, 1]: {invalid_targets}"
                    )

        # 2. Expected feature presence
        for feat in expected_features:
            if feat not in df.columns:
                missing_cols.append(feat)

        if missing_cols:
            errors.append(
                f"Missing {len(missing_cols)} expected feature columns: {missing_cols[:5]}..."
            )

        # 3. Numeric feature checks
        present_features = [f for f in expected_features if f in df.columns]
        for feat in present_features:
            if not pd.api.types.is_numeric_dtype(df[feat]):
                non_numeric.append(feat)

        if non_numeric:
            errors.append(
                f"Features must be numeric for model training, but found non-numeric: {non_numeric[:5]}"
            )

        # 4. Duplicate applicant detection within single split
        dup_applicants = 0
        if applicant_id_column and applicant_id_column in df.columns:
            dup_applicants = int(df[applicant_id_column].duplicated().sum())
            if dup_applicants > 0:
                warnings.append(
                    f"Dataset contains {dup_applicants} repeated assessments for the same applicant. "
                    "Ensure grouped cross-validation is used."
                )

        is_valid = len(errors) == 0

        return ValidationReport(
            is_valid=is_valid,
            total_rows=total_rows,
            total_columns=total_cols,
            missing_columns=missing_cols,
            null_target_count=null_targets,
            invalid_target_values=invalid_targets,
            non_numeric_features=non_numeric,
            duplicate_applicant_count=dup_applicants,
            validation_errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def audit_split_leakage(
        train_df: pd.DataFrame,
        val_df: Optional[pd.DataFrame] = None,
        test_df: Optional[pd.DataFrame] = None,
        applicant_id_column: str = "applicant_profile_id",
    ) -> LeakageAuditReport:
        """Verify that applicant identities do not overlap across train, validation, and test splits.

        Args:
            train_df: Training partition.
            val_df: Validation partition.
            test_df: Test partition.
            applicant_id_column: Column name containing applicant UUIDs.

        Returns:
            LeakageAuditReport: Detection of identity leakage across partitions.
        """
        train_apps = set(train_df[applicant_id_column].dropna().unique()) if applicant_id_column in train_df.columns else set()
        val_apps = set(val_df[applicant_id_column].dropna().unique()) if val_df is not None and applicant_id_column in val_df.columns else set()
        test_apps = set(test_df[applicant_id_column].dropna().unique()) if test_df is not None and applicant_id_column in test_df.columns else set()

        over_train_val = sorted(list(train_apps & val_apps))
        over_train_test = sorted(list(train_apps & test_apps))
        over_val_test = sorted(list(val_apps & test_apps))

        leakage_detected = (
            len(over_train_val) > 0 or len(over_train_test) > 0 or len(over_val_test) > 0
        )

        return LeakageAuditReport(
            leakage_detected=leakage_detected,
            train_applicant_count=len(train_apps),
            val_applicant_count=len(val_apps),
            test_applicant_count=len(test_apps),
            overlapping_train_val=over_train_val,
            overlapping_train_test=over_train_test,
            overlapping_val_test=over_val_test,
        )
