"""Applicant profile service for gig worker registration and updates."""
import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy.orm import Session
from app.models.applicant import ApplicantProfile
from app.repositories.applicant import ApplicantRepository
from app.repositories.user import UserRepository
from app.schemas.applicant import ApplicantProfileCreate, ApplicantProfileUpdate
from app.services.exceptions import DuplicateEntityError, EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ApplicantService:
    """Business service orchestrating gig worker profile operations."""

    def __init__(
        self,
        db: Session,
        applicant_repo: Optional[ApplicantRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ) -> None:
        """Initialize ApplicantService with required repositories."""
        self.db = db
        self.applicant_repo = applicant_repo or ApplicantRepository(db=db)
        self.user_repo = user_repo or UserRepository(db=db)

    def create_profile(
        self,
        profile_in: Union[ApplicantProfileCreate, Dict[str, Any]],
        user_id: Optional[Union[uuid.UUID, str]] = None,
        auto_commit: bool = True,
    ) -> ApplicantProfile:
        """Create a new applicant profile for a verified user account.

        Args:
            profile_in: Profile data.
            user_id: Optional User account primary key UUID (if not in profile_in).
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ApplicantProfile: Created profile entity.

        Raises:
            ValidationError: If user_id is missing.
            EntityNotFoundError: If the associated User does not exist.
            DuplicateEntityError: If an ApplicantProfile already exists for this User.
        """
        data = _extract_dict(profile_in)
        resolved_user_id = user_id or data.get("user_id")
        if not resolved_user_id:
            raise ValidationError("user_id is required to create an applicant profile.")

        data["user_id"] = resolved_user_id

        # Ensure associated User exists
        user = self.user_repo.get_by_id(resolved_user_id, db=self.db)
        if not user:
            raise EntityNotFoundError(f"Associated User with id '{resolved_user_id}' does not exist.")

        # Ensure single profile per user
        existing = self.applicant_repo.get_by_user_id(resolved_user_id, db=self.db)
        if existing:
            raise DuplicateEntityError(
                f"ApplicantProfile for user '{resolved_user_id}' already exists."
            )

        try:
            profile = self.applicant_repo.create(data, commit=False, db=self.db)
            if auto_commit:
                self.db.commit()
                self.db.refresh(profile)
            return profile
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_profile(
        self,
        profile_id: Union[uuid.UUID, str],
    ) -> ApplicantProfile:
        """Retrieve an applicant profile by ID.

        Args:
            profile_id: Profile primary key UUID.

        Returns:
            ApplicantProfile: Matching profile entity.

        Raises:
            EntityNotFoundError: If profile does not exist.
        """
        profile = self.applicant_repo.get_by_id(profile_id, db=self.db)
        if not profile:
            raise EntityNotFoundError(f"ApplicantProfile with id '{profile_id}' not found.")
        return profile

    def get_profile_by_user_id(
        self,
        user_id: Union[uuid.UUID, str],
    ) -> Optional[ApplicantProfile]:
        """Look up an applicant profile associated with a user ID.

        Args:
            user_id: User account primary key UUID.

        Returns:
            Optional[ApplicantProfile]: Associated profile or None.
        """
        return self.applicant_repo.get_by_user_id(user_id, db=self.db)

    def update_profile(
        self,
        profile_id: Union[uuid.UUID, str],
        profile_update: Union[ApplicantProfileUpdate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> ApplicantProfile:
        """Update an existing applicant profile.

        Args:
            profile_id: Profile primary key UUID.
            profile_update: Fields to update.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ApplicantProfile: Updated profile entity.

        Raises:
            EntityNotFoundError: If profile does not exist.
        """
        profile = self.get_profile(profile_id)
        data = _extract_dict(profile_update)

        try:
            updated_profile = self.applicant_repo.update(
                profile, data, commit=False, db=self.db
            )
            if auto_commit:
                self.db.commit()
                self.db.refresh(updated_profile)
            return updated_profile
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise
