"""Tests validating Alembic migration configuration and revision scripts."""
import os
import subprocess
import unittest
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.core.config import settings
from app.models import (
    ApplicantProfile,
    Application,
    AuditLog,
    Base,
    Consent,
    CreditAssessment,
    FinancialSignal,
    ModelVersion,
    ReviewOutcome,
    User,
)


class TestAlembicMigrationSetup(unittest.TestCase):
    """Test suite for Alembic configuration and migration assets."""

    @classmethod
    def setUpClass(cls) -> None:
        """Locate backend and alembic root paths."""
        cls.backend_dir = Path(__file__).resolve().parent.parent
        cls.alembic_ini_path = cls.backend_dir / "alembic.ini"
        cls.alembic_dir = cls.backend_dir / "alembic"

    def test_alembic_configuration_files_exist(self) -> None:
        """Verify alembic.ini, env.py, script.py.mako, and versions directory exist."""
        self.assertTrue(self.alembic_ini_path.is_file(), "alembic.ini is missing")
        self.assertTrue((self.alembic_dir / "env.py").is_file(), "alembic/env.py is missing")
        self.assertTrue(
            (self.alembic_dir / "script.py.mako").is_file(),
            "alembic/script.py.mako is missing",
        )
        self.assertTrue(
            (self.alembic_dir / "versions").is_dir(),
            "alembic/versions directory is missing",
        )

    def test_alembic_config_loads_app_settings(self) -> None:
        """Verify Alembic Config loads and correctly resolves script_location."""
        alembic_cfg = Config(str(self.alembic_ini_path))
        script_location = alembic_cfg.get_main_option("script_location")
        self.assertIsNotNone(script_location)
        self.assertIn("alembic", script_location)

        # Confirm app settings DATABASE_URL is available
        self.assertIsNotNone(settings.DATABASE_URL)
        self.assertTrue(settings.DATABASE_URL.startswith("postgresql"))

    def test_base_metadata_contains_all_domain_models(self) -> None:
        """Verify Base.metadata contains all 9 required PARAKH domain tables."""
        expected_tables = {
            "users",
            "applicant_profiles",
            "applications",
            "consents",
            "financial_signals",
            "model_versions",
            "credit_assessments",
            "review_outcomes",
            "audit_logs",
        }
        actual_tables = set(Base.metadata.tables.keys())
        self.assertTrue(
            expected_tables.issubset(actual_tables),
            f"Missing tables in Base.metadata: {expected_tables - actual_tables}",
        )

    def test_initial_migration_script_registered(self) -> None:
        """Verify ScriptDirectory discovers migrations and has a single head."""
        alembic_cfg = Config(str(self.alembic_ini_path))
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()
        self.assertEqual(len(heads), 1, "Expected exactly 1 migration head")
        revisions = [rev.doc for rev in script.walk_revisions() if rev.doc]
        self.assertTrue(
            any("initial_schema" in doc for doc in revisions),
            "Expected initial_schema migration in revision history",
        )

    def test_offline_sql_generation(self) -> None:
        """Verify Alembic can generate full SQL DDL offline without active PostgreSQL."""
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "base:head", "--sql"],
            cwd=str(self.backend_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"alembic upgrade --sql failed: {result.stderr}",
        )
        sql_output = result.stdout
        self.assertIn("CREATE TABLE users", sql_output)
        self.assertIn("CREATE TABLE applicant_profiles", sql_output)
        self.assertIn("CREATE TABLE applications", sql_output)
        self.assertIn("CREATE TABLE consents", sql_output)
        self.assertIn("CREATE TABLE financial_signals", sql_output)
        self.assertIn("CREATE TABLE model_versions", sql_output)
        self.assertIn("CREATE TABLE credit_assessments", sql_output)
        self.assertIn("CREATE TABLE review_outcomes", sql_output)
        self.assertIn("CREATE TABLE audit_logs", sql_output)

    def test_frontend_directory_untouched(self) -> None:
        """Verify frontend directory has not been modified or corrupted."""
        project_root = self.backend_dir.parent
        frontend_dir = project_root / "frontend"
        self.assertTrue(frontend_dir.is_dir(), "frontend directory must exist")
        package_json = frontend_dir / "package.json"
        self.assertTrue(package_json.is_file(), "frontend/package.json must exist")


if __name__ == "__main__":
    unittest.main()
