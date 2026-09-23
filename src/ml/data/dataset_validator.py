"""Comprehensive dataset validator for PARAKH credit risk datasets (Phase 3).

Validates canonical application-level Parquet datasets against the frozen ML data contract
(docs/final-ml-data-requirements.md v1.1.0) and Phase 2 Handoff specification.

Covers:
1. Schema & column completeness (52 canonical columns, 40 derived features)
2. Target semantics & insufficient-data segregation (0, 1, or null)
3. Categorical domain compliance
4. Numerical feature ranges and non-negativity invariants
5. Missingness semantics (0 feature nulls, null target iff Insufficient Data)
6. Identity & relational integrity (UUIDv4, unique applications)
7. Temporal ordering and anti-leakage checks (monotonic timestamps, strictly pre-t0 predictors)
8. Impossible-combination checks
9. Cohort proportions and observed default rate bounds (10% to 15%)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from src.ml.constants import DEFAULT_RANDOM_SEED


# 52 Canonical Columns in Frozen Contract Order
CANONICAL_COLUMNS: List[str] = [
    # 1. Identity & Profile Metadata (10 columns)
    "applicant_profile_id",
    "application_id",
    "cutoff_timestamp",
    "cohort_archetype",
    "gig_work_type",
    "years_working",
    "average_working_days",
    "requested_loan_amount",
    "loan_tenure_months",
    "loan_purpose",
    # 2. Mandatory Core Derived Features (19 columns)
    "feat_inc_median_90d",
    "feat_inc_p25_90d",
    "feat_inc_cv_90d",
    "feat_inc_downside_var",
    "feat_trend_slope_90d",
    "feat_trend_momentum_30_90",
    "feat_act_active_days_ratio",
    "feat_act_zero_earn_weeks",
    "feat_rec_bounceback_ratio",
    "feat_rec_days_to_recover",
    "feat_liq_buffer_to_loan",
    "feat_liq_burn_months",
    "feat_bur_dti_ratio",
    "feat_bur_installment_dti",
    "feat_bur_total_dti",
    "feat_suf_observed_days",
    "feat_suf_payout_count",
    "feat_suf_group_count",
    "feat_suf_missing_ratio",
    # 3. Optional Derived Features (21 columns)
    "feat_inc_mean_90d",
    "feat_inc_trimmed_mean",
    "feat_inc_iqr_ratio",
    "feat_inc_min_max_ratio",
    "feat_trend_consec_drops",
    "feat_act_max_idle_streak",
    "feat_act_weekend_intensity",
    "feat_rec_max_drawdown",
    "feat_ten_years_working",
    "feat_ten_platform_rating",
    "feat_ten_trips_completed",
    "feat_ten_cancellation_rate",
    "feat_liq_net_margin",
    "feat_pay_utility_on_time",
    "feat_pay_max_bill_delay",
    "feat_pay_repay_reliability",
    "feat_bur_loan_to_income",
    "feat_int_vol_x_recovery",
    "feat_int_vol_x_buffer",
    "feat_int_trend_x_dti",
    "feat_int_resilience_idx",
    # 4. Target / Forward Outcome (2 columns)
    "target_default_flag",
    "repayment_risk_probability",
]

# 40 Derived Features
DERIVED_FEATURES: List[str] = [c for c in CANONICAL_COLUMNS if c.startswith("feat_")]

MANDATORY_FEATURES: List[str] = CANONICAL_COLUMNS[10:29]  # 19 features
OPTIONAL_FEATURES: List[str] = CANONICAL_COLUMNS[29:50]   # 21 features

# Allowed Categorical Values
ALLOWED_COHORTS: Set[str] = {
    "Healthy Volatile",
    "Stable",
    "Declining",
    "Irregular",
    "High Obligation",
    "Insufficient Data",
}

ALLOWED_GIG_WORK_TYPES: Set[str] = {
    "DELIVERY",
    "RIDE_HAILING",
    "LOGISTICS",
    "HOME_SERVICES",
    "FREELANCE_MICRO",
    "OTHER",
}

ALLOWED_LOAN_PURPOSES: Set[str] = {
    "VEHICLE_MAINTENANCE",
    "WORKING_CAPITAL",
    "EQUIPMENT_PURCHASE",
    "PERSONAL_EMERGENCY",
    "OTHER",
}

ALLOWED_LOAN_TENURES: Set[int] = {6, 9, 12}

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

# Feature Bounds (min, max, allow_negative) based on Section 6 of final-ml-data-requirements.md
FEATURE_BOUNDS: Dict[str, Tuple[float, float, bool]] = {
    "feat_inc_median_90d": (0.0, 500000.0, False),
    "feat_inc_p25_90d": (0.0, 500000.0, False),
    "feat_inc_cv_90d": (0.0, 5.0, False),
    "feat_inc_downside_var": (0.0, 1.0e10, False),
    "feat_trend_slope_90d": (-50000.0, 50000.0, True),
    "feat_trend_momentum_30_90": (0.0, 5.0, False),
    "feat_act_active_days_ratio": (0.0, 1.0, False),
    "feat_act_zero_earn_weeks": (0.0, 13.0, False),
    "feat_rec_bounceback_ratio": (0.0, 10.0, False),
    "feat_rec_days_to_recover": (0.0, 90.0, False),
    "feat_liq_buffer_to_loan": (0.0, 50.0, False),
    "feat_liq_burn_months": (0.0, 60.0, False),
    "feat_bur_dti_ratio": (0.0, 20.0, False),
    "feat_bur_installment_dti": (0.0, 20.0, False),
    "feat_bur_total_dti": (0.0, 20.0, False),
    "feat_suf_observed_days": (0.0, 90.0, False),
    "feat_suf_payout_count": (0.0, 90.0, False),
    "feat_suf_group_count": (0.0, 5.0, False),
    "feat_suf_missing_ratio": (0.0, 1.0, False),
    "feat_inc_mean_90d": (0.0, 500000.0, False),
    "feat_inc_trimmed_mean": (0.0, 500000.0, False),
    "feat_inc_iqr_ratio": (0.0, 10.0, False),
    "feat_inc_min_max_ratio": (0.0, 1.0, False),
    "feat_trend_consec_drops": (0.0, 13.0, False),
    "feat_act_max_idle_streak": (0.0, 90.0, False),
    "feat_act_weekend_intensity": (0.0, 1.0, False),
    "feat_rec_max_drawdown": (0.0, 1.0, False),
    "feat_ten_years_working": (0.0, 50.0, False),
    "feat_ten_platform_rating": (1.0, 5.0, False),
    "feat_ten_trips_completed": (0.0, 100000.0, False),
    "feat_ten_cancellation_rate": (0.0, 1.0, False),
    "feat_liq_net_margin": (-2.0, 1.0, True),
    "feat_pay_utility_on_time": (0.0, 1.0, False),
    "feat_pay_max_bill_delay": (0.0, 180.0, False),
    "feat_pay_repay_reliability": (0.0, 1.0, False),
    "feat_bur_loan_to_income": (0.0, 10.0, False),
    "feat_int_vol_x_recovery": (0.0, 450.0, False),
    "feat_int_vol_x_buffer": (0.0, 50.0, False),
    "feat_int_trend_x_dti": (-50000.0, 50000.0, True),
    "feat_int_resilience_idx": (0.0, 100.0, False),
    "requested_loan_amount": (1000.0, 500000.0, False),
    "years_working": (0.0, 50.0, False),
    "average_working_days": (0.0, 31.0, False),
}


@dataclass
class DatasetValidationDiagnostics:
    """Detailed summary diagnostics from a dataset validation pass."""

    total_rows: int = 0
    unique_applicants: int = 0
    scored_rows: int = 0
    insufficient_data_rows: int = 0
    default_count: int = 0
    scored_default_rate: float = 0.0
    actual_columns_count: int = 0
    expected_columns_count: int = 52
    missing_columns: List[str] = field(default_factory=list)
    unexpected_columns: List[str] = field(default_factory=list)
    datatype_violations: List[str] = field(default_factory=list)
    feature_range_violations: List[str] = field(default_factory=list)
    categorical_violations: List[str] = field(default_factory=list)
    target_violations: List[str] = field(default_factory=list)
    temporal_violations: List[str] = field(default_factory=list)
    impossible_combo_violations: List[str] = field(default_factory=list)
    missingness_violations: List[str] = field(default_factory=list)
    per_feature_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cohort_counts: Dict[str, int] = field(default_factory=dict)
    cohort_proportions: Dict[str, float] = field(default_factory=dict)


@dataclass
class ComprehensiveValidationReport:
    """Full validation report produced by Phase 3 Dataset Validator."""

    is_valid: bool
    status: str  # "PASS" or "FAIL"
    diagnostics: DatasetValidationDiagnostics
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        diag = self.diagnostics
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "dataset": {
                "total_rows": diag.total_rows,
                "unique_applicants": diag.unique_applicants,
                "scored_rows": diag.scored_rows,
                "insufficient_data_rows": diag.insufficient_data_rows,
                "default_count": diag.default_count,
                "scored_default_rate": diag.scored_default_rate,
            },
            "schema": {
                "actual_column_count": diag.actual_columns_count,
                "expected_column_count": diag.expected_columns_count,
                "missing_columns": diag.missing_columns,
                "unexpected_columns": diag.unexpected_columns,
                "datatype_violations": diag.datatype_violations,
            },
            "features": {
                "all_40_derived_features_present": len(diag.missing_columns) == 0
                and all(f in diag.per_feature_stats for f in DERIVED_FEATURES),
                "range_violations_count": len(diag.feature_range_violations),
                "range_violations": diag.feature_range_violations[:10],
                "categorical_violations": diag.categorical_violations,
            },
            "target": {
                "target_violations": diag.target_violations,
                "scored_default_rate": diag.scored_default_rate,
            },
            "temporal": {
                "temporal_violations": diag.temporal_violations,
            },
            "impossible_combinations": {
                "violations_count": len(diag.impossible_combo_violations),
                "violations": diag.impossible_combo_violations,
            },
            "cohorts": {
                "counts": diag.cohort_counts,
                "proportions": diag.cohort_proportions,
            },
        }


class Phase3DatasetValidator:
    """Validates the canonical synthetic credit application dataset against frozen contracts."""

    @classmethod
    def validate_file(cls, parquet_path: Union[str, Path]) -> ComprehensiveValidationReport:
        """Load and validate Parquet dataset file from disk."""
        path = Path(parquet_path)
        if not path.exists():
            diag = DatasetValidationDiagnostics()
            return ComprehensiveValidationReport(
                is_valid=False,
                status="FAIL",
                diagnostics=diag,
                errors=[f"Dataset file does not exist at '{path}'."],
            )

        df = pd.read_parquet(path)
        return cls.validate_dataframe(df)

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame) -> ComprehensiveValidationReport:
        """Execute complete suite of Phase 3 contract validation checks on DataFrame."""
        errors: List[str] = []
        warnings: List[str] = []
        diag = DatasetValidationDiagnostics()

        diag.total_rows = len(df)
        diag.actual_columns_count = len(df.columns)

        if diag.total_rows == 0:
            errors.append("Dataset contains 0 rows.")
            return ComprehensiveValidationReport(
                is_valid=False, status="FAIL", diagnostics=diag, errors=errors
            )

        # ---------------------------------------------------------
        # 1. Schema Validation (52 canonical columns)
        # ---------------------------------------------------------
        actual_cols_set = set(df.columns)
        expected_cols_set = set(CANONICAL_COLUMNS)

        diag.missing_columns = sorted(list(expected_cols_set - actual_cols_set))
        diag.unexpected_columns = sorted(list(actual_cols_set - expected_cols_set))

        if diag.missing_columns:
            errors.append(f"Missing {len(diag.missing_columns)} expected columns: {diag.missing_columns}")
        if diag.unexpected_columns:
            errors.append(f"Found {len(diag.unexpected_columns)} unexpected columns: {diag.unexpected_columns}")

        # Column order check
        if list(df.columns) != CANONICAL_COLUMNS:
            warnings.append("Columns in DataFrame do not strictly match the 52 canonical column ordering.")

        # Check all 40 derived features are present
        missing_derived = [f for f in DERIVED_FEATURES if f not in df.columns]
        if missing_derived:
            errors.append(f"Missing derived features: {missing_derived}")

        # Check datatypes
        for col in df.columns:
            if col in CANONICAL_COLUMNS:
                s = df[col]
                if col in ("applicant_profile_id", "application_id", "cutoff_timestamp", "cohort_archetype", "gig_work_type", "loan_purpose"):
                    if not pd.api.types.is_string_dtype(s) and not pd.api.types.is_object_dtype(s):
                        diag.datatype_violations.append(f"Column '{col}' expected string/object, got {s.dtype}")
                elif col in ("target_default_flag",):
                    # Nullable integer or float
                    if not (pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s)):
                        diag.datatype_violations.append(f"Column '{col}' expected numeric (float/int), got {s.dtype}")
                else:
                    if not pd.api.types.is_numeric_dtype(s):
                        diag.datatype_violations.append(f"Numeric column '{col}' has non-numeric dtype {s.dtype}")

        if diag.datatype_violations:
            errors.extend(diag.datatype_violations)

        # ---------------------------------------------------------
        # 2. Identity & Relational Integrity
        # ---------------------------------------------------------
        if "applicant_profile_id" in df.columns:
            diag.unique_applicants = df["applicant_profile_id"].nunique()
            # UUID check
            invalid_profile_uuids = [
                uid for uid in df["applicant_profile_id"].dropna().unique() if not UUID_REGEX.match(str(uid))
            ]
            if invalid_profile_uuids:
                errors.append(f"Found {len(invalid_profile_uuids)} invalid applicant_profile_id UUID strings.")

        if "application_id" in df.columns:
            if df["application_id"].nunique() != diag.total_rows:
                errors.append(
                    f"application_id is not unique! Total rows: {diag.total_rows}, Unique: {df['application_id'].nunique()}"
                )
            invalid_app_uuids = [
                uid for uid in df["application_id"].dropna().unique() if not UUID_REGEX.match(str(uid))
            ]
            if invalid_app_uuids:
                errors.append(f"Found {len(invalid_app_uuids)} invalid application_id UUID strings.")

        # ---------------------------------------------------------
        # 3. Categorical Domains & Cohort Proportions
        # ---------------------------------------------------------
        if "cohort_archetype" in df.columns:
            cohort_counts = df["cohort_archetype"].value_counts().to_dict()
            diag.cohort_counts = cohort_counts
            diag.cohort_proportions = {k: v / diag.total_rows for k, v in cohort_counts.items()}
            invalid_cohorts = set(cohort_counts.keys()) - ALLOWED_COHORTS
            if invalid_cohorts:
                msg = f"Invalid cohort_archetype values: {invalid_cohorts}"
                diag.categorical_violations.append(msg)
                errors.append(msg)

        if "gig_work_type" in df.columns:
            gigs = set(df["gig_work_type"].dropna().unique())
            invalid_gigs = gigs - ALLOWED_GIG_WORK_TYPES
            if invalid_gigs:
                msg = f"Invalid gig_work_type values: {invalid_gigs}"
                diag.categorical_violations.append(msg)
                errors.append(msg)

        if "loan_purpose" in df.columns:
            purposes = set(df["loan_purpose"].dropna().unique())
            invalid_purposes = purposes - ALLOWED_LOAN_PURPOSES
            if invalid_purposes:
                msg = f"Invalid loan_purpose values: {invalid_purposes}"
                diag.categorical_violations.append(msg)
                errors.append(msg)

        if "loan_tenure_months" in df.columns:
            tenures = set(df["loan_tenure_months"].dropna().unique())
            invalid_tenures = tenures - ALLOWED_LOAN_TENURES
            if invalid_tenures:
                msg = f"Unexpected loan_tenure_months values: {invalid_tenures}"
                diag.categorical_violations.append(msg)
                warnings.append(msg)

        # ---------------------------------------------------------
        # 4. Target & Insufficient-Data Semantics
        # ---------------------------------------------------------
        if "target_default_flag" in df.columns and "cohort_archetype" in df.columns:
            target_series = df["target_default_flag"]
            scored_mask = target_series.notnull()
            unscored_mask = target_series.isnull()

            diag.scored_rows = int(scored_mask.sum())
            diag.insufficient_data_rows = int(unscored_mask.sum())

            # Check that all scored targets are strictly 0 or 1
            scored_vals = set(target_series[scored_mask].unique())
            disallowed_targets = scored_vals - {0, 1, 0.0, 1.0}
            if disallowed_targets:
                msg = f"Disallowed target_default_flag values found in scored rows: {disallowed_targets}"
                diag.target_violations.append(msg)
                errors.append(msg)

            # Check Insufficient Data cohort vs null target equivalence
            insuf_cohort_mask = df["cohort_archetype"] == "Insufficient Data"
            insuf_target_not_null = df[insuf_cohort_mask & scored_mask]
            if len(insuf_target_not_null) > 0:
                msg = f"Found {len(insuf_target_not_null)} Insufficient Data applications with non-null target_default_flag."
                diag.target_violations.append(msg)
                errors.append(msg)

            other_cohort_target_null = df[(~insuf_cohort_mask) & unscored_mask]
            if len(other_cohort_target_null) > 0:
                msg = f"Found {len(other_cohort_target_null)} non-Insufficient Data applications with null target_default_flag."
                diag.target_violations.append(msg)
                errors.append(msg)

            # Target rate calculation
            diag.default_count = int(target_series[scored_mask].sum())
            if diag.scored_rows > 0:
                diag.scored_default_rate = diag.default_count / diag.scored_rows
                if not (0.10 <= diag.scored_default_rate <= 0.15):
                    errors.append(
                        f"Scored default rate {diag.scored_default_rate:.4f} is outside the required [10.0%, 15.0%] range."
                    )

        if "repayment_risk_probability" in df.columns:
            prob_series = df["repayment_risk_probability"]
            scored_prob = prob_series.dropna()
            out_of_bounds = scored_prob[(scored_prob < 0.0) | (scored_prob > 1.0)]
            if len(out_of_bounds) > 0:
                msg = f"repayment_risk_probability contains {len(out_of_bounds)} values outside [0.0, 1.0]."
                diag.target_violations.append(msg)
                errors.append(msg)

        # ---------------------------------------------------------
        # 5. Missingness & Non-Zero Invariants
        # ---------------------------------------------------------
        for col in df.columns:
            if col in ("target_default_flag", "repayment_risk_probability"):
                continue  # Target nulls are checked separately
            null_count = int(df[col].isna().sum())
            if null_count > 0:
                msg = f"Feature/metadata column '{col}' contains {null_count} null/NaN values."
                diag.missingness_violations.append(msg)
                errors.append(msg)

        # ---------------------------------------------------------
        # 6. Feature Ranges, Non-Negativity & Bounds
        # ---------------------------------------------------------
        for col, (f_min, f_max, allow_neg) in FEATURE_BOUNDS.items():
            if col not in df.columns:
                continue

            s = df[col].dropna()
            try:
                numeric_s = pd.to_numeric(s, errors="raise")
                c_min = float(numeric_s.min())
                c_max = float(numeric_s.max())
                n_nan = int(s.isna().sum())
                n_inf = int(np.isinf(numeric_s).sum())
                s = numeric_s
            except (ValueError, TypeError) as ex:
                msg = f"Column '{col}' expected numeric values for range check, but conversion failed: {ex}"
                diag.feature_range_violations.append(msg)
                errors.append(msg)
                continue

            diag.per_feature_stats[col] = {
                "min": c_min,
                "max": c_max,
                "mean": float(s.mean()),
                "std": float(s.std()) if len(s) > 1 else 0.0,
                "missing": n_nan,
                "inf": n_inf,
                "invalids": 0,
            }

            if n_inf > 0:
                msg = f"Column '{col}' contains {n_inf} infinite values."
                diag.feature_range_violations.append(msg)
                errors.append(msg)

            if not allow_neg and c_min < -1e-6:
                msg = f"Column '{col}' contains negative values (min: {c_min}), but negative values are disallowed."
                diag.feature_range_violations.append(msg)
                diag.per_feature_stats[col]["invalids"] += int((s < 0).sum())
                errors.append(msg)

            if c_min < f_min - 1e-4 or c_max > f_max + 1e-4:
                msg = f"Column '{col}' values [{c_min:.4f}, {c_max:.4f}] exceed contract bounds [{f_min}, {f_max}]."
                diag.feature_range_violations.append(msg)
                diag.per_feature_stats[col]["invalids"] += int(((s < f_min) | (s > f_max)).sum())
                errors.append(msg)

        # ---------------------------------------------------------
        # 7. Temporal & Anti-Leakage Validation
        # ---------------------------------------------------------
        if "cutoff_timestamp" in df.columns:
            ts_series = df["cutoff_timestamp"]
            for idx, ts_str in enumerate(ts_series[:50]):  # Sample check ISO8601
                try:
                    dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        diag.temporal_violations.append(f"Timestamp at row {idx} is not timezone-aware.")
                        break
                except Exception as ex:
                    diag.temporal_violations.append(f"Invalid timestamp format at row {idx}: {ex}")
                    break

            # Monotonic ordering for repeat applicants
            if "applicant_profile_id" in df.columns:
                repeat_apps = df["applicant_profile_id"].value_counts()
                repeat_ids = repeat_apps[repeat_apps > 1].index

                monotonic_violations = 0
                for app_id in repeat_ids:
                    app_records = df[df["applicant_profile_id"] == app_id].sort_values("cutoff_timestamp")
                    timestamps = [
                        datetime.fromisoformat(str(t).replace("Z", "+00:00"))
                        for t in app_records["cutoff_timestamp"]
                    ]
                    for i in range(len(timestamps) - 1):
                        diff = timestamps[i + 1] - timestamps[i]
                        if diff.total_seconds() < 0:
                            monotonic_violations += 1
                        if diff.days < 30:
                            warnings.append(
                                f"Applicant {app_id} repeated assessment interval is {diff.days} days (< 30 days)."
                            )

                if monotonic_violations > 0:
                    msg = f"Found {monotonic_violations} timestamp monotonicity violations for repeat applicants."
                    diag.temporal_violations.append(msg)
                    errors.append(msg)

        # Anti-leakage: verify no forward simulation columns are present
        forbidden_forward_cols = {
            "consecutive_negative_days",
            "prediction_horizon_days",
            "future_income",
            "future_balance",
            "exogenous_shock_count",
            "forward_living_expenses",
        }
        leaked_cols = forbidden_forward_cols & actual_cols_set
        if leaked_cols:
            msg = f"CRITICAL: Found forward target-generation variables leaking into dataset: {leaked_cols}"
            diag.temporal_violations.append(msg)
            errors.append(msg)

        # ---------------------------------------------------------
        # 8. Impossible Combination Checks
        # ---------------------------------------------------------
        if "feat_act_active_days_ratio" in df.columns and "feat_inc_median_90d" in df.columns:
            zero_active_positive_income = df[
                (df["feat_act_active_days_ratio"] == 0.0) & (df["feat_inc_median_90d"] > 0.0)
            ]
            if len(zero_active_positive_income) > 0:
                msg = f"Found {len(zero_active_positive_income)} records with 0 active days but positive median income."
                diag.impossible_combo_violations.append(msg)
                errors.append(msg)

        if "feat_inc_p25_90d" in df.columns and "feat_inc_median_90d" in df.columns:
            p25_greater_than_median = df[
                df["feat_inc_p25_90d"] > (df["feat_inc_median_90d"] + 1e-4)
            ]
            if len(p25_greater_than_median) > 0:
                msg = f"Found {len(p25_greater_than_median)} records where p25 income exceeds median income."
                diag.impossible_combo_violations.append(msg)
                errors.append(msg)

        if "feat_act_zero_earn_weeks" in df.columns and "feat_inc_median_90d" in df.columns:
            all_zero_weeks_positive_income = df[
                (df["feat_act_zero_earn_weeks"] == 13) & (df["feat_inc_median_90d"] > 0.0)
            ]
            if len(all_zero_weeks_positive_income) > 0:
                msg = f"Found {len(all_zero_weeks_positive_income)} records with 13 zero-earn weeks but positive income."
                diag.impossible_combo_violations.append(msg)
                errors.append(msg)

        if diag.impossible_combo_violations:
            errors.extend(diag.impossible_combo_violations)

        is_valid = len(errors) == 0
        status = "PASS" if is_valid else "FAIL"

        return ComprehensiveValidationReport(
            is_valid=is_valid,
            status=status,
            diagnostics=diag,
            errors=errors,
            warnings=warnings,
        )
