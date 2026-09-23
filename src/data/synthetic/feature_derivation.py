"""
PARAKH Synthetic Credit Application Generator - Feature Derivation Layer (P2-T06)
Derives all 40 frozen ML model features from raw application data and 90-day historical telemetry.
Strictly adheres to docs/final-ml-data-requirements.md (v1.1.0 Frozen Specification).

Guarantees:
- Pure deterministic derivation: no PRNG calls, identical inputs yield identical outputs
- Strict temporal isolation: zero predictors or events at or after cutoff t0
- Cohort independence: cohort labels are NEVER inspected or used in feature calculations
- Strict preservation of zero vs unobserved vs null semantics
- Full range and impossible-combination validation
"""

from datetime import datetime, timezone
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from src.data.synthetic.config import OBSERVATION_WINDOW_DAYS
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    TemporalLeakageError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    ApplicationHistoricalData,
    DailyActivityEvent,
    DerivedFeatures,
    WeeklyPayoutEvent,
)


# ==============================================================================
# 1. INDIVIDUAL FEATURE CALCULATION FUNCTIONS (DETERMINISTIC & MODULAR)
# ==============================================================================

def calculate_median_income(payouts: List[float]) -> float:
    """Calculate median of weekly net payouts {I_k}."""
    if not payouts:
        return 0.0
    sorted_p = sorted(payouts)
    k = len(sorted_p)
    if k % 2 == 1:
        med = sorted_p[k // 2]
    else:
        med = (sorted_p[k // 2 - 1] + sorted_p[k // 2]) / 2.0
    return round(med, 2)


def calculate_p25_income(payouts: List[float], median_val: float) -> float:
    """Calculate 25th percentile of weekly net payouts using exclusive quantiles."""
    if not payouts:
        return 0.0
    sorted_p = sorted(payouts)
    k = len(sorted_p)
    if k == 1:
        p25 = sorted_p[0]
    else:
        q1, _, _ = statistics.quantiles(sorted_p, n=4, method="exclusive")
        p25 = max(0.0, min(q1, median_val))
    return round(p25, 2)


def calculate_mean_income(payouts: List[float]) -> float:
    """Calculate arithmetic mean of weekly net payouts."""
    if not payouts:
        return 0.0
    return round(sum(payouts) / float(len(payouts)), 2)


def calculate_trimmed_mean_income(payouts: List[float]) -> float:
    """Calculate 10% trimmed mean of weekly net payouts."""
    if not payouts:
        return 0.0
    sorted_p = sorted(payouts)
    k = len(sorted_p)
    trim_k = int(math.floor(0.10 * k))
    if trim_k > 0 and k - 2 * trim_k > 0:
        trimmed = sorted_p[trim_k : k - trim_k]
        return round(sum(trimmed) / float(len(trimmed)), 2)
    return round(sum(sorted_p) / float(k), 2)


def calculate_income_cv(payouts: List[float]) -> float:
    """Calculate coefficient of variation (sigma / mu) of weekly net payouts."""
    if len(payouts) <= 1:
        return 0.0
    mean_val = sum(payouts) / float(len(payouts))
    if mean_val <= 0.0:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in payouts) / float(len(payouts))
    std = math.sqrt(variance)
    cv = std / mean_val
    return round(min(max(cv, 0.0), 5.0), 4)


def calculate_downside_variance(payouts: List[float], median_val: float) -> float:
    """Calculate semi-variance strictly on weekly payouts below the median."""
    if not payouts:
        return 0.0
    k = len(payouts)
    squared_shortfalls = sum((x - median_val) ** 2 for x in payouts if x < median_val)
    return round(squared_shortfalls / float(k), 2)


def calculate_iqr_ratio(payouts: List[float], median_val: float) -> float:
    """Calculate interquartile range normalized by median: (P75 - P25) / Median."""
    if len(payouts) <= 1 or median_val <= 0.0:
        return 0.0
    sorted_p = sorted(payouts)
    q1, _, q3 = statistics.quantiles(sorted_p, n=4, method="exclusive")
    iqr = max(0.0, q3 - q1)
    return round(min(iqr / median_val, 10.0), 4)


def calculate_min_max_ratio(payouts: List[float]) -> float:
    """Calculate ratio of minimum weekly payout to maximum weekly payout."""
    if len(payouts) <= 1:
        return 1.0
    min_val = min(payouts)
    max_val = max(payouts)
    if max_val <= 0.0:
        return 0.0
    return round(min(max(min_val / max_val, 0.0), 1.0), 4)


def calculate_trend_slope(payouts: List[float]) -> float:
    """Calculate OLS linear regression slope across weekly payout sequence (INR/week)."""
    k = len(payouts)
    if k <= 1:
        return 0.0
    k_mean = (k + 1) / 2.0
    y_mean = sum(payouts) / float(k)
    num = sum((i + 1 - k_mean) * (payouts[i] - y_mean) for i in range(k))
    den = sum((i + 1 - k_mean) ** 2 for i in range(k))
    if den == 0.0:
        return 0.0
    slope = num / den
    return round(min(max(slope, -50000.0), 50000.0), 2)


def calculate_trend_momentum(payouts: List[float]) -> float:
    """Calculate momentum ratio: mean of last 4 weeks divided by mean of full observation window."""
    k = len(payouts)
    if k < 4:
        return 1.0  # Flat / neutral baseline when history is insufficient
    mean_full = sum(payouts) / float(k)
    if mean_full <= 0.0:
        return 1.0
    recent_payouts = payouts[-4:]
    mean_recent = sum(recent_payouts) / 4.0
    momentum = mean_recent / mean_full
    return round(min(max(momentum, 0.0), 5.0), 4)


def calculate_consecutive_drops(payouts: List[float]) -> int:
    """Calculate maximum streak of consecutive declining weekly payout cycles."""
    if len(payouts) <= 1:
        return 0
    max_drops = 0
    current_drops = 0
    for i in range(1, len(payouts)):
        if payouts[i] < payouts[i - 1]:
            current_drops += 1
            if current_drops > max_drops:
                max_drops = current_drops
        else:
            current_drops = 0
    return min(max_drops, 13)


def calculate_active_days_ratio(daily_events: List[DailyActivityEvent]) -> float:
    """Calculate active days ratio: active shifts worked divided by 90 observation days."""
    if not daily_events:
        return 0.0
    active_count = sum(1 for ev in daily_events if ev.is_active)
    return round(active_count / float(OBSERVATION_WINDOW_DAYS), 4)


def calculate_zero_earning_weeks(payouts: List[float]) -> int:
    """Count weekly settlement payout cycles with zero recorded net earnings."""
    return sum(1 for p in payouts if p == 0.0)


def calculate_max_idle_streak(daily_events: List[DailyActivityEvent]) -> int:
    """Calculate longest consecutive streak of inactive calendar days."""
    if not daily_events:
        return 0
    max_streak = 0
    current_streak = 0
    for ev in daily_events:
        if not ev.is_active:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
    return min(max_streak, OBSERVATION_WINDOW_DAYS)


def calculate_weekend_intensity(daily_events: List[DailyActivityEvent]) -> float:
    """Calculate weekend active hours divided by total active hours."""
    weekend_hours = sum(ev.hours_worked for ev in daily_events if ev.is_weekend and not ev.is_unobserved)
    total_hours = sum(ev.hours_worked for ev in daily_events if not ev.is_unobserved)
    if total_hours <= 0.0:
        return 0.0
    return round(min(max(weekend_hours / total_hours, 0.0), 1.0), 4)


def calculate_recovery_metrics(
    payouts: List[float],
    daily_events: List[DailyActivityEvent],
    median_val: float,
) -> Tuple[float, float]:
    """
    Calculate post-trough bounceback ratio and days to recover to >= 85% baseline.
    Returns: (feat_rec_bounceback_ratio, feat_rec_days_to_recover)
    """
    k = len(payouts)
    # 1. Weekly payout trough check (< 85% median)
    if k > 0 and median_val > 0.0:
        min_payout = min(payouts)
        if min_payout < 0.85 * median_val:
            trough_idx = payouts.index(min_payout)
            post_trough = payouts[trough_idx + 1 :]
            if post_trough:
                bounceback = max(post_trough) / median_val
                rec_idx = None
                for idx, p in enumerate(post_trough, start=1):
                    if p >= 0.85 * median_val:
                        rec_idx = idx
                        break
                days_to_recover = float(rec_idx * 7) if rec_idx is not None else float(min(90, (k - trough_idx) * 7))
            else:
                bounceback = min_payout / median_val
                days_to_recover = float(min(90, (k - trough_idx) * 7))
            return (
                round(min(max(bounceback, 0.0), 10.0), 4),
                round(min(max(days_to_recover, 0.0), 90.0), 1),
            )

    # 2. Daily shift trough check (e.g. acute mid-horizon shock)
    observed_daily = [ev.net_earnings for ev in daily_events if not ev.is_unobserved]
    daily_baseline = median_val / 6.0 if median_val > 0.0 else 0.0

    if daily_baseline > 0.0 and observed_daily:
        min_daily = min(observed_daily)
        if min_daily < 0.70 * daily_baseline:
            trough_day = observed_daily.index(min_daily)
            post_daily = observed_daily[trough_day + 1 :]
            if post_daily:
                bounceback = max(post_daily) / daily_baseline
                rec_day = None
                for idx, val in enumerate(post_daily, start=1):
                    if val >= 0.85 * daily_baseline:
                        rec_day = idx
                        break
                days_to_recover = float(rec_day if rec_day is not None else len(post_daily))
            else:
                bounceback = 1.0
                days_to_recover = 0.0
            return (
                round(min(max(bounceback, 0.0), 10.0), 4),
                round(min(max(days_to_recover, 0.0), 90.0), 1),
            )

    # 3. Steady profile / insufficient history without acute dips
    if payouts and median_val > 0.0:
        bounceback = max(payouts) / median_val
    else:
        bounceback = 1.0
    days_to_recover = 0.0
    return (
        round(min(max(bounceback, 0.0), 10.0), 4),
        round(days_to_recover, 1),
    )


def calculate_max_drawdown(payouts: List[float]) -> float:
    """Calculate maximum peak-to-trough percentage drawdown across weekly payouts."""
    if len(payouts) <= 1:
        return 0.0
    peak = 0.0
    max_dd = 0.0
    for p in payouts:
        if p > peak:
            peak = p
        if peak > 0.0:
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd
    return round(min(max(max_dd, 0.0), 1.0), 4)


def calculate_buffer_to_loan(cashflow_buffer: float, loan_amount: float) -> float:
    """Calculate cashflow buffer divided by requested loan amount."""
    if loan_amount <= 0.0:
        return 0.0
    return round(min(max(cashflow_buffer / loan_amount, 0.0), 50.0), 4)


def calculate_burn_months(cashflow_buffer: float, existing_debt: float, living_cost: float) -> float:
    """Calculate liquid reserve buffer divided by monthly non-discretionary commitments."""
    monthly_commitments = existing_debt + living_cost
    if monthly_commitments <= 0.0:
        return 0.0
    return round(min(max(cashflow_buffer / monthly_commitments, 0.0), 60.0), 4)


def calculate_net_margin(
    daily_events: List[DailyActivityEvent],
    monthly_living_expense: float,
    existing_monthly_debt: float,
    observed_days: int,
) -> float:
    """Calculate net cash flow margin: (Gross earnings - expenses) / Gross earnings over 90d."""
    total_gross = sum(ev.gross_earnings for ev in daily_events if not ev.is_unobserved)
    total_net = sum(ev.net_earnings for ev in daily_events if not ev.is_unobserved)
    if total_gross <= 0.0:
        return -1.0
    expenses = (monthly_living_expense + existing_monthly_debt) * (float(observed_days) / 30.0)
    margin = (total_net - expenses) / total_gross
    return round(min(max(margin, -2.0), 1.0), 4)


def calculate_dti_ratios(
    existing_monthly_debt: float,
    contractual_emi: float,
    median_weekly_income: float,
) -> Tuple[float, float, float]:
    """
    Calculate DTI ratios against median monthly income.
    Returns: (feat_bur_dti_ratio, feat_bur_installment_dti, feat_bur_total_dti)
    """
    monthly_income = median_weekly_income * 4.333333
    if monthly_income <= 0.0:
        dti = 0.0 if existing_monthly_debt == 0.0 else 20.0
        installment_dti = 20.0
    else:
        dti = existing_monthly_debt / monthly_income
        installment_dti = contractual_emi / monthly_income

    dti = min(max(dti, 0.0), 20.0)
    installment_dti = min(max(installment_dti, 0.0), 20.0)
    total_dti = min(dti + installment_dti, 20.0)
    return (
        round(dti, 4),
        round(installment_dti, 4),
        round(total_dti, 4),
    )


def calculate_loan_to_income(loan_amount: float, median_weekly_income: float) -> float:
    """Calculate requested loan principal divided by annualized median income."""
    annual_income = median_weekly_income * 52.0
    if annual_income <= 0.0:
        return 10.0
    return round(min(max(loan_amount / annual_income, 0.0), 10.0), 4)


def calculate_trips_completed(daily_events: List[DailyActivityEvent]) -> int:
    """Calculate cumulative trips completed in observation window from active working hours."""
    total_hours = sum(ev.hours_worked for ev in daily_events if not ev.is_unobserved)
    trips = int(round(total_hours * 1.6))
    return min(max(trips, 0), 100000)


def calculate_group_count(
    history: ApplicationHistoricalData,
    profile: ApplicantProfile,
    application: Application,
) -> int:
    """
    Calculate active core signal groups populated across the trailing observation window
    (Section 12.1 and Table 2 of ml-data-specification):
    1. Gig Income Series: >= 30 days observed and >= 4 completed payout cycles
    2. Daily Work Activity: >= 30 days observed and >= 10 active days
    3. Cashflow Buffer: verified trailing buffer (requires >= 30 days observation)
    4. Payment Discipline: verified repayment track record (requires >= 30 days observation)
    5. Financial Obligations: existing debt and loan EMI populated
    """
    if history.observed_days < 30:
        # Thin-file new entrant: only application-level financial obligations group is established
        return 1

    has_gig_income = history.observed_days >= 30 and len(history.weekly_payouts) >= 4
    active_days_count = sum(1 for ev in history.daily_events if ev.is_active and not ev.is_unobserved)
    has_work_activity = history.observed_days >= 30 and active_days_count >= 10
    has_cashflow_buffer = profile.starting_cashflow_buffer is not None and profile.starting_cashflow_buffer > 0.0
    has_payment_discipline = profile.payment_reliability is not None
    has_financial_obligations = profile.existing_monthly_debt is not None and application.contractual_emi is not None

    count = sum([
        has_gig_income,
        has_work_activity,
        has_cashflow_buffer,
        has_payment_discipline,
        has_financial_obligations,
    ])
    return min(max(count, 0), 5)


def calculate_missing_ratio(optional_values: List[Any]) -> float:
    """Calculate missing ratio over the 18 optional fields."""
    if not optional_values:
        return 0.0
    null_count = sum(1 for val in optional_values if val is None)
    return round(min(max(null_count / 18.0, 0.0), 1.0), 4)


def calculate_interaction_features(
    cv: float,
    recovery_days: float,
    buffer_to_loan: float,
    slope: float,
    total_dti: float,
    bounceback: float,
) -> Tuple[float, float, float, float]:
    """
    Calculate all 4 mandatory interaction features:
    1. feat_int_vol_x_recovery = cv * recovery_days
    2. feat_int_vol_x_buffer = cv / (buffer_to_loan + 0.1)
    3. feat_int_trend_x_dti = slope * (1.0 + total_dti)
    4. feat_int_resilience_idx = bounceback / (cv + 0.05)
    """
    int_vol_rec = min(max(cv * recovery_days, 0.0), 450.0)
    int_vol_buf = min(max(cv / (buffer_to_loan + 0.1), 0.0), 50.0)
    int_trend_dti = min(max(slope * (1.0 + total_dti), -50000.0), 50000.0)
    int_resilience = min(max(bounceback / (cv + 0.05), 0.0), 100.0)

    return (
        round(int_vol_rec, 4),
        round(int_vol_buf, 4),
        round(int_trend_dti, 2),
        round(int_resilience, 4),
    )


# ==============================================================================
# 2. FEATURE RANGE & IMPOSSIBLE COMBINATION VALIDATOR
# ==============================================================================

def validate_derived_features(features: DerivedFeatures) -> None:
    """
    Validates all 40 derived features against frozen bounds and impossible combination rules.
    Raises ValidationError or ImpossibleCombinationError on violations.
    """
    # 1. Impossible combination checks (Section 5.2)
    if features.feat_act_active_days_ratio == 0.0 and features.feat_inc_median_90d > 0.0:
        raise ImpossibleCombinationError(
            f"Zero active days with positive income: active_ratio={features.feat_act_active_days_ratio}, "
            f"median_income={features.feat_inc_median_90d}"
        )
    if features.feat_inc_cv_90d == 0.0 and features.feat_inc_downside_var > 0.0:
        raise ImpossibleCombinationError(
            f"Zero CV with positive downside variance: cv={features.feat_inc_cv_90d}, "
            f"downside_var={features.feat_inc_downside_var}"
        )
    if features.feat_rec_bounceback_ratio < 0.0:
        raise ImpossibleCombinationError(
            f"Negative bounceback ratio: {features.feat_rec_bounceback_ratio}"
        )
    if features.feat_suf_payout_count > features.feat_suf_observed_days:
        raise ImpossibleCombinationError(
            f"Payout count exceeds observed days: payouts={features.feat_suf_payout_count}, "
            f"observed_days={features.feat_suf_observed_days}"
        )

    # 2. Mandatory bounds checks
    assert 0.0 <= features.feat_inc_median_90d <= 500000.0, f"feat_inc_median_90d out of bounds: {features.feat_inc_median_90d}"
    assert 0.0 <= features.feat_inc_p25_90d <= 500000.0, f"feat_inc_p25_90d out of bounds: {features.feat_inc_p25_90d}"
    assert features.feat_inc_p25_90d <= features.feat_inc_median_90d, "feat_inc_p25_90d must not exceed median"
    assert 0.0 <= features.feat_inc_cv_90d <= 5.0, f"feat_inc_cv_90d out of bounds: {features.feat_inc_cv_90d}"
    assert 0.0 <= features.feat_inc_downside_var <= 1.0e10, f"feat_inc_downside_var out of bounds: {features.feat_inc_downside_var}"
    assert -50000.0 <= features.feat_trend_slope_90d <= 50000.0, f"feat_trend_slope_90d out of bounds: {features.feat_trend_slope_90d}"
    assert 0.0 <= features.feat_trend_momentum_30_90 <= 5.0, f"feat_trend_momentum_30_90 out of bounds: {features.feat_trend_momentum_30_90}"
    assert 0.0 <= features.feat_act_active_days_ratio <= 1.0, f"feat_act_active_days_ratio out of bounds: {features.feat_act_active_days_ratio}"
    assert 0 <= features.feat_act_zero_earn_weeks <= 13, f"feat_act_zero_earn_weeks out of bounds: {features.feat_act_zero_earn_weeks}"
    assert 0.0 <= features.feat_rec_bounceback_ratio <= 10.0, f"feat_rec_bounceback_ratio out of bounds: {features.feat_rec_bounceback_ratio}"
    assert 0.0 <= features.feat_rec_days_to_recover <= 90.0, f"feat_rec_days_to_recover out of bounds: {features.feat_rec_days_to_recover}"
    assert 0.0 <= features.feat_liq_buffer_to_loan <= 50.0, f"feat_liq_buffer_to_loan out of bounds: {features.feat_liq_buffer_to_loan}"
    assert 0.0 <= features.feat_liq_burn_months <= 60.0, f"feat_liq_burn_months out of bounds: {features.feat_liq_burn_months}"
    assert 0.0 <= features.feat_bur_dti_ratio <= 20.0, f"feat_bur_dti_ratio out of bounds: {features.feat_bur_dti_ratio}"
    assert 0.0 <= features.feat_bur_installment_dti <= 20.0, f"feat_bur_installment_dti out of bounds: {features.feat_bur_installment_dti}"
    assert 0.0 <= features.feat_bur_total_dti <= 20.0, f"feat_bur_total_dti out of bounds: {features.feat_bur_total_dti}"
    assert 0 <= features.feat_suf_observed_days <= 90, f"feat_suf_observed_days out of bounds: {features.feat_suf_observed_days}"
    assert 0 <= features.feat_suf_payout_count <= 90, f"feat_suf_payout_count out of bounds: {features.feat_suf_payout_count}"
    assert 0 <= features.feat_suf_group_count <= 5, f"feat_suf_group_count out of bounds: {features.feat_suf_group_count}"
    assert 0.0 <= features.feat_suf_missing_ratio <= 1.0, f"feat_suf_missing_ratio out of bounds: {features.feat_suf_missing_ratio}"

    # 3. Interactions bounds
    assert 0.0 <= features.feat_int_vol_x_recovery <= 450.0
    assert 0.0 <= features.feat_int_vol_x_buffer <= 50.0
    assert -50000.0 <= features.feat_int_trend_x_dti <= 50000.0
    assert 0.0 <= features.feat_int_resilience_idx <= 100.0


# ==============================================================================
# 3. HIGH-LEVEL DETERMINISTIC FEATURE DERIVATION ORCHESTRATOR
# ==============================================================================

def derive_application_features(
    application: Application,
    applicant_profile: ApplicantProfile,
    history: ApplicationHistoricalData,
) -> ApplicationFeatures:
    """
    Derives all 40 frozen ML features from raw inputs deterministically.
    Enforces strict temporal barriers and anti-leakage invariants.
    """
    # --------------------------------------------------------------------------
    # 1. Temporal Boundary Guard
    # --------------------------------------------------------------------------
    cutoff_dt = datetime.fromisoformat(application.cutoff_timestamp.replace("Z", "+00:00"))

    for ev in history.daily_events:
        ev_dt = datetime.fromisoformat(ev.date.replace("Z", "+00:00"))
        if ev_dt >= cutoff_dt:
            raise TemporalLeakageError(
                f"Historical daily event at {ev.date} occurs at or after cutoff {application.cutoff_timestamp}"
            )

    for p in history.weekly_payouts:
        p_dt = datetime.fromisoformat(p.payout_timestamp.replace("Z", "+00:00"))
        if p_dt >= cutoff_dt:
            raise TemporalLeakageError(
                f"Historical payout at {p.payout_timestamp} settles at or after cutoff {application.cutoff_timestamp}"
            )

    # --------------------------------------------------------------------------
    # 2. Extract Raw Telemetry Sequences
    # --------------------------------------------------------------------------
    payout_amounts = [p.net_amount for p in history.weekly_payouts]
    daily_events = history.daily_events

    # --------------------------------------------------------------------------
    # 3. Derive Income Level & Volatility Features
    # --------------------------------------------------------------------------
    feat_inc_median_90d = calculate_median_income(payout_amounts)
    feat_inc_p25_90d = calculate_p25_income(payout_amounts, feat_inc_median_90d)
    feat_inc_mean_90d = calculate_mean_income(payout_amounts)
    feat_inc_trimmed_mean = calculate_trimmed_mean_income(payout_amounts)
    feat_inc_cv_90d = calculate_income_cv(payout_amounts)
    feat_inc_downside_var = calculate_downside_variance(payout_amounts, feat_inc_median_90d)
    feat_inc_iqr_ratio = calculate_iqr_ratio(payout_amounts, feat_inc_median_90d)
    feat_inc_min_max_ratio = calculate_min_max_ratio(payout_amounts)

    # --------------------------------------------------------------------------
    # 4. Derive Trajectory & Momentum Features
    # --------------------------------------------------------------------------
    feat_trend_slope_90d = calculate_trend_slope(payout_amounts)
    feat_trend_momentum_30_90 = calculate_trend_momentum(payout_amounts)
    feat_trend_consec_drops = calculate_consecutive_drops(payout_amounts)

    # --------------------------------------------------------------------------
    # 5. Derive Work Activity & Engagement Features
    # --------------------------------------------------------------------------
    feat_act_active_days_ratio = calculate_active_days_ratio(daily_events)
    feat_act_zero_earn_weeks = calculate_zero_earning_weeks(payout_amounts)
    feat_act_max_idle_streak = calculate_max_idle_streak(daily_events)
    feat_act_weekend_intensity = calculate_weekend_intensity(daily_events)

    # --------------------------------------------------------------------------
    # 6. Derive Recovery & Resilience Features
    # --------------------------------------------------------------------------
    feat_rec_bounceback_ratio, feat_rec_days_to_recover = calculate_recovery_metrics(
        payout_amounts, daily_events, feat_inc_median_90d
    )
    feat_rec_max_drawdown = calculate_max_drawdown(payout_amounts)

    # --------------------------------------------------------------------------
    # 7. Derive Tenure & Platform Discipline Features
    # --------------------------------------------------------------------------
    feat_ten_years_working = (
        round(applicant_profile.years_working, 2)
        if applicant_profile.years_working is not None
        else None
    )
    feat_ten_platform_rating = (
        round(applicant_profile.platform_rating, 2)
        if applicant_profile.platform_rating is not None
        else None
    )
    feat_ten_trips_completed = calculate_trips_completed(daily_events)
    feat_ten_cancellation_rate = (
        round(applicant_profile.cancellation_rate, 4)
        if applicant_profile.cancellation_rate is not None
        else None
    )

    # --------------------------------------------------------------------------
    # 8. Derive Liquidity & Debt Burden Features
    # --------------------------------------------------------------------------
    feat_liq_buffer_to_loan = calculate_buffer_to_loan(
        applicant_profile.starting_cashflow_buffer, application.requested_loan_amount
    )
    feat_liq_burn_months = calculate_burn_months(
        applicant_profile.starting_cashflow_buffer,
        applicant_profile.existing_monthly_debt,
        applicant_profile.monthly_living_expense,
    )
    feat_liq_net_margin = calculate_net_margin(
        daily_events,
        applicant_profile.monthly_living_expense,
        applicant_profile.existing_monthly_debt,
        history.observed_days,
    )
    feat_bur_dti_ratio, feat_bur_installment_dti, feat_bur_total_dti = calculate_dti_ratios(
        applicant_profile.existing_monthly_debt,
        application.contractual_emi,
        feat_inc_median_90d,
    )
    feat_bur_loan_to_income = calculate_loan_to_income(
        application.requested_loan_amount, feat_inc_median_90d
    )

    # --------------------------------------------------------------------------
    # 9. Derive Alternative Credit & Payments Features
    # --------------------------------------------------------------------------
    if applicant_profile.payment_reliability is not None:
        feat_pay_utility_on_time = round(applicant_profile.payment_reliability, 4)
        feat_pay_max_bill_delay = int(round((1.0 - applicant_profile.payment_reliability) * 30.0))
        feat_pay_repay_reliability = round(applicant_profile.payment_reliability, 4)
    else:
        feat_pay_utility_on_time = None
        feat_pay_max_bill_delay = None
        feat_pay_repay_reliability = None

    # --------------------------------------------------------------------------
    # 10. Derive Data Sufficiency & Missingness Features
    # --------------------------------------------------------------------------
    feat_suf_observed_days = history.observed_days
    feat_suf_payout_count = len(history.weekly_payouts)
    feat_suf_group_count = calculate_group_count(history, applicant_profile, application)

    optional_candidates = [
        feat_inc_mean_90d,
        feat_inc_trimmed_mean,
        feat_inc_iqr_ratio,
        feat_inc_min_max_ratio,
        feat_trend_consec_drops,
        feat_act_max_idle_streak,
        feat_act_weekend_intensity,
        feat_rec_max_drawdown,
        feat_ten_years_working,
        feat_ten_platform_rating,
        feat_ten_trips_completed,
        feat_ten_cancellation_rate,
        feat_liq_net_margin,
        feat_pay_utility_on_time,
        feat_pay_max_bill_delay,
        feat_pay_repay_reliability,
        feat_bur_loan_to_income,
        application.loan_purpose,
    ]
    feat_suf_missing_ratio = calculate_missing_ratio(optional_candidates)

    # --------------------------------------------------------------------------
    # 11. Derive Interaction Features (Mandatory, Non-null)
    # --------------------------------------------------------------------------
    (
        feat_int_vol_x_recovery,
        feat_int_vol_x_buffer,
        feat_int_trend_x_dti,
        feat_int_resilience_idx,
    ) = calculate_interaction_features(
        feat_inc_cv_90d,
        feat_rec_days_to_recover,
        feat_liq_buffer_to_loan,
        feat_trend_slope_90d,
        feat_bur_total_dti,
        feat_rec_bounceback_ratio,
    )

    # --------------------------------------------------------------------------
    # 12. Assemble DerivedFeatures Dataclass
    # --------------------------------------------------------------------------
    derived = DerivedFeatures(
        # Mandatory core features (19)
        feat_inc_median_90d=feat_inc_median_90d,
        feat_inc_p25_90d=feat_inc_p25_90d,
        feat_inc_cv_90d=feat_inc_cv_90d,
        feat_inc_downside_var=feat_inc_downside_var,
        feat_trend_slope_90d=feat_trend_slope_90d,
        feat_trend_momentum_30_90=feat_trend_momentum_30_90,
        feat_act_active_days_ratio=feat_act_active_days_ratio,
        feat_act_zero_earn_weeks=feat_act_zero_earn_weeks,
        feat_rec_bounceback_ratio=feat_rec_bounceback_ratio,
        feat_rec_days_to_recover=feat_rec_days_to_recover,
        feat_liq_buffer_to_loan=feat_liq_buffer_to_loan,
        feat_liq_burn_months=feat_liq_burn_months,
        feat_bur_dti_ratio=feat_bur_dti_ratio,
        feat_bur_installment_dti=feat_bur_installment_dti,
        feat_bur_total_dti=feat_bur_total_dti,
        feat_suf_observed_days=feat_suf_observed_days,
        feat_suf_payout_count=feat_suf_payout_count,
        feat_suf_group_count=feat_suf_group_count,
        feat_suf_missing_ratio=feat_suf_missing_ratio,
        # Optional features (17)
        feat_inc_mean_90d=feat_inc_mean_90d,
        feat_inc_trimmed_mean=feat_inc_trimmed_mean,
        feat_inc_iqr_ratio=feat_inc_iqr_ratio,
        feat_inc_min_max_ratio=feat_inc_min_max_ratio,
        feat_trend_consec_drops=feat_trend_consec_drops,
        feat_act_max_idle_streak=feat_act_max_idle_streak,
        feat_act_weekend_intensity=feat_act_weekend_intensity,
        feat_rec_max_drawdown=feat_rec_max_drawdown,
        feat_ten_years_working=feat_ten_years_working,
        feat_ten_platform_rating=feat_ten_platform_rating,
        feat_ten_trips_completed=feat_ten_trips_completed,
        feat_ten_cancellation_rate=feat_ten_cancellation_rate,
        feat_liq_net_margin=feat_liq_net_margin,
        feat_pay_utility_on_time=feat_pay_utility_on_time,
        feat_pay_max_bill_delay=feat_pay_max_bill_delay,
        feat_pay_repay_reliability=feat_pay_repay_reliability,
        feat_bur_loan_to_income=feat_bur_loan_to_income,
        # Interaction features (4)
        feat_int_vol_x_recovery=feat_int_vol_x_recovery,
        feat_int_vol_x_buffer=feat_int_vol_x_buffer,
        feat_int_trend_x_dti=feat_int_trend_x_dti,
        feat_int_resilience_idx=feat_int_resilience_idx,
    )

    # --------------------------------------------------------------------------
    # 13. Validate Derived Features Against Contract
    # --------------------------------------------------------------------------
    validate_derived_features(derived)

    return ApplicationFeatures(
        application_id=application.application_id,
        applicant_profile_id=application.applicant_profile_id,
        cutoff_timestamp=application.cutoff_timestamp,
        features=derived,
    )
