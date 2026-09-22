"""Tests for PARAKH repository persistence layer."""
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings
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
from app.repositories import (
    ApplicantProfileRepository,
    ApplicantRepository,
    ApplicationRepository,
    AssessmentRepository,
    AuditLogRepository,
    AuditRepository,
    BaseRepository,
    ConsentRepository,
    CreditAssessmentRepository,
    FinancialSignalRepository,
    ModelVersionRepository,
    ReviewOutcomeRepository,
    ReviewRepository,
    UserRepository,
)


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable without hanging."""
    from sqlalchemy import text
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"connect_timeout": 1},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


class TestRepositoryUnit(unittest.TestCase):
    """Unit tests for repository layer using an isolated in-memory database."""

    @classmethod
    def setUpClass(cls):
        """Create an in-memory SQLite engine and initialize tables."""
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)

    @classmethod
    def tearDownClass(cls):
        """Clean up SQLite database resources."""
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        """Create a fresh database session for each test."""
        self.db: Session = self.SessionLocal()

    def tearDown(self):
        """Rollback and close the session after each test."""
        self.db.rollback()
        self.db.close()

    def test_repository_model_associations(self):
        """Verify repositories are associated with their correct domain models."""
        self.assertEqual(UserRepository().model, User)
        self.assertEqual(ApplicantRepository().model, ApplicantProfile)
        self.assertEqual(ApplicantProfileRepository().model, ApplicantProfile)
        self.assertEqual(ApplicationRepository().model, Application)
        self.assertEqual(ConsentRepository().model, Consent)
        self.assertEqual(FinancialSignalRepository().model, FinancialSignal)
        self.assertEqual(AssessmentRepository().model, CreditAssessment)
        self.assertEqual(CreditAssessmentRepository().model, CreditAssessment)
        self.assertEqual(ModelVersionRepository().model, ModelVersion)
        self.assertEqual(ReviewRepository().model, ReviewOutcome)
        self.assertEqual(ReviewOutcomeRepository().model, ReviewOutcome)
        self.assertEqual(AuditRepository().model, AuditLog)
        self.assertEqual(AuditLogRepository().model, AuditLog)

    def test_base_repository_session_validation(self):
        """Verify ValueError is raised if no session is provided at init or call."""
        repo = BaseRepository(User)
        with self.assertRaises(ValueError):
            repo.get_by_id(uuid.uuid4())

    def test_base_repository_crud(self):
        """Verify generic CRUD operations on BaseRepository."""
        repo = BaseRepository(User, db=self.db)
        # Create
        user = repo.create({
            "email": "base_test@example.com",
            "role": UserRole.APPLICANT,
        })
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "base_test@example.com")

        # Get by ID (UUID and string)
        fetched = repo.get_by_id(user.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, user.id)

        fetched_str = repo.get_by_id(str(user.id))
        self.assertIsNotNone(fetched_str)
        self.assertEqual(fetched_str.id, user.id)

        # Get all
        users = repo.get_all(limit=10)
        self.assertGreaterEqual(len(users), 1)

        # Update
        updated = repo.update(user, {"is_active": False})
        self.assertFalse(updated.is_active)

        # Delete
        deleted = repo.delete(user.id)
        self.assertIsNotNone(deleted)
        self.assertIsNone(repo.get_by_id(user.id))

    def test_user_repository_email_lookup(self):
        """Verify UserRepository finds user by email case-insensitively and trimmed."""
        repo = UserRepository(db=self.db)
        user = repo.create({
            "email": "Ravi.Kumar@example.com",
            "role": UserRole.APPLICANT,
        })

        found = repo.get_by_email("ravi.kumar@example.com")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, user.id)

        found_spaces = repo.get_by_email("  RAVI.KUMAR@EXAMPLE.COM  ")
        self.assertIsNotNone(found_spaces)
        self.assertEqual(found_spaces.id, user.id)

        not_found = repo.get_by_email("unknown@example.com")
        self.assertIsNone(not_found)

    def test_applicant_repository_user_lookup(self):
        """Verify ApplicantRepository retrieves profile by user_id."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)

        user = user_repo.create({"email": "gig_driver@example.com"})
        profile = applicant_repo.create({
            "user_id": user.id,
            "gig_work_type": "Ride-Hailing Driver",
            "years_working": Decimal("3.5"),
            "average_working_days": 26,
            "business_or_loan_purpose": "Vehicle Maintenance",
        })

        found = applicant_repo.get_by_user_id(user.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, profile.id)
        self.assertEqual(found.gig_work_type, "Ride-Hailing Driver")

        # Test string lookup
        found_str = applicant_repo.get_by_user_id(str(user.id))
        self.assertIsNotNone(found_str)
        self.assertEqual(found_str.id, profile.id)

    def test_application_repository_and_status_update(self):
        """Verify ApplicationRepository listing and status progression."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)

        user = user_repo.create({"email": "delivery_partner@example.com"})
        profile = applicant_repo.create({
            "user_id": user.id,
            "gig_work_type": "Food Delivery",
        })

        app1 = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("15000.00"),
            "loan_purpose": "E-bike battery replacement",
            "status": ApplicationStatus.DRAFT,
        })

        # List by applicant
        apps = app_repo.list_by_applicant(profile.id)
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, app1.id)

        # Update status
        updated_app = app_repo.update_status(app1.id, ApplicationStatus.SUBMITTED)
        self.assertIsNotNone(updated_app)
        self.assertEqual(updated_app.status, ApplicationStatus.SUBMITTED)

        # Update status with string
        updated_app2 = app_repo.update_status(app1, "UNDER_REVIEW")
        self.assertIsNotNone(updated_app2)
        self.assertEqual(updated_app2.status, ApplicationStatus.UNDER_REVIEW)

    def test_consent_repository_and_revocation(self):
        """Verify ConsentRepository active filtering and revocation."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)
        consent_repo = ConsentRepository(db=self.db)

        user = user_repo.create({"email": "consent_user@example.com"})
        profile = applicant_repo.create({
            "user_id": user.id,
            "gig_work_type": "Freelance",
        })
        app = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("20000.00"),
        })

        c1 = consent_repo.create({
            "application_id": app.id,
            "applicant_profile_id": profile.id,
            "data_source": ConsentDataSource.PLATFORM,
            "purpose": "Evaluate delivery regularity",
            "granted": True,
        })
        c2 = consent_repo.create({
            "application_id": app.id,
            "applicant_profile_id": profile.id,
            "data_source": ConsentDataSource.FINANCIAL_ACTIVITY,
            "purpose": "Verify bank statement turnover",
            "granted": True,
        })

        all_consents = consent_repo.get_by_application(app.id)
        self.assertEqual(len(all_consents), 2)

        active = consent_repo.get_active_consents(application_id=app.id)
        self.assertEqual(len(active), 2)

        # Revoke c1
        revoked = consent_repo.revoke(c1.id)
        self.assertIsNotNone(revoked)
        self.assertFalse(revoked.granted)
        self.assertIsNotNone(revoked.revoked_at)

        # Re-check active
        active_after = consent_repo.get_active_consents(application_id=app.id)
        self.assertEqual(len(active_after), 1)
        self.assertEqual(active_after[0].id, c2.id)

    def test_financial_signal_repository_retrieval(self):
        """Verify FinancialSignalRepository retrieves signals and latest record."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)
        sig_repo = FinancialSignalRepository(db=self.db)

        user = user_repo.create({"email": "sig_user@example.com"})
        profile = applicant_repo.create({"user_id": user.id, "gig_work_type": "Logistics"})
        app = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("10000.00"),
        })

        sig1 = sig_repo.create({
            "application_id": app.id,
            "applicant_profile_id": profile.id,
            "source": SignalSource.PLATFORM,
            "average_income": Decimal("32000.00"),
            "payment_regularity": Decimal("0.9200"),
            "created_at": datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc),
        })

        sig2 = sig_repo.create({
            "application_id": app.id,
            "applicant_profile_id": profile.id,
            "source": SignalSource.DERIVED,
            "average_income": Decimal("34500.00"),
            "payment_regularity": Decimal("0.9500"),
            "created_at": datetime(2026, 9, 22, 10, 5, 0, tzinfo=timezone.utc),
        })

        signals = sig_repo.get_by_application(app.id)
        self.assertEqual(len(signals), 2)

        latest = sig_repo.get_latest(app.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.id, sig2.id)

    def test_assessment_repository_retrieval(self):
        """Verify AssessmentRepository retrieves assessments and latest record."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)
        model_repo = ModelVersionRepository(db=self.db)
        assess_repo = AssessmentRepository(db=self.db)

        user = user_repo.create({"email": "assess_user@example.com"})
        profile = applicant_repo.create({"user_id": user.id, "gig_work_type": "Delivery"})
        app = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("12000.00"),
        })
        mv = model_repo.create({
            "model_name": "parakh_baseline_gbm",
            "version": "1.0.0",
            "algorithm": "LightGBM",
            "is_active": True,
        })

        a1 = assess_repo.create({
            "application_id": app.id,
            "model_version_id": mv.id,
            "credit_score": 680,
            "risk_probability": Decimal("0.1800"),
            "risk_level": RiskLevel.MODERATE,
            "confidence": Decimal("0.8500"),
            "created_at": datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc),
        })

        a2 = assess_repo.create({
            "application_id": app.id,
            "model_version_id": mv.id,
            "credit_score": 720,
            "risk_probability": Decimal("0.1100"),
            "risk_level": RiskLevel.LOWER,
            "confidence": Decimal("0.9100"),
            "created_at": datetime(2026, 9, 22, 10, 5, 0, tzinfo=timezone.utc),
        })

        assessments = assess_repo.get_by_application(app.id)
        self.assertEqual(len(assessments), 2)

        latest = assess_repo.get_latest(app.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.id, a2.id)

    def test_model_version_repository_active_and_listing(self):
        """Verify ModelVersionRepository active model retrieval and version listing."""
        repo = ModelVersionRepository(db=self.db)

        v1 = repo.create({
            "model_name": "credit_engine",
            "version": "1.0.0",
            "is_active": False,
        })
        v2 = repo.create({
            "model_name": "credit_engine",
            "version": "1.1.0",
            "is_active": True,
        })
        v3 = repo.create({
            "model_name": "fraud_engine",
            "version": "0.9.0",
            "is_active": True,
        })

        active_credit = repo.get_active("credit_engine")
        self.assertIsNotNone(active_credit)
        self.assertEqual(active_credit.id, v2.id)
        self.assertEqual(active_credit.version, "1.1.0")

        all_credit_versions = repo.list_versions("credit_engine")
        self.assertEqual(len(all_credit_versions), 2)

    def test_review_repository_queries(self):
        """Verify ReviewRepository retrieves outcomes by application and reviewer."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)
        review_repo = ReviewRepository(db=self.db)

        applicant_user = user_repo.create({"email": "applicant_rev@example.com"})
        reviewer = user_repo.create({
            "email": "credit_officer@example.com",
            "role": UserRole.REVIEWER,
        })
        profile = applicant_repo.create({"user_id": applicant_user.id, "gig_work_type": "Courier"})
        app = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("18000.00"),
        })

        r1 = review_repo.create({
            "application_id": app.id,
            "reviewer_id": reviewer.id,
            "outcome": ReviewOutcomeType.REVIEWED,
            "notes": "Verified verified platform history",
        })

        by_app = review_repo.get_by_application(app.id)
        self.assertEqual(len(by_app), 1)
        self.assertEqual(by_app[0].id, r1.id)

        by_rev = review_repo.get_by_reviewer(reviewer.id)
        self.assertEqual(len(by_rev), 1)
        self.assertEqual(by_rev[0].id, r1.id)

    def test_audit_repository_queries(self):
        """Verify AuditRepository queries by application and user."""
        user_repo = UserRepository(db=self.db)
        applicant_repo = ApplicantRepository(db=self.db)
        app_repo = ApplicationRepository(db=self.db)
        audit_repo = AuditRepository(db=self.db)

        user = user_repo.create({"email": "audit_user@example.com"})
        profile = applicant_repo.create({"user_id": user.id, "gig_work_type": "Handyman"})
        app = app_repo.create({
            "applicant_profile_id": profile.id,
            "requested_loan_amount": Decimal("5000.00"),
        })

        audit_log = audit_repo.create({
            "user_id": user.id,
            "application_id": app.id,
            "action": "APPLICATION_SUBMITTED",
            "entity_type": "Application",
            "entity_id": str(app.id),
        })

        by_app = audit_repo.get_by_application(app.id)
        self.assertEqual(len(by_app), 1)
        self.assertEqual(by_app[0].id, audit_log.id)

        by_user = audit_repo.get_by_user(user.id)
        self.assertEqual(len(by_user), 1)
        self.assertEqual(by_user[0].id, audit_log.id)


class TestRepositoryMockUnit(unittest.TestCase):
    """Unit tests using Mock Session for testing isolation and edge cases."""

    def test_mock_session_interactions(self):
        """Verify repository invokes Session methods properly."""
        mock_session = MagicMock(spec=Session)
        user_repo = UserRepository(db=mock_session)

        user_instance = User(email="mock@example.com", role=UserRole.APPLICANT)
        user_repo.create(user_instance, commit=False)

        mock_session.add.assert_called_once_with(user_instance)
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_not_called()

    def test_mock_session_commit_mode(self):
        """Verify commit=True triggers session.commit and refresh."""
        mock_session = MagicMock(spec=Session)
        user_repo = UserRepository(db=mock_session)

        user_instance = User(email="commit_mock@example.com", role=UserRole.APPLICANT)
        user_repo.create(user_instance, commit=True)

        mock_session.add.assert_called_once_with(user_instance)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(user_instance)


class TestRepositoryPostgresIntegration(unittest.TestCase):
    """Integration test suite for live PostgreSQL if available."""

    @unittest.skipUnless(
        can_connect_to_postgres(),
        "PostgreSQL is not reachable locally. Skipping live integration tests.",
    )
    def test_live_postgres_user_repository(self):
        """Verify repository operations against live PostgreSQL database."""
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            repo = UserRepository(db=db)
            test_email = f"live_test_{uuid.uuid4().hex[:8]}@example.com"
            user = repo.create({"email": test_email}, commit=True)
            self.assertIsNotNone(user.id)
            found = repo.get_by_email(test_email)
            self.assertIsNotNone(found)
            repo.delete(user.id, commit=True)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
