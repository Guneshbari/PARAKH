"""
Unit and Integration Tests for Dataset Validation & Leakage Checks (P2-T09).
Covers all 20 required validation test areas:
1. Schema validation.
2. Missing-column detection.
3. Unexpected-column detection.
4. Invalid-type detection.
5. Duplicate application detection.
6. Invalid applicant relationship detection.
7. Invalid cohort detection.
8. Invalid feature range detection.
9. Invalid categorical-value detection.
10. Invalid target detection.
11. Invalid temporal relationship detection.
12. Post-t0 leakage detection.
13. Future-target leakage detection.
14. Application-isolation validation.
15. Missingness validation.
16. Impossible-combination detection.
17. Cohort distribution reporting.
18. Default-rate reporting.
19. Determinism validation.
20. Valid dataset passes all validators.
"""

from datetime import datetime, timezone, timedelta
import unittest
from typing import Dict, List

from src.data.synthetic.config import (
    MASTER_SEED,
    COHORT_ARCHETYPES,
    COHORT_INSUFFICIENT_DATA,
    COHORT_STABLE,
    REPEAT_INTERVAL_DAYS_MIN,
)
from src.data.synthetic.exceptions import (
    CohortValidationError,
    FeatureRangeError,
    IdentityValidationError,
    ImpossibleCombinationError,
    MissingnessViolationError,
    ReproducibilityError,
    SchemaError,
    TargetValidationError,
    TemporalLeakageError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    ApplicationHistoricalData,
    DerivedFeatures,
    ForwardOutcome,
    AssembledApplicationRecord,
    FINAL_DATASET_SCHEMA,
    get_column_names,
)
from src.data.synthetic.random_state import RandomStateManager
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.telemetry_generator import (
    generate_application_history,
    DailyActivityEvent,
    WeeklyPayoutEvent,
)
from src.data.synthetic.feature_derivation import derive_application_features
from src.data.synthetic.target_generator import simulate_forward_outcome
from src.data.synthetic.assembly import assemble_dataset
from src.data.synthetic.validators import (
    ValidationErrorDetail,
    DatasetValidationReport,
    validate_record_schema,
    validate_identities_and_relations,
    validate_cohort_distribution,
    validate_feature_semantics,
    validate_target_semantics,
    validate_temporal_distribution,
    validate_impossible_combinations,
    validate_missingness,
    validate_leakage_suite,
    validate_determinism,
    validate_dataset,
    validate_dataset_strict,
)


class TestValidators(unittest.TestCase):
    """Exhaustive test suite for dataset validation and leakage detection (P2-T09)."""

    @classmethod
    def setUpClass(cls):
        """Generate small deterministic fixture (50 applicants, 10 repeats, 60 applications)."""
        cls.population = generate_population(RandomStateManager(MASTER_SEED), n_applicants=50, n_repeats=10)
        cls.profiles = {p.applicant_profile_id: p for p in cls.population.profiles}
        cls.features: Dict[str, ApplicationFeatures] = {}
        cls.outcomes: Dict[str, ForwardOutcome] = {}
        cls.histories: Dict[str, ApplicationHistoricalData] = {}

        for app in cls.population.applications:
            prof = cls.profiles[app.applicant_profile_id]
            history = generate_application_history(app, prof, master_seed=MASTER_SEED)
            cls.histories[app.application_id] = history
            feat = derive_application_features(app, prof, history)
            cls.features[app.application_id] = feat
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
            cls.outcomes[app.application_id] = outcome

        cls.assembled_records = assemble_dataset(
            applications=cls.population.applications,
            profiles=cls.profiles,
            features=cls.features,
            outcomes=cls.outcomes,
            deterministic_sort=True,
        )

    # ==========================================================================
    # 1. SCHEMA VALIDATION
    # ==========================================================================

    def test_01_schema_validation_valid_record(self):
        """1. Schema validation succeeds with 0 errors on valid record."""
        rec = self.assembled_records[0].to_dict()
        errors = validate_record_schema(rec)
        self.assertEqual(len(errors), 0, f"Expected 0 errors on valid record, got {errors}")

    def test_02_missing_column_detection(self):
        """2. Detects missing required column."""
        rec = self.assembled_records[0].to_dict()
        del rec["feat_inc_median_90d"]
        errors = validate_record_schema(rec)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("feat_inc_median_90d" in e.message for e in errors))

    def test_03_unexpected_column_detection(self):
        """3. Detects unexpected column."""
        rec = self.assembled_records[0].to_dict()
        rec["unapproved_secret_metric"] = 123.45
        errors = validate_record_schema(rec)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("unapproved_secret_metric" in e.message for e in errors))

    def test_04_invalid_type_detection(self):
        """4. Detects invalid column data type."""
        # A. String where float expected
        rec1 = self.assembled_records[0].to_dict()
        rec1["requested_loan_amount"] = "twenty_thousand"
        errs1 = validate_record_schema(rec1)
        self.assertTrue(any("requested_loan_amount" in e.message for e in errs1))

        # B. Bool where int expected (bool is subclass of int in Python)
        rec2 = self.assembled_records[0].to_dict()
        rec2["loan_tenure_months"] = True
        errs2 = validate_record_schema(rec2)
        self.assertTrue(any("loan_tenure_months" in e.message for e in errs2))

    # ==========================================================================
    # 2. IDENTITY / RELATIONAL VALIDATION
    # ==========================================================================

    def test_05_duplicate_application_detection(self):
        """5. Detects duplicate application_id in dataset."""
        dupe_records = list(self.assembled_records) + [self.assembled_records[0]]
        errors = validate_identities_and_relations(dupe_records)
        self.assertTrue(any("Duplicate application_id detected" in e.message for e in errors))

    def test_06_invalid_applicant_relationship_detection(self):
        """6. Detects invalid or mismatched applicant_profile_id."""
        rec = self.assembled_records[0].to_dict()
        rec["applicant_profile_id"] = "not-a-valid-uuid"
        errors = validate_identities_and_relations([rec])
        self.assertTrue(any("not a valid UUIDv4" in e.message for e in errors))

    # ==========================================================================
    # 3. COHORT VALIDATION
    # ==========================================================================

    def test_07_invalid_cohort_detection(self):
        """7. Detects unrecognized cohort_archetype."""
        rec = self.assembled_records[0].to_dict()
        rec["cohort_archetype"] = "Super Prime"
        counts, props, errors = validate_cohort_distribution([rec], enforce_proportions=False)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Invalid cohort_archetype 'Super Prime'" in e.message for e in errors))

    # ==========================================================================
    # 4. FEATURE & CATEGORICAL VALIDATION
    # ==========================================================================

    def test_08_invalid_feature_range_detection(self):
        """8. Detects feature out of physical/contractual bounds."""
        rec = self.assembled_records[0].to_dict()
        rec["feat_inc_cv_90d"] = 9.99  # Allowed [0.0, 5.0]
        stats, cats, errors = validate_feature_semantics([rec])
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("feat_inc_cv_90d" in e.message and "out of bounds" in e.message for e in errors))

    def test_09_invalid_categorical_value_detection(self):
        """9. Detects unexpected categorical domain value."""
        rec = self.assembled_records[0].to_dict()
        rec["gig_work_type"] = "ASTRONAUT_PILOT"
        stats, cats, errors = validate_feature_semantics([rec])
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("gig_work_type" in e.message and "unexpected value" in e.message for e in errors))

    # ==========================================================================
    # 5. TARGET VALIDATION
    # ==========================================================================

    def test_10_invalid_target_detection(self):
        """10. Detects invalid target values and scored vs unscored violations."""
        # A. Non-binary target
        rec1 = self.assembled_records[0].to_dict()
        rec1["cohort_archetype"] = COHORT_STABLE
        rec1["target_default_flag"] = 3
        summary1, errs1, warns1 = validate_target_semantics([rec1])
        self.assertTrue(any("Invalid target_default_flag value: 3" in e.message for e in errs1))

        # B. Non-null target on Insufficient Data cohort
        rec2 = self.assembled_records[0].to_dict()
        rec2["cohort_archetype"] = COHORT_INSUFFICIENT_DATA
        rec2["target_default_flag"] = 1
        summary2, errs2, warns2 = validate_target_semantics([rec2])
        self.assertTrue(any("Insufficient Data cohort record has non-null target_default_flag" in e.message for e in errs2))

    # ==========================================================================
    # 6. TEMPORAL VALIDATION
    # ==========================================================================

    def test_11_invalid_temporal_relationship_detection(self):
        """11. Detects repeat applicant spacing violation (< 120 days)."""
        app1 = self.assembled_records[0].to_dict()
        app2 = self.assembled_records[1].to_dict()
        # Set same applicant profile ID with only 10-day separation
        app2["applicant_profile_id"] = app1["applicant_profile_id"]
        t1 = datetime.fromisoformat(app1["cutoff_timestamp"].replace("Z", "+00:00"))
        t2 = t1 + timedelta(days=10)
        app2["cutoff_timestamp"] = t2.isoformat().replace("+00:00", "Z")

        summary, errors = validate_temporal_distribution([app1, app2])
        self.assertGreater(len(errors), 0)
        self.assertTrue(any(f"violating minimum requirement of {REPEAT_INTERVAL_DAYS_MIN} days" in e.message for e in errors))

    # ==========================================================================
    # 7. LEAKAGE VALIDATION
    # ==========================================================================

    def test_12_post_t0_leakage_detection(self):
        """12. Verifies post-t0 event leakage test rejects event at or after t0."""
        passed, summary, errors = validate_leakage_suite(n_sample_apps=3)
        self.assertTrue(summary["test_results"]["test_a_post_t0_event"])

    def test_13_future_target_leakage_detection(self):
        """13. Verifies derived features are invariant to future outcome simulator runs."""
        passed, summary, errors = validate_leakage_suite(n_sample_apps=3)
        self.assertTrue(summary["test_results"]["test_b_future_target"])
        self.assertTrue(summary["test_results"]["test_c_target_in_feature"])

    def test_14_application_isolation_validation(self):
        """14. Verifies modifying Application A does not alter Application B features or outcomes."""
        passed, summary, errors = validate_leakage_suite(n_sample_apps=3)
        self.assertTrue(summary["test_results"]["test_e_application_isolation"])

    # ==========================================================================
    # 8. MISSINGNESS & IMPOSSIBLE COMBINATIONS
    # ==========================================================================

    def test_15_missingness_validation(self):
        """15. Detects null in non-nullable column while permitting null in nullable column."""
        # Non-nullable field set to None
        rec1 = self.assembled_records[0].to_dict()
        rec1["feat_act_active_days_ratio"] = None
        counts1, ratios1, errs1 = validate_missingness([rec1])
        self.assertTrue(any("feat_act_active_days_ratio" in e.message for e in errs1))

        # Nullable field set to None
        rec2 = self.assembled_records[0].to_dict()
        rec2["years_working"] = None
        counts2, ratios2, errs2 = validate_missingness([rec2])
        self.assertEqual(len(errs2), 0)

    def test_16_impossible_combination_detection(self):
        """16. Detects physically impossible combinations defined in contract Section 5.2."""
        rec = self.assembled_records[0].to_dict()
        rec["feat_act_active_days_ratio"] = 0.0
        rec["feat_inc_median_90d"] = 8000.0  # Positive income with zero work
        errors = validate_impossible_combinations([rec])
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Positive income" in e.message and "zero active days" in e.message for e in errors))

    # ==========================================================================
    # 9. REPORTING & DETERMINISM
    # ==========================================================================

    def test_17_cohort_distribution_reporting(self):
        """17. Validates that cohort distribution reports all 6 cohorts."""
        counts, props, errors = validate_cohort_distribution(self.assembled_records, enforce_proportions=False)
        self.assertEqual(len(counts), 6)
        self.assertEqual(sum(counts.values()), len(self.assembled_records))

    def test_18_default_rate_reporting(self):
        """18. Validates faithful reporting of default rate without post-hoc manipulation."""
        summary, errors, warnings = validate_target_semantics(self.assembled_records)
        self.assertIn("scored_count", summary)
        self.assertIn("default_count", summary)
        self.assertIn("default_rate", summary)
        self.assertGreater(summary["scored_count"], 0)
        expected_rate = summary["default_count"] / summary["scored_count"]
        self.assertAlmostEqual(summary["default_rate"], expected_rate, places=4)

    def test_19_determinism_validation(self):
        """19. Verifies end-to-end determinism validation."""
        passed, msg, errors = validate_determinism(master_seed=MASTER_SEED, n_sample_applicants=10)
        self.assertTrue(passed, f"Determinism validation failed: {msg}")
        self.assertEqual(len(errors), 0)

    def test_20_valid_dataset_passes_all_validators(self):
        """20. Valid dataset passes all validators with overall_status PASS."""
        report = validate_dataset(
            records=self.assembled_records,
            applications=self.population.applications,
            profiles=self.profiles,
            histories=self.histories,
            outcomes=self.outcomes,
            run_leakage_tests=True,
            run_determinism_test=True,
            enforce_proportions=False,  # Sample size is 50 applicants, not 10k
        )
        self.assertEqual(report.overall_status, "PASS")
        self.assertEqual(len(report.validation_errors), 0)
        self.assertEqual(report.row_count, 60)
        self.assertTrue(report.leakage_checks["passed"])
        self.assertTrue(report.determinism_result["passed"])

        # Also test validate_dataset_strict
        strict_report = validate_dataset_strict(
            records=self.assembled_records,
            applications=self.population.applications,
            profiles=self.profiles,
            histories=self.histories,
            outcomes=self.outcomes,
            run_leakage_tests=False,
            run_determinism_test=False,
            enforce_proportions=False,
        )
        self.assertEqual(strict_report.overall_status, "PASS")


if __name__ == "__main__":
    unittest.main()
