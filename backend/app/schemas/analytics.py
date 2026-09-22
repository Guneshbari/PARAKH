"""Pydantic schemas for portfolio analytics aggregation endpoints."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ScoreBucket(BaseModel):
    """Histogram bucket for credit score distribution."""

    range: str = Field(..., description="Score range label, e.g. '740–799'")
    label: str = Field(..., description="Human-readable tier label")
    count: int = Field(..., ge=0, description="Number of assessments in this bucket")
    percentage: float = Field(..., ge=0, le=100, description="Percentage of total assessments")
    risk_tier: str = Field(..., description="Associated risk tier label")


class MonthlyVolumePoint(BaseModel):
    """Single month data point for volume and average score trend."""

    month: str = Field(..., description="Month label, e.g. 'Sep 2026'")
    count: int = Field(..., ge=0, description="Number of applications created in this month")
    avg_score: Optional[float] = Field(None, description="Average credit score for applications assessed in this month")


class SectorRiskItem(BaseModel):
    """Sector/gig-work-type risk distribution aggregation."""

    sector: str = Field(..., description="Gig sector or work type from applicant profile")
    lower_risk: int = Field(0, ge=0, description="Count of assessments with LOWER risk")
    moderate_risk: int = Field(0, ge=0, description="Count of assessments with MODERATE risk")
    higher_risk: int = Field(0, ge=0, description="Count of assessments with HIGHER risk")
    manual_review: int = Field(0, ge=0, description="Count of assessments with INSUFFICIENT risk (manual review)")
    total: int = Field(0, ge=0, description="Total assessed applications in this sector")


class PortfolioAnalyticsResponse(BaseModel):
    """Aggregated portfolio analytics derived from application and assessment data."""

    total_applications: int = Field(..., ge=0, description="Total number of applications in the system")
    total_applicants: int = Field(0, ge=0, description="Total unique applicant profiles registered")
    status_distribution: Dict[str, int] = Field(
        ...,
        description="Count of applications grouped by ApplicationStatus (e.g. {'SUBMITTED': 5, 'ASSESSED': 3})",
    )
    risk_distribution: Dict[str, int] = Field(
        ...,
        description="Count of credit assessments grouped by RiskLevel (e.g. {'LOWER': 10, 'MODERATE': 5})",
    )
    average_credit_score: Optional[float] = Field(
        None,
        description="Mean credit score across all completed assessments (null if no assessments exist)",
    )
    average_risk_probability: Optional[float] = Field(
        None,
        description="Mean risk probability across all completed assessments (null if no assessments exist)",
    )
    assessment_completion_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of applications that have reached ASSESSED, MANUAL_REVIEW, or COMPLETED status",
    )
    total_assessments: int = Field(..., ge=0, description="Total number of credit assessments generated")
    assessed_applications: int = Field(0, ge=0, description="Count of applications in ASSESSED status")
    manual_review_applications: int = Field(0, ge=0, description="Count of applications requiring manual review")
    completed_applications: int = Field(0, ge=0, description="Count of applications completed/reviewed")
    score_distribution: List[ScoreBucket] = Field(
        default_factory=list,
        description="Credit score histogram buckets",
    )
    monthly_volume: List[MonthlyVolumePoint] = Field(
        default_factory=list,
        description="Application volume and average score by month (last 6 months)",
    )
    sector_risk: List[SectorRiskItem] = Field(
        default_factory=list,
        description="Sector risk distribution aggregated from real ApplicantProfile and CreditAssessment records",
    )
