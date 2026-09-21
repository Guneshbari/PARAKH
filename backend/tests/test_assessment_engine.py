"""Comprehensive unit and integration tests for the Assessment Engine Interface."""
import unittest
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional
from unittest.mock import MagicMock
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import (
    AssessmentEngineError,
    AssessmentInputError,
    AssessmentNotImplementedError,
    AssessmentOutputError,
)
from app.assessment.schemas import (
    PROHIBITED_FIELDS,
    AssessmentInput,
    AssessmentResult,
)
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.base import Base
from app.models.model_version import ModelVersion
from app.models.user import User, UserRole
from app.models.applicant import ApplicantProfile
from app.models.financial_signal import FinancialSignal, SignalSource
from app.schemas.assessment import CreditAssessmentCreate
from app.services.assessment import AssessmentService
from app.services.exceptions import EntityNotFoundError


class DummyValidEngine(AssessmentEngine):
    """Minimal dummy implementation to verify contract satisfaction."""

    @property
    def engine_name(self) -> str:
        return "DummyRuleEngine"

    @property
    def engine_version(self) -> str:
        return "0.1.0"

    def assess(self, input_data: AssessmentInput) -> AssessmentResult:
        # Simple rule-based calculation for dummy testing
        score = 720 if (input_data.average_income or 0) > 15000 else 580
        risk_level = RiskLevel.LOWER if score >= 700 else RiskLevel.MODERATE
        return AssessmentResult(
            score=score,
            risk_probability=Decimal("0.1250"),
            confidence=Decimal("0.8500"),
            risk_level=risk_level,
            model_name=self.engine_name,
            model_version=self.engine_version,
            debt_to_income=Decimal("0.2500"),
            utilization=Decimal("0.3000"),
            income_stability=Decimal("0.8000"),
            repayment_reliability=Decimal("0.9000"),
            key_factors=["Consistent active days", "Moderate debt obligation"],
            explanation={"average_income_weight": 0.45, "tenure_weight": 0.25},
        )


class DummyInvalidOutputEngine(AssessmentEngine):
    """Engine returning non-contract output to test detection."""

    def assess(self, input_data: AssessmentInput) -> Any:
        return {"raw_dict": "not_an_assessment_result"}


class TestAssessmentEngineInterface(unittest.TestCase):
    """Test interface contracts, constraints, and polymorphism."""

    def test_abstract_interface_cannot_be_instantiated(self):
        """Verify that AssessmentEngine ABC cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            AssessmentEngine()  # type: ignore

    def test_dummy_implementation_satisfies_interface(self):
        """Verify that a minimal concrete class can satisfy the interface."""
        engine = DummyValidEngine()
        self.assertEqual(engine.engine_name, "DummyRuleEngine")
        self.assertEqual(engine.engine_version, "0.1.0")

        input_data = AssessmentInput(
            requested_loan_amount=Decimal("50000"),
            loan_tenure_months=12,
            average_income=Decimal("25000"),
        )
        result = engine.assess(input_data)
        self.assertIsInstance(result, AssessmentResult)
        self.assertEqual(result.score, 720)
        self.assertEqual(result.risk_level, RiskLevel.LOWER)


class TestAssessmentInputContract(unittest.TestCase):
    """Test AssessmentInput validation, defaults, and data minimization."""

    def test_valid_assessment_input_creation(self):
        """Verify valid AssessmentInput creation with complete fields."""
        app_id = uuid.uuid4()
        prof_id = uuid.uuid4()

        input_data = AssessmentInput(
            application_id=app_id,
            applicant_profile_id=prof_id,
            requested_loan_amount=Decimal("35000.00"),
            loan_tenure_months=6,
            loan_purpose="Vehicle battery replacement",
            gig_work_type="food delivery",
            years_working=Decimal("2.5"),
            average_working_days=26,
            average_income=Decimal("22000.00"),
            median_income=Decimal("21500.00"),
            income_volatility=Decimal("0.15"),
            income_trend="GROWING",
            active_days=280,
            payment_regularity=Decimal("0.92"),
            cashflow_buffer=Decimal("5000.00"),
            existing_obligation=Decimal("3000.00"),
            platform_rating=Decimal("4.85"),
            repayment_reliability=Decimal("0.95"),
            derived_features={"payout_frequency_per_week": 2},
        )

        self.assertEqual(input_data.application_id, app_id)
        self.assertEqual(input_data.requested_loan_amount, Decimal("35000.00"))
        self.assertEqual(input_data.loan_tenure_months, 6)
        self.assertEqual(input_data.derived_features["payout_frequency_per_week"], 2)

    def test_invalid_requested_loan_amount_rejected(self):
        """Verify requested_loan_amount must be strictly positive."""
        with self.assertRaises(PydanticValidationError):
            AssessmentInput(requested_loan_amount=Decimal("0"))

        with self.assertRaises(PydanticValidationError):
            AssessmentInput(requested_loan_amount=Decimal("-1000"))

    def test_invalid_tenure_bounds(self):
        """Verify loan_tenure_months bounds [1, 120]."""
        with self.assertRaises(PydanticValidationError):
            AssessmentInput(
                requested_loan_amount=Decimal("10000"),
                loan_tenure_months=0,
            )

        with self.assertRaises(PydanticValidationError):
            AssessmentInput(
                requested_loan_amount=Decimal("10000"),
                loan_tenure_months=121,
            )

    def test_prohibited_raw_fields_rejected_by_extra_forbid(self):
        """Verify prohibited raw financial/PII fields are rejected immediately."""
        prohibited_samples = [
            {"raw_transactions": [{"id": 1, "amt": 500}]},
            {"raw_bank_statements": "PDF_BASE64"},
            {"raw_upi_transactions": ["txn1", "txn2"]},
            {"raw_upi_logs": "log_data"},
            {"merchant_name": "Cafe Coffee Day"},
            {"merchant_description": "Dining"},
            {"gps_coordinates": {"lat": 12.97, "lng": 77.59}},
            {"location_history": ["loc1", "loc2"]},
            {"contact_list": [{"name": "Boss", "phone": "12345"}]},
            {"password": "secret_password"},
            {"banking_login_credentials": {"user": "admin"}},
            {"bank_account_number": "1234567890"},
        ]

        for sample in prohibited_samples:
            with self.subTest(prohibited_field=list(sample.keys())[0]):
                payload = {"requested_loan_amount": Decimal("20000"), **sample}
                with self.assertRaises((PydanticValidationError, AssessmentInputError)):
                    AssessmentInput(**payload)

    def test_prohibited_fields_rejected_inside_derived_features(self):
        """Verify recursive validator rejects prohibited keys nested in derived_features."""
        nested_payload = {
            "requested_loan_amount": Decimal("20000"),
            "derived_features": {
                "valid_derived_metric": 123,
                "gps_coordinates": {"lat": 18.52, "lng": 73.85},
            },
        }
        with self.assertRaises(AssessmentInputError) as ctx:
            AssessmentInput(**nested_payload)
        self.assertIn("gps_coordinates", str(ctx.exception))

    def test_from_domain_objects_adapter(self):
        """Verify AssessmentInput.from_domain_objects extracts attributes correctly."""
        mock_app = MagicMock()
        mock_app.id = uuid.uuid4()
        mock_app.applicant_profile_id = uuid.uuid4()
        mock_app.requested_loan_amount = Decimal("40000.00")
        mock_app.preferred_repayment_period = 9
        mock_app.loan_purpose = "Grocery inventory purchase"

        mock_profile = MagicMock()
        mock_profile.gig_work_type = "ride hailing"
        mock_profile.years_working = Decimal("3.0")
        mock_profile.average_working_days = 24

        mock_signal = MagicMock()
        mock_signal.average_income = Decimal("28000.00")
        mock_signal.median_income = Decimal("27000.00")
        mock_signal.income_volatility = Decimal("0.12")
        mock_signal.income_trend = "STABLE"
        mock_signal.active_days = 310
        mock_signal.payment_regularity = Decimal("0.96")
        mock_signal.cashflow_buffer = Decimal("8000.00")
        mock_signal.existing_obligation = Decimal("2000.00")
        mock_signal.platform_rating = Decimal("4.90")
        mock_signal.repayment_reliability = Decimal("0.98")

        adapter_input = AssessmentInput.from_domain_objects(
            application=mock_app,
            applicant_profile=mock_profile,
            financial_signal=mock_signal,
            derived_features={"sample_metric": 42},
        )

        self.assertEqual(adapter_input.application_id, mock_app.id)
        self.assertEqual(adapter_input.applicant_profile_id, mock_app.applicant_profile_id)
        self.assertEqual(adapter_input.requested_loan_amount, Decimal("40000.00"))
        self.assertEqual(adapter_input.loan_tenure_months, 9)
        self.assertEqual(adapter_input.gig_work_type, "ride hailing")
        self.assertEqual(adapter_input.average_income, Decimal("28000.00"))
        self.assertEqual(adapter_input.derived_features["sample_metric"], 42)


class TestAssessmentResultContract(unittest.TestCase):
    """Test AssessmentResult validation, bounds, and ORM conversion."""

    def test_valid_assessment_result_creation(self):
        """Verify valid AssessmentResult creation with bounds and types."""
        result = AssessmentResult(
            score=750,
            risk_probability=Decimal("0.1500"),
            confidence=Decimal("0.9000"),
            risk_level=RiskLevel.LOWER,
            model_name="ParakhCreditScorer",
            model_version="1.0.0",
            debt_to_income=Decimal("0.2000"),
            utilization=Decimal("0.2500"),
            income_stability=Decimal("0.8500"),
            repayment_reliability=Decimal("0.9200"),
            key_factors=["High earnings regularity", "Low debt-to-income"],
            explanation={"income_weight": 0.4, "tenure_weight": 0.3},
        )

        self.assertEqual(result.score, 750)
        self.assertEqual(result.risk_probability, Decimal("0.1500"))
        self.assertEqual(result.confidence, Decimal("0.9000"))
        self.assertEqual(result.risk_level, RiskLevel.LOWER)
        self.assertEqual(result.model_name, "ParakhCreditScorer")
        self.assertEqual(len(result.key_factors), 2)

    def test_insufficient_evidence_nullable_scores(self):
        """Verify nullable scores for INSUFFICIENT evidence scenarios."""
        result = AssessmentResult(
            score=None,
            risk_probability=None,
            confidence=Decimal("0.2000"),
            risk_level=RiskLevel.INSUFFICIENT,
            model_name="ParakhColdStartScorer",
            model_version="1.0.0",
        )
        self.assertIsNone(result.score)
        self.assertIsNone(result.risk_probability)
        self.assertEqual(result.risk_level, RiskLevel.INSUFFICIENT)

    def test_invalid_probability_rejected(self):
        """Verify risk_probability outside [0, 1] is rejected."""
        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=600,
                risk_probability=Decimal("1.0001"),
                confidence=Decimal("0.8"),
                risk_level=RiskLevel.MODERATE,
                model_name="Engine",
                model_version="1.0",
            )

        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=600,
                risk_probability=Decimal("-0.01"),
                confidence=Decimal("0.8"),
                risk_level=RiskLevel.MODERATE,
                model_name="Engine",
                model_version="1.0",
            )

    def test_invalid_confidence_rejected(self):
        """Verify confidence outside [0, 1] is rejected."""
        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=600,
                risk_probability=Decimal("0.5"),
                confidence=Decimal("1.5"),
                risk_level=RiskLevel.MODERATE,
                model_name="Engine",
                model_version="1.0",
            )

        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=600,
                risk_probability=Decimal("0.5"),
                confidence=Decimal("-0.1"),
                risk_level=RiskLevel.MODERATE,
                model_name="Engine",
                model_version="1.0",
            )

    def test_invalid_score_bounds_rejected(self):
        """Verify credit score bounds [0, 1000]."""
        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=1001,
                risk_probability=Decimal("0.1"),
                risk_level=RiskLevel.LOWER,
                model_name="Engine",
                model_version="1.0",
            )

        with self.assertRaises(PydanticValidationError):
            AssessmentResult(
                score=-1,
                risk_probability=Decimal("0.1"),
                risk_level=RiskLevel.LOWER,
                model_name="Engine",
                model_version="1.0",
            )

    def test_risk_level_reuses_existing_domain_enum(self):
        """Verify that RiskLevel is the existing domain enum from app.models.assessment."""
        for level in [RiskLevel.LOWER, RiskLevel.MODERATE, RiskLevel.HIGHER, RiskLevel.INSUFFICIENT]:
            result = AssessmentResult(
                score=650,
                risk_level=level,
                model_name="Engine",
                model_version="1.0",
            )
            self.assertIs(result.risk_level, level)

    def test_to_credit_assessment_create_adapter(self):
        """Verify AssessmentResult can convert to CreditAssessmentCreate schema."""
        app_id = uuid.uuid4()
        mv_id = uuid.uuid4()

        result = AssessmentResult(
            score=700,
            risk_probability=Decimal("0.1800"),
            confidence=Decimal("0.8800"),
            risk_level=RiskLevel.LOWER,
            model_name="Engine",
            model_version="1.0",
            debt_to_income=Decimal("0.2200"),
            utilization=Decimal("0.1500"),
            income_stability=Decimal("0.8000"),
            repayment_reliability=Decimal("0.9000"),
        )

        create_dto = result.to_credit_assessment_create(
            application_id=app_id,
            model_version_id=mv_id,
        )

        self.assertIsInstance(create_dto, CreditAssessmentCreate)
        self.assertEqual(create_dto.application_id, app_id)
        self.assertEqual(create_dto.model_version_id, mv_id)
        self.assertEqual(create_dto.credit_score, 700)
        self.assertEqual(create_dto.risk_probability, Decimal("0.1800"))
        self.assertEqual(create_dto.risk_level, RiskLevel.LOWER)


class TestAssessmentServiceEngineIntegration(unittest.TestCase):
    """Test AssessmentService integration with AssessmentEngine dependency."""

    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_assessment_repo = MagicMock()
        self.mock_app_repo = MagicMock()
        self.mock_mv_repo = MagicMock()

    def test_service_without_engine_raises_error(self):
        """Verify calling assess_application without an engine raises AssessmentEngineError."""
        service = AssessmentService(
            db=self.mock_db,
            assessment_repo=self.mock_assessment_repo,
            app_repo=self.mock_app_repo,
            model_version_repo=self.mock_mv_repo,
        )
        with self.assertRaises(AssessmentEngineError):
            service.assess_application(application_id=uuid.uuid4())

    def test_service_uses_injected_engine_dependency(self):
        """Verify AssessmentService invokes injected engine and creates assessment."""
        engine = DummyValidEngine()
        service = AssessmentService(
            db=self.mock_db,
            assessment_repo=self.mock_assessment_repo,
            app_repo=self.mock_app_repo,
            model_version_repo=self.mock_mv_repo,
            engine=engine,
        )

        app_id = uuid.uuid4()
        mv_id = uuid.uuid4()

        mock_app = MagicMock()
        mock_app.id = app_id
        mock_app.applicant_profile_id = uuid.uuid4()
        mock_app.requested_loan_amount = Decimal("30000.00")
        mock_app.preferred_repayment_period = 6
        mock_app.loan_purpose = "Vehicle maintenance"
        mock_app.applicant_profile = None
        mock_app.financial_signals = []

        mock_mv = MagicMock()
        mock_mv.id = mv_id

        self.mock_app_repo.get_by_id.return_value = mock_app
        self.mock_mv_repo.get_active.return_value = mock_mv

        mock_created_assessment = MagicMock()
        self.mock_assessment_repo.create.return_value = mock_created_assessment

        created = service.assess_application(application_id=app_id)

        self.mock_app_repo.get_by_id.assert_called_with(app_id, db=self.mock_db)
        self.mock_assessment_repo.create.assert_called_once()
        self.assertEqual(created, mock_created_assessment)

    def test_invalid_engine_output_detected(self):
        """Verify AssessmentService raises AssessmentOutputError when engine returns malformed data."""
        bad_engine = DummyInvalidOutputEngine()
        self.mock_signal_repo = MagicMock()
        self.mock_signal_repo.get_latest.return_value = None
        service = AssessmentService(
            db=self.mock_db,
            assessment_repo=self.mock_assessment_repo,
            app_repo=self.mock_app_repo,
            model_version_repo=self.mock_mv_repo,
            signal_repo=self.mock_signal_repo,
            engine=bad_engine,
        )

        app_id = uuid.uuid4()
        mock_app = MagicMock()
        mock_app.id = app_id
        mock_app.applicant_profile_id = uuid.uuid4()
        mock_app.requested_loan_amount = Decimal("15000.00")
        mock_app.preferred_repayment_period = 6
        mock_app.loan_purpose = "Inventory purchase"
        mock_app.applicant_profile = None
        mock_app.financial_signals = []

        mock_mv = MagicMock()
        mock_mv.id = uuid.uuid4()

        self.mock_app_repo.get_by_id.return_value = mock_app
        self.mock_mv_repo.get_active.return_value = mock_mv

        with self.assertRaises(AssessmentOutputError):
            service.assess_application(application_id=app_id)


class TestAssessmentEngineEndToEndInMemory(unittest.TestCase):
    """End-to-end integration test of assessment engine flow in SQLite."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed ModelVersion, User, Profile, and Application
        self.mv = ModelVersion(
            model_name="DummyRuleEngine",
            version="0.1.0",
            algorithm="RuleBasedMock",
            description="Task 09 verification model version",
            is_active=True,
        )
        self.user = User(
            email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
            role=UserRole.APPLICANT,
        )
        self.db.add_all([self.mv, self.user])
        self.db.flush()

        self.profile = ApplicantProfile(
            user_id=self.user.id,
            gig_work_type="food delivery",
            years_working=Decimal("2.0"),
            average_working_days=25,
        )
        self.db.add(self.profile)
        self.db.flush()

        self.application = Application(
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("25000.00"),
            loan_purpose="Maintenance",
            preferred_repayment_period=6,
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.application)
        self.db.flush()

        self.signal = FinancialSignal(
            application_id=self.application.id,
            applicant_profile_id=self.profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("22000.00"),
            payment_regularity=Decimal("0.90"),
        )
        self.db.add(self.signal)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_end_to_end_assessment_execution(self):
        """Execute complete assessment workflow from application through engine to database."""
        scoring_engine = DummyValidEngine()
        service = AssessmentService(db=self.db, engine=scoring_engine)

        assessment = service.assess_application(
            application_id=self.application.id,
            auto_commit=True,
        )

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.application_id, self.application.id)
        self.assertEqual(assessment.model_version_id, self.mv.id)
        self.assertEqual(assessment.credit_score, 720)
        self.assertEqual(assessment.risk_level, RiskLevel.LOWER)
        self.assertEqual(assessment.risk_probability, Decimal("0.1250"))
        self.assertEqual(assessment.confidence, Decimal("0.8500"))


class TestAssessmentEnginePostgresIntegration(unittest.TestCase):
    """Integration test against live PostgreSQL database."""

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

    def test_live_postgres_assessment_engine_flow(self):
        """Verify engine execution and assessment persistence in live PostgreSQL without polluting DB."""
        unique_suffix = uuid.uuid4().hex[:8]
        user = User(
            email=f"pg_engine_{unique_suffix}@parakh.test",
            role=UserRole.APPLICANT,
        )
        self.db.add(user)
        self.db.flush()

        profile = ApplicantProfile(
            user_id=user.id,
            gig_work_type="parcel logistics",
            years_working=Decimal("3.5"),
            average_working_days=27,
        )
        self.db.add(profile)
        self.db.flush()

        application = Application(
            applicant_profile_id=profile.id,
            requested_loan_amount=Decimal("30000.00"),
            loan_purpose="Vehicle repair",
            preferred_repayment_period=12,
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(application)
        self.db.flush()

        signal = FinancialSignal(
            application_id=application.id,
            applicant_profile_id=profile.id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("25000.00"),
            payment_regularity=Decimal("0.90"),
        )
        self.db.add(signal)
        self.db.flush()

        mv = ModelVersion(
            model_name=f"DummyRuleEngine_{unique_suffix}",
            version="0.1.0",
            algorithm="RuleBasedMock",
            description="Task 09 Postgres test model version",
            is_active=True,
        )
        self.db.add(mv)
        self.db.flush()

        scoring_engine = DummyValidEngine()
        service = AssessmentService(db=self.db, engine=scoring_engine)

        assessment = service.assess_application(
            application_id=application.id,
            model_version_id=mv.id,
            auto_commit=False,  # Keep in rollback scope
        )

        self.assertIsNotNone(assessment.id)
        self.assertEqual(assessment.credit_score, 720)
        self.assertEqual(assessment.risk_level, RiskLevel.LOWER)

        # Cleanup rollback
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
