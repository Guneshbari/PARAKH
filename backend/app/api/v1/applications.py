"""Alternative credit assessment application API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import get_application_service, get_current_active_user
from app.models.application import ApplicationStatus
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationUpdate,
)
from app.services.applicant import ApplicantService
from app.services.application import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get(
    "",
    response_model=List[ApplicationResponse],
    status_code=status.HTTP_200_OK,
    summary="List All Applications",
    description="Fetch all credit applications with optional status filter. Requires REVIEWER or ADMIN role.",
)
def list_all_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter applications by status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> List[ApplicationResponse]:
    """List applications with role authorization for reviewers and administrators."""
    if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only reviewers and administrators can list all applications.",
        )
    apps = application_service.list_all_applications(status=status_filter, skip=skip, limit=limit)
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Application",
    description="Submit a new credit assessment application for an applicant profile.",
)
def create_application(
    application_in: ApplicationCreate,
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Create a new credit application with profile ownership enforcement."""
    if current_user.role == UserRole.APPLICANT:
        applicant_service = ApplicantService(db=application_service.db)
        profile = applicant_service.get_profile(application_in.applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot submit an application for another applicant profile.",
            )

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
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Retrieve application by ID with ownership enforcement."""
    app = application_service.get_application(application_id)
    if current_user.role == UserRole.APPLICANT:
        applicant_service = ApplicantService(db=application_service.db)
        profile = applicant_service.get_profile(app.applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot view another applicant's application.",
            )
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
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> List[ApplicationResponse]:
    """List applications for an applicant profile with ownership enforcement."""
    if current_user.role == UserRole.APPLICANT:
        applicant_service = ApplicantService(db=application_service.db)
        profile = applicant_service.get_profile(applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot view another applicant's applications.",
            )

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
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Update application details with ownership enforcement."""
    app = application_service.get_application(application_id)
    if current_user.role != UserRole.ADMIN:
        applicant_service = ApplicantService(db=application_service.db)
        profile = applicant_service.get_profile(app.applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot modify another applicant's application.",
            )
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
    current_user: User = Depends(get_current_active_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    """Transition application lifecycle status with role authorization."""
    app = application_service.get_application(application_id)
    if current_user.role in (UserRole.REVIEWER, UserRole.ADMIN):
        pass  # Reviewers and admins can perform transitions
    elif current_user.role == UserRole.APPLICANT:
        applicant_service = ApplicantService(db=application_service.db)
        profile = applicant_service.get_profile(app.applicant_profile_id)
        if profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot transition another applicant's application.",
            )
        if app.status != ApplicationStatus.DRAFT or status_in.status != ApplicationStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Applicants may only submit draft applications.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for current user role.",
        )

    updated = application_service.update_status(application_id, status_in.status)
    return ApplicationResponse.model_validate(updated)
