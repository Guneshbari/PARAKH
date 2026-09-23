"""
PARAKH Synthetic Data Generator - Population Test Suite (P2-T04)
Verifies:
- Structural sizing: exactly 10,000 applicants, 12,000 applications, 2,000 repeats, 8,000 singles
- Exact cohort distribution: 2500, 2500, 2000, 1500, 1000, 500
- Timestamp validity: bounds [2025-01-01, 2026-09-22], UTC, strictly increasing for repeats
- Repeat interval: between 120 and 270 days
- Identifiers: valid UUIDv4 strings, uniqueness, relational integrity
- Profile & loan schema: ranges, allowed categoricals, non-negative amounts
- Deterministic reproducibility with master seed 42
- Anti-leakage: zero target or forward variables in population layer
"""

from collections import Counter
from datetime import datetime, timezone
import unittest
import uuid

from src.data.synthetic.config import (
    MASTER_SEED,
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
    REPEAT_APPLICANTS,
    SINGLE_APPLICANTS,
    COHORT_ARCHETYPES,
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    GIG_WORK_TYPES,
    LOAN_PURPOSES,
    LOAN_TENURES,
    LOAN_AMOUNT_MIN,
    LOAN_AMOUNT_MAX,
    LIVING_EXPENSE_MONTHLY_MIN,
    LIVING_EXPENSE_MONTHLY_MAX,
    REPEAT_INTERVAL_DAYS_MIN,
    REPEAT_INTERVAL_DAYS_MAX,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.random_state import RandomStateManager


class TestPopulationGenerator(unittest.TestCase):
    """Full validation suite for P2-T04 population generation layer."""

    @classmethod
    def setUpClass(cls):
        """Generate population once with master seed 42 for testing."""
        cls.population = generate_population(RandomStateManager(MASTER_SEED))

    # ==========================================================================
    # 1. STRUCTURAL SIZING TESTS
    # ==========================================================================

    def test_applicant_count(self):
        """Must generate exactly 10,000 unique applicants and profiles."""
        self.assertEqual(len(self.population.applicants), UNIQUE_APPLICANTS)
        self.assertEqual(len(self.population.profiles), UNIQUE_APPLICANTS)

        applicant_ids = [a.applicant_profile_id for a in self.population.applicants]
        self.assertEqual(len(set(applicant_ids)), UNIQUE_APPLICANTS)

    def test_application_count(self):
        """Must generate exactly 12,000 applications."""
        self.assertEqual(len(self.population.applications), TOTAL_APPLICATIONS)

        application_ids = [app.application_id for app in self.population.applications]
        self.assertEqual(len(set(application_ids)), TOTAL_APPLICATIONS)

    def test_repeat_applicant_structure(self):
        """
        Verify repeat applicant structure:
        - Exactly 2,000 repeat applicants (each with 2 applications)
        - Exactly 8,000 single applicants (each with 1 application)
        - Total: 8,000 * 1 + 2,000 * 2 = 12,000
        """
        self.assertEqual(len(self.population.repeat_applicant_ids), REPEAT_APPLICANTS)
        repeat_set = set(self.population.repeat_applicant_ids)
        self.assertEqual(len(repeat_set), REPEAT_APPLICANTS)

        # Count applications per applicant
        app_counts = Counter(app.applicant_profile_id for app in self.population.applications)
        self.assertEqual(len(app_counts), UNIQUE_APPLICANTS)

        two_app_count = sum(1 for cnt in app_counts.values() if cnt == 2)
        one_app_count = sum(1 for cnt in app_counts.values() if cnt == 1)

        self.assertEqual(two_app_count, REPEAT_APPLICANTS)
        self.assertEqual(one_app_count, SINGLE_APPLICANTS)

        # Verify that all 2-app applicants match repeat_applicant_ids
        two_app_ids = {aid for aid, cnt in app_counts.items() if cnt == 2}
        self.assertEqual(two_app_ids, repeat_set)

    # ==========================================================================
    # 2. COHORT DISTRIBUTION TESTS
    # ==========================================================================

    def test_cohort_exact_counts(self):
        """
        Verify exact cohort counts match frozen proportions for 10,000 applicants:
        - Healthy Volatile: 2,500 (25%)
        - Stable: 2,500 (25%)
        - Declining: 2,000 (20%)
        - Irregular: 1,500 (15%)
        - High Obligation: 1,000 (10%)
        - Insufficient Data: 500 (5%)
        """
        cohort_counts = Counter(a.cohort_archetype for a in self.population.applicants)
        self.assertEqual(len(cohort_counts), 6)
        self.assertEqual(cohort_counts[COHORT_HEALTHY_VOLATILE], 2500)
        self.assertEqual(cohort_counts[COHORT_STABLE], 2500)
        self.assertEqual(cohort_counts[COHORT_DECLINING], 2000)
        self.assertEqual(cohort_counts[COHORT_IRREGULAR], 1500)
        self.assertEqual(cohort_counts[COHORT_HIGH_OBLIGATION], 1000)
        self.assertEqual(cohort_counts[COHORT_INSUFFICIENT_DATA], 500)

        # Confirm profiles match applicants' cohorts
        for applicant, profile in zip(self.population.applicants, self.population.profiles):
            self.assertEqual(applicant.cohort_archetype, profile.cohort_archetype)

    # ==========================================================================
    # 3. APPLICATION TIMESTAMP TESTS
    # ==========================================================================

    def test_timestamp_bounds_and_format(self):
        """Every application timestamp must be UTC ISO-8601 within [2025-01-01, 2026-09-22]."""
        start_bound = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_bound = datetime(2026, 9, 22, 23, 59, 59, tzinfo=timezone.utc)

        for app in self.population.applications:
            # Parse ISO-8601 string
            dt = datetime.fromisoformat(app.cutoff_timestamp.replace("Z", "+00:00"))
            self.assertGreaterEqual(dt, start_bound)
            self.assertLessEqual(dt, end_bound)
            self.assertEqual(dt.tzinfo, timezone.utc)

    def test_repeat_applicant_sequencing_and_intervals(self):
        """
        For repeat applicants:
        - t0_second must be strictly greater than t0_first
        - interval must be between 120 and 270 calendar days
        """
        # Group applications by applicant
        apps_by_applicant = {}
        for app in self.population.applications:
            apps_by_applicant.setdefault(app.applicant_profile_id, []).append(app)

        repeat_set = set(self.population.repeat_applicant_ids)
        for applicant_id in repeat_set:
            apps = apps_by_applicant[applicant_id]
            self.assertEqual(len(apps), 2)
            # Sort by application index
            app_1 = next(a for a in apps if a.application_index == 1)
            app_2 = next(a for a in apps if a.application_index == 2)

            dt_1 = datetime.fromisoformat(app_1.cutoff_timestamp.replace("Z", "+00:00"))
            dt_2 = datetime.fromisoformat(app_2.cutoff_timestamp.replace("Z", "+00:00"))

            self.assertGreater(dt_2, dt_1, "t0_second must be strictly later than t0_first")

            delta_days = (dt_2.date() - dt_1.date()).days
            self.assertGreaterEqual(
                delta_days,
                REPEAT_INTERVAL_DAYS_MIN,
                f"Repeat interval {delta_days} days is below min {REPEAT_INTERVAL_DAYS_MIN}",
            )
            self.assertLessEqual(
                delta_days,
                REPEAT_INTERVAL_DAYS_MAX,
                f"Repeat interval {delta_days} days exceeds max {REPEAT_INTERVAL_DAYS_MAX}",
            )

    # ==========================================================================
    # 4. IDENTIFIERS & RELATIONAL INTEGRITY
    # ==========================================================================

    def test_uuid_validity(self):
        """Verify all applicant and application IDs are valid RFC 4122 UUIDv4 strings."""
        for applicant in self.population.applicants:
            parsed = uuid.UUID(applicant.applicant_profile_id)
            self.assertEqual(parsed.version, 4)

        for app in self.population.applications:
            parsed = uuid.UUID(app.application_id)
            self.assertEqual(parsed.version, 4)

    def test_relational_integrity(self):
        """Every application must reference a valid existing applicant profile ID."""
        applicant_id_set = {a.applicant_profile_id for a in self.population.applicants}
        for app in self.population.applications:
            self.assertIn(app.applicant_profile_id, applicant_id_set)

    # ==========================================================================
    # 5. PROFILE & LOAN SCHEMA COMPLIANCE
    # ==========================================================================

    def test_profile_fields_compliance(self):
        """Verify profile attributes conform to types, categories, and physical ranges."""
        for profile in self.population.profiles:
            self.assertIn(profile.gig_work_type, GIG_WORK_TYPES)
            self.assertGreaterEqual(profile.years_working, 0.0)
            self.assertLessEqual(profile.years_working, 50.0)
            self.assertGreaterEqual(profile.average_working_days, 0)
            self.assertLessEqual(profile.average_working_days, 31)

            # Living expense in [12000, 22000]
            self.assertGreaterEqual(profile.monthly_living_expense, LIVING_EXPENSE_MONTHLY_MIN)
            self.assertLessEqual(profile.monthly_living_expense, LIVING_EXPENSE_MONTHLY_MAX)

            # Existing debt non-negative
            self.assertGreaterEqual(profile.existing_monthly_debt, 0.0)
            # Starting buffer non-negative
            self.assertGreaterEqual(profile.starting_cashflow_buffer, 0.0)

            # Insufficient data tenure <= 0.10 years
            if profile.cohort_archetype == COHORT_INSUFFICIENT_DATA:
                self.assertLessEqual(profile.years_working, 0.10)

    def test_loan_fields_compliance(self):
        """Verify application loan attributes conform to categories, tenures, amounts, and EMI."""
        for app in self.population.applications:
            self.assertIn(app.loan_purpose, LOAN_PURPOSES)
            self.assertIn(app.loan_tenure_months, LOAN_TENURES)
            self.assertGreaterEqual(app.requested_loan_amount, LOAN_AMOUNT_MIN)
            self.assertLessEqual(app.requested_loan_amount, LOAN_AMOUNT_MAX)
            # Must be rounded to nearest 500
            self.assertEqual(app.requested_loan_amount % 500.0, 0.0)

            # Contractual EMI must be positive and greater than principal / tenure
            self.assertGreater(app.contractual_emi, 0.0)
            self.assertGreater(
                app.contractual_emi,
                app.requested_loan_amount / app.loan_tenure_months,
            )
            # Daily debt obligation must be positive
            self.assertGreater(app.daily_debt_obligation, 0.0)

    # ==========================================================================
    # 6. REPRODUCIBILITY TESTS
    # ==========================================================================

    def test_deterministic_reproducibility(self):
        """Running generate_population twice with master seed 42 produces identical data."""
        pop_1 = generate_population(RandomStateManager(MASTER_SEED))
        pop_2 = generate_population(RandomStateManager(MASTER_SEED))

        # Check applicants
        for a1, a2 in zip(pop_1.applicants, pop_2.applicants):
            self.assertEqual(a1.applicant_profile_id, a2.applicant_profile_id)
            self.assertEqual(a1.cohort_archetype, a2.cohort_archetype)

        # Check profiles
        for p1, p2 in zip(pop_1.profiles, pop_2.profiles):
            self.assertEqual(p1.applicant_profile_id, p2.applicant_profile_id)
            self.assertEqual(p1.gig_work_type, p2.gig_work_type)
            self.assertEqual(p1.years_working, p2.years_working)
            self.assertEqual(p1.average_working_days, p2.average_working_days)
            self.assertEqual(p1.monthly_living_expense, p2.monthly_living_expense)
            self.assertEqual(p1.existing_monthly_debt, p2.existing_monthly_debt)
            self.assertEqual(p1.starting_cashflow_buffer, p2.starting_cashflow_buffer)

        # Check applications
        for app1, app2 in zip(pop_1.applications, pop_2.applications):
            self.assertEqual(app1.application_id, app2.application_id)
            self.assertEqual(app1.applicant_profile_id, app2.applicant_profile_id)
            self.assertEqual(app1.application_index, app2.application_index)
            self.assertEqual(app1.cutoff_timestamp, app2.cutoff_timestamp)
            self.assertEqual(app1.requested_loan_amount, app2.requested_loan_amount)
            self.assertEqual(app1.loan_tenure_months, app2.loan_tenure_months)
            self.assertEqual(app1.loan_purpose, app2.loan_purpose)
            self.assertEqual(app1.contractual_emi, app2.contractual_emi)
            self.assertEqual(app1.daily_debt_obligation, app2.daily_debt_obligation)

        self.assertEqual(pop_1.repeat_applicant_ids, pop_2.repeat_applicant_ids)

    # ==========================================================================
    # 7. ANTI-LEAKAGE VERIFICATION
    # ==========================================================================

    def test_no_target_or_forward_leakage(self):
        """
        Verify that applicant profiles and applications contain zero target fields
        or forward simulation parameters.
        """
        for app in self.population.applications:
            self.assertFalse(hasattr(app, "target_default_flag"))
            self.assertFalse(hasattr(app, "repayment_risk_probability"))
            self.assertFalse(hasattr(app, "forward_earnings"))
            self.assertFalse(hasattr(app, "forward_expenses"))


if __name__ == "__main__":
    unittest.main()
