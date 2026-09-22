"""Models package exposing all SQLAlchemy domain entities and enums."""
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.audit import AuditLog
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.consent import Consent, ConsentDataSource
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.review import ReviewOutcome, ReviewOutcomeType
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserRole",
    "ApplicantProfile",
    "Application",
    "ApplicationStatus",
    "Consent",
    "ConsentDataSource",
    "FinancialSignal",
    "SignalSource",
    "ModelVersion",
    "CreditAssessment",
    "RiskLevel",
    "ReviewOutcome",
    "ReviewOutcomeType",
    "AuditLog",
]
