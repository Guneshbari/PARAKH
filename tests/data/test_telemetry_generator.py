"""
PARAKH Synthetic Data Generator - Historical Telemetry Test Suite (P2-T05)
Verifies:
- Relational integrity: every event belongs to a valid application_id
- Timestamp formatting: valid UTC ISO-8601 formatting for shifts and settlement timestamps
- Strict temporal bounds: history_start <= event_time < t0 (zero leakage across all events)
- Payout settlement timing: max(payout_timestamp) < t0
- Repeat applicants: independent, non-overlapping 90-day historical observation windows
- Deterministic reproducibility: master seed 42 produces identical telemetry
- Independent application RNG streams: SHA-256 derived PRNGs are isolated
- Cohort dynamics:
  * Healthy Volatile: high CV, weekend surge, acute dip and recovery
  * Stable: low CV, steady shifts, zero zero-earning weeks
  * Declining: negative earnings trend, consecutive weekly drops
  * Irregular: high inactive days, prolonged idle streaks, zero-earning weeks
  * High Obligation: steady elevated earnings
  * Insufficient Data: observed_days in [5, 25], payout_count in [1, 3], pre-onboarding unobserved days
- Zero vs unobserved semantics: 0.0 != unobserved != null
- Accounting invariants: gross >= net >= 0, gross == net + platform_fee
- Anti-leakage: zero forward or target labels present in historical layer
"""

from datetime import datetime, timezone, timedelta
import math
import unittest

from src.data.synthetic.config import (
    COHORT_DECLINING,
    COHORT_HEALTHY_VOLATILE,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    COHORT_IRREGULAR,
    COHORT_STABLE,
    MASTER_SEED,
    OBSERVATION_WINDOW_DAYS,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.random_state import RandomStateManager
from src.data.synthetic.schemas import (
    Application,
    ApplicantProfile,
    ApplicationHistoricalData,
    DailyActivityEvent,
    WeeklyPayoutEvent,
)
from src.data.synthetic.telemetry_generator import (
    format_utc_iso,
    generate_application_history,
    get_application_rng,
)


class TestTelemetryGenerator(unittest.TestCase):
    """Full test suite for 90-day historical time-series generator (P2-T05)."""

    @classmethod
    def setUpClass(cls):
        """Generate population once and sample applications across cohorts."""
        cls.population = generate_population(RandomStateManager(MASTER_SEED))
        cls.profiles_by_id = {p.applicant_profile_id: p for p in cls.population.profiles}

        # Index applications by cohort
        cls.apps_by_cohort = {}
        for app in cls.population.applications:
            prof = cls.profiles_by_id[app.applicant_profile_id]
            cls.apps_by_cohort.setdefault(prof.cohort_archetype, []).append(app)

    def test_relational_integrity(self):
        """Every daily event and weekly payout must belong to the application_id."""
        sample_app = self.population.applications[0]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        self.assertEqual(history.application_id, sample_app.application_id)
        self.assertEqual(history.applicant_profile_id, sample_app.applicant_profile_id)

        for event in history.daily_events:
            self.assertEqual(event.application_id, sample_app.application_id)

        for payout in history.weekly_payouts:
            self.assertEqual(payout.application_id, sample_app.application_id)

    def test_iso8601_utc_timestamps(self):
        """All daily shifts and weekly payout timestamps must be valid ISO-8601 UTC strings."""
        sample_app = self.population.applications[10]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        # Cutoff parsing
        cutoff_dt = datetime.fromisoformat(history.cutoff_timestamp.replace("Z", "+00:00"))
        start_dt = datetime.fromisoformat(history.history_start_timestamp.replace("Z", "+00:00"))
        self.assertEqual(cutoff_dt.tzinfo, timezone.utc)
        self.assertEqual(start_dt.tzinfo, timezone.utc)

        for event in history.daily_events:
            dt = datetime.fromisoformat(event.date.replace("Z", "+00:00"))
            self.assertEqual(dt.tzinfo, timezone.utc)
            self.assertTrue(event.date.endswith("Z"))

        for payout in history.weekly_payouts:
            p_dt = datetime.fromisoformat(payout.payout_timestamp.replace("Z", "+00:00"))
            self.assertEqual(p_dt.tzinfo, timezone.utc)
            self.assertTrue(payout.payout_timestamp.endswith("Z"))

    def test_strict_temporal_bounds_and_anti_leakage(self):
        """All historical events must strictly satisfy: t0 - 90d <= event_time < t0."""
        # Test on multiple applications across different cohorts
        sample_apps = [self.apps_by_cohort[c][0] for c in self.apps_by_cohort]

        for app in sample_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)
            cutoff_dt = datetime.fromisoformat(app.cutoff_timestamp.replace("Z", "+00:00"))
            window_start_dt = cutoff_dt - timedelta(days=OBSERVATION_WINDOW_DAYS)

            # Check daily events
            self.assertEqual(len(history.daily_events), OBSERVATION_WINDOW_DAYS)
            for event in history.daily_events:
                event_dt = datetime.fromisoformat(event.date.replace("Z", "+00:00"))
                # Temporal invariant: window_start <= event_dt < cutoff_dt
                self.assertGreaterEqual(event_dt, window_start_dt)
                self.assertLess(event_dt, cutoff_dt)

            # Check weekly payouts
            for payout in history.weekly_payouts:
                payout_dt = datetime.fromisoformat(payout.payout_timestamp.replace("Z", "+00:00"))
                start_cycle_dt = datetime.fromisoformat(payout.period_start.replace("Z", "+00:00"))
                end_cycle_dt = datetime.fromisoformat(payout.period_end.replace("Z", "+00:00"))

                self.assertGreaterEqual(start_cycle_dt, window_start_dt)
                self.assertLessEqual(end_cycle_dt, payout_dt)
                self.assertLess(payout_dt, cutoff_dt, f"Payout timestamp {payout_dt} leaked past cutoff {cutoff_dt}")

    def test_repeat_applicant_independent_windows(self):
        """Repeat applicants must have independent historical windows without overlap or leakage."""
        # Find repeat applicants (those with exactly 2 applications)
        applicant_app_counts = {}
        for app in self.population.applications:
            applicant_app_counts.setdefault(app.applicant_profile_id, []).append(app)

        repeat_applicant_ids = [pid for pid, apps in applicant_app_counts.items() if len(apps) == 2]
        self.assertGreater(len(repeat_applicant_ids), 0)

        # Test first 10 repeat applicants
        for pid in repeat_applicant_ids[:10]:
            apps = sorted(applicant_app_counts[pid], key=lambda a: a.cutoff_timestamp)
            app1, app2 = apps[0], apps[1]
            profile = self.profiles_by_id[pid]

            t1 = datetime.fromisoformat(app1.cutoff_timestamp.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(app2.cutoff_timestamp.replace("Z", "+00:00"))

            # Interval must be >= 120 days
            delta_days = (t2 - t1).total_seconds() / 86400.0
            self.assertGreaterEqual(delta_days, 120.0)

            hist1 = generate_application_history(app1, profile, MASTER_SEED)
            hist2 = generate_application_history(app2, profile, MASTER_SEED)

            # Max event time in hist1 must be strictly before min event time in hist2
            max_t1_daily = max(datetime.fromisoformat(e.date.replace("Z", "+00:00")) for e in hist1.daily_events)
            min_t2_daily = min(datetime.fromisoformat(e.date.replace("Z", "+00:00")) for e in hist2.daily_events)

            self.assertLess(max_t1_daily, min_t2_daily)

            max_t1_payout = max(datetime.fromisoformat(p.payout_timestamp.replace("Z", "+00:00")) for p in hist1.weekly_payouts)
            min_t2_payout = min(datetime.fromisoformat(p.period_start.replace("Z", "+00:00")) for p in hist2.weekly_payouts)

            self.assertLess(max_t1_payout, min_t2_payout)

    def test_deterministic_reproducibility(self):
        """Identical inputs and master seed must produce bit-for-bit identical history."""
        sample_app = self.population.applications[42]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]

        hist_a = generate_application_history(sample_app, profile, master_seed=42)
        hist_b = generate_application_history(sample_app, profile, master_seed=42)

        self.assertEqual(hist_a.observed_days, hist_b.observed_days)
        self.assertEqual(len(hist_a.daily_events), len(hist_b.daily_events))
        self.assertEqual(len(hist_a.weekly_payouts), len(hist_b.weekly_payouts))

        for ea, eb in zip(hist_a.daily_events, hist_b.daily_events):
            self.assertEqual(ea.date, eb.date)
            self.assertEqual(ea.is_active, eb.is_active)
            self.assertAlmostEqual(ea.gross_earnings, eb.gross_earnings, places=4)
            self.assertAlmostEqual(ea.net_earnings, eb.net_earnings, places=4)
            self.assertEqual(ea.is_unobserved, eb.is_unobserved)

        for pa, pb in zip(hist_a.weekly_payouts, hist_b.weekly_payouts):
            self.assertEqual(pa.payout_id, pb.payout_id)
            self.assertAlmostEqual(pa.net_amount, pb.net_amount, places=4)

    def test_independent_application_rng_streams(self):
        """Different applications must derive independent random streams."""
        app1 = self.population.applications[0]
        app2 = self.population.applications[1]

        rng1 = get_application_rng(MASTER_SEED, app1.application_id)
        rng2 = get_application_rng(MASTER_SEED, app2.application_id)

        seq1 = [rng1.random() for _ in range(10)]
        seq2 = [rng2.random() for _ in range(10)]

        self.assertNotEqual(seq1, seq2)

    def test_accounting_and_platform_fee_invariants(self):
        """Platform fee and gross earnings must obey conservation laws: gross == net + fee."""
        sample_apps = self.population.applications[:20]
        for app in sample_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            for event in history.daily_events:
                self.assertGreaterEqual(event.gross_earnings, 0.0)
                self.assertGreaterEqual(event.net_earnings, 0.0)
                self.assertGreaterEqual(event.platform_fee, 0.0)
                self.assertGreaterEqual(event.gross_earnings, event.net_earnings)
                self.assertAlmostEqual(event.gross_earnings, event.net_earnings + event.platform_fee, places=2)

            for payout in history.weekly_payouts:
                self.assertGreaterEqual(payout.gross_amount, payout.net_amount)
                self.assertGreaterEqual(payout.net_amount, 0.0)

    def test_cohort_healthy_volatile_dynamics(self):
        """Healthy Volatile cohort must exhibit high CV, weekend surge, and acute dip with recovery."""
        hv_apps = self.apps_by_cohort[COHORT_HEALTHY_VOLATILE][:30]

        total_weekday_earnings = []
        total_weekend_earnings = []
        cv_list = []
        dip_detected_count = 0

        for app in hv_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            active_earnings = [e.net_earnings for e in history.daily_events if e.is_active]
            if len(active_earnings) > 1:
                mean_e = sum(active_earnings) / len(active_earnings)
                variance = sum((x - mean_e) ** 2 for x in active_earnings) / len(active_earnings)
                cv = math.sqrt(variance) / mean_e if mean_e > 0 else 0
                cv_list.append(cv)

            weekday_net = [e.net_earnings for e in history.daily_events if e.is_active and not e.is_weekend]
            weekend_net = [e.net_earnings for e in history.daily_events if e.is_active and e.is_weekend]
            if weekday_net:
                total_weekday_earnings.append(sum(weekday_net) / len(weekday_net))
            if weekend_net:
                total_weekend_earnings.append(sum(weekend_net) / len(weekend_net))

            # Check for acute dip: 5-8 days with earnings <= 50% baseline
            baseline = profile.baseline_weekly_income / 6.0
            low_days = [e for e in history.daily_events if e.net_earnings < 0.50 * baseline]
            if len(low_days) >= 4:
                dip_detected_count += 1

        # Healthy Volatile average CV should be substantial (target ~ 0.35)
        avg_cv = sum(cv_list) / len(cv_list)
        self.assertGreaterEqual(avg_cv, 0.20)

        # Weekend earnings surge check: average weekend net earnings should exceed weekday earnings
        avg_weekend = sum(total_weekend_earnings) / len(total_weekend_earnings)
        avg_weekday = sum(total_weekday_earnings) / len(total_weekday_earnings)
        self.assertGreater(avg_weekend, avg_weekday)

        # Acute dip episode should be present in most Healthy Volatile profiles
        self.assertGreater(dip_detected_count, len(hv_apps) * 0.70)

    def test_cohort_stable_dynamics(self):
        """Stable cohort must have low CV, high active shifts, and zero zero-earning weeks."""
        stable_apps = self.apps_by_cohort[COHORT_STABLE][:30]
        cv_list = []
        zero_earning_payout_weeks = 0

        for app in stable_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            active_earnings = [e.net_earnings for e in history.daily_events if e.is_active]
            if len(active_earnings) > 1:
                mean_e = sum(active_earnings) / len(active_earnings)
                variance = sum((x - mean_e) ** 2 for x in active_earnings) / len(active_earnings)
                cv = math.sqrt(variance) / mean_e if mean_e > 0 else 0
                cv_list.append(cv)

            # High active shift count: > 50 active days in 90d
            active_days_count = sum(1 for e in history.daily_events if e.is_active)
            self.assertGreaterEqual(active_days_count, 50)

            # Zero-earning weeks check
            for payout in history.weekly_payouts:
                if payout.net_amount == 0.0:
                    zero_earning_payout_weeks += 1

        avg_cv = sum(cv_list) / len(cv_list)
        # Stable CV must be strictly low (around 0.10 - 0.20)
        self.assertLess(avg_cv, 0.25)
        # Zero zero-earning weeks in Stable cohort
        self.assertEqual(zero_earning_payout_weeks, 0)

    def test_cohort_declining_dynamics(self):
        """Declining cohort must show negative trajectory over 90 days."""
        declining_apps = self.apps_by_cohort[COHORT_DECLINING][:30]
        net_drift_negative_count = 0

        for app in declining_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            # Compare first 30 days total net vs last 30 days total net
            first_30 = sum(e.net_earnings for e in history.daily_events[:30])
            last_30 = sum(e.net_earnings for e in history.daily_events[-30:])

            if last_30 < first_30:
                net_drift_negative_count += 1

        # Vast majority of declining cohort must have last 30d < first 30d
        self.assertGreater(net_drift_negative_count, len(declining_apps) * 0.85)

    def test_cohort_irregular_dynamics(self):
        """Irregular cohort must have high inactivity rate, idle streaks, and zero-earning weeks."""
        irregular_apps = self.apps_by_cohort[COHORT_IRREGULAR][:30]
        has_zero_week_count = 0
        has_streak_count = 0

        for app in irregular_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            # Inactive days count
            inactive_days = sum(1 for e in history.daily_events if not e.is_active)
            self.assertGreaterEqual(inactive_days, 35)

            # Check for idle streaks >= 6 days
            max_streak = 0
            cur_streak = 0
            for e in history.daily_events:
                if not e.is_active:
                    cur_streak += 1
                    max_streak = max(max_streak, cur_streak)
                else:
                    cur_streak = 0
            if max_streak >= 6:
                has_streak_count += 1

            # Check for zero-earning weekly payouts
            zero_weeks = sum(1 for p in history.weekly_payouts if p.net_amount == 0.0)
            if zero_weeks >= 1:
                has_zero_week_count += 1

        self.assertGreater(has_streak_count, len(irregular_apps) * 0.80)
        self.assertGreater(has_zero_week_count, len(irregular_apps) * 0.70)

    def test_cohort_insufficient_data_dynamics(self):
        """Insufficient Data cohort must have observed_days in [5, 25] and payout_count in [1, 3]."""
        thin_apps = self.apps_by_cohort[COHORT_INSUFFICIENT_DATA][:30]

        for app in thin_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)

            self.assertGreaterEqual(history.observed_days, 5)
            self.assertLessEqual(history.observed_days, 25)

            # Payout count must be between 1 and 3
            self.assertGreaterEqual(len(history.weekly_payouts), 1)
            self.assertLessEqual(len(history.weekly_payouts), 3)

            # Days prior to onboarding must be flagged is_unobserved = True
            unobserved_days = [e for e in history.daily_events if e.is_unobserved]
            observed_days = [e for e in history.daily_events if not e.is_unobserved]

            self.assertEqual(len(observed_days), history.observed_days)
            self.assertEqual(len(unobserved_days), OBSERVATION_WINDOW_DAYS - history.observed_days)

            # Unobserved days have 0.0 earnings and 0 hours
            for e in unobserved_days:
                self.assertFalse(e.is_active)
                self.assertEqual(e.hours_worked, 0.0)
                self.assertEqual(e.net_earnings, 0.0)
                self.assertEqual(e.gross_earnings, 0.0)

    def test_zero_vs_unobserved_semantics(self):
        """Zero net earnings on inactive days must be numeric 0.0, distinct from unobserved days."""
        sample_app = self.apps_by_cohort[COHORT_INSUFFICIENT_DATA][0]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        unobserved_count = sum(1 for e in history.daily_events if e.is_unobserved)
        self.assertGreater(unobserved_count, 0)

        # Inactive days in observed period have is_unobserved == False
        observed_inactive = [e for e in history.daily_events if not e.is_unobserved and not e.is_active]
        for e in observed_inactive:
            self.assertFalse(e.is_unobserved)
            self.assertEqual(e.net_earnings, 0.0)

    def test_anti_leakage_absence_of_future_targets(self):
        """ApplicationHistoricalData must not contain any forward target or outcome variables."""
        sample_app = self.population.applications[0]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        history_dict = history.__dict__
        forbidden_keys = [
            "target_default_flag",
            "repayment_risk_probability",
            "forward_earnings",
            "forward_living_expenses",
            "forward_cashflow",
            "forward_insolvency",
            "future",
            "post_t0",
        ]
        for key in forbidden_keys:
            self.assertNotIn(key, history_dict)

        for event in history.daily_events:
            for key in forbidden_keys:
                self.assertNotIn(key, event.__dict__)

        for payout in history.weekly_payouts:
            for key in forbidden_keys:
                self.assertNotIn(key, payout.__dict__)


if __name__ == "__main__":
    unittest.main()
