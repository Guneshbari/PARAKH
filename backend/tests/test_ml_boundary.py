"""Unit and integration tests for Phase 10: ML-Ready Boundary architecture.

Verifies:
1. AssessmentEngine contract decoupling and engine selection factory.
2. MockAssessmentEngine remaining the active default.
3. FeaturePipeline boundary for Person 2's engineered features.
4. MLModel and MLAssessmentEngine boundary for Person 3's predictions.
5. Standard AssessmentResult mapping cleanly into CreditAssessment persistence.
6. Data-minimization enforcement across the pipeline.
"""
import unittest
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import (
    AssessmentEngineError,
    AssessmentInputError,
    AssessmentNotImplementedError,
    AssessmentOutputError,
)
from app.assessment.factory import create_assessment_engine
from app.assessment.ml_engine import (
    MLAssessmentEngine,
    MLModel,
    MLModelOutput,
)
from app.assessment.mock import MockAssessmentEngine
from app.assessment.pipeline import (
    FeaturePipeline,
    PassthroughFeaturePipeline,
)
from app.assessment.schemas import (
    AssessmentInput,
    AssessmentResult,
)
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.applicant import ApplicantProfile
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.base import Base
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.user import User, UserRole
from app.services.assessment import AssessmentService


class DummyTestModel(MLModel):
    """Dummy MLModel implementation to verify Person 3 boundary without fabricating logic."""

    @property
    def model_name(self) -> str:
        return "test-lightgbm-boundary"

    @property
    def model_version(self) -> str:
        return "1.0.0-test"

    def predict(self, input_data: AssessmentInput) -> MLModelOutput:
        # Verify input_data provides loan info and derived_features
        feat = input_data.derived_features
        score = 760 if feat.get("custom_ratio", 0) > 0.5 else 590
        risk_level = RiskLevel.LOWER if score >= 700 else RiskLevel.MODERATE
        return MLModelOutput(
            risk_probability=Decimal("0.0850"),
            confidence=Decimal("0.9200"),
            credit_score=score,
            risk_level=risk_level,
            key_factors=["Strong custom ratio", "High platform consistency"],
            explanation={"custom_ratio_weight": 0.42},
            debt_to_income=Decimal("0.2100"),
            utilization=Decimal("0.1900"),
            income_stability=Decimal("0.8900"),
            repayment_reliability=Decimal("0.9600"),
        )


class DummyFeaturePipeline(FeaturePipeline):
    """Dummy FeaturePipeline implementation to verify Person 2 boundary."""

    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return {
            "custom_ratio": 0.75,
            "signal_count": len(signals),
        }


class TestEngineSelectionAndFactory(unittest.TestCase):
    """Test engine selection, configuration, and default behaviors."""

    def test_default_engine_is_mock(self):
        """Verify that default settings produce MockAssessmentEngine."""
        engine = create_assessment_engine()
        self.assertIsInstance(engine, MockAssessmentEngine)
        self.assertEqual(engine.engine_name, "parakh-mock-engine")

    def test_explicit_mock_engine_creation(self):
        """Verify that requesting 'mock' creates MockAssessmentEngine."""
        engine = create_assessment_engine("mock")
        self.assertIsInstance(engine, MockAssessmentEngine)

    def test_explicit_ml_engine_creation(self):
        """Verify that requesting 'ml' creates MLAssessmentEngine."""
        engine = create_assessment_engine("ml")
        self.assertIsInstance(engine, MLAssessmentEngine)
        self.assertEqual(engine.engine_name, "parakh-ml-engine")

    def test_invalid_engine_name_raises_error(self):
        """Verify that an unsupported engine name raises AssessmentEngineError."""
        with self.assertRaises(AssessmentEngineError) as ctx:
            create_assessment_engine("unsupported-engine-xyz")
        self.assertIn("Unsupported assessment engine", str(ctx.exception))

    def test_settings_override_selects_engine(self):
        """Verify that setting settings.ASSESSMENT_ENGINE changes factory output."""
        with patch.object(settings, "ASSESSMENT_ENGINE", "ml"):
            engine = create_assessment_engine()
            self.assertIsInstance(engine, MLAssessmentEngine)


class TestPerson2FeaturePipelineBoundary(unittest.TestCase):
    """Test Person 2 FeaturePipeline interface, passthrough, and data minimization."""

    def test_passthrough_pipeline_propagates_signal_metadata(self):
        """Verify PassthroughFeaturePipeline extracts non-sensitive signal_metadata."""
        pipeline = PassthroughFeaturePipeline()
        mock_signal = MagicMock()
        mock_signal.signal_metadata = {"extracted_score": 42, "trend_factor": 1.2}

        features = pipeline.extract_features(signals=[mock_signal])
        self.assertEqual(features["extracted_score"], 42)
        self.assertEqual(features["trend_factor"], 1.2)

    def test_passthrough_pipeline_empty_signals(self):
        """Verify PassthroughFeaturePipeline handles empty signals gracefully."""
        pipeline = PassthroughFeaturePipeline()
        features = pipeline.extract_features(signals=[])
        self.assertEqual(features, {})

    def test_feature_pipeline_violating_data_minimization_rejected(self):
        """Verify that prohibited fields in signal_metadata raise AssessmentInputError."""
        pipeline = PassthroughFeaturePipeline()
        mock_signal = MagicMock()
        mock_signal.signal_metadata = {"raw_transactions": ["txn1", "txn2"]}

        with self.assertRaises(AssessmentInputError):
            pipeline.extract_features(signals=[mock_signal])

    def test_custom_feature_pipeline_satisfies_contract(self):
        """Verify that a custom FeaturePipeline implementation works seamlessly."""
        pipeline = DummyFeaturePipeline()
        features = pipeline.extract_features(signals=[{"id": 1}, {"id": 2}])
        self.assertEqual(features["custom_ratio"], 0.75)
        self.assertEqual(features["signal_count"], 2)


class TestPerson3MLModelBoundary(unittest.TestCase):
    """Test Person 3 MLModel interface, MLAssessmentEngine, and mapping to AssessmentResult."""

    def test_ml_engine_without_model_raises_not_implemented(self):
        """Verify MLAssessmentEngine without a registered model raises AssessmentNotImplementedError."""
        engine = MLAssessmentEngine()
        input_data = AssessmentInput(
            requested_loan_amount=Decimal("25000"),
            loan_tenure_months=6,
        )
        with self.assertRaises(AssessmentNotImplementedError):
            engine.assess(input_data)

    def test_ml_engine_with_model_produces_assessment_result(self):
        """Verify MLAssessmentEngine with registered model produces a valid AssessmentResult."""
        model = DummyTestModel()
        engine = MLAssessmentEngine(model=model)

        self.assertEqual(engine.engine_name, "test-lightgbm-boundary")
        self.assertEqual(engine.engine_version, "1.0.0-test")

        input_data = AssessmentInput(
            requested_loan_amount=Decimal("30000"),
            loan_tenure_months=12,
            derived_features={"custom_ratio": 0.8},
        )
        result = engine.assess(input_data)

        self.assertIsInstance(result, AssessmentResult)
        self.assertEqual(result.score, 760)
        self.assertEqual(result.risk_level, RiskLevel.LOWER)
        self.assertEqual(result.risk_probability, Decimal("0.0850"))
        self.assertEqual(result.confidence, Decimal("0.9200"))
        self.assertEqual(result.model_name, "test-lightgbm-boundary")
        self.assertEqual(result.model_version, "1.0.0-test")
        self.assertIn("Strong custom ratio", result.key_factors)
        self.assertIn("custom_ratio_weight", result.explanation)

    def test_ml_engine_rejects_invalid_model_output(self):
        """Verify MLAssessmentEngine validates that model returns MLModelOutput."""
        bad_model = MagicMock()
        bad_model.predict.return_value = {"raw": "dict"}  # Not MLModelOutput
        bad_model.model_name = "bad-model"
        bad_model.model_version = "0.0.1"

        engine = MLAssessmentEngine(model=bad_model)
        input_data = AssessmentInput(requested_loan_amount=Decimal("10000"))

        with self.assertRaises(AssessmentOutputError):
            engine.assess(input_data)


class TestAssessmentServiceMLReadyIntegration(unittest.TestCase):
    """Test AssessmentService integration with AssessmentEngine, FeaturePipeline, and CreditAssessment persistence."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed User
        self.user = User(
            id=uuid.uuid4(),
            email="boundary.test@example.com",
            password_hash="hash",
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add(self.user)

        # Seed Profile
        self.profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.user.id,
            gig_work_type="RIDE_HAILING",
            years_working=Decimal("3.0"),
            average_working_days=24,
        )
        self.db.add(self.profile)

        # Seed Application
        self.application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            status=ApplicationStatus.SUBMITTED,
            requested_loan_amount=Decimal("45000.00"),
            preferred_repayment_period=12,
            loan_purpose="Vehicle repair",
        )
        self.db.add(self.application)

        # Seed FinancialSignal
        self.signal = FinancialSignal(
            id=uuid.uuid4(),
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("35000.00"),
            median_income=Decimal("34000.00"),
            income_volatility=Decimal("0.1200"),
            payment_regularity=Decimal("0.9500"),
            cashflow_buffer=Decimal("15000.00"),
            existing_obligation=Decimal("5000.00"),
            platform_rating=Decimal("4.80"),
            repayment_reliability=Decimal("0.9800"),
        )
        self.db.add(self.signal)

        # Seed ModelVersion
        self.model_version = ModelVersion(
            id=uuid.uuid4(),
            model_name="parakh-mock-engine",
            version="1.0.0",
            is_active=True,
        )
        self.db.add(self.model_version)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_mock_engine_persists_credit_assessment(self):
        """Verify MockAssessmentEngine runs via AssessmentService and persists to CreditAssessment."""
        service = AssessmentService(db=self.db, engine=MockAssessmentEngine())
        assessment = service.assess_application(application_id=self.application.id)

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.application_id, self.application.id)
        self.assertEqual(assessment.model_version_id, self.model_version.id)
        self.assertGreater(assessment.credit_score, 500)
        self.assertEqual(assessment.risk_level, RiskLevel.LOWER)

        # Verify DB persistence
        db_record = self.db.query(CreditAssessment).filter_by(id=assessment.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.credit_score, assessment.credit_score)

    def test_ml_engine_with_model_persists_credit_assessment(self):
        """Verify MLAssessmentEngine with Person 3 model persists identically to existing CreditAssessment table."""
        ml_model = DummyTestModel()
        ml_engine = MLAssessmentEngine(model=ml_model)
        feature_pipeline = DummyFeaturePipeline()

        # Seed matching model version
        mv_ml = ModelVersion(
            id=uuid.uuid4(),
            model_name=ml_model.model_name,
            version=ml_model.model_version,
            is_active=False,
        )
        self.db.add(mv_ml)
        self.db.commit()

        service = AssessmentService(
            db=self.db,
            engine=ml_engine,
            feature_pipeline=feature_pipeline,
        )

        assessment = service.assess_application(
            application_id=self.application.id,
            model_version_id=mv_ml.id,
        )

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.credit_score, 760)
        self.assertEqual(assessment.risk_level, RiskLevel.LOWER)
        self.assertEqual(assessment.risk_probability, Decimal("0.0850"))
        self.assertEqual(assessment.confidence, Decimal("0.9200"))

        # Verify exact same PostgreSQL/SQLite credit_assessments table is used
        db_record = self.db.query(CreditAssessment).filter_by(id=assessment.id).first()
        self.assertIsNotNone(db_record)
        self.assertEqual(db_record.credit_score, 760)
        self.assertEqual(db_record.risk_probability, Decimal("0.0850"))


if __name__ == "__main__":
    unittest.main()
