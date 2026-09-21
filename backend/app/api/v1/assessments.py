"""Credit assessment workflow API routes."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import (
    check_application_ownership,
    get_assessment_service,
    get_current_active_user,
)
from app.models.user import User
from app.schemas.assessment import CreditAssessmentResponse
from app.services.assessment import AssessmentService
from app.services.exceptions import EntityNotFoundError

router = APIRouter(tags=["assessments"])


@router.post(
    "/applications/{application_id}/assess",
    response_model=CreditAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Credit Assessment",
    description=(
        "Trigger credit assessment evaluation on an application using the configured assessment engine. "
        "Extracts normalized features, executes the engine, persists the evaluation output, and returns the result."
    ),
)
def assess_application(
    application_id: UUID,
    model_version_id: Optional[UUID] = Query(
        None,
        description="Optional model version ID override. If omitted, uses active model version.",
    ),
    current_user: User = Depends(get_current_active_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResponse:
    """Execute credit assessment evaluation with role/ownership enforcement."""
    check_application_ownership(
        assessment_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    assessment = assessment_service.assess_application(
        application_id=application_id,
        model_version_id=model_version_id,
    )
    return CreditAssessmentResponse.model_validate(assessment)


@router.get(
    "/assessments/{assessment_id}",
    response_model=CreditAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Assessment by ID",
    description="Retrieve a historical credit assessment decision output by ID.",
)
def get_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResponse:
    """Retrieve credit assessment by ID with ownership enforcement."""
    assessment = assessment_service.get_assessment(assessment_id)
    check_application_ownership(
        assessment_service.db,
        assessment.application_id,
        current_user,
        allow_reviewers=True,
    )
    return CreditAssessmentResponse.model_validate(assessment)


@router.get(
    "/applications/{application_id}/assessments",
    response_model=List[CreditAssessmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Assessments",
    description="Fetch all credit assessments conducted on an application in reverse chronological order.",
)
def get_application_assessments(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> List[CreditAssessmentResponse]:
    """List all assessments for an application with role/ownership enforcement."""
    check_application_ownership(
        assessment_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    assessments = assessment_service.get_application_assessments(application_id)
    return [CreditAssessmentResponse.model_validate(a) for a in assessments]


@router.get(
    "/applications/{application_id}/assessments/latest",
    response_model=CreditAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Application Assessment",
    description="Fetch the most recent credit assessment generated for an application.",
)
def get_latest_assessment(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    assessment_service: AssessmentService = Depends(get_assessment_service),
) -> CreditAssessmentResponse:
    """Retrieve the latest assessment for an application with role/ownership enforcement."""
    check_application_ownership(
        assessment_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    assessment = assessment_service.get_latest_assessment(application_id)
    if not assessment:
        raise EntityNotFoundError(
            f"No credit assessments found for application '{application_id}'."
        )
    return CreditAssessmentResponse.model_validate(assessment)

