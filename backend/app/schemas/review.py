"""Pydantic schemas for ReviewOutcome entity."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.review import ReviewOutcomeType


class ReviewOutcomeBase(BaseModel):
    """Base fields for human evaluation records."""

    outcome: ReviewOutcomeType = Field(..., description="Decision outcome of human review")
    notes: Optional[str] = Field(None, description="Reviewer comments and justification")


class ReviewOutcomeCreate(ReviewOutcomeBase):
    """Schema for submitting a human review outcome."""

    application_id: UUID
    reviewer_id: UUID


class ReviewOutcomeResponse(ReviewOutcomeBase):
    """Response schema representing a completed human review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    reviewer_id: UUID
    created_at: datetime
    updated_at: datetime
