"""Cohort-specific evaluation utilities for PARAKH credit risk assessment.

Implements segmented performance auditing across the synthetic population cohorts
defined in the Phase 1 Data Contract (Stable, Healthy Volatile, Declining, Irregular, etc.).
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np

from src.ml.evaluation.calibration import CalibrationResult, evaluate_calibration
from src.ml.evaluation.metrics import ClassificationMetrics, evaluate_predictions


@dataclass
class CohortEvaluationResult:
    """Evaluation summary for a specific borrower cohort."""

    cohort_name: str
    sample_count: int
    positive_count: int
    negative_count: int
    empirical_default_rate: float
    metrics: Optional[ClassificationMetrics]
    calibration: Optional[CalibrationResult]
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert cohort evaluation to dictionary."""
        d = asdict(self)
        if self.metrics:
            d["metrics"] = self.metrics.to_dict()
        if self.calibration:
            d["calibration"] = self.calibration.to_dict()
        return d


def evaluate_by_cohort(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob: Union[Sequence[float], np.ndarray],
    cohorts: Sequence[str],
    threshold: float = 0.5,
    min_samples_for_metrics: int = 2,
    include_calibration: bool = True,
) -> Dict[str, CohortEvaluationResult]:
    """Calculate evaluation metrics independently across borrower cohorts.

    Args:
        y_true: Ground truth binary repayment labels.
        y_prob: Predicted default probabilities.
        cohorts: Sequence of cohort identifiers matching y_true and y_prob length.
        threshold: Decision threshold for classification metrics.
        min_samples_for_metrics: Minimum cohort size required to compute metrics (default 2).
        include_calibration: Whether to calculate calibration curve per cohort.

    Returns:
        Dict[str, CohortEvaluationResult]: Mapping of cohort name to evaluation results.

    Raises:
        ValueError: If input lengths do not match or arrays are empty.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    cohorts_arr = np.asarray(cohorts, dtype=str)

    n_samples = len(y_true_arr)
    if n_samples == 0:
        raise ValueError("Input arrays must not be empty.")
    if len(y_prob_arr) != n_samples or len(cohorts_arr) != n_samples:
        raise ValueError(
            f"Mismatched lengths: y_true={len(y_true_arr)}, y_prob={len(y_prob_arr)}, cohorts={len(cohorts_arr)}"
        )

    unique_cohorts = sorted(list(set(cohorts_arr)))
    results: Dict[str, CohortEvaluationResult] = {}

    for cohort in unique_cohorts:
        mask = (cohorts_arr == cohort)
        c_true = y_true_arr[mask]
        c_prob = y_prob_arr[mask]
        c_count = int(len(c_true))
        c_pos = int(np.sum(c_true == 1))
        c_neg = int(np.sum(c_true == 0))
        c_def_rate = float(c_pos / c_count) if c_count > 0 else 0.0

        if c_count < min_samples_for_metrics:
            results[cohort] = CohortEvaluationResult(
                cohort_name=cohort,
                sample_count=c_count,
                positive_count=c_pos,
                negative_count=c_neg,
                empirical_default_rate=round(c_def_rate, 4),
                metrics=None,
                calibration=None,
                notes=f"Insufficient sample count ({c_count} < {min_samples_for_metrics}) to evaluate metrics.",
            )
            continue

        # Evaluate classification metrics safely
        c_metrics = evaluate_predictions(c_true, c_prob, threshold=threshold)

        # Evaluate calibration if requested and enough samples exist
        c_calib: Optional[CalibrationResult] = None
        if include_calibration:
            if c_count >= 5:
                n_bins = min(5, c_count)
                try:
                    c_calib = evaluate_calibration(c_true, c_prob, n_bins=n_bins)
                except Exception as err:
                    c_metrics.notes = (
                        f"{c_metrics.notes}; Calibration skipped: {err}"
                        if c_metrics.notes
                        else f"Calibration skipped: {err}"
                    )
            else:
                if c_metrics.notes:
                    c_metrics.notes += "; Cohort too small for calibration evaluation"
                else:
                    c_metrics.notes = "Cohort too small for calibration evaluation"

        results[cohort] = CohortEvaluationResult(
            cohort_name=cohort,
            sample_count=c_count,
            positive_count=c_pos,
            negative_count=c_neg,
            empirical_default_rate=round(c_def_rate, 4),
            metrics=c_metrics,
            calibration=c_calib,
            notes=c_metrics.notes,
        )

    return results
