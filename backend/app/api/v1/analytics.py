"""Portfolio analytics aggregation API route.

Provides server-side SQL aggregations over Application, ApplicantProfile,
and CreditAssessment tables for the admin/reviewer dashboard.
All queries use GROUP BY and aggregate functions for efficiency — strictly no N+1.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.user import User, UserRole
from app.schemas.analytics import (
    MonthlyVolumePoint,
    PortfolioAnalyticsResponse,
    ScoreBucket,
    SectorRiskItem,
)

router = APIRouter(tags=["analytics"])

# Score bucket definitions matching the alternative credit resilience tier system
SCORE_BUCKETS = [
    {"min": 800, "max": 850, "range": "800–850", "label": "Exceptional Resilience", "risk_tier": "LOWER_ESTIMATED RISK"},
    {"min": 740, "max": 799, "range": "740–799", "label": "Strong Shock Recovery", "risk_tier": "LOWER_ESTIMATED RISK"},
    {"min": 680, "max": 739, "range": "680–739", "label": "Moderate Cyclical Variance", "risk_tier": "MODERATE_ESTIMATED RISK"},
    {"min": 600, "max": 679, "range": "600–679", "label": "Elevated Income Volatility", "risk_tier": "HIGHER_ESTIMATED RISK"},
    {"min": 0, "max": 599, "range": "< 600", "label": "Insufficient Evidence / High Volatility", "risk_tier": "INSUFFICIENT_EVIDENCE_MANUAL_REVIEW"},
]

# Month name lookup
MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _build_sector_risk(db: Session) -> List[SectorRiskItem]:
    """Aggregate risk tier distribution by gig work type from persisted data."""
    sector_risk_rows = (
        db.query(
            ApplicantProfile.gig_work_type,
            CreditAssessment.risk_level,
            func.count(CreditAssessment.id),
        )
        .join(Application, Application.id == CreditAssessment.application_id)
        .join(ApplicantProfile, ApplicantProfile.id == Application.applicant_profile_id)
        .group_by(ApplicantProfile.gig_work_type, CreditAssessment.risk_level)
        .all()
    )

    sector_map: Dict[str, Dict[str, int]] = {}
    for gig_type, risk_lvl, count in sector_risk_rows:
        if not gig_type:
            continue
        if gig_type not in sector_map:
            sector_map[gig_type] = {
                "lower": 0,
                "moderate": 0,
                "higher": 0,
                "manual_review": 0,
                "total": 0,
            }
        lvl_val = risk_lvl.value if hasattr(risk_lvl, "value") else str(risk_lvl)
        if lvl_val == RiskLevel.LOWER.value:
            sector_map[gig_type]["lower"] += count
        elif lvl_val == RiskLevel.MODERATE.value:
            sector_map[gig_type]["moderate"] += count
        elif lvl_val == RiskLevel.HIGHER.value:
            sector_map[gig_type]["higher"] += count
        elif lvl_val == RiskLevel.INSUFFICIENT.value:
            sector_map[gig_type]["manual_review"] += count
        sector_map[gig_type]["total"] += count

    return [
        SectorRiskItem(
            sector=sector_name,
            lower_risk=counts["lower"],
            moderate_risk=counts["moderate"],
            higher_risk=counts["higher"],
            manual_review=counts["manual_review"],
            total=counts["total"],
        )
        for sector_name, counts in sector_map.items()
    ]


@router.get(
    "/portfolio",
    response_model=PortfolioAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Portfolio Analytics Aggregation",
    description=(
        "Returns aggregated portfolio KPIs computed from Application, ApplicantProfile, "
        "and CreditAssessment tables. Includes status distribution, risk distribution, "
        "score histogram, monthly volume trend, and sector risk breakdown. "
        "Restricted to REVIEWER and ADMIN roles."
    ),
)
def get_portfolio_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PortfolioAnalyticsResponse:
    """Compute and return portfolio-level analytics from the database."""
    # RBAC enforcement
    if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only reviewers and administrators can access portfolio analytics.",
        )

    # 1. Total applications and total applicants count
    total_applications: int = db.query(func.count(Application.id)).scalar() or 0
    total_applicants: int = db.query(func.count(ApplicantProfile.id)).scalar() or 0

    # 2. Status distribution: COUNT GROUP BY status
    status_rows = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    status_distribution: Dict[str, int] = {}
    for app_status, count in status_rows:
        key = app_status.value if hasattr(app_status, "value") else str(app_status)
        status_distribution[key] = count

    # Ensure all canonical ApplicationStatus values are present
    for s in ApplicationStatus:
        if s.value not in status_distribution:
            status_distribution[s.value] = 0

    # 3. Risk distribution: COUNT GROUP BY risk_level from CreditAssessment
    risk_rows = (
        db.query(CreditAssessment.risk_level, func.count(CreditAssessment.id))
        .group_by(CreditAssessment.risk_level)
        .all()
    )
    risk_distribution: Dict[str, int] = {}
    for risk_level, count in risk_rows:
        key = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
        risk_distribution[key] = count

    # Ensure all canonical RiskLevel values are present
    for rl in RiskLevel:
        if rl.value not in risk_distribution:
            risk_distribution[rl.value] = 0

    # 4. Average credit score and risk probability
    avg_row = db.query(
        func.avg(CreditAssessment.credit_score),
        func.avg(CreditAssessment.risk_probability),
        func.count(CreditAssessment.id),
    ).first()

    average_credit_score: Optional[float] = None
    average_risk_probability: Optional[float] = None
    total_assessments: int = 0

    if avg_row:
        if avg_row[0] is not None:
            average_credit_score = round(float(avg_row[0]), 1)
        if avg_row[1] is not None:
            average_risk_probability = round(float(avg_row[1]), 4)
        total_assessments = avg_row[2] or 0

    # 5. Assessment completion rate & pipeline counts
    assessed_applications = status_distribution.get(ApplicationStatus.ASSESSED.value, 0)
    manual_review_applications = status_distribution.get(ApplicationStatus.MANUAL_REVIEW.value, 0)
    completed_applications = status_distribution.get(ApplicationStatus.COMPLETED.value, 0)

    completed_statuses_count = (
        assessed_applications + manual_review_applications + completed_applications
    )
    assessment_completion_rate = (
        round((completed_statuses_count / total_applications) * 100, 1)
        if total_applications > 0
        else 0.0
    )

    # 6. Score distribution histogram
    score_distribution: List[ScoreBucket] = []
    if total_assessments > 0:
        scored_total = (
            db.query(func.count(CreditAssessment.id))
            .filter(CreditAssessment.credit_score.isnot(None))
            .scalar()
        ) or 1

        for bucket in SCORE_BUCKETS:
            bucket_count: int = (
                db.query(func.count(CreditAssessment.id))
                .filter(
                    CreditAssessment.credit_score.isnot(None),
                    CreditAssessment.credit_score >= bucket["min"],
                    CreditAssessment.credit_score <= bucket["max"],
                )
                .scalar()
            ) or 0

            score_distribution.append(
                ScoreBucket(
                    range=bucket["range"],
                    label=bucket["label"],
                    count=bucket_count,
                    percentage=round((bucket_count / scored_total) * 100, 1) if scored_total > 0 else 0.0,
                    risk_tier=bucket["risk_tier"],
                )
            )

    # 7. Monthly volume trend (last 6 months)
    monthly_volume: List[MonthlyVolumePoint] = []
    now = datetime.utcnow()

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i * 30)
        target_year = target_date.year
        target_month = target_date.month

        month_count: int = (
            db.query(func.count(Application.id))
            .filter(
                extract("year", Application.created_at) == target_year,
                extract("month", Application.created_at) == target_month,
            )
            .scalar()
        ) or 0

        month_avg_score = (
            db.query(func.avg(CreditAssessment.credit_score))
            .filter(
                CreditAssessment.credit_score.isnot(None),
                extract("year", CreditAssessment.created_at) == target_year,
                extract("month", CreditAssessment.created_at) == target_month,
            )
            .scalar()
        )

        month_label = f"{MONTH_NAMES[target_month]} {target_year}"
        monthly_volume.append(
            MonthlyVolumePoint(
                month=month_label,
                count=month_count,
                avg_score=round(float(month_avg_score), 1) if month_avg_score is not None else None,
            )
        )

    # 8. Sector risk breakdown
    sector_risk = _build_sector_risk(db)

    return PortfolioAnalyticsResponse(
        total_applications=total_applications,
        total_applicants=total_applicants,
        status_distribution=status_distribution,
        risk_distribution=risk_distribution,
        average_credit_score=average_credit_score,
        average_risk_probability=average_risk_probability,
        assessment_completion_rate=assessment_completion_rate,
        total_assessments=total_assessments,
        assessed_applications=assessed_applications,
        manual_review_applications=manual_review_applications,
        completed_applications=completed_applications,
        score_distribution=score_distribution,
        monthly_volume=monthly_volume,
        sector_risk=sector_risk,
    )


@router.get(
    "/sector-risk",
    response_model=List[SectorRiskItem],
    status_code=status.HTTP_200_OK,
    summary="Sector Risk Distribution",
    description=(
        "Returns risk tier distribution grouped by applicant gig work type/sector. "
        "Only includes records where persisted data exists. Restricted to REVIEWER and ADMIN roles."
    ),
)
def get_sector_risk(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[SectorRiskItem]:
    """Compute and return sector-level risk distribution from the database."""
    if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only reviewers and administrators can access sector risk analytics.",
        )
    return _build_sector_risk(db)
