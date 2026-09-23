"""
PARAKH Synthetic Data Generator - 90-Day Historical Time-Series Generator
Simulates the raw daily shifts and weekly payout settlement events occurring
strictly within the trailing observation window [t0 - 90d, t0).

Guarantees:
- Zero temporal leakage: all events satisfy t0 - 90d <= event_time < t0
- Distinct cohort behavioral dynamics (Healthy Volatile, Stable, Declining, Irregular, High Obligation, Insufficient Data)
- Deterministic, application-level isolated random substreams
- Preservation of 0 != missing != null semantics
"""

from datetime import datetime, timezone, timedelta
import hashlib
import math
import random
from typing import Dict, List, Optional, Tuple

from src.data.synthetic.applicant_generator import generate_deterministic_uuid
from src.data.synthetic.config import (
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    MASTER_SEED,
    OBSERVATION_WINDOW_DAYS,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ApplicationHistoricalData,
    DailyActivityEvent,
    HistoricalTelemetry,
    WeeklyPayoutEvent,
)


def get_application_rng(master_seed: int, application_id: str) -> random.Random:
    """
    Derives an independent, deterministic PRNG instance for a specific application.
    Eliminates cross-application RNG coupling and ensures bit-for-bit reproducibility.
    """
    payload = f"{master_seed}:telemetry:{application_id}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    app_seed = (int(digest[:8], 16) % 2147483647) + 1
    return random.Random(app_seed)


def format_utc_iso(dt: datetime) -> str:
    """Format datetime as UTC ISO-8601 string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_application_history(
    application: Application,
    applicant_profile: ApplicantProfile,
    master_seed: int = MASTER_SEED,
) -> ApplicationHistoricalData:
    """
    Generates the complete 90-day raw event history for an application strictly before t0.
    """
    rng = get_application_rng(master_seed, application.application_id)
    cutoff_dt = datetime.fromisoformat(application.cutoff_timestamp.replace("Z", "+00:00"))
    history_start_dt = cutoff_dt - timedelta(days=OBSERVATION_WINDOW_DAYS)

    cohort = applicant_profile.cohort_archetype
    baseline_weekly = applicant_profile.baseline_weekly_income
    typical_active_days = max(1, applicant_profile.average_working_days // 4)
    baseline_daily_net = baseline_weekly / float(typical_active_days)

    # --------------------------------------------------------------------------
    # 1. Determine Observed Days Window
    # --------------------------------------------------------------------------
    if cohort == COHORT_INSUFFICIENT_DATA:
        # Thin-file new entrant: only onboarded 5 to 25 days before t0
        observed_days = rng.randint(5, 25)
    else:
        observed_days = OBSERVATION_WINDOW_DAYS  # Full 90 days

    unobserved_count = OBSERVATION_WINDOW_DAYS - observed_days

    # --------------------------------------------------------------------------
    # 2. Cohort-Specific Behavior Configuration
    # --------------------------------------------------------------------------
    # Healthy Volatile: acute dip setup (5-8 days dip around day 30-45)
    dip_start_day = rng.randint(25, 42) if cohort == COHORT_HEALTHY_VOLATILE else -1
    dip_duration = rng.randint(5, 8)
    recovery_duration = rng.randint(4, 7)
    dip_end_day = dip_start_day + dip_duration
    recovery_end_day = dip_end_day + recovery_duration

    # Irregular: idle streak setup
    idle_streak_1_start = rng.randint(15, 30) if cohort == COHORT_IRREGULAR else -1
    idle_streak_1_len = rng.randint(7, 12)
    idle_streak_2_start = rng.randint(50, 65) if cohort == COHORT_IRREGULAR else -1
    idle_streak_2_len = rng.randint(8, 14)

    # --------------------------------------------------------------------------
    # 3. Simulate 90 Daily Shifts (Day 0 = t0 - 90d, Day 89 = t0 - 1d)
    # --------------------------------------------------------------------------
    daily_events: List[DailyActivityEvent] = []

    for day_idx in range(OBSERVATION_WINDOW_DAYS):
        day_offset = day_idx - OBSERVATION_WINDOW_DAYS  # -90 to -1
        # Shift start at 8 hours into the daily observation slice
        event_dt = history_start_dt + timedelta(days=day_idx, hours=8)
        is_weekend = event_dt.date().weekday() >= 5  # Saturday (5) or Sunday (6)

        # Check if day is prior to platform onboarding (Insufficient Data)
        if day_idx < unobserved_count:
            daily_events.append(
                DailyActivityEvent(
                    application_id=application.application_id,
                    date=format_utc_iso(event_dt),
                    day_offset=day_offset,
                    is_active=False,
                    hours_worked=0.0,
                    is_weekend=is_weekend,
                    gross_earnings=0.0,
                    platform_fee=0.0,
                    net_earnings=0.0,
                    is_unobserved=True,
                )
            )
            continue

        # Determine daily active status and earning potential based on cohort
        is_active = False
        target_net = 0.0

        if cohort == COHORT_HEALTHY_VOLATILE:
            # High active probability with weekend surges and acute temporary dip
            in_trough = dip_start_day <= day_idx < dip_end_day
            in_recovery = dip_end_day <= day_idx < recovery_end_day

            if in_trough:
                # Acute illness/repair: low activity, severe earning dip (20-35% baseline)
                is_active = rng.random() < 0.35
                target_net = baseline_daily_net * rng.uniform(0.20, 0.35) if is_active else 0.0
            elif in_recovery:
                # Rapid bounceback: ramping back up to baseline
                ramp = (day_idx - dip_end_day + 1) / float(recovery_duration)
                is_active = rng.random() < 0.85
                target_net = baseline_daily_net * (0.40 + 0.60 * ramp) if is_active else 0.0
            else:
                # Normal volatile operation: high variance, weekend surges
                prob_active = 0.90 if is_weekend else 0.80
                is_active = rng.random() < prob_active
                if is_active:
                    multiplier = rng.uniform(1.25, 1.45) if is_weekend else rng.uniform(0.70, 1.35)
                    # Occasional holiday surge spike (+35-50%)
                    if rng.random() < 0.08:
                        multiplier *= 1.35
                    target_net = baseline_daily_net * multiplier

        elif cohort == COHORT_STABLE:
            # Steady active commitment, low variance around baseline
            prob_active = 0.90 if is_weekend else 0.85
            is_active = rng.random() < prob_active
            if is_active:
                multiplier = rng.uniform(0.92, 1.08)
                target_net = baseline_daily_net * multiplier

        elif cohort == COHORT_DECLINING:
            # Structural deterioration: active rate and earnings drift downwards
            rel_progress = float(day_idx) / 89.0  # 0.0 -> 1.0
            trajectory = max(0.55, 1.0 - 0.40 * rel_progress)  # 1.0 -> 0.60
            prob_active = max(0.40, 0.80 - 0.35 * rel_progress)
            is_active = rng.random() < prob_active
            if is_active:
                multiplier = rng.uniform(0.85, 1.15) * trajectory
                target_net = baseline_daily_net * multiplier

        elif cohort == COHORT_IRREGULAR:
            # Intermittent, sparse active days with long idle gaps
            in_idle_streak = (
                (idle_streak_1_start <= day_idx < idle_streak_1_start + idle_streak_1_len)
                or (idle_streak_2_start <= day_idx < idle_streak_2_start + idle_streak_2_len)
            )
            if in_idle_streak:
                is_active = False
                target_net = 0.0
            else:
                is_active = rng.random() < 0.40
                if is_active:
                    multiplier = rng.uniform(0.60, 1.50)
                    target_net = baseline_daily_net * multiplier

        elif cohort == COHORT_HIGH_OBLIGATION:
            # Driven to work high hours due to debt burden, steady earnings
            prob_active = 0.90 if is_weekend else 0.85
            is_active = rng.random() < prob_active
            if is_active:
                multiplier = rng.uniform(0.90, 1.15)
                target_net = baseline_daily_net * multiplier

        else:  # COHORT_INSUFFICIENT_DATA (Observed portion)
            prob_active = 0.80
            is_active = rng.random() < prob_active
            if is_active:
                multiplier = rng.uniform(0.80, 1.20)
                target_net = baseline_daily_net * multiplier

        # Compute hours and gross/net amounts
        if is_active and target_net > 0.0:
            hours_worked = round(min(max(rng.gauss(8.5, 1.5), 3.0), 14.0), 1)
            net_earnings = round(target_net, 2)
            commission_rate = rng.uniform(0.18, 0.22)
            platform_fee = round(net_earnings * commission_rate / (1.0 - commission_rate), 2)
            gross_earnings = round(net_earnings + platform_fee, 2)
        else:
            is_active = False
            hours_worked = 0.0
            net_earnings = 0.0
            platform_fee = 0.0
            gross_earnings = 0.0

        daily_events.append(
            DailyActivityEvent(
                application_id=application.application_id,
                date=format_utc_iso(event_dt),
                day_offset=day_offset,
                is_active=is_active,
                hours_worked=hours_worked,
                is_weekend=is_weekend,
                gross_earnings=gross_earnings,
                platform_fee=platform_fee,
                net_earnings=net_earnings,
                is_unobserved=False,
            )
        )

    # --------------------------------------------------------------------------
    # 4. Aggregate Daily Events into Weekly Settlement Payouts (Cycles 1 to 13)
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # 4. Aggregate Daily Events into Weekly Settlement Payouts
    # --------------------------------------------------------------------------
    weekly_payouts: List[WeeklyPayoutEvent] = []

    if cohort == COHORT_INSUFFICIENT_DATA:
        # Insufficient Data: 1 to 3 completed weekly settlement cycles
        target_payout_count = rng.randint(1, min(3, max(1, observed_days // 7)))
        if target_payout_count == 1:
            start_idx = max(unobserved_count, OBSERVATION_WINDOW_DAYS - 7)
            chunks = [daily_events[start_idx:OBSERVATION_WINDOW_DAYS]]
        elif target_payout_count == 2:
            chunks = [
                daily_events[OBSERVATION_WINDOW_DAYS - 14 : OBSERVATION_WINDOW_DAYS - 7],
                daily_events[OBSERVATION_WINDOW_DAYS - 7 : OBSERVATION_WINDOW_DAYS],
            ]
        else:
            chunks = [
                daily_events[OBSERVATION_WINDOW_DAYS - 21 : OBSERVATION_WINDOW_DAYS - 14],
                daily_events[OBSERVATION_WINDOW_DAYS - 14 : OBSERVATION_WINDOW_DAYS - 7],
                daily_events[OBSERVATION_WINDOW_DAYS - 7 : OBSERVATION_WINDOW_DAYS],
            ]
    else:
        # Standard cohorts: 13 weekly cycles (12 x 7-day + 1 x 6-day)
        cycle_length = 7
        chunks = []
        for start_idx in range(0, OBSERVATION_WINDOW_DAYS, cycle_length):
            end_idx = min(start_idx + cycle_length, OBSERVATION_WINDOW_DAYS)
            chunks.append(daily_events[start_idx:end_idx])

    for cycle_index, chunk in enumerate(chunks, start=1):
        payout_id = generate_deterministic_uuid(rng)
        period_start = chunk[0].date
        period_end = chunk[-1].date

        # Payout timestamp: settled 4 hours after the last shift of the cycle
        last_shift_dt = datetime.fromisoformat(chunk[-1].date.replace("Z", "+00:00"))
        settlement_dt = last_shift_dt + timedelta(hours=4)

        # Invariant check: payout must be strictly before cutoff timestamp t0
        assert settlement_dt < cutoff_dt, (
            f"Payout timestamp {settlement_dt} must be strictly prior to cutoff {cutoff_dt}"
        )

        gross_sum = round(sum(ev.gross_earnings for ev in chunk if not ev.is_unobserved), 2)
        net_sum = round(sum(ev.net_earnings for ev in chunk if not ev.is_unobserved), 2)
        active_count = sum(1 for ev in chunk if ev.is_active and not ev.is_unobserved)

        weekly_payouts.append(
            WeeklyPayoutEvent(
                application_id=application.application_id,
                payout_id=payout_id,
                cycle_index=cycle_index,
                period_start=period_start,
                period_end=period_end,
                payout_timestamp=format_utc_iso(settlement_dt),
                gross_amount=gross_sum,
                net_amount=net_sum,
                active_days=active_count,
                is_settled=True,
            )
        )

    # --------------------------------------------------------------------------
    # 5. Build Summary HistoricalTelemetry Structure
    # --------------------------------------------------------------------------
    daily_active_flags = [ev.is_active for ev in daily_events]
    daily_net_earnings = [ev.net_earnings for ev in daily_events]
    daily_gross_earnings = [ev.gross_earnings for ev in daily_events]
    daily_working_hours = [ev.hours_worked for ev in daily_events]
    weekly_net_payouts = [p.net_amount for p in weekly_payouts]

    telemetry_summary = HistoricalTelemetry(
        application_id=application.application_id,
        daily_active_flags=daily_active_flags,
        daily_net_earnings=daily_net_earnings,
        daily_gross_earnings=daily_gross_earnings,
        daily_working_hours=daily_working_hours,
        weekly_net_payouts=weekly_net_payouts,
        observed_days=observed_days,
        payout_count=len(weekly_payouts),
    )

    return ApplicationHistoricalData(
        application_id=application.application_id,
        applicant_profile_id=application.applicant_profile_id,
        cutoff_timestamp=application.cutoff_timestamp,
        history_start_timestamp=format_utc_iso(history_start_dt),
        history_end_timestamp=application.cutoff_timestamp,
        observed_days=observed_days,
        daily_events=daily_events,
        weekly_payouts=weekly_payouts,
        telemetry_summary=telemetry_summary,
    )
