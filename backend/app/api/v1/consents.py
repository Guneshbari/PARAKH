"""Applicant consent and privacy authorization API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_consent_service
from app.models.consent import ConsentDataSource
from app.schemas.consent import ConsentCreate, ConsentResponse
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
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentResponse:
    """Record explicit applicant consent."""
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
    consent_service: ConsentService = Depends(get_consent_service),
) -> List[ConsentResponse]:
    """List all consent records for an application."""
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
    consent_service: ConsentService = Depends(get_consent_service),
) -> List[ConsentResponse]:
    """List active consents for an application."""
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
    consent_service: ConsentService = Depends(get_consent_service),
) -> ConsentResponse:
    """Revoke a previously granted consent."""
    revoked = consent_service.revoke_consent(consent_id)
    return ConsentResponse.model_validate(revoked)
