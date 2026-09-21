"""User service for account lifecycle management and business workflows."""
import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class UserService:
    """Business service orchestrating User account operations."""

    def __init__(
        self,
        db: Session,
        user_repo: Optional[UserRepository] = None,
    ) -> None:
        """Initialize UserService with an active database session and repository."""
        self.db = db
        self.user_repo = user_repo or UserRepository(db=db)

    def create_user(
        self,
        user_in: Union[UserCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> User:
        """Create a new user account after normalizing email and checking uniqueness.

        Args:
            user_in: User creation data.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            User: Created user entity.

        Raises:
            ValidationError: If email is missing or empty.
            DuplicateEntityError: If a user with the normalized email already exists.
        """
        data = _extract_dict(user_in)
        raw_email = data.get("email")
        if not raw_email or not str(raw_email).strip():
            raise ValidationError("Email address is required.")

        normalized_email = str(raw_email).lower().strip()
        existing = self.user_repo.get_by_email(normalized_email, db=self.db)
        if existing:
            raise DuplicateEntityError(f"User with email '{normalized_email}' already exists.")

        data["email"] = normalized_email
        raw_password = data.pop("password", None)
        if raw_password:
            data["password_hash"] = hash_password(str(raw_password))

        try:
            user = self.user_repo.create(data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_user(
        self,
        user_id: Union[uuid.UUID, str],
    ) -> User:
        """Retrieve a user by ID.

        Args:
            user_id: Primary key UUID.

        Returns:
            User: Matching user entity.

        Raises:
            EntityNotFoundError: If user does not exist.
        """
        user = self.user_repo.get_by_id(user_id, db=self.db)
        if not user:
            raise EntityNotFoundError(f"User with id '{user_id}' not found.")
        return user

    def get_user_by_email(
        self,
        email: str,
    ) -> Optional[User]:
        """Look up a user by email address after case normalization.

        Args:
            email: Email address string.

        Returns:
            Optional[User]: Matching user or None.
        """
        normalized_email = email.lower().strip()
        return self.user_repo.get_by_email(normalized_email, db=self.db)

    def update_user(
        self,
        user_id: Union[uuid.UUID, str],
        user_update: Union[UserUpdate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> User:
        """Update an existing user account.

        Args:
            user_id: Primary key UUID.
            user_update: Fields to update.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            User: Updated user entity.

        Raises:
            EntityNotFoundError: If user does not exist.
            DuplicateEntityError: If new email is already taken.
        """
        user = self.get_user(user_id)
        data = _extract_dict(user_update)

        if "email" in data and data["email"] is not None:
            normalized_email = str(data["email"]).lower().strip()
            if normalized_email != user.email:
                existing = self.user_repo.get_by_email(normalized_email, db=self.db)
                if existing:
                    raise DuplicateEntityError(
                        f"User with email '{normalized_email}' already exists."
                    )
            data["email"] = normalized_email

        if "password" in data:
            raw_password = data.pop("password", None)
            if raw_password:
                data["password_hash"] = hash_password(str(raw_password))

        try:
            updated_user = self.user_repo.update(user, data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(updated_user)
            return updated_user
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate user credentials against stored bcrypt password hash.

        Args:
            email: Raw user email address.
            password: Provided plaintext password.

        Returns:
            Optional[User]: Matching authenticated User if valid, else None.
        """
        if not email or not password:
            return None
        normalized_email = str(email).lower().strip()
        user = self.user_repo.get_by_email(normalized_email, db=self.db)
        if not user or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
