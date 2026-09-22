"""Tests validating PARAKH SQLAlchemy domain model definitions and constraints."""
import unittest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    Base,
    Consent,
    ConsentDataSource,
    CreditAssessment,
    FinancialSignal,
    ModelVersion,
    ReviewOutcome,
    ReviewOutcomeType,
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)


class TestDomainModelStructure(unittest.TestCase):
    """Test suite validating domain entity relationships, keys, and constraints."""

    def test_all_models_inherit_from_base(self) -> None:
        """Verify all domain models inherit from DeclarativeBase Base."""
        models = [
            User,
            ApplicantProfile,
            Application,
            Consent,
            FinancialSignal,
            CreditAssessment,
            ModelVersion,
            ReviewOutcome,
            AuditLog,
        ]
        for model in models:
            with self.subTest(model=model.__name__):
                self.assertTrue(
                    issubclass(model, DeclarativeBase),
                    f"{model.__name__} does not inherit from DeclarativeBase",
                )
                self.assertIn(model.__tablename__, Base.metadata.tables)

    def test_primary_keys_exist(self) -> None:
        """Verify all domain models define 'id' as primary key."""
        models = [
            User,
            ApplicantProfile,
            Application,
            Consent,
            FinancialSignal,
            CreditAssessment,
            ModelVersion,
            ReviewOutcome,
            AuditLog,
        ]
        for model in models:
            with self.subTest(model=model.__name__):
                mapper = sa_inspect(model)
                pk_names = [col.name for col in mapper.primary_key]
                self.assertEqual(
                    pk_names,
                    ["id"],
                    f"{model.__name__} primary key should be ['id']",
                )

    def test_foreign_keys_exist(self) -> None:
        """Verify required foreign key linkages across entities."""
        # 1. ApplicantProfile -> User
        applicant_fks = {
            fk.target_fullname for fk in sa_inspect(ApplicantProfile).columns["user_id"].foreign_keys
        }
        self.assertIn("users.id", applicant_fks)

        # 2. Application -> ApplicantProfile
        app_fks = {
            fk.target_fullname
            for fk in sa_inspect(Application).columns["applicant_profile_id"].foreign_keys
        }
        self.assertIn("applicant_profiles.id", app_fks)

        # 3. CreditAssessment -> Application & ModelVersion
        assess_app_fks = {
            fk.target_fullname
            for fk in sa_inspect(CreditAssessment).columns["application_id"].foreign_keys
        }
        self.assertIn("applications.id", assess_app_fks)

        assess_model_fks = {
            fk.target_fullname
            for fk in sa_inspect(CreditAssessment).columns["model_version_id"].foreign_keys
        }
        self.assertIn("model_versions.id", assess_model_fks)

        # 4. ReviewOutcome -> Application & Reviewer User
        review_app_fks = {
            fk.target_fullname
            for fk in sa_inspect(ReviewOutcome).columns["application_id"].foreign_keys
        }
        self.assertIn("applications.id", review_app_fks)

        review_user_fks = {
            fk.target_fullname
            for fk in sa_inspect(ReviewOutcome).columns["reviewer_id"].foreign_keys
        }
        self.assertIn("users.id", review_user_fks)

        # 5. FinancialSignal & Consent -> Application
        signal_app_fks = {
            fk.target_fullname
            for fk in sa_inspect(FinancialSignal).columns["application_id"].foreign_keys
        }
        self.assertIn("applications.id", signal_app_fks)

        consent_app_fks = {
            fk.target_fullname
            for fk in sa_inspect(Consent).columns["application_id"].foreign_keys
        }
        self.assertIn("applications.id", consent_app_fks)

    def test_relationships_and_cardinality(self) -> None:
        """Verify key relationships and one-to-one / one-to-many cardinality."""
        user_mapper = sa_inspect(User)
        self.assertIn("applicant_profile", user_mapper.relationships)
        self.assertFalse(
            user_mapper.relationships["applicant_profile"].uselist,
            "User to ApplicantProfile should be one-to-one (uselist=False)",
        )

        app_mapper = sa_inspect(Application)
        self.assertIn("applicant_profile", app_mapper.relationships)
        self.assertIn("consents", app_mapper.relationships)
        self.assertIn("financial_signals", app_mapper.relationships)
        self.assertIn("credit_assessments", app_mapper.relationships)
        self.assertIn("review_outcomes", app_mapper.relationships)
        self.assertIn("audit_logs", app_mapper.relationships)

        assessment_mapper = sa_inspect(CreditAssessment)
        self.assertIn("application", assessment_mapper.relationships)
        self.assertIn("model_version", assessment_mapper.relationships)

        review_mapper = sa_inspect(ReviewOutcome)
        self.assertIn("reviewer", review_mapper.relationships)
        self.assertIn("application", review_mapper.relationships)

    def test_unique_constraints(self) -> None:
        """Verify unique constraints on user email and applicant user_id."""
        user_email_col = sa_inspect(User).columns["email"]
        self.assertTrue(user_email_col.unique)

        applicant_user_col = sa_inspect(ApplicantProfile).columns["user_id"]
        self.assertTrue(applicant_user_col.unique)

    def test_enum_definitions(self) -> None:
        """Verify domain enums provide expected taxonomy choices."""
        self.assertEqual(UserRole.APPLICANT.value, "APPLICANT")
        self.assertEqual(UserRole.REVIEWER.value, "REVIEWER")

        self.assertIn("DRAFT", [s.value for s in ApplicationStatus])
        self.assertIn("SUBMITTED", [s.value for s in ApplicationStatus])
        self.assertIn("UNDER_REVIEW", [s.value for s in ApplicationStatus])
        self.assertIn("ASSESSED", [s.value for s in ApplicationStatus])
        self.assertIn("MANUAL_REVIEW", [s.value for s in ApplicationStatus])
        self.assertIn("COMPLETED", [s.value for s in ApplicationStatus])

        self.assertIn("PLATFORM", [s.value for s in ConsentDataSource])
        self.assertIn("FINANCIAL_ACTIVITY", [s.value for s in ConsentDataSource])
        self.assertIn("UTILITY", [s.value for s in ConsentDataSource])

        self.assertIn("LOWER", [r.value for r in RiskLevel])
        self.assertIn("MODERATE", [r.value for r in RiskLevel])
        self.assertIn("HIGHER", [r.value for r in RiskLevel])
        self.assertIn("INSUFFICIENT", [r.value for r in RiskLevel])

        self.assertIn("REVIEWED", [o.value for o in ReviewOutcomeType])
        self.assertIn("ESCALATED", [o.value for o in ReviewOutcomeType])
        self.assertIn("ADDITIONAL_INFORMATION_REQUIRED", [o.value for o in ReviewOutcomeType])

    def test_data_minimization(self) -> None:
        """Verify prohibited sensitive fields are not present in any domain tables."""
        forbidden_keywords = [
            "contact",
            "gps",
            "location_history",
            "merchant",
            "upi_transaction",
            "bank_statement",
            "card_number",
            "cvv",
            "raw_password",
            "plaintext",
        ]
        for table_name, table in Base.metadata.tables.items():
            for col in table.columns:
                col_lower = col.name.lower()
                for forbidden in forbidden_keywords:
                    self.assertNotIn(
                        forbidden,
                        col_lower,
                        f"Prohibited sensitive field '{col.name}' found in table '{table_name}'",
                    )


class TestModelFieldConstraintsAndDefaults(unittest.TestCase):
    """Test suite validating column nullability and column defaults on domain models."""

    def test_non_nullable_critical_columns(self) -> None:
        """Verify critical columns cannot be null across domain models."""
        user_cols = sa_inspect(User).columns
        self.assertFalse(user_cols["email"].nullable)
        self.assertFalse(user_cols["role"].nullable)

        app_cols = sa_inspect(Application).columns
        self.assertFalse(app_cols["applicant_profile_id"].nullable)
        self.assertFalse(app_cols["requested_loan_amount"].nullable)
        self.assertFalse(app_cols["status"].nullable)

        consent_cols = sa_inspect(Consent).columns
        self.assertFalse(consent_cols["data_source"].nullable)
        self.assertFalse(consent_cols["granted"].nullable)

        signal_cols = sa_inspect(FinancialSignal).columns
        self.assertFalse(signal_cols["application_id"].nullable)
        self.assertFalse(signal_cols["source"].nullable)

        audit_cols = sa_inspect(AuditLog).columns
        self.assertFalse(audit_cols["action"].nullable)
        self.assertFalse(audit_cols["entity_type"].nullable)

    def test_model_defaults_on_persistence(self) -> None:
        """Verify domain models apply correct default values when persisted."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine_mem = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine_mem)
        SessionTest = sessionmaker(bind=engine_mem)

        with SessionTest() as db:
            user = User(email="default_test@example.com", password_hash="hashed")
            db.add(user)
            db.commit()
            db.refresh(user)
            self.assertTrue(user.is_active)
            self.assertEqual(user.role, UserRole.APPLICANT)

            model_ver = ModelVersion(model_name="default_model", version="1.0.0")
            db.add(model_ver)
            db.commit()
            db.refresh(model_ver)
            self.assertTrue(model_ver.is_active)

        Base.metadata.drop_all(engine_mem)
        engine_mem.dispose()


if __name__ == "__main__":
    unittest.main()


