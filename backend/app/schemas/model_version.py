"""Pydantic schemas for ModelVersion entity."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelVersionBase(BaseModel):
    """Base fields for algorithmic model version tracking."""

    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    version: str = Field(..., min_length=1, max_length=50, description="Semantic version string")
    algorithm: Optional[str] = Field(None, max_length=100, description="Algorithm architecture or family")
    description: Optional[str] = Field(None, description="Detailed model purpose and features")
    is_active: bool = Field(default=True, description="Whether this version is available for active scoring")


class ModelVersionCreate(ModelVersionBase):
    """Schema for registering a new model version."""

    pass


class ModelVersionResponse(ModelVersionBase):
    """Response schema for model version provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class FairnessAuditRecord(BaseModel):
    """Explicit evaluation record for offline fairness auditing."""

    y_true: int = Field(..., ge=0, le=1, description="Binary ground-truth repayment outcome (0=repaid, 1=default)")
    y_prob: float = Field(..., ge=0.0, le=1.0, description="Predicted default probability")
    subgroup: str = Field(..., min_length=1, description="Operational subgroup identifier")


class FairnessAuditRequest(BaseModel):
    """Request payload for offline fairness evaluation execution."""

    subgroup_field: str = Field(
        default="gig_work_type",
        min_length=1,
        max_length=100,
        description="Operational grouping field (e.g. gig_work_type, cohort_archetype, loan_purpose)",
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Decision threshold for classification into default vs. non-default",
    )
    records: Optional[List[FairnessAuditRecord]] = Field(
        default=None,
        description="Optional caller-supplied evaluation records. If omitted, the offline benchmark dataset is used.",
    )

    @field_validator("records")
    @classmethod
    def validate_records_non_empty(
        cls, v: Optional[List[FairnessAuditRecord]]
    ) -> Optional[List[FairnessAuditRecord]]:
        if v is not None and len(v) == 0:
            raise ValueError("records list cannot be empty when provided.")
        return v


class SubgroupFairnessMetricsResponse(BaseModel):
    """Fairness and performance metrics for an individual operational subgroup."""

    subgroup_name: str
    sample_count: int
    positive_actual_count: int
    negative_actual_count: int
    empirical_default_rate: float
    favorable_prediction_rate: float
    true_positive_rate: Optional[float] = None
    false_positive_rate: Optional[float] = None
    precision: Optional[float] = None


class FairnessAuditResponse(BaseModel):
    """Fairness audit evaluation response."""

    model_version_id: UUID
    model_name: str
    version: str
    evaluation_timestamp: datetime
    subgroup_field: str
    threshold: float
    sample_count: int
    subgroups: Dict[str, SubgroupFairnessMetricsResponse]
    demographic_parity_ratio: Optional[float] = None
    equal_opportunity_difference: Optional[float] = None
    limitations_disclaimer: str
    audit_notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# P2-10: Global SHAP Feature Importance Schemas
# ---------------------------------------------------------------------------

class GlobalSHAPFeatureItem(BaseModel):
    """Per-feature global SHAP importance entry.

    mean_abs_shap: Mean absolute SHAP value across the evaluation population.
                   Represents the average magnitude of each feature's contribution
                   to model predictions (primary importance measure).
    mean_shap:     Signed mean SHAP value, indicating average directional influence.
                   Positive = average risk-increasing contribution; negative = risk-reducing.
    rank:          1-based rank by mean_abs_shap descending (deterministic secondary sort
                   by feature_name ascending when values are equal).
    """

    feature_name: str = Field(..., description="Model feature identifier")
    mean_abs_shap: float = Field(..., description="Mean absolute SHAP value (primary importance measure)")
    mean_shap: float = Field(..., description="Signed mean SHAP value (average directional contribution)")
    rank: int = Field(..., ge=1, description="1-based rank ordered by mean_abs_shap descending")


class GlobalSHAPResponse(BaseModel):
    """Global/model-level SHAP feature importance aggregation response.

    This result is computed from the offline evaluation dataset using the
    existing TreeSHAP infrastructure and does NOT expose individual applicant data.
    It is associated with a specific registered model version for provenance tracking.
    """

    model_version_id: UUID = Field(..., description="Model version UUID used for computation")
    model_version: str = Field(..., description="Model semantic version string")
    model_name: str = Field(..., description="Model name identifier")
    evaluated_at: datetime = Field(..., description="UTC timestamp of aggregation execution")
    sample_count: int = Field(..., ge=0, description="Number of evaluation records used for aggregation")
    dataset_source: str = Field(
        ...,
        description="Description of the evaluation dataset used (not individual applicant data)",
    )
    features: List[GlobalSHAPFeatureItem] = Field(
        ...,
        description="Feature importance entries ordered by mean_abs_shap descending",
    )
