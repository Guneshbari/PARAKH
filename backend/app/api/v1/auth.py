"""Authentication endpoints for user login, token generation, and identity resolution."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_audit_service, get_current_active_user, get_user_service
from app.core.audit_events import AuditAction, AuditOutcome
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.audit import AuditService
from app.services.user import UserService

router = APIRouter(tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate with email and password to receive a signed JWT access token.",
)
def login(
    login_in: LoginRequest,
    user_service: UserService = Depends(get_user_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> TokenResponse:
    """Authenticate user credentials and issue a JWT access token."""
    user = user_service.authenticate_user(
        email=login_in.email,
        password=login_in.password,
    )
    if not user:
        try:
            audit_service.record_event(
                action=AuditAction.LOGIN_FAILURE,
                entity_type="Authentication",
                entity_id=None,
                user_id=None,
                outcome=AuditOutcome.FAILURE,
                metadata={"attempted_email": login_in.email.lower().strip() if login_in.email else None},
                commit=True,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        try:
            audit_service.record_event(
                action=AuditAction.ACCESS_DENIED,
                entity_type="Authentication",
                entity_id=str(user.id),
                user_id=user.id,
                actor_role=user.role,
                outcome=AuditOutcome.DENIED,
                metadata={"reason": "Inactive account login attempt"},
                commit=True,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact system administrator.",
        )

    try:
        audit_service.record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="Authentication",
            entity_id=str(user.id),
            user_id=user.id,
            actor_role=user.role,
            outcome=AuditOutcome.SUCCESS,
            metadata={"email": user.email},
            commit=True,
        )
    except Exception:
        pass

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_seconds,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current Authenticated User",
    description="Retrieve account profile and assigned role for the currently authenticated caller.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the profile of the current authenticated user."""
    return UserResponse.model_validate(current_user)
