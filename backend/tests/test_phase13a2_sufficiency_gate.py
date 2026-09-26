"""Comprehensive test suite for Phase 13A-2: MLModelAdapter Sufficiency Gate Enforcement.

Verifies:
1. Missing signal_metadata cannot receive sufficient defaults and routes to INSUFFICIENT.
2. Empty signal_metadata cannot receive sufficient defaults and routes to INSUFFICIENT.
3. Partial signal_metadata (e.g. only observed_days, only payout_count, only group_count)
   cannot receive fabricated defaults for missing mandatory fields and routes to INSUFFICIENT.
4. Explicit insufficient metadata correctly routes to INSUFFICIENT with informative reasons.
5. Explicit sufficient metadata produces a standard scored assessment with SHAP values.
6. Friendly alias keys ('observed_days', 'payout_count', 'group_count') are supported.
7. MLModelAdapter.transform_input_to_ml_dict does NOT fabricate 90.0, 12.0, 4.0, or 0.0.
8. No LightGBM scoring occurs for insufficient applications (predict_proba is never called).
9. Insufficient assessments persist correctly in PostgreSQL/SQLite with null score and
   proper explanation structure according to Phase 13A-1 persistence contracts.
10. Security: Consent revocation and RBAC ownership remain strictly enforced.
"""
import uuid
import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.assessment.ml_model_adapter import MLModelAdapter, get_shared_risk_predictor
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


class TestPhase13A2SufficiencyGate(unittest.TestCase):
    """Exhaustive test suite verifying the ML data sufficiency gate and absence of fabricated defaults."""

    @classmethod
    def setUpClass(cls):
        """Pre-warm shared RiskPredictor singleton once for the test suite."""
        cls.shared_predictor = get_shared_risk_predictor()

    def setUp(self):
        """Set up in-memory SQLite database, FastAPI TestClient, and seed base domain data."""
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

        # 1. Seed Primary Applicant User & Token
        self.applicant_user = User(
            id=uuid.uuid4(),
            email="arjun.verma.suf@parakh.com",
            password_hash=hash_password("ApplicantPassword123!"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.applicant_user)

        # 2. Seed Second Applicant (for RBAC ownership validation)
        self.other_user = User(
            id=uuid.uuid4(),
            email="other.user.suf@parakh.com",
            password_hash=hash_password("OtherPassword123!"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.other_user)

        # 3. Seed Reviewer User
        self.reviewer_user = User(
            id=uuid.uuid4(),
            email="reviewer.suf@parakh.com",
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
            years_working=Decimal("3.0"),
            average_working_days=25,
            business_or_loan_purpose="WORKING_CAPITAL",
        )
        self.db.add(self.profile)

        # 5. Seed Model Version
        self.model_version = ModelVersion(
            id=uuid.uuid4(),
            model_name="volatility-aware-risk-model",
            version="1.0.0",
            algorithm="LightGBM + RobustScaler + TreeSHAP",
            description="Production frozen Phase 9 Volatility-Aware Credit Risk Model",
            is_active=True,
        )
        self.db.add(self.model_version)
        self.db.commit()

        # Auth headers
        applicant_token = create_access_token(
            subject=str(self.applicant_user.id),
            role="APPLICANT",
        )
        self.applicant_headers = {
            "Authorization": f"Bearer {applicant_token}",
            "Content-Type": "application/json",
        }

        other_token = create_access_token(
            subject=str(self.other_user.id),
            role="APPLICANT",
        )
        self.other_headers = {
            "Authorization": f"Bearer {other_token}",
            "Content-Type": "application/json",
        }

    def tearDown(self):
        """Clean up database session and drop all tables."""
        self.db.close()
        Base.metadata.drop_all(bind=self.db_engine)
        app.dependency_overrides.clear()

    def _create_application_with_signal(self, signal_metadata: Any, consent_granted: bool = True) -> Application:
        """Helper to create an application, consent record, and financial signal."""
        application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("20000.00"),
            preferred_repayment_period=12,
            loan_purpose="WORKING_CAPITAL",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(application)

        consent = Consent(
            id=uuid.uuid4(),
            application_id=application.id,
            applicant_profile_id=self.profile.id,
            data_source=ConsentDataSource.PLATFORM,
            purpose="Credit assessment under DPDP",
            granted=consent_granted,
            revoked_at=None if consent_granted else self.db.query(User).first().created_at,
        )
        self.db.add(consent)

        signal = FinancialSignal(
            id=uuid.uuid4(),
            application_id=application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("8000.00"),
            median_income=Decimal("7800.00"),
            income_volatility=Decimal("0.2000"),
            payment_regularity=Decimal("0.9500"),
            cashflow_buffer=Decimal("10000.00"),
            existing_obligation=Decimal("3000.00"),
            platform_rating=Decimal("4.80"),
            repayment_reliability=Decimal("0.9600"),
            signal_metadata=signal_metadata,
        )
        self.db.add(signal)
        self.db.commit()
        return application

    # --------------------------------------------------------------------------
    # 1. Missing signal_metadata cannot receive sufficient defaults
    # --------------------------------------------------------------------------
    def test_01_missing_signal_metadata_routes_to_insufficient(self):
        """Missing signal_metadata (None) must not receive fabricated defaults and must route to INSUFFICIENT."""
        app_obj = self._create_application_with_signal(signal_metadata=None)

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            # Risk tier and scores must reflect INSUFFICIENT
            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(data["score"])
            self.assertIsNone(data["credit_score"])
            self.assertIsNone(data["risk_probability"])
            self.assertLessEqual(float(data["confidence"] or 0.0), 0.001)

            # Explanation must indicate insufficiency and list missing telemetry
            expl = data.get("explanation", {})
            self.assertTrue(expl.get("is_insufficient_evidence"))
            missing = expl.get("missing_signals", [])
            self.assertTrue(len(missing) >= 3, f"Expected 3 missing signals, got: {missing}")
            self.assertTrue(any("observed" in s.lower() for s in missing))
            self.assertTrue(any("payout" in s.lower() for s in missing))
            self.assertTrue(any("signal group" in s.lower() for s in missing))
            self.assertEqual(expl.get("shap_values"), [])

    # --------------------------------------------------------------------------
    # 2. Empty signal_metadata cannot receive sufficient defaults
    # --------------------------------------------------------------------------
    def test_02_empty_signal_metadata_routes_to_insufficient(self):
        """Empty signal_metadata ({}) must not receive fabricated defaults and must route to INSUFFICIENT."""
        app_obj = self._create_application_with_signal(signal_metadata={})

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(data["score"])
            self.assertIsNone(data["credit_score"])
            self.assertIsNone(data["risk_probability"])

            expl = data.get("explanation", {})
            self.assertTrue(expl.get("is_insufficient_evidence"))
            missing = expl.get("missing_signals", [])
            self.assertTrue(len(missing) >= 3)

    # --------------------------------------------------------------------------
    # 3. Partial signal_metadata: Only observed_days
    # --------------------------------------------------------------------------
    def test_03_partial_metadata_only_observed_days_routes_to_insufficient(self):
        """Providing only observed_days must NOT fabricate payout_count or group_count."""
        app_obj = self._create_application_with_signal(
            signal_metadata={"feat_suf_observed_days": 90.0}
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(data["score"])
            self.assertIsNone(data["credit_score"])
            self.assertIsNone(data["risk_probability"])

            expl = data.get("explanation", {})
            missing = expl.get("missing_signals", [])
            # Observed days was provided (90 >= 30), so only payout and group count should be missing
            self.assertTrue(any("payout" in s.lower() for s in missing))
            self.assertTrue(any("signal group" in s.lower() for s in missing))
            self.assertFalse(any("observed" in s.lower() for s in missing))

    # --------------------------------------------------------------------------
    # 4. Partial signal_metadata: Only payout_count
    # --------------------------------------------------------------------------
    def test_04_partial_metadata_only_payout_count_routes_to_insufficient(self):
        """Providing only payout_count must NOT fabricate observed_days or group_count."""
        app_obj = self._create_application_with_signal(
            signal_metadata={"feat_suf_payout_count": 12.0}
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            expl = data.get("explanation", {})
            missing = expl.get("missing_signals", [])
            self.assertTrue(any("observed" in s.lower() for s in missing))
            self.assertTrue(any("signal group" in s.lower() for s in missing))
            self.assertFalse(any("payout" in s.lower() for s in missing))

    # --------------------------------------------------------------------------
    # 5. Partial signal_metadata: Only group_count
    # --------------------------------------------------------------------------
    def test_05_partial_metadata_only_group_count_routes_to_insufficient(self):
        """Providing only group_count must NOT fabricate observed_days or payout_count."""
        app_obj = self._create_application_with_signal(
            signal_metadata={"feat_suf_group_count": 4.0}
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            expl = data.get("explanation", {})
            missing = expl.get("missing_signals", [])
            self.assertTrue(any("observed" in s.lower() for s in missing))
            self.assertTrue(any("payout" in s.lower() for s in missing))
            self.assertFalse(any("signal group" in s.lower() for s in missing))

    # --------------------------------------------------------------------------
    # 6. Explicit insufficient metadata
    # --------------------------------------------------------------------------
    def test_06_explicit_insufficient_metadata_routes_to_insufficient(self):
        """Telemetry explicitly below sufficiency thresholds must route to INSUFFICIENT."""
        app_obj = self._create_application_with_signal(
            signal_metadata={
                "feat_suf_observed_days": 14.0,  # < 30
                "feat_suf_payout_count": 2.0,    # < 4
                "feat_suf_group_count": 1.0,     # < 2
            }
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            self.assertEqual(data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(data["score"])
            self.assertIsNone(data["risk_probability"])

            expl = data.get("explanation", {})
            missing = expl.get("missing_signals", [])
            self.assertEqual(len(missing), 3)
            self.assertTrue(any("14 days" in s for s in missing))
            self.assertTrue(any("2" in s and "4 cycles" in s for s in missing))
            self.assertTrue(any("1" in s and "signal groups" in s for s in missing))

    # --------------------------------------------------------------------------
    # 7. Explicit sufficient metadata scores normally
    # --------------------------------------------------------------------------
    def test_07_explicit_sufficient_metadata_produces_scored_assessment(self):
        """Explicitly sufficient telemetry must be scored normally by the LightGBM model."""
        app_obj = self._create_application_with_signal(
            signal_metadata={
                "feat_suf_observed_days": 90.0,
                "feat_suf_payout_count": 12.0,
                "feat_suf_group_count": 4.0,
            }
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            # Must be scored
            self.assertIn(data["risk_level"], ["LOWER", "MODERATE", "HIGHER"])
            self.assertIsNotNone(data["score"])
            self.assertIsNotNone(data["credit_score"])
            self.assertIsNotNone(data["risk_probability"])
            self.assertGreater(float(data["risk_probability"]), 0.0)

            # Explanation must contain TreeSHAP factors
            expl = data.get("explanation", {})
            self.assertFalse(expl.get("is_insufficient_evidence"))
            self.assertEqual(expl.get("missing_signals"), [])
            shap_values = expl.get("shap_values", [])
            self.assertTrue(len(shap_values) > 0, "Scored application must have SHAP values")

    # --------------------------------------------------------------------------
    # 8. Friendly alias keys ('observed_days', 'payout_count', 'group_count')
    # --------------------------------------------------------------------------
    def test_08_alias_keys_supported_for_sufficiency(self):
        """Domain telemetry keys without 'feat_suf_' prefix must be properly recognized."""
        app_obj = self._create_application_with_signal(
            signal_metadata={
                "observed_days": 90.0,
                "payout_count": 12.0,
                "group_count": 4.0,
            }
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201, resp.text)
            data = resp.json()

            # Must be scored normally
            self.assertIn(data["risk_level"], ["LOWER", "MODERATE", "HIGHER"])
            self.assertIsNotNone(data["score"])
            self.assertIsNotNone(data["credit_score"])

    # --------------------------------------------------------------------------
    # 9. Adapter transform does NOT fabricate defaults
    # --------------------------------------------------------------------------
    def test_09_ml_model_adapter_transform_does_not_fabricate_defaults(self):
        """MLModelAdapter.transform_input_to_ml_dict must produce None for missing telemetry."""
        raw_input = AssessmentInput(
            requested_loan_amount=Decimal("20000.00"),
            loan_tenure_months=12,
            loan_purpose="WORKING_CAPITAL",
            gig_work_type="DELIVERY",
            years_working=Decimal("2.0"),
            average_working_days=24,
            average_income=Decimal("8000.00"),
            median_income=Decimal("7800.00"),
            derived_features={},  # Empty derived features
        )

        flat_dict = MLModelAdapter.transform_input_to_ml_dict(raw_input)

        self.assertIsNone(
            flat_dict.get("feat_suf_observed_days"),
            "feat_suf_observed_days must be None when not provided; 90.0 must NOT be defaulted",
        )
        self.assertIsNone(
            flat_dict.get("feat_suf_payout_count"),
            "feat_suf_payout_count must be None when not provided; 12.0 must NOT be defaulted",
        )
        self.assertIsNone(
            flat_dict.get("feat_suf_group_count"),
            "feat_suf_group_count must be None when not provided; 4.0 must NOT be defaulted",
        )
        self.assertEqual(
            flat_dict.get("feat_suf_missing_ratio"),
            1.0,
            "feat_suf_missing_ratio must indicate 1.0 (telemetry absent) when sufficiency is missing",
        )

    # --------------------------------------------------------------------------
    # 10. No LightGBM scoring occurs for insufficient evidence
    # --------------------------------------------------------------------------
    def test_10_no_lightgbm_scoring_occurs_for_insufficient_evidence(self):
        """Model predict_proba must never be called when an application has insufficient evidence."""
        app_obj = self._create_application_with_signal(signal_metadata=None)

        with patch.object(self.shared_predictor._model, "predict_proba") as mock_predict_proba:
            with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
                resp = self.client.post(
                    f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                    headers=self.applicant_headers,
                )
                self.assertEqual(resp.status_code, 201)
                data = resp.json()
                self.assertEqual(data["risk_level"], "INSUFFICIENT")
                mock_predict_proba.assert_not_called()

    # --------------------------------------------------------------------------
    # 11. Persisted assessment schema consistency
    # --------------------------------------------------------------------------
    def test_11_persisted_insufficient_assessment_schema_consistency(self):
        """Insufficient assessment in PostgreSQL/SQLite must persist null score and valid explanation."""
        app_obj = self._create_application_with_signal(signal_metadata={})

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.applicant_headers,
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            assessment_id = uuid.UUID(data["id"])

            # Query database record directly
            db_record = self.db.query(CreditAssessment).filter_by(id=assessment_id).first()
            self.assertIsNotNone(db_record)
            self.assertIsNone(db_record.credit_score)
            self.assertIsNone(db_record.risk_probability)
            self.assertEqual(db_record.risk_level, RiskLevel.INSUFFICIENT)
            self.assertIsNotNone(db_record.explanation)
            self.assertTrue(db_record.explanation.get("is_insufficient_evidence"))

            # GET endpoint returns identical record
            get_resp = self.client.get(
                f"/api/v1/assessments/{assessment_id}",
                headers=self.applicant_headers,
            )
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()
            self.assertEqual(get_data["risk_level"], "INSUFFICIENT")
            self.assertIsNone(get_data["score"])
            self.assertIsNone(get_data["credit_score"])
            self.assertTrue(get_data["explanation"]["is_insufficient_evidence"])

    # --------------------------------------------------------------------------
    # 12. Security: Consent enforcement blocks before sufficiency check
    # --------------------------------------------------------------------------
    def test_12_consent_enforcement_blocks_before_sufficiency_check(self):
        """Revoked or absent consent must block assessment with 403 before any evaluation occurs."""
        app_obj = self._create_application_with_signal(
            signal_metadata={"feat_suf_observed_days": 90.0, "feat_suf_payout_count": 12.0, "feat_suf_group_count": 4.0},
            consent_granted=False,
        )

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=true",
                headers=self.applicant_headers,
            )
            # Must be rejected due to consent violation
            self.assertEqual(resp.status_code, 403)
            self.assertIn("consent", resp.text.lower())

    # --------------------------------------------------------------------------
    # 13. Security: RBAC ownership
    # --------------------------------------------------------------------------
    def test_13_rbac_unauthorized_user_cannot_assess(self):
        """An applicant cannot initiate an assessment on another user's application."""
        app_obj = self._create_application_with_signal(signal_metadata=None)

        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            resp = self.client.post(
                f"/api/v1/applications/{app_obj.id}/assess?enforce_consent=false",
                headers=self.other_headers,  # Other applicant's token
            )
            self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
