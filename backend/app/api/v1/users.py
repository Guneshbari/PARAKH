"""User account management API routes."""
from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.api.deps import get_user_service
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.exceptions import EntityNotFoundError
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Register a new platform user account with email and optional role.",
)
def create_user(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Create a new user account."""
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
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Retrieve user account by ID."""
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
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Look up a user account by email address."""
    user = user_service.get_user_by_email(email)
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
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Update user account details."""
    updated = user_service.update_user(user_id, user_update)
    return UserResponse.model_validate(updated)
