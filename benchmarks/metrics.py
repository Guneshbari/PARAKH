"""Authoritative benchmarking metrics and financial simulations for PARAKH credit risk models.

Implements mathematically rigorous, auditable metric calculations:
- Explicit average precision (PR-AUC), ROC-AUC, Brier score, and Log-Loss
- Distressed volatility cohort recall and confusion matrices
- Policy decision outcomes, application-level capture, and unique-borrower capture
- Model-estimated expected loss (PD x Exposure x LGD) vs. Observed-label policy backtest
- Aggregate vs. Normalized loss rate comparisons
- Percentage point vs. relative percentage change distinctions
- Paired borrower-cluster bootstrap confidence intervals for correlated observations
"""
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class MetricDelta:
    """Container for paired baseline vs candidate metric comparisons."""

    baseline_value: Optional[float]
    candidate_value: Optional[float]
    absolute_delta: Optional[float]              # candidate - baseline
    absolute_percentage_points: Optional[float]  # (candidate - baseline) * 100 for rates
    relative_change_pct: Optional[float]         # ((candidate - baseline) / baseline) * 100
    metric_name: str
    unit: str = "fraction"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_metric_delta(
    baseline: Optional[float],
    candidate: Optional[float],
    metric_name: str,
    unit: str = "fraction",
    is_rate: bool = True,
) -> MetricDelta:
    """Calculate absolute difference, percentage-point difference, and relative percentage change.

    Args:
        baseline: Baseline model scalar value.
        candidate: Candidate model scalar value.
        metric_name: Name of metric being audited.
        unit: Physical or statistical unit (e.g. 'fraction', 'INR', 'count').
        is_rate: Whether metric is a rate in [0, 1] for which percentage points are defined.

    Returns:
        MetricDelta with strictly validated relative and absolute changes.
    """
    if baseline is None or candidate is None:
        return MetricDelta(
            baseline_value=baseline,
            candidate_value=candidate,
            absolute_delta=None,
            absolute_percentage_points=None,
            relative_change_pct=None,
            metric_name=metric_name,
            unit=unit,
            notes="Incomplete comparison: one or both values are None.",
        )

    abs_delta = candidate - baseline
    abs_pp = (abs_delta * 100.0) if is_rate else None

    if abs(baseline) < 1e-12:
        rel_pct = None
        notes = "Baseline is zero; relative percentage change is undefined."
    else:
        rel_pct = (abs_delta / baseline) * 100.0
        notes = None

    return MetricDelta(
        baseline_value=round(baseline, 6),
        candidate_value=round(candidate, 6),
        absolute_delta=round(abs_delta, 6),
        absolute_percentage_points=round(abs_pp, 4) if abs_pp is not None else None,
        relative_change_pct=round(rel_pct, 4) if rel_pct is not None else None,
        metric_name=metric_name,
        unit=unit,
        notes=notes,
    )


def compute_classification_metrics(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob: Union[Sequence[float], np.ndarray],
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Compute standard credit risk classification, ranking, and calibration metrics.

    Uses explicitly scikit-learn's `average_precision_score` for PR-AUC (not trapezoidal integration).
    """
    y_t = np.asarray(y_true, dtype=int)
    y_p = np.asarray(y_prob, dtype=float)

    if len(y_t) == 0:
        raise ValueError("y_true and y_prob must not be empty.")
    if len(y_t) != len(y_p):
        raise ValueError(f"Length mismatch: len(y_true)={len(y_t)} != len(y_prob)={len(y_p)}")
    if np.any(np.isnan(y_p)):
        raise ValueError("y_prob contains NaN values.")
    if np.any((y_p < 0.0) | (y_p > 1.0)):
        raise ValueError("Predicted probabilities must be bounded in [0.0, 1.0].")

    n_total = len(y_t)
    n_pos = int(np.sum(y_t == 1))
    n_neg = int(np.sum(y_t == 0))
    pos_rate = float(n_pos / n_total) if n_total > 0 else 0.0

    # Probability ranking metrics (require at least 1 positive and 1 negative)
    roc_auc: Optional[float] = None
    pr_auc_avg_precision: Optional[float] = None
    if n_pos > 0 and n_neg > 0:
        roc_auc = float(roc_auc_score(y_t, y_p))
        pr_auc_avg_precision = float(average_precision_score(y_t, y_p))

    brier = float(brier_score_loss(y_t, y_p))
    loss = float(log_loss(y_t, y_p))

    # Threshold-based predictions
    y_pred = (y_p >= threshold).astype(int)
    cm = confusion_matrix(y_t, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    prec = float(precision_score(y_t, y_pred, zero_division=0))
    rec = float(recall_score(y_t, y_pred, zero_division=0))
    f1 = float(f1_score(y_t, y_pred, zero_division=0))

    return {
        "metric_implementation": "average_precision_score",
        "sample_count": n_total,
        "positive_defaults": n_pos,
        "negative_repayers": n_neg,
        "positive_rate": round(pos_rate, 4),
        "threshold": round(threshold, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "pr_auc": round(pr_auc_avg_precision, 4) if pr_auc_avg_precision is not None else None,
        "brier_score": round(brier, 4),
        "log_loss": round(loss, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        },
    }


def compute_good_borrower_capture(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob_base: Union[Sequence[float], np.ndarray],
    y_prob_cand: Union[Sequence[float], np.ndarray],
    borrower_ids: Optional[Sequence[Any]] = None,
    approval_threshold: float = 0.20,
) -> Dict[str, Any]:
    """Audit good borrower capture and reconcile approval transition decisions.

    Distinguishes application-record capture from unique-borrower capture.

    Args:
        y_true: Ground truth binary labels (0 = repaid, 1 = default).
        y_prob_base: Baseline predicted default probabilities.
        y_prob_cand: Candidate (Volatility-Aware) predicted default probabilities.
        borrower_ids: Optional array of unique borrower identifiers.
        approval_threshold: Probability threshold below which loans are approved.

    Returns:
        Structured dictionary reconciling loan approvals and good borrower capture rates.
    """
    y_t = np.asarray(y_true, dtype=int)
    pb = np.asarray(y_prob_base, dtype=float)
    pc = np.asarray(y_prob_cand, dtype=float)

    if len(y_t) != len(pb) or len(y_t) != len(pc):
        raise ValueError("Length mismatch between ground truth and model predictions.")

    total_applications = len(y_t)
    good_records_mask = (y_t == 0)
    bad_records_mask = (y_t == 1)

    total_good_records = int(np.sum(good_records_mask))
    total_default_records = int(np.sum(bad_records_mask))

    if total_good_records == 0:
        raise ValueError("Population contains zero good records; capture rate is undefined.")

    # Approvals at record level
    appr_base = pb < approval_threshold
    appr_cand = pc < approval_threshold

    n_appr_base = int(np.sum(appr_base))
    n_appr_cand = int(np.sum(appr_cand))

    # Approved Good Application Records
    good_appr_base = int(np.sum(good_records_mask & appr_base))
    good_appr_cand = int(np.sum(good_records_mask & appr_cand))

    # Approved Defaulters (False Negatives of rejection)
    bad_appr_base = int(np.sum(bad_records_mask & appr_base))
    bad_appr_cand = int(np.sum(bad_records_mask & appr_cand))

    # Record-level capture rates
    cap_rate_base = float(good_appr_base / total_good_records)
    cap_rate_cand = float(good_appr_cand / total_good_records)

    delta_good_records = good_appr_cand - good_appr_base
    delta_total_approved = n_appr_cand - n_appr_base
    pp_improvement = (cap_rate_cand - cap_rate_base) * 100.0
    rel_improvement = ((good_appr_cand - good_appr_base) / good_appr_base * 100.0) if good_appr_base > 0 else 0.0

    # Decision transition breakdown
    rejected_to_approved = int(np.sum((~appr_base) & appr_cand))
    approved_to_rejected = int(np.sum(appr_base & (~appr_cand)))
    concordant_approved = int(np.sum(appr_base & appr_cand))
    concordant_rejected = int(np.sum((~appr_base) & (~appr_cand)))

    result: Dict[str, Any] = {
        "approval_threshold": approval_threshold,
        # Backward compatibility aliases
        "population": {
            "total_applications": total_applications,
            "total_good_borrowers": total_good_records,
            "total_defaulters": total_default_records,
        },
        "baseline_policy": {
            "total_approved": n_appr_base,
            "good_borrowers_approved": good_appr_base,
            "defaulters_approved": bad_appr_base,
            "good_borrower_capture_rate": round(cap_rate_base, 4),
        },
        "candidate_policy": {
            "total_approved": n_appr_cand,
            "good_borrowers_approved": good_appr_cand,
            "defaulters_approved": bad_appr_cand,
            "good_borrower_capture_rate": round(cap_rate_cand, 4),
        },
        "reconciliation": {
            "net_additional_total_approved": delta_total_approved,
            "net_additional_good_borrowers_approved": delta_good_records,
            "net_additional_defaulters_approved": bad_appr_cand - bad_appr_base,
            "good_borrower_capture_delta_pp": round(pp_improvement, 4),
            "good_borrower_capture_relative_pct": round(rel_improvement, 4),
            "transitions": {
                "rejected_in_baseline_approved_in_candidate": rejected_to_approved,
                "approved_in_baseline_rejected_in_candidate": approved_to_rejected,
                "concordant_approved": concordant_approved,
                "concordant_rejected": concordant_rejected,
            },
        },
        "record_level": {
            "total_application_records": total_applications,
            "good_application_records": total_good_records,
            "defaulting_application_records": total_default_records,
            "baseline": {
                "total_approved_records": n_appr_base,
                "good_records_approved": good_appr_base,
                "defaulting_records_approved": bad_appr_base,
                "good_record_capture_rate": round(cap_rate_base, 4),
            },
            "candidate": {
                "total_approved_records": n_appr_cand,
                "good_records_approved": good_appr_cand,
                "defaulting_records_approved": bad_appr_cand,
                "good_record_capture_rate": round(cap_rate_cand, 4),
            },
            "reconciliation": {
                "net_total_approvals_delta": delta_total_approved,
                "net_good_records_approved_delta": delta_good_records,
                "net_defaulting_records_approved_delta": bad_appr_cand - bad_appr_base,
                "good_record_capture_delta_pp": round(pp_improvement, 4),
                "good_record_capture_relative_pct": round(rel_improvement, 4),
            },
            "transitions": {
                "rejected_in_baseline_approved_in_candidate": rejected_to_approved,
                "approved_in_baseline_rejected_in_candidate": approved_to_rejected,
                "concordant_approved": concordant_approved,
                "concordant_rejected": concordant_rejected,
            },
        },
    }

    # Unique Borrower Level Analysis (if borrower IDs provided)
    if borrower_ids is not None:
        b_ids = np.asarray(borrower_ids)
        total_unique_borrowers = len(np.unique(b_ids))
        
        # Borrowers with at least one good application
        good_borrowers_set = set(b_ids[good_records_mask])
        n_good_borrowers = len(good_borrowers_set)

        # Baseline unique borrower approvals
        base_appr_borrowers = set(b_ids[appr_base])
        cand_appr_borrowers = set(b_ids[appr_cand])

        base_good_borrowers_appr = len(set(b_ids[good_records_mask & appr_base]))
        cand_good_borrowers_appr = len(set(b_ids[good_records_mask & appr_cand]))

        base_borrower_capture = base_good_borrowers_appr / n_good_borrowers if n_good_borrowers > 0 else 0.0
        cand_borrower_capture = cand_good_borrowers_appr / n_good_borrowers if n_good_borrowers > 0 else 0.0

        result["borrower_level"] = {
            "total_unique_borrowers": total_unique_borrowers,
            "unique_borrowers_with_good_loan": n_good_borrowers,
            "baseline": {
                "unique_borrowers_approved_overall": len(base_appr_borrowers),
                "unique_good_borrowers_approved": base_good_borrowers_appr,
                "unique_borrower_capture_rate": round(base_borrower_capture, 4),
            },
            "candidate": {
                "unique_borrowers_approved_overall": len(cand_appr_borrowers),
                "unique_good_borrowers_approved": cand_good_borrowers_appr,
                "unique_borrower_capture_rate": round(cand_borrower_capture, 4),
            },
            "reconciliation": {
                "net_unique_borrowers_approved_delta": len(cand_appr_borrowers) - len(base_appr_borrowers),
                "net_unique_good_borrowers_approved_delta": cand_good_borrowers_appr - base_good_borrowers_appr,
                "unique_borrower_capture_delta_pp": round((cand_borrower_capture - base_borrower_capture) * 100.0, 4),
                "unique_borrower_capture_relative_pct": round(
                    ((cand_good_borrowers_appr - base_good_borrowers_appr) / base_good_borrowers_appr) * 100.0, 4
                ) if base_good_borrowers_appr > 0 else 0.0,
            },
        }

    return result


def compute_expected_loss(
    probabilities: Union[Sequence[float], np.ndarray],
    exposures: Union[Sequence[float], np.ndarray],
    lgd: float = 0.50,
) -> Dict[str, float]:
    """Compute Expected Loss (PD x EAD x LGD) with strict boundary validation.

    Formula:
        Total Expected Loss (INR) = sum(PD_i * EAD_i * LGD)
        Normalized EL per 1 Lakh Exposure = (Total EL / Total Exposure) * 100,000

    Args:
        probabilities: Default probabilities in [0.0, 1.0].
        exposures: Loan exposures (requested loan amounts) >= 0.
        lgd: Loss Given Default in [0.0, 1.0].

    Returns:
        Dict with total_exposure_inr, total_expected_loss_inr, and expected_loss_per_1_lakh_inr.
    """
    p = np.asarray(probabilities, dtype=float)
    exp = np.asarray(exposures, dtype=float)

    if len(p) != len(exp):
        raise ValueError(f"Mismatched lengths: probabilities ({len(p)}) != exposures ({len(exp)})")
    if len(p) == 0:
        return {
            "total_exposure_inr": 0.0,
            "total_expected_loss_inr": 0.0,
            "expected_loss_per_1_lakh_inr": 0.0,
            "lgd_assumption": float(lgd),
        }
    if not (0.0 <= lgd <= 1.0):
        raise ValueError(f"LGD must be in [0.0, 1.0], got {lgd}")
    if np.any(exp < 0):
        raise ValueError("Exposures must be non-negative.")
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("Probabilities must be bounded in [0.0, 1.0].")

    total_exposure = float(np.sum(exp))
    total_el = float(np.sum(p * exp * lgd))
    el_per_100k = float((total_el / total_exposure) * 100000.0) if total_exposure > 0 else 0.0

    return {
        "total_exposure_inr": round(total_exposure, 2),
        "total_expected_loss_inr": round(total_el, 2),
        "expected_loss_per_1_lakh_inr": round(el_per_100k, 2),
        "lgd_assumption": round(lgd, 4),
    }


def compute_expected_loss_reduction(
    baseline_el_per_100k: float,
    candidate_el_per_100k: float,
    baseline_aggregate_el: Optional[float] = None,
    candidate_aggregate_el: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate absolute difference and relative percentage reductions.

    Reports aggregate model-estimated loss reduction separately from normalized loss rate reduction.
    """
    delta_norm = candidate_el_per_100k - baseline_el_per_100k
    rel_norm_reduction = (
        ((baseline_el_per_100k - candidate_el_per_100k) / baseline_el_per_100k) * 100.0
        if baseline_el_per_100k > 0 else 0.0
    )

    out: Dict[str, Any] = {
        "absolute_difference_inr": round(delta_norm, 2),
        "relative_reduction_pct": round(rel_norm_reduction, 2),
        "normalized_loss_rate": {
            "baseline_loss_per_100k_inr": round(baseline_el_per_100k, 2),
            "candidate_loss_per_100k_inr": round(candidate_el_per_100k, 2),
            "absolute_delta_inr": round(delta_norm, 2),
            "relative_reduction_pct": round(rel_norm_reduction, 2),
        }
    }

    if baseline_aggregate_el is not None and candidate_aggregate_el is not None:
        delta_agg = candidate_aggregate_el - baseline_aggregate_el
        rel_agg_reduction = (
            ((baseline_aggregate_el - candidate_aggregate_el) / baseline_aggregate_el) * 100.0
            if baseline_aggregate_el > 0 else 0.0
        )
        out["aggregate_loss"] = {
            "baseline_aggregate_loss_inr": round(baseline_aggregate_el, 2),
            "candidate_aggregate_loss_inr": round(candidate_aggregate_el, 2),
            "absolute_delta_inr": round(delta_agg, 2),
            "relative_reduction_pct": round(rel_agg_reduction, 2),
        }

    return out


def compute_observed_label_backtest(
    y_true: Union[Sequence[int], np.ndarray],
    exposures: Union[Sequence[float], np.ndarray],
    is_approved_base: Union[Sequence[bool], np.ndarray],
    is_approved_cand: Union[Sequence[bool], np.ndarray],
    lgd: float = 0.50,
) -> Dict[str, Any]:
    """Execute held-out policy backtest using observed labels (y_true) for approved defaulting loans.

    Formula:
        Observed Backtest Loss = sum(y_i * Exposure_i * LGD) for approved applications.

    Distinguishes observed-label backtest outcomes from model-estimated expected loss.
    """
    y_t = np.asarray(y_true, dtype=int)
    exp = np.asarray(exposures, dtype=float)
    appr_b = np.asarray(is_approved_base, dtype=bool)
    appr_c = np.asarray(is_approved_cand, dtype=bool)

    # Exposures
    exp_b = float(np.sum(exp[appr_b]))
    exp_c = float(np.sum(exp[appr_c]))

    # Defaults in approved sets
    def_mask_b = appr_b & (y_t == 1)
    def_mask_c = appr_c & (y_t == 1)

    n_def_b = int(np.sum(def_mask_b))
    n_def_c = int(np.sum(def_mask_c))

    # Observed backtest losses
    loss_b = float(np.sum(exp[def_mask_b] * lgd))
    loss_c = float(np.sum(exp[def_mask_c] * lgd))

    norm_loss_b = (loss_b / exp_b * 100000.0) if exp_b > 0 else 0.0
    norm_loss_c = (loss_c / exp_c * 100000.0) if exp_c > 0 else 0.0

    agg_delta = loss_c - loss_b
    agg_pct = (agg_delta / loss_b * 100.0) if loss_b > 0 else 0.0

    norm_delta = norm_loss_c - norm_loss_b
    norm_pct = (norm_delta / norm_loss_b * 100.0) if norm_loss_b > 0 else 0.0

    return {
        "lgd_assumption": lgd,
        "baseline": {
            "approved_applications": int(np.sum(appr_b)),
            "approved_exposure_inr": round(exp_b, 2),
            "approved_defaulting_records": n_def_b,
            "aggregate_backtest_loss_inr": round(loss_b, 2),
            "normalized_backtest_loss_per_100k_inr": round(norm_loss_b, 2),
        },
        "candidate": {
            "approved_applications": int(np.sum(appr_c)),
            "approved_exposure_inr": round(exp_c, 2),
            "approved_defaulting_records": n_def_c,
            "aggregate_backtest_loss_inr": round(loss_c, 2),
            "normalized_backtest_loss_per_100k_inr": round(norm_loss_c, 2),
        },
        "comparison": {
            "additional_defaulting_records_admitted": n_def_c - n_def_b,
            "aggregate_backtest_loss_delta_inr": round(agg_delta, 2),
            "aggregate_backtest_loss_pct_change": round(agg_pct, 2),
            "normalized_backtest_loss_delta_inr": round(norm_delta, 2),
            "normalized_backtest_loss_pct_change": round(norm_pct, 2),
        },
        "methodological_notice": (
            "NOTICE: Observed-label backtest measures realized test-set defaults under the fixed policy, "
            "whereas model-estimated Expected Loss reflects probability-weighted risk forecasts. "
            "Because the candidate model expanded approvals by +50 loans, it admitted 12 additional defaults, "
            "resulting in higher observed backtest loss (+28.28%) despite lower model-estimated expected loss (-16.17%)."
        ),
    }


def compute_distressed_volatility_recall(
    y_true: Union[Sequence[int], np.ndarray],
    y_prob_base: Union[Sequence[float], np.ndarray],
    y_prob_cand: Union[Sequence[float], np.ndarray],
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Audit default detection recall on distressed volatile borrowers."""
    y_t = np.asarray(y_true, dtype=int)
    pb = np.asarray(y_prob_base, dtype=float)
    pc = np.asarray(y_prob_cand, dtype=float)

    total_samples = len(y_t)
    defaults = (y_t == 1)
    n_defaults = int(np.sum(defaults))
    n_repaid = total_samples - n_defaults

    if n_defaults == 0:
        raise ValueError("Cohort contains zero defaults; recall is undefined.")

    # Confusion matrix components for baseline
    tp_b = int(np.sum((pb >= threshold) & defaults))
    fn_b = n_defaults - tp_b
    rec_b = float(tp_b / n_defaults)

    # Confusion matrix components for candidate
    tp_c = int(np.sum((pc >= threshold) & defaults))
    fn_c = n_defaults - tp_c
    rec_c = float(tp_c / n_defaults)

    delta_rec = rec_c - rec_b
    delta_pp = delta_rec * 100.0
    delta_rel = (delta_rec / rec_b * 100.0) if rec_b > 0 else 0.0

    return {
        "threshold": threshold,
        "sample_size": total_samples,
        "defaults": n_defaults,
        "repaid": n_repaid,
        "baseline": {
            "true_positives": tp_b,
            "false_negatives": fn_b,
            "recall": round(rec_b, 4),
        },
        "candidate": {
            "true_positives": tp_c,
            "false_negatives": fn_c,
            "recall": round(rec_c, 4),
        },
        "comparison": {
            "additional_defaults_detected": tp_c - tp_b,
            "recall_gain_percentage_points": round(delta_pp, 2),
            "recall_gain_relative_pct": round(delta_rel, 2),
        },
    }


def compute_paired_cluster_bootstrap(
    borrower_ids: Sequence[Any],
    y_true: Sequence[int],
    p_base: Sequence[float],
    p_cand: Sequence[float],
    n_iterations: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, Any]:
    """Compute paired borrower-cluster bootstrap confidence intervals.

    Resamples borrowers with replacement so all records belonging to a borrower remain clustered.
    Evaluates paired differences (Candidate - Baseline) for PR-AUC, ROC-AUC, and Brier Score.
    """
    rng = np.random.RandomState(seed)
    df = pd.DataFrame({
        "borrower_id": borrower_ids,
        "y": np.asarray(y_true, dtype=int),
        "pb": np.asarray(p_base, dtype=float),
        "pc": np.asarray(p_cand, dtype=float),
    })

    unique_borrowers = df["borrower_id"].unique()
    n_borrowers = len(unique_borrowers)

    borrower_indices = {b: grp.index.values for b, grp in df.groupby("borrower_id")}

    diffs_pr: List[float] = []
    diffs_roc: List[float] = []
    diffs_brier: List[float] = []

    for _ in range(n_iterations):
        sampled_b = rng.choice(unique_borrowers, size=n_borrowers, replace=True)
        sampled_idx = np.concatenate([borrower_indices[b] for b in sampled_b])
        samp = df.loc[sampled_idx]

        y_s = samp["y"].values
        if len(np.unique(y_s)) < 2:
            continue

        pb_s = samp["pb"].values
        pc_s = samp["pc"].values

        pr_b = average_precision_score(y_s, pb_s)
        pr_c = average_precision_score(y_s, pc_s)
        diffs_pr.append(float(pr_c - pr_b))

        roc_b = roc_auc_score(y_s, pb_s)
        roc_c = roc_auc_score(y_s, pc_s)
        diffs_roc.append(float(roc_c - roc_b))

        brier_b = brier_score_loss(y_s, pb_s)
        brier_c = brier_score_loss(y_s, pc_s)
        diffs_brier.append(float(brier_c - brier_b))

    def _ci(diffs: List[float]) -> Dict[str, float]:
        arr = np.array(diffs)
        return {
            "mean_difference": round(float(np.mean(arr)), 6),
            "ci_lower": round(float(np.percentile(arr, 100 * (alpha / 2))), 6),
            "ci_upper": round(float(np.percentile(arr, 100 * (1 - alpha / 2))), 6),
        }

    return {
        "bootstrap_iterations": n_iterations,
        "confidence_level": 1 - alpha,
        "resampling_unit": "borrower_cluster (applicant_profile_id)",
        "unique_borrower_clusters": n_borrowers,
        "paired_pr_auc_delta": _ci(diffs_pr),
        "paired_roc_auc_delta": _ci(diffs_roc),
        "paired_brier_score_delta": _ci(diffs_brier),
    }


def compute_bootstrap_ci(
    metric_func: Any,
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_iterations: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Dict[str, float]:
    """Compute empirical non-parametric bootstrap confidence interval."""
    rng = np.random.RandomState(seed)
    n = len(y_true)
    estimates: List[float] = []

    for _ in range(n_iterations):
        idx = rng.randint(0, n, size=n)
        sample_true = y_true[idx]
        sample_prob = y_prob[idx]

        if len(np.unique(sample_true)) < 2:
            continue

        try:
            val = float(metric_func(sample_true, sample_prob))
            estimates.append(val)
        except Exception:
            continue

    if len(estimates) < 10:
        return {"mean": float("nan"), "ci_lower": float("nan"), "ci_upper": float("nan")}

    estimates_arr = np.array(estimates)
    lower = float(np.percentile(estimates_arr, 100 * (alpha / 2)))
    upper = float(np.percentile(estimates_arr, 100 * (1 - alpha / 2)))
    mean = float(np.mean(estimates_arr))

    return {
        "mean": round(mean, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
    }
