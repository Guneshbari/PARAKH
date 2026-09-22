"""PARAKH ML Explainability Package.

Provides interfaces and data structures for local and global model explanations
(SHAP integration in Phase 7) and plain-language factor translations.
"""
from src.ml.explainability.base import (
    BaseExplainer,
    FeatureContribution,
    GlobalExplanation,
    ImpactDirection,
    LocalExplanation,
    PlainLanguageTranslator,
)

__all__ = [
    "BaseExplainer",
    "FeatureContribution",
    "GlobalExplanation",
    "ImpactDirection",
    "LocalExplanation",
    "PlainLanguageTranslator",
]
