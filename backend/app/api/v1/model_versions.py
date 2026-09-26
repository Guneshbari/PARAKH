"""Algorithmic model version registry API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import (
    get_current_active_user,
    get_model_version_service,
    require_role,
)
from app.models.user import User, UserRole
from app.schemas.model_version import (
    FairnessAuditRequest,
    FairnessAuditResponse,
    ModelVersionCreate,
    ModelVersionResponse,
)
from app.services.exceptions import EntityNotFoundError, ValidationError
from app.services.model_version import ModelVersionService

router = APIRouter(prefix="/model-versions", tags=["model-versions"])


@router.post(
    "",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Model Version",
    description="Register a new scoring model or algorithm version in the system registry. Requires ADMIN role.",
)
def create_model_version(
    model_version_in: ModelVersionCreate,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> ModelVersionResponse:
    """Register a new model version (Admin only)."""
    mv = mv_service.create_model_version(model_version_in)
    return ModelVersionResponse.model_validate(mv)


@router.get(
    "",
    response_model=List[ModelVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Model Versions",
    description="List all registered model versions, optionally filtered by model name.",
)
def list_model_versions(
    model_name: Optional[str] = Query(None, description="Optional model identifier filter"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    current_user: User = Depends(get_current_active_user),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> List[ModelVersionResponse]:
    """List registered model versions."""
    versions = mv_service.list_versions(model_name=model_name, skip=skip, limit=limit)
    return [ModelVersionResponse.model_validate(v) for v in versions]


@router.get(
    "/active/{model_name}",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Model Version",
    description="Fetch the currently active model version for a specific scoring algorithm.",
)
def get_active_model_version(
    model_name: str,
    current_user: User = Depends(get_current_active_user),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> ModelVersionResponse:
    """Retrieve active model version by name."""
    mv = mv_service.get_active_model(model_name=model_name)
    if not mv:
        raise EntityNotFoundError(f"Active ModelVersion for '{model_name}' not found.")
    return ModelVersionResponse.model_validate(mv)


@router.get(
    "/{model_version_id}",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Model Version by ID",
    description="Retrieve algorithmic model version metadata by primary key UUID.",
)
def get_model_version(
    model_version_id: UUID,
    current_user: User = Depends(get_current_active_user),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> ModelVersionResponse:
    """Retrieve model version by ID."""
    mv = mv_service.get_model_version(model_version_id)
    return ModelVersionResponse.model_validate(mv)


@router.post(
    "/{model_version_id}/activate",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate Model Version",
    description="Promote and activate a registered scoring model version. Deactivates other active versions in the same model family. Requires ADMIN role.",
)
def activate_model_version(
    model_version_id: UUID,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> ModelVersionResponse:
    """Activate a model version (Admin only)."""
    mv = mv_service.activate_model_version(model_version_id, actor=current_admin)
    return ModelVersionResponse.model_validate(mv)


@router.post(
    "/{model_version_id}/fairness-audit",
    response_model=FairnessAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Offline Fairness Audit",
    description="Execute an offline fairness audit (Demographic Parity Ratio and Equal Opportunity Difference) across operational subgroups. Requires ADMIN or REVIEWER role.",
)
@router.post(
    "/{model_version_id}/fairness",
    response_model=FairnessAuditResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def evaluate_model_version_fairness(
    model_version_id: UUID,
    audit_request: Optional[FairnessAuditRequest] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.REVIEWER)),
    mv_service: ModelVersionService = Depends(get_model_version_service),
) -> FairnessAuditResponse:
    """Execute offline fairness audit (Admin and Reviewer only)."""
    try:
        req = audit_request or FairnessAuditRequest()
        return mv_service.evaluate_fairness(
            model_version_id=model_version_id,
            audit_request=req,
            actor=current_user,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc.message if hasattr(exc, "message") else exc),
        )

