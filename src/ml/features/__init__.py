"""PARAKH ML Feature Engineering Package.

Provides deterministic, leakage-safe feature engineering and lineage tracking
for volatility-aware credit risk modeling.
"""
from src.ml.features.feature_engineering import (
    BASELINE_FEATURE_SET,
    ENGINEERED_VOLATILITY_FEATURES,
    FeatureEngineer,
    FeatureLineageRecord,
    MASTER_LINEAGE,
    build_model_ready_matrices,
)

__all__ = [
    "FeatureEngineer",
    "FeatureLineageRecord",
    "MASTER_LINEAGE",
    "ENGINEERED_VOLATILITY_FEATURES",
    "BASELINE_FEATURE_SET",
    "build_model_ready_matrices",
]
