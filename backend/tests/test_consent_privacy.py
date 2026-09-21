"""Comprehensive unit and integration tests for PARAKH consent and privacy enforcement."""
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
    Base,
    Consent,
    ConsentDataSource,
    FinancialSignal,
    SignalSource,
    User,
    UserRole,
)
from app.repositories import (
    ApplicantRepository,
    ApplicationRepository,
    ConsentRepository,
    FinancialSignalRepository,
)
from app.schemas.consent import ConsentCreate
from app.schemas.financial_signal import FinancialSignalCreate
from app.services import (
    ConsentRequiredError,
    ConsentService,
    EntityNotFoundError,
    FinancialSignalService,
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


class TestConsentPrivacyUnitWithMocks(unittest.TestCase):
    """Unit tests isolating consent verification rules using mocks."""

    def setUp(self):
        self.mock_db = MagicMock(spec=Session)
        self.mock_consent_repo = MagicMock(spec=ConsentRepository)
        self.mock_app_repo = MagicMock(spec=ApplicationRepository)
        self.mock_applicant_repo = MagicMock(spec=ApplicantRepository)
        self.service = ConsentService(
            db=self.mock_db,
            consent_repo=self.mock_consent_repo,
            app_repo=self.mock_app_repo,
            applicant_repo=self.mock_applicant_repo,
        )

    def test_valid_consent_creation(self):
        """Verify successful consent creation with matching application and profile."""
        app_id = uuid.uuid4()
        profile_id = uuid.uuid4()
        app_mock = Application(id=app_id, applicant_profile_id=profile_id)
        profile_mock = ApplicantProfile(id=profile_id)

        self.mock_app_repo.get_by_id.return_value = app_mock
        self.mock_applicant_repo.get_by_id.return_value = profile_mock

        consent_in = ConsentCreate(
            application_id=app_id,
            applicant_profile_id=profile_id,
            data_source=ConsentDataSource.PLATFORM,
            purpose="Assess delivery regularity",
        )
        self.service.create_consent(consent_in)

        self.mock_consent_repo.create.assert_called_once()
        created_data = self.mock_consent_repo.create.call_args[0][0]
        self.assertEqual(created_data["application_id"], app_id)
        self.assertEqual(created_data["applicant_profile_id"], profile_id)
        self.assertEqual(created_data["data_source"], ConsentDataSource.PLATFORM)
        self.assertTrue(created_data["granted"])
        self.assertIsNone(created_data["revoked_at"])
        self.mock_db.commit.assert_called_once()

    def test_missing_application_rejection(self):
        """Verify consent creation requires an existing application."""
        # 1. Missing application_id in payload
        with self.assertRaises(ValidationError):
            self.service.create_consent({
                "data_source": ConsentDataSource.PLATFORM,
                "purpose": "Verify earnings",
            })

        # 2. Application does not exist in database
        app_id = uuid.uuid4()
        self.mock_app_repo.get_by_id.return_value = None
        with self.assertRaises(EntityNotFoundError):
            self.service.create_consent({
                "application_id": app_id,
                "data_source": ConsentDataSource.PLATFORM,
                "purpose": "Verify earnings",
            })

    def test_incorrect_application_profile_association_rejection(self):
        """Verify mismatched applicant_profile_id is rejected."""
        app_id = uuid.uuid4()
        legit_profile_id = uuid.uuid4()
        attacker_profile_id = uuid.uuid4()

        app_mock = Application(id=app_id, applicant_profile_id=legit_profile_id)
        self.mock_app_repo.get_by_id.return_value = app_mock

        with self.assertRaises(ValidationError):
            self.service.create_consent({
                "application_id": app_id,
                "applicant_profile_id": attacker_profile_id,  # mismatch!
                "data_source": ConsentDataSource.PLATFORM,
                "purpose": "Unauthorized access attempt",
            })

    def test_active_consent_detection(self):
        """Verify active consent returns True for has_active_consent and returns object for require_active_consent."""
        app_id = uuid.uuid4()
        active_consent = Consent(
            id=uuid.uuid4(),
            application_id=app_id,
            data_source=ConsentDataSource.PLATFORM,
            granted=True,
            revoked_at=None,
        )
        self.mock_consent_repo.get_active_consent.return_value = active_consent

        self.assertTrue(
            self.service.has_active_consent(app_id, ConsentDataSource.PLATFORM)
        )
        retrieved = self.service.require_active_consent(app_id, ConsentDataSource.PLATFORM)
        self.assertEqual(retrieved.id, active_consent.id)

    def test_missing_consent_rejection(self):
        """Verify missing consent returns False and raises ConsentRequiredError."""
        app_id = uuid.uuid4()
        self.mock_consent_repo.get_active_consent.return_value = None

        self.assertFalse(
            self.service.has_active_consent(app_id, ConsentDataSource.UTILITY)
        )
        with self.assertRaises(ConsentRequiredError):
            self.service.require_active_consent(app_id, ConsentDataSource.UTILITY)

    def test_revoked_consent_rejection(self):
        """Verify revoked consent is rejected as inactive."""
        app_id = uuid.uuid4()
        # Repository query for active consent filters revoked_at IS NULL, so None is returned
        self.mock_consent_repo.get_active_consent.return_value = None

        self.assertFalse(
            self.service.has_active_consent(app_id, ConsentDataSource.FINANCIAL_ACTIVITY)
        )
        with self.assertRaises(ConsentRequiredError):
            self.service.require_active_consent(app_id, ConsentDataSource.FINANCIAL_ACTIVITY)

    def test_consent_from_another_application_rejected(self):
        """Verify consent for Application A never authorizes Application B."""
        app_a = uuid.uuid4()
        app_b = uuid.uuid4()

        # Mock repo simulates query filtered by application_id
        def mock_get_active(application_id, data_source, db=None):
            if application_id == app_a and data_source == ConsentDataSource.PLATFORM:
                return Consent(application_id=app_a, data_source=ConsentDataSource.PLATFORM, granted=True)
            return None

        self.mock_consent_repo.get_active_consent.side_effect = mock_get_active

        # Authorized for Application A
        self.assertTrue(self.service.has_active_consent(app_a, ConsentDataSource.PLATFORM))

        # Rejected for Application B
        self.assertFalse(self.service.has_active_consent(app_b, ConsentDataSource.PLATFORM))
        with self.assertRaises(ConsentRequiredError):
            self.service.require_active_consent(app_b, ConsentDataSource.PLATFORM)

    def test_independent_consent_categories(self):
        """Verify PLATFORM, FINANCIAL_ACTIVITY, and UTILITY consents are evaluated independently."""
        app_id = uuid.uuid4()

        # Application has PLATFORM active, FINANCIAL_ACTIVITY revoked/missing, UTILITY active
        def mock_category_lookup(application_id, data_source, db=None):
            if application_id == app_id:
                if data_source == ConsentDataSource.PLATFORM:
                    return Consent(application_id=app_id, data_source=ConsentDataSource.PLATFORM, granted=True)
                elif data_source == ConsentDataSource.UTILITY:
                    return Consent(application_id=app_id, data_source=ConsentDataSource.UTILITY, granted=True)
            return None

        self.mock_consent_repo.get_active_consent.side_effect = mock_category_lookup

        # PLATFORM -> authorized
        self.assertTrue(self.service.has_active_consent(app_id, ConsentDataSource.PLATFORM))
        self.assertIsNotNone(self.service.require_active_consent(app_id, ConsentDataSource.PLATFORM))

        # FINANCIAL_ACTIVITY -> unauthorized
        self.assertFalse(self.service.has_active_consent(app_id, ConsentDataSource.FINANCIAL_ACTIVITY))
        with self.assertRaises(ConsentRequiredError):
            self.service.require_active_consent(app_id, ConsentDataSource.FINANCIAL_ACTIVITY)

        # UTILITY -> authorized
        self.assertTrue(self.service.has_active_consent(app_id, ConsentDataSource.UTILITY))
        self.assertIsNotNone(self.service.require_active_consent(app_id, ConsentDataSource.UTILITY))

    def test_revocation_persistence(self):
        """Verify revoking consent stamps revoked_at and sets granted=False without deleting record."""
        consent_id = uuid.uuid4()
        existing = Consent(
            id=consent_id,
            granted=True,
            revoked_at=None,
        )
        self.mock_consent_repo.get_by_id.return_value = existing
        self.mock_consent_repo.revoke.return_value = Consent(
            id=consent_id,
            granted=False,
            revoked_at=datetime.now(timezone.utc),
        )

        revoked = self.service.revoke_consent(consent_id)
        self.assertFalse(revoked.granted)
        self.assertIsNotNone(revoked.revoked_at)
        self.mock_consent_repo.delete.assert_not_called()
        self.mock_db.commit.assert_called_once()

    def test_privacy_data_minimization_rejection(self):
        """Verify FinancialSignalService rigorously rejects raw, invasive, or non-aggregated fields."""
        mock_signal_repo = MagicMock(spec=FinancialSignalRepository)
        signal_service = FinancialSignalService(
            db=self.mock_db,
            signal_repo=mock_signal_repo,
            app_repo=self.mock_app_repo,
            consent_service=self.service,
        )

        invasive_inputs = [
            {"raw_transactions": [{"id": 1, "amt": 500}]},
            {"raw_bank_statements": "PDF base64 statement data"},
            {"raw_upi_transactions": ["txn1", "txn2"]},
            {"raw_upi_logs": "upi log string"},
            {"upi_vpa": "user@okaxis"},
            {"bank_account_number": "1234567890"},
            {"bank_credentials": {"pin": "1234"}},
            {"banking_login_credentials": "password"},
            {"merchant_name": "Cafe Coffee Day"},
            {"merchant_description": "Coffee and snacks"},
            {"merchant_details": {"m_id": 99}},
            {"gps_coordinates": "12.9716, 77.5946"},
            {"location_history": ["loc1", "loc2"]},
            {"contact_list": ["friend1", "friend2"]},
            {"contacts": ["9876543210"]},
            {"password": "secretpassword"},
            {"password_hash": "hash_val"},
        ]

        app_id = uuid.uuid4()
        self.mock_app_repo.get_by_id.return_value = Application(id=app_id)

        for invasive_field in invasive_inputs:
            payload = {
                "application_id": app_id,
                "source": SignalSource.PLATFORM,
                "average_income": Decimal("25000.00"),
                **invasive_field,
            }
            with self.assertRaises(ValidationError, msg=f"Failed to reject field {list(invasive_field.keys())}"):
                signal_service.create_signal(payload)

        mock_signal_repo.create.assert_not_called()


class TestConsentPrivacyEndToEnd(unittest.TestCase):
    """End-to-end consent lifecycle and authorization workflow using in-memory database."""

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
        self.consent_service = ConsentService(db=self.db)
        self.signal_service = FinancialSignalService(
            db=self.db, consent_service=self.consent_service
        )

        # Setup base applicant and application with unique emails
        unique_suffix = uuid.uuid4().hex[:8]
        user_a = User(email=f"applicant_a_{unique_suffix}@example.com", role=UserRole.APPLICANT)
        self.db.add(user_a)
        self.db.flush()

        profile_a = ApplicantProfile(user_id=user_a.id, gig_work_type="Delivery")
        self.db.add(profile_a)
        self.db.flush()

        self.app_a = Application(
            applicant_profile_id=profile_a.id,
            requested_loan_amount=Decimal("10000.00"),
        )
        self.db.add(self.app_a)
        self.db.flush()

        # Setup second applicant and application (for cross-application tests)
        user_b = User(email=f"applicant_b_{unique_suffix}@example.com", role=UserRole.APPLICANT)
        self.db.add(user_b)
        self.db.flush()

        self.profile_b = ApplicantProfile(user_id=user_b.id, gig_work_type="Rider")
        self.db.add(self.profile_b)
        self.db.flush()

        self.app_b = Application(
            applicant_profile_id=self.profile_b.id,
            requested_loan_amount=Decimal("20000.00"),
        )
        self.db.add(self.app_b)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_full_consent_lifecycle_and_independent_categories(self):
        """Test full consent granting, independent checks, revocation, and re-granting."""
        # Initially, no active consent
        self.assertFalse(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        )
        with self.assertRaises(ConsentRequiredError):
            self.consent_service.require_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)

        # Grant PLATFORM consent
        consent_platform = self.consent_service.create_consent(
            ConsentCreate(
                application_id=self.app_a.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Evaluate delivery regularity",
            )
        )
        self.assertTrue(consent_platform.granted)
        self.assertIsNone(consent_platform.revoked_at)
        self.assertTrue(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        )

        # Grant UTILITY consent
        consent_utility = self.consent_service.create_consent(
            ConsentCreate(
                application_id=self.app_a.id,
                data_source=ConsentDataSource.UTILITY,
                purpose="Evaluate telecom payment reliability",
            )
        )
        self.assertTrue(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.UTILITY)
        )

        # FINANCIAL_ACTIVITY was never granted -> unauthorized
        self.assertFalse(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.FINANCIAL_ACTIVITY)
        )
        with self.assertRaises(ConsentRequiredError):
            self.consent_service.require_active_consent(self.app_a.id, ConsentDataSource.FINANCIAL_ACTIVITY)

        # Revoke PLATFORM consent
        self.consent_service.revoke_consent(consent_platform.id)
        self.assertFalse(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        )
        with self.assertRaises(ConsentRequiredError):
            self.consent_service.require_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)

        # UTILITY must remain authorized (independent categories)
        self.assertTrue(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.UTILITY)
        )

        # Re-grant PLATFORM consent (deterministic re-consent lifecycle)
        consent_platform_v2 = self.consent_service.create_consent(
            ConsentCreate(
                application_id=self.app_a.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Re-grant delivery regularity access",
            )
        )
        self.assertTrue(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        )
        active_consent = self.consent_service.require_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        self.assertEqual(active_consent.id, consent_platform_v2.id)

    def test_cross_application_consent_isolation(self):
        """Verify Application A consent never authorizes Application B."""
        # Grant PLATFORM consent on App A
        self.consent_service.create_consent(
            ConsentCreate(
                application_id=self.app_a.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="App A delivery metrics",
            )
        )

        # App A is authorized
        self.assertTrue(
            self.consent_service.has_active_consent(self.app_a.id, ConsentDataSource.PLATFORM)
        )

        # App B must NOT be authorized
        self.assertFalse(
            self.consent_service.has_active_consent(self.app_b.id, ConsentDataSource.PLATFORM)
        )
        with self.assertRaises(ConsentRequiredError):
            self.consent_service.require_active_consent(self.app_b.id, ConsentDataSource.PLATFORM)

        # Cross-profile ownership violation: attempt to create consent for App A with Profile B
        with self.assertRaises(ValidationError):
            self.consent_service.create_consent(
                ConsentCreate(
                    application_id=self.app_a.id,
                    applicant_profile_id=self.profile_b.id,  # Mismatch!
                    data_source=ConsentDataSource.PLATFORM,
                    purpose="Spoofed profile",
                )
            )

    def test_financial_signal_service_consent_enforcement(self):
        """Verify FinancialSignalService with consent enforcement allows authorized and blocks unauthorized data."""
        # 1. Without consent, creating PLATFORM signal with consent enforcement raises ConsentRequiredError
        signal_data = FinancialSignalCreate(
            application_id=self.app_a.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("30000.00"),
            payment_regularity=Decimal("0.9500"),
        )
        with self.assertRaises(ConsentRequiredError):
            self.signal_service.create_signal_with_consent(signal_data)

        # 2. Grant PLATFORM consent
        self.consent_service.create_consent(
            ConsentCreate(
                application_id=self.app_a.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Access earnings signals",
            )
        )

        # 3. Now creating PLATFORM signal with consent enforcement succeeds
        persisted_sig = self.signal_service.create_signal_with_consent(signal_data)
        self.assertIsNotNone(persisted_sig.id)
        self.assertEqual(persisted_sig.average_income, Decimal("30000.00"))


class TestConsentPrivacyPostgresIntegration(unittest.TestCase):
    """Integration test against live PostgreSQL database."""

    @unittest.skipUnless(
        can_connect_to_postgres(),
        "Live PostgreSQL is not available. Skipping integration test.",
    )
    def test_live_postgres_consent_lifecycle(self):
        """Execute full consent grant, active check, and revocation on live PostgreSQL with clean rollback."""
        from app.core.database import SessionLocal
        db: Session = SessionLocal()
        try:
            consent_service = ConsentService(db=db)

            # Create test user, profile, application
            user = User(
                email=f"pg_consent_{uuid.uuid4().hex[:8]}@example.com",
                role=UserRole.APPLICANT,
            )
            db.add(user)
            db.flush()

            profile = ApplicantProfile(user_id=user.id, gig_work_type="Driver")
            db.add(profile)
            db.flush()

            app = Application(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("12000.00"),
            )
            db.add(app)
            db.flush()

            # Grant consent
            consent = consent_service.create_consent({
                "application_id": app.id,
                "data_source": ConsentDataSource.PLATFORM,
                "purpose": "Live PostgreSQL verification",
            })
            self.assertIsNotNone(consent.id)
            self.assertTrue(consent_service.has_active_consent(app.id, ConsentDataSource.PLATFORM))

            # Revoke consent
            consent_service.revoke_consent(consent.id)
            self.assertFalse(consent_service.has_active_consent(app.id, ConsentDataSource.PLATFORM))

            # Clean up test rows
            db.delete(consent)
            db.delete(app)
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
