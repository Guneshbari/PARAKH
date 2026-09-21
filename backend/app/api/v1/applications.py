"""Alternative credit assessment application API routes."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_application_service
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.services.application import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application",
    description="Submit a new credit assessment application for an applicant profile.",
)
def create_application(
    application_in: ApplicationCreate,
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Create a new credit application."""
    app = application_service.create_application(application_in)
    return ApplicationResponse.model_validate(app)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application by ID",
    description="Retrieve details and current status of an application by ID.",
)
def get_application(
    application_id: UUID,
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Retrieve application by ID."""
    app = application_service.get_application(application_id)
    return ApplicationResponse.model_validate(app)


@router.get(
    "/applicant/{applicant_profile_id}",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Applications by Applicant Profile",
    description="Fetch all credit applications submitted by a specific gig worker profile.",
)
def list_applicant_applications(
    applicant_profile_id: UUID,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    application_service: ApplicationService = Depends(get_application_service),
) -> List[ApplicationResponse]:
    """List applications for an applicant profile."""
    apps = application_service.list_applications(
        applicant_profile_id=applicant_profile_id, skip=skip, limit=limit
    )
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application",
    description="Update requested loan amount, purpose, repayment period, or status on an application.",
)
def update_application(
    application_id: UUID,
    app_update: ApplicationUpdate,
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Update application details."""
    updated = application_service.update_application(application_id, app_update)
    return ApplicationResponse.model_validate(updated)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Application Status",
    description="Advance an application's lifecycle status according to the valid transition state machine.",
)
def update_application_status(
    application_id: UUID,
    status_in: ApplicationStatusUpdate,
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Transition application lifecycle status."""
    updated = application_service.update_status(application_id, status_in.status)
    return ApplicationResponse.model_validate(updated)
