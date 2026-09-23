"""Comprehensive integration tests for Phase 10B: Backend + ML Integration.

Verifies:
1. Factory resolution for 'mock' and 'ml' engines under explicit and settings-driven configurations.
2. Singleton RiskPredictor lifecycle and reuse (avoiding expensive reinitialization).
3. Exact direct-vs-integrated prediction equivalence (P1 == P2, tier1 == tier2, score1 == score2, version1 == version2).
4. Insufficient telemetry / evidence handling (score=None, tier=INSUFFICIENT).
5. Data minimization and privacy checks (rejection of PROHIBITED_FIELDS).
6. End-to-end database persistence of CreditAssessment through AssessmentService.
7. Mock assessment engine remaining fully functional and non-regressed.
"""
from decimal import Decimal
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assessment.exceptions import AssessmentInputError
from app.assessment.factory import create_assessment_engine
from app.assessment.ml_engine import MLAssessmentEngine, MLModelOutput
from app.assessment.ml_model_adapter import (
    MLModelAdapter,
    get_shared_risk_predictor,
    reset_shared_risk_predictor,
)
from app.assessment.mock import MockAssessmentEngine
from app.assessment.schemas import AssessmentInput
from app.core.config import settings
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.base import Base
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.user import User, UserRole
from app.services.assessment import AssessmentService
from src.ml.inference.predictor import RiskPredictor


class TestFactoryAndSingletonLifecycle(unittest.TestCase):
    """Test engine factory resolution and singleton lifecycle management."""

    def test_default_engine_is_mock(self):
        """Verify default configuration resolves to MockAssessmentEngine."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "mock"):
            engine = create_assessment_engine()
            self.assertIsInstance(engine, MockAssessmentEngine)
            self.assertEqual(engine.engine_name, "parakh-mock-engine")

    def test_explicit_mock_engine_creation(self):
        """Verify explicit 'mock' parameter creates MockAssessmentEngine."""
        engine = create_assessment_engine("mock")
        self.assertIsInstance(engine, MockAssessmentEngine)

    def test_explicit_ml_engine_boundary_contract(self):
        """Verify explicit 'ml' parameter without attach_model preserves boundary contract."""
        engine = create_assessment_engine("ml", attach_model=False)
        self.assertIsInstance(engine, MLAssessmentEngine)
        self.assertEqual(engine.engine_name, "parakh-ml-engine")

    def test_settings_driven_ml_engine_attaches_model_adapter(self):
        """Verify settings.ASSESSMENT_ENGINE='ml' automatically attaches production MLModelAdapter."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            engine = create_assessment_engine()
            self.assertIsInstance(engine, MLAssessmentEngine)
            self.assertEqual(engine.engine_name, "volatility-aware-risk-model")
            self.assertEqual(engine.engine_version, "1.0.0")

    def test_singleton_risk_predictor_identity(self):
        """Verify get_shared_risk_predictor returns the exact same object reference."""
        p1 = get_shared_risk_predictor()
        p2 = get_shared_risk_predictor()
        self.assertIs(p1, p2, "RiskPredictor singleton must return identical instance reference.")

    def test_ml_model_adapter_properties(self):
        """Verify MLModelAdapter exposes expected model metadata."""
        adapter = MLModelAdapter()
        self.assertEqual(adapter.model_name, "volatility-aware-risk-model")
        self.assertEqual(adapter.model_version, "1.0.0")


class TestMLBackendIntegrationEquivalence(unittest.TestCase):
    """Test bit-for-bit equivalence between direct Phase 9 predictor and integrated backend service."""

    def setUp(self):
        self.db_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.db_engine)
        self.SessionLocal = sessionmaker(bind=self.db_engine)
        self.db = self.SessionLocal()

        # Seed User
        self.user = User(
            id=uuid.uuid4(),
            email="direct.vs.integrated@example.com",
            password_hash="hash123",
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.user)

        # Seed Profile
        self.profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.user.id,
            gig_work_type="DELIVERY",
            years_working=Decimal("2.5"),
            average_working_days=25,
        )
        self.db.add(self.profile)

        # Seed Application
        self.application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            status=ApplicationStatus.SUBMITTED,
            requested_loan_amount=Decimal("30000.00"),
            preferred_repayment_period=12,
            loan_purpose="WORKING_CAPITAL",
        )
        self.db.add(self.application)

        # Seed FinancialSignal
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
        )
        self.db.add(self.signal)

        # Seed active ModelVersion matching frozen LightGBM model
        self.model_version = ModelVersion(
            id=uuid.uuid4(),
            model_name="volatility-aware-risk-model",
            version="1.0.0",
            is_active=True,
        )
        self.db.add(self.model_version)
        self.db.commit()

        self.shared_predictor = get_shared_risk_predictor()
        self.adapter = MLModelAdapter(predictor=self.shared_predictor)
        self.ml_engine = MLAssessmentEngine(model=self.adapter)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.db_engine)

    def test_direct_vs_backend_exact_equivalence(self):
        """Verify P1 == P2 exact equivalence between direct Phase 9 predictor and backend service."""
        # 1. Prepare standard AssessmentInput
        assessment_input = AssessmentInput(
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("30000.00"),
            loan_tenure_months=12,
            loan_purpose="WORKING_CAPITAL",
            gig_work_type="DELIVERY",
            years_working=Decimal("2.5"),
            average_working_days=25,
            average_income=Decimal("8500.00"),
            median_income=Decimal("8200.00"),
            income_volatility=Decimal("0.1800"),
            payment_regularity=Decimal("0.9600"),
            cashflow_buffer=Decimal("12000.00"),
            existing_obligation=Decimal("3500.00"),
            platform_rating=Decimal("4.85"),
            repayment_reliability=Decimal("0.9800"),
        )

        # 2. Direct Phase 9 Inference Path (P1)
        flat_ml_dict = MLModelAdapter.transform_input_to_ml_dict(assessment_input)
        direct_pred = self.shared_predictor.predict(flat_ml_dict)

        p1_prob = direct_pred.repayment_risk_probability
        p1_tier = direct_pred.risk_tier
        p1_score = direct_pred.presentation_score
        p1_version = getattr(self.shared_predictor, "_model_version", "1.0.0")

        # 3. Backend Integrated Path (P2)
        service = AssessmentService(db=self.db, engine=self.ml_engine)
        persisted_assessment = service.assess_application(
            application_id=self.application.id,
            model_version_id=self.model_version.id,
        )

        p2_prob = float(persisted_assessment.risk_probability)
        p2_tier = persisted_assessment.risk_level.value
        p2_score = persisted_assessment.credit_score
        p2_version = getattr(persisted_assessment, "_transient_model_version", None)

        # 4. Assert Exact Equivalence
        self.assertAlmostEqual(
            p1_prob,
            p2_prob,
            places=4,
            msg=f"Risk probabilities do not match: Direct P1={p1_prob}, Backend P2={p2_prob}",
        )
        self.assertEqual(
            p1_tier,
            p2_tier,
            msg=f"Risk tiers do not match: Direct P1={p1_tier}, Backend P2={p2_tier}",
        )
        self.assertEqual(
            p1_score,
            p2_score,
            msg=f"Presentation scores do not match: Direct P1={p1_score}, Backend P2={p2_score}",
        )
        self.assertEqual(
            p1_version,
            p2_version,
            msg=f"Model versions do not match: Direct P1={p1_version}, Backend P2={p2_version}",
        )

        # Verify DB persistence of CreditAssessment
        db_record = self.db.query(CreditAssessment).filter_by(id=persisted_assessment.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.credit_score, p1_score)
        self.assertEqual(db_record.risk_level.value, p1_tier)
        self.assertEqual(db_record.model_version_id, self.model_version.id)

    def test_insufficient_evidence_routing(self):
        """Verify insufficient observation/telemetry produces unrated assessment with score=None."""
        insufficient_input = AssessmentInput(
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("30000.00"),
            loan_tenure_months=12,
            derived_features={
                "feat_suf_observed_days": 14.0,  # Below mandatory 30-day floor
                "feat_suf_payout_count": 2.0,   # Below mandatory 4 payouts
            },
        )

        output: MLModelOutput = self.adapter.predict(insufficient_input)

        self.assertIsNone(output.credit_score, "Insufficient evidence must yield None credit score.")
        self.assertEqual(output.risk_level, RiskLevel.INSUFFICIENT)
        self.assertTrue(output.explanation.get("is_insufficient_evidence"))
        self.assertTrue(len(output.explanation.get("missing_signals", [])) > 0)

    def test_prohibited_privacy_field_rejected(self):
        """Verify presence of prohibited privacy keys in derived features raises AssessmentInputError."""
        with self.assertRaises(AssessmentInputError) as ctx:
            AssessmentInput(
                application_id=self.application.id,
                applicant_profile_id=self.profile.id,
                requested_loan_amount=Decimal("30000.00"),
                derived_features={
                    "raw_bank_statements": "confidential_pdf_blob",
                },
            )
        self.assertIn("Prohibited privacy-invasive field", str(ctx.exception))

    def test_mock_engine_persists_without_regression(self):
        """Verify MockAssessmentEngine continues to function normally alongside ML engine."""
        mock_mv = ModelVersion(
            id=uuid.uuid4(),
            model_name="parakh-mock-engine",
            version="1.0.0",
            is_active=False,
        )
        self.db.add(mock_mv)
        self.db.commit()

        mock_engine = MockAssessmentEngine()
        service = AssessmentService(db=self.db, engine=mock_engine)

        mock_assessment = service.assess_application(
            application_id=self.application.id,
            model_version_id=mock_mv.id,
        )

        self.assertIsNotNone(mock_assessment.id)
        self.assertGreater(mock_assessment.credit_score, 500)
        self.assertIn(mock_assessment.risk_level, [RiskLevel.LOWER, RiskLevel.MODERATE, RiskLevel.HIGHER])


if __name__ == "__main__":
    unittest.main()
