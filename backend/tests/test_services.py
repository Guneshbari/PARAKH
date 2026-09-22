"""Comprehensive unit and integration tests for the PARAKH service layer."""
import unittest
import uuid
from decimal import Decimal
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import settings
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
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
    ApplicantRepository,
    ApplicationRepository,
    AssessmentRepository,
    ConsentRepository,
    FinancialSignalRepository,
    ModelVersionRepository,
    ReviewRepository,
    UserRepository,
)
from app.schemas.applicant import ApplicantProfileCreate, ApplicantProfileUpdate
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.assessment import CreditAssessmentCreate
from app.schemas.consent import ConsentCreate
from app.schemas.financial_signal import FinancialSignalCreate
from app.schemas.model_version import ModelVersionCreate
from app.schemas.review import ReviewOutcomeCreate
from app.schemas.user import UserCreate, UserUpdate
from app.services import (
    ApplicantService,
    ApplicationService,
    AssessmentService,
    ConsentService,
    DuplicateEntityError,
    EntityNotFoundError,
    FinancialSignalService,
    InvalidStateTransitionError,
    ModelVersionService,
    ReviewService,
    UserService,
    ValidationError,
)


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable."""
    from sqlalchemy import text
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


class TestServicesWithMocks(unittest.TestCase):
    """Unit tests isolating service business rules using mocked repositories and sessions."""

    def setUp(self):
        self.mock_db = MagicMock(spec=Session)

    def test_user_creation_normalizes_email(self):
        """Verify email is converted to lowercase and trimmed."""
        mock_repo = MagicMock(spec=UserRepository)
        mock_repo.get_by_email.return_value = None
        service = UserService(db=self.mock_db, user_repo=mock_repo)

        user_in = UserCreate(
            email="  GIG.Worker@Example.COM  ",
            role=UserRole.APPLICANT,
            password="securepassword123",
        )
        service.create_user(user_in)

        mock_repo.get_by_email.assert_called_once_with("gig.worker@example.com", db=self.mock_db)
        call_args = mock_repo.create.call_args[0][0]
        self.assertEqual(call_args["email"], "gig.worker@example.com")
        self.mock_db.commit.assert_called_once()

    def test_user_creation_duplicate_email_raises_error(self):
        """Verify duplicate email throws DuplicateEntityError before creating."""
        mock_repo = MagicMock(spec=UserRepository)
        mock_repo.get_by_email.return_value = User(email="existing@example.com")
        service = UserService(db=self.mock_db, user_repo=mock_repo)

        with self.assertRaises(DuplicateEntityError):
            service.create_user(
                UserCreate(email="existing@example.com", password="securepassword123")
            )

        mock_repo.create.assert_not_called()

    def test_user_creation_missing_email_raises_error(self):
        """Verify empty email throws ValidationError."""
        mock_repo = MagicMock(spec=UserRepository)
        service = UserService(db=self.mock_db, user_repo=mock_repo)

        with self.assertRaises(ValidationError):
            service.create_user({"email": "   "})

    def test_user_retrieval_not_found(self):
        """Verify non-existent user throws EntityNotFoundError."""
        mock_repo = MagicMock(spec=UserRepository)
        mock_repo.get_by_id.return_value = None
        service = UserService(db=self.mock_db, user_repo=mock_repo)

        with self.assertRaises(EntityNotFoundError):
            service.get_user(uuid.uuid4())

    def test_applicant_profile_missing_user_raises_error(self):
        """Verify creating profile for non-existent user throws EntityNotFoundError."""
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        mock_user_repo = MagicMock(spec=UserRepository)
        mock_user_repo.get_by_id.return_value = None
        service = ApplicantService(
            db=self.mock_db,
            applicant_repo=mock_applicant_repo,
            user_repo=mock_user_repo,
        )

        with self.assertRaises(EntityNotFoundError):
            service.create_profile(
                ApplicantProfileCreate(gig_work_type="Delivery"),
                user_id=uuid.uuid4(),
            )

    def test_applicant_profile_duplicate_raises_error(self):
        """Verify duplicate profile for existing user throws DuplicateEntityError."""
        user_id = uuid.uuid4()
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        mock_user_repo = MagicMock(spec=UserRepository)
        mock_user_repo.get_by_id.return_value = User(id=user_id, email="u@ex.com")
        mock_applicant_repo.get_by_user_id.return_value = ApplicantProfile(user_id=user_id)

        service = ApplicantService(
            db=self.mock_db,
            applicant_repo=mock_applicant_repo,
            user_repo=mock_user_repo,
        )

        with self.assertRaises(DuplicateEntityError):
            service.create_profile(
                ApplicantProfileCreate(gig_work_type="Delivery"),
                user_id=user_id,
            )

    def test_application_creation_missing_profile_raises_error(self):
        """Verify application creation with non-existent applicant profile throws EntityNotFoundError."""
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        mock_applicant_repo.get_by_id.return_value = None

        service = ApplicationService(
            db=self.mock_db,
            app_repo=mock_app_repo,
            applicant_repo=mock_applicant_repo,
        )

        with self.assertRaises(EntityNotFoundError):
            service.create_application(ApplicationCreate(
                applicant_profile_id=uuid.uuid4(),
                requested_loan_amount=Decimal("10000.00"),
            ))

    def test_application_creation_invalid_loan_amount_raises_error(self):
        """Verify zero or negative loan amount throws ValidationError."""
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        profile_id = uuid.uuid4()
        mock_applicant_repo.get_by_id.return_value = ApplicantProfile(id=profile_id)

        service = ApplicationService(
            db=self.mock_db,
            app_repo=mock_app_repo,
            applicant_repo=mock_applicant_repo,
        )

        with self.assertRaises(ValidationError):
            service.create_application({
                "applicant_profile_id": profile_id,
                "requested_loan_amount": Decimal("0.00"),
            })

    def test_application_valid_status_transitions(self):
        """Verify valid application status lifecycle transitions."""
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        service = ApplicationService(
            db=self.mock_db,
            app_repo=mock_app_repo,
            applicant_repo=mock_applicant_repo,
        )

        app_id = uuid.uuid4()
        app_mock = Application(id=app_id, status=ApplicationStatus.DRAFT)
        mock_app_repo.get_by_id.return_value = app_mock
        mock_app_repo.update_status.return_value = app_mock

        # DRAFT -> SUBMITTED (valid)
        service.update_status(app_id, ApplicationStatus.SUBMITTED)
        mock_app_repo.update_status.assert_called_with(
            app_mock, ApplicationStatus.SUBMITTED, commit=False, db=self.mock_db
        )

    def test_application_invalid_status_transitions(self):
        """Verify invalid transitions raise InvalidStateTransitionError."""
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        service = ApplicationService(
            db=self.mock_db,
            app_repo=mock_app_repo,
            applicant_repo=mock_applicant_repo,
        )

        app_id = uuid.uuid4()
        # Cannot jump DRAFT -> COMPLETED
        app_mock = Application(id=app_id, status=ApplicationStatus.DRAFT)
        mock_app_repo.get_by_id.return_value = app_mock

        with self.assertRaises(InvalidStateTransitionError):
            service.update_status(app_id, ApplicationStatus.COMPLETED)

        # Cannot jump SUBMITTED -> ASSESSED directly
        app_mock.status = ApplicationStatus.SUBMITTED
        with self.assertRaises(InvalidStateTransitionError):
            service.update_status(app_id, ApplicationStatus.ASSESSED)

        # Terminal COMPLETED cannot transition
        app_mock.status = ApplicationStatus.COMPLETED
        with self.assertRaises(InvalidStateTransitionError):
            service.update_status(app_id, ApplicationStatus.DRAFT)

    def test_consent_creation_validations(self):
        """Verify consent requires purpose and valid application/profile."""
        mock_consent_repo = MagicMock(spec=ConsentRepository)
        service = ConsentService(db=self.mock_db, consent_repo=mock_consent_repo)

        # Missing both application_id and profile_id
        with self.assertRaises(ValidationError):
            service.create_consent({
                "purpose": "Verify turnover",
                "data_source": ConsentDataSource.PLATFORM,
            })

        # Empty purpose
        with self.assertRaises(ValidationError):
            service.create_consent({
                "application_id": uuid.uuid4(),
                "purpose": "   ",
                "data_source": ConsentDataSource.PLATFORM,
            })

    def test_financial_signal_data_minimization_enforcement(self):
        """Verify FinancialSignalService rejects prohibited privacy-invasive data."""
        mock_signal_repo = MagicMock(spec=FinancialSignalRepository)
        service = FinancialSignalService(db=self.mock_db, signal_repo=mock_signal_repo)

        # Attempting to persist prohibited fields
        prohibited_payload = {
            "application_id": uuid.uuid4(),
            "source": SignalSource.PLATFORM,
            "raw_transactions": [{"txn_id": "123", "amount": 500}],
            "gps_coordinates": "12.9716, 77.5946",
        }
        with self.assertRaises(ValidationError):
            service.create_signal(prohibited_payload)

    def test_assessment_range_validations(self):
        """Verify probability and confidence must be between 0 and 1."""
        mock_assess_repo = MagicMock(spec=AssessmentRepository)
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_mv_repo = MagicMock(spec=ModelVersionRepository)

        app_id = uuid.uuid4()
        mv_id = uuid.uuid4()
        mock_app_repo.get_by_id.return_value = Application(id=app_id)
        mock_mv_repo.get_by_id.return_value = ModelVersion(id=mv_id)

        service = AssessmentService(
            db=self.mock_db,
            assessment_repo=mock_assess_repo,
            app_repo=mock_app_repo,
            model_version_repo=mock_mv_repo,
        )

        with self.assertRaises(ValidationError):
            service.create_assessment({
                "application_id": app_id,
                "model_version_id": mv_id,
                "risk_level": RiskLevel.MODERATE,
                "risk_probability": Decimal("1.5"),  # Invalid > 1
            })

        with self.assertRaises(ValidationError):
            service.create_assessment({
                "application_id": app_id,
                "model_version_id": mv_id,
                "risk_level": RiskLevel.MODERATE,
                "confidence": Decimal("-0.1"),  # Invalid < 0
            })

    def test_model_version_validations(self):
        """Verify ModelVersionService enforces required fields and handles missing records."""
        mock_mv_repo = MagicMock(spec=ModelVersionRepository)
        service = ModelVersionService(db=self.mock_db, model_version_repo=mock_mv_repo)

        with self.assertRaises(ValidationError):
            service.create_model_version({"model_name": ""})

        mock_mv_repo.get_by_id.return_value = None
        with self.assertRaises(EntityNotFoundError):
            service.get_model_version(uuid.uuid4())

    def test_review_service_validations(self):
        """Verify ReviewService enforces reviewer and application existence."""
        mock_rev_repo = MagicMock(spec=ReviewRepository)
        mock_app_repo = MagicMock(spec=ApplicationRepository)
        mock_user_repo = MagicMock(spec=UserRepository)

        service = ReviewService(
            db=self.mock_db,
            review_repo=mock_rev_repo,
            app_repo=mock_app_repo,
            user_repo=mock_user_repo,
        )

        app_id = uuid.uuid4()
        rev_id = uuid.uuid4()
        mock_app_repo.get_by_id.return_value = None  # App missing

        with self.assertRaises(EntityNotFoundError):
            service.create_review({
                "application_id": app_id,
                "reviewer_id": rev_id,
                "outcome": ReviewOutcomeType.REVIEWED,
            })


class TestServicesEndToEndInMemory(unittest.TestCase):
    """End-to-end service integration tests using an isolated in-memory SQLite database."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        self.db: Session = self.SessionLocal()
        self.user_service = UserService(db=self.db)
        self.applicant_service = ApplicantService(db=self.db)
        self.app_service = ApplicationService(db=self.db)
        self.consent_service = ConsentService(db=self.db)
        self.signal_service = FinancialSignalService(db=self.db)
        self.mv_service = ModelVersionService(db=self.db)
        self.assess_service = AssessmentService(db=self.db)
        self.review_service = ReviewService(db=self.db)

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_complete_application_lifecycle_workflow(self):
        """Exercise full end-to-end business flow across all services."""
        # 1. Register User
        user = self.user_service.create_user(
            UserCreate(
                email="workflow_user@example.com",
                role=UserRole.APPLICANT,
                password="securepassword123",
            )
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "workflow_user@example.com")

        # 2. Create ApplicantProfile
        profile = self.applicant_service.create_profile(
            ApplicantProfileCreate(
                gig_work_type="Delivery Partner",
                years_working=Decimal("2.5"),
                average_working_days=25,
                business_or_loan_purpose="Vehicle Upgrades",
            ),
            user_id=user.id,
        )
        self.assertIsNotNone(profile.id)
        self.assertEqual(profile.user_id, user.id)

        # 3. Create Application
        application = self.app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
                loan_purpose="Maintenance",
            )
        )
        self.assertIsNotNone(application.id)
        self.assertEqual(application.status, ApplicationStatus.DRAFT)

        # 4. Progress Application Status through valid lifecycle
        app_sub = self.app_service.update_status(application.id, ApplicationStatus.SUBMITTED)
        self.assertEqual(app_sub.status, ApplicationStatus.SUBMITTED)

        app_review = self.app_service.update_status(application.id, ApplicationStatus.UNDER_REVIEW)
        self.assertEqual(app_review.status, ApplicationStatus.UNDER_REVIEW)

        app_manual = self.app_service.update_status(application.id, ApplicationStatus.MANUAL_REVIEW)
        self.assertEqual(app_manual.status, ApplicationStatus.MANUAL_REVIEW)

        app_assessed = self.app_service.update_status(application.id, ApplicationStatus.ASSESSED)
        self.assertEqual(app_assessed.status, ApplicationStatus.ASSESSED)

        app_completed = self.app_service.update_status(application.id, ApplicationStatus.COMPLETED)
        self.assertEqual(app_completed.status, ApplicationStatus.COMPLETED)

        # 5. Record and Revoke Consent
        consent = self.consent_service.create_consent(
            ConsentCreate(
                application_id=application.id,
                applicant_profile_id=profile.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Assess monthly ride earnings",
            )
        )
        self.assertTrue(consent.granted)
        active_consents = self.consent_service.get_active_consents(application_id=application.id)
        self.assertEqual(len(active_consents), 1)

        revoked_consent = self.consent_service.revoke_consent(consent.id)
        self.assertFalse(revoked_consent.granted)
        self.assertIsNotNone(revoked_consent.revoked_at)
        active_after = self.consent_service.get_active_consents(application_id=application.id)
        self.assertEqual(len(active_after), 0)

        # 6. Record Financial Signals (Aggregated only)
        signal = self.signal_service.create_signal(
            FinancialSignalCreate(
                application_id=application.id,
                applicant_profile_id=profile.id,
                source=SignalSource.PLATFORM,
                average_income=Decimal("35000.00"),
                payment_regularity=Decimal("0.9400"),
                cashflow_buffer=Decimal("5000.00"),
            )
        )
        self.assertIsNotNone(signal.id)
        latest_sig = self.signal_service.get_latest_signal(application.id)
        self.assertIsNotNone(latest_sig)
        self.assertEqual(latest_sig.average_income, Decimal("35000.00"))

        # 7. Model Version & Assessment
        mv = self.mv_service.create_model_version(
            ModelVersionCreate(
                model_name="parakh_risk_v1",
                version="1.0.0",
                algorithm="GradientBoosting",
                is_active=True,
            )
        )
        active_mv = self.mv_service.get_active_model("parakh_risk_v1")
        self.assertIsNotNone(active_mv)
        self.assertEqual(active_mv.version, "1.0.0")

        assessment = self.assess_service.create_assessment(
            CreditAssessmentCreate(
                application_id=application.id,
                model_version_id=mv.id,
                credit_score=710,
                risk_probability=Decimal("0.1200"),
                risk_level=RiskLevel.LOWER,
                confidence=Decimal("0.8900"),
            )
        )
        self.assertIsNotNone(assessment.id)
        latest_assess = self.assess_service.get_latest_assessment(application.id)
        self.assertIsNotNone(latest_assess)
        self.assertEqual(latest_assess.credit_score, 710)

        # 8. Human Review Outcome
        reviewer = self.user_service.create_user(
            UserCreate(
                email="officer_review@example.com",
                role=UserRole.REVIEWER,
                password="securepassword123",
            )
        )
        review = self.review_service.create_review(
            ReviewOutcomeCreate(
                application_id=application.id,
                reviewer_id=reviewer.id,
                outcome=ReviewOutcomeType.REVIEWED,
                notes="Platform metrics corroborated by consistent delivery tenure.",
            )
        )
        self.assertIsNotNone(review.id)
        app_reviews = self.review_service.get_application_reviews(application.id)
        self.assertEqual(len(app_reviews), 1)
        self.assertEqual(app_reviews[0].outcome, ReviewOutcomeType.REVIEWED)


class TestServicesPostgresIntegration(unittest.TestCase):
    """Integration test suite executing transactional operations against live PostgreSQL."""

    @unittest.skipUnless(
        can_connect_to_postgres(),
        "Live PostgreSQL is not available. Skipping PostgreSQL integration tests.",
    )
    def test_live_postgres_user_and_applicant_service_transaction(self):
        """Test transaction rollback and cleanup against live PostgreSQL without polluting DB."""
        from app.core.database import SessionLocal
        db: Session = SessionLocal()
        try:
            user_service = UserService(db=db)
            applicant_service = ApplicantService(db=db)

            # Create test user
            unique_email = f"live_svc_test_{uuid.uuid4().hex[:8]}@example.com"
            user = user_service.create_user({"email": unique_email, "role": UserRole.APPLICANT})
            self.assertIsNotNone(user.id)

            # Create test profile
            profile = applicant_service.create_profile({
                "user_id": user.id,
                "gig_work_type": "Live Courier",
            })
            self.assertIsNotNone(profile.id)

            # Clean up test records immediately
            from sqlalchemy import text
            db.execute(text("DELETE FROM audit_logs WHERE user_id = :u OR entity_id = :u_str OR entity_id = :p_str"), {"u": user.id, "u_str": str(user.id), "p_str": str(profile.id)})
            db.delete(profile)
            db.delete(user)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
