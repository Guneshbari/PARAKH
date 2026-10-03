"""Step 8, 9 — Financial Inclusion Coverage and Responsible Abstention Gate Analysis.

Evaluates:
1. Evidence-based assessment coverage across thin-file / gig-worker populations (Step 8):
   - Scored vs Insufficient applications
   - Coverage by cohort archetype
   - Assessment coverage = scored / total; Abstention rate = insufficient / total
2. Abstention Impact on Predictive Reliability & Safety (Step 9):
   - Demonstrates that the data sufficiency gate (feat_suf_observed_days >= 30,
     feat_suf_payout_count >= 4, feat_suf_group_count >= 2) prevents noisy/uncalibrated
     scoring on thin-file records.
   - Coverage vs predictive performance tradeoff curve under varying history requirements.
"""
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from experiments.benchmarks.impact.common import (
    MANDATORY_SYNTHETIC_DISCLAIMER,
    REPORTS_DIR,
    RESULTS_DIR,
    load_benchmark_data_and_models,
    to_serializable,
)
from src.ml.constants import (
    MIN_REQUIRED_CORE_SIGNAL_GROUPS,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
)
from src.ml.evaluation.calibration import evaluate_calibration


def audit_assessment_coverage(dataset_df: pd.DataFrame) -> Dict[str, Any]:
    """Measure evidence-based assessment coverage vs responsible abstention rate."""
    total_apps = len(dataset_df)
    unique_applicants = dataset_df["applicant_profile_id"].nunique()

    # Sufficiency check logic from InputValidator
    obs_days = dataset_df["feat_suf_observed_days"].fillna(0)
    payouts = dataset_df["feat_suf_payout_count"].fillna(0)
    groups = dataset_df["feat_suf_group_count"].fillna(0)

    is_sufficient = (obs_days >= 30) & (payouts >= 4) & (groups >= MIN_REQUIRED_CORE_SIGNAL_GROUPS)
    is_insufficient = ~is_sufficient

    n_sufficient = int(np.sum(is_sufficient))
    n_insufficient = int(np.sum(is_insufficient))

    coverage_rate = float(n_sufficient / total_apps)
    abstention_rate = float(n_insufficient / total_apps)

    # Coverage by cohort archetype
    cohort_coverage: Dict[str, Any] = {}
    for arch in sorted(dataset_df["cohort_archetype"].unique()):
        mask = (dataset_df["cohort_archetype"] == arch)
        n_arch = int(np.sum(mask))
        n_arch_suff = int(np.sum(mask & is_sufficient))
        n_arch_insuff = int(np.sum(mask & is_insufficient))
        cov = float(n_arch_suff / n_arch) if n_arch > 0 else 0.0

        cohort_coverage[arch] = {
            "total_applications": n_arch,
            "sufficient_applications": n_arch_suff,
            "insufficient_abstentions": n_arch_insuff,
            "evidence_based_coverage_rate": round(cov, 4),
            "abstention_rate": round(1.0 - cov, 4),
        }

    return {
        "total_applications": total_apps,
        "unique_applicants": unique_applicants,
        "sufficient_evidence_applications": n_sufficient,
        "insufficient_evidence_applications": n_insufficient,
        "evidence_based_assessment_coverage_rate": round(coverage_rate, 4),
        "responsible_abstention_rate": round(abstention_rate, 4),
        "cohort_breakdown": cohort_coverage,
        "statutory_interpretation": (
            f"Across the full synthetic gig worker applicant population (N = {total_apps:,}), "
            f"PARAKH provides an evidence-based credit assessment for {coverage_rate * 100:.2f}% of applications "
            f"using non-traditional telemetry (daily earnings, active days, recovery velocity, cashflow buffers). "
            f"The system responsibly abstains from scoring on {abstention_rate * 100:.2f}% of applications "
            f"where observation history is insufficient (<30 days or <4 payout cycles), protecting thin-file "
            f"workers from arbitrary or uncalibrated algorithmic decisions."
        ),
    }


def analyze_abstention_impact_and_tradeoff(
    data_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """Demonstrate the impact of the data sufficiency gate and compute the coverage-performance curve."""
    test_df: pd.DataFrame = data_bundle["test_df"]
    y_test: np.ndarray = data_bundle["y_test"]
    p_vol: np.ndarray = data_bundle["p_vol"]

    # In the held-out test split, scored records have target_default_flag
    # Evaluate calibration and error metrics on the sufficient test population
    cal_res = evaluate_calibration(y_test, p_vol, n_bins=10)
    brier = float(brier_score_loss(y_test, p_vol))
    roc_auc = float(roc_auc_score(y_test, p_vol))
    pr_auc = float(average_precision_score(y_test, p_vol))

    # Simulate coverage-performance tradeoff by sweeping observation history gate
    # from 0 to 60 days on the held-out split
    history_thresholds = [0, 15, 30, 45, 60]
    tradeoff_points: List[Dict[str, Any]] = []

    for min_days in history_thresholds:
        mask = (test_df["feat_suf_observed_days"] >= min_days).values
        n_eligible = int(np.sum(mask))
        cov_frac = float(n_eligible / len(test_df))

        sub_y = y_test[mask]
        sub_p = p_vol[mask]

        if len(np.unique(sub_y)) >= 2:
            sub_roc = float(roc_auc_score(sub_y, sub_p))
            sub_pr = float(average_precision_score(sub_y, sub_p))
            sub_brier = float(brier_score_loss(sub_y, sub_p))
            sub_cal = evaluate_calibration(sub_y, sub_p, n_bins=5)
            ece = sub_cal.expected_calibration_error
        else:
            sub_roc, sub_pr, sub_brier, ece = None, None, None, None

        tradeoff_points.append({
            "min_observed_days_gate": min_days,
            "eligible_sample_count": n_eligible,
            "coverage_fraction": round(cov_frac, 4),
            "roc_auc": round(sub_roc, 4) if sub_roc is not None else None,
            "pr_auc": round(sub_pr, 4) if sub_pr is not None else None,
            "brier_score": round(sub_brier, 4) if sub_brier is not None else None,
            "expected_calibration_error": round(ece, 4) if ece is not None else None,
        })

    return {
        "sufficient_evidence_test_metrics": {
            "sample_count": len(test_df),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(cal_res.expected_calibration_error, 4),
            "maximum_calibration_error": round(cal_res.maximum_calibration_error, 4),
        },
        "coverage_performance_tradeoff_curve": tradeoff_points,
    }


def run_abstention_coverage(
    data_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute complete financial inclusion coverage and abstention impact benchmark."""
    if data_bundle is None:
        data_bundle = load_benchmark_data_and_models()

    dataset_df = data_bundle["dataset_df"]

    print("  Auditing Financial Inclusion Coverage across 12,000 applications...")
    cov_res = audit_assessment_coverage(dataset_df)

    print("  Analyzing Abstention Impact on Predictive Reliability...")
    impact_res = analyze_abstention_impact_and_tradeoff(data_bundle)

    results: Dict[str, Any] = {
        "disclaimer": MANDATORY_SYNTHETIC_DISCLAIMER,
        "financial_inclusion_coverage": cov_res,
        "abstention_impact_audit": impact_res,
    }

    # Save JSON results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "05_abstention_coverage_results.json"
    with open(out_file, "w") as f:
        json.dump(to_serializable(results), f, indent=2)
    print(f"  ✓ Abstention & coverage results saved to {out_file}")

    # Generate charts
    generate_coverage_charts(cov_res, impact_res)

    return results


def generate_coverage_charts(
    cov_res: Dict[str, Any],
    impact_res: Dict[str, Any],
) -> None:
    """Generate visual chart for coverage vs predictive performance tradeoff."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Chart: Coverage vs Performance Tradeoff Curve
    points = impact_res["coverage_performance_tradeoff_curve"]
    gates = [p["min_observed_days_gate"] for p in points]
    coverages = [p["coverage_fraction"] * 100 for p in points]
    pr_aucs = [p["pr_auc"] * 100 for p in points]
    eces = [p["expected_calibration_error"] * 100 for p in points]

    fig, ax1 = plt.subplots(figsize=(8.5, 5))

    color1 = "#0d6efd"
    ax1.set_xlabel("Minimum Required Observation Days Gate (Days)", fontsize=11)
    ax1.set_ylabel("Evidence-Based Assessment Coverage (%)", color=color1, fontsize=11)
    line1 = ax1.plot(gates, coverages, marker="o", linewidth=2.5, color=color1, label="Assessment Coverage (%)")
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_ylim(0, 110)

    ax2 = ax1.twinx()
    color2 = "#198754"
    ax2.set_ylabel("PR-AUC (%) [Predictive Quality]", color=color2, fontsize=11)
    line2 = ax2.plot(gates, pr_aucs, marker="s", linewidth=2.5, color=color2, linestyle="--", label="PR-AUC (%)")
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(80, 100)

    # Draw vertical line for PARAKH's chosen gate (30 days)
    ax1.axvline(x=30, color="#dc3545", linestyle=":", linewidth=2, label="PARAKH Frozen Gate (30d)")

    # Combined legend
    lines = line1 + line2 + [plt.Line2D([0], [0], color="#dc3545", linestyle=":", linewidth=2)]
    labels = ["Assessment Coverage (%)", "PR-AUC (%)", "PARAKH Frozen Gate (30d)"]
    ax1.legend(lines, labels, loc="lower left", frameon=True)

    plt.title("Coverage vs Predictive Quality Tradeoff:\nEvaluating Responsible Abstention Gate Thresholds", fontsize=12)
    plt.tight_layout()
    chart_path = REPORTS_DIR / "06_coverage_vs_performance.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"  ✓ Coverage charts saved to {REPORTS_DIR}")


if __name__ == "__main__":
    print("Running 05_abstention_coverage...")
    res = run_abstention_coverage()
    print("Complete!")
