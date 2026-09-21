"""Human adjudication and credit officer review API routes."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_review_service
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
    description="Record a human credit officer review outcome (e.g. REVIEWED, ESCALATED) for an application.",
)
def create_review(
    application_id: UUID,
    review_in: ReviewOutcomeCreate,
    review_service: ReviewService = Depends(get_review_service),
) -> ReviewOutcomeResponse:
    """Record human officer review outcome."""
    data = review_in.model_dump()
    data["application_id"] = application_id
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
    review_service: ReviewService = Depends(get_review_service),
) -> List[ReviewOutcomeResponse]:
    """List review outcomes for an application."""
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
    review_service: ReviewService = Depends(get_review_service),
) -> List[ReviewOutcomeResponse]:
    """List reviews submitted by a reviewer."""
    reviews = review_service.get_reviewer_reviews(reviewer_id, skip=skip, limit=limit)
    return [ReviewOutcomeResponse.model_validate(r) for r in reviews]
