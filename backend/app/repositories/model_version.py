"""Model version repository for assessment algorithm provenance."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.model_version import ModelVersion
from app.repositories.base import BaseRepository, _parse_id


class ModelVersionRepository(BaseRepository[ModelVersion]):
    """Repository handling persistence operations for ModelVersion records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        """Initialize ModelVersionRepository with ModelVersion model."""
        super().__init__(ModelVersion, db)

    def create(
        self,
        obj_in: Union[ModelVersion, Dict[str, Any]],
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ModelVersion:
        """Create a new ModelVersion record.

        Args:
            obj_in: ModelVersion instance or dictionary.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            ModelVersion: Persisted model version record.
        """
        return super().create(obj_in, commit=commit, db=db)

    def get_by_id(
        self,
        id: Union[uuid.UUID, str],
        db: Optional[Session] = None,
    ) -> Optional[ModelVersion]:
        """Fetch a ModelVersion by primary key UUID.

        Args:
            id: Model version UUID.
            db: Optional session override.

        Returns:
            Optional[ModelVersion]: Matching record or None.
        """
        return super().get_by_id(id, db=db)

    def get_active(
        self,
        model_name: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[ModelVersion]:
        """Fetch the latest active model version.

        Args:
            model_name: Optional model identifier filter.
            db: Optional session override.

        Returns:
            Optional[ModelVersion]: Active model version or None.
        """
        session = self._get_db(db)
        stmt = select(ModelVersion).where(ModelVersion.is_active.is_(True))
        if model_name is not None:
            stmt = stmt.where(ModelVersion.model_name == model_name)
        stmt = stmt.order_by(ModelVersion.created_at.desc()).limit(1)
        return session.scalars(stmt).first()

    def list_versions(
        self,
        model_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None,
    ) -> List[ModelVersion]:
        """List model versions ordered by creation date descending.

        Args:
            model_name: Optional model identifier filter.
            skip: Pagination offset.
            limit: Maximum items to return.
            db: Optional session override.

        Returns:
            List[ModelVersion]: List of model versions.
        """
        session = self._get_db(db)
        stmt = select(ModelVersion)
        if model_name is not None:
            stmt = stmt.where(ModelVersion.model_name == model_name)
        stmt = stmt.order_by(ModelVersion.created_at.desc()).offset(skip).limit(limit)
        return list(session.scalars(stmt).all())

    def activate(
        self,
        model_version: ModelVersion,
        commit: bool = False,
        db: Optional[Session] = None,
    ) -> ModelVersion:
        """Promote and activate a model version, deactivating other versions of the same model family.

        Args:
            model_version: Target ModelVersion to activate.
            commit: Whether to commit immediately.
            db: Optional session override.

        Returns:
            ModelVersion: Activated model version.
        """
        session = self._get_db(db)
        # Deactivate all other active versions with the same model_name
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_name == model_version.model_name)
            .where(ModelVersion.is_active.is_(True))
            .where(ModelVersion.id != model_version.id)
        )
        for other_active in session.scalars(stmt).all():
            other_active.is_active = False
            session.add(other_active)

        model_version.is_active = True
        session.add(model_version)

        if commit:
            session.commit()
            session.refresh(model_version)
        else:
            session.flush()

        return model_version
