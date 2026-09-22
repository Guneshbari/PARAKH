"""Core classification evaluation metrics for PARAKH credit risk assessment.

Implements probability-based and threshold-based metrics with robust edge-case handling
(e.g., single-class subsets, extreme class imbalance, zero denominator scenarios).
"""
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence, Union
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class ClassificationMetrics:
    """Structured evaluation metrics container for binary credit risk models."""

    # Probability-based metrics (independent of decision threshold)
    roc_auc: Optional[float]
    pr_auc: Optional[float]
    brier_score: Optional[float]

    # Threshold-based metrics
    threshold: float
    precision: float
    recall: float
    f1: float

    # Confusion matrix components
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    # Sample statistics
    total_samples: int
    positive_samples: int
    negative_samples: int
    positive_rate: float

    # Audit & diagnostics
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a JSON-serializable dictionary."""
        return asdict(self)


def evaluate_predictions(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob: Union[Sequence[float], np.ndarray],
    threshold: float = 0.5,
) -> ClassificationMetrics:
    """Calculate comprehensive credit risk classification metrics.

    Args:
        y_true: Ground truth binary labels (0 = non-default, 1 = default).
        y_prob: Predicted default probabilities bounded in [0.0, 1.0].
        threshold: Decision threshold for threshold-based metrics (default 0.5).

    Returns:
        ClassificationMetrics: Structured container with probability and threshold metrics.

    Raises:
        ValueError: If inputs are empty or lengths do not match.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    if len(y_true_arr) == 0:
        raise ValueError("y_true and y_prob must not be empty.")
    if len(y_true_arr) != len(y_prob_arr):
        raise ValueError(
            f"Length mismatch: len(y_true)={len(y_true_arr)} != len(y_prob)={len(y_prob_arr)}"
        )
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"Threshold must be in [0.0, 1.0], got {threshold}")

    # Clip probabilities to [0, 1] to guard against numerical overflow
    y_prob_arr = np.clip(y_prob_arr, 0.0, 1.0)

    total_samples = int(len(y_true_arr))
    unique_classes = np.unique(y_true_arr)
    positive_samples = int(np.sum(y_true_arr == 1))
    negative_samples = int(np.sum(y_true_arr == 0))
    positive_rate = float(positive_samples / total_samples) if total_samples > 0 else 0.0

    notes_list = []

    # Probability-based metrics (Brier score is always defined)
    brier: Optional[float] = float(brier_score_loss(y_true_arr, y_prob_arr))

    # ROC-AUC and PR-AUC require at least two distinct classes
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None

    if len(unique_classes) < 2:
        notes_list.append(
            f"Single-class evaluation: only class {unique_classes[0]} present. "
            "ROC-AUC and PR-AUC are undefined."
        )
    else:
        try:
            roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
        except ValueError as err:
            notes_list.append(f"ROC-AUC calculation error: {err}")

        try:
            pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
        except ValueError as err:
            notes_list.append(f"PR-AUC calculation error: {err}")

    # Threshold-based predictions
    y_pred = (y_prob_arr >= threshold).astype(int)

    # Scikit-learn confusion matrix [[TN, FP], [FN, TP]]
    cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))

    return ClassificationMetrics(
        roc_auc=round(roc_auc, 4) if roc_auc is not None else None,
        pr_auc=round(pr_auc, 4) if pr_auc is not None else None,
        brier_score=round(brier, 4) if brier is not None else None,
        threshold=round(float(threshold), 4),
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1=round(f1, 4),
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        total_samples=total_samples,
        positive_samples=positive_samples,
        negative_samples=negative_samples,
        positive_rate=round(positive_rate, 4),
        notes="; ".join(notes_list) if notes_list else None,
    )
