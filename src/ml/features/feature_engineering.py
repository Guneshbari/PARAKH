"""PARAKH Feature Engineering Layer (Phase 4).

Builds, manages, and validates the deterministic model-ready feature engineering layer
on top of the Phase 3 validated/preprocessed credit application dataset.

Core Invariants:
1. Volatility-Aware Paradigm: Relates volatility to earning baselines, recovery speed,
   trend momentum, cashflow buffers, and debt obligations, preserving the distinction
   between healthy gig-work variability and genuine deterioration.
2. Temporal Integrity: Every predictor uses information strictly available before t0.
3. Determinism: Bitwise-reproducible mathematical transformations without row-order dependence.
4. Numerical Safety: Divide-by-zero prevention with documented epsilons (+0.1, +1.0, +0.05).
5. Feature Lineage: Complete provenance from source signals through transformations to model input.
6. Benchmark Isolation: Separates BASELINE features from VOLATILITY_AWARE feature sets.
"""
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.dataset_validator import (
    DERIVED_FEATURES,
    MANDATORY_FEATURES,
    OPTIONAL_FEATURES,
)
from src.ml.data.preprocessing import (
    CATEGORICAL_INPUT_COLUMNS,
    CreditRiskPreprocessor,
    EXCLUDED_NON_PREDICTORS,
    RAW_NUMERIC_COLUMNS,
)


@dataclass
class FeatureLineageRecord:
    """Documented provenance and metadata for a single machine learning feature."""

    feature_name: str
    feature_group: str
    source_features: List[str]
    calculation_formula: str
    unit: str
    feature_type: str  # 'raw_input', 'derived_telemetry', 'interaction_contract', 'engineered_volatility'
    semantic_meaning: str
    temporal_availability: str = "Strictly pre-t0 [t0 - 90d, t0)"
    used_in_baseline: bool = False
    used_in_volatility_aware: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return asdict(self)


# -----------------------------------------------------------------------------
# 9 Newly Engineered Volatility-Aware Interaction Features
# -----------------------------------------------------------------------------
ENGINEERED_VOLATILITY_FEATURES: List[str] = [
    # 1. Volatility relative to baseline earnings
    "feat_eng_vol_to_baseline",
    "feat_eng_downside_to_median",
    # 2. Volatility conditioned on trajectory / trend
    "feat_eng_vol_x_trend",
    # 3. Volatility conditioned on recovery and resilience
    "feat_eng_vol_to_bounceback",
    "feat_eng_recovery_velocity",
    # 4. Volatility conditioned on liquidity & cashflow buffer
    "feat_eng_buffer_burn_coverage",
    "feat_eng_vol_cushion_ratio",
    # 5. Volatility conditioned on debt & obligation capacity
    "feat_eng_dti_risk_multiplier",
    "feat_eng_installment_floor_coverage",
]

# Baseline feature set: classical linear underwriting signals without non-linear volatility interactions
BASELINE_FEATURE_SET: List[str] = [
    # Baseline income level
    "feat_inc_median_90d",
    "feat_inc_mean_90d",
    "feat_inc_p25_90d",
    # Raw unconditioned volatility (naive linear entry)
    "feat_inc_cv_90d",
    # Basic activity
    "feat_act_active_days_ratio",
    "feat_act_zero_earn_weeks",
    "feat_act_max_idle_streak",
    # Tenure & rating
    "feat_ten_years_working",
    "feat_ten_platform_rating",
    "feat_ten_trips_completed",
    # Debt service burden
    "feat_bur_dti_ratio",
    "feat_bur_installment_dti",
    "feat_bur_total_dti",
    # Reserves
    "feat_liq_buffer_to_loan",
    "feat_liq_burn_months",
    # Payment discipline
    "feat_pay_utility_on_time",
    "feat_pay_repay_reliability",
    # Sufficiency
    "feat_suf_observed_days",
    "feat_suf_payout_count",
    # Raw application inputs
    "requested_loan_amount",
    "loan_tenure_months",
    "years_working",
    "average_working_days",
    "gig_work_type",
    "loan_purpose",
    # Installment coverage at floor
    "feat_eng_installment_floor_coverage",
]


# Master Feature Lineage Registry
MASTER_LINEAGE: Dict[str, FeatureLineageRecord] = {
    # 1. Income Level
    "feat_inc_median_90d": FeatureLineageRecord(
        feature_name="feat_inc_median_90d",
        feature_group="income_level",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Median({P_k}) over 90 days",
        unit="INR",
        feature_type="derived_telemetry",
        semantic_meaning="Robust periodic earning baseline insulated against outlier spikes.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_inc_p25_90d": FeatureLineageRecord(
        feature_name="feat_inc_p25_90d",
        feature_group="income_level",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="25th percentile({P_k}) over 90 days",
        unit="INR",
        feature_type="derived_telemetry",
        semantic_meaning="Conservative earnings floor during lean earning periods.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_inc_mean_90d": FeatureLineageRecord(
        feature_name="feat_inc_mean_90d",
        feature_group="income_level",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Arithmetic mean({P_k}) over 90 days",
        unit="INR",
        feature_type="derived_telemetry",
        semantic_meaning="Average earning volume across observation window.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_inc_trimmed_mean": FeatureLineageRecord(
        feature_name="feat_inc_trimmed_mean",
        feature_group="income_level",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="10% symmetric trimmed mean of payouts",
        unit="INR",
        feature_type="derived_telemetry",
        semantic_meaning="Central tendency stripped of extreme platform surge spikes.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 2. Volatility & Dispersion
    "feat_inc_cv_90d": FeatureLineageRecord(
        feature_name="feat_inc_cv_90d",
        feature_group="income_volatility",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="StdDev(P_k) / Mean(P_k)",
        unit="Ratio [0.0, 5.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Coefficient of variation measuring relative earnings instability.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_inc_downside_var": FeatureLineageRecord(
        feature_name="feat_inc_downside_var",
        feature_group="income_volatility",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="(1/K) * sum(min(0, P_k - Median)^2)",
        unit="INR^2",
        feature_type="derived_telemetry",
        semantic_meaning="Semi-variance isolating adverse downside shocks below median.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_inc_iqr_ratio": FeatureLineageRecord(
        feature_name="feat_inc_iqr_ratio",
        feature_group="income_volatility",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="(P75 - P25) / Median",
        unit="Ratio [0.0, 10.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Non-parametric dispersion normalized by median.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_inc_min_max_ratio": FeatureLineageRecord(
        feature_name="feat_inc_min_max_ratio",
        feature_group="income_volatility",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Min(P_k) / Max(P_k)",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Spread ratio between worst and best weekly earnings.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 3. Trajectory & Trend
    "feat_trend_slope_90d": FeatureLineageRecord(
        feature_name="feat_trend_slope_90d",
        feature_group="income_trend",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="OLS slope of weekly income over time t=1..13",
        unit="INR/week",
        feature_type="derived_telemetry",
        semantic_meaning="Linear trajectory slope indicating earnings expansion or decay.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_trend_momentum_30_90": FeatureLineageRecord(
        feature_name="feat_trend_momentum_30_90",
        feature_group="income_trend",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Mean(payouts last 30d) / Mean(payouts 90d)",
        unit="Ratio [0.0, 5.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Recent earnings momentum (>1 expansion, <1 contraction).",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_trend_consec_drops": FeatureLineageRecord(
        feature_name="feat_trend_consec_drops",
        feature_group="income_trend",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Max consecutive cycles with P_{k} < P_{k-1}",
        unit="Count [0, 13]",
        feature_type="derived_telemetry",
        semantic_meaning="Maximum uninterrupted sequence of weekly earnings decline.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 4. Work Activity & Consistency
    "feat_act_active_days_ratio": FeatureLineageRecord(
        feature_name="feat_act_active_days_ratio",
        feature_group="work_activity",
        source_features=["daily_activity_events.active_hours"],
        calculation_formula="Count(days with active_hours > 0) / 90",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Platform engagement consistency across 90-day window.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_act_zero_earn_weeks": FeatureLineageRecord(
        feature_name="feat_act_zero_earn_weeks",
        feature_group="work_activity",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Count(weeks with payout == 0)",
        unit="Count [0, 13]",
        feature_type="derived_telemetry",
        semantic_meaning="Number of completely unproductive weeks with zero income.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_act_max_idle_streak": FeatureLineageRecord(
        feature_name="feat_act_max_idle_streak",
        feature_group="work_activity",
        source_features=["daily_activity_events.active_hours"],
        calculation_formula="Max consecutive calendar days with 0 active hours",
        unit="Days [0, 90]",
        feature_type="derived_telemetry",
        semantic_meaning="Longest consecutive duration of work inactivity.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_act_weekend_intensity": FeatureLineageRecord(
        feature_name="feat_act_weekend_intensity",
        feature_group="work_activity",
        source_features=["daily_activity_events.active_hours"],
        calculation_formula="Weekend active hours / Total active hours",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Proportion of gig labor performed during weekend peak demand.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 5. Resilience & Recovery
    "feat_rec_bounceback_ratio": FeatureLineageRecord(
        feature_name="feat_rec_bounceback_ratio",
        feature_group="resilience_recovery",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Post-trough peak earnings / Pre-trough baseline",
        unit="Ratio [0.0, 10.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Rebound elasticity following an earnings trough.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_rec_days_to_recover": FeatureLineageRecord(
        feature_name="feat_rec_days_to_recover",
        feature_group="resilience_recovery",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="Days from trough to restoring >= 80% baseline income",
        unit="Days [0.0, 90.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Elapsed recovery duration following earnings shortfall.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_rec_max_drawdown": FeatureLineageRecord(
        feature_name="feat_rec_max_drawdown",
        feature_group="resilience_recovery",
        source_features=["weekly_payout_events.payout_amount"],
        calculation_formula="(Peak - Trough) / Peak",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Peak-to-trough earning contraction depth.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 6. Platform Tenure & Standing
    "feat_ten_years_working": FeatureLineageRecord(
        feature_name="feat_ten_years_working",
        feature_group="tenure_standing",
        source_features=["applicant_profiles.years_working"],
        calculation_formula="Direct profile attribute",
        unit="Years [0.0, 50.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Total professional experience in the gig economy.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_ten_platform_rating": FeatureLineageRecord(
        feature_name="feat_ten_platform_rating",
        feature_group="tenure_standing",
        source_features=["applicant_profiles.platform_rating"],
        calculation_formula="Direct platform standing metric",
        unit="Rating [1.0, 5.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Platform customer satisfaction and quality standing.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_ten_trips_completed": FeatureLineageRecord(
        feature_name="feat_ten_trips_completed",
        feature_group="tenure_standing",
        source_features=["applicant_profiles.trips_completed"],
        calculation_formula="Lifetime orders/rides count",
        unit="Count [0, 100000]",
        feature_type="derived_telemetry",
        semantic_meaning="Cumulative gig work output and platform operational volume.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_ten_cancellation_rate": FeatureLineageRecord(
        feature_name="feat_ten_cancellation_rate",
        feature_group="tenure_standing",
        source_features=["applicant_profiles.cancellation_rate"],
        calculation_formula="Cancellations / Dispatches",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Operational reliability and fulfillment discipline.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 7. Liquidity & Financial Buffer
    "feat_liq_buffer_to_loan": FeatureLineageRecord(
        feature_name="feat_liq_buffer_to_loan",
        feature_group="liquidity_buffer",
        source_features=["applicant_profiles.liquid_buffer", "applications.requested_loan_amount"],
        calculation_formula="liquid_buffer / requested_loan_amount",
        unit="Ratio [0.0, 50.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Capital reserve cushion relative to total loan principal.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_liq_burn_months": FeatureLineageRecord(
        feature_name="feat_liq_burn_months",
        feature_group="liquidity_buffer",
        source_features=["applicant_profiles.liquid_buffer", "applicant_profiles.living_expenses"],
        calculation_formula="liquid_buffer / (living_expenses + debt + eps)",
        unit="Months [0.0, 60.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Cash reserve runway in months before insolvency with zero income.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_liq_net_margin": FeatureLineageRecord(
        feature_name="feat_liq_net_margin",
        feature_group="liquidity_buffer",
        source_features=["weekly_payout_events.payout_amount", "applicant_profiles.living_expenses"],
        calculation_formula="(Earnings - Living Expenses) / Earnings",
        unit="Ratio [-2.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Net operational savings margin after subsistence living costs.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 8. Payment Discipline
    "feat_pay_utility_on_time": FeatureLineageRecord(
        feature_name="feat_pay_utility_on_time",
        feature_group="payment_discipline",
        source_features=["payment_records.utility_bills"],
        calculation_formula="On-time bill payments / Total bill payments",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Punctuality on recurring non-credit utility obligations.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_pay_max_bill_delay": FeatureLineageRecord(
        feature_name="feat_pay_max_bill_delay",
        feature_group="payment_discipline",
        source_features=["payment_records.utility_bills"],
        calculation_formula="Max days past due across all utility bills",
        unit="Days [0, 180]",
        feature_type="derived_telemetry",
        semantic_meaning="Maximum payment delinquency on utility commitments.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_pay_repay_reliability": FeatureLineageRecord(
        feature_name="feat_pay_repay_reliability",
        feature_group="payment_discipline",
        source_features=["payment_records.alternative_loans"],
        calculation_formula="Composite alternative repayment index [0, 1]",
        unit="Index [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Track record of fulfilling micro-loan and informal commitments.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    # 9. Debt Burden & Capacity
    "feat_bur_dti_ratio": FeatureLineageRecord(
        feature_name="feat_bur_dti_ratio",
        feature_group="debt_burden",
        source_features=["applicant_profiles.existing_debt", "weekly_payout_events.payout_amount"],
        calculation_formula="existing_debt / median_monthly_income",
        unit="Ratio [0.0, 20.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Pre-existing monthly debt commitment relative to monthly income.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_bur_installment_dti": FeatureLineageRecord(
        feature_name="feat_bur_installment_dti",
        feature_group="debt_burden",
        source_features=["applications.requested_loan_amount", "applications.loan_tenure_months"],
        calculation_formula="projected_installment / median_monthly_income",
        unit="Ratio [0.0, 20.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Incremental debt leverage added by requested loan.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_bur_total_dti": FeatureLineageRecord(
        feature_name="feat_bur_total_dti",
        feature_group="debt_burden",
        source_features=["applicant_profiles.existing_debt", "applications.requested_loan_amount"],
        calculation_formula="(existing_debt + installment) / median_monthly_income",
        unit="Ratio [0.0, 20.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Total post-loan monthly debt service burden.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_bur_loan_to_income": FeatureLineageRecord(
        feature_name="feat_bur_loan_to_income",
        feature_group="debt_burden",
        source_features=["applications.requested_loan_amount", "weekly_payout_events.payout_amount"],
        calculation_formula="loan_amount / (median_monthly_income * 12)",
        unit="Ratio [0.0, 10.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Requested principal relative to annualized earning capacity.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # 10. Data Sufficiency
    "feat_suf_observed_days": FeatureLineageRecord(
        feature_name="feat_suf_observed_days",
        feature_group="data_sufficiency",
        source_features=["telemetry.timestamps"],
        calculation_formula="Days from first observed event to t0",
        unit="Days [0, 90]",
        feature_type="derived_telemetry",
        semantic_meaning="Temporal depth of consented observation history.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_suf_payout_count": FeatureLineageRecord(
        feature_name="feat_suf_payout_count",
        feature_group="data_sufficiency",
        source_features=["weekly_payout_events"],
        calculation_formula="Count of completed payout transactions",
        unit="Count [0, 90]",
        feature_type="derived_telemetry",
        semantic_meaning="Sample size of payout cycles (min 4 required for scoring).",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "feat_suf_group_count": FeatureLineageRecord(
        feature_name="feat_suf_group_count",
        feature_group="data_sufficiency",
        source_features=["data_providers"],
        calculation_formula="Distinct non-empty signal groups present at t0",
        unit="Count [0, 5]",
        feature_type="derived_telemetry",
        semantic_meaning="Breadth of alternative signal categories available.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_suf_missing_ratio": FeatureLineageRecord(
        feature_name="feat_suf_missing_ratio",
        feature_group="data_sufficiency",
        source_features=["feature_matrix"],
        calculation_formula="Count(null fields) / Count(total fields)",
        unit="Ratio [0.0, 1.0]",
        feature_type="derived_telemetry",
        semantic_meaning="Overall feature completeness across optional fields.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # Canonical Interactions from Contract
    "feat_int_vol_x_recovery": FeatureLineageRecord(
        feature_name="feat_int_vol_x_recovery",
        feature_group="volatility_interaction",
        source_features=["feat_inc_cv_90d", "feat_rec_days_to_recover"],
        calculation_formula="feat_inc_cv_90d * feat_rec_days_to_recover",
        unit="Index [0.0, 450.0]",
        feature_type="interaction_contract",
        semantic_meaning="Joint exposure to volatility and extended recovery duration.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_int_vol_x_buffer": FeatureLineageRecord(
        feature_name="feat_int_vol_x_buffer",
        feature_group="volatility_interaction",
        source_features=["feat_inc_cv_90d", "feat_liq_buffer_to_loan"],
        calculation_formula="feat_inc_cv_90d / (feat_liq_buffer_to_loan + 0.1)",
        unit="Index [0.0, 50.0]",
        feature_type="interaction_contract",
        semantic_meaning="Earnings instability unbuffered by capital reserves.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_int_trend_x_dti": FeatureLineageRecord(
        feature_name="feat_int_trend_x_dti",
        feature_group="volatility_interaction",
        source_features=["feat_trend_slope_90d", "feat_bur_total_dti"],
        calculation_formula="feat_trend_slope_90d * feat_bur_total_dti",
        unit="Index [-50000, 50000]",
        feature_type="interaction_contract",
        semantic_meaning="Compounding risk of downward income trajectory with heavy debt burden.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_int_resilience_idx": FeatureLineageRecord(
        feature_name="feat_int_resilience_idx",
        feature_group="volatility_interaction",
        source_features=["feat_rec_bounceback_ratio", "feat_inc_cv_90d", "feat_liq_burn_months"],
        calculation_formula="(bounceback * burn_months) / (cv + 0.1)",
        unit="Index [0.0, 100.0]",
        feature_type="interaction_contract",
        semantic_meaning="Composite financial resilience index combining recovery and liquidity against volatility.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    # Raw Context Inputs
    "requested_loan_amount": FeatureLineageRecord(
        feature_name="requested_loan_amount",
        feature_group="loan_context",
        source_features=["applications.requested_loan_amount"],
        calculation_formula="Direct loan application attribute",
        unit="INR",
        feature_type="raw_input",
        semantic_meaning="Total principal requested in loan application.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "loan_tenure_months": FeatureLineageRecord(
        feature_name="loan_tenure_months",
        feature_group="loan_context",
        source_features=["applications.loan_tenure_months"],
        calculation_formula="Direct loan application attribute",
        unit="Months",
        feature_type="raw_input",
        semantic_meaning="Requested repayment duration in months.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "years_working": FeatureLineageRecord(
        feature_name="years_working",
        feature_group="profile_context",
        source_features=["applicant_profiles.years_working"],
        calculation_formula="Direct profile attribute",
        unit="Years",
        feature_type="raw_input",
        semantic_meaning="Worker lifetime professional work experience.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "average_working_days": FeatureLineageRecord(
        feature_name="average_working_days",
        feature_group="profile_context",
        source_features=["applicant_profiles.average_working_days"],
        calculation_formula="Direct profile attribute",
        unit="Days/month",
        feature_type="raw_input",
        semantic_meaning="Self-reported active monthly working days.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "gig_work_type": FeatureLineageRecord(
        feature_name="gig_work_type",
        feature_group="profile_context",
        source_features=["applicant_profiles.gig_work_type"],
        calculation_formula="Categorical nominal sector",
        unit="Nominal Category",
        feature_type="raw_input",
        semantic_meaning="Primary gig economy sector.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    "loan_purpose": FeatureLineageRecord(
        feature_name="loan_purpose",
        feature_group="loan_context",
        source_features=["applications.loan_purpose"],
        calculation_formula="Categorical nominal purpose",
        unit="Nominal Category",
        feature_type="raw_input",
        semantic_meaning="Stated operational purpose of loan proceeds.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
    # ---------------------------------------------------------
    # 9 Newly Engineered Volatility-Aware Interaction Features
    # ---------------------------------------------------------
    "feat_eng_vol_to_baseline": FeatureLineageRecord(
        feature_name="feat_eng_vol_to_baseline",
        feature_group="volatility_interaction",
        source_features=["feat_inc_cv_90d", "feat_inc_median_90d"],
        calculation_formula="feat_inc_cv_90d / (feat_inc_median_90d / 10000.0 + 0.1)",
        unit="Dimensionless Ratio",
        feature_type="engineered_volatility",
        semantic_meaning="Income volatility normalized by absolute earnings capacity (₹10k scale). Distinguishes high-earner variance from low-earner distress.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_downside_to_median": FeatureLineageRecord(
        feature_name="feat_eng_downside_to_median",
        feature_group="volatility_interaction",
        source_features=["feat_inc_downside_var", "feat_inc_median_90d"],
        calculation_formula="sqrt(feat_inc_downside_var) / (feat_inc_median_90d + 1.0)",
        unit="Dimensionless Ratio",
        feature_type="engineered_volatility",
        semantic_meaning="Downside standard deviation relative to median income. Measures downside vulnerability normalized by earning baseline.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_vol_x_trend": FeatureLineageRecord(
        feature_name="feat_eng_vol_x_trend",
        feature_group="volatility_interaction",
        source_features=["feat_inc_cv_90d", "feat_trend_momentum_30_90"],
        calculation_formula="feat_inc_cv_90d * (feat_trend_momentum_30_90 - 1.0)",
        unit="Dimensionless Index",
        feature_type="engineered_volatility",
        semantic_meaning="Directional volatility: positive index indicates expanding variance (surge/growth), negative index indicates decaying variance (deterioration).",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_vol_to_bounceback": FeatureLineageRecord(
        feature_name="feat_eng_vol_to_bounceback",
        feature_group="volatility_interaction",
        source_features=["feat_inc_cv_90d", "feat_rec_bounceback_ratio"],
        calculation_formula="feat_inc_cv_90d / (feat_rec_bounceback_ratio + 0.1)",
        unit="Dimensionless Ratio",
        feature_type="engineered_volatility",
        semantic_meaning="Earnings volatility unmitigated by post-trough recovery bounceback.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_recovery_velocity": FeatureLineageRecord(
        feature_name="feat_eng_recovery_velocity",
        feature_group="volatility_interaction",
        source_features=["feat_rec_bounceback_ratio", "feat_rec_days_to_recover"],
        calculation_formula="feat_rec_bounceback_ratio / (feat_rec_days_to_recover / 7.0 + 1.0)",
        unit="Velocity Index",
        feature_type="engineered_volatility",
        semantic_meaning="Rebound strength per week elapsed from shock trough. Higher values denote rapid, elastic post-trough recovery.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_buffer_burn_coverage": FeatureLineageRecord(
        feature_name="feat_eng_buffer_burn_coverage",
        feature_group="volatility_interaction",
        source_features=["feat_liq_burn_months", "feat_liq_buffer_to_loan"],
        calculation_formula="feat_liq_burn_months * (feat_liq_buffer_to_loan + 0.1)",
        unit="Months",
        feature_type="engineered_volatility",
        semantic_meaning="Comprehensive liquidity strength: reserve runway months multiplied by loan capital buffer.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_vol_cushion_ratio": FeatureLineageRecord(
        feature_name="feat_eng_vol_cushion_ratio",
        feature_group="volatility_interaction",
        source_features=["feat_liq_buffer_to_loan", "feat_inc_cv_90d"],
        calculation_formula="(feat_liq_buffer_to_loan + 0.1) / (feat_inc_cv_90d + 0.05)",
        unit="Ratio",
        feature_type="engineered_volatility",
        semantic_meaning="Liquid buffer available per unit of income volatility. High cushion indicates ample liquidity insulation against earnings dips.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_dti_risk_multiplier": FeatureLineageRecord(
        feature_name="feat_eng_dti_risk_multiplier",
        feature_group="volatility_interaction",
        source_features=["feat_bur_total_dti", "feat_inc_cv_90d"],
        calculation_formula="feat_bur_total_dti * (1.0 + feat_inc_cv_90d)",
        unit="Leverage Index",
        feature_type="engineered_volatility",
        semantic_meaning="Compounding financial stress of high DTI combined with volatile earnings cashflow.",
        used_in_baseline=False,
        used_in_volatility_aware=True,
    ),
    "feat_eng_installment_floor_coverage": FeatureLineageRecord(
        feature_name="feat_eng_installment_floor_coverage",
        feature_group="debt_burden",
        source_features=["feat_inc_p25_90d", "applications.requested_loan_amount", "applications.loan_tenure_months"],
        calculation_formula="feat_inc_p25_90d / (requested_loan_amount / loan_tenure_months + 1.0)",
        unit="Coverage Ratio",
        feature_type="engineered_volatility",
        semantic_meaning="Conservative earning floor (25th percentile) coverage of monthly loan installment.",
        used_in_baseline=True,
        used_in_volatility_aware=True,
    ),
}


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Deterministic, leakage-safe feature engineering transformer for credit risk data."""

    def __init__(
        self,
        include_engineered_interactions: bool = True,
    ) -> None:
        """Initialize feature engineer.

        Args:
            include_engineered_interactions: Whether to compute the 9 volatility interaction features.
        """
        self.include_engineered_interactions = include_engineered_interactions
        self.is_fitted_: bool = False
        self.feature_names_in_: List[str] = []
        self.engineered_feature_names_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> "FeatureEngineer":
        """Validate input DataFrame schema and initialize feature engineering state."""
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"X must be a pandas DataFrame, got {type(X).__name__}")
        if len(X) == 0:
            raise ValueError("Cannot fit FeatureEngineer on an empty DataFrame.")

        self.feature_names_in_ = list(X.columns)
        self.engineered_feature_names_ = (
            list(ENGINEERED_VOLATILITY_FEATURES) if self.include_engineered_interactions else []
        )
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Derive engineered interaction features deterministically.

        Args:
            X: Input DataFrame containing canonical derived features and loan attributes.

        Returns:
            pd.DataFrame: DataFrame containing all input columns plus newly engineered features.
        """
        if not self.is_fitted_:
            # Auto-fit if transform is called directly
            self.fit(X)

        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"X must be a pandas DataFrame, got {type(X).__name__}")

        result_df = X.copy()
        if not self.include_engineered_interactions:
            return result_df

        # -----------------------------------------------------------------
        # 1. Volatility relative to baseline earnings
        # -----------------------------------------------------------------
        cv = result_df["feat_inc_cv_90d"].values
        median_inc = result_df["feat_inc_median_90d"].values
        downside_var = result_df["feat_inc_downside_var"].values

        # Normalizes CV by income scale (₹10,000 unit), with +0.1 epsilon
        result_df["feat_eng_vol_to_baseline"] = cv / (median_inc / 10000.0 + 0.1)

        # Downside standard deviation as ratio of median income
        result_df["feat_eng_downside_to_median"] = np.sqrt(np.maximum(downside_var, 0.0)) / (
            median_inc + 1.0
        )

        # -----------------------------------------------------------------
        # 2. Volatility conditioned on trajectory / trend
        # -----------------------------------------------------------------
        momentum = result_df["feat_trend_momentum_30_90"].values
        # Positive index = expanding volatility with growth; negative = decay volatility
        result_df["feat_eng_vol_x_trend"] = cv * (momentum - 1.0)

        # -----------------------------------------------------------------
        # 3. Volatility conditioned on recovery and resilience
        # -----------------------------------------------------------------
        bounceback = result_df["feat_rec_bounceback_ratio"].values
        days_recover = result_df["feat_rec_days_to_recover"].values

        result_df["feat_eng_vol_to_bounceback"] = cv / (bounceback + 0.1)
        result_df["feat_eng_recovery_velocity"] = bounceback / (days_recover / 7.0 + 1.0)

        # -----------------------------------------------------------------
        # 4. Volatility conditioned on liquidity & cashflow buffer
        # -----------------------------------------------------------------
        buffer_loan = result_df["feat_liq_buffer_to_loan"].values
        burn_months = result_df["feat_liq_burn_months"].values

        result_df["feat_eng_buffer_burn_coverage"] = burn_months * (buffer_loan + 0.1)
        result_df["feat_eng_vol_cushion_ratio"] = (buffer_loan + 0.1) / (cv + 0.05)

        # -----------------------------------------------------------------
        # 5. Volatility conditioned on debt & obligation capacity
        # -----------------------------------------------------------------
        total_dti = result_df["feat_bur_total_dti"].values
        loan_amount = result_df["requested_loan_amount"].values
        tenure = result_df["loan_tenure_months"].values
        p25_inc = result_df["feat_inc_p25_90d"].values

        # Compounding debt burden multiplier under volatility
        result_df["feat_eng_dti_risk_multiplier"] = total_dti * (1.0 + cv)

        # Conservative income floor (P25) coverage of monthly installment
        monthly_installment = loan_amount / np.maximum(tenure, 1.0)
        result_df["feat_eng_installment_floor_coverage"] = p25_inc / (monthly_installment + 1.0)

        return result_df

    def fit_transform(self, X: pd.DataFrame, y: Optional[Any] = None) -> pd.DataFrame:
        """Fit and transform DataFrame in one step."""
        return self.fit(X, y).transform(X)

    @classmethod
    def get_feature_subset(
        cls, variant: Union[str, ExperimentVariant] = ExperimentVariant.VOLATILITY_AWARE
    ) -> List[str]:
        """Return the authorized list of feature names for a given experiment variant.

        Args:
            variant: Either ExperimentVariant.BASELINE or ExperimentVariant.VOLATILITY_AWARE.

        Returns:
            List[str]: List of column names to select for model ingestion.
        """
        variant_str = variant.value if isinstance(variant, ExperimentVariant) else str(variant).upper()

        if variant_str == ExperimentVariant.BASELINE.value:
            return list(BASELINE_FEATURE_SET)
        elif variant_str == ExperimentVariant.VOLATILITY_AWARE.value:
            all_cols = (
                list(DERIVED_FEATURES)
                + list(RAW_NUMERIC_COLUMNS)
                + list(CATEGORICAL_INPUT_COLUMNS)
                + list(ENGINEERED_VOLATILITY_FEATURES)
            )
            # Retain unique columns in order
            seen: Set[str] = set()
            ordered: List[str] = []
            for c in all_cols:
                if c not in seen:
                    seen.add(c)
                    ordered.append(c)
            return ordered
        else:
            raise ValueError(
                f"Unknown variant '{variant_str}'. Choose 'BASELINE' or 'VOLATILITY_AWARE'."
            )

    @classmethod
    def get_feature_inventory(cls) -> pd.DataFrame:
        """Return complete feature inventory and lineage as a DataFrame."""
        rows = [record.to_dict() for record in MASTER_LINEAGE.values()]
        return pd.DataFrame(rows)


def build_model_ready_matrices(
    train_df: pd.DataFrame,
    val_df: Optional[pd.DataFrame] = None,
    test_df: Optional[pd.DataFrame] = None,
    variant: Union[str, ExperimentVariant] = ExperimentVariant.VOLATILITY_AWARE,
    target_column: str = "target_default_flag",
    scaler_type: str = "robust",
    add_missing_indicators: bool = True,
    scored_only: bool = True,
) -> Dict[str, Any]:
    """Complete end-to-end pipeline: feature engineering + train-only preprocessing.

    Args:
        train_df: Training split DataFrame.
        val_df: Validation split DataFrame (optional).
        test_df: Test split DataFrame (optional).
        variant: Feature selection variant ('BASELINE' or 'VOLATILITY_AWARE').
        target_column: Target column name.
        scaler_type: Preprocessing scaler ('robust', 'standard', or None).
        add_missing_indicators: Whether to add missingness binary flags.
        scored_only: If True, filters out unscored (Insufficient Data) rows for model matrices.

    Returns:
        Dict containing X_train, y_train, X_val, y_val, X_test, y_test, preprocessor, and engineer.
    """
    engineer = FeatureEngineer(include_engineered_interactions=True)

    # 1. Feature Engineering (deterministic transformations)
    train_eng = engineer.fit_transform(train_df)
    val_eng = engineer.transform(val_df) if val_df is not None else None
    test_eng = engineer.transform(test_df) if test_df is not None else None

    # Filter scored rows if requested
    if scored_only and target_column in train_eng.columns:
        train_eng = train_eng[train_eng[target_column].notnull()].copy()
        if val_eng is not None and target_column in val_eng.columns:
            val_eng = val_eng[val_eng[target_column].notnull()].copy()
        if test_eng is not None and target_column in test_eng.columns:
            test_eng = test_eng[test_eng[target_column].notnull()].copy()

    # Determine feature subset
    selected_cols = FeatureEngineer.get_feature_subset(variant)

    # 2. Preprocessing (fitted strictly on training split)
    preprocessor = CreditRiskPreprocessor(
        scaler_type=scaler_type,
        apply_log_transform=True,
        clip_leverage_ratios=True,
        add_missing_indicators=add_missing_indicators,
        include_raw_loan_features=True,
        selected_features=selected_cols,
    )

    X_train = preprocessor.fit_transform(train_eng)
    y_train = (
        train_eng[target_column].values.astype(int)
        if target_column in train_eng.columns
        else None
    )

    X_val = preprocessor.transform(val_eng) if val_eng is not None else None
    y_val = (
        val_eng[target_column].values.astype(int)
        if val_eng is not None and target_column in val_eng.columns
        else None
    )

    X_test = preprocessor.transform(test_eng) if test_eng is not None else None
    y_test = (
        test_eng[target_column].values.astype(int)
        if test_eng is not None and target_column in test_eng.columns
        else None
    )

    return {
        "X_train": X_train,
        "y_train": y_train,
        "X_val": X_val,
        "y_val": y_val,
        "X_test": X_test,
        "y_test": y_test,
        "feature_engineer": engineer,
        "preprocessor": preprocessor,
        "feature_names_out": preprocessor.get_feature_names_out(),
        "variant": variant,
    }
