"""Verification test suite for Phase 13A-1: TreeSHAP Explanation Persistence.

Tests confirm that ML assessment explanations are durably stored in PostgreSQL (or SQLite in memory)
within the `credit_assessments.explanation` JSONB column, surviving the initial POST request,
retrievable through GET endpoints in fresh client sessions, readable when historical records
have NULL explanations, and securely protected by RBAC ownership boundaries.
"""
import uuid
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.assessment.ml_model_adapter import get_shared_risk_predictor
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


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable from host."""
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


class TestPhase13A1ExplanationPersistence(unittest.TestCase):
    """Exhaustive test suite verifying TreeSHAP explanation persistence in PostgreSQL/SQLite."""

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
            email="ramesh.persistence@parakh.com",
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

        # 3. Seed Reviewer User
        self.reviewer_user = User(
            id=uuid.uuid4(),
            email="reviewer@parakh.com",
            password_hash=hash_password("ReviewerPassword123!"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        self.db.add(self.reviewer_user)

        # 4. Seed Applicant Profile
        self.profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.applicant_user.id,
            gig_work_type="DELIVERY",
            years_working=Decimal("3.5"),
            average_working_days=26,
            business_or_loan_purpose="VEHICLE_MAINTENANCE",
        )
        self.db.add(self.profile)

        # 5. Seed Application
        self.application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("25000.00"),
            preferred_repayment_period=12,
            loan_purpose="VEHICLE_MAINTENANCE",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.application)

        # 6. Seed Active Consent
        self.consent = Consent(
            id=uuid.uuid4(),
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            data_source=ConsentDataSource.PLATFORM,
            purpose="Credit risk assessment and volatility modeling",
            granted=True,
            revoked_at=None,
        )
        self.db.add(self.consent)

        # 7. Seed Rich Financial Signal
        self.financial_signal = FinancialSignal(
            id=uuid.uuid4(),
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("8500.00"),
            median_income=Decimal("8200.00"),
            income_volatility=Decimal("0.1800"),
            income_trend="UP",
            active_days=24,
            payment_regularity=Decimal("0.9600"),
            cashflow_buffer=Decimal("6500.00"),
            existing_obligation=Decimal("1200.00"),
            platform_rating=Decimal("4.85"),
            repayment_reliability=Decimal("0.9800"),
            signal_metadata={
                "feat_inc_median_90d": 8200.0,
                "feat_inc_p25_90d": 7100.0,
                "feat_inc_cv_90d": 0.18,
                "feat_inc_downside_var": 45000.0,
                "feat_trend_slope_90d": 120.0,
                "feat_trend_momentum_30_90": 1.08,
                "feat_act_active_days_ratio": 0.88,
                "feat_act_zero_earn_weeks": 0.0,
                "feat_rec_bounceback_ratio": 1.25,
                "feat_rec_days_to_recover": 4.0,
                "feat_liq_buffer_to_loan": 0.26,
                "feat_liq_burn_months": 2.8,
                "feat_bur_dti_ratio": 0.14,
                "feat_bur_installment_dti": 0.25,
                "feat_bur_total_dti": 0.39,
                "feat_suf_observed_days": 90.0,
                "feat_suf_payout_count": 12.0,
                "feat_suf_group_count": 4.0,
                "feat_suf_missing_ratio": 0.0,
            },
        )
        self.db.add(self.financial_signal)

        # 8. Seed ModelVersion
        self.mv = ModelVersion(
            id=uuid.uuid4(),
            model_name="volatility-aware-risk-model",
            version="1.0.0",
            algorithm="LightGBM",
            description="Volatility-aware alternative credit risk model",
            is_active=True,
        )
        self.db.add(self.mv)
        self.db.commit()

        # Auth headers
        applicant_token = create_access_token(
            subject=str(self.applicant_user.id), role=self.applicant_user.role.value
        )
        self.applicant_headers = {"Authorization": f"Bearer {applicant_token}"}

        other_token = create_access_token(
            subject=str(self.other_applicant.id), role=self.other_applicant.role.value
        )
        self.other_headers = {"Authorization": f"Bearer {other_token}"}

        reviewer_token = create_access_token(
            subject=str(self.reviewer_user.id), role=self.reviewer_user.role.value
        )
        self.reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    def tearDown(self):
        """Clean up database and client overrides."""
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.db_engine)
        self.db_engine.dispose()

    def test_01_scored_assessment_explanation_persisted_in_db(self):
        """1. Verify that POST /assess generates TreeSHAP explanation and persists it in DB."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            response = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(response.status_code, 201, response.text)
            post_data = response.json()

            # Verify response structure
            self.assertIn("explanation", post_data)
            self.assertIsInstance(post_data["explanation"], dict)
            expl = post_data["explanation"]
            self.assertIn("shap_values", expl)
            self.assertIsInstance(expl["shap_values"], list)
            self.assertTrue(len(expl["shap_values"]) > 0, "Expected non-empty shap_values list")
            self.assertIn("key_protective_factors", expl)
            self.assertIn("key_risk_factors", expl)
            self.assertIn("disclaimer", expl)

            # Query database directly to confirm DB-level persistence
            assessment_id = uuid.UUID(post_data["id"])
            db_record = self.db.query(CreditAssessment).filter_by(id=assessment_id).first()
            self.assertIsNotNone(db_record, "CreditAssessment record must exist in DB")
            self.assertIsNotNone(db_record.explanation, "CreditAssessment.explanation must NOT be None")
            self.assertIsInstance(db_record.explanation, dict)

            # Verify exact content equivalence between DB and POST response
            self.assertEqual(db_record.explanation.get("shap_values"), expl["shap_values"])
            self.assertEqual(db_record.explanation.get("disclaimer"), expl["disclaimer"])
            self.assertEqual(db_record.explanation.get("key_protective_factors"), expl["key_protective_factors"])
            self.assertEqual(db_record.explanation.get("key_risk_factors"), expl["key_risk_factors"])

    def test_02_get_assessment_by_id_returns_persisted_explanation(self):
        """2. Verify GET /assessments/{id} returns the persisted TreeSHAP explanation."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            # Trigger assessment
            post_resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(post_resp.status_code, 201)
            post_data = post_resp.json()
            assessment_id = post_data["id"]

            # GET assessment by ID in a distinct query
            get_resp = self.client.get(
                f"/api/v1/assessments/{assessment_id}",
                headers=self.applicant_headers,
            )
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()

            # Confirm explanation persistence and equivalence
            self.assertIsNotNone(get_data.get("explanation"))
            self.assertIsInstance(get_data["explanation"], dict)
            self.assertEqual(get_data["explanation"]["shap_values"], post_data["explanation"]["shap_values"])
            self.assertEqual(get_data["explanation"]["disclaimer"], post_data["explanation"]["disclaimer"])
            self.assertEqual(get_data["score"], post_data["score"])
            self.assertEqual(get_data["risk_level"], post_data["risk_level"])
            self.assertEqual(get_data["key_factors"], post_data["key_factors"])

    def test_03_get_latest_assessment_by_application_returns_persisted_explanation(self):
        """3. Verify GET /applications/{id}/assessments/latest returns the persisted TreeSHAP explanation."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            post_resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(post_resp.status_code, 201)
            post_data = post_resp.json()

            # GET latest assessment by application
            latest_resp = self.client.get(
                f"/api/v1/applications/{self.application.id}/assessments/latest",
                headers=self.applicant_headers,
            )
            self.assertEqual(latest_resp.status_code, 200)
            latest_data = latest_resp.json()

            self.assertEqual(latest_data["id"], post_data["id"])
            self.assertIsNotNone(latest_data.get("explanation"))
            self.assertEqual(latest_data["explanation"]["shap_values"], post_data["explanation"]["shap_values"])
            self.assertEqual(latest_data["key_factors"], post_data["key_factors"])

    def test_04_historical_rows_with_null_explanation_remain_readable(self):
        """4. Verify that historical credit_assessments rows with NULL explanation remain readable without errors."""
        historical_assessment = CreditAssessment(
            id=uuid.uuid4(),
            application_id=self.application.id,
            model_version_id=self.mv.id,
            credit_score=720,
            risk_probability=Decimal("0.1250"),
            risk_level=RiskLevel.LOWER,
            confidence=Decimal("0.8900"),
            debt_to_income=Decimal("0.2200"),
            utilization=Decimal("0.3500"),
            income_stability=Decimal("0.8500"),
            repayment_reliability=Decimal("0.9500"),
            assessment_status="COMPLETED",
            explanation=None,  # Pre-migration row has NULL explanation
        )
        self.db.add(historical_assessment)
        self.db.commit()

        # Query via GET endpoint
        resp = self.client.get(
            f"/api/v1/assessments/{historical_assessment.id}",
            headers=self.applicant_headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Verify historical data is intact and explanation is None/null without crashing
        self.assertEqual(data["id"], str(historical_assessment.id))
        self.assertEqual(data["score"], 720)
        self.assertEqual(data["risk_level"], "LOWER")
        self.assertIsNone(data["explanation"], "Historical records with NULL explanation must return null")
        self.assertTrue(len(data["key_factors"]) > 0, "Key factors should provide fallback indicators")

    def test_05_insufficient_assessment_preserves_missing_signals_without_fabrication(self):
        """5. Verify INSUFFICIENT evidence assessments persist missing signals and do not fabricate SHAP data."""
        # Create an application with insufficient telemetry
        insufficient_app = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("15000.00"),
            preferred_repayment_period=6,
            loan_purpose="PERSONAL_EMERGENCY",
            status=ApplicationStatus.SUBMITTED,
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
            resp = self.client.post(
                f"/api/v1/applications/{insufficient_app.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()

            # Verify insufficient attributes
            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(data["score"])
            self.assertIsNone(data["credit_score"])

            # Verify explanation persistence
            expl = data.get("explanation", {})
            self.assertTrue(expl.get("is_insufficient_evidence"))
            missing = expl.get("missing_signals", [])
            self.assertTrue(len(missing) >= 3, "Expected at least 3 insufficiency failure reasons")
            self.assertEqual(expl.get("shap_values"), [], "Insufficient assessments must not fabricate SHAP values")

            # Check DB record directly
            db_rec = self.db.query(CreditAssessment).filter_by(id=uuid.UUID(data["id"])).first()
            self.assertIsNotNone(db_rec)
            self.assertIsNotNone(db_rec.explanation)
            self.assertTrue(db_rec.explanation.get("is_insufficient_evidence"))
            self.assertEqual(db_rec.explanation.get("missing_signals"), missing)

            # Subsequent GET request returns the exact same missing signals
            get_resp = self.client.get(
                f"/api/v1/assessments/{data['id']}",
                headers=self.applicant_headers,
            )
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()
            self.assertEqual(get_data["explanation"]["missing_signals"], missing)

    def test_06_unauthorized_user_cannot_access_assessment_explanation(self):
        """6. Verify RBAC prevents unauthorized applicants from accessing another user's assessment explanation."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            post_resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(post_resp.status_code, 201)
            assessment_id = post_resp.json()["id"]

            # Another applicant attempts to GET the assessment by ID -> 403 Forbidden
            unauth_resp = self.client.get(
                f"/api/v1/assessments/{assessment_id}",
                headers=self.other_headers,
            )
            self.assertEqual(unauth_resp.status_code, 403)

            # Another applicant attempts to GET latest by application -> 403 Forbidden
            unauth_latest = self.client.get(
                f"/api/v1/applications/{self.application.id}/assessments/latest",
                headers=self.other_headers,
            )
            self.assertEqual(unauth_latest.status_code, 403)

            # Reviewer CAN access it (authorized role)
            reviewer_resp = self.client.get(
                f"/api/v1/assessments/{assessment_id}",
                headers=self.reviewer_headers,
            )
            self.assertEqual(reviewer_resp.status_code, 200)
            self.assertIsNotNone(reviewer_resp.json().get("explanation"))

    def test_07_fresh_session_independent_of_session_storage(self):
        """7. Verify a fresh client session can retrieve the complete TreeSHAP explanation without prior POST."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            # 1. Trigger and persist assessment
            post_resp = self.client.post(
                f"/api/v1/applications/{self.application.id}/assess",
                headers=self.applicant_headers,
            )
            self.assertEqual(post_resp.status_code, 201)
            orig_expl = post_resp.json()["explanation"]

            # 2. Simulate a completely new, clean client session (representing a new browser tab/device)
            fresh_client = TestClient(app)
            fresh_resp = fresh_client.get(
                f"/api/v1/applications/{self.application.id}/assessments/latest",
                headers=self.applicant_headers,
            )
            self.assertEqual(fresh_resp.status_code, 200)
            fresh_data = fresh_resp.json()

            # Explanation is 100% available and identical without sessionStorage
            self.assertIsNotNone(fresh_data.get("explanation"))
            self.assertEqual(fresh_data["explanation"]["shap_values"], orig_expl["shap_values"])
            self.assertEqual(fresh_data["explanation"]["disclaimer"], orig_expl["disclaimer"])
            self.assertEqual(fresh_data["explanation"]["key_protective_factors"], orig_expl["key_protective_factors"])


def get_postgres_engine():
    """Attempt connecting to live PostgreSQL across known environment endpoints."""
    urls = [
        "postgresql+psycopg://parakh:parakh_password@172.21.0.2:5432/parakh",
        settings.DATABASE_URL,
        "postgresql+psycopg://parakh:parakh_password@localhost:5432/parakh",
    ]
    for url in urls:
        try:
            eng = create_engine(url, connect_args={"connect_timeout": 1})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception:
            continue
    return None


class TestPhase13A1LivePostgresIntegration(unittest.TestCase):
    """Direct verification against live PostgreSQL database with real JSONB operators."""

    def test_live_postgres_jsonb_explanation_round_trip(self):
        """Verify real PostgreSQL stores and queries JSONB TreeSHAP explanation."""
        pg_engine = get_postgres_engine()
        if not pg_engine:
            self.skipTest("Live PostgreSQL is not accessible. Skipping live DB test.")

        Session = sessionmaker(bind=pg_engine)
        session = Session()
        try:
            # Check column type in PostgreSQL information schema
            col_info = session.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'credit_assessments' AND column_name = 'explanation';"
                )
            ).fetchone()
            self.assertIsNotNone(col_info, "explanation column must exist in live PostgreSQL")
            self.assertEqual(col_info[0], "explanation")
            self.assertEqual(col_info[1], "jsonb")
            self.assertEqual(col_info[2], "YES")

            mv_id = session.execute(text("SELECT id FROM model_versions WHERE is_active = true LIMIT 1;")).scalar()
            if not mv_id:
                mv_id = session.execute(text("SELECT id FROM model_versions LIMIT 1;")).scalar()

            existing_app_id = session.execute(text("SELECT id FROM applications LIMIT 1;")).scalar()
            if mv_id and existing_app_id:
                assessment_id = uuid.uuid4()
                sample_explanation = {
                    "disclaimer": "Live PostgreSQL JSONB test",
                    "is_insufficient_evidence": False,
                    "shap_values": [
                        {"feature": "feat_rec_bounceback_ratio", "value": 0.28, "displayName": "Recovery Velocity"},
                        {"feature": "feat_inc_cv_90d", "value": -0.15, "displayName": "Income Volatility"}
                    ],
                    "key_protective_factors": [{"factor_name": "Recovery Velocity", "attribution_value": 0.28}],
                    "key_risk_factors": [{"factor_name": "Income Volatility", "attribution_value": -0.15}],
                }
                assessment = CreditAssessment(
                    id=assessment_id,
                    application_id=existing_app_id,
                    model_version_id=mv_id,
                    credit_score=750,
                    risk_probability=Decimal("0.1000"),
                    risk_level=RiskLevel.LOWER,
                    confidence=Decimal("0.9200"),
                    debt_to_income=Decimal("0.2000"),
                    utilization=Decimal("0.3000"),
                    income_stability=Decimal("0.8800"),
                    repayment_reliability=Decimal("0.9700"),
                    assessment_status="COMPLETED",
                    explanation=sample_explanation,
                )
                session.add(assessment)
                session.commit()

                # Query back using raw PostgreSQL JSONB operators
                raw_row = session.execute(
                    text("SELECT explanation->>'disclaimer', jsonb_array_length(explanation->'shap_values') FROM credit_assessments WHERE id = :id"),
                    {"id": assessment_id}
                ).fetchone()
                self.assertEqual(raw_row[0], "Live PostgreSQL JSONB test")
                self.assertEqual(raw_row[1], 2)

                # Query via SQLAlchemy ORM
                queried = session.get(CreditAssessment, assessment_id)
                self.assertIsNotNone(queried)
                self.assertIsInstance(queried.explanation, dict)
                self.assertEqual(len(queried.explanation["shap_values"]), 2)

                # Clean up
                session.delete(queried)
                session.commit()
        finally:
            session.close()
            pg_engine.dispose()


if __name__ == "__main__":
    unittest.main()
