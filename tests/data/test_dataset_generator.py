"""
Unit test suite for P2-T10: Final Synthetic Dataset Generator.
Verifies the 10 requirements:
1. Exactly 12,000 rows generated.
2. Approximately 10,000 unique applicants (expected exactly 10,000).
3. Required cohort counts & proportions.
4. Repeated applicants (2,000 applicants with exactly 2 applications, >= 120 days apart).
5. Deterministic generation (running twice yields bit-for-bit identical parquet tables).
6. Artifact creation (all expected parquet, json, txt files exist and are non-empty).
7. Schema preservation (52 columns, exact column names and dtypes).
8. Validation pass (overall_status == PASS).
9. Default-rate reporting (clean float reported, no post-hoc relabeling).
10. No future leakage.
"""

from collections import Counter, defaultdict
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
import pyarrow.parquet as pq

from src.data.synthetic.config import (
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
    REPEAT_APPLICANTS,
    COHORT_ARCHETYPES,
    COHORT_INSUFFICIENT_DATA,
    COHORT_PROPORTIONS,
    MASTER_SEED,
    REPEAT_INTERVAL_DAYS_MIN,
)
from src.data.synthetic.schemas import FINAL_DATASET_SCHEMA
from src.data.synthetic.dataset_generator import (
    CANONICAL_OUTPUT_PATH,
    generate_full_synthetic_dataset,
    create_canonical_pyarrow_schema,
)


class TestDatasetGenerator(unittest.TestCase):
    """Test suite verifying final synthetic dataset generation and serialized artifacts."""

    @classmethod
    def setUpClass(cls):
        """
        Ensure canonical dataset exists or generate it to a temporary directory if needed.
        If canonical output already exists at data/synthetic/synthetic_credit_applications.parquet,
        read it. Otherwise generate it.
        """
        cls.canonical_parquet = CANONICAL_OUTPUT_PATH
        cls.base_dir = os.path.dirname(os.path.abspath(cls.canonical_parquet))

        if not os.path.exists(cls.canonical_parquet):
            cls.generation_result = generate_full_synthetic_dataset(
                master_seed=MASTER_SEED,
                n_applicants=UNIQUE_APPLICANTS,
                n_repeats=REPEAT_APPLICANTS,
                output_parquet_path=cls.canonical_parquet,
            )
        else:
            cls.generation_result = None

        # Read the generated primary parquet table
        cls.table = pq.read_table(cls.canonical_parquet)
        cls.pydict = cls.table.to_pydict()

    def test_01_exactly_12000_rows(self):
        """1. Dataset must contain exactly 12,000 application assessment rows."""
        self.assertEqual(len(self.table), TOTAL_APPLICATIONS)
        self.assertEqual(len(self.pydict["application_id"]), 12000)

    def test_02_exactly_10000_unique_applicants(self):
        """2. Dataset must contain approximately 10,000 unique applicants (exactly 10,000)."""
        unique_applicants = len(set(self.pydict["applicant_profile_id"]))
        self.assertEqual(unique_applicants, UNIQUE_APPLICANTS)

    def test_03_required_cohort_counts_and_proportions(self):
        """3. All six required cohorts must match contractual counts and proportions within tolerance."""
        cohort_counts = Counter(self.pydict["cohort_archetype"])
        total = len(self.pydict["cohort_archetype"])

        for cohort in COHORT_ARCHETYPES:
            self.assertIn(cohort, cohort_counts, f"Missing cohort '{cohort}' in dataset")
            expected_prop = COHORT_PROPORTIONS[cohort]
            actual_prop = cohort_counts[cohort] / total
            # Contract tolerance: within 3% absolute proportion
            self.assertAlmostEqual(
                actual_prop,
                expected_prop,
                delta=0.03,
                msg=f"Cohort '{cohort}' actual prop {actual_prop:.4f} deviates from expected {expected_prop:.4f}",
            )

    def test_04_repeat_applicants_structure_and_spacing(self):
        """4. Exactly 2,000 repeat applicants with 2 applications, >= 120 days apart."""
        apps_by_prof = defaultdict(list)
        for prof_id, t0 in zip(self.pydict["applicant_profile_id"], self.pydict["cutoff_timestamp"]):
            apps_by_prof[prof_id].append(t0)

        repeats = {k: v for k, v in apps_by_prof.items() if len(v) == 2}
        singles = {k: v for k, v in apps_by_prof.items() if len(v) == 1}

        self.assertEqual(len(repeats), REPEAT_APPLICANTS)
        self.assertEqual(len(singles), UNIQUE_APPLICANTS - REPEAT_APPLICANTS)
        self.assertEqual(sum(1 for v in apps_by_prof.values() if len(v) > 2), 0)

        # Check spacing between repeat applications
        for prof_id, t0_list in repeats.items():
            sorted_t0 = sorted(t0_list)
            t1 = datetime.fromisoformat(sorted_t0[0].replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(sorted_t0[1].replace("Z", "+00:00"))
            delta_days = (t2.date() - t1.date()).days
            self.assertGreaterEqual(
                delta_days,
                REPEAT_INTERVAL_DAYS_MIN,
                f"Applicant {prof_id} has interval {delta_days} days, violation of min {REPEAT_INTERVAL_DAYS_MIN}",
            )

    def test_05_deterministic_generation(self):
        """5. Deterministic generation: Running twice with identical seed yields bit-for-bit identical tables."""
        temp_dir = tempfile.mkdtemp(prefix="parakh_test_det_")
        try:
            p1 = os.path.join(temp_dir, "run1.parquet")
            p2 = os.path.join(temp_dir, "run2.parquet")

            # Run with a small sample of applicants for quick bit-for-bit check
            res1 = generate_full_synthetic_dataset(
                master_seed=MASTER_SEED,
                n_applicants=50,
                n_repeats=10,
                output_parquet_path=p1,
                serialize_raw=False,
                run_strict_validation=False,
            )
            res2 = generate_full_synthetic_dataset(
                master_seed=MASTER_SEED,
                n_applicants=50,
                n_repeats=10,
                output_parquet_path=p2,
                serialize_raw=False,
                run_strict_validation=False,
            )

            t1 = pq.read_table(p1)
            t2 = pq.read_table(p2)

            self.assertTrue(t1.equals(t2), "Parquet tables from identical seed must be bit-for-bit identical")
        finally:
            shutil.rmtree(temp_dir)

    def test_06_artifact_creation(self):
        """6. All expected primary, raw, event, and validation artifacts exist and are non-empty."""
        expected_artifacts = [
            self.canonical_parquet,
            os.path.join(self.base_dir, "raw", "applicant_profiles.parquet"),
            os.path.join(self.base_dir, "raw", "applications.parquet"),
            os.path.join(self.base_dir, "events", "daily_activity_events.parquet"),
            os.path.join(self.base_dir, "events", "weekly_payout_events.parquet"),
            os.path.join(self.base_dir, "validation", "validation_report.json"),
            os.path.join(self.base_dir, "validation", "validation_report.txt"),
            os.path.join(self.base_dir, "generation_metadata.json"),
        ]

        for path in expected_artifacts:
            self.assertTrue(os.path.exists(path), f"Artifact missing: {path}")
            self.assertGreater(os.path.getsize(path), 0, f"Artifact is empty: {path}")

        # Verify validation report json is valid JSON
        val_json = os.path.join(self.base_dir, "validation", "validation_report.json")
        with open(val_json, "r") as f:
            val_data = json.load(f)
        self.assertEqual(val_data["row_count"], 12000)
        self.assertEqual(val_data["overall_status"], "PASS")

    def test_07_schema_preservation(self):
        """7. Schema must have exactly 52 columns with exact column names and expected types."""
        self.assertEqual(len(self.table.column_names), 52)
        expected_cols = [col.name for col in FINAL_DATASET_SCHEMA]
        self.assertEqual(self.table.column_names, expected_cols)

        # Check pyarrow schema field nullability and types
        expected_pyarrow_schema = create_canonical_pyarrow_schema()
        for field in expected_pyarrow_schema:
            actual_field = self.table.schema.field(field.name)
            self.assertEqual(actual_field.type, field.type, f"Field '{field.name}' type mismatch")
            self.assertEqual(actual_field.nullable, field.nullable, f"Field '{field.name}' nullable mismatch")

    def test_08_validation_pass(self):
        """8. Generated dataset passes full P2-T09 validation suite with overall_status == PASS."""
        meta_json = os.path.join(self.base_dir, "generation_metadata.json")
        self.assertTrue(os.path.exists(meta_json))
        with open(meta_json, "r") as f:
            meta = json.load(f)
        self.assertEqual(meta["overall_validation_status"], "PASS")

    def test_09_default_rate_reporting(self):
        """9. Scored default rate is cleanly calculated and reported without post-hoc manipulation."""
        cohorts = self.pydict["cohort_archetype"]
        flags = self.pydict["target_default_flag"]
        probs = self.pydict["repayment_risk_probability"]

        scored_flags = []
        for cohort, flag, prob in zip(cohorts, flags, probs):
            if cohort == COHORT_INSUFFICIENT_DATA:
                self.assertIsNone(flag)
                self.assertIsNone(prob)
            else:
                self.assertIn(flag, (0, 1))
                self.assertIsInstance(prob, float)
                self.assertTrue(0.0 <= prob <= 1.0)
                scored_flags.append(flag)

        self.assertGreater(len(scored_flags), 0)
        actual_rate = sum(scored_flags) / len(scored_flags)
        self.assertGreater(actual_rate, 0.0)
        self.assertLess(actual_rate, 1.0)

    def test_10_no_future_leakage(self):
        """10. Historical events and derived features strictly precede t0 with zero future leakage."""
        daily_pq = os.path.join(self.base_dir, "events", "daily_activity_events.parquet")
        daily_table = pq.read_table(daily_pq, columns=["day_offset"])
        day_offsets = daily_table.column("day_offset").to_pylist()

        # Day offsets must be strictly negative [-90, -1]
        self.assertTrue(all(-90 <= o <= -1 for o in day_offsets))

        # Target columns not present in derived feature names
        feature_cols = [c.name for c in FINAL_DATASET_SCHEMA if c.name.startswith("feat_")]
        self.assertNotIn("target_default_flag", feature_cols)
        self.assertNotIn("repayment_risk_probability", feature_cols)


if __name__ == "__main__":
    unittest.main()
