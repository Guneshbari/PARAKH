"""Input validation for PARAKH credit risk inference pipeline (Phase 9).

Validates a raw application assessment dictionary against the frozen Phase 2 data contract
before it is submitted to the feature engineering and model scoring pipeline.

Validation rules enforced:
  1. Absence of forbidden / prohibited fields (PROHIBITED_FIELDS).
  2. Absence of excluded non-predictor columns (EXCLUDED_NON_PREDICTORS).
  3. Presence of all 46 required pre-encoding input columns (6 raw + 40 derived features).
  4. Correct data types for all numeric and categorical inputs.
  5. Numeric feature range bounds (from FEATURE_BOUNDS in dataset_validator.py).
  6. Allowed categorical domain values (gig_work_type, loan_purpose, loan_tenure_months).
  7. Data sufficiency flags (observed_days, payout_count, group_count).
"""
from typing import Any, Dict, List, Optional, Set, Tuple
import math

from src.ml.constants import (
    MIN_REQUIRED_CORE_SIGNAL_GROUPS,
    PROHIBITED_FIELDS,
)
from src.ml.data.dataset_validator import (
    ALLOWED_GIG_WORK_TYPES,
    ALLOWED_LOAN_PURPOSES,
    ALLOWED_LOAN_TENURES,
    FEATURE_BOUNDS,
)
from src.ml.data.preprocessing import EXCLUDED_NON_PREDICTORS


# All 46 columns the predictor expects in the raw application dict.
# Corresponds to FINAL_MODEL.json expected_input_schema (6 raw + 40 derived features).
REQUIRED_INPUT_COLUMNS: List[str] = [
    # 6 raw application inputs
    "requested_loan_amount",
    "loan_tenure_months",
    "years_working",
    "average_working_days",
    "gig_work_type",
    "loan_purpose",
    # 40 derived telemetry features
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
]

# Numeric columns — all REQUIRED_INPUT_COLUMNS except the two categoricals
NUMERIC_INPUT_COLUMNS: Set[str] = set(REQUIRED_INPUT_COLUMNS) - {"gig_work_type", "loan_purpose"}


class InputValidationError(ValueError):
    """Raised when an inference input dict fails the frozen data contract validation."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        summary = f"Input validation failed with {len(errors)} error(s):\n" + "\n".join(
            f"  [{i+1}] {e}" for i, e in enumerate(errors)
        )
        super().__init__(summary)


class InputValidator:
    """Validates a raw application assessment dict before it enters the inference pipeline.

    This is a stateless validator — all validation rules are derived from the frozen
    Phase 2 data contract constants; no fitting or mutable state is maintained.
    """

    @classmethod
    def validate(cls, application: Dict[str, Any]) -> None:
        """Validate an application dict against the frozen inference input contract.

        Args:
            application: Raw application dict as supplied to the RiskPredictor.

        Raises:
            InputValidationError: If any validation rule is violated.
        """
        errors: List[str] = []

        # 1. Prohibited field check
        present_keys: Set[str] = set(application.keys())
        prohibited_present = present_keys & PROHIBITED_FIELDS
        if prohibited_present:
            for field in sorted(prohibited_present):
                errors.append(
                    f"Field '{field}' is prohibited by data-minimisation policy and must not be submitted."
                )

        # 2. Excluded non-predictor columns check
        excluded_present = present_keys & EXCLUDED_NON_PREDICTORS
        if excluded_present:
            for field in sorted(excluded_present):
                errors.append(
                    f"Field '{field}' is an excluded non-predictor column. Remove it from the input dict."
                )

        # 3. Required field presence
        missing_fields = [c for c in REQUIRED_INPUT_COLUMNS if c not in application]
        if missing_fields:
            errors.append(
                f"Missing {len(missing_fields)} required input field(s): {missing_fields}"
            )

        # Bail early if critical fields missing — further checks will error on KeyError
        if errors:
            raise InputValidationError(errors)

        # 4. Type checks + numeric range bounds
        for col in REQUIRED_INPUT_COLUMNS:
            val = application[col]

            if col in ("gig_work_type", "loan_purpose"):
                # Categorical: expect str
                if not isinstance(val, str):
                    errors.append(
                        f"Column '{col}' must be a string, got {type(val).__name__}."
                    )
                continue

            # Numeric: must be int or float
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                errors.append(
                    f"Column '{col}' must be a numeric value (int or float), got {type(val).__name__}."
                )
                continue

            if math.isnan(val) or math.isinf(val):
                errors.append(
                    f"Column '{col}' contains a non-finite value ({val}). Provide a valid numeric value."
                )
                continue

            # Range check against FEATURE_BOUNDS (which also contains raw loan columns)
            if col in FEATURE_BOUNDS:
                f_min, f_max, allow_neg = FEATURE_BOUNDS[col]
                if not allow_neg and val < -1e-9:
                    errors.append(
                        f"Column '{col}' = {val} is negative but negative values are not permitted."
                    )
                if val < f_min - 1e-4 or val > f_max + 1e-4:
                    errors.append(
                        f"Column '{col}' = {val} is outside contracted bounds [{f_min}, {f_max}]."
                    )

        # 5. Categorical domain checks
        gig = application.get("gig_work_type", "")
        if isinstance(gig, str) and gig not in ALLOWED_GIG_WORK_TYPES:
            errors.append(
                f"'gig_work_type' value '{gig}' is not in the allowed set: {sorted(ALLOWED_GIG_WORK_TYPES)}."
            )

        purpose = application.get("loan_purpose", "")
        if isinstance(purpose, str) and purpose not in ALLOWED_LOAN_PURPOSES:
            errors.append(
                f"'loan_purpose' value '{purpose}' is not in the allowed set: {sorted(ALLOWED_LOAN_PURPOSES)}."
            )

        tenure = application.get("loan_tenure_months")
        if tenure is not None and not isinstance(tenure, bool):
            if isinstance(tenure, (int, float)) and int(tenure) not in ALLOWED_LOAN_TENURES:
                errors.append(
                    f"'loan_tenure_months' = {tenure} is not an allowed value. "
                    f"Must be one of {sorted(ALLOWED_LOAN_TENURES)}."
                )

        if errors:
            raise InputValidationError(errors)

    @classmethod
    def check_data_sufficiency(
        cls, application: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Evaluate whether the application passes data sufficiency thresholds.

        Applies the three data sufficiency rules from the frozen contract:
          - feat_suf_observed_days >= 30
          - feat_suf_payout_count >= 4
          - feat_suf_group_count >= MIN_REQUIRED_CORE_SIGNAL_GROUPS (2)

        Args:
            application: Validated application dict.

        Returns:
            Tuple[bool, List[str]]: (is_insufficient, list_of_failure_reasons).
                is_insufficient=True means the application should not be scored.
        """
        reasons: List[str] = []

        observed_days = application.get("feat_suf_observed_days")
        payout_count = application.get("feat_suf_payout_count")
        group_count = application.get("feat_suf_group_count")

        if observed_days is not None and observed_days < 30:
            reasons.append(
                f"Observed history ({observed_days:.0f} days) is below the minimum required 30 days."
            )
        if payout_count is not None and payout_count < 4:
            reasons.append(
                f"Payout cycle count ({payout_count:.0f}) is below the minimum required 4 cycles."
            )
        if group_count is not None and group_count < MIN_REQUIRED_CORE_SIGNAL_GROUPS:
            reasons.append(
                f"Core signal group count ({group_count:.0f}) is below the minimum required "
                f"{MIN_REQUIRED_CORE_SIGNAL_GROUPS} signal groups."
            )

        is_insufficient = len(reasons) > 0
        return is_insufficient, reasons
