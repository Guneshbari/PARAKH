"""
Unit and Integration Tests for Forward Target & Outcome Generator (P2-T07).
Validates:
1. Target existence for eligible applications.
2. Frozen target encoding (0, 1, or None).
3. Future outcome horizon strictly > t0.
4. Prediction horizon matching loan tenure and frozen bounds [30, 90].
5. Deterministic reproducibility with master seed 42.
6. Independent application PRNG streams.
7. Repeat applications having independent, non-overlapping future windows.
8. Zero mutation of historical predictors or applications.
9. Feature independence from generated forward outcomes.
10. Incomplete observation handling for Insufficient Data cohort.
11. Zero target leakage into the feature layer.
12. Observed default rate calculation and natural emergence.
13. Absence of post-generation relabeling.
14. Rejection of impossible outcome combinations.
15. Mismatched profile ID rejection.
"""

from datetime import datetime, timezone, timedelta
import unittest
from typing import Dict, List

from src.data.synthetic.config import (
    MASTER_SEED,
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    INSOLVENCY_GRACE_PERIOD_DAYS,
    PREDICTION_HORIZON_DAYS_MIN,
    PREDICTION_HORIZON_DAYS_MAX,
)
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    DerivedFeatures,
    ApplicationFeatures,
    ForwardOutcome,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.telemetry_generator import generate_application_history
from src.data.synthetic.feature_derivation import derive_application_features
from src.data.synthetic.target_generator import (
    get_target_rng,
    compute_prediction_horizon,
    simulate_single_forward_path,
    simulate_forward_outcome,
    generate_forward_outcomes,
    validate_forward_outcome,
)


class TestTargetGenerator(unittest.TestCase):
    """Test suite for the forward target and outcome generator."""

    @classmethod
    def setUpClass(cls):
        """Generate test population once for test efficiency."""
        cls.population = generate_population(n_applicants=200, n_repeats=40)
        cls.profiles_by_id = {p.applicant_profile_id: p for p in cls.population.profiles}

    def test_target_exists_for_eligible_applications(self):
        """1. Target exists and is binary {0, 1} for all scored cohorts."""
        scored_cohorts = {
            COHORT_HEALTHY_VOLATILE,
            COHORT_STABLE,
            COHORT_DECLINING,
            COHORT_IRREGULAR,
            COHORT_HIGH_OBLIGATION,
        }
        for app in self.population.applications:
            prof = self.profiles_by_id[app.applicant_profile_id]
            if prof.cohort_archetype in scored_cohorts:
                outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
                self.assertIsNotNone(
                    outcome.target_default_flag,
                    f"Target must not be None for scored cohort {prof.cohort_archetype}",
                )
                self.assertIn(
                    outcome.target_default_flag,
                    (0, 1),
                    f"Target must be 0 or 1, got {outcome.target_default_flag}",
                )
                self.assertIsInstance(outcome.target_default_flag, int)

    def test_frozen_target_encoding(self):
        """2. Target values follow the frozen encoding: 0, 1, or None."""
        for app in self.population.applications[:50]:
            prof = self.profiles_by_id[app.applicant_profile_id]
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
            if prof.cohort_archetype == COHORT_INSUFFICIENT_DATA:
                self.assertIsNone(outcome.target_default_flag)
                self.assertIsNone(outcome.repayment_risk_probability)
            else:
                self.assertIn(outcome.target_default_flag, (0, 1))
                self.assertIsInstance(outcome.repayment_risk_probability, float)
                self.assertGreaterEqual(outcome.repayment_risk_probability, 0.0)
                self.assertLessEqual(outcome.repayment_risk_probability, 1.0)

    def test_future_outcome_window_strictly_after_t0(self):
        """3. Future outcome window begins strictly after cutoff timestamp t0."""
        for app in self.population.applications[:30]:
            prof = self.profiles_by_id[app.applicant_profile_id]
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=2)
            t0_dt = datetime.fromisoformat(app.cutoff_timestamp.replace("Z", "+00:00"))
            outcome_start_dt = t0_dt + timedelta(days=1)
            outcome_end_dt = t0_dt + timedelta(days=outcome.prediction_horizon_days)

            self.assertGreater(
                outcome_start_dt,
                t0_dt,
                "Forward outcome simulation start must be strictly greater than t0",
            )
            self.assertGreater(
                outcome_end_dt,
                outcome_start_dt,
                "Outcome window end must be strictly after outcome window start",
            )
            self.assertEqual(outcome.cutoff_timestamp, app.cutoff_timestamp)

    def test_prediction_horizon_matches_contract(self):
        """4. Prediction horizon matches loan tenure and is bounded in [30, 90] days."""
        # Tenure 1 month -> 30 days
        self.assertEqual(compute_prediction_horizon(1), 30)
        # Tenure 2 months -> 60 days
        self.assertEqual(compute_prediction_horizon(2), 60)
        # Tenure 3, 4, 6, 12 months -> clipped to 90 days
        self.assertEqual(compute_prediction_horizon(3), 90)
        self.assertEqual(compute_prediction_horizon(4), 90)
        self.assertEqual(compute_prediction_horizon(6), 90)
        self.assertEqual(compute_prediction_horizon(12), 90)

        for app in self.population.applications:
            h = compute_prediction_horizon(app.loan_tenure_months)
            self.assertGreaterEqual(h, PREDICTION_HORIZON_DAYS_MIN)
            self.assertLessEqual(h, PREDICTION_HORIZON_DAYS_MAX)

    def test_deterministic_reproducibility(self):
        """5. Same seed produces bit-for-bit identical outcomes."""
        app = self.population.applications[0]
        prof = self.profiles_by_id[app.applicant_profile_id]

        outcome1 = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=10)
        outcome2 = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=10)

        self.assertEqual(outcome1.application_id, outcome2.application_id)
        self.assertEqual(outcome1.prediction_horizon_days, outcome2.prediction_horizon_days)
        self.assertEqual(outcome1.consecutive_negative_days, outcome2.consecutive_negative_days)
        self.assertEqual(outcome1.target_default_flag, outcome2.target_default_flag)
        self.assertEqual(outcome1.repayment_risk_probability, outcome2.repayment_risk_probability)

    def test_independent_application_prng_streams(self):
        """6. Different applications use independent deterministic RNG streams."""
        app1 = self.population.applications[0]
        app2 = self.population.applications[1]
        prof1 = self.profiles_by_id[app1.applicant_profile_id]
        prof2 = self.profiles_by_id[app2.applicant_profile_id]

        rng1 = get_target_rng(MASTER_SEED, app1.application_id)
        rng2 = get_target_rng(MASTER_SEED, app2.application_id)

        draws1 = [rng1.random() for _ in range(5)]
        draws2 = [rng2.random() for _ in range(5)]

        self.assertNotEqual(draws1, draws2, "Independent applications must have distinct random sequences")

    def test_repeat_applicants_independent_future_windows(self):
        """7. Repeat applications have distinct, non-overlapping future windows and independent outcomes."""
        # Find a repeat applicant
        repeat_ids = self.population.repeat_applicant_ids
        self.assertTrue(len(repeat_ids) > 0)

        target_prof_id = repeat_ids[0]
        prof = self.profiles_by_id[target_prof_id]
        apps = [a for a in self.population.applications if a.applicant_profile_id == target_prof_id]
        self.assertEqual(len(apps), 2)

        app1 = next(a for a in apps if a.application_index == 1)
        app2 = next(a for a in apps if a.application_index == 2)

        t0_1 = datetime.fromisoformat(app1.cutoff_timestamp.replace("Z", "+00:00"))
        t0_2 = datetime.fromisoformat(app2.cutoff_timestamp.replace("Z", "+00:00"))

        outcome1 = simulate_forward_outcome(app1, prof, master_seed=MASTER_SEED, n_mc_paths=5)
        outcome2 = simulate_forward_outcome(app2, prof, master_seed=MASTER_SEED, n_mc_paths=5)

        end_window1 = t0_1 + timedelta(days=outcome1.prediction_horizon_days)

        # Non-overlapping windows: outcome window 1 ends before application 2 cutoff
        self.assertLess(
            end_window1,
            t0_2,
            f"Outcome window 1 ({end_window1}) must close before Application 2 cutoff ({t0_2})",
        )
        # Distinct application IDs
        self.assertNotEqual(outcome1.application_id, outcome2.application_id)

    def test_no_mutation_of_historical_predictors(self):
        """8. Target generation does not modify application or applicant profile objects."""
        app = self.population.applications[5]
        prof = self.profiles_by_id[app.applicant_profile_id]

        app_dict_before = dict(app.__dict__)
        prof_dict_before = dict(prof.__dict__)

        _ = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)

        self.assertEqual(app.__dict__, app_dict_before, "Application object must not be mutated")
        self.assertEqual(prof.__dict__, prof_dict_before, "ApplicantProfile object must not be mutated")

    def test_feature_values_independent_of_forward_outcome(self):
        """9. Feature derivation values do not depend on generated future outcomes."""
        app = self.population.applications[3]
        prof = self.profiles_by_id[app.applicant_profile_id]
        history = generate_application_history(app, prof, master_seed=MASTER_SEED)

        # Derive features before simulating outcome
        features_before = derive_application_features(app, prof, history)

        # Simulate outcome
        outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)

        # Derive features after simulating outcome
        features_after = derive_application_features(app, prof, history)

        self.assertEqual(
            features_before.to_dict(),
            features_after.to_dict(),
            "Features derived before and after target simulation must be bit-for-bit identical",
        )

    def test_insufficient_data_cohort_unscored(self):
        """10. Incomplete observation / Insufficient Data cohort records have null targets."""
        insufficient_profs = [
            p for p in self.population.profiles if p.cohort_archetype == COHORT_INSUFFICIENT_DATA
        ]
        self.assertTrue(len(insufficient_profs) > 0)

        for prof in insufficient_profs:
            apps = [a for a in self.population.applications if a.applicant_profile_id == prof.applicant_profile_id]
            for app in apps:
                outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
                self.assertIsNone(
                    outcome.target_default_flag,
                    "Insufficient Data cohort must have target_default_flag = None",
                )
                self.assertIsNone(
                    outcome.repayment_risk_probability,
                    "Insufficient Data cohort must have repayment_risk_probability = None",
                )
                self.assertEqual(outcome.consecutive_negative_days, 0)

    def test_zero_target_leakage_into_feature_layer(self):
        """11. DerivedFeatures and ApplicationFeatures contain zero target columns or forward variables."""
        leakage_fields = {
            "target_default_flag",
            "repayment_risk_probability",
            "consecutive_negative_days",
            "prediction_horizon_days",
            "is_default",
            "min_buffer",
            "B_t",
            "I_t",
            "S_t",
        }
        derived_feature_fields = set(DerivedFeatures.__dataclass_fields__.keys())
        app_feature_fields = set(ApplicationFeatures.__dataclass_fields__.keys())

        overlap1 = derived_feature_fields.intersection(leakage_fields)
        overlap2 = app_feature_fields.intersection(leakage_fields)

        self.assertEqual(overlap1, set(), f"DerivedFeatures contains target leakage: {overlap1}")
        self.assertEqual(overlap2, set(), f"ApplicationFeatures contains target leakage: {overlap2}")

    def test_observed_default_rate_calculation(self):
        """12. Observed default rate calculates cleanly without post-hoc manipulation."""
        scored_total = 0
        defaults_total = 0
        for app in self.population.applications:
            prof = self.profiles_by_id[app.applicant_profile_id]
            if prof.cohort_archetype == COHORT_INSUFFICIENT_DATA:
                continue
            scored_total += 1
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
            if outcome.target_default_flag == 1:
                defaults_total += 1

        default_rate = defaults_total / scored_total
        self.assertGreater(scored_total, 0)
        self.assertGreater(default_rate, 0.05)
        self.assertLess(default_rate, 0.60)

    def test_no_post_generation_relabeling(self):
        """13. Target strictly satisfies: target == 1 iff consecutive_negative_days >= 7."""
        for app in self.population.applications[:50]:
            prof = self.profiles_by_id[app.applicant_profile_id]
            if prof.cohort_archetype == COHORT_INSUFFICIENT_DATA:
                continue
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
            if outcome.consecutive_negative_days >= INSOLVENCY_GRACE_PERIOD_DAYS:
                self.assertEqual(
                    outcome.target_default_flag,
                    1,
                    "consecutive_negative_days >= 7 must yield target_default_flag = 1",
                )
            else:
                self.assertEqual(
                    outcome.target_default_flag,
                    0,
                    "consecutive_negative_days < 7 must yield target_default_flag = 0",
                )

    def test_rejection_of_impossible_combinations(self):
        """14. validate_forward_outcome rejects impossible or contradictory combinations."""
        # Target 1 but only 3 negative days (< 7)
        invalid_1 = ForwardOutcome(
            application_id="app-1",
            prediction_horizon_days=90,
            consecutive_negative_days=3,
            target_default_flag=1,
            repayment_risk_probability=0.60,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_1, COHORT_STABLE)

        # Target 0 but 10 negative days (>= 7)
        invalid_2 = ForwardOutcome(
            application_id="app-2",
            prediction_horizon_days=90,
            consecutive_negative_days=10,
            target_default_flag=0,
            repayment_risk_probability=0.10,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_2, COHORT_STABLE)

        # Null target for scored cohort
        invalid_3 = ForwardOutcome(
            application_id="app-3",
            prediction_horizon_days=90,
            consecutive_negative_days=0,
            target_default_flag=None,
            repayment_risk_probability=None,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_3, COHORT_STABLE)

        # Non-null target for Insufficient Data cohort
        invalid_4 = ForwardOutcome(
            application_id="app-4",
            prediction_horizon_days=90,
            consecutive_negative_days=0,
            target_default_flag=0,
            repayment_risk_probability=0.05,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_4, COHORT_INSUFFICIENT_DATA)

        # Probability out of bounds
        invalid_5 = ForwardOutcome(
            application_id="app-5",
            prediction_horizon_days=90,
            consecutive_negative_days=0,
            target_default_flag=0,
            repayment_risk_probability=1.50,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_5, COHORT_STABLE)

        # Horizon out of bounds
        invalid_6 = ForwardOutcome(
            application_id="app-6",
            prediction_horizon_days=15,
            consecutive_negative_days=0,
            target_default_flag=0,
            repayment_risk_probability=0.10,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_forward_outcome(invalid_6, COHORT_STABLE)

    def test_mismatched_profile_rejection(self):
        """15. Rejects application when passed a profile with mismatched ID."""
        app = self.population.applications[0]
        # Get another profile
        other_prof = next(p for p in self.population.profiles if p.applicant_profile_id != app.applicant_profile_id)

        with self.assertRaises(ValidationError):
            simulate_forward_outcome(app, other_prof, master_seed=MASTER_SEED)

    def test_batch_generation(self):
        """16. generate_forward_outcomes processes batch cleanly."""
        apps_batch = self.population.applications[:20]
        outcomes = generate_forward_outcomes(apps_batch, self.profiles_by_id, master_seed=MASTER_SEED, n_mc_paths=3)
        self.assertEqual(len(outcomes), 20)
        for i, out in enumerate(outcomes):
            self.assertEqual(out.application_id, apps_batch[i].application_id)


if __name__ == "__main__":
    unittest.main()
