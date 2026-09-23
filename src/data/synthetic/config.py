"""
PARAKH Synthetic Credit Application Generator - Configuration
Frozen configuration parameters derived from:
- docs/final-ml-data-requirements.md (v1.1.0 Frozen ML Data Contract)
- Person 3 Authoritative Parameter Clarification Addendum
- P2-T02 Approved Architecture and Schema Freeze

DO NOT MODIFY FROZEN CONSTANTS.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


# ==============================================================================
# 1. CORE RANDOMNESS & SIZING (FROZEN)
# ==============================================================================

MASTER_SEED: int = 42

TOTAL_APPLICATIONS: int = 12000
UNIQUE_APPLICANTS: int = 10000
REPEAT_APPLICANTS: int = 2000
SINGLE_APPLICANTS: int = UNIQUE_APPLICANTS - REPEAT_APPLICANTS  # 8000
APPLICATIONS_PER_REPEAT: int = 2

# Verification check: 8000 * 1 + 2000 * 2 = 12000
assert SINGLE_APPLICANTS * 1 + REPEAT_APPLICANTS * APPLICATIONS_PER_REPEAT == TOTAL_APPLICATIONS, (
    "Application count arithmetic mismatch"
)


# ==============================================================================
# 2. TEMPORAL BOUNDARIES (FROZEN)
# ==============================================================================

# Application Cutoff Window (t0)
APPLICATION_TIMESTAMP_START: str = "2025-01-01T00:00:00Z"
APPLICATION_TIMESTAMP_END: str = "2026-09-22T23:59:59Z"

# Trailing Observation Window: strictly [t0 - 90d, t0)
OBSERVATION_WINDOW_DAYS: int = 90

# Forward Prediction Horizon: (t0, t0 + T_pred] where T_pred in [30, 90] days
PREDICTION_HORIZON_DAYS_MIN: int = 30
PREDICTION_HORIZON_DAYS_MAX: int = 90

# Repeat Applicant Spacing: t0_second = t0_first + Delta_t
REPEAT_INTERVAL_DAYS_MIN: int = 120
REPEAT_INTERVAL_DAYS_MAX: int = 270


# ==============================================================================
# 3. POPULATION COHORT ARCHETYPES & PROPORTIONS (FROZEN)
# ==============================================================================

COHORT_HEALTHY_VOLATILE: str = "Healthy Volatile"
COHORT_STABLE: str = "Stable"
COHORT_DECLINING: str = "Declining"
COHORT_IRREGULAR: str = "Irregular"
COHORT_HIGH_OBLIGATION: str = "High Obligation"
COHORT_INSUFFICIENT_DATA: str = "Insufficient Data"

COHORT_ARCHETYPES: Tuple[str, ...] = (
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
)

COHORT_PROPORTIONS: Dict[str, float] = {
    COHORT_HEALTHY_VOLATILE: 0.25,
    COHORT_STABLE: 0.25,
    COHORT_DECLINING: 0.20,
    COHORT_IRREGULAR: 0.15,
    COHORT_HIGH_OBLIGATION: 0.10,
    COHORT_INSUFFICIENT_DATA: 0.05,
}

COHORT_PROPORTION_TOLERANCE: float = 0.02  # +/- 2.0% validation tolerance


# ==============================================================================
# 4. GIG WORK TYPE & LOAN PURPOSE CATEGORICALS (FROZEN)
# ==============================================================================

GIG_WORK_DELIVERY: str = "DELIVERY"
GIG_WORK_RIDE_HAILING: str = "RIDE_HAILING"
GIG_WORK_LOGISTICS: str = "LOGISTICS"
GIG_WORK_HOME_SERVICES: str = "HOME_SERVICES"
GIG_WORK_FREELANCE_MICRO: str = "FREELANCE_MICRO"
GIG_WORK_OTHER: str = "OTHER"

GIG_WORK_TYPES: Tuple[str, ...] = (
    GIG_WORK_DELIVERY,
    GIG_WORK_RIDE_HAILING,
    GIG_WORK_LOGISTICS,
    GIG_WORK_HOME_SERVICES,
    GIG_WORK_FREELANCE_MICRO,
    GIG_WORK_OTHER,
)

GIG_WORK_TYPE_PROPORTIONS: Dict[str, float] = {
    GIG_WORK_DELIVERY: 0.40,
    GIG_WORK_RIDE_HAILING: 0.35,
    GIG_WORK_LOGISTICS: 0.12,
    GIG_WORK_HOME_SERVICES: 0.08,
    GIG_WORK_FREELANCE_MICRO: 0.03,
    GIG_WORK_OTHER: 0.02,
}

PURPOSE_VEHICLE_MAINTENANCE: str = "VEHICLE_MAINTENANCE"
PURPOSE_WORKING_CAPITAL: str = "WORKING_CAPITAL"
PURPOSE_EQUIPMENT_PURCHASE: str = "EQUIPMENT_PURCHASE"
PURPOSE_PERSONAL_EMERGENCY: str = "PERSONAL_EMERGENCY"
PURPOSE_OTHER: str = "OTHER"

LOAN_PURPOSES: Tuple[str, ...] = (
    PURPOSE_VEHICLE_MAINTENANCE,
    PURPOSE_WORKING_CAPITAL,
    PURPOSE_EQUIPMENT_PURCHASE,
    PURPOSE_PERSONAL_EMERGENCY,
    PURPOSE_OTHER,
)

LOAN_PURPOSE_PROPORTIONS: Dict[str, float] = {
    PURPOSE_VEHICLE_MAINTENANCE: 0.45,
    PURPOSE_WORKING_CAPITAL: 0.30,
    PURPOSE_EQUIPMENT_PURCHASE: 0.15,
    PURPOSE_PERSONAL_EMERGENCY: 0.07,
    PURPOSE_OTHER: 0.03,
}


# ==============================================================================
# 5. LOAN TERMS & EMI PARAMETERS (FROZEN)
# ==============================================================================

# Loan Amount Bounds (INR)
LOAN_AMOUNT_MIN: float = 500.0
LOAN_AMOUNT_MAX: float = 500000.0
LOAN_AMOUNT_LOGNORMAL_MU: float = math.log(20000.0)
LOAN_AMOUNT_LOGNORMAL_SIGMA: float = 0.55
LOAN_AMOUNT_ROUND_BASE: float = 500.0

# Loan Sizing Affordability Multiples (Approved P2-T10 Frozen Parameters)
LOAN_MULTIPLE_MIN: float = 1.0
LOAN_MULTIPLE_MAX: float = 1.75

# Existing Monthly Debt Scaling Factor (Approved P2-T10 Frozen Parameters)
EXISTING_DEBT_MULTIPLIER: float = 0.50

# Loan Tenures (Months) and Proportions (Approved P2-T10 Affordability Revision)
LOAN_TENURES: Tuple[int, ...] = (1, 2, 3, 4, 6, 9, 12)
LOAN_TENURE_PROPORTIONS: Dict[int, float] = {
    6: 0.20,
    9: 0.30,
    12: 0.50,
}

# Contractual EMI Interest Rate (Reducing-Balance Amortization)
EMI_ANNUAL_FIXED_RATE: float = 0.18  # 18.0% p.a.
EMI_MONTHLY_RATE: float = 0.015      # 1.5% per month (0.18 / 12)


def calculate_contractual_emi(principal: float, tenure_months: int) -> float:
    """
    Standard reducing-balance amortization EMI formula:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    For n == 1: EMI = P * (1 + r)
    """
    if tenure_months <= 0:
        raise ValueError("tenure_months must be positive")
    if principal <= 0:
        return 0.0
    r = EMI_MONTHLY_RATE
    n = tenure_months
    factor = (1.0 + r) ** n
    return float(principal * (r * factor) / (factor - 1.0))


# ==============================================================================
# 6. LIVING EXPENSE PARAMETERS (FROZEN)
# ==============================================================================

LIVING_EXPENSE_MONTHLY_MU: float = math.log(14000.0)
LIVING_EXPENSE_MONTHLY_SIGMA: float = 0.10
LIVING_EXPENSE_MONTHLY_MIN: float = 12000.0
LIVING_EXPENSE_MONTHLY_MAX: float = 22000.0
LIVING_EXPENSE_DAYS_PER_MONTH: float = 30.0


# ==============================================================================
# 7. FORWARD EARNINGS PARAMETERS (FROZEN)
# ==============================================================================

FORWARD_EARNINGS_AR_ALPHA: float = 0.70
FORWARD_EARNINGS_BASE_SIGMA_RATIO: float = 0.12  # 0.12 * historical baseline
FORWARD_EARNINGS_JUMP_PROBABILITY: float = 0.02   # per day
FORWARD_EARNINGS_JUMP_MAGNITUDE_MIN: float = 0.15 # 15% of historical baseline
FORWARD_EARNINGS_JUMP_MAGNITUDE_MAX: float = 0.30 # 30% of historical baseline
DECLINING_COHORT_TRAJECTORY_DRIFT: float = -0.003 # -0.003 / day


# ==============================================================================
# 8. EXOGENOUS FINANCIAL SHOCK PARAMETERS (FROZEN)
# ==============================================================================

SHOCK_MONTHLY_LAMBDA: float = 0.05
SHOCK_DAILY_LAMBDA: float = SHOCK_MONTHLY_LAMBDA / 30.0  # 0.001667 shocks/day
SHOCK_PARETO_SCALE: float = 3000.0                       # s_m in INR
SHOCK_PARETO_SHAPE: float = 2.20                         # alpha
SHOCK_HARD_CAP: float = 25000.0                          # Max shock cap in INR

SHOCK_COHORT_MODIFIERS: Dict[str, float] = {
    COHORT_IRREGULAR: 1.25,
    COHORT_DECLINING: 1.10,
    COHORT_STABLE: 0.80,
    COHORT_HEALTHY_VOLATILE: 1.00,
    COHORT_HIGH_OBLIGATION: 1.00,
    COHORT_INSUFFICIENT_DATA: 1.00,
}


# ==============================================================================
# 9. TARGET & INSOLVENCY PARAMETERS (FROZEN)
# ==============================================================================

INSOLVENCY_GRACE_PERIOD_DAYS: int = 7
TARGET_DEFAULT_RATE_MIN: float = 0.10  # 10.0%
TARGET_DEFAULT_RATE_MAX: float = 0.15  # 15.0%
TARGET_DEFAULT_RATE_TARGET: float = 0.125 # ~12.5% center

TARGET_COLUMN_BINARY: str = "target_default_flag"
TARGET_COLUMN_CONTINUOUS: str = "repayment_risk_probability"


# ==============================================================================
# 10. MISSINGNESS RATES FOR OPTIONAL FEATURES (FROZEN)
# ==============================================================================

OPTIONAL_FEATURE_MISSING_RATES: Dict[str, float] = {
    "years_working": 0.10,
    "average_working_days": 0.10,
    "loan_purpose": 0.05,
    "feat_ten_years_working": 0.10,
    "feat_ten_platform_rating": 0.15,
    "feat_ten_trips_completed": 0.10,
    "feat_ten_cancellation_rate": 0.20,
    "feat_liq_net_margin": 0.25,
    "feat_pay_utility_on_time": 0.35,
    "feat_pay_max_bill_delay": 0.35,
    "feat_pay_repay_reliability": 0.40,
}


# ==============================================================================
# 11. CANONICAL OUTPUT PATH (FROZEN)
# ==============================================================================

CANONICAL_OUTPUT_PATH: str = "data/synthetic/synthetic_credit_applications.parquet"


# ==============================================================================
# 12. CONFIGURATION VALIDATION HELPER
# ==============================================================================

def validate_config() -> bool:
    """
    Validates internal consistency of all frozen configuration constants.
    Raises AssertionError if any mathematical or contractual relation fails.
    """
    # 1. Row & applicant consistency
    assert UNIQUE_APPLICANTS == 10000, "Unique applicants must be 10000"
    assert REPEAT_APPLICANTS == 2000, "Repeat applicants must be 2000"
    assert SINGLE_APPLICANTS == 8000, "Single applicants must be 8000"
    assert SINGLE_APPLICANTS + REPEAT_APPLICANTS == UNIQUE_APPLICANTS, "Sum must equal unique applicants"
    assert SINGLE_APPLICANTS * 1 + REPEAT_APPLICANTS * 2 == TOTAL_APPLICATIONS, (
        "Total application rows must equal 12000"
    )

    # 2. Probability distribution sums
    assert math.isclose(sum(COHORT_PROPORTIONS.values()), 1.0, rel_tol=1e-6), (
        "Cohort proportions must sum to 1.0"
    )
    assert math.isclose(sum(GIG_WORK_TYPE_PROPORTIONS.values()), 1.0, rel_tol=1e-6), (
        "Gig work type proportions must sum to 1.0"
    )
    assert math.isclose(sum(LOAN_PURPOSE_PROPORTIONS.values()), 1.0, rel_tol=1e-6), (
        "Loan purpose proportions must sum to 1.0"
    )
    assert math.isclose(sum(LOAN_TENURE_PROPORTIONS.values()), 1.0, rel_tol=1e-6), (
        "Loan tenure proportions must sum to 1.0"
    )

    # 3. EMI rate consistency
    assert math.isclose(EMI_ANNUAL_FIXED_RATE, 0.18, rel_tol=1e-6), "Annual EMI rate must be 18%"
    assert math.isclose(EMI_MONTHLY_RATE, 0.015, rel_tol=1e-6), "Monthly EMI rate must be 0.015"
    assert math.isclose(EMI_MONTHLY_RATE, EMI_ANNUAL_FIXED_RATE / 12.0, rel_tol=1e-6), (
        "Monthly rate must equal annual rate / 12"
    )

    # 4. Temporal window consistency
    assert OBSERVATION_WINDOW_DAYS == 90, "Observation window must be 90 days"
    assert PREDICTION_HORIZON_DAYS_MIN == 30, "Prediction horizon min must be 30 days"
    assert PREDICTION_HORIZON_DAYS_MAX == 90, "Prediction horizon max must be 90 days"
    assert REPEAT_INTERVAL_DAYS_MIN == 120, "Repeat interval min must be 120 days"
    assert REPEAT_INTERVAL_DAYS_MAX == 270, "Repeat interval max must be 270 days"

    # 5. Living cost bounds
    assert LIVING_EXPENSE_MONTHLY_MIN == 12000.0, "Min living expense must be 12000"
    assert LIVING_EXPENSE_MONTHLY_MAX == 22000.0, "Max living expense must be 22000"
    assert math.isclose(LIVING_EXPENSE_MONTHLY_MU, math.log(14000.0), rel_tol=1e-6), (
        "Living expense mu must be ln(14000)"
    )

    # 6. Forward earnings AR(1)
    assert FORWARD_EARNINGS_AR_ALPHA == 0.70, "AR alpha must be 0.70"
    assert FORWARD_EARNINGS_BASE_SIGMA_RATIO == 0.12, "Base sigma ratio must be 0.12"
    assert FORWARD_EARNINGS_JUMP_PROBABILITY == 0.02, "Jump probability must be 0.02/day"
    assert DECLINING_COHORT_TRAJECTORY_DRIFT == -0.003, "Declining drift must be -0.003/day"

    return True


# Run self-validation on module import
validate_config()
