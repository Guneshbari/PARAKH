"""FastAPI route dependencies for database sessions, services, and engines."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.assessment.base import AssessmentEngine
from app.assessment.mock import MockAssessmentEngine
from app.core.database import get_db
from app.services.applicant import ApplicantService
from app.services.application import ApplicationService
from app.services.assessment import AssessmentService
from app.services.consent import ConsentService
from app.services.financial_signal import FinancialSignalService
from app.services.model_version import ModelVersionService
from app.services.review import ReviewService
from app.services.user import UserService

# Re-export get_db for unified dependency access
__all__ = [
    "get_db",
    "get_assessment_engine",
    "get_user_service",
    "get_applicant_service",
    "get_application_service",
    "get_consent_service",
    "get_financial_signal_service",
    "get_assessment_service",
    "get_model_version_service",
    "get_review_service",
]


def get_assessment_engine() -> AssessmentEngine:
    """Dependency returning the configured AssessmentEngine instance (MockAssessmentEngine)."""
    return MockAssessmentEngine()


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency providing a UserService instance bound to the request database session."""
    return UserService(db=db)


def get_applicant_service(db: Session = Depends(get_db)) -> ApplicantService:
    """Dependency providing an ApplicantService instance bound to the request database session."""
    return ApplicantService(db=db)


def get_application_service(db: Session = Depends(get_db)) -> ApplicationService:
    """Dependency providing an ApplicationService instance bound to the request database session."""
    return ApplicationService(db=db)


def get_consent_service(db: Session = Depends(get_db)) -> ConsentService:
    """Dependency providing a ConsentService instance bound to the request database session."""
    return ConsentService(db=db)


def get_financial_signal_service(
    db: Session = Depends(get_db),
    consent_service: ConsentService = Depends(get_consent_service),
) -> FinancialSignalService:
    """Dependency providing a FinancialSignalService instance with consent verification capability."""
    return FinancialSignalService(db=db, consent_service=consent_service)


def get_assessment_service(
    db: Session = Depends(get_db),
    engine: AssessmentEngine = Depends(get_assessment_engine),
) -> AssessmentService:
    """Dependency providing an AssessmentService instance with injected assessment engine."""
    return AssessmentService(db=db, engine=engine)


def get_model_version_service(
    db: Session = Depends(get_db),
) -> ModelVersionService:
    """Dependency providing a ModelVersionService instance bound to the request database session."""
    return ModelVersionService(db=db)


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    """Dependency providing a ReviewService instance bound to the request database session."""
    return ReviewService(db=db)
