"""Fairness and subgroup auditing framework for PARAKH credit risk assessment.

Supports auditing algorithmic parity and performance parity across approved operational
subgroups (gig work sector, tenure cohort, income tier) without inferring personal protected characteristics.
Includes explicit disclaimers regarding synthetic data limitations.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np


@dataclass
class SubgroupFairnessMetrics:
    """Metrics for an individual operational subgroup."""

    subgroup_name: str
    sample_count: int
    positive_actual_count: int
    negative_actual_count: int
    empirical_default_rate: float
    favorable_prediction_rate: float  # Acceptance rate: fraction predicted as non-default (score >= threshold)
    true_positive_rate: Optional[float]  # Recall for default detection
    false_positive_rate: Optional[float]
    precision: Optional[float]


@dataclass
class FairnessAuditReport:
    """Consolidated fairness audit report across subgroups."""

    subgroup_field: str
    subgroups: Dict[str, SubgroupFairnessMetrics]
    demographic_parity_ratio: Optional[float]
    equal_opportunity_difference: Optional[float]
    limitations_disclaimer: str
    audit_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        d = asdict(self)
        d["subgroups"] = {k: asdict(v) for k, v in self.subgroups.items()}
        return d


def audit_subgroup_fairness(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob: Union[Sequence[float], np.ndarray],
    subgroups: Sequence[str],
    subgroup_field_name: str = "gig_work_type",
    threshold: float = 0.5,
) -> FairnessAuditReport:
    """Audit algorithmic fairness metrics across approved operational subgroups.

    Args:
        y_true: Binary repayment outcomes (0 = repaid, 1 = default).
        y_prob: Predicted default probabilities.
        subgroups: Sequence of subgroup identifiers matching y_true.
        subgroup_field_name: Name of the operational grouping field (e.g. 'gig_work_type').
        threshold: Decision threshold for classification into default vs. non-default.

    Returns:
        FairnessAuditReport: Subgroup statistics and parity ratios.

    Raises:
        ValueError: If array lengths do not match or arrays are empty.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    subgroups_arr = np.asarray(subgroups, dtype=str)

    n_samples = len(y_true_arr)
    if n_samples == 0:
        raise ValueError("Inputs cannot be empty.")
    if len(y_prob_arr) != n_samples or len(subgroups_arr) != n_samples:
        raise ValueError("Length mismatch between inputs.")

    # Binary prediction: 1 = default predicted, 0 = non-default (favorable) predicted
    y_pred = (y_prob_arr >= threshold).astype(int)

    unique_subgroups = sorted(list(set(subgroups_arr)))
    subgroup_metrics_dict: Dict[str, SubgroupFairnessMetrics] = {}
    favorable_rates: List[float] = []
    tpr_rates: List[float] = []

    for group_val in unique_subgroups:
        mask = (subgroups_arr == group_val)
        g_true = y_true_arr[mask]
        g_prob = y_prob_arr[mask]
        g_pred = y_pred[mask]

        g_count = len(g_true)
        g_pos = int(np.sum(g_true == 1))
        g_neg = int(np.sum(g_true == 0))
        g_def_rate = float(g_pos / g_count) if g_count > 0 else 0.0

        # Favorable outcome is non-default prediction (y_pred == 0)
        favorable_count = int(np.sum(g_pred == 0))
        fav_rate = float(favorable_count / g_count) if g_count > 0 else 0.0
        favorable_rates.append(fav_rate)

        # True positive rate (Recall for default: predicted default among actual defaults)
        tpr: Optional[float] = None
        if g_pos > 0:
            tp = int(np.sum((g_pred == 1) & (g_true == 1)))
            tpr = float(tp / g_pos)
            tpr_rates.append(tpr)

        # False positive rate (predicted default among actual non-defaults)
        fpr: Optional[float] = None
        if g_neg > 0:
            fp = int(np.sum((g_pred == 1) & (g_true == 0)))
            fpr = float(fp / g_neg)

        # Precision (actual defaults among predicted defaults)
        prec: Optional[float] = None
        pred_pos_count = int(np.sum(g_pred == 1))
        if pred_pos_count > 0:
            tp = int(np.sum((g_pred == 1) & (g_true == 1)))
            prec = float(tp / pred_pos_count)

        subgroup_metrics_dict[group_val] = SubgroupFairnessMetrics(
            subgroup_name=group_val,
            sample_count=g_count,
            positive_actual_count=g_pos,
            negative_actual_count=g_neg,
            empirical_default_rate=round(g_def_rate, 4),
            favorable_prediction_rate=round(fav_rate, 4),
            true_positive_rate=round(tpr, 4) if tpr is not None else None,
            false_positive_rate=round(fpr, 4) if fpr is not None else None,
            precision=round(prec, 4) if prec is not None else None,
        )

    # Demographic Parity Ratio: min(favorable_rate) / max(favorable_rate)
    dpr: Optional[float] = None
    if favorable_rates and max(favorable_rates) > 0:
        dpr = round(float(min(favorable_rates) / max(favorable_rates)), 4)

    # Equal Opportunity Difference: max(TPR) - min(TPR) across groups
    eod: Optional[float] = None
    if len(tpr_rates) >= 2:
        eod = round(float(max(tpr_rates) - min(tpr_rates)), 4)

    disclaimer = (
        "IMPORTANT LIMITATION: Fairness metrics calculated on synthetic benchmark data evaluate "
        "algorithmic pipeline consistency across simulated cohorts. They DO NOT prove real-world fairness "
        "in human populations, which requires validation on representative empirical populations."
    )

    notes = [
        f"Audited {len(unique_subgroups)} distinct subgroups for field '{subgroup_field_name}'.",
        "Subgroup definitions are restricted to approved operational variables (e.g. gig work type, tenure).",
        "No protected personal characteristics (gender, religion, ethnicity) are collected or inferred.",
    ]

    return FairnessAuditReport(
        subgroup_field=subgroup_field_name,
        subgroups=subgroup_metrics_dict,
        demographic_parity_ratio=dpr,
        equal_opportunity_difference=eod,
        limitations_disclaimer=disclaimer,
        audit_notes=notes,
    )
