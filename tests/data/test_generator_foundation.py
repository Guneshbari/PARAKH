"""
PARAKH Synthetic Data Generator - Foundation Test Suite
Verifies:
- Seed reproducibility and independent substream isolation
- Configuration consistency and mathematical invariants
- Schema column count, exact names, and categorical classification
- Exception hierarchy
"""

import math
import unittest

from src.data.synthetic.config import (
    MASTER_SEED,
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
    REPEAT_APPLICANTS,
    SINGLE_APPLICANTS,
    APPLICATIONS_PER_REPEAT,
    COHORT_PROPORTIONS,
    GIG_WORK_TYPE_PROPORTIONS,
    LOAN_PURPOSE_PROPORTIONS,
    LOAN_TENURE_PROPORTIONS,
    EMI_ANNUAL_FIXED_RATE,
    EMI_MONTHLY_RATE,
    OBSERVATION_WINDOW_DAYS,
    PREDICTION_HORIZON_DAYS_MIN,
    PREDICTION_HORIZON_DAYS_MAX,
    REPEAT_INTERVAL_DAYS_MIN,
    REPEAT_INTERVAL_DAYS_MAX,
    LIVING_EXPENSE_MONTHLY_MIN,
    LIVING_EXPENSE_MONTHLY_MAX,
    FORWARD_EARNINGS_AR_ALPHA,
    CANONICAL_OUTPUT_PATH,
    calculate_contractual_emi,
    validate_config,
)
from src.data.synthetic.random_state import (
    RandomStateManager,
    Substream,
)
from src.data.synthetic.schemas import (
    Applicant,
    ApplicantProfile,
    Application,
    HistoricalTelemetry,
    DerivedFeatures,
    ForwardOutcome,
    FinalRecord,
    ColumnCategory,
    DataType,
    FINAL_DATASET_SCHEMA,
    get_column_names,
    get_metadata_columns,
    get_raw_profile_columns,
    get_raw_loan_columns,
    get_derived_feature_columns,
    get_target_columns,
    get_feature_matrix_columns,
    get_excluded_columns,
    get_mandatory_feature_columns,
    get_optional_feature_columns,
    get_interaction_feature_columns,
    validate_schema_counts,
)
from src.data.synthetic.exceptions import (
    GeneratorError,
    ConfigurationError,
    SchemaError,
    ValidationError,
    TemporalLeakageError,
    ImpossibleCombinationError,
    MissingnessViolationError,
    ReproducibilityError,
)


class TestConfiguration(unittest.TestCase):
    """Verifies frozen configuration invariants."""

    def test_config_self_validation(self):
        """validate_config() should pass without error."""
        self.assertTrue(validate_config())

    def test_sizing_invariants(self):
        """Verify applicant and application sizing algebra."""
        self.assertEqual(TOTAL_APPLICATIONS, 12000)
        self.assertEqual(UNIQUE_APPLICANTS, 10000)
        self.assertEqual(REPEAT_APPLICANTS, 2000)
        self.assertEqual(SINGLE_APPLICANTS, 8000)
        self.assertEqual(APPLICATIONS_PER_REPEAT, 2)
        # 8,000 single + 2,000 repeat * 2 = 12,000 applications
        self.assertEqual(
            SINGLE_APPLICANTS * 1 + REPEAT_APPLICANTS * APPLICATIONS_PER_REPEAT,
            TOTAL_APPLICATIONS,
        )

    def test_proportion_sums(self):
        """All categorical distributions must sum exactly to 1.0."""
        self.assertAlmostEqual(sum(COHORT_PROPORTIONS.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(GIG_WORK_TYPE_PROPORTIONS.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(LOAN_PURPOSE_PROPORTIONS.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(LOAN_TENURE_PROPORTIONS.values()), 1.0, places=6)

    def test_temporal_invariants(self):
        """Verify temporal bounds match frozen specification."""
        self.assertEqual(OBSERVATION_WINDOW_DAYS, 90)
        self.assertEqual(PREDICTION_HORIZON_DAYS_MIN, 30)
        self.assertEqual(PREDICTION_HORIZON_DAYS_MAX, 90)
        self.assertEqual(REPEAT_INTERVAL_DAYS_MIN, 120)
        self.assertEqual(REPEAT_INTERVAL_DAYS_MAX, 270)

    def test_emi_formula(self):
        """Verify reducing-balance EMI formula calculation."""
        # For a loan of 10,000 over 1 month at 1.5% monthly: EMI = 10000 * 1.015 = 10150
        emi_1m = calculate_contractual_emi(10000.0, 1)
        self.assertAlmostEqual(emi_1m, 10150.0, places=2)

        # For loan of 12,000 over 3 months at 1.5% monthly:
        # factor = 1.015^3 = 1.045678375
        # EMI = 12000 * 0.015 * factor / (factor - 1) = 4120.60
        emi_3m = calculate_contractual_emi(12000.0, 3)
        self.assertAlmostEqual(emi_3m, 4120.60, places=2)

        # Edge cases
        self.assertEqual(calculate_contractual_emi(0.0, 3), 0.0)
        with self.assertRaises(ValueError):
            calculate_contractual_emi(10000.0, 0)


class TestRandomState(unittest.TestCase):
    """Verifies deterministic random substream management."""

    def test_master_seed_reproducibility(self):
        """Two independent RandomStateManager instances with seed 42 produce identical draws."""
        r1 = RandomStateManager(MASTER_SEED)
        r2 = RandomStateManager(MASTER_SEED)

        for substream in Substream:
            draws_1 = [r1.get_stream(substream).random() for _ in range(20)]
            draws_2 = [r2.get_stream(substream).random() for _ in range(20)]
            self.assertEqual(
                draws_1,
                draws_2,
                f"Substream {substream.value} was not identical across instances",
            )

    def test_substream_isolation(self):
        """Drawing from one substream must not perturb another substream."""
        r_isolated = RandomStateManager(42)
        r_perturbed = RandomStateManager(42)

        # Perturb 'cohorts' substream heavily in r_perturbed
        _ = [r_perturbed.get_stream(Substream.COHORTS).random() for _ in range(100)]

        # 'applicants' substream in both must remain completely identical
        draws_iso = [r_isolated.get_stream(Substream.APPLICANTS).random() for _ in range(20)]
        draws_pert = [r_perturbed.get_stream(Substream.APPLICANTS).random() for _ in range(20)]
        self.assertEqual(draws_iso, draws_pert)

    def test_different_seeds_produce_different_sequences(self):
        """Seed 42 and Seed 99 must produce distinct values."""
        r1 = RandomStateManager(42)
        r2 = RandomStateManager(99)

        draws_1 = [r1.get_stream(Substream.APPLICANTS).random() for _ in range(10)]
        draws_2 = [r2.get_stream(Substream.APPLICANTS).random() for _ in range(10)]
        self.assertNotEqual(draws_1, draws_2)

    def test_applicant_seed_spawning(self):
        """spawn_applicant_seeds produces distinct, reproducible seeds."""
        r1 = RandomStateManager(42)
        r2 = RandomStateManager(42)

        seeds_1 = r1.spawn_applicant_seeds(100)
        seeds_2 = r2.spawn_applicant_seeds(100)

        self.assertEqual(len(seeds_1), 100)
        self.assertEqual(seeds_1, seeds_2)
        # Seeds must be distinct across applicants
        self.assertEqual(len(set(seeds_1)), 100)

    def test_reset(self):
        """reset() must restore substreams to initial state."""
        r = RandomStateManager(42)
        first_draws = [r.get_stream(Substream.PROFILES).random() for _ in range(10)]
        r.reset()
        reset_draws = [r.get_stream(Substream.PROFILES).random() for _ in range(10)]
        self.assertEqual(first_draws, reset_draws)


class TestSchemas(unittest.TestCase):
    """Verifies schema column counts, exact names, and dataclasses."""

    def test_schema_counts(self):
        """Verify exact schema column partition counts."""
        counts = validate_schema_counts()
        self.assertEqual(counts["total_columns"], 52)
        self.assertEqual(counts["metadata_columns"], 4)
        self.assertEqual(counts["raw_profile_columns"], 3)
        self.assertEqual(counts["raw_loan_columns"], 3)
        self.assertEqual(counts["derived_feature_columns"], 40)
        self.assertEqual(counts["target_columns"], 2)
        self.assertEqual(counts["feature_matrix_columns"], 46)
        self.assertEqual(counts["excluded_columns"], 6)
        self.assertEqual(counts["mandatory_core_features"], 19)
        self.assertEqual(counts["optional_derived_features"], 17)
        self.assertEqual(counts["interaction_features"], 4)

    def test_exact_column_names_match_contract(self):
        """Verify all 52 column names match Section 15.1 and Section 21."""
        expected_columns = [
            # Metadata (4)
            "applicant_profile_id", "application_id", "cutoff_timestamp", "cohort_archetype",
            # Raw Profile (3)
            "gig_work_type", "years_working", "average_working_days",
            # Raw Loan (3)
            "requested_loan_amount", "loan_tenure_months", "loan_purpose",
            # Mandatory Derived Features (19)
            "feat_inc_median_90d", "feat_inc_p25_90d", "feat_inc_cv_90d", "feat_inc_downside_var",
            "feat_trend_slope_90d", "feat_trend_momentum_30_90", "feat_act_active_days_ratio",
            "feat_act_zero_earn_weeks", "feat_rec_bounceback_ratio", "feat_rec_days_to_recover",
            "feat_liq_buffer_to_loan", "feat_liq_burn_months", "feat_bur_dti_ratio",
            "feat_bur_installment_dti", "feat_bur_total_dti", "feat_suf_observed_days",
            "feat_suf_payout_count", "feat_suf_group_count", "feat_suf_missing_ratio",
            # Optional Derived Features (17)
            "feat_inc_mean_90d", "feat_inc_trimmed_mean", "feat_inc_iqr_ratio",
            "feat_inc_min_max_ratio", "feat_trend_consec_drops", "feat_act_max_idle_streak",
            "feat_act_weekend_intensity", "feat_rec_max_drawdown", "feat_ten_years_working",
            "feat_ten_platform_rating", "feat_ten_trips_completed", "feat_ten_cancellation_rate",
            "feat_liq_net_margin", "feat_pay_utility_on_time", "feat_pay_max_bill_delay",
            "feat_pay_repay_reliability", "feat_bur_loan_to_income",
            # Interaction Terms (4)
            "feat_int_vol_x_recovery", "feat_int_vol_x_buffer", "feat_int_trend_x_dti",
            "feat_int_resilience_idx",
            # Targets (2)
            "target_default_flag", "repayment_risk_probability",
        ]
        actual_columns = get_column_names()
        self.assertEqual(actual_columns, expected_columns)
        self.assertEqual(len(actual_columns), 52)

    def test_dataclasses_instantiation(self):
        """Intermediate dataclasses instantiate correctly with proper fields."""
        applicant = Applicant(
            applicant_profile_id="11111111-1111-4111-8111-111111111111",
            cohort_archetype="Healthy Volatile",
        )
        self.assertEqual(applicant.cohort_archetype, "Healthy Volatile")

        profile = ApplicantProfile(
            applicant_profile_id=applicant.applicant_profile_id,
            cohort_archetype=applicant.cohort_archetype,
            gig_work_type="DELIVERY",
            years_working=2.5,
            average_working_days=24,
            monthly_living_expense=14200.0,
            existing_monthly_debt=3000.0,
            starting_cashflow_buffer=15000.0,
            baseline_weekly_income=7500.0,
        )
        self.assertEqual(profile.gig_work_type, "DELIVERY")

        app = Application(
            application_id="22222222-2222-4222-8222-222222222222",
            applicant_profile_id=applicant.applicant_profile_id,
            application_index=1,
            cutoff_timestamp="2025-06-15T10:00:00Z",
            requested_loan_amount=20000.0,
            loan_tenure_months=3,
            loan_purpose="VEHICLE_MAINTENANCE",
            contractual_emi=6867.92,
            daily_debt_obligation=328.93,
        )
        self.assertEqual(app.requested_loan_amount, 20000.0)

        outcome = ForwardOutcome(
            application_id=app.application_id,
            prediction_horizon_days=90,
            consecutive_negative_days=0,
            target_default_flag=0,
            repayment_risk_probability=0.045,
        )
        self.assertEqual(outcome.target_default_flag, 0)


class TestExceptions(unittest.TestCase):
    """Verifies exception inheritance hierarchy."""

    def test_exception_inheritance(self):
        """All generator exceptions must inherit from GeneratorError."""
        self.assertTrue(issubclass(ConfigurationError, GeneratorError))
        self.assertTrue(issubclass(SchemaError, GeneratorError))
        self.assertTrue(issubclass(ValidationError, GeneratorError))
        self.assertTrue(issubclass(TemporalLeakageError, ValidationError))
        self.assertTrue(issubclass(ImpossibleCombinationError, ValidationError))
        self.assertTrue(issubclass(MissingnessViolationError, ValidationError))
        self.assertTrue(issubclass(ReproducibilityError, ValidationError))


if __name__ == "__main__":
    unittest.main()
