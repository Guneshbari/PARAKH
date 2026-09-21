"""Applicant gig worker profile API routes."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_applicant_service
from app.schemas.applicant import (
    ApplicantProfileCreate,
    ApplicantProfileResponse,
    ApplicantProfileUpdate,
)
from app.services.applicant import ApplicantService
from app.services.exceptions import EntityNotFoundError

router = APIRouter(prefix="/applicants", tags=["applicants"])


@router.post(
    "",
    response_model=ApplicantProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Applicant Profile",
    description="Register a new gig worker profile for an existing user account.",
)
def create_applicant_profile(
    profile_in: ApplicantProfileCreate,
    user_id: Optional[UUID] = Query(
        None,
        description="Optional query override for associated User ID if omitted in payload",
    ),
    applicant_service: ApplicantService = Depends(get_applicant_service),
) -> ApplicantProfileResponse:
    """Create a new gig worker profile."""
    profile = applicant_service.create_profile(profile_in, user_id=user_id)
    return ApplicantProfileResponse.model_validate(profile)


@router.get(
    "/{profile_id}",
    response_model=ApplicantProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Applicant Profile by ID",
    description="Retrieve gig worker profile by profile primary key UUID.",
)
def get_applicant_profile(
    profile_id: UUID,
    applicant_service: ApplicantService = Depends(get_applicant_service),
) -> ApplicantProfileResponse:
    """Retrieve applicant profile by ID."""
    profile = applicant_service.get_profile(profile_id)
    return ApplicantProfileResponse.model_validate(profile)


@router.get(
    "/user/{user_id}",
    response_model=ApplicantProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Applicant Profile by User ID",
    description="Retrieve the gig worker profile associated with a specific User ID.",
)
def get_applicant_profile_by_user(
    user_id: UUID,
    applicant_service: ApplicantService = Depends(get_applicant_service),
) -> ApplicantProfileResponse:
    """Retrieve applicant profile for a user."""
    profile = applicant_service.get_profile_by_user_id(user_id)
    if not profile:
        raise EntityNotFoundError(f"ApplicantProfile for user '{user_id}' not found.")
    return ApplicantProfileResponse.model_validate(profile)


@router.patch(
    "/{profile_id}",
    response_model=ApplicantProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Applicant Profile",
    description="Update gig work type, experience, working days, or loan purpose on a profile.",
)
def update_applicant_profile(
    profile_id: UUID,
    profile_update: ApplicantProfileUpdate,
    applicant_service: ApplicantService = Depends(get_applicant_service),
) -> ApplicantProfileResponse:
    """Update applicant profile details."""
    updated = applicant_service.update_profile(profile_id, profile_update)
    return ApplicantProfileResponse.model_validate(updated)
