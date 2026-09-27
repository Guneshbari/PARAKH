"""Feature engineering pipeline contract and implementations for PARAKH.

Defines the boundary between raw/persisted FinancialSignal records, structured
runtime telemetry (telemetry_series), and the AssessmentEngine.
"""
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.assessment.schemas import _check_for_prohibited_keys
from src.data.synthetic.schemas import DailyActivityEvent
from src.ml.features.feature_derivation import (
    calculate_active_days_ratio,
    calculate_buffer_to_loan,
    calculate_burn_months,
    calculate_consecutive_drops,
    calculate_downside_variance,
    calculate_dti_ratios,
    calculate_income_cv,
    calculate_interaction_features,
    calculate_iqr_ratio,
    calculate_loan_to_income,
    calculate_max_drawdown,
    calculate_max_idle_streak,
    calculate_mean_income,
    calculate_median_income,
    calculate_min_max_ratio,
    calculate_missing_ratio,
    calculate_net_margin,
    calculate_p25_income,
    calculate_recovery_metrics,
    calculate_trend_momentum,
    calculate_trend_slope,
    calculate_trimmed_mean_income,
    calculate_trips_completed,
    calculate_weekend_intensity,
    calculate_zero_earning_weeks,
)

logger = logging.getLogger(__name__)


def _to_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Helper to safely convert numeric/Decimal/string to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_datetime(val: Any) -> Optional[datetime]:
    """Parse string/date/datetime into timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _parse_date(val: Any) -> Optional[date]:
    """Parse string/date/datetime into calendar date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(val)
            except ValueError:
                return None

def calculate_application_recovery_cycles(
    valid_payouts: List[Dict[str, Any]],
    valid_shifts: List[Dict[str, Any]],
    median_val: float,
) -> Tuple[int, int, Optional[float]]:
    """Calculate application-specific cyclical low-income dip events and successful recovery cycles.

    Evaluates observed cashflow chronologically (from earliest to latest).
    A cyclical low-income dip occurs when payout drops below 85% of median baseline.
    A recovery cycle is successful when cashflow returns to >= 85% baseline within 14 days (1-2 cycles).
    If weekly payouts exhibit zero dips, evaluates chronological daily activity shifts.
    If no dips were encountered across the observation window, returns (0, 0, None).

    Returns:
        Tuple of (dips_encountered, recoveries_completed, recovery_rate_after_low_income).
    """
    dips_encountered = 0
    recoveries_completed = 0

    # 1. Weekly payout trough check (chronologically sorted)
    if valid_payouts and median_val > 0.0:
        payouts_chrono = sorted(
            valid_payouts,
            key=lambda p: _parse_datetime(p.get("payout_timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        )
        payout_amounts_chrono = [float(p.get("net_amount", 0.0)) for p in payouts_chrono]
        threshold = 0.85 * median_val
        n = len(payout_amounts_chrono)
        i = 0
        while i < n:
            if payout_amounts_chrono[i] < threshold:
                dips_encountered += 1
                recovered = False
                lookahead = min(n, i + 3)
                for j in range(i + 1, lookahead):
                    if payout_amounts_chrono[j] >= threshold:
                        recovered = True
                        break
                if recovered:
                    recoveries_completed += 1
                # Advance past consecutive low cycles belonging to this same dip episode
                while i + 1 < n and payout_amounts_chrono[i + 1] < threshold:
                    i += 1
            i += 1

    # 2. Daily shift trough check if weekly payouts showed zero dips
    if dips_encountered == 0 and valid_shifts:
        shifts_chrono = sorted(
            valid_shifts,
            key=lambda s: _parse_date(s.get("date")) or date.min,
        )
        active_shifts = [s for s in shifts_chrono if not s.get("is_unobserved", False)]
        daily_earnings = [float(s.get("net_earnings", 0.0)) for s in active_shifts]
        if daily_earnings:
            daily_median = sorted(daily_earnings)[len(daily_earnings) // 2]
            if daily_median > 0.0:
                daily_threshold = 0.85 * daily_median
                n_days = len(daily_earnings)
                d = 0
                while d < n_days:
                    if daily_earnings[d] < daily_threshold:
                        dips_encountered += 1
                        recovered = False
                        lookahead = min(n_days, d + 15)  # within 14 days
                        for dj in range(d + 1, lookahead):
                            if daily_earnings[dj] >= daily_threshold:
                                recovered = True
                                break
                        if recovered:
                            recoveries_completed += 1
                        while d + 1 < n_days and daily_earnings[d + 1] < daily_threshold:
                            d += 1
                    d += 1

    if dips_encountered == 0:
        return 0, 0, None

    recovery_rate = round(recoveries_completed / dips_encountered, 4)
    return dips_encountered, recoveries_completed, recovery_rate


class FeaturePipeline(ABC):
    """Abstract interface for PARAKH's feature engineering pipeline.

    Framework-independent contract transforming raw/persisted FinancialSignal records
    and application context into an engine-consumable feature set.
    """

    @abstractmethod
    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
        cutoff_timestamp: Optional[Union[datetime, str]] = None,
    ) -> Dict[str, Any]:
        """Extract and compute sanitized features for credit assessment.

        Args:
            signals: Sequence of FinancialSignal domain records or dictionaries.
            application: Optional Application domain model or dictionary.
            applicant_profile: Optional ApplicantProfile domain model or dictionary.
            cutoff_timestamp: Optional cutoff timestamp; events at or after this time are excluded.

        Returns:
            Dict[str, Any]: Key-value feature set passed into AssessmentInput.derived_features.
        """
        pass


class PassthroughFeaturePipeline(FeaturePipeline):
    """Legacy fallback feature pipeline retained for backwards compatibility and test suites.

    Preserves existing non-sensitive signal_metadata without feature derivation.
    Active runtime credit assessments use TelemetryFeaturePipeline.
    """

    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
        cutoff_timestamp: Optional[Union[datetime, str]] = None,
    ) -> Dict[str, Any]:
        """Extract features by propagating existing non-sensitive signal_metadata."""
        features: Dict[str, Any] = {}
        if signals:
            latest = signals[-1] if isinstance(signals, (list, tuple)) else signals
            if isinstance(latest, dict):
                meta = latest.get("signal_metadata")
            else:
                meta = getattr(latest, "signal_metadata", None)

            if isinstance(meta, dict):
                _check_for_prohibited_keys(meta)
                features.update(meta)

        return features


class TelemetryFeaturePipeline(FeaturePipeline):
    """Authoritative runtime feature derivation pipeline for PARAKH.

    Replaces passive passthrough with deterministic mathematical derivation from structured
    runtime telemetry (telemetry_series). Reuses the authoritative training feature functions
    to guarantee zero train/serve feature calculation skew. Enforces strict temporal barriers
    preventing future information leakage.
    """

    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
        cutoff_timestamp: Optional[Union[datetime, str]] = None,
    ) -> Dict[str, Any]:
        """Extract and derive model features from runtime telemetry.

        If telemetry_series is present, derives the full base feature contract.
        If telemetry_series is absent, falls back gracefully to non-sensitive signal_metadata
        without fabricating data sufficiency metrics (preserving Phase 13A-2 sufficiency gate).
        """
        if not signals:
            return {}

        latest = signals[-1] if isinstance(signals, (list, tuple)) else signals

        # 1. Check for structured telemetry_series
        telemetry_raw = getattr(latest, "telemetry_series", None)
        if telemetry_raw is None and isinstance(latest, dict):
            telemetry_raw = latest.get("telemetry_series")

        # Backward compatibility: check inside signal_metadata
        if telemetry_raw is None:
            meta = getattr(latest, "signal_metadata", None) or (
                latest.get("signal_metadata") if isinstance(latest, dict) else None
            )
            if isinstance(meta, dict) and "telemetry_series" in meta:
                telemetry_raw = meta.get("telemetry_series")

        # Fall back to metadata passthrough if no telemetry series provided
        if not telemetry_raw:
            return self._fallback_passthrough(latest)

        # 2. Extract telemetry components
        if hasattr(telemetry_raw, "model_dump"):
            telemetry_dict = telemetry_raw.model_dump()
        elif hasattr(telemetry_raw, "__dict__"):
            telemetry_dict = vars(telemetry_raw)
        elif isinstance(telemetry_raw, dict):
            telemetry_dict = telemetry_raw
        else:
            return self._fallback_passthrough(latest)

        weekly_payouts_raw = telemetry_dict.get("weekly_payouts") or []
        daily_activity_raw = telemetry_dict.get("daily_activity") or []
        explicit_observed_days = telemetry_dict.get("observed_days")
        active_signal_groups = telemetry_dict.get("active_signal_groups")

        # 3. Determine assessment cutoff timestamp (Anti-leakage barrier)
        cutoff_dt = _parse_datetime(cutoff_timestamp)
        if cutoff_dt is None and application is not None:
            created_at = getattr(application, "created_at", None) or (
                application.get("created_at") if isinstance(application, dict) else None
            )
            cutoff_dt = _parse_datetime(created_at)

        if cutoff_dt is None:
            cutoff_dt = datetime.now(timezone.utc)

        cutoff_date = cutoff_dt.date()

        # 4. Filter events strictly before cutoff
        valid_payouts: List[Dict[str, Any]] = []
        payout_dates: List[date] = []
        for p in weekly_payouts_raw:
            p_dict = p if isinstance(p, dict) else (vars(p) if hasattr(p, "__dict__") else {})
            ts_raw = p_dict.get("payout_timestamp")
            ts_dt = _parse_datetime(ts_raw)
            if ts_dt is None:
                continue
            # Temporal guard: exclude events at or after cutoff
            if ts_dt < cutoff_dt:
                valid_payouts.append(p_dict)
                payout_dates.append(ts_dt.date())

        valid_shifts: List[Dict[str, Any]] = []
        shift_dates: List[date] = []
        for s in daily_activity_raw:
            s_dict = s if isinstance(s, dict) else (vars(s) if hasattr(s, "__dict__") else {})
            d_raw = s_dict.get("date")
            s_date = _parse_date(d_raw)
            if s_date is None:
                continue
            # Temporal guard: exclude shifts at or after cutoff
            if s_date < cutoff_date:
                valid_shifts.append(s_dict)
                shift_dates.append(s_date)

        # 5. Determine temporal depth (observed_days)
        if explicit_observed_days is not None:
            observed_days = int(explicit_observed_days)
        else:
            all_dates = payout_dates + shift_dates
            if all_dates:
                earliest_date = min(all_dates)
                observed_days = max(0, min(90, (cutoff_date - earliest_date).days))
            else:
                observed_days = 0

        payout_count = len(valid_payouts)

        # 6. Extract raw payout amounts & construct activity events
        payout_amounts: List[float] = [
            float(p.get("net_amount", 0.0)) for p in valid_payouts
        ]

        app_id_str = str(
            getattr(application, "id", None)
            or (application.get("id") if isinstance(application, dict) else "runtime_app")
        )

        daily_events: List[DailyActivityEvent] = []
        for idx, s in enumerate(valid_shifts):
            s_date_obj = _parse_date(s.get("date")) or cutoff_date
            is_wknd = s.get("is_weekend")
            if is_wknd is None:
                is_wknd = s_date_obj.weekday() >= 5

            day_off = (s_date_obj - cutoff_date).days
            ev = DailyActivityEvent(
                application_id=app_id_str,
                date=s_date_obj.isoformat(),
                day_offset=day_off,
                is_active=bool(s.get("is_active", True)),
                hours_worked=float(s.get("hours_worked", 0.0)),
                is_weekend=bool(is_wknd),
                gross_earnings=float(s.get("gross_earnings", s.get("net_earnings", 0.0))),
                platform_fee=float(s.get("platform_fee", 0.0)),
                net_earnings=float(s.get("net_earnings", 0.0)),
                is_unobserved=bool(s.get("is_unobserved", False)),
            )
            daily_events.append(ev)

        # 7. Extract profile, application, and scalar signal context
        def _get_field(obj: Any, name: str, default: Any = None) -> Any:
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        req_loan_amount = _to_float(
            _get_field(application, "requested_loan_amount"), default=25000.0
        )
        tenure_months = _to_float(
            _get_field(application, "preferred_repayment_period")
            or _get_field(application, "loan_tenure_months"),
            default=12.0,
        )
        contractual_emi = req_loan_amount / max(1.0, tenure_months)

        existing_debt = _to_float(
            _get_field(latest, "existing_obligation")
            or _get_field(applicant_profile, "existing_monthly_debt"),
            default=0.0,
        )
        cashflow_buffer = _to_float(
            _get_field(latest, "cashflow_buffer")
            or _get_field(applicant_profile, "starting_cashflow_buffer"),
            default=0.0,
        )
        living_cost = _to_float(
            _get_field(applicant_profile, "monthly_living_expense"),
            default=12000.0,
        )
        years_working = _to_float(
            _get_field(applicant_profile, "years_working"),
            default=0.0,
        )
        platform_rating = _to_float(
            _get_field(latest, "platform_rating")
            or _get_field(applicant_profile, "platform_rating"),
            default=None,
        )
        cancellation_rate = _to_float(
            _get_field(applicant_profile, "cancellation_rate"),
            default=None,
        )
        payment_reliability = _to_float(
            _get_field(latest, "repayment_reliability")
            or _get_field(applicant_profile, "payment_reliability"),
            default=None,
        )
        payment_regularity = _to_float(
            _get_field(latest, "payment_regularity"),
            default=payment_reliability,
        )

        # 8. Derive Income Level & Volatility Features
        if payout_amounts:
            feat_inc_median_90d = calculate_median_income(payout_amounts)
            feat_inc_p25_90d = calculate_p25_income(payout_amounts, feat_inc_median_90d)
            feat_inc_mean_90d = calculate_mean_income(payout_amounts)
            feat_inc_trimmed_mean = calculate_trimmed_mean_income(payout_amounts)
            feat_inc_cv_90d = calculate_income_cv(payout_amounts)
            feat_inc_downside_var = calculate_downside_variance(payout_amounts, feat_inc_median_90d)
            feat_inc_iqr_ratio = calculate_iqr_ratio(payout_amounts, feat_inc_median_90d)
            feat_inc_min_max_ratio = calculate_min_max_ratio(payout_amounts)
        else:
            # Fall back to scalar signal if payouts empty
            scalar_med = _to_float(_get_field(latest, "median_income"), 0.0)
            feat_inc_median_90d = scalar_med
            feat_inc_p25_90d = scalar_med * 0.85
            feat_inc_mean_90d = _to_float(_get_field(latest, "average_income"), scalar_med)
            feat_inc_trimmed_mean = scalar_med
            feat_inc_cv_90d = _to_float(_get_field(latest, "income_volatility"), 0.0)
            feat_inc_downside_var = (scalar_med * 0.20) ** 2
            feat_inc_iqr_ratio = 0.35
            feat_inc_min_max_ratio = 0.50

        # 9. Derive Trajectory & Momentum Features
        if len(payout_amounts) >= 2:
            feat_trend_slope_90d = calculate_trend_slope(payout_amounts)
            feat_trend_momentum_30_90 = calculate_trend_momentum(payout_amounts)
            feat_trend_consec_drops = float(calculate_consecutive_drops(payout_amounts))
        else:
            feat_trend_slope_90d = 0.0
            feat_trend_momentum_30_90 = 1.0
            feat_trend_consec_drops = 0.0

        # 10. Derive Work Activity & Consistency Features
        if daily_events:
            feat_act_active_days_ratio = calculate_active_days_ratio(daily_events)
            feat_act_max_idle_streak = float(calculate_max_idle_streak(daily_events))
            feat_act_weekend_intensity = calculate_weekend_intensity(daily_events)
            feat_ten_trips_completed = float(calculate_trips_completed(daily_events))
            feat_liq_net_margin = calculate_net_margin(
                daily_events, living_cost, existing_debt, observed_days
            )
        else:
            active_days_count = _to_float(_get_field(latest, "active_days"), None)
            feat_act_active_days_ratio = (
                min(1.0, max(0.0, active_days_count / 90.0))
                if active_days_count is not None
                else 0.0
            )
            feat_act_max_idle_streak = 5.0
            feat_act_weekend_intensity = 0.30
            feat_ten_trips_completed = 500.0
            feat_liq_net_margin = 0.15

        feat_act_zero_earn_weeks = float(calculate_zero_earning_weeks(payout_amounts))

        # 11. Derive Recovery & Resilience Features
        feat_rec_bounceback_ratio, feat_rec_days_to_recover = calculate_recovery_metrics(
            payout_amounts, daily_events, feat_inc_median_90d
        )
        feat_rec_max_drawdown = calculate_max_drawdown(payout_amounts)

        dips_count, recs_count, rec_rate = calculate_application_recovery_cycles(
            valid_payouts, valid_shifts, feat_inc_median_90d
        )

        # 12. Derive Platform Standing & Tenure Features
        feat_ten_years_working = years_working
        feat_ten_platform_rating = platform_rating if platform_rating is not None else 4.50
        feat_ten_cancellation_rate = cancellation_rate if cancellation_rate is not None else 0.03

        # 13. Derive Liquidity & Debt Burden Features
        feat_liq_buffer_to_loan = calculate_buffer_to_loan(cashflow_buffer, req_loan_amount)
        feat_liq_burn_months = calculate_burn_months(cashflow_buffer, existing_debt, living_cost)
        feat_bur_dti_ratio, feat_bur_installment_dti, feat_bur_total_dti = calculate_dti_ratios(
            existing_debt, contractual_emi, feat_inc_median_90d
        )
        # Authoritative formula: loan divided by annualized median income (median * 52)
        feat_bur_loan_to_income = calculate_loan_to_income(req_loan_amount, feat_inc_median_90d)

        # 14. Derive Payment Discipline Features
        if payment_regularity is not None:
            feat_pay_utility_on_time = payment_regularity
            feat_pay_max_bill_delay = float(int(round((1.0 - payment_regularity) * 30.0)))
            feat_pay_repay_reliability = payment_reliability or payment_regularity
        elif payment_reliability is not None:
            feat_pay_utility_on_time = payment_reliability
            feat_pay_max_bill_delay = float(int(round((1.0 - payment_reliability) * 30.0)))
            feat_pay_repay_reliability = payment_reliability
        else:
            feat_pay_utility_on_time = 0.90
            feat_pay_max_bill_delay = 3.0
            feat_pay_repay_reliability = 0.95

        # 15. Derive Core Signal Group Count & Sufficiency Metrics
        group_count = self._derive_group_count(
            observed_days=observed_days,
            payout_count=payout_count,
            daily_events=daily_events,
            cashflow_buffer=cashflow_buffer,
            payment_reliability=payment_reliability,
            existing_debt=existing_debt,
            contractual_emi=contractual_emi,
            active_signal_groups=active_signal_groups,
        )

        feat_suf_observed_days = float(observed_days)
        feat_suf_payout_count = float(payout_count)
        feat_suf_group_count = float(group_count)

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
        ]
        feat_suf_missing_ratio = calculate_missing_ratio(optional_candidates)

        # 16. Derive Contract Interaction Terms (Authoritative Formulas)
        int_rec, int_buf, int_trend, int_res = calculate_interaction_features(
            cv=feat_inc_cv_90d,
            recovery_days=feat_rec_days_to_recover,
            buffer_to_loan=feat_liq_buffer_to_loan,
            slope=feat_trend_slope_90d,
            total_dti=feat_bur_total_dti,
            bounceback=feat_rec_bounceback_ratio,
        )

        derived_features: Dict[str, Any] = {
            # 19 core derived features
            "feat_inc_median_90d": feat_inc_median_90d,
            "feat_inc_p25_90d": feat_inc_p25_90d,
            "feat_inc_cv_90d": feat_inc_cv_90d,
            "feat_inc_downside_var": feat_inc_downside_var,
            "feat_trend_slope_90d": feat_trend_slope_90d,
            "feat_trend_momentum_30_90": feat_trend_momentum_30_90,
            "feat_act_active_days_ratio": feat_act_active_days_ratio,
            "feat_act_zero_earn_weeks": feat_act_zero_earn_weeks,
            "feat_rec_bounceback_ratio": feat_rec_bounceback_ratio,
            "feat_rec_days_to_recover": feat_rec_days_to_recover,
            "feat_liq_buffer_to_loan": feat_liq_buffer_to_loan,
            "feat_liq_burn_months": feat_liq_burn_months,
            "feat_bur_dti_ratio": feat_bur_dti_ratio,
            "feat_bur_installment_dti": feat_bur_installment_dti,
            "feat_bur_total_dti": feat_bur_total_dti,
            "feat_suf_observed_days": feat_suf_observed_days,
            "feat_suf_payout_count": feat_suf_payout_count,
            "feat_suf_group_count": feat_suf_group_count,
            "feat_suf_missing_ratio": feat_suf_missing_ratio,
            # 21 optional derived features
            "feat_inc_mean_90d": feat_inc_mean_90d,
            "feat_inc_trimmed_mean": feat_inc_trimmed_mean,
            "feat_inc_iqr_ratio": feat_inc_iqr_ratio,
            "feat_inc_min_max_ratio": feat_inc_min_max_ratio,
            "feat_trend_consec_drops": feat_trend_consec_drops,
            "feat_act_max_idle_streak": feat_act_max_idle_streak,
            "feat_act_weekend_intensity": feat_act_weekend_intensity,
            "feat_rec_max_drawdown": feat_rec_max_drawdown,
            "feat_ten_years_working": feat_ten_years_working,
            "feat_ten_platform_rating": feat_ten_platform_rating,
            "feat_ten_trips_completed": feat_ten_trips_completed,
            "feat_ten_cancellation_rate": feat_ten_cancellation_rate,
            "feat_liq_net_margin": feat_liq_net_margin,
            "feat_pay_utility_on_time": feat_pay_utility_on_time,
            "feat_pay_max_bill_delay": feat_pay_max_bill_delay,
            "feat_pay_repay_reliability": feat_pay_repay_reliability,
            "feat_bur_loan_to_income": feat_bur_loan_to_income,
            "feat_int_vol_x_recovery": int_rec,
            "feat_int_vol_x_buffer": int_buf,
            "feat_int_trend_x_dti": int_trend,
            "feat_int_resilience_idx": int_res,
            # Application-specific rebound & recovery metrics (Phase 17)
            "recovery_rate_after_low_income": rec_rate,
            "low_income_periods_encountered": dips_count,
            "successful_recovery_cycles": recs_count,
        }

        # 17. Merge non-colliding non-prohibited fields from signal_metadata
        meta = getattr(latest, "signal_metadata", None) or (
            latest.get("signal_metadata") if isinstance(latest, dict) else None
        )
        if isinstance(meta, dict):
            _check_for_prohibited_keys(meta)
            for k, v in meta.items():
                if k not in derived_features and k != "telemetry_series":
                    derived_features[k] = v

        return derived_features

    def _derive_group_count(
        self,
        observed_days: int,
        payout_count: int,
        daily_events: List[DailyActivityEvent],
        cashflow_buffer: float,
        payment_reliability: Optional[float],
        existing_debt: float,
        contractual_emi: float,
        active_signal_groups: Optional[List[str]] = None,
    ) -> int:
        """Derive distinct core alternative signal categories established at cutoff."""
        if active_signal_groups is not None:
            return max(0, min(len(active_signal_groups), 5))

        if observed_days < 30:
            return 1

        has_gig_income = observed_days >= 30 and payout_count >= 4
        active_days_count = sum(
            1 for ev in daily_events if ev.is_active and not ev.is_unobserved
        )
        has_work_activity = observed_days >= 30 and (
            active_days_count >= 10 if daily_events else True
        )
        has_cashflow_buffer = cashflow_buffer is not None and cashflow_buffer > 0.0
        has_payment_discipline = payment_reliability is not None
        has_financial_obligations = existing_debt is not None and contractual_emi is not None

        count = sum([
            has_gig_income,
            has_work_activity,
            has_cashflow_buffer,
            has_payment_discipline,
            has_financial_obligations,
        ])
        return min(max(count, 0), 5)

    def _fallback_passthrough(self, latest: Any) -> Dict[str, Any]:
        """Fallback to metadata passthrough when telemetry_series is missing."""
        features: Dict[str, Any] = {}
        if isinstance(latest, dict):
            meta = latest.get("signal_metadata")
        else:
            meta = getattr(latest, "signal_metadata", None)

        if isinstance(meta, dict):
            _check_for_prohibited_keys(meta)
            features.update(meta)

        return features
