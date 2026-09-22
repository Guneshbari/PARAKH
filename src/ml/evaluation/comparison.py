"""Model comparison framework for testing the PARAKH volatility-aware hypothesis.

Provides structured comparison between:
- Experiment A: Baseline model (standard risk modeling with linear volatility deductions).
- Experiment B: Volatility-aware model (joint conditioning on volatility, recovery, trend, and buffers).

Crucially tracks cohort-level performance on 'Healthy Volatile' and 'Declining'
cohorts to verify whether healthy gig workers are being unfairly penalized.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from src.ml.constants import CohortArchetype, ExperimentVariant
from src.ml.evaluation.tracking import ExperimentMetadata


@dataclass
class CohortDelta:
    """Metric deltas for a specific cohort between baseline and volatility-aware models."""

    cohort_name: str
    sample_count: int
    empirical_default_rate: float
    baseline_default_rate_predicted: Optional[float]
    volatility_aware_default_rate_predicted: Optional[float]
    delta_predicted_default_rate: Optional[float]  # (volatility_aware - baseline)
    delta_roc_auc: Optional[float]
    delta_pr_auc: Optional[float]
    delta_brier: Optional[float]


@dataclass
class ModelComparisonResult:
    """Comprehensive comparison between Baseline (Exp A) and Volatility-Aware (Exp B) models."""

    baseline_id: str
    volatility_aware_id: str

    # Global metric comparisons (volatility_aware - baseline)
    global_metric_deltas: Dict[str, float]

    # Cohort-specific comparisons
    cohort_deltas: Dict[str, CohortDelta]

    # Specific hypothesis testing focus
    healthy_volatile_impact: Dict[str, Any]
    declining_cohort_impact: Dict[str, Any]

    # Overall empirical findings summary
    summary_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison result to dictionary."""
        d = asdict(self)
        d["cohort_deltas"] = {k: asdict(v) for k, v in self.cohort_deltas.items()}
        return d


def compare_models(
    baseline_meta: ExperimentMetadata,
    volatility_aware_meta: ExperimentMetadata,
) -> ModelComparisonResult:
    """Compare baseline and volatility-aware experiment runs empirically.

    Args:
        baseline_meta: Metadata from Experiment A (Baseline).
        volatility_aware_meta: Metadata from Experiment B (Volatility-Aware).

    Returns:
        ModelComparisonResult: Structured comparison focusing on global metrics and cohort impacts.
    """
    base_metrics = baseline_meta.metrics or {}
    vol_metrics = volatility_aware_meta.metrics or {}

    # Calculate global metric deltas (volatility_aware - baseline)
    deltas: Dict[str, float] = {}
    for metric_name in ["roc_auc", "pr_auc", "brier_score", "precision", "recall", "f1"]:
        b_val = base_metrics.get(metric_name)
        v_val = vol_metrics.get(metric_name)
        if b_val is not None and v_val is not None:
            deltas[f"delta_{metric_name}"] = round(float(v_val - b_val), 4)

    # Compare cohort metrics if available
    b_cohorts = baseline_meta.cohort_metrics or {}
    v_cohorts = volatility_aware_meta.cohort_metrics or {}
    cohort_deltas_dict: Dict[str, CohortDelta] = {}

    all_cohort_names = sorted(list(set(b_cohorts.keys()) | set(v_cohorts.keys())))

    for c_name in all_cohort_names:
        b_c = b_cohorts.get(c_name, {})
        v_c = v_cohorts.get(c_name, {})

        b_sample_count = b_c.get("sample_count", 0)
        v_sample_count = v_c.get("sample_count", 0)
        sample_count = max(b_sample_count, v_sample_count)

        emp_rate = b_c.get("empirical_default_rate", v_c.get("empirical_default_rate", 0.0))

        b_m = b_c.get("metrics") or {}
        v_m = v_c.get("metrics") or {}

        delta_roc: Optional[float] = None
        if b_m.get("roc_auc") is not None and v_m.get("roc_auc") is not None:
            delta_roc = round(float(v_m["roc_auc"] - b_m["roc_auc"]), 4)

        delta_pr: Optional[float] = None
        if b_m.get("pr_auc") is not None and v_m.get("pr_auc") is not None:
            delta_pr = round(float(v_m["pr_auc"] - b_m["pr_auc"]), 4)

        delta_brier: Optional[float] = None
        if b_m.get("brier_score") is not None and v_m.get("brier_score") is not None:
            delta_brier = round(float(v_m["brier_score"] - b_m["brier_score"]), 4)

        b_pred_rate = b_m.get("positive_rate")
        v_pred_rate = v_m.get("positive_rate")
        delta_pred_rate: Optional[float] = None
        if b_pred_rate is not None and v_pred_rate is not None:
            delta_pred_rate = round(float(v_pred_rate - b_pred_rate), 4)

        cohort_deltas_dict[c_name] = CohortDelta(
            cohort_name=c_name,
            sample_count=sample_count,
            empirical_default_rate=emp_rate,
            baseline_default_rate_predicted=b_pred_rate,
            volatility_aware_default_rate_predicted=v_pred_rate,
            delta_predicted_default_rate=delta_pred_rate,
            delta_roc_auc=delta_roc,
            delta_pr_auc=delta_pr,
            delta_brier=delta_brier,
        )

    # Focus analysis: Healthy Volatile cohort
    hv_name = CohortArchetype.HEALTHY_VOLATILE.value
    hv_delta = cohort_deltas_dict.get(hv_name)
    healthy_volatile_impact = {
        "cohort_name": hv_name,
        "hypothesis": "Baseline model penalizes healthy volatility as default risk; volatility-aware model recognizes earning resilience and lowers false positive default predictions.",
        "delta_predicted_default_rate": hv_delta.delta_predicted_default_rate if hv_delta else None,
        "delta_brier_score": hv_delta.delta_brier if hv_delta else None,
        "delta_pr_auc": hv_delta.delta_pr_auc if hv_delta else None,
    }

    # Focus analysis: Declining cohort
    dec_name = CohortArchetype.DECLINING.value
    dec_delta = cohort_deltas_dict.get(dec_name)
    declining_cohort_impact = {
        "cohort_name": dec_name,
        "hypothesis": "Volatility-aware model must correctly catch persistent deterioration despite low variance, maintaining high recall on structural default risks.",
        "delta_predicted_default_rate": dec_delta.delta_predicted_default_rate if dec_delta else None,
        "delta_recall": round(
            float(
                (v_cohorts.get(dec_name, {}).get("metrics") or {}).get("recall", 0.0)
                - (b_cohorts.get(dec_name, {}).get("metrics") or {}).get("recall", 0.0)
            ),
            4,
        )
        if dec_name in b_cohorts and dec_name in v_cohorts
        else None,
    }

    notes = [
        "Model comparison is strictly empirical; neither model is assumed superior a priori.",
        "Healthy Volatile cohort performance is a critical evaluation dimension to verify that income variance is not falsely penalized.",
    ]

    return ModelComparisonResult(
        baseline_id=baseline_meta.experiment_id,
        volatility_aware_id=volatility_aware_meta.experiment_id,
        global_metric_deltas=deltas,
        cohort_deltas=cohort_deltas_dict,
        healthy_volatile_impact=healthy_volatile_impact,
        declining_cohort_impact=declining_cohort_impact,
        summary_notes=notes,
    )
