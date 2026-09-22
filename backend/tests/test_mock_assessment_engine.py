"""Comprehensive tests for the MockAssessmentEngine implementation."""
import unittest
import uuid
from decimal import Decimal
from typing import Any, Dict
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import AssessmentInputError
from app.assessment.mock import MockAssessmentEngine
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.applicant import ApplicantProfile
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.base import Base
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.user import User, UserRole
from app.services.assessment import AssessmentService


class TestMockAssessmentEngineCore(unittest.TestCase):
    """Unit tests for MockAssessmentEngine rules, contracts, and determinism."""

    def setUp(self):
        self.engine = MockAssessmentEngine()

    def test_implements_assessment_engine_interface(self):
        """1. Verify mock engine implements AssessmentEngine ABC."""
        self.assertIsInstance(self.engine, AssessmentEngine)
        self.assertTrue(issubclass(MockAssessmentEngine, AssessmentEngine))

    def test_engine_metadata_availability(self):
        """2. Verify engine metadata is populated with expected identifier and version."""
        self.assertEqual(self.engine.engine_name, "parakh-mock-engine")
        self.assertEqual(self.engine.engine_version, "1.0.0")

    def test_deterministic_result_for_identical_input(self):
        """3 & 13. Verify identical input produces byte-for-byte identical AssessmentResult every time."""
        input_data = AssessmentInput(
            requested_loan_amount=Decimal("30000.00"),
            loan_tenure_months=6,
            average_income=Decimal("32000.00"),
            payment_regularity=Decimal("0.90"),
            years_working=Decimal("2.5"),
            average_working_days=25,
            cashflow_buffer=Decimal("6000.00"),
            existing_obligation=Decimal("3000.00"),
            platform_rating=Decimal("4.80"),
        )

        res_first = self.engine.assess(input_data)
        for _ in range(10):
            res_repeat = self.engine.assess(input_data)
            self.assertEqual(res_first.score, res_repeat.score)
            self.assertEqual(res_first.risk_probability, res_repeat.risk_probability)
            self.assertEqual(res_first.confidence, res_repeat.confidence)
            self.assertEqual(res_first.risk_level, res_repeat.risk_level)
            self.assertEqual(res_first.key_factors, res_repeat.key_factors)
            self.assertEqual(res_first.explanation, res_repeat.explanation)

    def test_high_quality_input_produces_lower_risk(self):
        """4. Verify strong financial and gig activity profile yields LOWER risk."""
        high_quality_input = AssessmentInput(
            requested_loan_amount=Decimal("25000.00"),
            loan_tenure_months=6,
            average_income=Decimal("45000.00"),
            median_income=Decimal("44000.00"),
            income_volatility=Decimal("0.08"),
            income_trend="GROWING",
            payment_regularity=Decimal("0.96"),
            repayment_reliability=Decimal("0.98"),
            years_working=Decimal("4.0"),
            average_working_days=27,
            active_days=320,
            cashflow_buffer=Decimal("12000.00"),
            existing_obligation=Decimal("2500.00"),
            platform_rating=Decimal("4.92"),
        )

        result = self.engine.assess(high_quality_input)
        self.assertIsInstance(result, AssessmentResult)
        self.assertIsNotNone(result.score)
        self.assertGreaterEqual(result.score, 700)
        self.assertEqual(result.risk_level, RiskLevel.LOWER)
        self.assertLessEqual(result.risk_probability, Decimal("0.3000"))
        self.assertGreaterEqual(result.confidence, Decimal("0.8000"))

    def test_low_quality_input_produces_higher_risk(self):
        """5. Verify weak or distressed indicators yield HIGHER risk."""
        low_quality_input = AssessmentInput(
            requested_loan_amount=Decimal("60000.00"),
            loan_tenure_months=12,
            average_income=Decimal("12000.00"),
            income_volatility=Decimal("0.45"),
            income_trend="DECLINING",
            payment_regularity=Decimal("0.35"),
            repayment_reliability=Decimal("0.30"),
            years_working=Decimal("0.5"),
            average_working_days=10,
            active_days=50,
            cashflow_buffer=Decimal("500.00"),
            existing_obligation=Decimal("9000.00"),  # DTI = 0.75
            platform_rating=Decimal("3.10"),
        )

        result = self.engine.assess(low_quality_input)
        self.assertIsInstance(result, AssessmentResult)
        self.assertIsNotNone(result.score)
        self.assertLess(result.score, 550)
        self.assertEqual(result.risk_level, RiskLevel.HIGHER)
        self.assertGreaterEqual(result.risk_probability, Decimal("0.6000"))

    def test_insufficient_evidence_handling(self):
        """6 & 9. Verify sparse/cold-start profiles return INSUFFICIENT risk with nullable score."""
        sparse_input = AssessmentInput(
            requested_loan_amount=Decimal("20000.00"),
            loan_purpose="Motorcycle repair",
            # Zero financial indicators, zero work signals
        )

        result = self.engine.assess(sparse_input)
        self.assertIsInstance(result, AssessmentResult)
        self.assertIsNone(result.score)
        self.assertEqual(result.risk_level, RiskLevel.INSUFFICIENT)
        self.assertGreaterEqual(result.risk_probability, Decimal("0.0"))
        self.assertLessEqual(result.risk_probability, Decimal("1.0"))
        self.assertGreaterEqual(result.confidence, Decimal("0.0"))
        self.assertLessEqual(result.confidence, Decimal("1.0"))
        self.assertTrue(len(result.key_factors) > 0)
        self.assertTrue(result.explanation.get("insufficient_evidence"))

    def test_score_within_bounds(self):
        """7. Verify credit score always remains within [0, 1000] or is None."""
        test_inputs = [
            # Ultra low
            AssessmentInput(
                requested_loan_amount=Decimal("100000.00"),
                average_income=Decimal("1000.00"),
                payment_regularity=Decimal("0.05"),
            ),
            # Average
            AssessmentInput(
                requested_loan_amount=Decimal("20000.00"),
                average_income=Decimal("25000.00"),
                payment_regularity=Decimal("0.70"),
            ),
            # Max possible
            AssessmentInput(
                requested_loan_amount=Decimal("10000.00"),
                average_income=Decimal("90000.00"),
                payment_regularity=Decimal("1.0"),
                repayment_reliability=Decimal("1.0"),
                years_working=Decimal("10.0"),
                average_working_days=31,
                active_days=365,
                cashflow_buffer=Decimal("50000.00"),
                existing_obligation=Decimal("0.00"),
                platform_rating=Decimal("5.0"),
            ),
        ]

        for inp in test_inputs:
            res = self.engine.assess(inp)
            if res.score is not None:
                self.assertGreaterEqual(res.score, 0)
                self.assertLessEqual(res.score, 1000)

    def test_risk_probability_within_bounds(self):
        """8. Verify risk_probability is bounded [0, 1]."""
        inp = AssessmentInput(
            requested_loan_amount=Decimal("30000.00"),
            average_income=Decimal("28000.00"),
            payment_regularity=Decimal("0.85"),
        )
        res = self.engine.assess(inp)
        self.assertGreaterEqual(res.risk_probability, Decimal("0.0000"))
        self.assertLessEqual(res.risk_probability, Decimal("1.0000"))

    def test_confidence_within_bounds(self):
        """9. Verify confidence is bounded [0, 1]."""
        inp = AssessmentInput(
            requested_loan_amount=Decimal("15000.00"),
            average_income=Decimal("18000.00"),
            payment_regularity=Decimal("0.75"),
        )
        res = self.engine.assess(inp)
        self.assertGreaterEqual(res.confidence, Decimal("0.0000"))
        self.assertLessEqual(res.confidence, Decimal("1.0000"))

    def test_risk_level_reuses_existing_enum(self):
        """10. Verify RiskLevel is strictly the domain enum from app.models.assessment."""
        inp = AssessmentInput(
            requested_loan_amount=Decimal("20000.00"),
            average_income=Decimal("35000.00"),
            payment_regularity=Decimal("0.90"),
        )
        res = self.engine.assess(inp)
        self.assertIsInstance(res.risk_level, RiskLevel)

    def test_key_factors_populated(self):
        """11. Verify key_factors are human-readable and non-empty."""
        inp = AssessmentInput(
            requested_loan_amount=Decimal("30000.00"),
            average_income=Decimal("40000.00"),
            payment_regularity=Decimal("0.95"),
            cashflow_buffer=Decimal("10000.00"),
            existing_obligation=Decimal("2000.00"),
        )
        res = self.engine.assess(inp)
        self.assertIsInstance(res.key_factors, list)
        self.assertGreater(len(res.key_factors), 0)
        for factor in res.key_factors:
            self.assertIsInstance(factor, str)
            self.assertGreater(len(factor), 5)

    def test_explanation_structure_populated(self):
        """12. Verify explanation dictionary contains structured component scores and weights."""
        inp = AssessmentInput(
            requested_loan_amount=Decimal("25000.00"),
            average_income=Decimal("30000.00"),
            payment_regularity=Decimal("0.85"),
        )
        res = self.engine.assess(inp)
        self.assertIsInstance(res.explanation, dict)
        self.assertIn("components", res.explanation)
        self.assertIn("weights", res.explanation)
        self.assertIn("income_stability", res.explanation["components"])
        self.assertIn("payment_reliability", res.explanation["components"])
        self.assertIn("engine_note", res.explanation)

    def test_prohibited_input_remains_rejected(self):
        """14. Verify privacy boundaries reject raw/sensitive fields before reaching scoring."""
        prohibited_payloads = [
            {"requested_loan_amount": Decimal("10000"), "raw_transactions": ["txn1"]},
            {"requested_loan_amount": Decimal("10000"), "raw_bank_statements": "pdf"},
            {"requested_loan_amount": Decimal("10000"), "raw_upi_transactions": [1, 2]},
            {"requested_loan_amount": Decimal("10000"), "merchant_name": "Store"},
            {"requested_loan_amount": Decimal("10000"), "gps_coordinates": {"lat": 12.9}},
            {"requested_loan_amount": Decimal("10000"), "banking_login_credentials": "pwd"},
        ]

        for payload in prohibited_payloads:
            with self.subTest(field=list(payload.keys())[1]):
                with self.assertRaises((PydanticValidationError, AssessmentInputError)):
                    AssessmentInput(**payload)


class TestMockAssessmentEngineServiceIntegration(unittest.TestCase):
    """15. Test AssessmentService integration using MockAssessmentEngine."""

    def test_service_with_mock_engine(self):
        """Verify AssessmentService successfully executes MockAssessmentEngine."""
        mock_db = unittest.mock.MagicMock()
        mock_app_repo = unittest.mock.MagicMock()
        mock_assessment_repo = unittest.mock.MagicMock()
        mock_mv_repo = unittest.mock.MagicMock()
        mock_signal_repo = unittest.mock.MagicMock()

        engine = MockAssessmentEngine()
        service = AssessmentService(
            db=mock_db,
            assessment_repo=mock_assessment_repo,
            app_repo=mock_app_repo,
            model_version_repo=mock_mv_repo,
            signal_repo=mock_signal_repo,
            engine=engine,
        )

        app_id = uuid.uuid4()
        mv_id = uuid.uuid4()

        mock_app = unittest.mock.MagicMock()
        mock_app.id = app_id
        mock_app.applicant_profile_id = uuid.uuid4()
        mock_app.requested_loan_amount = Decimal("25000.00")
        mock_app.preferred_repayment_period = 6
        mock_app.loan_purpose = "Inventory"
        mock_app.applicant_profile = None

        mock_signal = unittest.mock.MagicMock()
        mock_signal.average_income = Decimal("35000.00")
        mock_signal.payment_regularity = Decimal("0.90")
        mock_signal.median_income = None
        mock_signal.income_volatility = None
        mock_signal.income_trend = None
        mock_signal.active_days = None
        mock_signal.cashflow_buffer = None
        mock_signal.existing_obligation = None
        mock_signal.platform_rating = None
        mock_signal.repayment_reliability = None

        mock_mv = unittest.mock.MagicMock()
        mock_mv.id = mv_id

        mock_app_repo.get_by_id.return_value = mock_app
        mock_mv_repo.get_active.return_value = mock_mv
        mock_signal_repo.get_latest.return_value = mock_signal

        mock_created_assessment = unittest.mock.MagicMock()
        mock_assessment_repo.create.return_value = mock_created_assessment

        created = service.assess_application(application_id=app_id)

        mock_app_repo.get_by_id.assert_called_with(app_id, db=mock_db)
        mock_assessment_repo.create.assert_called_once()
        self.assertEqual(created, mock_created_assessment)


class TestMockAssessmentEngineEndToEndSQLite(unittest.TestCase):
    """16. End-to-end integration test of MockAssessmentEngine with SQLite in-memory."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.mv = ModelVersion(
            model_name="parakh-mock-engine",
            version="1.0.0",
            algorithm="DeterministicRuleMock",
            description="TASK 10 Mock Assessment Engine",
            is_active=True,
        )
        self.user = User(
            email=f"mock_worker_{uuid.uuid4().hex[:6]}@parakh.test",
            role=UserRole.APPLICANT,
        )
        self.db.add_all([self.mv, self.user])
        self.db.flush()

        self.profile = ApplicantProfile(
            user_id=self.user.id,
            gig_work_type="food delivery",
            years_working=Decimal("2.5"),
            average_working_days=25,
        )
        self.db.add(self.profile)
        self.db.flush()

        self.application = Application(
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("30000.00"),
            loan_purpose="Two-wheeler maintenance",
            preferred_repayment_period=6,
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.application)
        self.db.flush()

        self.signal = FinancialSignal(
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("32000.00"),
            payment_regularity=Decimal("0.88"),
            cashflow_buffer=Decimal("5000.00"),
            existing_obligation=Decimal("2000.00"),
        )
        self.db.add(self.signal)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_e2e_sqlite_mock_assessment_workflow(self):
        """Verify complete assessment workflow: DB -> Service -> MockEngine -> DB."""
        mock_engine = MockAssessmentEngine()
        service = AssessmentService(db=self.db, engine=mock_engine)

        assessment = service.assess_application(
            application_id=self.application.id,
            auto_commit=True,
        )

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.application_id, self.application.id)
        self.assertEqual(assessment.model_version_id, self.mv.id)
        self.assertIsNotNone(assessment.credit_score)
        self.assertGreaterEqual(assessment.credit_score, 300)
        self.assertLessEqual(assessment.credit_score, 850)
        self.assertIn(assessment.risk_level, [RiskLevel.LOWER, RiskLevel.MODERATE, RiskLevel.HIGHER])
        self.assertGreaterEqual(assessment.confidence, Decimal("0.3000"))


class TestMockAssessmentEnginePostgresIntegration(unittest.TestCase):
    """17. Live PostgreSQL integration test for MockAssessmentEngine."""

    def setUp(self):
        try:
            self.engine = create_engine(settings.DATABASE_URL)
            with self.engine.connect() as conn:
                pass
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.db = self.SessionLocal()
        except Exception as e:
            self.skipTest(f"Live PostgreSQL database not available: {e}")

    def tearDown(self):
        if hasattr(self, "db"):
            self.db.rollback()
            self.db.close()
        if hasattr(self, "engine"):
            self.engine.dispose()

    def test_live_postgres_mock_assessment_flow(self):
        """Verify MockAssessmentEngine flow persists correctly into live PostgreSQL without polluting DB."""
        unique_suffix = uuid.uuid4().hex[:8]
        user = User(
            email=f"pg_mock_{unique_suffix}@parakh.test",
            role=UserRole.APPLICANT,
        )
        self.db.add(user)
        self.db.flush()

        profile = ApplicantProfile(
            user_id=user.id,
            gig_work_type="ride hailing",
            years_working=Decimal("3.0"),
            average_working_days=26,
        )
        self.db.add(profile)
        self.db.flush()

        application = Application(
            applicant_profile_id=profile.id,
            requested_loan_amount=Decimal("35000.00"),
            loan_purpose="Commercial permit fees",
            preferred_repayment_period=12,
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(application)
        self.db.flush()

        signal = FinancialSignal(
            application_id=application.id,
            applicant_profile_id=profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("38000.00"),
            payment_regularity=Decimal("0.92"),
            cashflow_buffer=Decimal("7000.00"),
            existing_obligation=Decimal("2500.00"),
        )
        self.db.add(signal)
        self.db.flush()

        mv = ModelVersion(
            model_name=f"parakh-mock-engine_{unique_suffix}",
            version="1.0.0",
            algorithm="DeterministicRuleMock",
            description="TASK 10 Postgres integration mock model version",
            is_active=True,
        )
        self.db.add(mv)
        self.db.flush()

        mock_engine = MockAssessmentEngine()
        service = AssessmentService(db=self.db, engine=mock_engine)

        assessment = service.assess_application(
            application_id=application.id,
            model_version_id=mv.id,
            auto_commit=False,  # Keep within rollback scope
        )

        self.assertIsNotNone(assessment.id)
        self.assertIsNotNone(assessment.credit_score)
        self.assertGreaterEqual(assessment.credit_score, 600)
        self.assertIn(assessment.risk_level, [RiskLevel.LOWER, RiskLevel.MODERATE])
        self.assertGreaterEqual(assessment.confidence, Decimal("0.5000"))

        # Roll back to keep test clean
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
