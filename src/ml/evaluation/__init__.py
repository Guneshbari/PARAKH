"""PARAKH ML Evaluation Package.

Provides classification metrics, calibration analysis, cohort auditing,
model comparison, experiment tracking, and fairness evaluation utilities.
"""
from src.ml.evaluation.calibration import CalibrationBin, CalibrationResult, evaluate_calibration
from src.ml.evaluation.cohorts import CohortEvaluationResult, evaluate_by_cohort
from src.ml.evaluation.comparison import CohortDelta, ModelComparisonResult, compare_models
from src.ml.evaluation.fairness import FairnessAuditReport, SubgroupFairnessMetrics, audit_subgroup_fairness
from src.ml.evaluation.metrics import ClassificationMetrics, evaluate_predictions
from src.ml.evaluation.tracking import ExperimentMetadata

__all__ = [
    "ClassificationMetrics",
    "evaluate_predictions",
    "CalibrationBin",
    "CalibrationResult",
    "evaluate_calibration",
    "CohortEvaluationResult",
    "evaluate_by_cohort",
    "CohortDelta",
    "ModelComparisonResult",
    "compare_models",
    "SubgroupFairnessMetrics",
    "FairnessAuditReport",
    "audit_subgroup_fairness",
    "ExperimentMetadata",
]
