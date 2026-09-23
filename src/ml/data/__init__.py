"""PARAKH ML Data Package.

Provides dataset validation boundaries, grouped train/val/test splitting,
and deterministic preprocessing for credit repayment risk modeling.
"""
from src.ml.data.dataset_validator import (
    ComprehensiveValidationReport,
    DatasetValidationDiagnostics,
    Phase3DatasetValidator,
    CANONICAL_COLUMNS,
    DERIVED_FEATURES,
    MANDATORY_FEATURES,
    OPTIONAL_FEATURES,
)
from src.ml.data.preprocessing import CreditRiskPreprocessor
from src.ml.data.splitting import (
    GroupedDatasetSplitter,
    GroupedSplitResult,
    PartitionSummary,
)
from src.ml.data.validation import (
    LeakageAuditReport,
    ModelDataValidator,
    ValidationReport,
)

__all__ = [
    "ModelDataValidator",
    "ValidationReport",
    "LeakageAuditReport",
    "Phase3DatasetValidator",
    "ComprehensiveValidationReport",
    "DatasetValidationDiagnostics",
    "CANONICAL_COLUMNS",
    "DERIVED_FEATURES",
    "MANDATORY_FEATURES",
    "OPTIONAL_FEATURES",
    "GroupedDatasetSplitter",
    "GroupedSplitResult",
    "PartitionSummary",
    "CreditRiskPreprocessor",
]
