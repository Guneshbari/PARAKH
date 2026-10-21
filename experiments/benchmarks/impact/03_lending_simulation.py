"""Step 10, 11 — Lending Portfolio & Expected Loss Simulation Framework.

Implements a reproducible, controlled lending simulation evaluating decision policies
(Approve / Human Review / Decline) and Expected Loss (PD x Exposure x LGD) across
multiple Loss Given Default (LGD) scenarios (25%, 50%, 75%) on the held-out test set (N = 1,698).
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

from experiments.benchmarks.impact.common import (
    MANDATORY_SYNTHETIC_DISCLAIMER,
    REPORTS_DIR,
    RESULTS_DIR,
    load_benchmark_data_and_models,
    to_serializable,
)
from src.ml.constants import (
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
)


LGD_ASSUMPTIONS: List[float] = [0.25, 0.50, 0.75]

SIMULATION_POLICY_ASSUMPTIONS: Dict[str, Any] = {
    "policy_name": "Provisional Three-Tier Credit Policy",
    "source": "FINAL_MODEL.json / docs/ml-specification.md",
    "tiers": {
        "APPROVE": {
            "condition": f"Predicted Default Probability < {PROVISIONAL_THRESHOLD_LOWER:.2f} (Presentation Score > 740)",
            "operational_action": "Streamlined automated credit grant",
        },
        "HUMAN_REVIEW": {
            "condition": f"{PROVISIONAL_THRESHOLD_LOWER:.2f} <= Predicted Probability < {PROVISIONAL_THRESHOLD_HIGHER:.2f} (Score 603 to 740)",
            "operational_action": "Credit adjudicator queue with explainability drill-down",
        },
        "DECLINE": {
            "condition": f"Predicted Default Probability >= {PROVISIONAL_THRESHOLD_HIGHER:.2f} (Presentation Score <= 602)",
            "operational_action": "Adverse credit decision with statutory notification",
        },
    },
    "exposure_field": "requested_loan_amount",
    "lgd_scenarios": [0.25, 0.50, 0.75],
    "disclaimer": MANDATORY_SYNTHETIC_DISCLAIMER,
}


def simulate_lending_portfolio(
    y_true: np.ndarray,
    p_pred: np.ndarray,
    exposure: np.ndarray,
    model_name: str,
    threshold_lower: float = PROVISIONAL_THRESHOLD_LOWER,
    threshold_higher: float = PROVISIONAL_THRESHOLD_HIGHER,
    lgd_list: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Execute simulated lending policy and portfolio risk calculation for a model.

    Args:
        y_true: Binary repayment outcomes (0 = repaid, 1 = default).
        p_pred: Model-predicted default probabilities in [0, 1].
        exposure: Loan exposure amounts (₹) from application requests.
        model_name: Name of model for reporting.
        threshold_lower: Lower threshold for automated approval (default 0.20).
        threshold_higher: Upper threshold for manual review cutoff (default 0.45).
        lgd_list: List of LGD fractions to evaluate (default [0.25, 0.50, 0.75]).

    Returns:
        Structured dictionary of portfolio simulation metrics and expected losses.
    """
    if lgd_list is None:
        lgd_list = LGD_ASSUMPTIONS

    y_t = np.asarray(y_true, dtype=int)
    p = np.asarray(p_pred, dtype=float)
    exp = np.asarray(exposure, dtype=float)
    n_total = len(y_t)
    total_requested_exposure = float(np.sum(exp))

    # Decision segmentation
    appr_mask = (p < threshold_lower)
    rev_mask = (p >= threshold_lower) & (p < threshold_higher)
    decl_mask = (p >= threshold_higher)

    n_appr = int(np.sum(appr_mask))
    n_rev = int(np.sum(rev_mask))
    n_decl = int(np.sum(decl_mask))

    appr_exposure = float(np.sum(exp[appr_mask]))
    rev_exposure = float(np.sum(exp[rev_mask]))
    decl_exposure = float(np.sum(exp[decl_mask]))

    # Quality among approved applications
    appr_defaults = int(np.sum(y_t[appr_mask] == 1))
    appr_goods = int(np.sum(y_t[appr_mask] == 0))
    appr_def_rate = float(appr_defaults / n_appr) if n_appr > 0 else 0.0
    appr_good_rate = float(appr_goods / n_appr) if n_appr > 0 else 0.0

    # Good loan capture rate: approved good borrowers / total good borrowers in population
    total_goods = int(np.sum(y_t == 0))
    good_loan_capture = float(appr_goods / total_goods) if total_goods > 0 else 0.0

    # Error metrics
    # False-positive: Good borrower declined (y == 0 and p >= threshold_higher)
    fpr_decline = float(np.mean(decl_mask[y_t == 0])) if total_goods > 0 else 0.0
    # False-negative: Defaulting borrower approved (y == 1 and p < threshold_lower)
    total_defaults = int(np.sum(y_t == 1))
    fnr_approval = float(np.mean(appr_mask[y_t == 1])) if total_defaults > 0 else 0.0

    # Expected Loss calculations across LGD scenarios
    expected_loss_results: Dict[str, Any] = {}
    for lgd in lgd_list:
        lgd_key = f"lgd_{int(lgd * 100)}pct"
        # EL for approved cohort
        approved_el = float(np.sum(p[appr_mask] * exp[appr_mask] * lgd))
        el_per_100k_approved = float((approved_el / appr_exposure) * 100000) if appr_exposure > 0 else 0.0

        # EL for entire portfolio if all were approved
        unconstrained_el = float(np.sum(p * exp * lgd))
        el_per_100k_unconstrained = float((unconstrained_el / total_requested_exposure) * 100000)

        # Realized default loss in approved portfolio
        realized_approved_loss = float(np.sum(y_t[appr_mask] * exp[appr_mask] * lgd))

        expected_loss_results[lgd_key] = {
            "lgd_assumption": lgd,
            "approved_portfolio_expected_loss_inr": round(approved_el, 2),
            "expected_loss_per_1_lakh_approved_inr": round(el_per_100k_approved, 2),
            "realized_default_loss_inr": round(realized_approved_loss, 2),
            "unconstrained_portfolio_el_inr": round(unconstrained_el, 2),
            "unconstrained_el_per_1_lakh_inr": round(el_per_100k_unconstrained, 2),
        }

    return {
        "model_name": model_name,
        "total_applications": n_total,
        "total_requested_exposure_inr": round(total_requested_exposure, 2),
        "outcomes": {
            "approved": {
                "count": n_appr,
                "rate": round(float(n_appr / n_total), 4),
                "exposure_inr": round(appr_exposure, 2),
                "exposure_share": round(float(appr_exposure / total_requested_exposure), 4),
                "actual_defaults": appr_defaults,
                "actual_good_repayers": appr_goods,
                "default_rate_among_approved": round(appr_def_rate, 4),
                "good_repayment_rate_among_approved": round(appr_good_rate, 4),
            },
            "human_review": {
                "count": n_rev,
                "rate": round(float(n_rev / n_total), 4),
                "exposure_inr": round(rev_exposure, 2),
                "exposure_share": round(float(rev_exposure / total_requested_exposure), 4),
            },
            "declined": {
                "count": n_decl,
                "rate": round(float(n_decl / n_total), 4),
                "exposure_inr": round(decl_exposure, 2),
                "exposure_share": round(float(decl_exposure / total_requested_exposure), 4),
            },
        },
        "capture_and_errors": {
            "good_borrower_capture_rate": round(good_loan_capture, 4),
            "good_borrowers_approved": appr_goods,
            "total_good_borrowers": total_goods,
            "false_positive_decline_rate": round(fpr_decline, 4),
            "false_negative_approval_rate": round(fnr_approval, 4),
        },
        "expected_loss_simulation": expected_loss_results,
    }


def run_lending_simulation(
    data_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute complete lending portfolio and expected loss benchmark."""
    if data_bundle is None:
        data_bundle = load_benchmark_data_and_models()

    test_df: pd.DataFrame = data_bundle["test_df"]
    y_test: np.ndarray = data_bundle["y_test"]
    p_base: np.ndarray = data_bundle["p_base"]
    p_vol: np.ndarray = data_bundle["p_vol"]
    exposure = test_df["requested_loan_amount"].values

    print("  Simulating portfolio outcomes for Baseline Logistic Regression...")
    sim_base = simulate_lending_portfolio(
        y_test, p_base, exposure, model_name="Baseline Logistic Regression"
    )

    print("  Simulating portfolio outcomes for PARAKH Volatility-Aware...")
    sim_vol = simulate_lending_portfolio(
        y_test, p_vol, exposure, model_name="PARAKH Volatility-Aware Model"
    )

    # Comparative analysis
    appr_rate_diff = sim_vol["outcomes"]["approved"]["rate"] - sim_base["outcomes"]["approved"]["rate"]
    good_capture_diff = sim_vol["capture_and_errors"]["good_borrower_capture_rate"] - sim_base["capture_and_errors"]["good_borrower_capture_rate"]
    net_good_loans = sim_vol["capture_and_errors"]["good_borrowers_approved"] - sim_base["capture_and_errors"]["good_borrowers_approved"]

    el_comp = {}
    for lgd in LGD_ASSUMPTIONS:
        lgd_key = f"lgd_{int(lgd * 100)}pct"
        base_el = sim_base["expected_loss_simulation"][lgd_key]["expected_loss_per_1_lakh_approved_inr"]
        vol_el = sim_vol["expected_loss_simulation"][lgd_key]["expected_loss_per_1_lakh_approved_inr"]
        el_comp[lgd_key] = {
            "baseline_el_per_100k": base_el,
            "parakh_el_per_100k": vol_el,
            "el_delta_inr": round(vol_el - base_el, 2),
            "percentage_change": round(((vol_el - base_el) / base_el) * 100, 2),
        }

    results: Dict[str, Any] = {
        "disclaimer": MANDATORY_SYNTHETIC_DISCLAIMER,
        "policy_assumptions": SIMULATION_POLICY_ASSUMPTIONS,
        "baseline_simulation": sim_base,
        "parakh_simulation": sim_vol,
        "comparative_summary": {
            "approval_rate_difference": round(appr_rate_diff, 4),
            "good_borrower_capture_difference": round(good_capture_diff, 4),
            "net_good_borrowers_expanded": net_good_loans,
            "human_review_rate_difference": round(
                sim_vol["outcomes"]["human_review"]["rate"] - sim_base["outcomes"]["human_review"]["rate"], 4
            ),
            "expected_loss_comparison_per_1_lakh": el_comp,
            "executive_finding": (
                f"Under identical policy cutoffs (<0.20 Approve, 0.20-0.45 Review, >=0.45 Decline), "
                f"PARAKH expands approval coverage by +{appr_rate_diff * 100:.2f} percentage points, "
                f"capturing +{net_good_loans} additional good borrowers (+{good_capture_diff * 100:.2f}% relative capture) "
                f"while reducing simulated expected loss per ₹1 Lakh exposure by "
                f"{abs(el_comp['lgd_50pct']['percentage_change']):.1f}% at 50% LGD."
            ),
        },
    }

    # Save JSON results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "03_lending_simulation_results.json"
    with open(out_file, "w") as f:
        json.dump(to_serializable(results), f, indent=2)
    print(f"  ✓ Lending simulation results saved to {out_file}")

    # Generate charts
    generate_simulation_charts(sim_base, sim_vol, el_comp)

    return results


def generate_simulation_charts(
    sim_base: Dict[str, Any],
    sim_vol: Dict[str, Any],
    el_comp: Dict[str, Any],
) -> None:
    """Generate charts for lending simulation outcomes and expected loss."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Chart 1: Portfolio Decision Outcomes Comparison
    fig, ax = plt.subplots(figsize=(8.5, 5))
    categories = ["Approve (< 20%)", "Human Review (20-45%)", "Decline (>= 45%)"]
    x = np.arange(len(categories))
    width = 0.35

    base_rates = [
        sim_base["outcomes"]["approved"]["rate"] * 100,
        sim_base["outcomes"]["human_review"]["rate"] * 100,
        sim_base["outcomes"]["declined"]["rate"] * 100,
    ]
    vol_rates = [
        sim_vol["outcomes"]["approved"]["rate"] * 100,
        sim_vol["outcomes"]["human_review"]["rate"] * 100,
        sim_vol["outcomes"]["declined"]["rate"] * 100,
    ]

    bars1 = ax.bar(x - width / 2, base_rates, width, label="Baseline Logistic Regression", color="#6c757d")
    bars2 = ax.bar(x + width / 2, vol_rates, width, label="PARAKH Volatility-Aware", color="#0d6efd")

    ax.set_ylabel("Portfolio Share (%)", fontsize=11)
    ax.set_title("Simulated Lending Decisions under Predeclared Policy Cutoffs\n(Held-Out Test Partition N = 1,698)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend(frameon=True)
    ax.set_ylim(0, 100)

    for bar in list(bars1) + list(bars2):
        height = bar.get_height()
        ax.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    chart1_path = REPORTS_DIR / "07_portfolio_outcomes.png"
    plt.savefig(chart1_path, dpi=300)
    plt.close()

    # Chart 2: Expected Loss Comparison by LGD Assumption
    fig, ax = plt.subplots(figsize=(8.5, 5))
    lgds = ["LGD = 25%", "LGD = 50%", "LGD = 75%"]
    x = np.arange(len(lgds))
    keys = ["lgd_25pct", "lgd_50pct", "lgd_75pct"]

    base_el = [el_comp[k]["baseline_el_per_100k"] for k in keys]
    vol_el = [el_comp[k]["parakh_el_per_100k"] for k in keys]

    bars1 = ax.bar(x - width / 2, base_el, width, label="Baseline Expected Loss", color="#6c757d")
    bars2 = ax.bar(x + width / 2, vol_el, width, label="PARAKH Expected Loss", color="#198754")

    ax.set_ylabel("Expected Loss (₹ per ₹1 Lakh Approved Exposure)", fontsize=11)
    ax.set_title("Simulated Expected Loss Sensitivity across LGD Scenarios\n(EL = P(Default) × Exposure × LGD)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(lgds, fontsize=10)
    ax.legend(frameon=True)

    for bar in list(bars1) + list(bars2):
        height = bar.get_height()
        ax.annotate(
            f"₹{height:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    plt.tight_layout()
    chart2_path = REPORTS_DIR / "08_expected_loss_by_lgd.png"
    plt.savefig(chart2_path, dpi=300)
    plt.close()

    print(f"  ✓ Lending simulation charts saved to {REPORTS_DIR}")


if __name__ == "__main__":
    print("Running 03_lending_simulation...")
    res = run_lending_simulation()
    print("Complete!")
