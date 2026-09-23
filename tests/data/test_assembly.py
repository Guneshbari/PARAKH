"""
Unit and Integration Tests for Application-Level Dataset Assembly (P2-T08).
Validates:
1. One application produces exactly one assembled record.
2. Repeated assessments for one applicant remain separate.
3. Application IDs remain unique.
4. Applicant IDs are preserved.
5. Cutoff timestamp t0 is preserved.
6. All 40 frozen features are present.
7. No unexpected ML feature is present (exact 52 columns).
8. Feature values are unchanged during assembly.
9. Target values are unchanged during assembly.
10. Insufficient-data target representation is preserved (nulls).
11. Historical/future temporal relationship remains valid.
12. Same inputs produce identical assembled output.
13. Record ordering is deterministic.
14. Duplicate applications are rejected.
15. Invalid feature vectors are rejected.
16. Invalid target values are rejected.
17. Mismatched relational keys are rejected.
"""

from datetime import datetime, timezone, timedelta
import unittest
from typing import Dict, List

from src.data.synthetic.config import (
    MASTER_SEED,
    COHORT_INSUFFICIENT_DATA,
    COHORT_STABLE,
    REPEAT_INTERVAL_DAYS_MIN,
)
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    SchemaError,
    TemporalLeakageError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    DerivedFeatures,
    ForwardOutcome,
    FinalRecord,
    AssembledApplicationRecord,
    FINAL_DATASET_SCHEMA,
    get_column_names,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.telemetry_generator import generate_application_history
from src.data.synthetic.feature_derivation import derive_application_features
from src.data.synthetic.target_generator import simulate_forward_outcome
from src.data.synthetic.assembly import (
    assemble_application_record,
    assemble_dataset,
    validate_assembled_record,
    validate_assembled_dataset,
)


class TestAssembly(unittest.TestCase):
    """Test suite for application-level dataset assembly layer."""

    @classmethod
    def setUpClass(cls):
        """Generate small deterministic fixture (50 applicants, 10 repeats, 60 applications)."""
        cls.population = generate_population(n_applicants=50, n_repeats=10)
        cls.profiles = {p.applicant_profile_id: p for p in cls.population.profiles}
        cls.features: Dict[str, ApplicationFeatures] = {}
        cls.outcomes: Dict[str, ForwardOutcome] = {}

        for app in cls.population.applications:
            prof = cls.profiles[app.applicant_profile_id]
            history = generate_application_history(app, prof, master_seed=MASTER_SEED)
            feat = derive_application_features(app, prof, history)
            cls.features[app.application_id] = feat
            outcome = simulate_forward_outcome(app, prof, master_seed=MASTER_SEED, n_mc_paths=5)
            cls.outcomes[app.application_id] = outcome

        cls.assembled_records = assemble_dataset(
            applications=cls.population.applications,
            profiles=cls.profiles,
            features=cls.features,
            outcomes=cls.outcomes,
        )

    def test_one_application_produces_exactly_one_record(self):
        """1. One application produces exactly one assembled record."""
        self.assertEqual(len(self.assembled_records), len(self.population.applications))
        self.assertEqual(len(self.assembled_records), 60)

    def test_repeated_assessments_remain_separate(self):
        """2. Repeated assessments for one applicant remain separate records."""
        repeat_ids = self.population.repeat_applicant_ids
        self.assertEqual(len(repeat_ids), 10)

        for rep_id in repeat_ids:
            matching = [r for r in self.assembled_records if r.applicant_profile_id == rep_id]
            self.assertEqual(
                len(matching),
                2,
                f"Repeat applicant '{rep_id}' must have exactly 2 separate assembled records",
            )
            # Distinct application IDs
            self.assertNotEqual(matching[0].application_id, matching[1].application_id)
            # Distinct cutoffs
            self.assertNotEqual(matching[0].cutoff_timestamp, matching[1].cutoff_timestamp)

    def test_application_ids_remain_unique(self):
        """3. Application IDs remain unique across all assembled records."""
        app_ids = [r.application_id for r in self.assembled_records]
        self.assertEqual(len(app_ids), len(set(app_ids)))

    def test_applicant_ids_preserved(self):
        """4. Applicant IDs are preserved and match source applications."""
        for app, rec in zip(self.population.applications, self.assembled_records):
            self.assertEqual(rec.applicant_profile_id, app.applicant_profile_id)
            self.assertEqual(rec.application_id, app.application_id)

    def test_cutoff_timestamp_t0_preserved(self):
        """5. Cutoff timestamp t0 is preserved exactly."""
        for app, rec in zip(self.population.applications, self.assembled_records):
            self.assertEqual(rec.cutoff_timestamp, app.cutoff_timestamp)

    def test_all_40_features_present(self):
        """6. All 40 frozen features are present in each assembled record."""
        expected_cols = get_column_names()
        derived_cols = [c for c in expected_cols if c.startswith("feat_")]
        self.assertEqual(len(derived_cols), 40)

        for rec in self.assembled_records:
            d = rec.to_dict()
            for col in derived_cols:
                self.assertIn(col, d, f"Derived feature '{col}' missing from assembled record dict")
                self.assertTrue(hasattr(rec.features, col), f"Feature '{col}' missing on rec.features")

    def test_no_unexpected_ml_features(self):
        """7. No unexpected ML feature is present; record matches exact 52-column schema."""
        expected_cols = get_column_names()
        self.assertEqual(len(expected_cols), 52)

        for rec in self.assembled_records:
            d = rec.to_dict()
            self.assertEqual(len(d), 52)
            self.assertEqual(list(d.keys()), expected_cols)

    def test_feature_values_unchanged_during_assembly(self):
        """8. Feature values are unchanged from P2-T06 feature derivation."""
        for rec in self.assembled_records:
            source_feat = self.features[rec.application_id].features
            assembled_feat = rec.features
            self.assertEqual(
                assembled_feat.__dict__,
                source_feat.__dict__,
                f"Features modified during assembly for application {rec.application_id}",
            )

    def test_target_values_unchanged_during_assembly(self):
        """9. Target values are unchanged from P2-T07 outcome simulation."""
        for rec in self.assembled_records:
            source_out = self.outcomes[rec.application_id]
            self.assertEqual(rec.target_default_flag, source_out.target_default_flag)
            self.assertEqual(rec.repayment_risk_probability, source_out.repayment_risk_probability)
            self.assertEqual(rec.prediction_horizon_days, source_out.prediction_horizon_days)
            self.assertEqual(rec.consecutive_negative_days, source_out.consecutive_negative_days)

    def test_insufficient_data_target_representation_preserved(self):
        """10. Insufficient Data cohort records preserve null target representation."""
        insufficient_records = [
            r for r in self.assembled_records if r.cohort_archetype == COHORT_INSUFFICIENT_DATA
        ]
        self.assertTrue(len(insufficient_records) > 0)

        for rec in insufficient_records:
            d = rec.to_dict()
            self.assertIsNone(rec.target_default_flag)
            self.assertIsNone(rec.repayment_risk_probability)
            self.assertIsNone(d["target_default_flag"])
            self.assertIsNone(d["repayment_risk_probability"])

    def test_historical_future_temporal_relationship_valid(self):
        """11. Historical/future temporal relationship remains valid."""
        for rec in self.assembled_records:
            t0 = datetime.fromisoformat(rec.cutoff_timestamp.replace("Z", "+00:00"))
            # Prediction horizon end
            t_end = t0 + timedelta(days=rec.prediction_horizon_days)
            self.assertGreater(t_end, t0)

    def test_deterministic_assembly(self):
        """12. Same inputs produce identical assembled output."""
        second_assembly = assemble_dataset(
            applications=self.population.applications,
            profiles=self.profiles,
            features=self.features,
            outcomes=self.outcomes,
        )
        self.assertEqual(len(self.assembled_records), len(second_assembly))
        for r1, r2 in zip(self.assembled_records, second_assembly):
            self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_deterministic_record_ordering(self):
        """13. Record ordering is deterministic when sorted by application_id."""
        sorted_records = assemble_dataset(
            applications=self.population.applications,
            profiles=self.profiles,
            features=self.features,
            outcomes=self.outcomes,
            deterministic_sort=True,
        )
        app_ids = [r.application_id for r in sorted_records]
        self.assertEqual(app_ids, sorted(app_ids))

    def test_duplicate_applications_rejected(self):
        """14. Duplicate application records are rejected with ImpossibleCombinationError."""
        dup_applications = list(self.population.applications) + [self.population.applications[0]]
        with self.assertRaises(ImpossibleCombinationError):
            assemble_dataset(
                applications=dup_applications,
                profiles=self.profiles,
                features=self.features,
                outcomes=self.outcomes,
            )

    def test_invalid_feature_vectors_rejected(self):
        """15. Invalid feature vectors (e.g. negative CV) are rejected."""
        rec = self.assembled_records[0]
        # Create invalid record with negative CV
        invalid_features_dict = dict(rec.features.__dict__)
        invalid_features_dict["feat_inc_cv_90d"] = -1.0
        invalid_features = DerivedFeatures(**invalid_features_dict)

        invalid_rec = AssembledApplicationRecord(
            application_id=rec.application_id,
            applicant_profile_id=rec.applicant_profile_id,
            cutoff_timestamp=rec.cutoff_timestamp,
            cohort_archetype=rec.cohort_archetype,
            gig_work_type=rec.gig_work_type,
            years_working=rec.years_working,
            average_working_days=rec.average_working_days,
            requested_loan_amount=rec.requested_loan_amount,
            loan_tenure_months=rec.loan_tenure_months,
            loan_purpose=rec.loan_purpose,
            features=invalid_features,
            target_default_flag=rec.target_default_flag,
            repayment_risk_probability=rec.repayment_risk_probability,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_assembled_record(invalid_rec)

    def test_invalid_target_values_rejected(self):
        """16. Invalid target values (e.g. target 1 with 0 negative days) are rejected."""
        rec = next(r for r in self.assembled_records if r.cohort_archetype == COHORT_STABLE)
        invalid_target_rec = AssembledApplicationRecord(
            application_id=rec.application_id,
            applicant_profile_id=rec.applicant_profile_id,
            cutoff_timestamp=rec.cutoff_timestamp,
            cohort_archetype=rec.cohort_archetype,
            gig_work_type=rec.gig_work_type,
            years_working=rec.years_working,
            average_working_days=rec.average_working_days,
            requested_loan_amount=rec.requested_loan_amount,
            loan_tenure_months=rec.loan_tenure_months,
            loan_purpose=rec.loan_purpose,
            features=rec.features,
            target_default_flag=1,  # Inconsistent: flag=1 but consecutive_negative_days=0 (< 7)
            repayment_risk_probability=0.85,
            prediction_horizon_days=90,
            consecutive_negative_days=0,
        )
        with self.assertRaises(ImpossibleCombinationError):
            validate_assembled_record(invalid_target_rec)

    def test_mismatched_relational_keys_rejected(self):
        """17. Mismatched application/profile/feature/outcome IDs are rejected with ValidationError."""
        app = self.population.applications[0]
        prof = self.profiles[self.population.applications[1].applicant_profile_id]  # Wrong profile!
        feat = self.features[app.application_id]
        out = self.outcomes[app.application_id]

        with self.assertRaises(ValidationError):
            assemble_application_record(app, prof, feat, out)

    def test_to_final_record_conversion(self):
        """18. AssembledApplicationRecord converts cleanly to FinalRecord."""
        rec = self.assembled_records[0]
        final_rec = rec.to_final_record()
        self.assertIsInstance(final_rec, FinalRecord)
        self.assertEqual(final_rec.fields, rec.to_dict())
        self.assertEqual(len(final_rec.to_dict()), 52)


if __name__ == "__main__":
    unittest.main()
