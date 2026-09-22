"""Integration tests for MockAssessmentEngine and credit evaluation workflows.

Verifies:
TEST A — Successful assessment (Application -> POST /assess -> MockAssessmentEngine -> DB)
TEST B — Retrieval (POST /assess -> GET latest assessment and GET assessment by ID)
TEST C — Authorization (Attempt assessment with unauthorized user -> 403)
TEST D — Consent (Attempt assessment without required consent -> 403, with consent -> 201)
TEST E — Missing application (Assess nonexistent application -> 404)
TEST F — Audit (Successful assessment records ASSESSMENT_EXECUTED audit event)
TEST G — Engine abstraction (Service calls AssessmentEngine abstraction, resolves to MockAssessmentEngine)
"""
import unittest
import uuid
from decimal import Decimal
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import (
    get_assessment_engine,
    get_assessment_service,
    get_current_active_user,
    get_db,
)
from app.assessment.base import AssessmentEngine
from app.assessment.mock import MockAssessmentEngine
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.core.audit_events import AuditAction
from app.core.security import hash_password
from app.main import app
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
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)
from app.repositories import (
    ApplicationRepository,
    AssessmentRepository,
    AuditRepository,
)
from app.services.assessment import AssessmentService


class TestMockAssessmentIntegrationSuite(unittest.TestCase):
    """End-to-end integration test suite for MockAssessmentEngine execution and API endpoints."""

    def setUp(self):
        """Create an isolated, thread-safe in-memory SQLite database sharing a StaticPool."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.client = TestClient(app)

        # Wire FastAPI get_db dependency to point to this isolated SQLite test database
        def override_get_db() -> Generator[Session, None, None]:
            db = self.SessionFactory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # Wire get_assessment_service dependency to use the isolated test database
        def override_get_assessment_service() -> AssessmentService:
            db = self.SessionFactory()
            return AssessmentService(db=db, engine=MockAssessmentEngine())

        app.dependency_overrides[get_assessment_service] = override_get_assessment_service

    def tearDown(self):
        """Clean up dependency overrides and drop tables."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _setup_baseline_entities(self, include_consent: bool = True):
        """Helper to create User, ApplicantProfile, Application, ModelVersion, and Signals."""
        session: Session = self.SessionFactory()
        try:
            # 1. Applicant User
            user = User(
                email="worker_mock@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(user)
            session.flush()

            # 2. Applicant Profile
            profile = ApplicantProfile(
                user_id=user.id,
                gig_work_type="ride-hailing",
                years_working=Decimal("3.0"),
                average_working_days=25,
                business_or_loan_purpose="Vehicle servicing",
            )
            session.add(profile)
            session.flush()

            # 3. Application
            application = Application(
                applicant_profile_id=profile.id,
                requested_loan_amount=Decimal("30000.00"),
                loan_purpose="Maintenance",
                preferred_repayment_period=12,
                status=ApplicationStatus.SUBMITTED,
            )
            session.add(application)
            session.flush()

            # 4. Optional Consent
            consent = None
            if include_consent:
                consent = Consent(
                    application_id=application.id,
                    applicant_profile_id=profile.id,
                    data_source=ConsentDataSource.PLATFORM,
                    purpose="Alternative credit assessment",
                    granted=True,
                )
                session.add(consent)
                session.flush()

            # 5. Financial Signal
            signal = FinancialSignal(
                application_id=application.id,
                applicant_profile_id=profile.id,
                source=SignalSource.PLATFORM,
                average_income=Decimal("38000.00"),
                median_income=Decimal("36000.00"),
                payment_regularity=Decimal("0.92"),
                cashflow_buffer=Decimal("6500.00"),
                existing_obligation=Decimal("2500.00"),
                platform_rating=Decimal("4.85"),
                repayment_reliability=Decimal("0.94"),
            )
            session.add(signal)
            session.flush()

            # 6. Model Version
            mv = ModelVersion(
                model_name="parakh-mock-engine",
                version="1.0.0",
                algorithm="DeterministicRuleMock",
                description="Default mock assessment engine",
                is_active=True,
            )
            session.add(mv)
            session.commit()

            return {
                "user_id": user.id,
                "user_email": user.email,
                "profile_id": profile.id,
                "application_id": application.id,
                "consent_id": consent.id if consent else None,
                "signal_id": signal.id,
                "model_version_id": mv.id,
            }
        finally:
            session.close()

    def test_a_successful_assessment_flow(self):
        """TEST A: Application -> POST /assess -> MockAssessmentEngine -> CreditAssessment -> Database."""
        data = self._setup_baseline_entities(include_consent=True)
        user = User(
            id=data["user_id"],
            email=data["user_email"],
            role=UserRole.APPLICANT,
            is_active=True,
        )
        app_id = data["application_id"]
        mv_id = data["model_version_id"]

        app.dependency_overrides[get_current_active_user] = lambda: user

        # Trigger POST /api/v1/applications/{application_id}/assess
        response = self.client.post(
            f"/api/v1/applications/{app_id}/assess?model_version_id={mv_id}",
        )
        self.assertEqual(response.status_code, 201, f"Assessment failed: {response.text}")

        res_data = response.json()
        self.assertIn("id", res_data)
        self.assertEqual(res_data["application_id"], str(app_id))
        self.assertEqual(res_data["model_version_id"], str(mv_id))
        self.assertIsNotNone(res_data["score"])
        self.assertGreaterEqual(res_data["score"], 300)
        self.assertLessEqual(res_data["score"], 850)
        self.assertIn(res_data["risk_level"], ["LOWER", "MODERATE", "HIGHER"])
        self.assertGreaterEqual(float(res_data["confidence"]), 0.3)
        self.assertEqual(res_data["model_name"], "parakh-mock-engine")
        self.assertEqual(res_data["model_version"], "1.0.0")
        self.assertTrue(len(res_data["key_factors"]) > 0)
        self.assertIsInstance(res_data["explanation"], dict)

        # Direct database verification
        session: Session = self.SessionFactory()
        try:
            assessment_repo = AssessmentRepository(db=session)
            db_assessment = assessment_repo.get_by_id(res_data["id"])
            self.assertIsNotNone(db_assessment)
            self.assertEqual(db_assessment.application_id, app_id)
            self.assertEqual(db_assessment.model_version_id, mv_id)
            self.assertEqual(db_assessment.credit_score, res_data["score"])
            self.assertEqual(db_assessment.risk_level.value, res_data["risk_level"])
        finally:
            session.close()

    def test_b_retrieval_matches_persisted_result(self):
        """TEST B: POST /assess -> GET latest assessment and GET assessment by ID."""
        data = self._setup_baseline_entities(include_consent=True)
        user = User(
            id=data["user_id"],
            email=data["user_email"],
            role=UserRole.APPLICANT,
            is_active=True,
        )
        app_id = data["application_id"]

        app.dependency_overrides[get_current_active_user] = lambda: user

        # 1. Execute assessment
        post_resp = self.client.post(f"/api/v1/applications/{app_id}/assess")
        self.assertEqual(post_resp.status_code, 201)
        post_data = post_resp.json()
        assessment_id = post_data["id"]

        # 2. GET /api/v1/applications/{application_id}/assessments/latest
        get_latest_resp = self.client.get(f"/api/v1/applications/{app_id}/assessments/latest")
        self.assertEqual(get_latest_resp.status_code, 200)
        latest_data = get_latest_resp.json()

        self.assertEqual(latest_data["id"], assessment_id)
        self.assertEqual(latest_data["application_id"], str(app_id))
        self.assertEqual(latest_data["score"], post_data["score"])
        self.assertEqual(latest_data["risk_level"], post_data["risk_level"])
        self.assertEqual(latest_data["confidence"], post_data["confidence"])
        self.assertEqual(latest_data["model_version"], post_data["model_version"])
        self.assertTrue(len(latest_data["key_factors"]) > 0)
        self.assertIsInstance(latest_data["explanation"], dict)

        # 3. GET /api/v1/assessments/{assessment_id}
        get_id_resp = self.client.get(f"/api/v1/assessments/{assessment_id}")
        self.assertEqual(get_id_resp.status_code, 200)
        id_data = get_id_resp.json()
        self.assertEqual(id_data["id"], assessment_id)
        self.assertEqual(id_data["score"], post_data["score"])

    def test_c_authorization_rejection(self):
        """TEST C: Attempt assessment with unauthorized user -> 403 Forbidden."""
        data = self._setup_baseline_entities(include_consent=True)
        app_id = data["application_id"]

        # Create a second, unrelated applicant user
        session: Session = self.SessionFactory()
        try:
            other_user = User(
                id=uuid.uuid4(),
                email="other_worker@parakh.in",
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(other_user)
            session.commit()
            other_user_id = other_user.id
        finally:
            session.close()

        # Act as other_user
        mock_other = User(
            id=other_user_id,
            email="other_worker@parakh.in",
            role=UserRole.APPLICANT,
            is_active=True,
        )
        app.dependency_overrides[get_current_active_user] = lambda: mock_other

        response = self.client.post(f"/api/v1/applications/{app_id}/assess")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.json().get("detail", ""))

    def test_d_consent_enforcement(self):
        """TEST D: Attempt assessment without required consent -> 403, and with consent -> 201."""
        # 1. Setup entities WITHOUT consent
        data = self._setup_baseline_entities(include_consent=False)
        user = User(
            id=data["user_id"],
            email=data["user_email"],
            role=UserRole.APPLICANT,
            is_active=True,
        )
        app_id = data["application_id"]
        profile_id = data["profile_id"]

        app.dependency_overrides[get_current_active_user] = lambda: user

        # Attempt assess: should fail with 403 Consent Required
        fail_resp = self.client.post(f"/api/v1/applications/{app_id}/assess")
        self.assertEqual(fail_resp.status_code, 403)
        self.assertIn("Active applicant consent is required", fail_resp.json().get("detail", ""))

        # 2. Grant consent now
        session: Session = self.SessionFactory()
        try:
            consent = Consent(
                application_id=app_id,
                applicant_profile_id=profile_id,
                data_source=ConsentDataSource.PLATFORM,
                purpose="Alternative credit assessment",
                granted=True,
            )
            session.add(consent)
            session.commit()
        finally:
            session.close()

        # Re-attempt assess: should succeed with 201
        success_resp = self.client.post(f"/api/v1/applications/{app_id}/assess")
        self.assertEqual(success_resp.status_code, 201)
        self.assertIsNotNone(success_resp.json().get("id"))

    def test_e_missing_application_404(self):
        """TEST E: Assess nonexistent application -> 404 Not Found."""
        random_app_id = uuid.uuid4()
        reviewer = User(
            id=uuid.uuid4(),
            email="reviewer_admin@parakh.in",
            role=UserRole.ADMIN,
            is_active=True,
        )
        app.dependency_overrides[get_current_active_user] = lambda: reviewer

        response = self.client.post(f"/api/v1/applications/{random_app_id}/assess")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json().get("detail", "").lower())

    def test_f_audit_event_recorded(self):
        """TEST F: Successful assessment must record ASSESSMENT_EXECUTED audit event."""
        data = self._setup_baseline_entities(include_consent=True)
        user = User(
            id=data["user_id"],
            email=data["user_email"],
            role=UserRole.APPLICANT,
            is_active=True,
        )
        app_id = data["application_id"]

        app.dependency_overrides[get_current_active_user] = lambda: user

        response = self.client.post(f"/api/v1/applications/{app_id}/assess")
        self.assertEqual(response.status_code, 201)
        assessment_id = response.json()["id"]

        session: Session = self.SessionFactory()
        try:
            audit_repo = AuditRepository(db=session)
            audits = audit_repo.get_by_application(app_id)
            actions = [log.action for log in audits]
            action_str = AuditAction.ASSESSMENT_EXECUTED.value if hasattr(AuditAction.ASSESSMENT_EXECUTED, "value") else str(AuditAction.ASSESSMENT_EXECUTED)
            self.assertIn(action_str, actions)

            # Check audit metadata
            assessment_logs = [log for log in audits if log.action == action_str]
            self.assertTrue(len(assessment_logs) >= 1)
            target_log = assessment_logs[0]
            self.assertEqual(target_log.entity_type, "CreditAssessment")
            self.assertEqual(target_log.entity_id, assessment_id)
            self.assertIsNotNone(target_log.audit_metadata)
            self.assertIn("risk_level", target_log.audit_metadata)
        finally:
            session.close()

    def test_g_engine_abstraction_and_mock_resolution(self):
        """TEST G: Verify service calls AssessmentEngine abstraction and resolves to MockAssessmentEngine."""
        # 1. Dependency injection resolution
        engine = get_assessment_engine()
        self.assertIsInstance(engine, AssessmentEngine)
        self.assertIsInstance(engine, MockAssessmentEngine)
        self.assertEqual(engine.engine_name, "parakh-mock-engine")
        self.assertEqual(engine.engine_version, "1.0.0")

        # 2. Verify AssessmentService works with any AssessmentEngine implementation
        class CustomTestEngine(AssessmentEngine):
            @property
            def engine_name(self) -> str:
                return "custom-test-engine"

            @property
            def engine_version(self) -> str:
                return "2.0.0-custom"

            def assess(self, input_data: AssessmentInput) -> AssessmentResult:
                return AssessmentResult(
                    score=750,
                    risk_probability=Decimal("0.1500"),
                    confidence=Decimal("0.9000"),
                    risk_level=RiskLevel.LOWER,
                    model_name=self.engine_name,
                    model_version=self.engine_version,
                    key_factors=["Custom factor 1", "Custom factor 2"],
                    explanation={"custom": True},
                )

        data = self._setup_baseline_entities(include_consent=True)
        app_id = data["application_id"]
        mv_id = data["model_version_id"]

        session: Session = self.SessionFactory()
        try:
            custom_engine = CustomTestEngine()
            service = AssessmentService(db=session, engine=custom_engine)
            assessment = service.assess_application(
                application_id=app_id,
                model_version_id=mv_id,
                auto_commit=True,
            )
            self.assertEqual(assessment.credit_score, 750)
            self.assertEqual(assessment.risk_level, RiskLevel.LOWER)
            self.assertEqual(getattr(assessment, "_transient_model_name"), "custom-test-engine")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
