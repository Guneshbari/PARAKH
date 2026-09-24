"""Phase 10C — End-to-End Backend + ML Integration Verification Tests.

Validates the complete end-to-end production runtime flow:
1. Real FastAPI application startup and dependency resolution (`settings.ASSESSMENT_ENGINE='ml'`).
2. Real ML engine factory and MLModelAdapter wiring to frozen Phase 9 RiskPredictor.
3. Full API request/response cycle via POST /api/v1/applications/{application_id}/assess.
4. Exact prediction equivalence: Direct Phase 9 inference (P1) == Real API output (P2).
5. Transactional database persistence: CreditAssessment record persisted with matching fields.
6. Insufficient evidence refusal routing (score=None, risk_probability=None, risk_level=INSUFFICIENT).
7. Data minimization and security enforcement (consent check, RBAC, PROHIBITED_FIELDS rejection).
8. Mock assessment engine regression prevention (mock mode continues working seamlessly).
9. Response contract compliance with frontend adapter schemas (@parakh/api).
10. Singleton predictor thread-safety and warm inference performance.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import time
import unittest
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_assessment_engine, get_db
from app.assessment.exceptions import AssessmentInputError
from app.assessment.factory import create_assessment_engine
from app.assessment.ml_engine import MLAssessmentEngine
from app.assessment.ml_model_adapter import (
    MLModelAdapter,
    get_shared_risk_predictor,
)
from app.assessment.mock import MockAssessmentEngine
from app.assessment.schemas import AssessmentInput
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.main import app
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
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)


class TestPhase10CE2EIntegration(unittest.TestCase):
    """Exhaustive end-to-end verification of backend + ML inference integration."""

    @classmethod
    def setUpClass(cls):
        """Pre-warm shared RiskPredictor singleton once for the test suite."""
        cls.shared_predictor = get_shared_risk_predictor()

    def setUp(self):
        """Set up in-memory SQLite database, FastAPI TestClient, and seed base data."""
        self.db_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.db_engine)
        self.SessionLocal = sessionmaker(bind=self.db_engine, autoflush=False, autocommit=False)
        self.db = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # 1. Seed Applicant User & Auth Token
        self.applicant_user = User(
            id=uuid.uuid4(),
            email="ramesh.kumar@parakh.com",
            password_hash=hash_password("ApplicantPassword123!"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.applicant_user)

        # 2. Seed Second Applicant (for RBAC ownership tests)
        self.other_applicant = User(
            id=uuid.uuid4(),
            email="other.applicant@parakh.com",
            password_hash=hash_password("OtherPassword123!"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.other_applicant)

        # 3. Seed Admin User
        self.admin_user = User(
            id=uuid.uuid4(),
            email="admin@parakh.com",
            password_hash=hash_password("AdminPassword123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(self.admin_user)

        # 4. Seed Applicant Profile
        self.profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.applicant_user.id,
            gig_work_type="DELIVERY",
            years_working=Decimal("2.5"),
            average_working_days=24,
            business_or_loan_purpose="WORKING_CAPITAL",
        )
        self.db.add(self.profile)

        # 5. Seed Valid Application
        self.application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            status=ApplicationStatus.SUBMITTED,
            requested_loan_amount=Decimal("30000.00"),
            preferred_repayment_period=12,
            loan_purpose="WORKING_CAPITAL",
        )
        self.db.add(self.application)

        # 6. Seed Consent
        self.consent = Consent(
            id=uuid.uuid4(),
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            data_source=ConsentDataSource.PLATFORM,
            purpose="Alternative credit assessment and underwriting",
            granted=True,
        )
        self.db.add(self.consent)

        # 7. Seed Financial Signal (Sufficient 90-day telemetry)
        self.signal = FinancialSignal(
            id=uuid.uuid4(),
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("8500.00"),
            median_income=Decimal("8200.00"),
            income_volatility=Decimal("0.1800"),
            payment_regularity=Decimal("0.9600"),
            cashflow_buffer=Decimal("12000.00"),
            existing_obligation=Decimal("3500.00"),
            platform_rating=Decimal("4.85"),
            repayment_reliability=Decimal("0.9800"),
            signal_metadata={
                "active_days": 75,
                "feat_inc_cv_90d": 0.18,
                "feat_suf_observed_days": 90.0,
                "feat_suf_payout_count": 12.0,
                "feat_suf_group_count": 4.0,
            },
        )
        self.db.add(self.signal)

        # 8. Seed ModelVersion for Volatility-Aware ML Model
        self.mv_ml = ModelVersion(
            id=uuid.uuid4(),
            model_name="volatility-aware-risk-model",
            version="1.0.0",
            algorithm="LightGBM + RobustScaler + TreeSHAP",
            description="Production frozen Phase 9 Volatility-Aware Credit Risk Model",
            is_active=True,
        )
        self.db.add(self.mv_ml)

        # 9. Seed ModelVersion for Mock Engine
        self.mv_mock = ModelVersion(
            id=uuid.uuid4(),
            model_name="parakh-mock-engine",
            version="1.0.0",
            algorithm="rule-based-mock",
            description="Default assessment scoring model version",
            is_active=False,
        )
        self.db.add(self.mv_mock)
        self.db.commit()

        # Auth Headers
        self.applicant_token = create_access_token(
            subject=str(self.applicant_user.id),
            role=self.applicant_user.role.value,
        )
        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}

        self.other_token = create_access_token(
            subject=str(self.other_applicant.id),
            role=self.other_applicant.role.value,
        )
        self.other_headers = {"Authorization": f"Bearer {self.other_token}"}

        self.admin_token = create_access_token(
            subject=str(self.admin_user.id),
            role=self.admin_user.role.value,
        )
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        """Clean up database and dependency overrides."""
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(bind=self.db_engine)

    def test_01_backend_runtime_startup_and_ml_engine_wiring(self):
        """Verify real FastAPI application startup and ML engine resolution under settings.ASSESSMENT_ENGINE='ml'."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            engine = get_assessment_engine()
            self.assertIsInstance(engine, MLAssessmentEngine)
            self.assertEqual(engine.engine_name, "volatility-aware-risk-model")
            self.assertEqual(engine.engine_version, "1.0.0")

    def test_02_valid_assessment_api_round_trip_and_persistence(self):
        """Verify full API request-to-response cycle and SQLite/Postgres persistence."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            response = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(response.status_code, 201, response.text)
            data = response.json()

            # Verify response shape & contracts
            self.assertIsNotNone(data.get("id"))
            self.assertEqual(data.get("application_id"), str(self.application.id))
            self.assertEqual(data.get("model_name"), "volatility-aware-risk-model")
            self.assertEqual(data.get("model_version"), "1.0.0")
            self.assertEqual(data.get("assessment_status"), "COMPLETED")
            self.assertIsNotNone(data.get("assessed_at"))

            # Valid predictions
            self.assertIsInstance(data.get("score"), int)
            self.assertEqual(data.get("score"), data.get("credit_score"))
            self.assertGreaterEqual(data.get("score"), 300)
            self.assertLessEqual(data.get("score"), 850)
            self.assertIsNotNone(data.get("risk_probability"))
            self.assertIn(data.get("risk_level"), ["LOWER", "MODERATE", "HIGHER"])

            # Explainability & SHAP
            explanation = data.get("explanation", {})
            self.assertIn("shap_values", explanation)
            self.assertIsInstance(explanation["shap_values"], list)
            self.assertIn("disclaimer", explanation)
            self.assertTrue(len(data.get("key_factors", [])) > 0)

            # DB persistence verification
            db_record = self.db.query(CreditAssessment).filter_by(id=uuid.UUID(data["id"])).first()
            self.assertIsNotNone(db_record)
            self.assertEqual(db_record.credit_score, data["credit_score"])
            self.assertEqual(float(db_record.risk_probability), float(data["risk_probability"]))
            self.assertEqual(db_record.risk_level.value, data["risk_level"])
            self.assertEqual(db_record.model_version_id, self.mv_ml.id)

    def test_03_prediction_equivalence_direct_vs_api(self):
        """Prove that the real HTTP/backend path produces the exact same ML result as direct Phase 9 inference."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            # 1. Build equivalent AssessmentInput
            assessment_input = AssessmentInput(
                application_id=self.application.id,
                applicant_profile_id=self.profile.id,
                requested_loan_amount=Decimal("30000.00"),
                loan_tenure_months=12,
                loan_purpose="WORKING_CAPITAL",
                gig_work_type="DELIVERY",
                years_working=Decimal("2.5"),
                average_working_days=24,
                average_income=Decimal("8500.00"),
                median_income=Decimal("8200.00"),
                income_volatility=Decimal("0.1800"),
                payment_regularity=Decimal("0.9600"),
                cashflow_buffer=Decimal("12000.00"),
                existing_obligation=Decimal("3500.00"),
                platform_rating=Decimal("4.85"),
                repayment_reliability=Decimal("0.9800"),
                derived_features={
                    "active_days": 75,
                    "feat_inc_cv_90d": 0.18,
                    "feat_suf_observed_days": 90.0,
                    "feat_suf_payout_count": 12.0,
                    "feat_suf_group_count": 4.0,
                },
            )

            # 2. Direct Phase 9 Inference (P1)
            flat_dict = MLModelAdapter.transform_input_to_ml_dict(assessment_input)
            p1_resp = self.shared_predictor.predict(flat_dict)

            # 3. Real API Round-Trip Path (P2)
            api_resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(api_resp.status_code, 201)
            p2_data = api_resp.json()

            # 4. Strict Equivalence Assertions
            self.assertAlmostEqual(
                float(p1_resp.repayment_risk_probability),
                float(p2_data["risk_probability"]),
                places=4,
                msg="Probability mismatch between direct Phase 9 and real API",
            )
            self.assertEqual(p1_resp.risk_tier, p2_data["risk_level"])
            self.assertEqual(p1_resp.presentation_score, p2_data["score"])
            self.assertEqual("1.0.0", p2_data["model_version"])
            self.assertEqual("volatility-aware-risk-model", p2_data["model_name"])

    def test_04_insufficient_evidence_routing_unrated_null_score(self):
        """Verify insufficient observation/telemetry returns INSUFFICIENT, null score, null probability, and no fabricated score."""
        # Create application with insufficient history (observed_days=12 < 30, payouts=2 < 4)
        insufficient_app = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            status=ApplicationStatus.SUBMITTED,
            requested_loan_amount=Decimal("15000.00"),
            preferred_repayment_period=6,
            loan_purpose="PERSONAL_EMERGENCY",
        )
        self.db.add(insufficient_app)

        insufficient_signal = FinancialSignal(
            id=uuid.uuid4(),
            application_id=insufficient_app.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("3000.00"),
            signal_metadata={
                "feat_suf_observed_days": 12.0,  # Below 30-day requirement
                "feat_suf_payout_count": 2.0,   # Below 4-payout requirement
                "feat_suf_group_count": 1.0,   # Below 2-group requirement
            },
        )
        self.db.add(insufficient_signal)
        self.db.commit()

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            response = self.client.post(
                f"/api/v1/applications/{insufficient_app.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(response.status_code, 201, response.text)
            data = response.json()

            # Strict insufficient evidence requirements
            self.assertEqual(data.get("risk_level"), "INSUFFICIENT")
            self.assertIsNone(data.get("credit_score"), "credit_score must be null for insufficient evidence")
            self.assertIsNone(data.get("score"), "score must be null for insufficient evidence")
            self.assertIsNone(data.get("risk_probability"), "risk_probability must be null for insufficient evidence")
            self.assertLessEqual(float(data.get("confidence") or 0.0), 0.001)

            # Refusal explanation and missing signals preserved
            explanation = data.get("explanation", {})
            self.assertTrue(explanation.get("is_insufficient_evidence"))
            missing_signals = explanation.get("missing_signals", [])
            self.assertTrue(len(missing_signals) >= 3)
            self.assertTrue(any("30 days" in s for s in missing_signals))

            # Database persistence verification
            db_record = self.db.query(CreditAssessment).filter_by(id=uuid.UUID(data["id"])).first()
            self.assertIsNotNone(db_record)
            self.assertIsNone(db_record.credit_score)
            self.assertIsNone(db_record.risk_probability)
            self.assertEqual(db_record.risk_level, RiskLevel.INSUFFICIENT)

    def test_05_prohibited_privacy_fields_rejected_by_api(self):
        """Verify privacy-invasive fields (e.g., bank statements, credentials) cannot be processed by the ML engine."""
        with self.assertRaises(AssessmentInputError) as ctx:
            AssessmentInput(
                application_id=self.application.id,
                applicant_profile_id=self.profile.id,
                requested_loan_amount=Decimal("20000.00"),
                derived_features={
                    "raw_bank_statements": "confidential_pdf_payload",
                    "account_passwords": "cleartext_secret",
                },
            )
        self.assertIn("Prohibited privacy-invasive field", str(ctx.exception))

    def test_06_consent_and_authorization_security_enforcement(self):
        """Verify consent checking and ownership enforcement before executing assessment."""
        # 1. Unauthenticated request -> 401
        resp = self.client.post(f"/api/v1/applications/{self.application.id}/assess")
        self.assertEqual(resp.status_code, 401)

        # 2. Unauthorized applicant accessing another applicant's application -> 403
        resp = self.client.post(
            f"/api/v1/applications/{self.application.id}/assess",
            headers=self.other_headers,
        )
        self.assertEqual(resp.status_code, 403)

        # 3. Missing consent when enforce_consent=True -> 400
        # Revoke consent
        self.consent.revoked_at = self.consent.created_at
        self.db.commit()

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess?enforce_consent=true",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Active applicant consent is required", resp.text)

    def test_07_mock_engine_regression_prevention(self):
        """Verify that existing MockAssessmentEngine continues functioning when ASSESSMENT_ENGINE='mock'."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "mock"):
            engine = get_assessment_engine()
            self.assertIsInstance(engine, MockAssessmentEngine)

            response = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
                params={"model_version_id": str(self.mv_mock.id)},
            )
            self.assertEqual(response.status_code, 201)
            data = response.json()

            self.assertEqual(data.get("model_name"), "parakh-mock-engine")
            self.assertGreater(data.get("credit_score"), 500)
            self.assertIn(data.get("risk_level"), ["LOWER", "MODERATE", "HIGHER"])

    def test_08_singleton_predictor_thread_safety_and_performance(self):
        """Verify singleton instance reuse under concurrent thread execution and observe warm latency."""
        # 1. Verify identity
        p1 = get_shared_risk_predictor()
        p2 = get_shared_risk_predictor()
        self.assertIs(p1, p2)

        # 2. Multi-threaded concurrency
        def get_pred_concurrently():
            return id(get_shared_risk_predictor())

        with ThreadPoolExecutor(max_workers=8) as executor:
            predictor_ids = list(executor.map(lambda _: get_pred_concurrently(), range(16)))

        self.assertEqual(len(set(predictor_ids)), 1, "Predictor must remain single instance across threads")

        # 3. Warm inference latency smoke test
        flat_dict = MLModelAdapter.transform_input_to_ml_dict(
            AssessmentInput(requested_loan_amount=Decimal("20000.00"))
        )
        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            p1.predict(flat_dict)
            latencies.append((time.perf_counter() - t0) * 1000)

        avg_latency_ms = sum(latencies) / len(latencies)
        self.assertLess(avg_latency_ms, 150.0, f"Average warm inference latency {avg_latency_ms:.2f}ms is unexpectedly high")


if __name__ == "__main__":
    unittest.main()
