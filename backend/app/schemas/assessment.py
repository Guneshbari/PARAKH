"""Pydantic schemas for CreditAssessment entity."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.assessment import RiskLevel


class CreditAssessmentBase(BaseModel):
    """Base fields representing assessment outputs."""

    credit_score: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Assigned alternative credit score (nullable if insufficient evidence)",
    )
    risk_probability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Estimated probability of default bounded [0, 1]",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Categorical risk tier (LOWER, MODERATE, HIGHER, INSUFFICIENT)",
    )
    confidence: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Model confidence level bounded [0, 1]",
    )
    debt_to_income: Optional[Decimal] = Field(
        None,
        description="Estimated debt-to-income ratio",
    )
    utilization: Optional[Decimal] = Field(
        None,
        description="Credit utilization proxy indicator",
    )
    income_stability: Optional[Decimal] = Field(
        None,
        description="Income stability index",
    )
    repayment_reliability: Optional[Decimal] = Field(
        None,
        description="Historical or platform repayment consistency",
    )
    explanation: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured explanation metadata (TreeSHAP factors, missing signals, diagnostics)",
    )
    assessment_status: str = Field(
        default="COMPLETED",
        description="Status of assessment generation process",
    )


class CreditAssessmentCreate(CreditAssessmentBase):
    """Schema for recording an assessment output."""

    application_id: UUID
    model_version_id: UUID


class CreditAssessmentResponse(CreditAssessmentBase):
    """Response schema returning credit assessment outputs."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    model_version_id: UUID
    score: Optional[int] = Field(None, description="Alternative credit score (alias for credit_score)")
    model_name: Optional[str] = Field(None, description="Scoring algorithm or engine identifier")
    model_version: Optional[str] = Field(None, description="Model semantic version string")
    key_factors: List[str] = Field(default_factory=list, description="Primary driving indicators")
    explanation: Optional[Dict[str, Any]] = Field(default=None, description="Structured explanation metadata")
    assessed_at: datetime
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def prepare_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "score" not in data or data["score"] is None:
                data["score"] = data.get("credit_score")
            return data

        mv_rel = getattr(data, "model_version", None)
        mv_version_str = getattr(data, "_transient_model_version", None)
        mv_name_str = getattr(data, "_transient_model_name", None)
        if mv_rel is not None and hasattr(mv_rel, "version"):
            if not mv_version_str:
                mv_version_str = mv_rel.version
            if not mv_name_str:
                mv_name_str = getattr(mv_rel, "model_name", None)

        score_val = getattr(data, "score", None)
        if score_val is None:
            score_val = getattr(data, "credit_score", None)

        raw_explanation = getattr(data, "_transient_explanation", None)
        if raw_explanation is None:
            raw_explanation = getattr(data, "explanation", None)

        raw_key_factors = getattr(data, "_transient_key_factors", None) or getattr(data, "key_factors", None)
        if not raw_key_factors and isinstance(raw_explanation, dict):
            factors = []
            for factor in raw_explanation.get("key_protective_factors", []):
                if isinstance(factor, dict):
                    name = factor.get("factor_name", "Protective Factor")
                    borrower_exp = factor.get("borrower_explanation", "")
                    factors.append(f"{name}: {borrower_exp}" if borrower_exp else name)
            for factor in raw_explanation.get("key_risk_factors", []):
                if isinstance(factor, dict):
                    name = factor.get("factor_name", "Risk Factor")
                    borrower_exp = factor.get("borrower_explanation", "")
                    factors.append(f"{name}: {borrower_exp}" if borrower_exp else name)
            if not factors and raw_explanation.get("is_insufficient_evidence") and raw_explanation.get("missing_signals"):
                factors = list(raw_explanation["missing_signals"])
            if factors:
                raw_key_factors = factors[:4]

        if not raw_key_factors:
            raw_key_factors = []
            if getattr(data, "repayment_reliability", None) is not None:
                raw_key_factors.append(f"Repayment reliability indicator: {data.repayment_reliability}")
            if getattr(data, "income_stability", None) is not None:
                raw_key_factors.append(f"Income stability index: {data.income_stability}")
            if getattr(data, "utilization", None) is not None:
                raw_key_factors.append(f"Credit utilization proxy: {data.utilization}")
            if not raw_key_factors:
                raw_key_factors = ["Credit evaluation completed based on alternative platform data"]

        return {
            "id": getattr(data, "id", None),
            "application_id": getattr(data, "application_id", None),
            "model_version_id": getattr(data, "model_version_id", None),
            "credit_score": getattr(data, "credit_score", None),
            "score": score_val,
            "risk_probability": getattr(data, "risk_probability", None),
            "risk_level": getattr(data, "risk_level", None),
            "confidence": getattr(data, "confidence", None),
            "debt_to_income": getattr(data, "debt_to_income", None),
            "utilization": getattr(data, "utilization", None),
            "income_stability": getattr(data, "income_stability", None),
            "repayment_reliability": getattr(data, "repayment_reliability", None),
            "assessment_status": getattr(data, "assessment_status", "COMPLETED"),
            "model_name": mv_name_str or getattr(data, "model_name", None),
            "model_version": mv_version_str,
            "key_factors": raw_key_factors,
            "explanation": raw_explanation,
            "assessed_at": getattr(data, "assessed_at", None),
            "created_at": getattr(data, "created_at", None),
        }
