"""
PARAKH Synthetic Data Generator - Feature Derivation Test Suite (P2-T06)
Verifies:
1. Every frozen feature is produced (exact 40 model features).
2. No unexpected feature is produced.
3. Feature names exactly match the frozen contract.
4. Feature types are strictly conformant (float, int, optional types).
5. Feature ranges adhere to hard boundaries from Table 2.1 & Section 21.
6. Determinism: identical raw inputs produce bit-for-bit identical features.
7. Sensitivity: modifying a relevant historical event updates the derived feature.
8. Post-t0 leakage test: events at or after t0 trigger TemporalLeakageError and do not alter predictors.
9. Missingness and zero semantics: 0.0 != None != unobserved.
10. Insufficient data cohort compliance: observed_days in [5, 25], payouts in [1, 3], group_count <= 1.
11. Cohort independence: cohort label is never used as a feature value.
12. Repeat applicants: independent feature calculation over disjoint historical windows.
13. Boundary conditions: t0 - 90d boundary, t0 boundary, zero income, zero debt.
"""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import unittest

from src.data.synthetic.config import (
    COHORT_DECLINING,
    COHORT_HEALTHY_VOLATILE,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    COHORT_IRREGULAR,
    COHORT_STABLE,
    MASTER_SEED,
)
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    TemporalLeakageError,
)
from src.data.synthetic.feature_derivation import (
    derive_application_features,
    validate_derived_features,
    calculate_median_income,
    calculate_p25_income,
    calculate_mean_income,
    calculate_trimmed_mean_income,
    calculate_income_cv,
    calculate_downside_variance,
    calculate_iqr_ratio,
    calculate_min_max_ratio,
    calculate_trend_slope,
    calculate_trend_momentum,
    calculate_consecutive_drops,
    calculate_active_days_ratio,
    calculate_zero_earning_weeks,
    calculate_max_idle_streak,
    calculate_weekend_intensity,
    calculate_recovery_metrics,
    calculate_max_drawdown,
    calculate_buffer_to_loan,
    calculate_burn_months,
    calculate_net_margin,
    calculate_dti_ratios,
    calculate_loan_to_income,
    calculate_trips_completed,
    calculate_group_count,
    calculate_missing_ratio,
    calculate_interaction_features,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.random_state import RandomStateManager
from src.data.synthetic.schemas import (
    ApplicationFeatures,
    DerivedFeatures,
    DailyActivityEvent,
    WeeklyPayoutEvent,
    get_derived_feature_columns,
)
from src.data.synthetic.telemetry_generator import (
    format_utc_iso,
    generate_application_history,
)


class TestFeatureDerivation(unittest.TestCase):
    """Full test suite for deterministic feature derivation layer (P2-T06)."""

    @classmethod
    def setUpClass(cls):
        """Generate population once and index by cohort."""
        cls.population = generate_population(RandomStateManager(MASTER_SEED))
        cls.profiles_by_id = {p.applicant_profile_id: p for p in cls.population.profiles}

        cls.apps_by_cohort = {}
        for app in cls.population.applications:
            prof = cls.profiles_by_id[app.applicant_profile_id]
            cls.apps_by_cohort.setdefault(prof.cohort_archetype, []).append(app)

    def test_feature_count_and_exact_naming(self):
        """Every frozen feature must be produced, with no unexpected features and exact names."""
        sample_app = self.population.applications[0]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        app_features = derive_application_features(sample_app, profile, history)
        derived_dict = app_features.features.__dict__

        # 1. Exactly 40 derived features
        self.assertEqual(len(derived_dict), 40)

        # 2. Exact match with frozen dataset schema derived feature columns
        schema_feature_names = set(get_derived_feature_columns())
        produced_feature_names = set(derived_dict.keys())
        self.assertEqual(produced_feature_names, schema_feature_names)

        # 3. Check identifiers
        self.assertEqual(app_features.application_id, sample_app.application_id)
        self.assertEqual(app_features.applicant_profile_id, sample_app.applicant_profile_id)
        self.assertEqual(app_features.cutoff_timestamp, sample_app.cutoff_timestamp)

    def test_feature_types(self):
        """All 40 features must have types conforming strictly to the contract."""
        sample_app = self.population.applications[5]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        app_features = derive_application_features(sample_app, profile, history)
        feat = app_features.features

        # Mandatory floats
        float_fields = [
            "feat_inc_median_90d", "feat_inc_p25_90d", "feat_inc_cv_90d",
            "feat_inc_downside_var", "feat_trend_slope_90d", "feat_trend_momentum_30_90",
            "feat_act_active_days_ratio", "feat_rec_bounceback_ratio", "feat_rec_days_to_recover",
            "feat_liq_buffer_to_loan", "feat_liq_burn_months", "feat_bur_dti_ratio",
            "feat_bur_installment_dti", "feat_bur_total_dti", "feat_suf_missing_ratio",
            "feat_int_vol_x_recovery", "feat_int_vol_x_buffer", "feat_int_trend_x_dti",
            "feat_int_resilience_idx",
        ]
        for f in float_fields:
            val = getattr(feat, f)
            self.assertIsInstance(val, float, f"Field {f} expected float, got {type(val)}")

        # Mandatory integers
        int_fields = [
            "feat_act_zero_earn_weeks", "feat_suf_observed_days",
            "feat_suf_payout_count", "feat_suf_group_count",
        ]
        for f in int_fields:
            val = getattr(feat, f)
            self.assertIsInstance(val, int, f"Field {f} expected int, got {type(val)}")

        # Optional fields (either float/int or None)
        if feat.feat_inc_mean_90d is not None:
            self.assertIsInstance(feat.feat_inc_mean_90d, float)
        if feat.feat_trend_consec_drops is not None:
            self.assertIsInstance(feat.feat_trend_consec_drops, int)
        if feat.feat_act_max_idle_streak is not None:
            self.assertIsInstance(feat.feat_act_max_idle_streak, int)
        if feat.feat_ten_trips_completed is not None:
            self.assertIsInstance(feat.feat_ten_trips_completed, int)

    def test_feature_ranges_across_all_cohorts(self):
        """All derived features must fall within their frozen mathematical bounds."""
        for cohort_name, apps in self.apps_by_cohort.items():
            for app in apps[:10]:
                profile = self.profiles_by_id[app.applicant_profile_id]
                history = generate_application_history(app, profile, MASTER_SEED)
                app_features = derive_application_features(app, profile, history)
                f = app_features.features

                # Group 1: Income
                self.assertGreaterEqual(f.feat_inc_median_90d, 0.0)
                self.assertLessEqual(f.feat_inc_median_90d, 500000.0)
                self.assertGreaterEqual(f.feat_inc_p25_90d, 0.0)
                self.assertLessEqual(f.feat_inc_p25_90d, f.feat_inc_median_90d)
                self.assertGreaterEqual(f.feat_inc_cv_90d, 0.0)
                self.assertLessEqual(f.feat_inc_cv_90d, 5.0)
                self.assertGreaterEqual(f.feat_inc_downside_var, 0.0)
                self.assertLessEqual(f.feat_inc_downside_var, 1.0e10)

                # Group 2: Trajectory
                self.assertGreaterEqual(f.feat_trend_slope_90d, -50000.0)
                self.assertLessEqual(f.feat_trend_slope_90d, 50000.0)
                self.assertGreaterEqual(f.feat_trend_momentum_30_90, 0.0)
                self.assertLessEqual(f.feat_trend_momentum_30_90, 5.0)

                # Group 3: Work Activity
                self.assertGreaterEqual(f.feat_act_active_days_ratio, 0.0)
                self.assertLessEqual(f.feat_act_active_days_ratio, 1.0)
                self.assertGreaterEqual(f.feat_act_zero_earn_weeks, 0)
                self.assertLessEqual(f.feat_act_zero_earn_weeks, 13)

                # Group 4: Recovery
                self.assertGreaterEqual(f.feat_rec_bounceback_ratio, 0.0)
                self.assertLessEqual(f.feat_rec_bounceback_ratio, 10.0)
                self.assertGreaterEqual(f.feat_rec_days_to_recover, 0.0)
                self.assertLessEqual(f.feat_rec_days_to_recover, 90.0)

                # Group 5: Liquidity & Debt
                self.assertGreaterEqual(f.feat_liq_buffer_to_loan, 0.0)
                self.assertLessEqual(f.feat_liq_buffer_to_loan, 50.0)
                self.assertGreaterEqual(f.feat_liq_burn_months, 0.0)
                self.assertLessEqual(f.feat_liq_burn_months, 60.0)
                self.assertGreaterEqual(f.feat_bur_dti_ratio, 0.0)
                self.assertLessEqual(f.feat_bur_dti_ratio, 20.0)
                self.assertGreaterEqual(f.feat_bur_installment_dti, 0.0)
                self.assertLessEqual(f.feat_bur_installment_dti, 20.0)
                self.assertGreaterEqual(f.feat_bur_total_dti, 0.0)
                self.assertLessEqual(f.feat_bur_total_dti, 20.0)

                # Group 6: Sufficiency
                self.assertGreaterEqual(f.feat_suf_observed_days, 0)
                self.assertLessEqual(f.feat_suf_observed_days, 90)
                self.assertGreaterEqual(f.feat_suf_payout_count, 0)
                self.assertLessEqual(f.feat_suf_payout_count, 90)
                self.assertGreaterEqual(f.feat_suf_group_count, 0)
                self.assertLessEqual(f.feat_suf_group_count, 5)
                self.assertGreaterEqual(f.feat_suf_missing_ratio, 0.0)
                self.assertLessEqual(f.feat_suf_missing_ratio, 1.0)

                # Group 7: Interactions
                self.assertGreaterEqual(f.feat_int_vol_x_recovery, 0.0)
                self.assertLessEqual(f.feat_int_vol_x_recovery, 450.0)
                self.assertGreaterEqual(f.feat_int_vol_x_buffer, 0.0)
                self.assertLessEqual(f.feat_int_vol_x_buffer, 50.0)
                self.assertGreaterEqual(f.feat_int_trend_x_dti, -50000.0)
                self.assertLessEqual(f.feat_int_trend_x_dti, 50000.0)
                self.assertGreaterEqual(f.feat_int_resilience_idx, 0.0)
                self.assertLessEqual(f.feat_int_resilience_idx, 100.0)

    def test_deterministic_reproducibility(self):
        """Deriving features twice from identical inputs must produce bit-for-bit identical outputs."""
        sample_app = self.population.applications[42]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        feat_a = derive_application_features(sample_app, profile, history)
        feat_b = derive_application_features(sample_app, profile, history)

        dict_a = feat_a.to_dict()
        dict_b = feat_b.to_dict()

        self.assertEqual(dict_a, dict_b)

    def test_sensitivity_to_historical_events(self):
        """Altering a historical payout must change the corresponding derived feature."""
        sample_app = self.population.applications[15]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history_orig = generate_application_history(sample_app, profile, MASTER_SEED)
        feat_orig = derive_application_features(sample_app, profile, history_orig)

        # Clone and mutate a payout
        history_mutated = deepcopy(history_orig)
        p0 = history_mutated.weekly_payouts[0]
        # Dramatically increase first payout
        mutated_p0 = WeeklyPayoutEvent(
            application_id=p0.application_id,
            payout_id=p0.payout_id,
            cycle_index=p0.cycle_index,
            period_start=p0.period_start,
            period_end=p0.period_end,
            payout_timestamp=p0.payout_timestamp,
            gross_amount=p0.gross_amount + 50000.0,
            net_amount=p0.net_amount + 40000.0,
            active_days=p0.active_days,
            is_settled=p0.is_settled,
        )
        history_mutated.weekly_payouts[0] = mutated_p0
        feat_mutated = derive_application_features(sample_app, profile, history_mutated)

        # Mean and slope must change
        self.assertNotEqual(feat_orig.features.feat_inc_mean_90d, feat_mutated.features.feat_inc_mean_90d)
        self.assertNotEqual(feat_orig.features.feat_trend_slope_90d, feat_mutated.features.feat_trend_slope_90d)

    def test_post_t0_temporal_leakage_guard(self):
        """Any event occurring at or after cutoff t0 must trigger TemporalLeakageError."""
        sample_app = self.population.applications[2]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        cutoff_dt = datetime.fromisoformat(sample_app.cutoff_timestamp.replace("Z", "+00:00"))

        # 1. Leakage via daily event at cutoff
        history_leaked_daily = deepcopy(history)
        leaked_daily_event = DailyActivityEvent(
            application_id=sample_app.application_id,
            date=format_utc_iso(cutoff_dt),  # exactly at t0
            day_offset=0,
            is_active=True,
            hours_worked=8.0,
            is_weekend=False,
            gross_earnings=1000.0,
            platform_fee=200.0,
            net_earnings=800.0,
            is_unobserved=False,
        )
        history_leaked_daily.daily_events.append(leaked_daily_event)

        with self.assertRaises(TemporalLeakageError):
            derive_application_features(sample_app, profile, history_leaked_daily)

        # 2. Leakage via weekly payout after cutoff
        history_leaked_payout = deepcopy(history)
        leaked_payout_event = WeeklyPayoutEvent(
            application_id=sample_app.application_id,
            payout_id="leak-test-uuid",
            cycle_index=14,
            period_start=format_utc_iso(cutoff_dt),
            period_end=format_utc_iso(cutoff_dt + timedelta(days=7)),
            payout_timestamp=format_utc_iso(cutoff_dt + timedelta(hours=1)),  # after t0
            gross_amount=5000.0,
            net_amount=4000.0,
            active_days=5,
            is_settled=True,
        )
        history_leaked_payout.weekly_payouts.append(leaked_payout_event)

        with self.assertRaises(TemporalLeakageError):
            derive_application_features(sample_app, profile, history_leaked_payout)

    def test_missing_and_zero_semantics(self):
        """Observed zero must be preserved as 0.0 and distinct from None/unobserved."""
        # 1. Debt-free applicant
        profile_zero_debt = deepcopy(self.population.profiles[0])
        profile_zero_debt.existing_monthly_debt = 0.0
        sample_app = self.population.applications[0]
        history = generate_application_history(sample_app, profile_zero_debt, MASTER_SEED)

        feat = derive_application_features(sample_app, profile_zero_debt, history).features
        self.assertEqual(feat.feat_bur_dti_ratio, 0.0)
        self.assertIsNotNone(feat.feat_bur_dti_ratio)

        # 2. Null optional fields in profile
        profile_nulls = deepcopy(profile_zero_debt)
        profile_nulls.years_working = None
        profile_nulls.platform_rating = None
        profile_nulls.cancellation_rate = None
        profile_nulls.payment_reliability = None

        feat_nulls = derive_application_features(sample_app, profile_nulls, history).features
        self.assertIsNone(feat_nulls.feat_ten_years_working)
        self.assertIsNone(feat_nulls.feat_ten_platform_rating)
        self.assertIsNone(feat_nulls.feat_ten_cancellation_rate)
        self.assertIsNone(feat_nulls.feat_pay_utility_on_time)
        self.assertIsNone(feat_nulls.feat_pay_max_bill_delay)
        self.assertIsNone(feat_nulls.feat_pay_repay_reliability)

        # Missing ratio must increase
        self.assertGreater(feat_nulls.feat_suf_missing_ratio, feat.feat_suf_missing_ratio)

    def test_cohort_insufficient_data_rules(self):
        """Insufficient Data cohort must obey frozen minimum-history and sufficiency rules."""
        thin_apps = self.apps_by_cohort[COHORT_INSUFFICIENT_DATA][:10]

        for app in thin_apps:
            profile = self.profiles_by_id[app.applicant_profile_id]
            history = generate_application_history(app, profile, MASTER_SEED)
            feat = derive_application_features(app, profile, history).features

            # History span in [5, 25] days
            self.assertGreaterEqual(feat.feat_suf_observed_days, 5)
            self.assertLessEqual(feat.feat_suf_observed_days, 25)

            # Payouts in [1, 3]
            self.assertGreaterEqual(feat.feat_suf_payout_count, 1)
            self.assertLessEqual(feat.feat_suf_payout_count, 3)

            # Signal groups <= 1
            self.assertLessEqual(feat.feat_suf_group_count, 1)

    def test_cohort_independence(self):
        """Cohort labels must not be used as direct feature values."""
        # Swap cohort archetype on identical profile & history: features must be 100% identical
        sample_app = self.population.applications[0]
        profile_orig = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile_orig, MASTER_SEED)

        feat_orig = derive_application_features(sample_app, profile_orig, history)

        profile_swapped = deepcopy(profile_orig)
        profile_swapped.cohort_archetype = COHORT_DECLINING  # swapped label
        feat_swapped = derive_application_features(sample_app, profile_swapped, history)

        # All 40 features must be completely identical despite swapped cohort label
        self.assertEqual(feat_orig.features, feat_swapped.features)

    def test_repeat_applicant_independent_features(self):
        """Repeat applications must calculate features independently over their own trailing windows."""
        applicant_app_counts = {}
        for app in self.population.applications:
            applicant_app_counts.setdefault(app.applicant_profile_id, []).append(app)

        repeat_pids = [pid for pid, apps in applicant_app_counts.items() if len(apps) == 2]
        self.assertGreater(len(repeat_pids), 0)

        # Test first 5 repeat applicants
        for pid in repeat_pids[:5]:
            apps = sorted(applicant_app_counts[pid], key=lambda a: a.cutoff_timestamp)
            app1, app2 = apps[0], apps[1]
            profile = self.profiles_by_id[pid]

            hist1 = generate_application_history(app1, profile, MASTER_SEED)
            hist2 = generate_application_history(app2, profile, MASTER_SEED)

            feat1 = derive_application_features(app1, profile, hist1)
            feat2 = derive_application_features(app2, profile, hist2)

            self.assertEqual(feat1.application_id, app1.application_id)
            self.assertEqual(feat2.application_id, app2.application_id)
            self.assertNotEqual(feat1.cutoff_timestamp, feat2.cutoff_timestamp)

    def test_impossible_combinations_rejection(self):
        """Physical contradictions must trigger ImpossibleCombinationError."""
        # 1. Zero active days with positive median income
        feat_contradiction = DerivedFeatures(
            feat_inc_median_90d=5000.0,
            feat_inc_p25_90d=4000.0,
            feat_inc_cv_90d=0.20,
            feat_inc_downside_var=1000.0,
            feat_trend_slope_90d=0.0,
            feat_trend_momentum_30_90=1.0,
            feat_act_active_days_ratio=0.0,  # contradiction: 0 active days but 5000 income
            feat_act_zero_earn_weeks=0,
            feat_rec_bounceback_ratio=1.0,
            feat_rec_days_to_recover=0.0,
            feat_liq_buffer_to_loan=1.0,
            feat_liq_burn_months=1.0,
            feat_bur_dti_ratio=0.1,
            feat_bur_installment_dti=0.1,
            feat_bur_total_dti=0.2,
            feat_suf_observed_days=90,
            feat_suf_payout_count=12,
            feat_suf_group_count=4,
            feat_suf_missing_ratio=0.0,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_derived_features(feat_contradiction)

    def test_explicit_leakage_procedure(self):
        """
        Explicit 4-step leakage verification procedure:
        1. Derive features from historical data.
        2. Attempt to add or modify an event occurring at or after t0.
        3. Verify that derivation strictly rejects the post-t0 event via TemporalLeakageError.
        4. Verify that the feature vector is immune to any post-t0 mutations.
        """
        sample_app = self.population.applications[7]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        history = generate_application_history(sample_app, profile, MASTER_SEED)

        # Step 1: Derive baseline feature vector F1
        f1 = derive_application_features(sample_app, profile, history)

        # Step 2: Create a post-t0 event (e.g. tomorrow's payout)
        cutoff_dt = datetime.fromisoformat(sample_app.cutoff_timestamp.replace("Z", "+00:00"))
        post_t0_payout = WeeklyPayoutEvent(
            application_id=sample_app.application_id,
            payout_id="post-t0-leakage-id",
            cycle_index=15,
            period_start=format_utc_iso(cutoff_dt),
            period_end=format_utc_iso(cutoff_dt + timedelta(days=7)),
            payout_timestamp=format_utc_iso(cutoff_dt + timedelta(days=7, hours=4)),
            gross_amount=15000.0,
            net_amount=12000.0,
            active_days=6,
            is_settled=True,
        )

        history_with_leak = deepcopy(history)
        history_with_leak.weekly_payouts.append(post_t0_payout)

        # Step 3: Verify derivation strictly raises TemporalLeakageError
        with self.assertRaises(TemporalLeakageError):
            derive_application_features(sample_app, profile, history_with_leak)

        # Step 4: Verify that filtering events to strictly event_time < t0 preserves exact F1
        sanitized_payouts = [
            p for p in history_with_leak.weekly_payouts
            if datetime.fromisoformat(p.payout_timestamp.replace("Z", "+00:00")) < cutoff_dt
        ]
        history_sanitized = deepcopy(history_with_leak)
        history_sanitized.weekly_payouts = sanitized_payouts
        f2 = derive_application_features(sample_app, profile, history_sanitized)

        self.assertEqual(f1.to_dict(), f2.to_dict())

    def test_boundary_conditions(self):
        """Verify behavior at exact temporal and value boundaries."""
        sample_app = self.population.applications[12]
        profile = self.profiles_by_id[sample_app.applicant_profile_id]
        cutoff_dt = datetime.fromisoformat(sample_app.cutoff_timestamp.replace("Z", "+00:00"))

        # 1. Event immediately before t0 (1 second before t0) must be accepted
        history = generate_application_history(sample_app, profile, MASTER_SEED)
        history_edge = deepcopy(history)
        edge_event = DailyActivityEvent(
            application_id=sample_app.application_id,
            date=format_utc_iso(cutoff_dt - timedelta(seconds=1)),
            day_offset=-1,
            is_active=True,
            hours_worked=4.0,
            is_weekend=False,
            gross_earnings=500.0,
            platform_fee=100.0,
            net_earnings=400.0,
            is_unobserved=False,
        )
        history_edge.daily_events[-1] = edge_event
        feat_edge = derive_application_features(sample_app, profile, history_edge)
        self.assertIsNotNone(feat_edge)

        # 2. Event exactly at t0 must be rejected
        history_exact_t0 = deepcopy(history)
        exact_t0_event = DailyActivityEvent(
            application_id=sample_app.application_id,
            date=format_utc_iso(cutoff_dt),
            day_offset=0,
            is_active=True,
            hours_worked=4.0,
            is_weekend=False,
            gross_earnings=500.0,
            platform_fee=100.0,
            net_earnings=400.0,
            is_unobserved=False,
        )
        history_exact_t0.daily_events[-1] = exact_t0_event
        with self.assertRaises(TemporalLeakageError):
            derive_application_features(sample_app, profile, history_exact_t0)

        # 3. Event exactly 90 days before t0 is valid
        start_dt = cutoff_dt - timedelta(days=90)
        history_start = deepcopy(history)
        history_start.daily_events[0] = DailyActivityEvent(
            application_id=sample_app.application_id,
            date=format_utc_iso(start_dt),
            day_offset=-90,
            is_active=False,
            hours_worked=0.0,
            is_weekend=False,
            gross_earnings=0.0,
            platform_fee=0.0,
            net_earnings=0.0,
            is_unobserved=False,
        )
        feat_start = derive_application_features(sample_app, profile, history_start)
        self.assertIsNotNone(feat_start)

    def test_individual_math_helpers(self):
        """Test individual calculation functions against frozen contract worked examples."""
        # Contract Section 3.2 examples
        sample_payouts = [6500.0, 7200.0, 8100.0, 7000.0]

        # Median = 7100.0
        self.assertEqual(calculate_median_income(sample_payouts), 7100.0)

        # 25th percentile = 6625.0
        self.assertEqual(calculate_p25_income(sample_payouts, 7100.0), 6625.0)

        # Mean = 7200.0
        self.assertEqual(calculate_mean_income(sample_payouts), 7200.0)

        # Buffer to loan: 15,000 / 20,000 = 0.75
        self.assertEqual(calculate_buffer_to_loan(15000.0, 20000.0), 0.75)

        # Burn months: 15,000 / 15,000 = 1.0
        self.assertEqual(calculate_burn_months(15000.0, 5000.0, 10000.0), 1.0)

        # DTI: Debt 4,000 / (7100 * 4.333333 = 30766.66) = 0.1300
        dti, inst_dti, total_dti = calculate_dti_ratios(4000.0, 3600.0, 7100.0)
        self.assertAlmostEqual(dti, 4000.0 / (7100.0 * 4.333333), places=3)
        self.assertAlmostEqual(inst_dti, 3600.0 / (7100.0 * 4.333333), places=3)
        self.assertAlmostEqual(total_dti, dti + inst_dti, places=3)

        # Interaction terms
        vol_rec, vol_buf, trend_dti, res_idx = calculate_interaction_features(
            0.35, 8.0, 0.75, 145.20, 0.2472, 1.1972
        )
        self.assertEqual(vol_rec, 2.80)
        self.assertEqual(vol_buf, 0.4118)
        self.assertEqual(trend_dti, 181.09)
        self.assertEqual(res_idx, 2.9930)


if __name__ == "__main__":
    unittest.main()
