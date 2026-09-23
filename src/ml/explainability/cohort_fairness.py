"""Subgroup and cohort fairness auditing framework for PARAKH credit risk models.

Computes selection rates, true positive rates, false positive rates, precision,
Brier score, and parity ratios across borrower behavioral cohorts, gig work sectors,
loan purposes, and income tiers. Evaluates both the Phase 5 baseline and Phase 6
volatility-aware model under strict ethical constraints.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

FAIRNESS_SYNTHETIC_DATA_DISCLAIMER = (
    "IMPORTANT REGULATORY & FAIRNESS NOTICE: The evaluation dataset is entirely synthetic and does "
    "not contain real-world legally protected demographic attributes (e.g., race, gender, religion, national "
    "origin, age). Subgroup divisions represent synthetic behavioral cohorts and simulated platform metadata. "
    "Observed disparities reflect intentionally designed synthetic population profiles and do not demonstrate "
    "real-world demographic fairness or compliance with statutory lending fairness standards (e.g., ECOA, FHA). "
    "Rigorous empirical fair-lending testing requires representative population data with audited demographic attributes."
)


@dataclass
class SegmentFairnessMetrics:
    """Detailed fairness and performance metrics for a single operational subgroup."""

    subgroup_name: str
    sample_count: int
    positive_actual_count: int
    negative_actual_count: int
    empirical_default_rate: float
    predicted_positive_count: int  # Flagged as default (y_pred == 1)
    predicted_negative_count: int  # Favorable outcome / non-default (y_pred == 0)
    selection_rate: float  # Selection rate = fraction predicted as default
    favorable_rate: float  # Favorable / approval rate = fraction predicted as non-default
    true_positive_rate: Optional[float]  # Recall
    false_positive_rate: Optional[float]
    precision: Optional[float]
    f1_score: Optional[float]
    brier_score: Optional[float]
    roc_auc: Optional[float]
    pr_auc: Optional[float]
    small_sample_flag: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


@dataclass
class MultiModelFairnessReport:
    """Consolidated fairness audit comparing multiple models across a segment field."""

    segment_field: str
    baseline_subgroups: Dict[str, SegmentFairnessMetrics]
    volatility_aware_subgroups: Dict[str, SegmentFairnessMetrics]
    baseline_demographic_parity_ratio: Optional[float]
    volatility_aware_demographic_parity_ratio: Optional[float]
    baseline_equal_opportunity_diff: Optional[float]
    volatility_aware_equal_opportunity_diff: Optional[float]
    threshold_used: float = 0.50
    disclaimer: str = FAIRNESS_SYNTHETIC_DATA_DISCLAIMER
    observations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "segment_field": self.segment_field,
            "threshold_used": self.threshold_used,
            "baseline_demographic_parity_ratio": self.baseline_demographic_parity_ratio,
            "volatility_aware_demographic_parity_ratio": self.volatility_aware_demographic_parity_ratio,
            "baseline_equal_opportunity_diff": self.baseline_equal_opportunity_diff,
            "volatility_aware_equal_opportunity_diff": self.volatility_aware_equal_opportunity_diff,
            "disclaimer": self.disclaimer,
            "observations": self.observations,
            "baseline_subgroups": {k: v.to_dict() for k, v in self.baseline_subgroups.items()},
            "volatility_aware_subgroups": {k: v.to_dict() for k, v in self.volatility_aware_subgroups.items()},
        }


def compute_subgroup_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    subgroups: Sequence[str],
    threshold: float = 0.50,
    min_samples_for_auc: int = 10,
) -> Dict[str, SegmentFairnessMetrics]:
    """Calculate fairness and performance metrics partitioned by subgroup.

    Args:
        y_true: Binary ground truth labels (0 = repaid, 1 = default).
        y_prob: Predicted default probabilities.
        subgroups: Sequence of subgroup identifiers matching y_true length.
        threshold: Diagnostic decision threshold (default 0.50).
        min_samples_for_auc: Minimum sample size required to report AUC metrics.

    Returns:
        Dict[str, SegmentFairnessMetrics]: Mapping from subgroup identifier to metrics.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    subgroups_arr = np.asarray(subgroups, dtype=str)

    y_pred_arr = (y_prob_arr >= threshold).astype(int)
    unique_groups = sorted(list(set(subgroups_arr)))
    results: Dict[str, SegmentFairnessMetrics] = {}

    for grp in unique_groups:
        mask = (subgroups_arr == grp)
        g_true = y_true_arr[mask]
        g_prob = y_prob_arr[mask]
        g_pred = y_pred_arr[mask]

        count = len(g_true)
        pos = int(np.sum(g_true == 1))
        neg = int(np.sum(g_true == 0))
        def_rate = float(pos / count) if count > 0 else 0.0

        pred_pos = int(np.sum(g_pred == 1))
        pred_neg = int(np.sum(g_pred == 0))
        sel_rate = float(pred_pos / count) if count > 0 else 0.0
        fav_rate = float(pred_neg / count) if count > 0 else 0.0

        tp = int(np.sum((g_true == 1) & (g_pred == 1)))
        fp = int(np.sum((g_true == 0) & (g_pred == 1)))
        tn = int(np.sum((g_true == 0) & (g_pred == 0)))
        fn = int(np.sum((g_true == 1) & (g_pred == 0)))

        tpr = float(tp / pos) if pos > 0 else None
        fpr = float(fp / neg) if neg > 0 else None
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else None
        f1 = (
            float(2 * precision * tpr / (precision + tpr))
            if (precision is not None and tpr is not None and (precision + tpr) > 0)
            else None
        )

        brier = float(brier_score_loss(g_true, g_prob)) if count > 0 else None

        roc_auc = None
        pr_auc = None
        if count >= min_samples_for_auc and pos > 0 and neg > 0:
            try:
                roc_auc = float(roc_auc_score(g_true, g_prob))
                pr_auc = float(average_precision_score(g_true, g_prob))
            except Exception:
                roc_auc = None
                pr_auc = None

        small_sample = (count < 30) or (pos < 5)

        results[grp] = SegmentFairnessMetrics(
            subgroup_name=grp,
            sample_count=count,
            positive_actual_count=pos,
            negative_actual_count=neg,
            empirical_default_rate=round(def_rate, 4),
            predicted_positive_count=pred_pos,
            predicted_negative_count=pred_neg,
            selection_rate=round(sel_rate, 4),
            favorable_rate=round(fav_rate, 4),
            true_positive_rate=round(tpr, 4) if tpr is not None else None,
            false_positive_rate=round(fpr, 4) if fpr is not None else None,
            precision=round(precision, 4) if precision is not None else None,
            f1_score=round(f1, 4) if f1 is not None else None,
            brier_score=round(brier, 4) if brier is not None else None,
            roc_auc=round(roc_auc, 4) if roc_auc is not None else None,
            pr_auc=round(pr_auc, 4) if pr_auc is not None else None,
            small_sample_flag=small_sample,
        )

    return results


def audit_comparative_fairness(
    y_true: np.ndarray,
    baseline_probs: np.ndarray,
    volatility_probs: np.ndarray,
    subgroups: Sequence[str],
    segment_field_name: str,
    threshold: float = 0.50,
) -> MultiModelFairnessReport:
    """Audit and compare fairness metrics between baseline and volatility-aware models.

    Args:
        y_true: Ground truth binary labels.
        baseline_probs: Predicted probabilities from Phase 5 baseline model.
        volatility_probs: Predicted probabilities from Phase 6 volatility-aware model.
        subgroups: Subgroup labels.
        segment_field_name: Name of segmentation variable (e.g. 'cohort_archetype').
        threshold: Decision cutoff (default 0.50).

    Returns:
        MultiModelFairnessReport: Structured comparative report with parity ratios.
    """
    b_metrics = compute_subgroup_metrics(y_true, baseline_probs, subgroups, threshold=threshold)
    v_metrics = compute_subgroup_metrics(y_true, volatility_probs, subgroups, threshold=threshold)

    # Compute Demographic Parity Ratio (min approval rate / max approval rate)
    b_favs = [m.favorable_rate for m in b_metrics.values() if m.sample_count >= 10]
    v_favs = [m.favorable_rate for m in v_metrics.values() if m.sample_count >= 10]

    b_dpr = (min(b_favs) / max(b_favs)) if (b_favs and max(b_favs) > 0) else None
    v_dpr = (min(v_favs) / max(v_favs)) if (v_favs and max(v_favs) > 0) else None

    # Compute Equal Opportunity Difference (max TPR - min TPR among valid groups)
    b_tprs = [m.true_positive_rate for m in b_metrics.values() if m.true_positive_rate is not None and not m.small_sample_flag]
    v_tprs = [m.true_positive_rate for m in v_metrics.values() if m.true_positive_rate is not None and not m.small_sample_flag]

    b_eod = (max(b_tprs) - min(b_tprs)) if len(b_tprs) >= 2 else None
    v_eod = (max(v_tprs) - min(v_tprs)) if len(v_tprs) >= 2 else None

    observations = [
        f"Segment '{segment_field_name}' evaluated across {len(b_metrics)} distinct groups.",
        f"Baseline Demographic Parity Ratio: {round(b_dpr, 4) if b_dpr is not None else 'N/A'}; "
        f"Volatility-Aware DPR: {round(v_dpr, 4) if v_dpr is not None else 'N/A'}.",
        f"Baseline Equal Opportunity Diff: {round(b_eod, 4) if b_eod is not None else 'N/A'}; "
        f"Volatility-Aware EOD: {round(v_eod, 4) if v_eod is not None else 'N/A'}.",
    ]

    return MultiModelFairnessReport(
        segment_field=segment_field_name,
        baseline_subgroups=b_metrics,
        volatility_aware_subgroups=v_metrics,
        baseline_demographic_parity_ratio=round(b_dpr, 4) if b_dpr is not None else None,
        volatility_aware_demographic_parity_ratio=round(v_dpr, 4) if v_dpr is not None else None,
        baseline_equal_opportunity_diff=round(b_eod, 4) if b_eod is not None else None,
        volatility_aware_equal_opportunity_diff=round(v_eod, 4) if v_eod is not None else None,
        threshold_used=threshold,
        observations=observations,
    )
