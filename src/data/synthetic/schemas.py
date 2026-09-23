"""
PARAKH Synthetic Credit Application Generator - Schemas
Defines typed intermediate dataclasses and the complete 52-column final dataset schema.
Strictly adheres to docs/final-ml-data-requirements.md (v1.1.0 Frozen Specification).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# 1. COLUMN CLASSIFICATION ENUMS
# ==============================================================================

class ColumnCategory(str, Enum):
    """Categorical classification of dataset columns."""
    METADATA = "metadata"
    PROFILE = "profile"
    LOAN = "loan/application"
    DERIVED_FEATURE = "derived/model feature"
    TARGET = "target"


class DataType(str, Enum):
    """Standardized physical data types."""
    STRING = "string"
    FLOAT64 = "float64"
    INT64 = "int64"


# ==============================================================================
# 2. COLUMN DEFINITION CONTRACT
# ==============================================================================

@dataclass(frozen=True)
class ColumnDefinition:
    """Exact specification of a single dataset column."""
    name: str
    dtype: DataType
    category: ColumnCategory
    required: bool
    nullable: bool
    in_feature_matrix: bool
    is_target: bool
    is_historical: bool
    allowed_range_or_categories: Optional[str]
    description: str


# ==============================================================================
# 3. INTERMEDIATE STAGE DATA STRUCTURES
# ==============================================================================

@dataclass
class Applicant:
    """Stage B output: Unique applicant identity and assigned cohort."""
    applicant_profile_id: str
    cohort_archetype: str


@dataclass
class ApplicantProfile:
    """Stage D output: Full worker background and financial baselines."""
    applicant_profile_id: str
    cohort_archetype: str
    gig_work_type: str
    years_working: Optional[float]
    average_working_days: Optional[int]
    monthly_living_expense: float
    existing_monthly_debt: float
    starting_cashflow_buffer: float
    baseline_weekly_income: float
    platform_rating: Optional[float] = None
    cancellation_rate: Optional[float] = None
    payment_reliability: Optional[float] = None


@dataclass
class Application:
    """Stage F output: Specific financing request event at cutoff t0."""
    application_id: str
    applicant_profile_id: str
    application_index: int              # 1 for first application, 2 for repeat
    cutoff_timestamp: str               # ISO-8601 UTC
    requested_loan_amount: float
    loan_tenure_months: int
    loan_purpose: Optional[str]
    contractual_emi: float
    daily_debt_obligation: float


@dataclass(frozen=True)
class DailyActivityEvent:
    """Raw daily activity shift record in trailing 90 days."""
    application_id: str
    date: str                          # ISO-8601 UTC date string
    day_offset: int                    # -90 to -1
    is_active: bool                    # whether shift was worked
    hours_worked: float                # active hours on shift
    is_weekend: bool                   # Saturday / Sunday flag
    gross_earnings: float              # gross platform earnings
    platform_fee: float                # commission deduction
    net_earnings: float                # gross - commission (>= 0)
    is_unobserved: bool = False        # True for pre-onboarding days (Insufficient Data)


@dataclass(frozen=True)
class WeeklyPayoutEvent:
    """Raw weekly settlement payout cycle in trailing 90 days."""
    application_id: str
    payout_id: str                     # Unique payout identifier
    cycle_index: int                   # 1 to K (K <= 13)
    period_start: str                  # ISO-8601 UTC string
    period_end: str                    # ISO-8601 UTC string
    payout_timestamp: str              # Settlement event timestamp strictly < t0
    gross_amount: float                # Sum of daily gross
    net_amount: float                  # Sum of daily net payouts (I_k)
    active_days: int                   # Active days count in cycle
    is_settled: bool = True            # Verified settled


@dataclass
class HistoricalTelemetry:
    """Stage E output: 90-day pre-cutoff activity and payout time-series."""
    application_id: str
    daily_active_flags: List[bool]
    daily_net_earnings: List[float]
    daily_gross_earnings: List[float]
    daily_working_hours: List[float]
    weekly_net_payouts: List[float]
    observed_days: int
    payout_count: int


@dataclass
class ApplicationHistoricalData:
    """Complete raw event history for a single application."""
    application_id: str
    applicant_profile_id: str
    cutoff_timestamp: str              # t0
    history_start_timestamp: str       # t0 - 90 days
    history_end_timestamp: str         # t0
    observed_days: int                 # Observed history span (5-90)
    daily_events: List[DailyActivityEvent]
    weekly_payouts: List[WeeklyPayoutEvent]
    telemetry_summary: HistoricalTelemetry



@dataclass
class DerivedFeatures:
    """Stage G/H output: All 40 derived model features computed from telemetry."""
    # Mandatory core signals (19 features)
    feat_inc_median_90d: float
    feat_inc_p25_90d: float
    feat_inc_cv_90d: float
    feat_inc_downside_var: float
    feat_trend_slope_90d: float
    feat_trend_momentum_30_90: float
    feat_act_active_days_ratio: float
    feat_act_zero_earn_weeks: int
    feat_rec_bounceback_ratio: float
    feat_rec_days_to_recover: float
    feat_liq_buffer_to_loan: float
    feat_liq_burn_months: float
    feat_bur_dti_ratio: float
    feat_bur_installment_dti: float
    feat_bur_total_dti: float
    feat_suf_observed_days: int
    feat_suf_payout_count: int
    feat_suf_group_count: int
    feat_suf_missing_ratio: float

    # Optional features (17 features)
    feat_inc_mean_90d: Optional[float] = None
    feat_inc_trimmed_mean: Optional[float] = None
    feat_inc_iqr_ratio: Optional[float] = None
    feat_inc_min_max_ratio: Optional[float] = None
    feat_trend_consec_drops: Optional[int] = None
    feat_act_max_idle_streak: Optional[int] = None
    feat_act_weekend_intensity: Optional[float] = None
    feat_rec_max_drawdown: Optional[float] = None
    feat_ten_years_working: Optional[float] = None
    feat_ten_platform_rating: Optional[float] = None
    feat_ten_trips_completed: Optional[int] = None
    feat_ten_cancellation_rate: Optional[float] = None
    feat_liq_net_margin: Optional[float] = None
    feat_pay_utility_on_time: Optional[float] = None
    feat_pay_max_bill_delay: Optional[int] = None
    feat_pay_repay_reliability: Optional[float] = None
    feat_bur_loan_to_income: Optional[float] = None

    # Interaction terms (4 features, mandatory non-null)
    feat_int_vol_x_recovery: float = 0.0
    feat_int_vol_x_buffer: float = 0.0
    feat_int_trend_x_dti: float = 0.0
    feat_int_resilience_idx: float = 0.0


@dataclass
class ApplicationFeatures:
    """Stage G/H output: Complete intermediate feature vector for an application."""
    application_id: str
    applicant_profile_id: str
    cutoff_timestamp: str
    features: DerivedFeatures

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary containing identifiers and all 40 derived features."""
        result: Dict[str, Any] = {
            "application_id": self.application_id,
            "applicant_profile_id": self.applicant_profile_id,
            "cutoff_timestamp": self.cutoff_timestamp,
        }
        result.update(self.features.__dict__)
        return result


@dataclass
class ForwardOutcome:
    """Stage I/J output: Forward cashflow simulation and default classification."""
    application_id: str
    prediction_horizon_days: int
    consecutive_negative_days: int
    target_default_flag: Optional[int]          # 0, 1, or None (if Insufficient Data)
    repayment_risk_probability: Optional[float] # Continuous [0.0, 1.0] or None


@dataclass
class FinalRecord:
    """Complete application row ready for Parquet serialization (52 fields)."""
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.fields)


@dataclass
class PopulationData:
    """Stage B-F output: Full in-memory applicant and application population."""
    applicants: List[Applicant]
    profiles: List[ApplicantProfile]
    applications: List[Application]
    repeat_applicant_ids: List[str]


# ==============================================================================
# 4. EXACT FINAL 52-COLUMN DATASET SCHEMA
# ==============================================================================

FINAL_DATASET_SCHEMA: Tuple[ColumnDefinition, ...] = (
    # --- METADATA (4 columns) ---
    ColumnDefinition(
        name="applicant_profile_id",
        dtype=DataType.STRING,
        category=ColumnCategory.METADATA,
        required=True,
        nullable=False,
        in_feature_matrix=False,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="Valid RFC 4122 UUIDv4",
        description="Unique worker identity token",
    ),
    ColumnDefinition(
        name="application_id",
        dtype=DataType.STRING,
        category=ColumnCategory.METADATA,
        required=True,
        nullable=False,
        in_feature_matrix=False,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="Valid RFC 4122 UUIDv4",
        description="Unique loan application identifier",
    ),
    ColumnDefinition(
        name="cutoff_timestamp",
        dtype=DataType.STRING,
        category=ColumnCategory.METADATA,
        required=True,
        nullable=False,
        in_feature_matrix=False,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="ISO-8601 UTC in 2025-01-01 to 2026-09-22",
        description="Application cutoff point (t0)",
    ),
    ColumnDefinition(
        name="cohort_archetype",
        dtype=DataType.STRING,
        category=ColumnCategory.METADATA,
        required=False,
        nullable=False,
        in_feature_matrix=False,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="Healthy Volatile, Stable, Declining, Irregular, High Obligation, Insufficient Data",
        description="Ground truth simulation cohort (metadata only; excluded from model training)",
    ),

    # --- RAW PROFILE (3 columns) ---
    ColumnDefinition(
        name="gig_work_type",
        dtype=DataType.STRING,
        category=ColumnCategory.PROFILE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="DELIVERY, RIDE_HAILING, LOGISTICS, HOME_SERVICES, FREELANCE_MICRO, OTHER",
        description="Primary gig economy operating sector",
    ),
    ColumnDefinition(
        name="years_working",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.PROFILE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 50.0] years",
        description="Self-reported cumulative tenure in gig economy",
    ),
    ColumnDefinition(
        name="average_working_days",
        dtype=DataType.INT64,
        category=ColumnCategory.PROFILE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 31] days/month",
        description="Self-reported typical active days per month",
    ),

    # --- RAW LOAN / APPLICATION (3 columns) ---
    ColumnDefinition(
        name="requested_loan_amount",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.LOAN,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[500.0, 500000.0] INR",
        description="Principal loan financing amount requested",
    ),
    ColumnDefinition(
        name="loan_tenure_months",
        dtype=DataType.INT64,
        category=ColumnCategory.LOAN,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[1, 60] months (discrete: 1, 2, 3, 4, 6, 12)",
        description="Contractual loan repayment tenure requested",
    ),
    ColumnDefinition(
        name="loan_purpose",
        dtype=DataType.STRING,
        category=ColumnCategory.LOAN,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="VEHICLE_MAINTENANCE, WORKING_CAPITAL, EQUIPMENT_PURCHASE, PERSONAL_EMERGENCY, OTHER",
        description="Declared purpose of requested financing",
    ),

    # --- DERIVED / MODEL FEATURES: MANDATORY (19 columns) ---
    ColumnDefinition(
        name="feat_inc_median_90d",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 500000.0] INR",
        description="Median weekly net income across trailing 90 days",
    ),
    ColumnDefinition(
        name="feat_inc_p25_90d",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 500000.0] INR",
        description="25th percentile of weekly net earnings (conservative earning floor)",
    ),
    ColumnDefinition(
        name="feat_inc_cv_90d",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 5.0] ratio",
        description="Coefficient of variation (sigma / mu) of net payouts",
    ),
    ColumnDefinition(
        name="feat_inc_downside_var",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0e10] INR^2",
        description="Semi-variance calculated strictly on weeks below median",
    ),
    ColumnDefinition(
        name="feat_trend_slope_90d",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[-50000.0, 50000.0] INR/week",
        description="Ordinary Least Squares regression slope across weekly payouts",
    ),
    ColumnDefinition(
        name="feat_trend_momentum_30_90",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 5.0] ratio",
        description="Ratio of mean earnings in last 30d to full 90d mean",
    ),
    ColumnDefinition(
        name="feat_act_active_days_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Total active working days divided by 90",
    ),
    ColumnDefinition(
        name="feat_act_zero_earn_weeks",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 13] count",
        description="Total calendar weeks with zero recorded earnings",
    ),
    ColumnDefinition(
        name="feat_rec_bounceback_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 10.0] ratio",
        description="Post-trough peak earnings divided by pre-trough baseline",
    ),
    ColumnDefinition(
        name="feat_rec_days_to_recover",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 90.0] days",
        description="Elapsed calendar days from income trough back to >= 80% median",
    ),
    ColumnDefinition(
        name="feat_liq_buffer_to_loan",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 50.0] ratio",
        description="Starting liquid buffer divided by requested loan amount",
    ),
    ColumnDefinition(
        name="feat_liq_burn_months",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 60.0] months",
        description="Liquid buffer divided by monthly non-discretionary commitments",
    ),
    ColumnDefinition(
        name="feat_bur_dti_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 20.0] ratio",
        description="Existing monthly debt divided by median monthly income",
    ),
    ColumnDefinition(
        name="feat_bur_installment_dti",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 20.0] ratio",
        description="Projected loan monthly installment divided by median income",
    ),
    ColumnDefinition(
        name="feat_bur_total_dti",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 20.0] ratio",
        description="(Existing debt + projected installment) / Median monthly income",
    ),
    ColumnDefinition(
        name="feat_suf_observed_days",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 90] days",
        description="Total days elapsed between first recorded activity and t0",
    ),
    ColumnDefinition(
        name="feat_suf_payout_count",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 90] count",
        description="Total verified payout settlement events in window",
    ),
    ColumnDefinition(
        name="feat_suf_group_count",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 5] count",
        description="Number of distinct core signal groups populated",
    ),
    ColumnDefinition(
        name="feat_suf_missing_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Fraction of optional feature fields missing or null",
    ),

    # --- DERIVED / MODEL FEATURES: OPTIONAL (17 columns) ---
    ColumnDefinition(
        name="feat_inc_mean_90d",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 500000.0] INR",
        description="Arithmetic mean of weekly net earnings",
    ),
    ColumnDefinition(
        name="feat_inc_trimmed_mean",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 500000.0] INR",
        description="10% trimmed mean of periodic earnings",
    ),
    ColumnDefinition(
        name="feat_inc_iqr_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 10.0] ratio",
        description="Interquartile range normalized by median",
    ),
    ColumnDefinition(
        name="feat_inc_min_max_ratio",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Minimum weekly payout divided by maximum weekly payout",
    ),
    ColumnDefinition(
        name="feat_trend_consec_drops",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 13] count",
        description="Maximum streak of consecutive declining weekly payout cycles",
    ),
    ColumnDefinition(
        name="feat_act_max_idle_streak",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 90] days",
        description="Longest consecutive streak of inactive calendar days",
    ),
    ColumnDefinition(
        name="feat_act_weekend_intensity",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Weekend active hours divided by total active hours",
    ),
    ColumnDefinition(
        name="feat_rec_max_drawdown",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Maximum percentage drawdown from rolling peak to subsequent trough",
    ),
    ColumnDefinition(
        name="feat_ten_years_working",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 50.0] years",
        description="Verified tenure in gig economy",
    ),
    ColumnDefinition(
        name="feat_ten_platform_rating",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[1.0, 5.0] rating",
        description="Composite platform customer rating snapshot at t0",
    ),
    ColumnDefinition(
        name="feat_ten_trips_completed",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 100000] count",
        description="Cumulative trips or deliveries completed in trailing 90d",
    ),
    ColumnDefinition(
        name="feat_ten_cancellation_rate",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Driver cancellation ratio over trailing 90d",
    ),
    ColumnDefinition(
        name="feat_liq_net_margin",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[-2.0, 1.0] ratio",
        description="(Gross earnings - expenses) / Gross earnings over 90d",
    ),
    ColumnDefinition(
        name="feat_pay_utility_on_time",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] ratio",
        description="Fraction of utility bills paid on or before due date",
    ),
    ColumnDefinition(
        name="feat_pay_max_bill_delay",
        dtype=DataType.INT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0, 180] days",
        description="Maximum days past due on trailing utility bills",
    ),
    ColumnDefinition(
        name="feat_pay_repay_reliability",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 1.0] index",
        description="Prior micro-loan or peer advance repayment consistency index",
    ),
    ColumnDefinition(
        name="feat_bur_loan_to_income",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=False,
        nullable=True,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 10.0] ratio",
        description="Requested loan principal divided by annualized median earnings",
    ),

    # --- DERIVED / MODEL FEATURES: INTERACTIONS (4 columns, non-null) ---
    ColumnDefinition(
        name="feat_int_vol_x_recovery",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 450.0] index",
        description="feat_inc_cv_90d * feat_rec_days_to_recover",
    ),
    ColumnDefinition(
        name="feat_int_vol_x_buffer",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 50.0] index",
        description="feat_inc_cv_90d / (feat_liq_buffer_to_loan + 0.1)",
    ),
    ColumnDefinition(
        name="feat_int_trend_x_dti",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[-50000.0, 50000.0] index",
        description="feat_trend_slope_90d * (1.0 + feat_bur_total_dti)",
    ),
    ColumnDefinition(
        name="feat_int_resilience_idx",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.DERIVED_FEATURE,
        required=True,
        nullable=False,
        in_feature_matrix=True,
        is_target=False,
        is_historical=True,
        allowed_range_or_categories="[0.0, 100.0] index",
        description="feat_rec_bounceback_ratio / (feat_inc_cv_90d + 0.05)",
    ),

    # --- TARGETS (2 columns) ---
    ColumnDefinition(
        name="target_default_flag",
        dtype=DataType.INT64,
        category=ColumnCategory.TARGET,
        required=True,
        nullable=True,
        in_feature_matrix=False,
        is_target=True,
        is_historical=False,
        allowed_range_or_categories="0, 1, or null (Insufficient Data)",
        description="Binary target: 1 = Default (>= 7 consecutive days Bt < 0), 0 = Repaid",
    ),
    ColumnDefinition(
        name="repayment_risk_probability",
        dtype=DataType.FLOAT64,
        category=ColumnCategory.TARGET,
        required=True,
        nullable=True,
        in_feature_matrix=False,
        is_target=True,
        is_historical=False,
        allowed_range_or_categories="[0.0000, 1.0000] or null (Insufficient Data)",
        description="Calibrated probability of repayment default over prediction horizon",
    ),
)


# ==============================================================================
# 5. SCHEMA QUERY & VALIDATION HELPERS
# ==============================================================================

def get_column_names() -> List[str]:
    """Returns the ordered list of all 52 column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA]


def get_metadata_columns() -> List[str]:
    """Returns the 4 metadata column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.category == ColumnCategory.METADATA]


def get_raw_profile_columns() -> List[str]:
    """Returns the 3 raw profile column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.category == ColumnCategory.PROFILE]


def get_raw_loan_columns() -> List[str]:
    """Returns the 3 raw loan column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.category == ColumnCategory.LOAN]


def get_derived_feature_columns() -> List[str]:
    """Returns the 40 derived model feature column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.category == ColumnCategory.DERIVED_FEATURE]


def get_target_columns() -> List[str]:
    """Returns the 2 target column names."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.category == ColumnCategory.TARGET]


def get_feature_matrix_columns() -> List[str]:
    """Returns the 46 columns permitted to enter the ML feature matrix."""
    return [col.name for col in FINAL_DATASET_SCHEMA if col.in_feature_matrix]


def get_excluded_columns() -> List[str]:
    """Returns the 6 columns strictly excluded from the ML feature matrix."""
    return [col.name for col in FINAL_DATASET_SCHEMA if not col.in_feature_matrix]


def get_mandatory_feature_columns() -> List[str]:
    """Returns the 19 core derived feature columns with 0% nulls permitted."""
    return [
        col.name for col in FINAL_DATASET_SCHEMA
        if col.category == ColumnCategory.DERIVED_FEATURE and not col.nullable
        and not col.name.startswith("feat_int_")
    ]


def get_optional_feature_columns() -> List[str]:
    """Returns the 17 optional derived feature columns that permit nulls."""
    return [
        col.name for col in FINAL_DATASET_SCHEMA
        if col.category == ColumnCategory.DERIVED_FEATURE and col.nullable
    ]


def get_interaction_feature_columns() -> List[str]:
    """Returns the 4 non-null derived interaction feature columns."""
    return [
        col.name for col in FINAL_DATASET_SCHEMA
        if col.name.startswith("feat_int_")
    ]


def validate_schema_counts() -> Dict[str, int]:
    """
    Validates the exact counts of all schema subsets against frozen requirements.
    Raises AssertionError if any count deviates from contract.
    """
    counts = {
        "total_columns": len(FINAL_DATASET_SCHEMA),
        "metadata_columns": len(get_metadata_columns()),
        "raw_profile_columns": len(get_raw_profile_columns()),
        "raw_loan_columns": len(get_raw_loan_columns()),
        "derived_feature_columns": len(get_derived_feature_columns()),
        "target_columns": len(get_target_columns()),
        "feature_matrix_columns": len(get_feature_matrix_columns()),
        "excluded_columns": len(get_excluded_columns()),
        "mandatory_core_features": len(get_mandatory_feature_columns()),
        "optional_derived_features": len(get_optional_feature_columns()),
        "interaction_features": len(get_interaction_feature_columns()),
    }

    assert counts["total_columns"] == 52, f"Total columns must be 52, got {counts['total_columns']}"
    assert counts["metadata_columns"] == 4, f"Metadata columns must be 4, got {counts['metadata_columns']}"
    assert counts["raw_profile_columns"] == 3, f"Raw profile columns must be 3, got {counts['raw_profile_columns']}"
    assert counts["raw_loan_columns"] == 3, f"Raw loan columns must be 3, got {counts['raw_loan_columns']}"
    assert counts["derived_feature_columns"] == 40, f"Derived features must be 40, got {counts['derived_feature_columns']}"
    assert counts["target_columns"] == 2, f"Target columns must be 2, got {counts['target_columns']}"
    assert counts["feature_matrix_columns"] == 46, f"Feature matrix columns must be 46, got {counts['feature_matrix_columns']}"
    assert counts["excluded_columns"] == 6, f"Excluded columns must be 6, got {counts['excluded_columns']}"
    assert counts["mandatory_core_features"] == 19, f"Mandatory features must be 19, got {counts['mandatory_core_features']}"
    assert counts["optional_derived_features"] == 17, f"Optional features must be 17, got {counts['optional_derived_features']}"
    assert counts["interaction_features"] == 4, f"Interaction features must be 4, got {counts['interaction_features']}"

    return counts


# Run self-validation on module import
validate_schema_counts()
