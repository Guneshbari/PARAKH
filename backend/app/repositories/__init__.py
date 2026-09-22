"""Repositories package exposing all domain persistence repositories."""
from app.repositories.applicant import (
    ApplicantProfileRepository,
    ApplicantRepository,
)
from app.repositories.application import ApplicationRepository
from app.repositories.assessment import (
    AssessmentRepository,
    CreditAssessmentRepository,
)
from app.repositories.audit import AuditLogRepository, AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.consent import ConsentRepository
from app.repositories.financial_signal import FinancialSignalRepository
from app.repositories.model_version import ModelVersionRepository
from app.repositories.review import (
    ReviewOutcomeRepository,
    ReviewRepository,
)
from app.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ApplicantRepository",
    "ApplicantProfileRepository",
    "ApplicationRepository",
    "ConsentRepository",
    "FinancialSignalRepository",
    "AssessmentRepository",
    "CreditAssessmentRepository",
    "ModelVersionRepository",
    "ReviewRepository",
    "ReviewOutcomeRepository",
    "AuditRepository",
    "AuditLogRepository",
]
