"""Comprehensive test suite for TASK 13 — Audit Logging.

Tests cover:
1. AuditService can record an event.
2. AuditRepository persistence works.
3. Actor/user information is recorded correctly.
4. Role information is recorded correctly.
5. Resource/entity information is recorded correctly.
6. Successful login generates audit event.
7. Failed login generates audit event.
8. Authorization failure generates audit event.
9. User creation generates audit event.
10. User update generates audit event.
11. Role change generates audit event.
12. Applicant creation generates audit event.
13. Application creation generates audit event.
14. Application status transition generates audit event.
15. Consent grant generates audit event.
16. Consent revocation generates audit event.
17. Financial signal ingestion generates audit event.
18. Assessment execution generates audit event.
19. Model version creation generates audit event.
20. Review creation generates audit event.
21. Password is never present in audit logs.
22. password_hash is never present in audit logs.
23. JWT is never present in audit logs.
24. SECRET_KEY is never present in audit logs.
25. Raw transaction data is rejected/sanitized.
26. Bank credentials are rejected/sanitized.
27. UPI identifiers are rejected/sanitized.
28. GPS/location data is rejected/sanitized.
29. Contact-list data is rejected/sanitized.
30. Failed business operations do not create misleading successful audit events.
31. Audit records survive normal business transaction persistence.
32. Audit retrieval, if implemented, enforces admin authorization.
33. Live PostgreSQL audit lifecycle.
34. Full end-to-end authenticated workflow produces expected audit trail.
"""
from decimal import Decimal
import unittest
from unittest.mock import MagicMock
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_active_user, get_db
from app.core.audit_events import AuditAction, AuditOutcome
from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.audit import AuditLog
from app.models.consent import Consent, ConsentDataSource
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.review import ReviewOutcome, ReviewOutcomeType
from app.models.user import User, UserRole
from app.repositories.audit import AuditRepository
from app.schemas.applicant import ApplicantProfileCreate, ApplicantProfileUpdate
from app.schemas.application import ApplicationCreate
from app.schemas.assessment import CreditAssessmentCreate
from app.schemas.consent import ConsentCreate
from app.schemas.financial_signal import FinancialSignalCreate
from app.schemas.model_version import ModelVersionCreate
from app.schemas.review import ReviewOutcomeCreate
from app.schemas.user import UserCreate, UserUpdate
from app.services.applicant import ApplicantService
from app.services.application import ApplicationService
from app.services.assessment import AssessmentService
from app.services.audit import AuditService, sanitize_audit_metadata
from app.services.consent import ConsentService
from app.services.exceptions import AuditLoggingError, ValidationError
from app.services.financial_signal import FinancialSignalService
from app.services.model_version import ModelVersionService
from app.services.review import ReviewService
from app.services.user import UserService


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable."""
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


class TestAuditUnitAndSanitization(unittest.TestCase):
    """Unit tests for AuditService, AuditRepository, and privacy sanitization rules."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.audit_service = AuditService(db=self.session)
        self.audit_repo = AuditRepository(db=self.session)

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_01_audit_service_can_record_an_event(self):
        """1. Verify AuditService can successfully record an event."""
        log = self.audit_service.record_event(
            action=AuditAction.USER_CREATED,
            entity_type="User",
            entity_id=str(uuid.uuid4()),
            outcome=AuditOutcome.SUCCESS,
            metadata={"detail": "Test record"},
            commit=True,
        )
        self.assertIsNotNone(log.id)
        self.assertEqual(log.action, AuditAction.USER_CREATED)
        self.assertEqual(log.entity_type, "User")
        self.assertEqual(log.audit_metadata.get("outcome"), AuditOutcome.SUCCESS)

    def test_02_audit_repository_persistence_works(self):
        """2. Verify AuditRepository direct persistence and query methods work."""
        app_id = uuid.uuid4()
        user_id = uuid.uuid4()
        entry = AuditLog(
            user_id=user_id,
            application_id=app_id,
            action=AuditAction.APPLICATION_CREATED,
            entity_type="Application",
            entity_id=str(app_id),
            audit_metadata={"outcome": AuditOutcome.SUCCESS},
        )
        saved = self.audit_repo.create(entry, commit=True, db=self.session)
        self.assertIsNotNone(saved.id)

        by_app = self.audit_repo.get_by_application(app_id, db=self.session)
        self.assertEqual(len(by_app), 1)
        self.assertEqual(by_app[0].id, saved.id)

        by_user = self.audit_repo.get_by_user(user_id, db=self.session)
        self.assertEqual(len(by_user), 1)
        self.assertEqual(by_user[0].id, saved.id)

        filtered = self.audit_repo.list_audit_logs(
            action=AuditAction.APPLICATION_CREATED,
            entity_type="Application",
            db=self.session,
        )
        self.assertEqual(len(filtered), 1)

    def test_03_actor_user_information_is_recorded_correctly(self):
        """3. Verify actor/user ID is recorded and parsed accurately."""
        actor_id = uuid.uuid4()
        log = self.audit_service.record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="Authentication",
            user_id=actor_id,
            commit=True,
        )
        self.assertEqual(log.user_id, actor_id)

    def test_04_role_information_is_recorded_correctly(self):
        """4. Verify actor role information is recorded in metadata."""
        log = self.audit_service.record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="Authentication",
            actor_role=UserRole.APPLICANT,
            commit=True,
        )
        self.assertEqual(log.audit_metadata.get("actor_role"), UserRole.APPLICANT.value)

    def test_05_resource_entity_information_is_recorded_correctly(self):
        """5. Verify entity_type and entity_id are recorded correctly."""
        test_id = str(uuid.uuid4())
        log = self.audit_service.record_event(
            action=AuditAction.CONSENT_GRANTED,
            entity_type="Consent",
            entity_id=test_id,
            commit=True,
        )
        self.assertEqual(log.entity_type, "Consent")
        self.assertEqual(log.entity_id, test_id)

    def test_21_password_is_never_present_in_audit_logs(self):
        """21. Verify plaintext passwords are automatically stripped/sanitized."""
        meta = {"email": "user@example.com", "password": "SuperSecretPassword123!"}
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("password", sanitized)
        self.assertIn("email", sanitized)

        log = self.audit_service.record_event(
            action=AuditAction.USER_CREATED,
            entity_type="User",
            metadata=meta,
            commit=True,
        )
        self.assertNotIn("password", log.audit_metadata)

    def test_22_password_hash_is_never_present_in_audit_logs(self):
        """22. Verify password_hash is automatically stripped/sanitized."""
        meta = {
            "user_id": str(uuid.uuid4()),
            "password_hash": "$2b$12$e8k6m0p1q2r3s4t5u6v7w8x9y0z1a2b3c4d5e6f7g8h9i0j1k2l3",
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("password_hash", sanitized)

        log = self.audit_service.record_event(
            action=AuditAction.USER_UPDATED,
            entity_type="User",
            metadata=meta,
            commit=True,
        )
        self.assertNotIn("password_hash", log.audit_metadata)

    def test_23_jwt_is_never_present_in_audit_logs(self):
        """23. Verify JWT tokens and bearer strings are stripped or redacted."""
        raw_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotStoreThisSignature"
        meta = {
            "token": raw_jwt,
            "jwt": raw_jwt,
            "authorization": f"Bearer {raw_jwt}",
            "nested": {"custom_encoded_data": raw_jwt},
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("token", sanitized)
        self.assertNotIn("jwt", sanitized)
        self.assertNotIn("authorization", sanitized)
        self.assertEqual(sanitized["nested"]["custom_encoded_data"], "[REDACTED_TOKEN]")

    def test_24_secret_key_is_never_present_in_audit_logs(self):
        """24. Verify SECRET_KEY and secret tokens are stripped."""
        meta = {"secret_key": "top-secret-backend-key", "api_key": "xyz123"}
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("secret_key", sanitized)
        self.assertNotIn("api_key", sanitized)

    def test_25_raw_transaction_data_is_rejected_sanitized(self):
        """25. Verify raw transaction data and statements are stripped."""
        meta = {
            "raw_transactions": [{"id": 1, "amount": 500}],
            "raw_bank_statements": "Statement text...",
            "safe_metric": 42,
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("raw_transactions", sanitized)
        self.assertNotIn("raw_bank_statements", sanitized)
        self.assertEqual(sanitized["safe_metric"], 42)

    def test_26_bank_credentials_are_rejected_sanitized(self):
        """26. Verify bank credentials and account numbers are stripped."""
        meta = {
            "bank_account_number": "123456789012",
            "bank_credentials": {"user": "bank_user", "pin": "1234"},
            "account_number": "9876543210",
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("bank_account_number", sanitized)
        self.assertNotIn("bank_credentials", sanitized)
        self.assertNotIn("account_number", sanitized)

    def test_27_upi_identifiers_are_rejected_sanitized(self):
        """27. Verify UPI IDs and VPAs are stripped."""
        meta = {"upi_vpa": "worker@upi", "upi_id": "9876543210@paytm", "vpa": "gig@okaxis"}
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("upi_vpa", sanitized)
        self.assertNotIn("upi_id", sanitized)
        self.assertNotIn("vpa", sanitized)

    def test_28_gps_location_data_is_rejected_sanitized(self):
        """28. Verify GPS and location coordinates are stripped."""
        meta = {
            "gps_coordinates": {"lat": 12.9716, "lon": 77.5946},
            "location_history": ["loc1", "loc2"],
            "coordinates": "12.9716,77.5946",
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("gps_coordinates", sanitized)
        self.assertNotIn("location_history", sanitized)
        self.assertNotIn("coordinates", sanitized)

    def test_29_contact_list_data_is_rejected_sanitized(self):
        """29. Verify contact lists and address books are stripped."""
        meta = {
            "contact_list": ["Friend 1", "Friend 2"],
            "contacts": [{"name": "Contact 1"}],
            "address_book": "Data",
        }
        sanitized = sanitize_audit_metadata(meta)
        self.assertNotIn("contact_list", sanitized)
        self.assertNotIn("contacts", sanitized)
        self.assertNotIn("address_book", sanitized)

    def test_audit_failure_raises_audit_logging_error(self):
        """Verify audit persistence failure logs and raises AuditLoggingError."""
        mock_repo = MagicMock(spec=AuditRepository)
        mock_repo.create.side_effect = Exception("DB Disk Full")
        service = AuditService(db=self.session, audit_repo=mock_repo)

        with self.assertRaises(AuditLoggingError):
            service.record_event(
                action=AuditAction.LOGIN_SUCCESS,
                entity_type="Authentication",
            )


class TestAuditServiceDomainEvents(unittest.TestCase):
    """Integration tests verifying domain operations generate corresponding audit events."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.audit_repo = AuditRepository(db=self.session)

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_09_user_creation_generates_audit_event(self):
        """9. Verify UserService.create_user records USER_CREATED event."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="audit_user@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.USER_CREATED,
            entity_type="User",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, user.id)
        self.assertEqual(logs[0].audit_metadata.get("email"), "audit_user@example.com")
        self.assertNotIn("password", logs[0].audit_metadata)
        self.assertNotIn("password_hash", logs[0].audit_metadata)

    def test_10_user_update_generates_audit_event(self):
        """10. Verify UserService.update_user records USER_UPDATED event."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="audit_upd@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        user_service.update_user(user.id, UserUpdate(is_active=False))

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.USER_UPDATED,
            entity_type="User",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, user.id)

    def test_11_role_change_generates_audit_event(self):
        """11. Verify changing a user's role records USER_ROLE_CHANGED event."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="audit_role@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        user_service.update_user(user.id, UserUpdate(role=UserRole.REVIEWER))

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.USER_ROLE_CHANGED,
            entity_type="User",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].audit_metadata.get("previous_role"), UserRole.APPLICANT.value)
        self.assertEqual(logs[0].audit_metadata.get("new_role"), UserRole.REVIEWER.value)

    def test_12_applicant_creation_generates_audit_event(self):
        """12. Verify ApplicantService.create_profile records APPLICANT_PROFILE_CREATED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="worker_prof@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(
                user_id=user.id,
                gig_work_type="Delivery",
                primary_platform="Swiggy",
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.APPLICANT_PROFILE_CREATED,
            entity_type="ApplicantProfile",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, user.id)
        self.assertEqual(logs[0].audit_metadata.get("gig_work_type"), "Delivery")

    def test_13_application_creation_generates_audit_event(self):
        """13. Verify ApplicationService.create_application records APPLICATION_CREATED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="app_create@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Rideshare")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("25000.00"),
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.APPLICATION_CREATED,
            entity_type="Application",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)

    def test_14_application_status_transition_generates_audit_event(self):
        """14. Verify ApplicationService.update_status records APPLICATION_STATUS_CHANGED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="app_trans@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Rideshare")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("25000.00"),
            )
        )
        # Advance status: DRAFT -> SUBMITTED
        app_service.update_status(application.id, ApplicationStatus.SUBMITTED)

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.APPLICATION_STATUS_CHANGED,
            entity_type="Application",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].audit_metadata.get("previous_status"), ApplicationStatus.DRAFT.value)
        self.assertEqual(logs[0].audit_metadata.get("new_status"), ApplicationStatus.SUBMITTED.value)

    def test_15_consent_grant_generates_audit_event(self):
        """15. Verify ConsentService.create_consent records CONSENT_GRANTED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="consent_grant@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Delivery")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
            )
        )
        consent_service = ConsentService(db=self.session)
        consent = consent_service.create_consent(
            ConsentCreate(
                application_id=application.id,
                applicant_profile_id=profile.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Platform earnings verification",
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.CONSENT_GRANTED,
            entity_type="Consent",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)
        self.assertEqual(logs[0].audit_metadata.get("data_source"), ConsentDataSource.PLATFORM.value)

    def test_16_consent_revocation_generates_audit_event(self):
        """16. Verify ConsentService.revoke_consent records CONSENT_REVOKED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="consent_revoke@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Delivery")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
            )
        )
        consent_service = ConsentService(db=self.session)
        consent = consent_service.create_consent(
            ConsentCreate(
                application_id=application.id,
                applicant_profile_id=profile.id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Platform earnings verification",
            )
        )
        consent_service.revoke_consent(consent.id)

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.CONSENT_REVOKED,
            entity_type="Consent",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)

    def test_17_financial_signal_ingestion_generates_audit_event(self):
        """17. Verify FinancialSignalService.create_signal records FINANCIAL_SIGNAL_CREATED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="sig_audit@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Delivery")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
            )
        )
        signal_service = FinancialSignalService(db=self.session)
        signal_service.create_signal(
            FinancialSignalCreate(
                application_id=application.id,
                source=SignalSource.PLATFORM,
                average_income=Decimal("35000.00"),
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.FINANCIAL_SIGNAL_CREATED,
            entity_type="FinancialSignal",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)
        self.assertEqual(logs[0].audit_metadata.get("source"), SignalSource.PLATFORM.value)

    def test_18_assessment_execution_generates_audit_event(self):
        """18. Verify AssessmentService.create_assessment records ASSESSMENT_EXECUTED."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="assess_audit@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=user.id, gig_work_type="Delivery")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
            )
        )
        mv_service = ModelVersionService(db=self.session)
        mv = mv_service.create_model_version(
            ModelVersionCreate(
                model_name="parakh-mock-v1",
                version="1.0.0",
                is_active=True,
            )
        )
        assessment_service = AssessmentService(db=self.session)
        assessment_service.create_assessment(
            CreditAssessmentCreate(
                application_id=application.id,
                model_version_id=mv.id,
                credit_score=720,
                risk_level=RiskLevel.LOWER,
                risk_probability=Decimal("0.12"),
                confidence=Decimal("0.90"),
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.ASSESSMENT_EXECUTED,
            entity_type="CreditAssessment",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)
        self.assertEqual(logs[0].audit_metadata.get("risk_level"), RiskLevel.LOWER.value)

    def test_19_model_version_creation_generates_audit_event(self):
        """19. Verify ModelVersionService.create_model_version records MODEL_VERSION_CREATED."""
        mv_service = ModelVersionService(db=self.session)
        mv = mv_service.create_model_version(
            ModelVersionCreate(
                model_name="parakh-mock-v1",
                version="1.0.0",
                is_active=True,
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.MODEL_VERSION_CREATED,
            entity_type="ModelVersion",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].audit_metadata.get("model_name"), "parakh-mock-v1")
        self.assertEqual(logs[0].audit_metadata.get("version"), "1.0.0")

    def test_20_review_creation_generates_audit_event(self):
        """20. Verify ReviewService.create_review records REVIEW_CREATED."""
        user_service = UserService(db=self.session)
        reviewer = user_service.create_user(
            UserCreate(
                email="reviewer_audit@example.com",
                role=UserRole.REVIEWER,
                password="securePassword123!",
            )
        )
        applicant = user_service.create_user(
            UserCreate(
                email="applicant_audit@example.com",
                role=UserRole.APPLICANT,
                password="securePassword123!",
            )
        )
        applicant_service = ApplicantService(db=self.session)
        profile = applicant_service.create_profile(
            ApplicantProfileCreate(user_id=applicant.id, gig_work_type="Delivery")
        )
        app_service = ApplicationService(db=self.session)
        application = app_service.create_application(
            ApplicationCreate(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("15000.00"),
            )
        )
        review_service = ReviewService(db=self.session)
        review_service.create_review(
            ReviewOutcomeCreate(
                application_id=application.id,
                reviewer_id=reviewer.id,
                outcome=ReviewOutcomeType.REVIEWED,
                notes="Eligible based on stable delivery history",
            )
        )

        logs = self.audit_repo.list_audit_logs(
            action=AuditAction.REVIEW_CREATED,
            entity_type="ReviewOutcome",
            db=self.session,
        )
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].application_id, application.id)
        self.assertEqual(logs[0].user_id, reviewer.id)
        self.assertEqual(logs[0].audit_metadata.get("review_outcome"), ReviewOutcomeType.REVIEWED.value)

    def test_30_failed_business_operations_do_not_create_misleading_successful_audit_events(self):
        """30. Verify rollback on failed business operations ensures no misleading success events are persisted."""
        user_service = UserService(db=self.session)
        user_service.create_user(
            UserCreate(
                email="unique@example.com",
                role=UserRole.APPLICANT,
                password="password123",
            )
        )

        # Attempting duplicate user creation will raise DuplicateEntityError and rollback
        with self.assertRaises(Exception):
            user_service.create_user(
                UserCreate(
                    email="unique@example.com",
                    role=UserRole.APPLICANT,
                    password="password123",
                )
            )

        # Total USER_CREATED events should still be exactly 1
        logs = self.audit_repo.list_audit_logs(action=AuditAction.USER_CREATED, db=self.session)
        self.assertEqual(len(logs), 1)

    def test_31_audit_records_survive_normal_business_transaction_persistence(self):
        """31. Verify audit logs are committed atomically along with the business operation."""
        user_service = UserService(db=self.session)
        user = user_service.create_user(
            UserCreate(
                email="survive@example.com",
                role=UserRole.APPLICANT,
                password="password123",
            )
        )

        # Query in a fresh query on session
        found_user = user_service.get_user(user.id)
        self.assertIsNotNone(found_user)
        logs = self.audit_repo.list_audit_logs(action=AuditAction.USER_CREATED, db=self.session)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, found_user.id)


from sqlalchemy.pool import StaticPool


class TestAuditApiAndSecurity(unittest.TestCase):
    """API-level integration tests for authentication auditing and admin audit retrieval."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Pre-seed Admin and Applicant
        db = self.Session()
        self.admin_id = uuid.uuid4()
        self.applicant_id = uuid.uuid4()
        self.admin = User(
            id=self.admin_id,
            email="admin@parakh.local",
            password_hash=hash_password("adminSecret123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.applicant = User(
            id=self.applicant_id,
            email="applicant@parakh.local",
            password_hash=hash_password("applicantSecret123"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add_all([self.admin, self.applicant])
        db.commit()
        db.close()

        self.admin_token = create_access_token(subject=self.admin_id, role=UserRole.ADMIN.value)
        self.applicant_token = create_access_token(subject=self.applicant_id, role=UserRole.APPLICANT.value)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_06_successful_login_generates_audit_event(self):
        """6. Verify successful login generates AUTH_LOGIN_SUCCESS audit event."""
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "applicant@parakh.local", "password": "applicantSecret123"},
        )
        self.assertEqual(res.status_code, 200)

        db = self.Session()
        logs = AuditRepository(db=db).list_audit_logs(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="Authentication",
            db=db,
        )
        db.close()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, self.applicant_id)
        self.assertEqual(logs[0].audit_metadata.get("outcome"), "SUCCESS")

    def test_07_failed_login_generates_audit_event(self):
        """7. Verify failed login generates AUTH_LOGIN_FAILURE audit event."""
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "applicant@parakh.local", "password": "WrongPassword!"},
        )
        self.assertEqual(res.status_code, 401)

        db = self.Session()
        logs = AuditRepository(db=db).list_audit_logs(
            action=AuditAction.LOGIN_FAILURE,
            entity_type="Authentication",
            db=db,
        )
        db.close()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].audit_metadata.get("outcome"), "FAILURE")
        self.assertEqual(logs[0].audit_metadata.get("attempted_email"), "applicant@parakh.local")

    def test_08_authorization_failure_generates_audit_event(self):
        """8. Verify accessing an admin-only endpoint as applicant generates AUTH_ACCESS_DENIED audit event."""
        # Non-admin trying to access admin audit log endpoint
        res = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.applicant_token}"},
        )
        self.assertEqual(res.status_code, 403)

        db = self.Session()
        logs = AuditRepository(db=db).list_audit_logs(
            action=AuditAction.ACCESS_DENIED,
            entity_type="Security",
            db=db,
        )
        db.close()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].user_id, self.applicant_id)
        self.assertEqual(logs[0].audit_metadata.get("outcome"), "DENIED")

    def test_32_audit_retrieval_enforces_admin_authorization(self):
        """32. Verify audit retrieval endpoints enforce strict admin authorization."""
        # 1. Unauthenticated -> 401
        res1 = self.client.get("/api/v1/audit-logs")
        self.assertEqual(res1.status_code, 401)

        # 2. Applicant caller -> 403
        res2 = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.applicant_token}"},
        )
        self.assertEqual(res2.status_code, 403)

        # 3. Admin caller -> 200
        res3 = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res3.status_code, 200)
        self.assertIsInstance(res3.json(), list)


class TestAuditPostgresLiveIntegration(unittest.TestCase):
    """Live PostgreSQL database integration tests for audit logging lifecycle."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL database is not reachable.")
        cls.engine = create_engine(settings.DATABASE_URL)
        cls.Session = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "engine"):
            cls.engine.dispose()

    def setUp(self):
        self.session = self.Session()

    def tearDown(self):
        self.session.close()

    def test_33_live_postgres_audit_lifecycle(self):
        """33. Verify audit record creation, query, and cleanup against live PostgreSQL."""
        audit_service = AuditService(db=self.session)
        created = audit_service.record_event(
            action="TEST_LIVE_AUDIT",
            entity_type="TestEntity",
            entity_id="test-123",
            outcome=AuditOutcome.SUCCESS,
            metadata={"environment": "live_postgres"},
            commit=True,
        )
        self.assertIsNotNone(created.id)

        # Query back from postgres
        queried = audit_service.get_event(created.id)
        self.assertEqual(queried.action, "TEST_LIVE_AUDIT")
        self.assertEqual(queried.audit_metadata.get("environment"), "live_postgres")

        # Cleanup test record
        self.session.delete(queried)
        self.session.commit()

    def test_34_full_end_to_end_authenticated_workflow_produces_expected_audit_trail(self):
        """34. Full end-to-end workflow on PostgreSQL produces expected audit trail and cleans up all records."""
        # Initialize services
        user_service = UserService(db=self.session)
        applicant_service = ApplicantService(db=self.session)
        app_service = ApplicationService(db=self.session)
        consent_service = ConsentService(db=self.session)
        signal_service = FinancialSignalService(db=self.session)
        assessment_service = AssessmentService(db=self.session)
        review_service = ReviewService(db=self.session)
        audit_repo = AuditRepository(db=self.session)

        # Track IDs for cleanup
        created_user_ids = []
        created_profile_ids = []
        created_app_ids = []
        created_audit_ids = []

        try:
            # 1. User
            user = user_service.create_user(
                UserCreate(
                    email=f"pg_worker_{uuid.uuid4().hex[:8]}@example.com",
                    role=UserRole.APPLICANT,
                    password="securePassword123!",
                )
            )
            created_user_ids.append(user.id)

            # 2. Applicant Profile
            profile = applicant_service.create_profile(
                ApplicantProfileCreate(
                    user_id=user.id,
                    gig_work_type="Delivery",
                    primary_platform="Zomato",
                )
            )
            created_profile_ids.append(profile.id)

            # 3. Application
            application = app_service.create_application(
                ApplicationCreate(
                    applicant_profile_id=profile.id,
                    requested_loan_amount=Decimal("30000.00"),
                )
            )
            created_app_ids.append(application.id)

            # 4. Consent
            consent = consent_service.create_consent(
                ConsentCreate(
                    application_id=application.id,
                    applicant_profile_id=profile.id,
                    data_source=ConsentDataSource.PLATFORM,
                    purpose="Delivery metrics scoring",
                )
            )

            # 5. Financial Signal
            signal = signal_service.create_signal(
                FinancialSignalCreate(
                    application_id=application.id,
                    source=SignalSource.PLATFORM,
                    average_income=Decimal("35000.00"),
                )
            )

            # 6. Model Version & Assessment
            mv_service = ModelVersionService(db=self.session)
            mv = mv_service.create_model_version(
                ModelVersionCreate(
                    model_name=f"pg-model-{uuid.uuid4().hex[:6]}",
                    version="1.0.0",
                    is_active=True,
                )
            )
            created_model_version_ids = [mv.id]

            assessment = assessment_service.create_assessment(
                CreditAssessmentCreate(
                    application_id=application.id,
                    model_version_id=mv.id,
                    credit_score=750,
                    risk_level=RiskLevel.LOWER,
                    risk_probability=Decimal("0.08"),
                    confidence=Decimal("0.92"),
                )
            )

            # 7. Reviewer User & Review
            reviewer = user_service.create_user(
                UserCreate(
                    email=f"pg_rev_{uuid.uuid4().hex[:8]}@example.com",
                    role=UserRole.REVIEWER,
                    password="securePassword123!",
                )
            )
            created_user_ids.append(reviewer.id)

            review = review_service.create_review(
                ReviewOutcomeCreate(
                    application_id=application.id,
                    reviewer_id=reviewer.id,
                    outcome=ReviewOutcomeType.REVIEWED,
                    notes="Solid performance indicators",
                )
            )

            # Query all audit logs for this application
            app_logs = audit_repo.get_by_application(application.id, db=self.session)
            created_audit_ids.extend([log.id for log in app_logs])

            # Also find the user's creation audit logs
            user_logs = audit_repo.get_by_user(user.id, db=self.session)
            created_audit_ids.extend([log.id for log in user_logs])

            actions = {log.action for log in app_logs}
            self.assertIn(AuditAction.APPLICATION_CREATED, actions)
            self.assertIn(AuditAction.CONSENT_GRANTED, actions)
            self.assertIn(AuditAction.FINANCIAL_SIGNAL_CREATED, actions)
            self.assertIn(AuditAction.ASSESSMENT_EXECUTED, actions)
            self.assertIn(AuditAction.REVIEW_CREATED, actions)

            # Verify no prohibited keys in any audit record
            for log in app_logs:
                if log.audit_metadata:
                    for key in ["password", "password_hash", "token", "raw_transactions"]:
                        self.assertNotIn(key, log.audit_metadata)

        finally:
            # Thorough teardown and cleanup of all records created
            for aid in set(created_audit_ids):
                self.session.execute(text("DELETE FROM audit_logs WHERE id = :id"), {"id": aid})
            for aid in created_app_ids:
                self.session.execute(text("DELETE FROM review_outcomes WHERE application_id = :id"), {"id": aid})
                self.session.execute(text("DELETE FROM credit_assessments WHERE application_id = :id"), {"id": aid})
                self.session.execute(text("DELETE FROM financial_signals WHERE application_id = :id"), {"id": aid})
                self.session.execute(text("DELETE FROM consents WHERE application_id = :id"), {"id": aid})
                self.session.execute(text("DELETE FROM applications WHERE id = :id"), {"id": aid})
            for pid in created_profile_ids:
                self.session.execute(text("DELETE FROM applicant_profiles WHERE id = :id"), {"id": pid})
            for mvid in created_model_version_ids:
                self.session.execute(text("DELETE FROM audit_logs WHERE entity_id = :id"), {"id": str(mvid)})
                self.session.execute(text("DELETE FROM model_versions WHERE id = :id"), {"id": mvid})
            for uid in created_user_ids:
                self.session.execute(text("DELETE FROM audit_logs WHERE user_id = :id"), {"id": uid})
                self.session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
            self.session.commit()
