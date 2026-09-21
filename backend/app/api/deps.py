from typing import Callable, Optional, Sequence
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.assessment.base import AssessmentEngine
from app.assessment.mock import MockAssessmentEngine
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.services.applicant import ApplicantService
from app.services.application import ApplicationService
from app.services.assessment import AssessmentService
from app.services.consent import ConsentService
from app.services.financial_signal import FinancialSignalService
from app.services.model_version import ModelVersionService
from app.services.review import ReviewService
from app.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)

# Re-export get_db and dependencies for unified access
__all__ = [
    "get_db",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "require_authenticated_user",
    "require_role",
    "require_any_role",
    "check_application_ownership",
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


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and validate the currently authenticated user from Bearer JWT."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserRepository(db=db).get_by_id(user_id_str, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify that the resolved user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


require_authenticated_user = get_current_active_user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory restricting route access to specified roles."""

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            role_names = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {role_names}",
            )
        return current_user

    return role_checker


def require_any_role(allowed_roles: Sequence[UserRole]) -> Callable[[User], User]:
    """Dependency factory restricting route access to any of the specified roles."""
    return require_role(*allowed_roles)


def check_application_ownership(
    db: Session,
    application_id: UUID,
    current_user: User,
    allow_reviewers: bool = False,
) -> None:
    """Verify that current_user has access to the specified application."""
    if current_user.role == UserRole.ADMIN:
        return
    if allow_reviewers and current_user.role == UserRole.REVIEWER:
        return
    if current_user.role == UserRole.APPLICANT:
        app_service = ApplicationService(db=db)
        app = app_service.get_application(application_id)
        applicant_service = ApplicantService(db=db)
        profile = applicant_service.get_profile(app.applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot access another applicant's data.",
            )
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Operation not permitted for current user role.",
    )

