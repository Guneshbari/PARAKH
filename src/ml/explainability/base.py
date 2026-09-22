"""Explainability interfaces and feature contribution structures for PARAKH ML models.

Defines the contract for future SHAP-based local and global model explanations
(Phase 7), cleanly separating quantitative attributions from plain-language translations.
No SHAP computation or fake values are generated in this preparation phase.
"""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

from src.ml.models.base import BaseRiskModel


class ImpactDirection(str, Enum):
    """Directional influence of an input feature on repayment risk."""

    INCREASES_RISK = "INCREASES_RISK"
    DECREASES_RISK = "DECREASES_RISK"
    NEUTRAL = "NEUTRAL"


@dataclass
class FeatureContribution:
    """Quantitative attribution and qualitative description for an individual feature."""

    feature_name: str
    feature_value: Any
    attribution_value: float  # e.g., SHAP value in log-odds or probability space
    impact_direction: ImpactDirection
    plain_language_description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert contribution to dictionary."""
        d = asdict(self)
        d["impact_direction"] = self.impact_direction.value
        return d


@dataclass
class LocalExplanation:
    """Instance-level feature attribution explanation (e.g., local SHAP breakdown)."""

    model_name: str
    model_version: str
    base_value: float  # Expected value / prior probability
    predicted_risk_probability: float
    contributions: List[FeatureContribution]
    top_risk_increasing_factors: List[FeatureContribution] = field(default_factory=list)
    top_risk_reducing_factors: List[FeatureContribution] = field(default_factory=list)
    plain_language_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert local explanation to dictionary."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "base_value": self.base_value,
            "predicted_risk_probability": self.predicted_risk_probability,
            "contributions": [c.to_dict() for c in self.contributions],
            "top_risk_increasing_factors": [c.to_dict() for c in self.top_risk_increasing_factors],
            "top_risk_reducing_factors": [c.to_dict() for c in self.top_risk_reducing_factors],
            "plain_language_summary": self.plain_language_summary,
        }


@dataclass
class GlobalExplanation:
    """Model-wide global feature importance and average absolute attributions."""

    model_name: str
    model_version: str
    mean_absolute_attributions: Dict[str, float]
    feature_importance_ranking: List[str]
    sample_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert global explanation to dictionary."""
        return asdict(self)


class BaseExplainer(ABC):
    """Abstract interface contract for model explainers (e.g. SHAP, TreeSHAP, LinearSHAP)."""

    def __init__(self, model: BaseRiskModel) -> None:
        """Initialize explainer with a trained risk model."""
        self.model = model

    @abstractmethod
    def explain_instance(
        self,
        features: Union[pd.Series, pd.DataFrame, np.ndarray, Dict[str, Any]],
        top_n: int = 5,
    ) -> LocalExplanation:
        """Generate local feature attributions for a single applicant assessment.

        Args:
            features: 1D or single-row feature observation.
            top_n: Number of leading positive/negative driving factors to extract.

        Returns:
            LocalExplanation: Structured local attributions and plain-language summary.
        """
        pass

    @abstractmethod
    def explain_global(
        self,
        X_sample: Union[pd.DataFrame, np.ndarray],
    ) -> GlobalExplanation:
        """Generate global feature importances across a background sample.

        Args:
            X_sample: Representative dataset sample.

        Returns:
            GlobalExplanation: Ranked features and mean absolute attributions.
        """
        pass


class PlainLanguageTranslator:
    """Translates numerical feature impacts into clear, human-understandable loan reviewer rationale."""

    # Default template mapping for key feature groups
    FEATURE_EXPLANATION_TEMPLATES = {
        "income_cv_90d": {
            ImpactDirection.DECREASES_RISK: "Consistent periodic income with low variance supports predictable repayment.",
            ImpactDirection.INCREASES_RISK: "Elevated earnings volatility across payout cycles indicates income unpredictability.",
        },
        "recovery_duration_days": {
            ImpactDirection.DECREASES_RISK: "Demonstrated rapid earning recovery following income dips indicates strong resilience.",
            ImpactDirection.INCREASES_RISK: "Prolonged recovery periods following income drops suggest cashflow vulnerability.",
        },
        "cashflow_buffer": {
            ImpactDirection.DECREASES_RISK: "Healthy liquid cash reserve provides an effective cushion against unexpected shocks.",
            ImpactDirection.INCREASES_RISK: "Limited cash reserve provides minimal buffer to absorb temporary earning disruptions.",
        },
        "debt_to_income": {
            ImpactDirection.DECREASES_RISK: "Favorable debt-to-income ratio leaves sufficient disposable income for debt service.",
            ImpactDirection.INCREASES_RISK: "High existing monthly debt commitments consume a substantial portion of baseline earnings.",
        },
        "active_days_ratio": {
            ImpactDirection.DECREASES_RISK: "Consistent active working engagement on the platform demonstrates earning reliability.",
            ImpactDirection.INCREASES_RISK: "Low active working days reduce cumulative earning capacity.",
        },
    }

    @classmethod
    def translate_factor(
        cls,
        feature_name: str,
        direction: ImpactDirection,
        feature_value: Optional[Any] = None,
    ) -> str:
        """Generate a plain-language summary statement for a feature attribution."""
        templates = cls.FEATURE_EXPLANATION_TEMPLATES.get(feature_name)
        if templates and direction in templates:
            return templates[direction]

        # Generic respectful fallback
        direction_word = "favorable" if direction == ImpactDirection.DECREASES_RISK else "elevated"
        clean_name = feature_name.replace("_", " ").title()
        return f"{clean_name} presents an {direction_word} pattern for credit assessment."
