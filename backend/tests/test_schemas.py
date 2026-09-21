"""Unit tests for Pydantic schemas validating API request/response contracts."""
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    Consent,
    ConsentDataSource,
    CreditAssessment,
    FinancialSignal,
    ModelVersion,
    ReviewOutcome,
    ReviewOutcomeType,
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)
from app.schemas import (
    ApplicantProfileCreate,
    ApplicantProfileResponse,
    ApplicantProfileUpdate,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationSummary,
    ApplicationUpdate,
    AuditLogResponse,
    ConsentCreate,
    ConsentResponse,
    CreditAssessmentCreate,
    CreditAssessmentResponse,
    FinancialSignalCreate,
    FinancialSignalResponse,
    ModelVersionCreate,
    ModelVersionResponse,
    ReviewOutcomeCreate,
    ReviewOutcomeResponse,
    UserCreate,
    UserResponse,
    UserSummary,
)


class TestPydanticSchemas(unittest.TestCase):
    """Test suite validating Pydantic contract rules, validation, and ORM conversion."""

    def test_user_create_and_validation(self) -> None:
        """Verify UserCreate accepts valid inputs and enforces validation."""
        valid_user = UserCreate(email="worker@gigplatform.com", password="StrongPassword123")
        self.assertEqual(valid_user.email, "worker@gigplatform.com")
        self.assertEqual(valid_user.role, UserRole.APPLICANT)

        # Rejects short password (<8 chars)
        with self.assertRaises(ValidationError):
            UserCreate(email="worker@gigplatform.com", password="short")

        # Rejects invalid email syntax
        with self.assertRaises(ValidationError):
            UserCreate(email="not-an-email", password="StrongPassword123")

        # Rejects invalid role enum
        with self.assertRaises(ValidationError):
            UserCreate(email="worker@gigplatform.com", password="StrongPassword123", role="INVALID_ROLE")

    def test_user_response_privacy_and_orm_compatibility(self) -> None:
        """Verify UserResponse serializes ORM models and never exposes password_hash."""
        self.assertNotIn("password", UserResponse.model_fields)
        self.assertNotIn("password_hash", UserResponse.model_fields)
        self.assertNotIn("password_hash", UserSummary.model_fields)

        now = datetime.now(timezone.utc)
        user_orm = User(
            id=uuid.uuid4(),
            email="omkar@example.com",
            password_hash="$2b$12$e8Y...hash...",
            role=UserRole.APPLICANT,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        user_resp = UserResponse.model_validate(user_orm)
        dumped = user_resp.model_dump()
        self.assertEqual(dumped["id"], user_orm.id)
        self.assertEqual(dumped["email"], "omkar@example.com")
        self.assertNotIn("password_hash", dumped)
        self.assertNotIn("password", dumped)

    def test_applicant_profile_validation_and_orm(self) -> None:
        """Verify ApplicantProfile validation and ORM serialization."""
        profile_in = ApplicantProfileCreate(
            gig_work_type="Food Delivery",
            years_working=Decimal("3.5"),
            average_working_days=26,
            business_or_loan_purpose="Vehicle maintenance",
        )
        self.assertEqual(profile_in.gig_work_type, "Food Delivery")

        # Reject negative working days or > 31
        with self.assertRaises(ValidationError):
            ApplicantProfileCreate(gig_work_type="Delivery", average_working_days=35)
        with self.assertRaises(ValidationError):
            ApplicantProfileCreate(gig_work_type="Delivery", average_working_days=-1)

        # Reject negative years working
        with self.assertRaises(ValidationError):
            ApplicantProfileCreate(gig_work_type="Delivery", years_working=Decimal("-1.0"))

        now = datetime.now(timezone.utc)
        orm_profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            gig_work_type="Ride Hailing",
            years_working=Decimal("2.0"),
            average_working_days=22,
            business_or_loan_purpose="Fuel advance",
            created_at=now,
            updated_at=now,
        )
        resp = ApplicantProfileResponse.model_validate(orm_profile)
        self.assertEqual(resp.gig_work_type, "Ride Hailing")
        self.assertEqual(resp.id, orm_profile.id)

    def test_application_validation_and_orm(self) -> None:
        """Verify Application loan amount constraints and ORM serialization."""
        profile_id = uuid.uuid4()
        valid_app = ApplicationCreate(
            applicant_profile_id=profile_id,
            requested_loan_amount=Decimal("25000.00"),
            loan_purpose="Smartphone upgrade for delivery app",
            preferred_repayment_period=6,
        )
        self.assertEqual(valid_app.requested_loan_amount, Decimal("25000.00"))

        # Loan amount must be strictly positive (>0)
        with self.assertRaises(ValidationError):
            ApplicationCreate(
                applicant_profile_id=profile_id,
                requested_loan_amount=Decimal("0.00"),
            )
        with self.assertRaises(ValidationError):
            ApplicationCreate(
                applicant_profile_id=profile_id,
                requested_loan_amount=Decimal("-5000.00"),
            )

        now = datetime.now(timezone.utc)
        orm_app = Application(
            id=uuid.uuid4(),
            applicant_profile_id=profile_id,
            requested_loan_amount=Decimal("15000.00"),
            loan_purpose="Equipment purchase",
            preferred_repayment_period=3,
            status=ApplicationStatus.SUBMITTED,
            created_at=now,
            updated_at=now,
        )
        app_resp = ApplicationResponse.model_validate(orm_app)
        self.assertEqual(app_resp.status, ApplicationStatus.SUBMITTED)
        self.assertEqual(app_resp.requested_loan_amount, Decimal("15000.00"))

        summary = ApplicationSummary.model_validate(orm_app)
        self.assertEqual(summary.status, ApplicationStatus.SUBMITTED)

    def test_consent_validation_and_orm(self) -> None:
        """Verify Consent schemas enforce valid data sources and ORM mapping."""
        consent_in = ConsentCreate(
            data_source=ConsentDataSource.PLATFORM,
            purpose="Income and delivery regularity verification",
            application_id=uuid.uuid4(),
        )
        self.assertEqual(consent_in.data_source, ConsentDataSource.PLATFORM)

        # Rejects invalid data source enum
        with self.assertRaises(ValidationError):
            ConsentCreate(
                data_source="CONTACT_LIST",  # Prohibited data source
                purpose="Testing",
            )

        now = datetime.now(timezone.utc)
        orm_consent = Consent(
            id=uuid.uuid4(),
            application_id=uuid.uuid4(),
            data_source=ConsentDataSource.FINANCIAL_ACTIVITY,
            purpose="Repayment consistency evaluation",
            granted=True,
            granted_at=now,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )
        resp = ConsentResponse.model_validate(orm_consent)
        self.assertTrue(resp.granted)
        self.assertIsNone(resp.revoked_at)

    def test_financial_signal_validation_and_privacy(self) -> None:
        """Verify FinancialSignal validation constraints and lack of sensitive raw fields."""
        # Privacy check: Ensure forbidden raw columns do NOT exist in schemas
        forbidden = ["contact", "gps", "location", "upi_transaction", "merchant", "statement"]
        for field in FinancialSignalCreate.model_fields:
            for bad_word in forbidden:
                self.assertNotIn(bad_word, field.lower())

        app_id = uuid.uuid4()
        valid_signal = FinancialSignalCreate(
            application_id=app_id,
            source=SignalSource.PLATFORM,
            average_income=Decimal("32000.00"),
            payment_regularity=Decimal("0.95"),
            platform_rating=Decimal("4.85"),
        )
        self.assertEqual(valid_signal.average_income, Decimal("32000.00"))

        # Reject negative average income
        with self.assertRaises(ValidationError):
            FinancialSignalCreate(
                application_id=app_id,
                source=SignalSource.PLATFORM,
                average_income=Decimal("-100.00"),
            )

        # Reject payment_regularity > 1.0
        with self.assertRaises(ValidationError):
            FinancialSignalCreate(
                application_id=app_id,
                source=SignalSource.PLATFORM,
                payment_regularity=Decimal("1.50"),
            )

        # Reject platform_rating > 5.0
        with self.assertRaises(ValidationError):
            FinancialSignalCreate(
                application_id=app_id,
                source=SignalSource.PLATFORM,
                platform_rating=Decimal("6.00"),
            )

    def test_credit_assessment_validation_and_orm(self) -> None:
        """Verify CreditAssessment range rules and ORM compatibility."""
        app_id = uuid.uuid4()
        model_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        valid_assessment = CreditAssessmentCreate(
            application_id=app_id,
            model_version_id=model_id,
            credit_score=720,
            risk_probability=Decimal("0.1250"),
            risk_level=RiskLevel.LOWER,
            confidence=Decimal("0.9000"),
            assessment_status="COMPLETED",
        )
        self.assertEqual(valid_assessment.credit_score, 720)

        # Risk probability must be bounded [0, 1]
        with self.assertRaises(ValidationError):
            CreditAssessmentCreate(
                application_id=app_id,
                model_version_id=model_id,
                risk_level=RiskLevel.LOWER,
                risk_probability=Decimal("1.05"),
            )
        with self.assertRaises(ValidationError):
            CreditAssessmentCreate(
                application_id=app_id,
                model_version_id=model_id,
                risk_level=RiskLevel.LOWER,
                risk_probability=Decimal("-0.01"),
            )

        # Confidence must be bounded [0, 1]
        with self.assertRaises(ValidationError):
            CreditAssessmentCreate(
                application_id=app_id,
                model_version_id=model_id,
                risk_level=RiskLevel.LOWER,
                confidence=Decimal("1.2"),
            )

        # Nullable score and probability for INSUFFICIENT evidence
        insufficient = CreditAssessmentCreate(
            application_id=app_id,
            model_version_id=model_id,
            credit_score=None,
            risk_probability=None,
            risk_level=RiskLevel.INSUFFICIENT,
            confidence=Decimal("0.2"),
        )
        self.assertIsNone(insufficient.credit_score)
        self.assertEqual(insufficient.risk_level, RiskLevel.INSUFFICIENT)

        orm_assessment = CreditAssessment(
            id=uuid.uuid4(),
            application_id=app_id,
            model_version_id=model_id,
            credit_score=680,
            risk_probability=Decimal("0.2400"),
            risk_level=RiskLevel.MODERATE,
            confidence=Decimal("0.8500"),
            assessment_status="COMPLETED",
            assessed_at=now,
            created_at=now,
        )
        resp = CreditAssessmentResponse.model_validate(orm_assessment)
        self.assertEqual(resp.credit_score, 680)
        self.assertEqual(resp.risk_level, RiskLevel.MODERATE)

    def test_audit_log_orm_alias_mapping(self) -> None:
        """Verify AuditLogResponse extracts audit_metadata via alias."""
        now = datetime.now(timezone.utc)
        orm_audit = AuditLog(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            application_id=uuid.uuid4(),
            action="APPLICATION_SUBMITTED",
            entity_type="Application",
            entity_id=str(uuid.uuid4()),
            audit_metadata={"ip": "127.0.0.1", "channel": "api"},
            created_at=now,
        )

        resp = AuditLogResponse.model_validate(orm_audit)
        self.assertEqual(resp.action, "APPLICATION_SUBMITTED")
        self.assertIsNotNone(resp.metadata)
        self.assertEqual(resp.metadata["channel"], "api")


if __name__ == "__main__":
    unittest.main()
