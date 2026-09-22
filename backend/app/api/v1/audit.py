"""Audit log retrieval endpoints restricted to platform administrators."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_audit_service, require_role
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogResponse
from app.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=List[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Audit Logs",
    description="Retrieve paginated audit log events with optional filters. Administrator access required.",
)
def list_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by affected or acting user ID"),
    application_id: Optional[UUID] = Query(None, description="Filter by associated application ID"),
    action: Optional[str] = Query(None, description="Filter by specific audit action"),
    entity_type: Optional[str] = Query(None, description="Filter by resource/entity type"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    audit_service: AuditService = Depends(get_audit_service),
) -> List[AuditLogResponse]:
    """Return filtered audit trail records for compliance and security auditing."""
    records = audit_service.list_events(
        user_id=user_id,
        application_id=application_id,
        action=action,
        entity_type=entity_type,
        skip=skip,
        limit=limit,
    )
    return [AuditLogResponse.model_validate(r) for r in records]


@router.get(
    "/{audit_id}",
    response_model=AuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Audit Log Entry",
    description="Retrieve a single audit log event by primary key ID. Administrator access required.",
)
def get_audit_log(
    audit_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditLogResponse:
    """Return a single audit trail record by its unique identifier."""
    record = audit_service.get_event(audit_id)
    return AuditLogResponse.model_validate(record)
