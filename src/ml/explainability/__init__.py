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
from src.ml.explainability.cohort_fairness import (
    FAIRNESS_SYNTHETIC_DATA_DISCLAIMER,
    MultiModelFairnessReport,
    SegmentFairnessMetrics,
    audit_comparative_fairness,
    compute_subgroup_metrics,
)
from src.ml.explainability.plain_language import (
    FEATURE_PLAIN_LANGUAGE_CATALOG,
    PlainLanguageExplainer,
    PlainLanguageFactor,
)
from src.ml.explainability.shap_explainer import (
    LogisticExplainer,
    TreeShapExplainer,
)

__all__ = [
    "BaseExplainer",
    "FeatureContribution",
    "GlobalExplanation",
    "ImpactDirection",
    "LocalExplanation",
    "PlainLanguageTranslator",
    "TreeShapExplainer",
    "LogisticExplainer",
    "PlainLanguageExplainer",
    "PlainLanguageFactor",
    "FEATURE_PLAIN_LANGUAGE_CATALOG",
    "SegmentFairnessMetrics",
    "MultiModelFairnessReport",
    "compute_subgroup_metrics",
    "audit_comparative_fairness",
    "FAIRNESS_SYNTHETIC_DATA_DISCLAIMER",
]
