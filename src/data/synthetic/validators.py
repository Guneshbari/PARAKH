"""
PARAKH Synthetic Credit Application Generator - Dataset Validation & Leakage Checks (P2-T09)
Implements the validation layer for the synthetic credit-risk dataset.
Validates assembled application-level records against the frozen ML data contract
(docs/final-ml-data-requirements.md v1.1.0).

Core Principle: Validation detects violations.
It NEVER alters, clips, repairs, relabels, downsamples, fills, or modifies data.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.data.synthetic.config import (
    APPLICATION_TIMESTAMP_END,
    APPLICATION_TIMESTAMP_START,
    COHORT_ARCHETYPES,
    COHORT_DECLINING,
    COHORT_HEALTHY_VOLATILE,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    COHORT_IRREGULAR,
    COHORT_PROPORTIONS,
    COHORT_STABLE,
    GIG_WORK_TYPES,
    INSOLVENCY_GRACE_PERIOD_DAYS,
    LOAN_AMOUNT_MAX,
    LOAN_AMOUNT_MIN,
    LOAN_PURPOSES,
    LOAN_TENURES,
    MASTER_SEED,
    OBSERVATION_WINDOW_DAYS,
    PREDICTION_HORIZON_DAYS_MAX,
    PREDICTION_HORIZON_DAYS_MIN,
    REPEAT_INTERVAL_DAYS_MIN,
)
from src.data.synthetic.exceptions import (
    CohortValidationError,
    FeatureRangeError,
    IdentityValidationError,
    ImpossibleCombinationError,
    MissingnessViolationError,
    ReproducibilityError,
    SchemaError,
    TargetValidationError,
    TemporalLeakageError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    FINAL_DATASET_SCHEMA,
    Applicant,
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    ApplicationHistoricalData,
    AssembledApplicationRecord,
    ColumnCategory,
    ColumnDefinition,
    DataType,
    DerivedFeatures,
    FinalRecord,
    ForwardOutcome,
    get_column_names,
    get_feature_matrix_columns,
    get_mandatory_feature_columns,
    get_optional_feature_columns,
    get_interaction_feature_columns,
)


# ==============================================================================
# 1. CONSTANTS & PHYSICAL BOUNDS CONTRACT
# ==============================================================================

UUIDV4_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Contractual feature bounds (hard min, hard max) from Sections 6.2 and 21.3
FEATURE_BOUNDS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    # Raw profile & loan fields
    "years_working": (0.0, 50.0),
    "average_working_days": (0, 31),
    "requested_loan_amount": (LOAN_AMOUNT_MIN, LOAN_AMOUNT_MAX),
    "loan_tenure_months": (1, 60),

    # 19 Mandatory Core Features
    "feat_inc_median_90d": (0.0, 500000.0),
    "feat_inc_p25_90d": (0.0, 500000.0),
    "feat_inc_cv_90d": (0.0, 5.0),
    "feat_inc_downside_var": (0.0, 1.0e10),
    "feat_trend_slope_90d": (-50000.0, 50000.0),
    "feat_trend_momentum_30_90": (0.0, 5.0),
    "feat_act_active_days_ratio": (0.0, 1.0),
    "feat_act_zero_earn_weeks": (0, 13),
    "feat_rec_bounceback_ratio": (0.0, 10.0),
    "feat_rec_days_to_recover": (0.0, 90.0),
    "feat_liq_buffer_to_loan": (0.0, 50.0),
    "feat_liq_burn_months": (0.0, 60.0),
    "feat_bur_dti_ratio": (0.0, 20.0),
    "feat_bur_installment_dti": (0.0, 20.0),
    "feat_bur_total_dti": (0.0, 20.0),
    "feat_suf_observed_days": (0, 90),
    "feat_suf_payout_count": (0, 90),
    "feat_suf_group_count": (0, 5),
    "feat_suf_missing_ratio": (0.0, 1.0),

    # 17 Optional Extended Features (when populated)
    "feat_inc_mean_90d": (0.0, 500000.0),
    "feat_inc_trimmed_mean": (0.0, 500000.0),
    "feat_inc_iqr_ratio": (0.0, 10.0),
    "feat_inc_min_max_ratio": (0.0, 1.0),
    "feat_trend_consec_drops": (0, 13),
    "feat_act_max_idle_streak": (0, 90),
    "feat_act_weekend_intensity": (0.0, 1.0),
    "feat_rec_max_drawdown": (0.0, 1.0),
    "feat_ten_years_working": (0.0, 50.0),
    "feat_ten_platform_rating": (1.0, 5.0),
    "feat_ten_trips_completed": (0, 100000),
    "feat_ten_cancellation_rate": (0.0, 1.0),
    "feat_liq_net_margin": (-2.0, 1.0),
    "feat_pay_utility_on_time": (0.0, 1.0),
    "feat_pay_max_bill_delay": (0, 180),
    "feat_pay_repay_reliability": (0.0, 1.0),
    "feat_bur_loan_to_income": (0.0, 10.0),

    # 4 Interaction Features
    "feat_int_vol_x_recovery": (0.0, 450.0),
    "feat_int_vol_x_buffer": (0.0, 50.0),
    "feat_int_trend_x_dti": (-50000.0, 50000.0),
    "feat_int_resilience_idx": (0.0, 100.0),

    # Targets (when populated)
    "repayment_risk_probability": (0.0, 1.0),
}

# Categorical allowed domains
CATEGORICAL_DOMAINS: Dict[str, Set[str]] = {
    "cohort_archetype": set(COHORT_ARCHETYPES),
    "gig_work_type": set(GIG_WORK_TYPES),
    "loan_purpose": set(LOAN_PURPOSES),
}


# ==============================================================================
# 2. VALIDATION DATA STRUCTURES & REPORT
# ==============================================================================

@dataclass
class ValidationErrorDetail:
    """Detailed record of a specific validation rule violation."""
    validator: str
    record_id: Optional[str]
    field_name: Optional[str]
    actual_value: Any
    expected_rule: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator": self.validator,
            "record_id": self.record_id,
            "field_name": self.field_name,
            "actual_value": str(self.actual_value),
            "expected_rule": self.expected_rule,
            "message": self.message,
        }


@dataclass
class DatasetValidationReport:
    """
    Comprehensive structured validation report for the synthetic credit dataset.
    Provides machine-readable metrics and diagnostic status across all 14 areas.
    """
    validation_timestamp: str
    row_count: int
    unique_applicants: int
    unique_applications: int
    cohort_counts: Dict[str, int]
    cohort_proportions: Dict[str, float]
    scored_count: int
    unscored_count: int
    default_count: int
    default_rate: float
    feature_missingness: Dict[str, int]
    feature_ranges: Dict[str, Dict[str, Any]]
    categorical_distributions: Dict[str, Dict[str, int]]
    temporal_checks: Dict[str, Any]
    leakage_checks: Dict[str, Any]
    impossible_combination_checks: Dict[str, Any]
    determinism_result: Dict[str, Any]
    overall_status: str  # "PASS" or "FAIL"
    validation_errors: List[ValidationErrorDetail] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes report into standard dictionary."""
        return {
            "validation_timestamp": self.validation_timestamp,
            "row_count": self.row_count,
            "unique_applicants": self.unique_applicants,
            "unique_applications": self.unique_applications,
            "cohort_counts": self.cohort_counts,
            "cohort_proportions": self.cohort_proportions,
            "scored_count": self.scored_count,
            "unscored_count": self.unscored_count,
            "default_count": self.default_count,
            "default_rate": self.default_rate,
            "feature_missingness": self.feature_missingness,
            "feature_ranges": self.feature_ranges,
            "categorical_distributions": self.categorical_distributions,
            "temporal_checks": self.temporal_checks,
            "leakage_checks": self.leakage_checks,
            "impossible_combination_checks": self.impossible_combination_checks,
            "determinism_result": self.determinism_result,
            "overall_status": self.overall_status,
            "validation_errors": [e.to_dict() for e in self.validation_errors],
            "validation_warnings": list(self.validation_warnings),
        }

    def summary(self) -> str:
        """Produces a human-readable text summary of the validation report."""
        lines = [
            "=" * 78,
            f"PARAKH SYNTHETIC DATASET VALIDATION REPORT — Status: {self.overall_status}",
            "=" * 78,
            f"Timestamp:          {self.validation_timestamp}",
            f"Total Applications: {self.row_count}",
            f"Unique Applicants:  {self.unique_applicants}",
            f"Unique Applications:{self.unique_applications}",
            f"Scored Records:     {self.scored_count}",
            f"Unscored Records:   {self.unscored_count}",
            f"Defaults Count:     {self.default_count}",
            f"Observed Default Rate: {self.default_rate:.2%} (Frozen Expectation: 10.0% - 15.0%)",
            "-" * 78,
            "COHORT PROPORTIONS:",
        ]
        for c, count in self.cohort_counts.items():
            prop = self.cohort_proportions.get(c, 0.0)
            exp = COHORT_PROPORTIONS.get(c, 0.0)
            lines.append(f"  - {c:20s}: {count:5d} ({prop:6.2%}, Expected: {exp:6.2%})")

        lines.extend([
            "-" * 78,
            f"LEAKAGE CHECKS:     {'PASSED' if self.leakage_checks.get('passed') else 'FAILED'}",
            f"IMPOSSIBLE COMBOS:  {'0 Violations' if self.impossible_combination_checks.get('violations_count') == 0 else f'{self.impossible_combination_checks.get("violations_count")} Violations'}",
            f"DETERMINISM TEST:   {'PASSED' if self.determinism_result.get('passed') else 'FAILED'}",
            f"ERRORS DETECTED:    {len(self.validation_errors)}",
            f"WARNINGS DETECTED:  {len(self.validation_warnings)}",
        ])

        if self.validation_warnings:
            lines.append("-" * 78)
            lines.append("WARNINGS:")
            for w in self.validation_warnings:
                lines.append(f"  [WARN] {w}")

        if self.validation_errors:
            lines.append("-" * 78)
            lines.append("ERRORS (First 10 shown):")
            for err in self.validation_errors[:10]:
                lines.append(f"  [ERR] {err.validator}: {err.message}")
            if len(self.validation_errors) > 10:
                lines.append(f"  ... and {len(self.validation_errors) - 10} more errors.")

        lines.append("=" * 78)
        return "\n".join(lines)


# ==============================================================================
# 3. RECORD COERCION / EXTRACTION HELPER
# ==============================================================================

def to_record_dict(record: Union[AssembledApplicationRecord, FinalRecord, Dict[str, Any]]) -> Dict[str, Any]:
    """Extracts standard dictionary representation from any valid record type."""
    if isinstance(record, (AssembledApplicationRecord, FinalRecord)):
        return record.to_dict()
    elif isinstance(record, dict):
        return record
    raise TypeError(f"Expected AssembledApplicationRecord, FinalRecord, or dict, got {type(record)}")


# ==============================================================================
# 4. AREA 1: SCHEMA VALIDATION
# ==============================================================================

def validate_record_schema(
    record_dict: Dict[str, Any],
    check_order: bool = True,
) -> List[ValidationErrorDetail]:
    """
    Validates a single record against the canonical 52-column FINAL_DATASET_SCHEMA:
    - Exactly 52 expected columns
    - No missing required columns
    - No unexpected extra columns
    - Correct column ordering where applicable
    - Correct physical data types
    - Correct nullable vs non-nullable semantics
    """
    errors: List[ValidationErrorDetail] = []
    record_id = str(record_dict.get("application_id", "UNKNOWN"))
    expected_cols = get_column_names()
    expected_set = set(expected_cols)
    actual_cols = list(record_dict.keys())
    actual_set = set(actual_cols)

    # 1. Missing columns
    missing_cols = expected_set - actual_set
    if missing_cols:
        errors.append(
            ValidationErrorDetail(
                validator="SchemaValidator",
                record_id=record_id,
                field_name=None,
                actual_value=f"Missing: {sorted(missing_cols)}",
                expected_rule="Must contain all 52 canonical columns",
                message=f"Record {record_id} is missing {len(missing_cols)} required columns: {sorted(missing_cols)}",
            )
        )

    # 2. Unexpected columns
    unexpected_cols = actual_set - expected_set
    if unexpected_cols:
        errors.append(
            ValidationErrorDetail(
                validator="SchemaValidator",
                record_id=record_id,
                field_name=None,
                actual_value=f"Unexpected: {sorted(unexpected_cols)}",
                expected_rule="Must contain only the 52 canonical columns",
                message=f"Record {record_id} contains {len(unexpected_cols)} unexpected columns: {sorted(unexpected_cols)}",
            )
        )

    # 3. Canonical column ordering (if no missing or unexpected columns)
    if check_order and not missing_cols and not unexpected_cols:
        if actual_cols != expected_cols:
            errors.append(
                ValidationErrorDetail(
                    validator="SchemaValidator",
                    record_id=record_id,
                    field_name=None,
                    actual_value="Incorrect ordering",
                    expected_rule="Columns must strictly follow FINAL_DATASET_SCHEMA sequence",
                    message=f"Record {record_id} column order does not match canonical 52-column schema",
                )
            )

    # 4. Column data types and nullability constraints
    for col_def in FINAL_DATASET_SCHEMA:
        col_name = col_def.name
        if col_name not in record_dict:
            continue

        val = record_dict[col_name]

        # Nullability check
        if val is None:
            if not col_def.nullable:
                errors.append(
                    ValidationErrorDetail(
                        validator="SchemaValidator",
                        record_id=record_id,
                        field_name=col_name,
                        actual_value=None,
                        expected_rule="Non-nullable field cannot be None/null",
                        message=f"Record {record_id}: Non-nullable column '{col_name}' is None/null",
                    )
                )
            continue

        # Physical data type check
        if col_def.dtype == DataType.STRING:
            if not isinstance(val, str):
                errors.append(
                    ValidationErrorDetail(
                        validator="SchemaValidator",
                        record_id=record_id,
                        field_name=col_name,
                        actual_value=type(val).__name__,
                        expected_rule="Must be string (str)",
                        message=f"Record {record_id}: Column '{col_name}' expected string, got {type(val).__name__}",
                    )
                )
        elif col_def.dtype == DataType.FLOAT64:
            # Python float or int (int permitted in memory if float-compatible, but not bool!)
            if isinstance(val, bool) or not isinstance(val, (float, int)):
                errors.append(
                    ValidationErrorDetail(
                        validator="SchemaValidator",
                        record_id=record_id,
                        field_name=col_name,
                        actual_value=type(val).__name__,
                        expected_rule="Must be float (or numeric float64)",
                        message=f"Record {record_id}: Column '{col_name}' expected float, got {type(val).__name__}",
                    )
                )
            elif isinstance(val, float) and math.isnan(val) and not col_def.nullable:
                errors.append(
                    ValidationErrorDetail(
                        validator="SchemaValidator",
                        record_id=record_id,
                        field_name=col_name,
                        actual_value="NaN",
                        expected_rule="Non-nullable float column cannot be NaN",
                        message=f"Record {record_id}: Column '{col_name}' is NaN",
                    )
                )
        elif col_def.dtype == DataType.INT64:
            if isinstance(val, bool) or not isinstance(val, int):
                errors.append(
                    ValidationErrorDetail(
                        validator="SchemaValidator",
                        record_id=record_id,
                        field_name=col_name,
                        actual_value=type(val).__name__,
                        expected_rule="Must be integer (int, not bool)",
                        message=f"Record {record_id}: Column '{col_name}' expected int, got {type(val).__name__}",
                    )
                )

    return errors


# ==============================================================================
# 5. AREA 2: IDENTITY / RELATIONAL VALIDATION
# ==============================================================================

def validate_identities_and_relations(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    applications: Optional[List[Application]] = None,
    profiles: Optional[Dict[str, ApplicantProfile]] = None,
) -> List[ValidationErrorDetail]:
    """
    Validates identities and relational structures across the dataset:
    - application_id uniqueness (no duplicate applications)
    - applicant_profile_id validity (valid RFC 4122 UUIDv4)
    - application_id validity (valid RFC 4122 UUIDv4)
    - application -> applicant relationship preservation
    - no orphaned records
    - repeated assessments for the same applicant are accepted and verified
    """
    errors: List[ValidationErrorDetail] = []
    seen_application_ids: Set[str] = set()
    apps_by_applicant: Dict[str, List[str]] = {}

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = r_dict.get("application_id")
        applicant_id = r_dict.get("applicant_profile_id")

        # 1. Check application_id presence and uniqueness
        if not app_id or not isinstance(app_id, str):
            errors.append(
                ValidationErrorDetail(
                    validator="IdentityValidator",
                    record_id=str(app_id),
                    field_name="application_id",
                    actual_value=app_id,
                    expected_rule="application_id must be a non-empty string",
                    message=f"Row {idx}: Missing or invalid application_id",
                )
            )
        elif app_id in seen_application_ids:
            errors.append(
                ValidationErrorDetail(
                    validator="IdentityValidator",
                    record_id=app_id,
                    field_name="application_id",
                    actual_value=app_id,
                    expected_rule="application_id must be globally unique across dataset",
                    message=f"Duplicate application_id detected: '{app_id}'",
                )
            )
        else:
            seen_application_ids.add(app_id)
            if not UUIDV4_REGEX.match(app_id):
                errors.append(
                    ValidationErrorDetail(
                        validator="IdentityValidator",
                        record_id=app_id,
                        field_name="application_id",
                        actual_value=app_id,
                        expected_rule="Must be a valid RFC 4122 UUIDv4 string",
                        message=f"application_id '{app_id}' is not a valid UUIDv4",
                    )
                )

        # 2. Check applicant_profile_id validity
        if not applicant_id or not isinstance(applicant_id, str):
            errors.append(
                ValidationErrorDetail(
                    validator="IdentityValidator",
                    record_id=str(app_id),
                    field_name="applicant_profile_id",
                    actual_value=applicant_id,
                    expected_rule="applicant_profile_id must be a non-empty string",
                    message=f"Row {idx} (app {app_id}): Missing or invalid applicant_profile_id",
                )
            )
        else:
            if not UUIDV4_REGEX.match(applicant_id):
                errors.append(
                    ValidationErrorDetail(
                        validator="IdentityValidator",
                        record_id=str(app_id),
                        field_name="applicant_profile_id",
                        actual_value=applicant_id,
                        expected_rule="Must be a valid RFC 4122 UUIDv4 string",
                        message=f"applicant_profile_id '{applicant_id}' is not a valid UUIDv4",
                    )
                )
            if app_id:
                apps_by_applicant.setdefault(applicant_id, []).append(app_id)

    # 3. Optional raw relational mapping cross-checks
    if applications and profiles:
        app_map = {a.application_id: a for a in applications}
        for rec in records:
            r_dict = to_record_dict(rec)
            a_id = r_dict.get("application_id")
            p_id = r_dict.get("applicant_profile_id")
            if a_id in app_map:
                orig_app = app_map[a_id]
                if orig_app.applicant_profile_id != p_id:
                    errors.append(
                        ValidationErrorDetail(
                            validator="IdentityValidator",
                            record_id=a_id,
                            field_name="applicant_profile_id",
                            actual_value=p_id,
                            expected_rule=f"Must match source application.applicant_profile_id ({orig_app.applicant_profile_id})",
                            message=f"Relational mismatch for app '{a_id}': record has '{p_id}', application has '{orig_app.applicant_profile_id}'",
                        )
                    )
            if p_id not in profiles:
                errors.append(
                    ValidationErrorDetail(
                        validator="IdentityValidator",
                        record_id=a_id,
                        field_name="applicant_profile_id",
                        actual_value=p_id,
                        expected_rule="applicant_profile_id must exist in profiles collection",
                        message=f"Orphaned applicant_profile_id '{p_id}' in record '{a_id}'",
                    )
                )

    return errors


# ==============================================================================
# 6. AREA 3: COHORT VALIDATION
# ==============================================================================

def validate_cohort_distribution(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    tolerance: float = 0.05,
    enforce_proportions: bool = True,
) -> Tuple[Dict[str, int], Dict[str, float], List[ValidationErrorDetail]]:
    """
    Validates the six required cohorts:
    1. Healthy Volatile (25.0%)
    2. Stable (25.0%)
    3. Declining (20.0%)
    4. Irregular (15.0%)
    5. High Obligation (10.0%)
    6. Insufficient Data (5.0%)
    """
    errors: List[ValidationErrorDetail] = []
    cohort_counts: Dict[str, int] = {c: 0 for c in COHORT_ARCHETYPES}
    total_records = len(records)

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        cohort = r_dict.get("cohort_archetype")
        app_id = r_dict.get("application_id", f"row_{idx}")

        if cohort not in COHORT_ARCHETYPES:
            errors.append(
                ValidationErrorDetail(
                    validator="CohortValidator",
                    record_id=str(app_id),
                    field_name="cohort_archetype",
                    actual_value=cohort,
                    expected_rule=f"Must be one of {COHORT_ARCHETYPES}",
                    message=f"Record {app_id}: Invalid cohort_archetype '{cohort}'",
                )
            )
        else:
            cohort_counts[cohort] += 1

    cohort_proportions = {
        c: (count / total_records) if total_records > 0 else 0.0
        for c, count in cohort_counts.items()
    }

    # Only test proportions if population is sufficiently large (>= 100 records)
    if enforce_proportions and total_records >= 100:
        for c, expected_prop in COHORT_PROPORTIONS.items():
            obs_prop = cohort_proportions.get(c, 0.0)
            if abs(obs_prop - expected_prop) > tolerance:
                errors.append(
                    ValidationErrorDetail(
                        validator="CohortValidator",
                        record_id=None,
                        field_name="cohort_archetype",
                        actual_value=f"{obs_prop:.4f}",
                        expected_rule=f"{expected_prop:.4f} +- {tolerance:.4f}",
                        message=(
                            f"Cohort '{c}' proportion {obs_prop:.2%} deviates from "
                            f"expected {expected_prop:.2%} by more than permitted tolerance {tolerance:.2%}"
                        ),
                    )
                )

    return cohort_counts, cohort_proportions, errors


# ==============================================================================
# 7. AREA 4 & 10: FEATURE SEMANTICS, RANGES & DISTRIBUTIONS
# ==============================================================================

def validate_feature_semantics(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, int]], List[ValidationErrorDetail]]:
    """
    Validates presence, physical bounds, ranges, and categorical domains for all 40 ML features
    and raw profile/loan fields.
    Collects numerical summaries (min, max, mean, missing, out_of_range) and categorical counts.
    """
    errors: List[ValidationErrorDetail] = []
    num_stats: Dict[str, Dict[str, Any]] = {}
    cat_stats: Dict[str, Dict[str, int]] = {}

    # Initialize statistics
    for col, (b_min, b_max) in FEATURE_BOUNDS.items():
        num_stats[col] = {
            "min": float("inf"),
            "max": float("-inf"),
            "sum": 0.0,
            "count": 0,
            "missing_count": 0,
            "out_of_range_count": 0,
            "bounds": (b_min, b_max),
        }

    for col, domain in CATEGORICAL_DOMAINS.items():
        cat_stats[col] = {c: 0 for c in domain}
        cat_stats[col]["__unexpected__"] = 0

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = str(r_dict.get("application_id", f"row_{idx}"))

        # 1. Numerical feature checks
        for col, (b_min, b_max) in FEATURE_BOUNDS.items():
            if col not in r_dict or r_dict[col] is None:
                num_stats[col]["missing_count"] += 1
                continue

            val = r_dict[col]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                fval = float(val)
                st = num_stats[col]
                st["count"] += 1
                st["sum"] += fval
                if fval < st["min"]:
                    st["min"] = fval
                if fval > st["max"]:
                    st["max"] = fval

                # Range violation check
                violation = False
                if b_min is not None and fval < b_min:
                    violation = True
                if b_max is not None and fval > b_max:
                    violation = True

                if violation:
                    st["out_of_range_count"] += 1
                    errors.append(
                        ValidationErrorDetail(
                            validator="FeatureValidator",
                            record_id=app_id,
                            field_name=col,
                            actual_value=val,
                            expected_rule=f"[{b_min}, {b_max}]",
                            message=f"Record {app_id}: Feature '{col}' value {val} out of bounds [{b_min}, {b_max}]",
                        )
                    )

        # 2. Categorical domain checks
        for col, domain in CATEGORICAL_DOMAINS.items():
            cval = r_dict.get(col)
            if cval is None:
                continue
            if cval in domain:
                cat_stats[col][cval] = cat_stats[col].get(cval, 0) + 1
            else:
                cat_stats[col]["__unexpected__"] += 1
                errors.append(
                    ValidationErrorDetail(
                        validator="FeatureValidator",
                        record_id=app_id,
                        field_name=col,
                        actual_value=cval,
                        expected_rule=f"Must be one of {domain}",
                        message=f"Record {app_id}: Categorical '{col}' has unexpected value '{cval}'",
                    )
                )

    # Finalize numerical statistics averages
    for col, st in num_stats.items():
        if st["count"] > 0:
            st["mean"] = round(st["sum"] / st["count"], 4)
        else:
            st["min"] = None
            st["max"] = None
            st["mean"] = None
        st.pop("sum", None)

    return num_stats, cat_stats, errors


# ==============================================================================
# 8. AREA 5 & 11: TARGET VALIDATION & COHORT * TARGET ANALYSIS
# ==============================================================================

def validate_target_semantics(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
) -> Tuple[Dict[str, Any], List[ValidationErrorDetail], List[str]]:
    """
    Validates target semantics against the frozen contract:
    - Insufficient Data cohort records must have target_default_flag = None and repayment_risk_probability = None
    - Scored cohort records must have target_default_flag in (0, 1) and repayment_risk_probability in [0.0, 1.0]
    - Reports scored count, unscored count, default count, and default rate
    - Evaluates observed default rate against frozen 10-15% expectation and emits warning if outside
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[str] = []

    cohort_target_stats: Dict[str, Dict[str, Any]] = {
        c: {"total": 0, "scored": 0, "unscored": 0, "defaults": 0, "default_rate": 0.0}
        for c in COHORT_ARCHETYPES
    }

    scored_total = 0
    unscored_total = 0
    defaults_total = 0

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = str(r_dict.get("application_id", f"row_{idx}"))
        cohort = r_dict.get("cohort_archetype")
        target = r_dict.get("target_default_flag")
        prob = r_dict.get("repayment_risk_probability")

        if cohort not in cohort_target_stats:
            continue

        c_stat = cohort_target_stats[cohort]
        c_stat["total"] += 1

        if cohort == COHORT_INSUFFICIENT_DATA:
            # Must be unscored
            unscored_total += 1
            c_stat["unscored"] += 1
            if target is not None:
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="target_default_flag",
                        actual_value=target,
                        expected_rule="Insufficient Data cohort records must have null target_default_flag",
                        message=f"Record {app_id}: Insufficient Data cohort record has non-null target_default_flag: {target}",
                    )
                )
            if prob is not None:
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="repayment_risk_probability",
                        actual_value=prob,
                        expected_rule="Insufficient Data cohort records must have null repayment_risk_probability",
                        message=f"Record {app_id}: Insufficient Data cohort record has non-null repayment_risk_probability: {prob}",
                    )
                )
        else:
            # Scored cohorts
            scored_total += 1
            c_stat["scored"] += 1

            if target is None:
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="target_default_flag",
                        actual_value=None,
                        expected_rule="Scored cohort records must have target_default_flag in {0, 1}",
                        message=f"Record {app_id}: Scored cohort '{cohort}' has null target_default_flag",
                    )
                )
            elif target not in (0, 1):
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="target_default_flag",
                        actual_value=target,
                        expected_rule="target_default_flag must be strictly 0 or 1",
                        message=f"Record {app_id}: Invalid target_default_flag value: {target}",
                    )
                )
            elif target == 1:
                defaults_total += 1
                c_stat["defaults"] += 1

            if prob is None:
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="repayment_risk_probability",
                        actual_value=None,
                        expected_rule="Scored cohort records must have repayment_risk_probability in [0.0, 1.0]",
                        message=f"Record {app_id}: Scored cohort '{cohort}' has null repayment_risk_probability",
                    )
                )
            elif not (0.0 <= prob <= 1.0):
                errors.append(
                    ValidationErrorDetail(
                        validator="TargetValidator",
                        record_id=app_id,
                        field_name="repayment_risk_probability",
                        actual_value=prob,
                        expected_rule="repayment_risk_probability must be bounded in [0.0, 1.0]",
                        message=f"Record {app_id}: repayment_risk_probability {prob} out of bounds [0.0, 1.0]",
                    )
                )

    # Compute default rates per cohort
    for c, c_stat in cohort_target_stats.items():
        if c_stat["scored"] > 0:
            c_stat["default_rate"] = round(c_stat["defaults"] / c_stat["scored"], 4)

    overall_default_rate = (
        round(defaults_total / scored_total, 4) if scored_total > 0 else 0.0
    )

    # Check observed default rate against 10.0% - 15.0% contract range
    if scored_total >= 50:
        if not (0.10 <= overall_default_rate <= 0.15):
            warnings.append(
                f"Observed default rate {overall_default_rate:.2%} is outside the frozen "
                f"expected range [10.0%, 15.0%]. Reported faithfully without artificial modification."
            )

    target_summary = {
        "scored_count": scored_total,
        "unscored_count": unscored_total,
        "default_count": defaults_total,
        "default_rate": overall_default_rate,
        "cohort_breakdown": cohort_target_stats,
    }

    return target_summary, errors, warnings


# ==============================================================================
# 9. AREA 6 & 12: TEMPORAL VALIDATION & DISTRIBUTION
# ==============================================================================

def validate_temporal_distribution(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    histories: Optional[Dict[str, ApplicationHistoricalData]] = None,
    outcomes: Optional[Dict[str, ForwardOutcome]] = None,
) -> Tuple[Dict[str, Any], List[ValidationErrorDetail]]:
    """
    Validates temporal constraints:
    - Application cutoff t0 within [2025-01-01, 2026-09-22]
    - Repeat applicant multi-application intervals >= 120 days
    - Historical events strictly before t0 (< t0)
    - Outcome events strictly after t0 (> t0)
    - Prediction horizon in [30, 90] days
    """
    errors: List[ValidationErrorDetail] = []
    min_t0: Optional[datetime] = None
    max_t0: Optional[datetime] = None
    apps_by_applicant: Dict[str, List[Tuple[str, datetime]]] = {}

    start_bound = datetime.fromisoformat(APPLICATION_TIMESTAMP_START.replace("Z", "+00:00"))
    end_bound = datetime.fromisoformat(APPLICATION_TIMESTAMP_END.replace("Z", "+00:00"))

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = str(r_dict.get("application_id", f"row_{idx}"))
        applicant_id = str(r_dict.get("applicant_profile_id", f"prof_{idx}"))
        t0_str = r_dict.get("cutoff_timestamp")

        if not t0_str or not isinstance(t0_str, str):
            errors.append(
                ValidationErrorDetail(
                    validator="TemporalValidator",
                    record_id=app_id,
                    field_name="cutoff_timestamp",
                    actual_value=t0_str,
                    expected_rule="cutoff_timestamp must be a valid ISO-8601 UTC string",
                    message=f"Record {app_id}: Missing or invalid cutoff_timestamp",
                )
            )
            continue

        try:
            t0_dt = datetime.fromisoformat(t0_str.replace("Z", "+00:00"))
        except Exception as e:
            errors.append(
                ValidationErrorDetail(
                    validator="TemporalValidator",
                    record_id=app_id,
                    field_name="cutoff_timestamp",
                    actual_value=t0_str,
                    expected_rule="Valid ISO-8601 UTC timestamp",
                    message=f"Record {app_id}: Failed to parse cutoff_timestamp '{t0_str}': {e}",
                )
            )
            continue

        if not (start_bound <= t0_dt <= end_bound):
            errors.append(
                ValidationErrorDetail(
                    validator="TemporalValidator",
                    record_id=app_id,
                    field_name="cutoff_timestamp",
                    actual_value=t0_str,
                    expected_rule=f"[{APPLICATION_TIMESTAMP_START}, {APPLICATION_TIMESTAMP_END}]",
                    message=f"Record {app_id}: cutoff_timestamp '{t0_str}' is out of frozen calendar bounds",
                )
            )

        if min_t0 is None or t0_dt < min_t0:
            min_t0 = t0_dt
        if max_t0 is None or t0_dt > max_t0:
            max_t0 = t0_dt

        apps_by_applicant.setdefault(applicant_id, []).append((app_id, t0_dt))

    # Check repeat applicant spacing
    repeat_intervals: List[float] = []
    for applicant_id, app_list in apps_by_applicant.items():
        if len(app_list) > 1:
            sorted_apps = sorted(app_list, key=lambda x: x[1])
            for i in range(len(sorted_apps) - 1):
                cur_app, cur_t0 = sorted_apps[i]
                nxt_app, nxt_t0 = sorted_apps[i + 1]
                delta_days = (nxt_t0 - cur_t0).total_seconds() / 86400.0
                repeat_intervals.append(delta_days)
                if delta_days < REPEAT_INTERVAL_DAYS_MIN:
                    errors.append(
                        ValidationErrorDetail(
                            validator="TemporalValidator",
                            record_id=nxt_app,
                            field_name="cutoff_timestamp",
                            actual_value=f"{delta_days:.1f} days",
                            expected_rule=f">= {REPEAT_INTERVAL_DAYS_MIN} days",
                            message=(
                                f"Repeat applicant '{applicant_id}': Applications '{cur_app}' and '{nxt_app}' "
                                f"have spacing of {delta_days:.1f} days, violating minimum requirement of {REPEAT_INTERVAL_DAYS_MIN} days"
                            ),
                        )
                    )

    # Optional check against raw historical and outcome telemetry
    if histories:
        for app_id, history in histories.items():
            t0_dt = datetime.fromisoformat(history.cutoff_timestamp.replace("Z", "+00:00"))
            for ev in history.daily_events:
                ev_dt = datetime.fromisoformat(ev.date.replace("Z", "+00:00"))
                if ev_dt >= t0_dt:
                    errors.append(
                        ValidationErrorDetail(
                            validator="TemporalValidator",
                            record_id=app_id,
                            field_name="daily_events.date",
                            actual_value=ev.date,
                            expected_rule=f"Strictly before cutoff {history.cutoff_timestamp}",
                            message=f"Historical shift event at {ev.date} occurs at or after cutoff {history.cutoff_timestamp}",
                        )
                    )
            for p in history.weekly_payouts:
                p_dt = datetime.fromisoformat(p.payout_timestamp.replace("Z", "+00:00"))
                if p_dt >= t0_dt:
                    errors.append(
                        ValidationErrorDetail(
                            validator="TemporalValidator",
                            record_id=app_id,
                            field_name="weekly_payouts.payout_timestamp",
                            actual_value=p.payout_timestamp,
                            expected_rule=f"Strictly before cutoff {history.cutoff_timestamp}",
                            message=f"Historical payout at {p.payout_timestamp} settles at or after cutoff {history.cutoff_timestamp}",
                        )
                    )

    if outcomes:
        for app_id, outcome in outcomes.items():
            if not (PREDICTION_HORIZON_DAYS_MIN <= outcome.prediction_horizon_days <= PREDICTION_HORIZON_DAYS_MAX):
                errors.append(
                    ValidationErrorDetail(
                        validator="TemporalValidator",
                        record_id=app_id,
                        field_name="prediction_horizon_days",
                        actual_value=outcome.prediction_horizon_days,
                        expected_rule=f"[{PREDICTION_HORIZON_DAYS_MIN}, {PREDICTION_HORIZON_DAYS_MAX}] days",
                        message=f"Prediction horizon {outcome.prediction_horizon_days} out of bounds",
                    )
                )

    temporal_summary = {
        "t0_min": min_t0.isoformat() if min_t0 else None,
        "t0_max": max_t0.isoformat() if max_t0 else None,
        "repeat_applicants_count": sum(1 for apps in apps_by_applicant.values() if len(apps) > 1),
        "repeat_intervals_count": len(repeat_intervals),
        "min_repeat_interval_days": min(repeat_intervals) if repeat_intervals else None,
        "max_repeat_interval_days": max(repeat_intervals) if repeat_intervals else None,
    }

    return temporal_summary, errors


# ==============================================================================
# 10. AREA 8: IMPOSSIBLE COMBINATIONS VALIDATION
# ==============================================================================

def validate_impossible_combinations(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    histories: Optional[Dict[str, ApplicationHistoricalData]] = None,
) -> List[ValidationErrorDetail]:
    """
    Validates all explicit impossible combinations defined in Section 5.2 of the frozen contract:
    1. gross_earnings < net_payout_amount
    2. feat_act_active_days_ratio == 0.0 and feat_inc_median_90d > 0.0
    3. feat_inc_cv_90d == 0.0 and feat_inc_downside_var > 0.0
    4. feat_rec_bounceback_ratio < 0.0
    5. feat_suf_payout_count > feat_suf_observed_days
    6. payout_period_start > payout_period_end
    7. payout_timestamp >= cutoff_timestamp
    8. feat_inc_p25_90d > feat_inc_median_90d
    9. feat_bur_total_dti < feat_bur_dti_ratio
    10. target_default_flag not in (0, 1, None)
    11. repayment_risk_probability < 0.0 or repayment_risk_probability > 1.0
    """
    errors: List[ValidationErrorDetail] = []

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = str(r_dict.get("application_id", f"row_{idx}"))

        # 2. Zero active days with positive income
        act_ratio = r_dict.get("feat_act_active_days_ratio")
        med_inc = r_dict.get("feat_inc_median_90d")
        if act_ratio is not None and med_inc is not None:
            if act_ratio == 0.0 and med_inc > 0.0:
                errors.append(
                    ValidationErrorDetail(
                        validator="ImpossibleCombinationValidator",
                        record_id=app_id,
                        field_name="feat_act_active_days_ratio",
                        actual_value=f"active={act_ratio}, inc={med_inc}",
                        expected_rule="feat_act_active_days_ratio == 0.0 requires feat_inc_median_90d == 0.0",
                        message=f"Record {app_id}: Positive income ({med_inc}) with zero active days",
                    )
                )

        # 3. Zero CV with positive downside variance
        cv = r_dict.get("feat_inc_cv_90d")
        down_var = r_dict.get("feat_inc_downside_var")
        if cv is not None and down_var is not None:
            if cv == 0.0 and down_var > 0.0:
                errors.append(
                    ValidationErrorDetail(
                        validator="ImpossibleCombinationValidator",
                        record_id=app_id,
                        field_name="feat_inc_downside_var",
                        actual_value=f"cv={cv}, down_var={down_var}",
                        expected_rule="feat_inc_cv_90d == 0.0 requires feat_inc_downside_var == 0.0",
                        message=f"Record {app_id}: Zero CV with positive downside variance ({down_var})",
                    )
                )

        # 4. Negative bounceback ratio
        bounce = r_dict.get("feat_rec_bounceback_ratio")
        if bounce is not None and bounce < 0.0:
            errors.append(
                ValidationErrorDetail(
                    validator="ImpossibleCombinationValidator",
                    record_id=app_id,
                    field_name="feat_rec_bounceback_ratio",
                    actual_value=bounce,
                    expected_rule="feat_rec_bounceback_ratio >= 0.0",
                    message=f"Record {app_id}: Negative bounceback ratio ({bounce})",
                )
            )

        # 5. Payout count exceeds observed days
        payouts = r_dict.get("feat_suf_payout_count")
        obs_days = r_dict.get("feat_suf_observed_days")
        if payouts is not None and obs_days is not None:
            if payouts > obs_days:
                errors.append(
                    ValidationErrorDetail(
                        validator="ImpossibleCombinationValidator",
                        record_id=app_id,
                        field_name="feat_suf_payout_count",
                        actual_value=f"payouts={payouts}, obs_days={obs_days}",
                        expected_rule="feat_suf_payout_count <= feat_suf_observed_days",
                        message=f"Record {app_id}: Payout count ({payouts}) exceeds observed days ({obs_days})",
                    )
                )

        # 8. p25 exceeds median
        p25 = r_dict.get("feat_inc_p25_90d")
        if p25 is not None and med_inc is not None:
            if p25 > med_inc:
                errors.append(
                    ValidationErrorDetail(
                        validator="ImpossibleCombinationValidator",
                        record_id=app_id,
                        field_name="feat_inc_p25_90d",
                        actual_value=f"p25={p25}, median={med_inc}",
                        expected_rule="feat_inc_p25_90d <= feat_inc_median_90d",
                        message=f"Record {app_id}: 25th percentile earnings ({p25}) exceeds median ({med_inc})",
                    )
                )

        # 9. Total DTI less than existing DTI
        tot_dti = r_dict.get("feat_bur_total_dti")
        base_dti = r_dict.get("feat_bur_dti_ratio")
        if tot_dti is not None and base_dti is not None:
            if tot_dti < base_dti:
                errors.append(
                    ValidationErrorDetail(
                        validator="ImpossibleCombinationValidator",
                        record_id=app_id,
                        field_name="feat_bur_total_dti",
                        actual_value=f"total={tot_dti}, existing={base_dti}",
                        expected_rule="feat_bur_total_dti >= feat_bur_dti_ratio",
                        message=f"Record {app_id}: Total DTI ({tot_dti}) is less than existing debt DTI ({base_dti})",
                    )
                )

    # Historical telemetry impossible combinations
    if histories:
        for app_id, hist in histories.items():
            t0_dt = datetime.fromisoformat(hist.cutoff_timestamp.replace("Z", "+00:00"))
            for p in hist.weekly_payouts:
                # 1. gross_earnings < net_payout_amount
                if p.gross_amount < p.net_amount:
                    errors.append(
                        ValidationErrorDetail(
                            validator="ImpossibleCombinationValidator",
                            record_id=app_id,
                            field_name="gross_amount",
                            actual_value=f"gross={p.gross_amount}, net={p.net_amount}",
                            expected_rule="gross_amount >= net_amount (platform fee cannot be negative)",
                            message=f"Record {app_id}: gross_amount ({p.gross_amount}) < net_amount ({p.net_amount})",
                        )
                    )
                # 6. period_start > period_end
                dt_start = datetime.fromisoformat(p.period_start.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(p.period_end.replace("Z", "+00:00"))
                if dt_start > dt_end:
                    errors.append(
                        ValidationErrorDetail(
                            validator="ImpossibleCombinationValidator",
                            record_id=app_id,
                            field_name="period_start",
                            actual_value=f"start={p.period_start}, end={p.period_end}",
                            expected_rule="period_start <= period_end",
                            message=f"Record {app_id}: Inverted payout interval: start={p.period_start}, end={p.period_end}",
                        )
                    )
                # 7. payout_timestamp >= cutoff_timestamp
                p_dt = datetime.fromisoformat(p.payout_timestamp.replace("Z", "+00:00"))
                if p_dt >= t0_dt:
                    errors.append(
                        ValidationErrorDetail(
                            validator="ImpossibleCombinationValidator",
                            record_id=app_id,
                            field_name="payout_timestamp",
                            actual_value=p.payout_timestamp,
                            expected_rule=f"Strictly before cutoff {hist.cutoff_timestamp}",
                            message=f"Record {app_id}: Payout timestamp {p.payout_timestamp} is at or after cutoff",
                        )
                    )

    return errors


# ==============================================================================
# 11. AREA 9: MISSINGNESS VALIDATION
# ==============================================================================

def validate_missingness(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
) -> Tuple[Dict[str, int], Dict[str, float], List[ValidationErrorDetail]]:
    """
    Validates dataset missingness:
    - Missing values appear ONLY where permitted (nullable fields)
    - Non-nullable fields have zero missing values
    - Numeric zero is NOT represented as null
    - Null is NOT converted into zero
    - Reports missing counts and proportions for all 52 columns
    """
    errors: List[ValidationErrorDetail] = []
    col_names = get_column_names()
    missing_counts = {c: 0 for c in col_names}
    total_records = len(records)

    schema_by_name = {col.name: col for col in FINAL_DATASET_SCHEMA}

    for idx, rec in enumerate(records):
        r_dict = to_record_dict(rec)
        app_id = str(r_dict.get("application_id", f"row_{idx}"))

        for col in col_names:
            val = r_dict.get(col)
            is_missing = False
            if val is None:
                is_missing = True
            elif isinstance(val, float) and math.isnan(val):
                is_missing = True

            if is_missing:
                missing_counts[col] += 1
                col_def = schema_by_name.get(col)
                if col_def and not col_def.nullable:
                    errors.append(
                        ValidationErrorDetail(
                            validator="MissingnessValidator",
                            record_id=app_id,
                            field_name=col,
                            actual_value=val,
                            expected_rule="Non-nullable field must not be missing or null",
                            message=f"Record {app_id}: Missing value detected in non-nullable column '{col}'",
                        )
                    )

    missing_ratios = {
        c: (cnt / total_records) if total_records > 0 else 0.0
        for c, cnt in missing_counts.items()
    }

    return missing_counts, missing_ratios, errors


# ==============================================================================
# 12. AREA 7: LEAKAGE VALIDATION SUITE
# ==============================================================================

def validate_leakage_suite(
    n_sample_apps: int = 5,
) -> Tuple[bool, Dict[str, Any], List[ValidationErrorDetail]]:
    """
    Executes the comprehensive 5-test leakage validation battery:
    A. POST-t0 EVENT TEST: Adding/modifying an event at or after t0 has zero impact on derived features.
    B. FUTURE TARGET TEST: Altering forward outcome simulation data does not change the feature vector.
    C. TARGET-IN-FEATURE TEST: Target fields and forward outcome variables are completely absent from predictor columns.
    D. CUTOFF TEST: Events immediately before t0 are included; events at or after t0 are rejected.
    E. APPLICATION ISOLATION TEST: Changing application A's history or outcome has zero impact on application B.
    """
    from src.data.synthetic.random_state import RandomStateManager
    from src.data.synthetic.population_generator import generate_population
    from src.data.synthetic.telemetry_generator import (
        generate_application_history,
        DailyActivityEvent,
        WeeklyPayoutEvent,
    )
    from src.data.synthetic.feature_derivation import derive_application_features
    from src.data.synthetic.target_generator import simulate_forward_outcome

    errors: List[ValidationErrorDetail] = []
    test_results: Dict[str, bool] = {
        "test_a_post_t0_event": True,
        "test_b_future_target": True,
        "test_c_target_in_feature": True,
        "test_d_cutoff_boundary": True,
        "test_e_application_isolation": True,
    }

    # Generate isolated test population
    pop = generate_population(RandomStateManager(MASTER_SEED), n_applicants=n_sample_apps, n_repeats=1)
    profiles = {p.applicant_profile_id: p for p in pop.profiles}
    app_0 = pop.applications[0]
    prof_0 = profiles[app_0.applicant_profile_id]

    # Baseline derivation
    hist_0 = generate_application_history(app_0, prof_0, master_seed=MASTER_SEED)
    feat_baseline = derive_application_features(app_0, prof_0, hist_0)
    feat_base_dict = asdict(feat_baseline.features)

    # --------------------------------------------------------------------------
    # Test A: Post-t0 Event Test
    # --------------------------------------------------------------------------
    t0_dt = datetime.fromisoformat(app_0.cutoff_timestamp.replace("Z", "+00:00"))
    post_t0_time = (t0_dt + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    # Creating corrupted history with post-t0 event
    corrupted_daily = list(hist_0.daily_events) + [
        DailyActivityEvent(
            application_id=app_0.application_id,
            date=post_t0_time,
            day_offset=1,
            is_active=True,
            hours_worked=8.0,
            is_weekend=False,
            gross_earnings=5000.0,
            platform_fee=1000.0,
            net_earnings=4000.0,
        )
    ]
    corrupted_hist = ApplicationHistoricalData(
        application_id=app_0.application_id,
        applicant_profile_id=app_0.applicant_profile_id,
        cutoff_timestamp=app_0.cutoff_timestamp,
        history_start_timestamp=hist_0.history_start_timestamp,
        history_end_timestamp=hist_0.history_end_timestamp,
        observed_days=hist_0.observed_days,
        daily_events=corrupted_daily,
        weekly_payouts=hist_0.weekly_payouts,
        telemetry_summary=hist_0.telemetry_summary,
    )

    try:
        # Must raise TemporalLeakageError
        derive_application_features(app_0, prof_0, corrupted_hist)
        test_results["test_a_post_t0_event"] = False
        errors.append(
            ValidationErrorDetail(
                validator="LeakageValidator",
                record_id=app_0.application_id,
                field_name="cutoff_timestamp",
                actual_value="derive_application_features accepted post-t0 event",
                expected_rule="derive_application_features must reject post-t0 historical event with TemporalLeakageError",
                message="Test A Failed: Post-t0 event was not caught during feature derivation",
            )
        )
    except TemporalLeakageError:
        pass  # Expected protection

    # --------------------------------------------------------------------------
    # Test B: Future Target Test
    # --------------------------------------------------------------------------
    outcome_1 = simulate_forward_outcome(app_0, prof_0, master_seed=MASTER_SEED, n_mc_paths=5)
    outcome_2 = simulate_forward_outcome(app_0, prof_0, master_seed=MASTER_SEED + 9999, n_mc_paths=5)

    # Feature vector derived from historical data must not depend on forward outcome
    feat_after_outcomes = asdict(derive_application_features(app_0, prof_0, hist_0).features)
    if feat_base_dict != feat_after_outcomes:
        test_results["test_b_future_target"] = False
        errors.append(
            ValidationErrorDetail(
                validator="LeakageValidator",
                record_id=app_0.application_id,
                field_name="features",
                actual_value="Features differed after running outcome simulator",
                expected_rule="Derived features must be invariant to future outcome simulator runs",
                message="Test B Failed: Features altered after forward outcome generation",
            )
        )

    # --------------------------------------------------------------------------
    # Test C: Target-in-Feature Test
    # --------------------------------------------------------------------------
    forbidden_terms = {
        "target_default_flag",
        "repayment_risk_probability",
        "consecutive_negative_days",
        "prediction_horizon_days",
        "forward_balance",
        "shock_magnitude",
    }
    feature_matrix_cols = set(get_feature_matrix_columns())
    derived_cols = set(feat_base_dict.keys())

    leaked_cols = (feature_matrix_cols | derived_cols) & forbidden_terms
    if leaked_cols:
        test_results["test_c_target_in_feature"] = False
        errors.append(
            ValidationErrorDetail(
                validator="LeakageValidator",
                record_id=None,
                field_name="feature_matrix_columns",
                actual_value=list(leaked_cols),
                expected_rule="Target and future outcome columns must NEVER be in feature matrix",
                message=f"Test C Failed: Target columns found in feature matrix: {leaked_cols}",
            )
        )

    # --------------------------------------------------------------------------
    # Test D: Cutoff Boundary Test
    # --------------------------------------------------------------------------
    # Exact cutoff timestamp t0
    exact_t0_payout = [
        WeeklyPayoutEvent(
            application_id=app_0.application_id,
            payout_id="test_leakage_payout",
            cycle_index=1,
            period_start="2025-01-01T00:00:00Z",
            period_end="2025-01-08T00:00:00Z",
            payout_timestamp=app_0.cutoff_timestamp,  # Exactly at t0
            gross_amount=5000.0,
            net_amount=4000.0,
            active_days=5,
        )
    ]
    corrupted_payout_hist = ApplicationHistoricalData(
        application_id=app_0.application_id,
        applicant_profile_id=app_0.applicant_profile_id,
        cutoff_timestamp=app_0.cutoff_timestamp,
        history_start_timestamp=hist_0.history_start_timestamp,
        history_end_timestamp=hist_0.history_end_timestamp,
        observed_days=hist_0.observed_days,
        daily_events=hist_0.daily_events,
        weekly_payouts=hist_0.weekly_payouts + exact_t0_payout,
        telemetry_summary=hist_0.telemetry_summary,
    )
    try:
        derive_application_features(app_0, prof_0, corrupted_payout_hist)
        test_results["test_d_cutoff_boundary"] = False
        errors.append(
            ValidationErrorDetail(
                validator="LeakageValidator",
                record_id=app_0.application_id,
                field_name="cutoff_timestamp",
                actual_value="derive_application_features accepted event exactly at t0",
                expected_rule="Event at t0 must be rejected with TemporalLeakageError",
                message="Test D Failed: Historical payout event exactly at t0 was not rejected",
            )
        )
    except TemporalLeakageError:
        pass  # Expected protection

    # --------------------------------------------------------------------------
    # Test E: Application Isolation Test
    # --------------------------------------------------------------------------
    if len(pop.applications) > 1:
        app_1 = pop.applications[1]
        prof_1 = profiles[app_1.applicant_profile_id]
        hist_1 = generate_application_history(app_1, prof_1, master_seed=MASTER_SEED)
        feat_1_baseline = asdict(derive_application_features(app_1, prof_1, hist_1).features)

        # Mutate application 0 data in memory
        app_0_mutated = Application(
            application_id=app_0.application_id,
            applicant_profile_id=app_0.applicant_profile_id,
            application_index=app_0.application_index,
            cutoff_timestamp=app_0.cutoff_timestamp,
            requested_loan_amount=app_0.requested_loan_amount * 5,
            loan_tenure_months=12,
            loan_purpose=app_0.loan_purpose,
            contractual_emi=app_0.contractual_emi * 5,
            daily_debt_obligation=app_0.daily_debt_obligation * 5,
        )
        hist_0_mutated = generate_application_history(app_0_mutated, prof_0, master_seed=MASTER_SEED + 42)
        _ = derive_application_features(app_0_mutated, prof_0, hist_0_mutated)

        # Re-derive application 1
        feat_1_after = asdict(derive_application_features(app_1, prof_1, hist_1).features)
        if feat_1_baseline != feat_1_after:
            test_results["test_e_application_isolation"] = False
            errors.append(
                ValidationErrorDetail(
                    validator="LeakageValidator",
                    record_id=app_1.application_id,
                    field_name="features",
                    actual_value="Application 1 features changed when mutating Application 0",
                    expected_rule="Applications must be strictly isolated with zero cross-talk",
                    message="Test E Failed: Mutating Application 0 altered Application 1 features",
                )
            )

    all_passed = all(test_results.values())
    leakage_summary = {
        "passed": all_passed,
        "tests_run": len(test_results),
        "test_results": test_results,
    }
    return all_passed, leakage_summary, errors


# ==============================================================================
# 13. AREA 13: DETERMINISM VALIDATION
# ==============================================================================

def validate_determinism(
    master_seed: int = MASTER_SEED,
    n_sample_applicants: int = 15,
) -> Tuple[bool, str, List[ValidationErrorDetail]]:
    """
    Validates end-to-end deterministic reproducibility:
    Runs population generation, telemetry simulation, feature derivation, outcome simulation,
    and assembly twice with the same master seed, verifying bit-for-bit identical outputs.
    """
    from src.data.synthetic.random_state import RandomStateManager
    from src.data.synthetic.population_generator import generate_population
    from src.data.synthetic.telemetry_generator import generate_application_history
    from src.data.synthetic.feature_derivation import derive_application_features
    from src.data.synthetic.target_generator import simulate_forward_outcome
    from src.data.synthetic.assembly import assemble_dataset

    errors: List[ValidationErrorDetail] = []

    def run_pipeline():
        pop = generate_population(RandomStateManager(master_seed), n_applicants=n_sample_applicants, n_repeats=2)
        profs = {p.applicant_profile_id: p for p in pop.profiles}
        feats = {}
        outs = {}
        for a in pop.applications:
            p = profs[a.applicant_profile_id]
            h = generate_application_history(a, p, master_seed=master_seed)
            feats[a.application_id] = derive_application_features(a, p, h)
            outs[a.application_id] = simulate_forward_outcome(a, p, master_seed=master_seed, n_mc_paths=5)
        return assemble_dataset(pop.applications, profs, feats, outs, deterministic_sort=True)

    records_run1 = run_pipeline()
    records_run2 = run_pipeline()

    if len(records_run1) != len(records_run2):
        errors.append(
            ValidationErrorDetail(
                validator="DeterminismValidator",
                record_id=None,
                field_name="row_count",
                actual_value=f"Run 1: {len(records_run1)}, Run 2: {len(records_run2)}",
                expected_rule="Identical master seeds must yield identical dataset sizes",
                message="Determinism validation failed: row count mismatch",
            )
        )
        return False, "Failed: Row count mismatch", errors

    for i, (r1, r2) in enumerate(zip(records_run1, records_run2)):
        d1 = r1.to_dict()
        d2 = r2.to_dict()
        if d1 != d2:
            diff_keys = [k for k in d1 if d1[k] != d2[k]]
            errors.append(
                ValidationErrorDetail(
                    validator="DeterminismValidator",
                    record_id=r1.application_id,
                    field_name=str(diff_keys),
                    actual_value=f"Differences in {diff_keys}",
                    expected_rule="Identical master seeds must produce bit-for-bit identical records",
                    message=f"Determinism mismatch on record {r1.application_id} in keys: {diff_keys}",
                )
            )
            return False, f"Failed: Mismatch on record {r1.application_id} in keys: {diff_keys}", errors

    return True, "Passed: 100% bit-for-bit reproducibility verified", errors


# ==============================================================================
# 14. DATASET VALIDATION ORCHESTRATOR
# ==============================================================================

def validate_dataset(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    applications: Optional[List[Application]] = None,
    profiles: Optional[Dict[str, ApplicantProfile]] = None,
    histories: Optional[Dict[str, ApplicationHistoricalData]] = None,
    outcomes: Optional[Dict[str, ForwardOutcome]] = None,
    run_leakage_tests: bool = True,
    run_determinism_test: bool = True,
    tolerance: float = 0.05,
    enforce_proportions: bool = True,
) -> DatasetValidationReport:
    """
    Main orchestrator performing comprehensive validation against the frozen ML data contract.
    Validates all 14 contractual areas, accumulates errors/warnings, and produces a structured
    DatasetValidationReport.

    Does NOT modify, repair, or clip data.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    total_records = len(records)
    all_errors: List[ValidationErrorDetail] = []
    all_warnings: List[str] = []

    # 1. Schema Validation
    for rec in records:
        r_dict = to_record_dict(rec)
        all_errors.extend(validate_record_schema(r_dict))

    # 2. Identity & Relational Validation
    all_errors.extend(validate_identities_and_relations(records, applications, profiles))
    unique_apps = len(set(to_record_dict(r).get("application_id") for r in records if to_record_dict(r).get("application_id")))
    unique_applicants = len(set(to_record_dict(r).get("applicant_profile_id") for r in records if to_record_dict(r).get("applicant_profile_id")))

    # 3. Cohort Validation
    cohort_counts, cohort_props, cohort_errors = validate_cohort_distribution(
        records, tolerance=tolerance, enforce_proportions=enforce_proportions
    )
    all_errors.extend(cohort_errors)

    # 4 & 10. Feature Semantics & Ranges
    feature_ranges, cat_dists, feature_errors = validate_feature_semantics(records)
    all_errors.extend(feature_errors)

    # 5 & 11. Target Semantics & Analysis
    target_summary, target_errors, target_warnings = validate_target_semantics(records)
    all_errors.extend(target_errors)
    all_warnings.extend(target_warnings)

    # 6 & 12. Temporal Validation
    temporal_summary, temporal_errors = validate_temporal_distribution(
        records, histories=histories, outcomes=outcomes
    )
    all_errors.extend(temporal_errors)

    # 8. Impossible Combinations
    combo_errors = validate_impossible_combinations(records, histories=histories)
    all_errors.extend(combo_errors)

    # 9. Missingness Validation
    missing_counts, missing_ratios, missing_errors = validate_missingness(records)
    all_errors.extend(missing_errors)

    # 7. Leakage Tests (optional / battery)
    if run_leakage_tests:
        leakage_passed, leakage_summary, leakage_errors = validate_leakage_suite()
        all_errors.extend(leakage_errors)
    else:
        leakage_summary = {"passed": True, "tests_run": 0, "status": "SKIPPED"}

    # 13. Determinism Test
    if run_determinism_test:
        det_passed, det_msg, det_errors = validate_determinism()
        all_errors.extend(det_errors)
        determinism_summary = {"passed": det_passed, "details": det_msg}
    else:
        determinism_summary = {"passed": True, "details": "SKIPPED"}

    overall_status = "PASS" if len(all_errors) == 0 else "FAIL"

    return DatasetValidationReport(
        validation_timestamp=timestamp,
        row_count=total_records,
        unique_applicants=unique_applicants,
        unique_applications=unique_apps,
        cohort_counts=cohort_counts,
        cohort_proportions=cohort_props,
        scored_count=target_summary["scored_count"],
        unscored_count=target_summary["unscored_count"],
        default_count=target_summary["default_count"],
        default_rate=target_summary["default_rate"],
        feature_missingness=missing_counts,
        feature_ranges=feature_ranges,
        categorical_distributions=cat_dists,
        temporal_checks=temporal_summary,
        leakage_checks=leakage_summary,
        impossible_combination_checks={
            "violations_count": len(combo_errors),
            "details": [e.message for e in combo_errors],
        },
        determinism_result=determinism_summary,
        overall_status=overall_status,
        validation_errors=all_errors,
        validation_warnings=all_warnings,
    )


def validate_dataset_strict(
    records: List[Union[AssembledApplicationRecord, Dict[str, Any]]],
    **kwargs: Any,
) -> DatasetValidationReport:
    """
    Executes validate_dataset and raises a descriptive ValidationError / SchemaError
    if overall_status is 'FAIL' or any contract rule is violated.
    """
    report = validate_dataset(records, **kwargs)
    if report.overall_status == "FAIL":
        first_err = report.validation_errors[0]
        # Map to specific exception types if appropriate
        if first_err.validator == "SchemaValidator":
            raise SchemaError(first_err.message)
        elif first_err.validator == "IdentityValidator":
            raise IdentityValidationError(first_err.message)
        elif first_err.validator == "CohortValidator":
            raise CohortValidationError(first_err.message)
        elif first_err.validator == "FeatureValidator":
            raise FeatureRangeError(first_err.message)
        elif first_err.validator == "TargetValidator":
            raise TargetValidationError(first_err.message)
        elif first_err.validator == "TemporalValidator":
            raise TemporalLeakageError(first_err.message)
        elif first_err.validator == "ImpossibleCombinationValidator":
            raise ImpossibleCombinationError(first_err.message)
        elif first_err.validator == "MissingnessValidator":
            raise MissingnessViolationError(first_err.message)
        elif first_err.validator == "LeakageValidator":
            raise TemporalLeakageError(first_err.message)
        elif first_err.validator == "DeterminismValidator":
            raise ReproducibilityError(first_err.message)
        raise ValidationError(f"Dataset validation failed: {first_err.message}")

    return report
