"""Output formatting for PARAKH credit risk inference pipeline (Phase 9).

Constructs the canonical PredictionResponse dataclass from intermediate pipeline results.
All field semantics follow the frozen contract in FINAL_MODEL.json / docs/final-model-selection.md.

Output fields (per frozen contract):
  repayment_risk_probability    — float [0, 1]; null for INSUFFICIENT applications.
  risk_tier                     — RiskTier enum value string.
  presentation_score            — int [300, 850]; null for INSUFFICIENT applications.
  confidence_or_data_sufficiency — float [0, 1]; 0.0 for INSUFFICIENT.
  missing_or_insufficient_signals — list[str] of data-sufficiency failure messages.
  explanation_factors            — borrower-facing plain-language explanation dict.
  model_name                     — frozen model name string.
  model_version                  — frozen model version string.
  feature_variant                — "VOLATILITY_AWARE".
  diagnostic_threshold_status    — description of the diagnostic threshold used.
  assessed_at                    — ISO 8601 UTC timestamp.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.ml.constants import (
    PRESENTATION_SCORE_MAX,
    PRESENTATION_SCORE_MIN,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
    RiskTier,
)

# Diagnostic threshold from FINAL_MODEL.json
DIAGNOSTIC_THRESHOLD: float = 0.50
DIAGNOSTIC_THRESHOLD_STATUS: str = (
    "Diagnostic threshold 0.50 is used for this prototype assessment. "
    "Operational lending thresholds require formal credit policy approval."
)


@dataclass
class PredictionResponse:
    """Canonical output for a single PARAKH credit risk inference call.

    Fields map 1-to-1 to the expected_output_schema in FINAL_MODEL.json.
    """

    # Core risk prediction outputs
    repayment_risk_probability: Optional[float]
    risk_tier: str                      # RiskTier.value string
    presentation_score: Optional[int]

    # Data sufficiency and confidence
    is_insufficient_evidence: bool
    confidence_or_data_sufficiency: float
    missing_or_insufficient_signals: List[str]

    # Explanation
    explanation_factors: Dict[str, Any]

    # Model provenance
    model_name: str
    model_version: str
    feature_variant: str
    diagnostic_threshold_status: str

    # Timestamp
    assessed_at: str  # ISO 8601 UTC

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to a JSON-serialisable dictionary."""
        return asdict(self)


class OutputFormatter:
    """Constructs a PredictionResponse from pipeline intermediates.

    All formulas are frozen from training scripts and src/ml/constants.py.
    """

    @classmethod
    def format_scored(
        cls,
        *,
        probability: float,
        explanation_factors: Dict[str, Any],
        model_name: str,
        model_version: str,
        feature_variant: str,
    ) -> PredictionResponse:
        """Format the output for a successfully scored application.

        Args:
            probability: Model-predicted default probability in [0, 1].
            explanation_factors: Output of PlainLanguageExplainer.generate_borrower_explanation_summary.
            model_name: Frozen model name from FINAL_MODEL.json.
            model_version: Frozen model version from FINAL_MODEL.json.
            feature_variant: Feature variant used ("VOLATILITY_AWARE").

        Returns:
            PredictionResponse with all scored fields populated.
        """
        prob = float(probability)
        prob = max(0.0, min(1.0, prob))  # Clamp to [0, 1]

        risk_tier = cls._map_risk_tier(prob)
        score = cls._compute_presentation_score(prob)

        # Confidence: distance from the midpoint of the dominant tier's interval
        # Clamp to [0.0, 1.0] — higher values = further from a tier boundary
        confidence = cls._compute_confidence(prob)

        return PredictionResponse(
            repayment_risk_probability=round(prob, 6),
            risk_tier=risk_tier.value,
            presentation_score=score,
            is_insufficient_evidence=False,
            confidence_or_data_sufficiency=round(confidence, 4),
            missing_or_insufficient_signals=[],
            explanation_factors=explanation_factors,
            model_name=model_name,
            model_version=model_version,
            feature_variant=feature_variant,
            diagnostic_threshold_status=DIAGNOSTIC_THRESHOLD_STATUS,
            assessed_at=cls._utc_timestamp(),
        )

    @classmethod
    def format_insufficient(
        cls,
        *,
        reasons: List[str],
        model_name: str,
        model_version: str,
        feature_variant: str,
    ) -> PredictionResponse:
        """Format the output for an application with insufficient evidence.

        Args:
            reasons: List of data-sufficiency failure reasons from InputValidator.
            model_name: Frozen model name.
            model_version: Frozen model version.
            feature_variant: Feature variant used.

        Returns:
            PredictionResponse with INSUFFICIENT tier and null scored fields.
        """
        return PredictionResponse(
            repayment_risk_probability=None,
            risk_tier=RiskTier.INSUFFICIENT.value,
            presentation_score=None,
            is_insufficient_evidence=True,
            confidence_or_data_sufficiency=0.0,
            missing_or_insufficient_signals=reasons,
            explanation_factors={
                "key_protective_factors": [],
                "key_risk_factors": [],
                "disclaimer": (
                    "This application could not be scored due to insufficient observation history, "
                    "payout cycles, or core signal groups. No statistical assessment was generated."
                ),
            },
            model_name=model_name,
            model_version=model_version,
            feature_variant=feature_variant,
            diagnostic_threshold_status=DIAGNOSTIC_THRESHOLD_STATUS,
            assessed_at=cls._utc_timestamp(),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_risk_tier(probability: float) -> RiskTier:
        """Map a default probability to the frozen risk tier.

        Thresholds (from src/ml/constants.py, frozen in Phase 5/6):
          - LOWER    : p < 0.20
          - MODERATE : 0.20 <= p < 0.45
          - HIGHER   : p >= 0.45
        """
        if probability < PROVISIONAL_THRESHOLD_LOWER:
            return RiskTier.LOWER
        elif probability < PROVISIONAL_THRESHOLD_HIGHER:
            return RiskTier.MODERATE
        else:
            return RiskTier.HIGHER

    @staticmethod
    def _compute_presentation_score(probability: float) -> int:
        """Convert default probability to a [300, 850] presentation score.

        Formula frozen from src/ml/constants.py + all training evaluation scripts:
            score = int(round(MIN + (1 - p) * (MAX - MIN)))
            score = max(MIN, min(MAX, score))
        Higher probability → lower score (higher risk → lower creditworthiness score).
        """
        score = int(round(
            PRESENTATION_SCORE_MIN + (1.0 - probability) * (PRESENTATION_SCORE_MAX - PRESENTATION_SCORE_MIN)
        ))
        return max(PRESENTATION_SCORE_MIN, min(PRESENTATION_SCORE_MAX, score))

    @staticmethod
    def _compute_confidence(probability: float) -> float:
        """Compute confidence as normalised distance from the nearest tier boundary.

        Provides a [0, 1] measure of how far into the assigned tier the prediction sits.
        A value near 1.0 indicates a clear, unambiguous tier assignment.
        A value near 0.0 indicates the prediction is close to a tier boundary.
        """
        # Tier boundaries
        lower_boundary = PROVISIONAL_THRESHOLD_LOWER   # 0.20
        higher_boundary = PROVISIONAL_THRESHOLD_HIGHER  # 0.45

        if probability < lower_boundary:
            # LOWER tier: distance from upper boundary (0.20), max span 0.20
            dist = lower_boundary - probability
            span = lower_boundary  # [0, 0.20]
            confidence = dist / span if span > 0 else 0.0
        elif probability < higher_boundary:
            # MODERATE tier: distance from nearest boundary, max span 0.25
            dist_lower = probability - lower_boundary
            dist_higher = higher_boundary - probability
            dist = min(dist_lower, dist_higher)
            span = (higher_boundary - lower_boundary) / 2.0
            confidence = dist / span if span > 0 else 0.0
        else:
            # HIGHER tier: distance from lower boundary (0.45), max span 0.55
            dist = probability - higher_boundary
            span = 1.0 - higher_boundary  # [0.45, 1.0]
            confidence = dist / span if span > 0 else 0.0

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _utc_timestamp() -> str:
        """Return current UTC time as ISO 8601 string."""
        return datetime.now(tz=timezone.utc).isoformat()
