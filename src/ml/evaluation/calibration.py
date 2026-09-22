"""Probability calibration evaluation utilities for PARAKH credit risk models.

Provides reliability curve calculations, Brier score verification, and Expected
Calibration Error (ECE) metrics to ensure predicted default probabilities reflect
true empirical default rates.
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss


@dataclass
class CalibrationBin:
    """Statistics for an individual probability calibration bin."""

    bin_index: int
    prob_min: float
    prob_max: float
    mean_predicted_prob: float
    empirical_fraction_positives: float
    sample_count: int
    absolute_error: float


@dataclass
class CalibrationResult:
    """Comprehensive calibration evaluation result."""

    brier_score: float
    expected_calibration_error: float  # ECE: Weighted average absolute calibration gap
    maximum_calibration_error: float   # MCE: Worst-case absolute calibration gap
    n_bins_requested: int
    n_bins_populated: int
    strategy: str
    bins: List[CalibrationBin]

    def to_dict(self) -> Dict[str, Any]:
        """Convert calibration result to dictionary."""
        return asdict(self)


def evaluate_calibration(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob: Union[Sequence[float], np.ndarray],
    n_bins: int = 10,
    strategy: str = "uniform",
) -> CalibrationResult:
    """Evaluate calibration of predicted default probabilities against observed outcomes.

    Args:
        y_true: Ground truth binary labels (0 = non-default, 1 = default).
        y_prob: Predicted probabilities bounded in [0.0, 1.0].
        n_bins: Number of probability discretization bins (default 10).
        strategy: Binning strategy ('uniform' for equal-width, 'quantile' for equal-frequency).

    Returns:
        CalibrationResult: Structured calibration metrics including ECE, MCE, and bin statistics.

    Raises:
        ValueError: If input arrays are empty, have mismatched lengths, or strategy is invalid.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    if len(y_true_arr) == 0:
        raise ValueError("y_true and y_prob cannot be empty.")
    if len(y_true_arr) != len(y_prob_arr):
        raise ValueError("Length of y_true and y_prob must match.")
    if n_bins <= 1:
        raise ValueError(f"n_bins must be greater than 1, got {n_bins}")
    if strategy not in ("uniform", "quantile"):
        raise ValueError(f"strategy must be 'uniform' or 'quantile', got '{strategy}'")

    y_prob_arr = np.clip(y_prob_arr, 0.0, 1.0)
    total_samples = len(y_true_arr)

    brier = float(brier_score_loss(y_true_arr, y_prob_arr))

    # Calculate empirical calibration curve using scikit-learn
    frac_pos, mean_pred = calibration_curve(
        y_true_arr,
        y_prob_arr,
        n_bins=n_bins,
        strategy=strategy,
    )

    # Determine bin edges to populate detailed bin counts and bounds
    if strategy == "uniform":
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    else:
        # Quantile bin edges based on sample percentiles
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.percentile(y_prob_arr, quantiles * 100)
        bin_edges[0] = 0.0
        bin_edges[-1] = 1.0

    bins_list: List[CalibrationBin] = []
    weighted_abs_errors: List[float] = []
    abs_errors: List[float] = []

    # Map samples to bins
    bin_assignments = np.digitize(y_prob_arr, bin_edges[1:-1])

    for i in range(len(frac_pos)):
        pred_p = float(mean_pred[i])
        emp_p = float(frac_pos[i])
        abs_err = abs(pred_p - emp_p)

        # Approximate bin bounds
        p_min = float(bin_edges[i])
        p_max = float(bin_edges[i + 1])

        # Find count of samples falling in this bin
        # We match based on closest mean_pred or bin assignments
        mask = (y_prob_arr >= p_min) & (y_prob_arr <= p_max) if i == len(frac_pos) - 1 else (y_prob_arr >= p_min) & (y_prob_arr < p_max)
        count = int(np.sum(mask))
        if count == 0:
            count = 1  # Fallback guard

        bins_list.append(
            CalibrationBin(
                bin_index=i,
                prob_min=round(p_min, 4),
                prob_max=round(p_max, 4),
                mean_predicted_prob=round(pred_p, 4),
                empirical_fraction_positives=round(emp_p, 4),
                sample_count=count,
                absolute_error=round(abs_err, 4),
            )
        )
        weighted_abs_errors.append((count / total_samples) * abs_err)
        abs_errors.append(abs_err)

    ece = float(sum(weighted_abs_errors)) if weighted_abs_errors else 0.0
    mce = float(max(abs_errors)) if abs_errors else 0.0

    return CalibrationResult(
        brier_score=round(brier, 4),
        expected_calibration_error=round(ece, 4),
        maximum_calibration_error=round(mce, 4),
        n_bins_requested=n_bins,
        n_bins_populated=len(frac_pos),
        strategy=strategy,
        bins=bins_list,
    )
