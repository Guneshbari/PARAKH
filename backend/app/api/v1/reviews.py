"""Human adjudication and credit officer review API routes."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import (
    check_application_ownership,
    get_current_active_user,
    get_review_service,
    require_role,
)
from app.models.user import User, UserRole
from app.schemas.review import (
    ReviewOutcomeCreate,
    ReviewOutcomeResponse,
)
from app.services.review import ReviewService

router = APIRouter(tags=["reviews"])


@router.post(
    "/applications/{application_id}/reviews",
    response_model=ReviewOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Review Outcome",
    description="Record a human credit officer review outcome (e.g. REVIEWED, ESCALATED) for an application. Requires REVIEWER or ADMIN role.",
)
def create_review(
    application_id: UUID,
    review_in: ReviewOutcomeCreate,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewOutcomeResponse:
    """Record human officer review outcome with reviewer authorization."""
    if current_user.role == UserRole.REVIEWER and review_in.reviewer_id and review_in.reviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewers can only submit reviews under their own reviewer ID.",
        )
    data = review_in.model_dump()
    data["application_id"] = application_id
    if current_user.role == UserRole.REVIEWER or not data.get("reviewer_id"):
        data["reviewer_id"] = current_user.id
    review = review_service.create_review(data)
    return ReviewOutcomeResponse.model_validate(review)


@router.get(
    "/applications/{application_id}/reviews",
    response_model=List[ReviewOutcomeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Reviews",
    description="Fetch all human review outcomes conducted on an application.",
)
def get_application_reviews(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    review_service: ReviewService = Depends(get_review_service),
) -> List[ReviewOutcomeResponse]:
    """List review outcomes for an application with role/ownership enforcement."""
    check_application_ownership(
        review_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    reviews = review_service.get_application_reviews(application_id)
    return [ReviewOutcomeResponse.model_validate(r) for r in reviews]


@router.get(
    "/reviewers/{reviewer_id}/reviews",
    response_model=List[ReviewOutcomeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Reviewer Reviews",
    description="Fetch all reviews submitted by a specific reviewer User ID.",
)
def get_reviewer_reviews(
    reviewer_id: UUID,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    current_user: User = Depends(get_current_active_user),
    review_service: ReviewService = Depends(get_review_service),
) -> List[ReviewOutcomeResponse]:
    """List reviews submitted by a reviewer with role enforcement."""
    if current_user.role == UserRole.APPLICANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: applicants cannot inspect reviewer activity.",
        )
    if current_user.role == UserRole.REVIEWER and current_user.id != reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: reviewers can only access their own review history.",
        )
    reviews = review_service.get_reviewer_reviews(reviewer_id, skip=skip, limit=limit)
    return [ReviewOutcomeResponse.model_validate(r) for r in reviews]

