"""User account management API routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_active_user, get_user_service, oauth2_scheme
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.exceptions import EntityNotFoundError
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Register a new platform user account. Reviewer/Admin roles require existing administrator privileges.",
)
def create_user(
    user_in: UserCreate,
    token: Optional[str] = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new user account."""
    # Self-registration only permits APPLICANT role unless performed by an authenticated ADMIN
    if user_in.role in (UserRole.REVIEWER, UserRole.ADMIN):
        is_admin = False
        if token:
            try:
                payload = decode_access_token(token)
                if payload.get("role") == UserRole.ADMIN.value:
                    is_admin = True
            except Exception:
                pass
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create Reviewer or Admin accounts.",
            )

    user = user_service.create_user(user_in)
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User by ID",
    description="Retrieve account details for a specific user ID.",
)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Retrieve user account by ID with ownership enforcement."""
    if current_user.role == UserRole.APPLICANT and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot view another user's account details.",
        )
    user = user_service.get_user(user_id)
    return UserResponse.model_validate(user)


@router.get(
    "/by-email/{email}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User by Email",
    description="Look up a user account by normalized email address.",
)
def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Look up a user account by email address with ownership enforcement."""
    normalized_email = email.lower().strip()
    if current_user.role == UserRole.APPLICANT and current_user.email != normalized_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot view another user's account details.",
        )
    user = user_service.get_user_by_email(normalized_email)
    if not user:
        raise EntityNotFoundError(f"User with email '{email}' not found.")
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User",
    description="Update user account profile information or role.",
)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Update user account details with ownership enforcement."""
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot modify another user's account.",
        )
    # Non-admins cannot alter account role
    if current_user.role != UserRole.ADMIN and user_update.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only administrators can change user roles.",
        )

    updated = user_service.update_user(user_id, user_update)
    return UserResponse.model_validate(updated)
