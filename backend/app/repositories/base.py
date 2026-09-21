"""Base repository providing generic persistence and retrieval operations."""
import uuid
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


def _parse_id(val: Union[uuid.UUID, str, int]) -> Union[uuid.UUID, str, int]:
    """Parse and normalize entity ID to UUID if valid string."""
    if isinstance(val, uuid.UUID):
        return val
    if isinstance(val, str):
        try:
            return uuid.UUID(val)
        except ValueError:
            return val
    return val


class BaseRepository(Generic[ModelType]):
    """Generic repository providing basic persistence operations.

    Follows SQLAlchemy 2.0 select and session semantics.
    Supports either session-scoped repository instances (via constructor)
    or per-call session passing.
    """

    def __init__(self, model: Type[ModelType], db: Optional[Session] = None) -> None:
        """Initialize repository for a specific SQLAlchemy model.

        Args:
            model: SQLAlchemy DeclarativeBase model class.
            db: Optional default SQLAlchemy Session for this repository instance.
        """
        self.model = model
        self.db = db

    def _get_db(self, db: Optional[Session] = None) -> Session:
        """Resolve active database session, prioritizing explicit argument over instance session."""
        session = db or self.db
        if session is None:
            raise ValueError(
                "A database session must be provided either at repository instantiation "
                "or directly to the repository method."
            )
        return session

    def get_by_id(
        self,
        id: Union[uuid.UUID, str, int],
        db: Optional[Session] = None,
    ) -> Optional[ModelType]:
        """Fetch a single record by primary key.

        Args:
            id: Primary key (UUID, string representation of UUID, or int).
            db: Optional session override.

        Returns:
            Optional[ModelType]: Found model instance or None.
        """
        session = self._get_db(db)
        parsed_id = _parse_id(id)
        return session.get(self.model, parsed_id)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[ModelType]:
        """Fetch multiple records with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            db: Optional session override.

        Returns:
            List[ModelType]: List of model instances.
        """
        session = self._get_db(db)
        stmt = select(self.model).offset(skip).limit(limit)
        return list(session.scalars(stmt).all())

    def create(
        self,
        obj_in: Union[ModelType, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ModelType:
        """Persist a new model record.

        Args:
            obj_in: Model instance or dictionary of attributes.
            commit: Whether to commit the transaction immediately (defaults to False for unit of work).
            db: Optional session override.

        Returns:
            ModelType: Persisted model instance with flushed primary key and defaults.
        """
        session = self._get_db(db)
        if isinstance(obj_in, self.model):
            db_obj = obj_in
        elif isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            raise TypeError(
                f"Expected instance of {self.model.__name__} or dict, got {type(obj_in).__name__}"
            )

        session.add(db_obj)
        if commit:
            session.commit()
            session.refresh(db_obj)
        else:
            session.flush()
        return db_obj

    def update(
        self,
        db_obj: ModelType,
        obj_in: Union[Dict[str, Any], Any],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ModelType:
        """Update fields on an existing model record.

        Args:
            db_obj: Existing SQLAlchemy model instance to update.
            obj_in: Dictionary or object containing updated attributes.
            commit: Whether to commit the transaction immediately (defaults to False).
            db: Optional session override.

        Returns:
            ModelType: Updated model instance.
        """
        session = self._get_db(db)
        if isinstance(obj_in, dict):
            update_data = obj_in
        elif hasattr(obj_in, "model_dump"):
            update_data = obj_in.model_dump(exclude_unset=True)
        elif hasattr(obj_in, "dict"):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = {
                k: v for k, v in vars(obj_in).items() if not k.startswith("_")
            }

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        session.add(db_obj)
        if commit:
            session.commit()
            session.refresh(db_obj)
        else:
            session.flush()
        return db_obj

    def delete(
        self,
        id: Union[uuid.UUID, str, int],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> Optional[ModelType]:
        """Delete a record by primary key.

        Args:
            id: Primary key of record to delete.
            commit: Whether to commit the transaction immediately (defaults to False).
            db: Optional session override.

        Returns:
            Optional[ModelType]: Deleted instance if found and removed, else None.
        """
        session = self._get_db(db)
        db_obj = self.get_by_id(id, db=session)
        if db_obj is not None:
            session.delete(db_obj)
            if commit:
                session.commit()
            else:
                session.flush()
        return db_obj
