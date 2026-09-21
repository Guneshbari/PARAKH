"""Model version service for algorithm provenance and active scoring models."""
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.models.model_version import ModelVersion
from app.repositories.model_version import ModelVersionRepository
from app.schemas.model_version import ModelVersionCreate
from app.services.audit import AuditService
from app.services.exceptions import EntityNotFoundError, ValidationError


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class ModelVersionService:
    """Business service managing algorithmic model registry and versions."""

    def __init__(
        self,
        db: Session,
        model_version_repo: Optional[ModelVersionRepository] = None,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        """Initialize ModelVersionService with ModelVersionRepository and audit service."""
        self.db = db
        self.model_version_repo = model_version_repo or ModelVersionRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)

    def create_model_version(
        self,
        model_version_in: Union[ModelVersionCreate, Dict[str, Any]],
        auto_commit: bool = True,
    ) -> ModelVersion:
        """Register a new algorithmic model version in the registry.

        Args:
            model_version_in: Model metadata.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            ModelVersion: Registered model version entity.

        Raises:
            ValidationError: If model_name or version is missing.
        """
        data = _extract_dict(model_version_in)
        if not data.get("model_name"):
            raise ValidationError("model_name is required.")
        if not data.get("version"):
            raise ValidationError("version string is required.")

        try:
            mv = self.model_version_repo.create(data, commit=False, db=self.db)
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.MODEL_VERSION_CREATED,
                        entity_type="ModelVersion",
                        entity_id=getattr(mv, "id", None),
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "model_name": getattr(mv, "model_name", None),
                            "version": getattr(mv, "version", None),
                            "is_active": getattr(mv, "is_active", None),
                        },
                        commit=False,
                    )
                except Exception:
                    pass
            if auto_commit:
                self.db.commit()
                self.db.refresh(mv)
            return mv
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_model_version(
        self,
        model_version_id: Union[uuid.UUID, str],
    ) -> ModelVersion:
        """Retrieve a model version by ID.

        Args:
            model_version_id: Primary key UUID.

        Returns:
            ModelVersion: Matching entity.

        Raises:
            EntityNotFoundError: If model version is not found.
        """
        mv = self.model_version_repo.get_by_id(model_version_id, db=self.db)
        if not mv:
            raise EntityNotFoundError(
                f"ModelVersion with id '{model_version_id}' not found."
            )
        return mv

    def get_active_model(
        self,
        model_name: Optional[str] = None,
    ) -> Optional[ModelVersion]:
        """Fetch the currently active model version for scoring.

        Args:
            model_name: Optional model identifier filter.

        Returns:
            Optional[ModelVersion]: Active model version or None.
        """
        return self.model_version_repo.get_active(model_name=model_name, db=self.db)

    def list_versions(
        self,
        model_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelVersion]:
        """List registered model versions with optional name filter.

        Args:
            model_name: Optional filter by model identifier.
            skip: Pagination offset.
            limit: Maximum items to return.

        Returns:
            List[ModelVersion]: List of model versions.
        """
        return self.model_version_repo.list_versions(
            model_name=model_name, skip=skip, limit=limit, db=self.db
        )
