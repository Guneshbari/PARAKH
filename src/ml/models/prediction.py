"""Typed prediction result contract for PARAKH ML assessments.

Defines the output interface that ML models produce and downstream presentation
or inference services consume. Completely decoupled from backend database ORM schemas.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from src.ml.constants import (
    PRESENTATION_SCORE_MAX,
    PRESENTATION_SCORE_MIN,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
    RiskTier,
)


@dataclass
class PredictionResult:
    """Standardized evaluation result produced by a PARAKH ML model.

    Represents an application-level assessment anchored to an applicant at a specific timestamp.
    Supports both scored outcomes and insufficient-evidence outcomes where statistical
    evaluation is refused due to data sparsity or truncated history.
    """

    model_name: str
    model_version: str
    risk_level: RiskTier
    confidence: float
    is_insufficient_evidence: bool = False

    # Scored evaluation fields (None when is_insufficient_evidence is True)
    risk_probability: Optional[float] = None
    score: Optional[int] = None
    debt_to_income: Optional[float] = None
    income_stability: Optional[float] = None
    repayment_reliability: Optional[float] = None

    # Context and explainability
    application_id: Optional[str] = None
    applicant_profile_id: Optional[str] = None
    income_archetype: Optional[str] = None
    volatility_interpretation: Optional[str] = None
    key_factors: List[str] = field(default_factory=list)
    explanation: Dict[str, Any] = field(default_factory=dict)
    missing_signal_guidance: Optional[List[str]] = None
    assessed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Validate internal consistency of the prediction contract."""
        self.validate()

    def validate(self) -> None:
        """Perform assertions on probability ranges, scores, and sufficiency state."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        if self.is_insufficient_evidence:
            if self.risk_level != RiskTier.INSUFFICIENT:
                raise ValueError(
                    f"risk_level must be INSUFFICIENT when is_insufficient_evidence is True, got {self.risk_level}"
                )
            if self.score is not None:
                raise ValueError("score must be None for insufficient evidence assessments")
        else:
            if self.risk_probability is None:
                raise ValueError("risk_probability must be provided for scored assessments")
            if not (0.0 <= self.risk_probability <= 1.0):
                raise ValueError(
                    f"risk_probability must be in [0.0, 1.0], got {self.risk_probability}"
                )
            if self.score is not None and not (0 <= self.score <= 1000):
                raise ValueError(f"score must be between 0 and 1000, got {self.score}")

    @classmethod
    def create_insufficient_evidence_result(
        cls,
        model_name: str,
        model_version: str,
        confidence: float,
        key_factors: List[str],
        missing_signal_guidance: List[str],
        application_id: Optional[str] = None,
        applicant_profile_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> "PredictionResult":
        """Factory method for constructing standard INSUFFICIENT evidence outcomes."""
        explanation_payload: Dict[str, Any] = {
            "insufficient_evidence": True,
            "engine_note": notes or "Assessment refused due to insufficient observation history or missing core signal pillars.",
        }
        return cls(
            model_name=model_name,
            model_version=model_version,
            risk_level=RiskTier.INSUFFICIENT,
            confidence=confidence,
            is_insufficient_evidence=True,
            risk_probability=None,
            score=None,
            key_factors=key_factors,
            missing_signal_guidance=missing_signal_guidance,
            application_id=application_id,
            applicant_profile_id=applicant_profile_id,
            explanation=explanation_payload,
        )

    @classmethod
    def create_scored_result(
        cls,
        model_name: str,
        model_version: str,
        risk_probability: float,
        confidence: float,
        key_factors: List[str],
        score: Optional[int] = None,
        risk_level: Optional[RiskTier] = None,
        debt_to_income: Optional[float] = None,
        income_stability: Optional[float] = None,
        repayment_reliability: Optional[float] = None,
        income_archetype: Optional[str] = None,
        volatility_interpretation: Optional[str] = None,
        explanation: Optional[Dict[str, Any]] = None,
        application_id: Optional[str] = None,
        applicant_profile_id: Optional[str] = None,
    ) -> "PredictionResult":
        """Factory method for constructing scored evaluations with calibrated probabilities.

        If score is omitted, computes monotonic presentation score (300-850).
        If risk_level is omitted, applies provisional decision thresholds.
        """
        # Monotonic presentation score mapping
        if score is None:
            score = int(
                round(
                    PRESENTATION_SCORE_MIN
                    + (1.0 - risk_probability)
                    * (PRESENTATION_SCORE_MAX - PRESENTATION_SCORE_MIN)
                )
            )
            score = max(PRESENTATION_SCORE_MIN, min(PRESENTATION_SCORE_MAX, score))

        # Provisional threshold mapping (documented as provisional in Phase 0 & 1)
        if risk_level is None:
            if risk_probability < PROVISIONAL_THRESHOLD_LOWER:
                risk_level = RiskTier.LOWER
            elif risk_probability < PROVISIONAL_THRESHOLD_HIGHER:
                risk_level = RiskTier.MODERATE
            else:
                risk_level = RiskTier.HIGHER

        return cls(
            model_name=model_name,
            model_version=model_version,
            risk_level=risk_level,
            confidence=confidence,
            is_insufficient_evidence=False,
            risk_probability=round(float(risk_probability), 4),
            score=score,
            debt_to_income=round(debt_to_income, 4) if debt_to_income is not None else None,
            income_stability=round(income_stability, 4) if income_stability is not None else None,
            repayment_reliability=round(repayment_reliability, 4) if repayment_reliability is not None else None,
            income_archetype=income_archetype,
            volatility_interpretation=volatility_interpretation,
            key_factors=key_factors,
            explanation=explanation or {},
            application_id=application_id,
            applicant_profile_id=applicant_profile_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize prediction result to a JSON-compatible dictionary."""
        d = asdict(self)
        d["risk_level"] = self.risk_level.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionResult":
        """Deserialize from dictionary."""
        data_copy = dict(data)
        if isinstance(data_copy.get("risk_level"), str):
            data_copy["risk_level"] = RiskTier(data_copy["risk_level"])
        return cls(**data_copy)
