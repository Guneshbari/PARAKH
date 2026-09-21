"""Schemas package exposing all public request and response contracts."""
from app.schemas.applicant import (
    ApplicantProfileCreate,
    ApplicantProfileResponse,
    ApplicantProfileUpdate,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationSummary,
    ApplicationUpdate,
)
from app.schemas.assessment import (
    CreditAssessmentCreate,
    CreditAssessmentResponse,
)
from app.schemas.audit import AuditLogResponse
from app.schemas.common import DatabaseHealthResponse, StatusResponse
from app.schemas.consent import ConsentCreate, ConsentResponse
from app.schemas.financial_signal import (
    FinancialSignalCreate,
    FinancialSignalResponse,
)
from app.schemas.model_version import (
    ModelVersionCreate,
    ModelVersionResponse,
)
from app.schemas.review import (
    ReviewOutcomeCreate,
    ReviewOutcomeResponse,
)
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserSummary,
    UserUpdate,
)

__all__ = [
    # Common
    "StatusResponse",
    "DatabaseHealthResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserSummary",
    "UserResponse",
    # Applicant
    "ApplicantProfileCreate",
    "ApplicantProfileUpdate",
    "ApplicantProfileResponse",
    # Application
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationSummary",
    "ApplicationResponse",
    # Consent
    "ConsentCreate",
    "ConsentResponse",
    # Financial Signal
    "FinancialSignalCreate",
    "FinancialSignalResponse",
    # Model Version
    "ModelVersionCreate",
    "ModelVersionResponse",
    # Assessment
    "CreditAssessmentCreate",
    "CreditAssessmentResponse",
    # Review
    "ReviewOutcomeCreate",
    "ReviewOutcomeResponse",
    # Audit
    "AuditLogResponse",
]
