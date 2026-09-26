"""Applicant consent and privacy authorization API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import (
    check_application_ownership,
    get_application_service,
    get_consent_service,
    get_current_active_user,
)
from app.models.consent import ConsentDataSource
from app.models.user import User, UserRole
from app.schemas.consent import (
    ConsentCreate,
    ConsentPreferencesResponse,
    ConsentPreferencesUpdate,
    ConsentResponse,
)
from app.services.applicant import ApplicantService
from app.services.application import ApplicationService
from app.services.consent import ConsentService

router = APIRouter(tags=["consents"])


@router.post(
    "/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Consent",
    description="Explicitly record applicant consent for a specific data source and application.",
)
def create_consent(
    consent_in: ConsentCreate,
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentResponse:
    """Record explicit applicant consent with ownership enforcement."""
    check_application_ownership(
        consent_service.db,
        consent_in.application_id,
        current_user,
        allow_reviewers=False,
    )
    consent = consent_service.create_consent(consent_in)
    return ConsentResponse.model_validate(consent)


@router.get(
    "/applications/{application_id}/consents",
    response_model=List[ConsentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Consents",
    description="Fetch all consent records (both active and revoked) for an application.",
)
def get_application_consents(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> List[ConsentResponse]:
    """List all consent records for an application with role/ownership enforcement."""
    check_application_ownership(
        consent_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    consents = consent_service.get_application_consents(application_id)
    return [ConsentResponse.model_validate(c) for c in consents]


@router.get(
    "/applications/{application_id}/consents/active",
    response_model=List[ConsentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Active Application Consents",
    description="Fetch currently active (granted=True, revoked_at IS NULL) consents for an application.",
)
def get_active_application_consents(
    application_id: UUID,
    data_source: Optional[ConsentDataSource] = Query(
        None,
        description="Optional filter by data category (PLATFORM, FINANCIAL_ACTIVITY, UTILITY)",
    ),
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> List[ConsentResponse]:
    """List active consents for an application with role/ownership enforcement."""
    check_application_ownership(
        consent_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    consents = consent_service.get_active_consents(
        application_id=application_id, data_source=data_source
    )
    return [ConsentResponse.model_validate(c) for c in consents]


@router.post(
    "/consents/{consent_id}/revoke",
    response_model=ConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Consent",
    description="Revoke an existing consent record by stamping revoked_at without deleting historical data.",
)
def revoke_consent(
    consent_id: UUID,
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentResponse:
    """Revoke a previously granted consent with ownership enforcement."""
    # Find consent to verify ownership before revoking
    consent_repo = consent_service.consent_repo
    consent = consent_repo.get_by_id(consent_id)
    if not consent:
        from app.services.exceptions import EntityNotFoundError
        raise EntityNotFoundError(f"Consent '{consent_id}' not found.")

    check_application_ownership(
        consent_service.db,
        consent.application_id,
        current_user,
        allow_reviewers=False,
    )
    revoked = consent_service.revoke_consent(consent_id)
    return ConsentResponse.model_validate(revoked)


# =============================================================================
# DPDP Consent Preferences Endpoints (P2-04)
# =============================================================================


@router.get(
    "/consents/preferences",
    response_model=ConsentPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get DPDP Consent Preferences",
    description="Retrieve persistent DPDP consent preferences for the authenticated applicant.",
)
def get_consent_preferences(
    user_id: Optional[UUID] = Query(
        None,
        description="Optional User ID override (Admin/Reviewer only)",
    ),
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentPreferencesResponse:
    """Fetch consent preferences with strict ownership enforcement."""
    target_user_id = user_id or current_user.id
    if current_user.role == UserRole.APPLICANT and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot view another applicant's preferences.",
        )
    return consent_service.get_consent_preferences(target_user_id)


@router.patch(
    "/consents/preferences",
    response_model=ConsentPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update DPDP Consent Preferences",
    description="Persist updated DPDP consent preferences for the authenticated applicant.",
)
@router.put(
    "/consents/preferences",
    response_model=ConsentPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace DPDP Consent Preferences",
    description="Persist updated DPDP consent preferences for the authenticated applicant.",
)
def update_consent_preferences(
    preferences_in: ConsentPreferencesUpdate,
    user_id: Optional[UUID] = Query(
        None,
        description="Optional User ID override (Admin only)",
    ),
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentPreferencesResponse:
    """Update consent preferences with ownership enforcement."""
    target_user_id = user_id or current_user.id
    if current_user.role == UserRole.APPLICANT and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot modify another applicant's preferences.",
        )
    if current_user.role == UserRole.REVIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: reviewers cannot modify applicant consent preferences.",
        )
    return consent_service.update_consent_preferences(target_user_id, preferences_in)


@router.post(
    "/consents/preferences/{preference_key}/revoke",
    response_model=ConsentPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke DPDP Consent Preference",
    description="Explicitly revoke a single DPDP consent preference.",
)
def revoke_consent_preference(
    preference_key: str,
    user_id: Optional[UUID] = Query(
        None,
        description="Optional User ID override (Admin only)",
    ),
    current_user: User = Depends(get_current_active_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentPreferencesResponse:
    """Revoke a specific consent preference with ownership enforcement."""
    target_user_id = user_id or current_user.id
    if current_user.role == UserRole.APPLICANT and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot modify another applicant's preferences.",
        )
    if current_user.role == UserRole.REVIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: reviewers cannot modify applicant consent preferences.",
        )
    return consent_service.revoke_consent_preference(target_user_id, preference_key)


