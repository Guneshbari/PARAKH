"""User repository for persistence and retrieval of PARAKH user accounts."""
import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository, _parse_id


class UserRepository(BaseRepository[User]):
    """Repository handling persistence operations for User accounts."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize UserRepository with User model."""
        super().__init__(User, db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[User]:
        """Fetch a User by primary key UUID.

        Args:
            id: UUID or string UUID.
            db: Optional session override.

        Returns:
            Optional[User]: Matching user or None.
        """
        return super().get_by_id(id, db=db)

    def get_by_email(
        self,
        email: str,
        db: Optional[Session] = None,
    ) -> Optional[User]:
        """Fetch a User by email address (case-insensitive).

        Args:
            email: Email address.
            db: Optional session override.

        Returns:
            Optional[User]: Matching user or None.
        """
        session = self._get_db(db)
        stmt = select(User).where(func.lower(User.email) == email.lower().strip())
        return session.scalars(stmt).first()

    def create(
        self,
        obj_in: Union[User, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> User:
        """Create a new User record.

        Args:
            obj_in: User instance or dictionary of user attributes.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            User: Persisted User instance.
        """
        return super().create(obj_in, commit=commit, db=db)

    def update(
        self,
        db_obj: User,
        obj_in: Union[Dict[str, Any], Any],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> User:
        """Update an existing User record.

        Args:
            db_obj: Existing User instance.
            obj_in: Dictionary or model of updated fields.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            User: Updated User instance.
        """
        return super().update(db_obj, obj_in, commit=commit, db=db)
