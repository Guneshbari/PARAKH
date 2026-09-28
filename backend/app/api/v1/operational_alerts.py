"""Operational alert API routes for system incidents and governance monitoring."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import (
    get_operational_alert_service,
    require_role,
)
from app.models.operational_alert import OperationalAlertStatus
from app.models.user import User, UserRole
from app.schemas.operational_alert import OperationalAlertResponse
from app.services.operational_alert import OperationalAlertService

router = APIRouter(tags=["operational-alerts"])


@router.get(
    "/operational-alerts",
    response_model=List[OperationalAlertResponse],
    status_code=status.HTTP_200_OK,
    summary="List Operational Alerts",
    description="List persistent operational alerts, system incidents, and sufficiency review flags.",
)
def list_operational_alerts(
    status: Optional[OperationalAlertStatus] = Query(
        None,
        description="Filter by alert status (OPEN, ACKNOWLEDGED, RESOLVED)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    skip: int = Query(0, ge=0, description="Offset"),
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    alert_service: OperationalAlertService = Depends(get_operational_alert_service),
) -> List[OperationalAlertResponse]:
    """Retrieve operational alerts filtered by status."""
    alerts = alert_service.list_alerts(status=status, limit=limit, skip=skip)
    return [OperationalAlertResponse.model_validate(a) for a in alerts]


@router.get(
    "/operational-alerts/{alert_id}",
    response_model=OperationalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Operational Alert by ID",
    description="Retrieve a single operational alert by primary key UUID.",
)
def get_operational_alert(
    alert_id: UUID,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    alert_service: OperationalAlertService = Depends(get_operational_alert_service),
) -> OperationalAlertResponse:
    """Retrieve single operational alert."""
    alert = alert_service.get_alert(alert_id)
    return OperationalAlertResponse.model_validate(alert)


@router.patch(
    "/operational-alerts/{alert_id}/acknowledge",
    response_model=OperationalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge Operational Alert",
    description="Transition an open operational alert to ACKNOWLEDGED state.",
)
def acknowledge_operational_alert(
    alert_id: UUID,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    alert_service: OperationalAlertService = Depends(get_operational_alert_service),
) -> OperationalAlertResponse:
    """Acknowledge operational alert."""
    alert = alert_service.acknowledge_alert(alert_id)
    return OperationalAlertResponse.model_validate(alert)


@router.patch(
    "/operational-alerts/{alert_id}/resolve",
    response_model=OperationalAlertResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Operational Alert",
    description="Transition an operational alert to RESOLVED state.",
)
def resolve_operational_alert(
    alert_id: UUID,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    alert_service: OperationalAlertService = Depends(get_operational_alert_service),
) -> OperationalAlertResponse:
    """Resolve operational alert."""
    alert = alert_service.resolve_alert(alert_id)
    return OperationalAlertResponse.model_validate(alert)
