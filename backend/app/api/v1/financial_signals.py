"""Financial signal ingestion and retrieval API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import (
    check_application_ownership,
    get_financial_signal_service,
    get_current_active_user,
)
from app.models.user import User
from app.schemas.financial_signal import (
    FinancialSignalCreate,
    FinancialSignalResponse,
)
from app.services.exceptions import EntityNotFoundError
from app.services.financial_signal import FinancialSignalService

router = APIRouter(tags=["financial-signals"])


@router.post(
    "/applications/{application_id}/financial-signals",
    response_model=FinancialSignalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Financial Signal",
    description="Record aggregated and derived financial indicators for an application. Enforces data-minimization rules.",
)
def create_financial_signal(
    application_id: UUID,
    signal_in: FinancialSignalCreate,
    enforce_consent: Optional[bool] = Query(
        None,
        description="Whether to verify active applicant consent for the signal source before saving",
    ),
    require_consent: Optional[bool] = Query(
        None,
        description="Alias for enforce_consent",
    ),
    current_user: User = Depends(get_current_active_user),
    signal_service: FinancialSignalService = Depends(get_financial_signal_service),
) -> FinancialSignalResponse:
    """Ingest aggregated financial indicators with ownership enforcement."""
    check_application_ownership(
        signal_service.db,
        application_id,
        current_user,
        allow_reviewers=False,
    )
    check_consent = bool(enforce_consent or require_consent)
    data = signal_in.model_dump()
    data["application_id"] = application_id
    signal = signal_service.create_signal(data, enforce_consent=check_consent)
    return FinancialSignalResponse.model_validate(signal)


@router.get(
    "/applications/{application_id}/financial-signals",
    response_model=List[FinancialSignalResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Financial Signals",
    description="Fetch all aggregated financial signals recorded for an application.",
)
def get_application_signals(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    signal_service: FinancialSignalService = Depends(get_financial_signal_service),
) -> List[FinancialSignalResponse]:
    """List financial signals for an application with role/ownership enforcement."""
    check_application_ownership(
        signal_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    signals = signal_service.get_application_signals(application_id)
    return [FinancialSignalResponse.model_validate(s) for s in signals]


@router.get(
    "/applications/{application_id}/financial-signals/latest",
    response_model=FinancialSignalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Financial Signal",
    description="Fetch the most recently recorded financial signal for an application.",
)
def get_latest_financial_signal(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    signal_service: FinancialSignalService = Depends(get_financial_signal_service),
) -> FinancialSignalResponse:
    """Retrieve the latest financial signal for an application with role/ownership enforcement."""
    check_application_ownership(
        signal_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    signal = signal_service.get_latest_signal(application_id)
    if not signal:
        raise EntityNotFoundError(
            f"No financial signals found for application '{application_id}'."
        )
    return FinancialSignalResponse.model_validate(signal)

