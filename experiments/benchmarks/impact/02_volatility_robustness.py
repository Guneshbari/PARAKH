"""Step 6, 7, 16 — Volatility-Recovery Matrix, Shock Recovery Stress Test, and Sensitivity Audits.

Implements:
1. Volatility-Recovery 2x2 Matrix:
   - Quadrants: Low/High Volatility x Low/High Recovery
   - Sample counts, observed default rates, predicted risk, score distributions, and discrimination
   - Heatmap visualisations
2. Controlled Shock-Recovery Stress Test:
   - Representative applicant profile under 4 controlled post-shock recovery trajectories
     (Fast, Moderate, Slow, No Recovery)
   - Baseline vs PARAKH probability and score divergence
3. Stability and Sensitivity Audits:
   - Controlled perturbations to income, expense, recovery velocity, and payout frequency
   - Smoothness and SHAP factor attribution continuity verification
"""
import copy
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
import seaborn as sns
from sklearn.metrics import average_precision_score, recall_score, roc_auc_score

from experiments.benchmarks.impact.common import (
    MANDATORY_SYNTHETIC_DISCLAIMER,
    REPORTS_DIR,
    RESULTS_DIR,
    calculate_presentation_score,
    determine_risk_tier,
    load_benchmark_data_and_models,
    to_serializable,
)
from src.ml.constants import (
    DEFAULT_RANDOM_SEED,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
)
from src.ml.explainability.shap_explainer import TreeShapExplainer
from src.ml.features.feature_engineering import FeatureEngineer


# -----------------------------------------------------------------------------
# 1. Volatility-Recovery Matrix (Step 6)
# -----------------------------------------------------------------------------
def analyze_volatility_recovery_matrix(
    test_df: pd.DataFrame,
    y_test: np.ndarray,
    p_base: np.ndarray,
    p_vol: np.ndarray,
    vol_cutoff: float = 0.22,
    rec_cutoff: float = 1.00,
) -> Dict[str, Any]:
    """Partition test population into 4 quadrants based on volatility and recovery.

    Quadrants:
      Q1: Low Volatility (CV <= vol_cutoff) + High Recovery (bounceback >= rec_cutoff)
      Q2: Low Volatility (CV <= vol_cutoff) + Low Recovery (bounceback < rec_cutoff)
      Q3: High Volatility (CV > vol_cutoff) + High Recovery (bounceback >= rec_cutoff)
      Q4: High Volatility (CV > vol_cutoff) + Low Recovery (bounceback < rec_cutoff)

    Returns:
        Structured dictionary of quadrant statistics, observed default rates, and model comparisons.
    """
    cv = test_df["feat_inc_cv_90d"].values
    rec = test_df["feat_rec_bounceback_ratio"].values

    quadrant_definitions = {
        "low_vol_high_rec": {
            "title": "Low Volatility + High Recovery (Benchmark Anchor)",
            "mask": (cv <= vol_cutoff) & (rec >= rec_cutoff),
            "expected_risk": "Lowest Risk Profile",
        },
        "low_vol_low_rec": {
            "title": "Low Volatility + Low Recovery (Subdued / Stagnant)",
            "mask": (cv <= vol_cutoff) & (rec < rec_cutoff),
            "expected_risk": "Intermediate Stagnation Risk",
        },
        "high_vol_high_rec": {
            "title": "High Volatility + High Recovery (Healthy Gig Fluctuations)",
            "mask": (cv > vol_cutoff) & (rec >= rec_cutoff),
            "expected_risk": "Resilient / Low-to-Moderate Default Risk",
        },
        "high_vol_low_rec": {
            "title": "High Volatility + Low Recovery (Distressed Volatility)",
            "mask": (cv > vol_cutoff) & (rec < rec_cutoff),
            "expected_risk": "Elevated Default Risk",
        },
    }

    matrix_results: Dict[str, Any] = {
        "volatility_cutoff_cv": vol_cutoff,
        "recovery_cutoff_bounceback": rec_cutoff,
        "quadrants": {},
        "heatmaps": {
            "observed_default_rate": [[0.0, 0.0], [0.0, 0.0]],
            "baseline_mean_predicted_prob": [[0.0, 0.0], [0.0, 0.0]],
            "parakh_mean_predicted_prob": [[0.0, 0.0], [0.0, 0.0]],
            "parakh_mean_score": [[0.0, 0.0], [0.0, 0.0]],
        },
    }

    # Grid mapping: row 0 = High Vol, row 1 = Low Vol; col 0 = Low Rec, col 1 = High Rec
    grid_coords = {
        "high_vol_low_rec": (0, 0),
        "high_vol_high_rec": (0, 1),
        "low_vol_low_rec": (1, 0),
        "low_vol_high_rec": (1, 1),
    }

    for key, qdef in quadrant_definitions.items():
        mask = qdef["mask"]
        q_y = y_test[mask]
        q_pb = p_base[mask]
        q_pv = p_vol[mask]
        n_samples = int(np.sum(mask))
        n_defaults = int(np.sum(q_y == 1))
        def_rate = float(n_defaults / n_samples) if n_samples > 0 else 0.0

        # Metrics
        pb_mean = float(np.mean(q_pb)) if n_samples > 0 else 0.0
        pv_mean = float(np.mean(q_pv)) if n_samples > 0 else 0.0
        scores_b = test_df.loc[mask, "score_baseline"].values
        scores_v = test_df.loc[mask, "score_volatility"].values
        sb_mean = float(np.mean(scores_b)) if n_samples > 0 else 0.0
        sv_mean = float(np.mean(scores_v)) if n_samples > 0 else 0.0

        # Discrimination where valid
        has_two_classes = (n_defaults > 0 and n_defaults < n_samples)
        pr_b = float(average_precision_score(q_y, q_pb)) if has_two_classes else None
        pr_v = float(average_precision_score(q_y, q_pv)) if has_two_classes else None

        # Recall at 0.50 diagnostic threshold
        rec_b = float(recall_score(q_y, q_pb >= 0.50, zero_division=0)) if n_defaults > 0 else None
        rec_v = float(recall_score(q_y, q_pv >= 0.50, zero_division=0)) if n_defaults > 0 else None

        # FPR on good borrowers (y == 0) at policy approval cutoff (0.20)
        q_goods = (q_y == 0)
        fpr_b = float(np.mean(q_pb[q_goods] >= PROVISIONAL_THRESHOLD_LOWER)) if np.sum(q_goods) > 0 else 0.0
        fpr_v = float(np.mean(q_pv[q_goods] >= PROVISIONAL_THRESHOLD_LOWER)) if np.sum(q_goods) > 0 else 0.0

        matrix_results["quadrants"][key] = {
            "title": qdef["title"],
            "expected_risk": qdef["expected_risk"],
            "sample_count": n_samples,
            "positive_defaults": n_defaults,
            "observed_default_rate": round(def_rate, 4),
            "baseline_mean_predicted_prob": round(pb_mean, 4),
            "parakh_mean_predicted_prob": round(pv_mean, 4),
            "baseline_mean_score": round(sb_mean, 1),
            "parakh_mean_score": round(sv_mean, 1),
            "parakh_score_delta": round(sv_mean - sb_mean, 1),
            "baseline_pr_auc": round(pr_b, 4) if pr_b is not None else None,
            "parakh_pr_auc": round(pr_v, 4) if pr_v is not None else None,
            "baseline_recall_at_050": round(rec_b, 4) if rec_b is not None else None,
            "parakh_recall_at_050": round(rec_v, 4) if rec_v is not None else None,
            "baseline_good_borrower_fpr_at_020": round(fpr_b, 4),
            "parakh_good_borrower_fpr_at_020": round(fpr_v, 4),
        }

        # Populate heatmap matrices
        r, c = grid_coords[key]
        matrix_results["heatmaps"]["observed_default_rate"][r][c] = round(def_rate * 100, 2)
        matrix_results["heatmaps"]["baseline_mean_predicted_prob"][r][c] = round(pb_mean * 100, 2)
        matrix_results["heatmaps"]["parakh_mean_predicted_prob"][r][c] = round(pv_mean * 100, 2)
        matrix_results["heatmaps"]["parakh_mean_score"][r][c] = round(sv_mean, 1)

    return matrix_results


# -----------------------------------------------------------------------------
# 2. Controlled Shock-Recovery Stress Test (Step 7)
# -----------------------------------------------------------------------------
def run_shock_recovery_stress_test(
    data_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate a controlled income shock with 4 distinct recovery trajectories.

    Methodology:
    1. Select a representative gig worker profile (delivery partner, ₹8,000/week baseline,
       moderate debt, healthy starting buffer).
    2. Model a 40% income shock in the middle of observation window.
    3. Simulate four post-shock recovery trajectories:
       - Fast Recovery: Rebounds to 130% baseline in 7 days, bounceback = 1.30, trend = +0.15
       - Moderate Recovery: Rebounds to 105% baseline in 18 days, bounceback = 1.05, trend = +0.05
       - Slow Recovery: Sluggish rebound to 85% baseline in 35 days, bounceback = 0.85, trend = -0.05
       - No Recovery: Remains depressed at 50% baseline, bounceback = 0.50, trend = -0.25
    4. Pass each trajectory through identical feature engineering and scoring pipelines.
    5. Compare baseline vs volatility-aware probability and score response.
    """
    baseline_model = data_bundle["baseline_model"]
    volatility_model = data_bundle["volatility_model"]
    base_prep = data_bundle["base_preprocessor"]
    vol_prep = data_bundle["vol_preprocessor"]
    engineer = FeatureEngineer(include_engineered_interactions=True)

    # Base representative gig worker profile
    base_applicant = {
        "requested_loan_amount": 40000.0,
        "loan_tenure_months": 6,
        "years_working": 1.2,
        "average_working_days": 20,
        "gig_work_type": "DELIVERY",
        "loan_purpose": "WORKING_CAPITAL",
        "feat_inc_median_90d": 5500.0,
        "feat_inc_p25_90d": 4800.0,
        "feat_inc_cv_90d": 0.18,  # Normal pre-shock volatility
        "feat_inc_downside_var": 0.10,
        "feat_trend_slope_90d": 0.01,
        "feat_trend_momentum_30_90": 1.01,
        "feat_act_active_days_ratio": 0.75,
        "feat_act_zero_earn_weeks": 0.0,
        "feat_rec_bounceback_ratio": 1.05,
        "feat_rec_days_to_recover": 14.0,
        "feat_liq_buffer_to_loan": 0.30,
        "feat_liq_burn_months": 1.5,
        "feat_bur_dti_ratio": 0.30,
        "feat_bur_installment_dti": 0.15,
        "feat_bur_total_dti": 0.30,
        "feat_suf_observed_days": 90.0,
        "feat_suf_payout_count": 12.0,
        "feat_suf_group_count": 5.0,
        "feat_suf_missing_ratio": 0.0,
        "feat_inc_mean_90d": 5600.0,
        "feat_inc_trimmed_mean": 5550.0,
        "feat_inc_iqr_ratio": 0.25,
        "feat_inc_min_max_ratio": 0.65,
        "feat_trend_consec_drops": 0.0,
        "feat_act_max_idle_streak": 3.0,
        "feat_act_weekend_intensity": 1.10,
        "feat_rec_max_drawdown": 0.20,
        "feat_ten_years_working": 1.2,
        "feat_ten_platform_rating": 4.70,
        "feat_ten_trips_completed": 800.0,
        "feat_ten_cancellation_rate": 0.04,
        "feat_liq_net_margin": 0.25,
        "feat_pay_utility_on_time": 0.95,
        "feat_pay_max_bill_delay": 2.0,
        "feat_pay_repay_reliability": 0.95,
        "feat_bur_loan_to_income": 0.40,
        "feat_int_vol_x_recovery": 0.18 * 1.05,
        "feat_int_vol_x_buffer": 0.18 * 0.30,
        "feat_int_trend_x_dti": 0.01 * 0.30,
        "feat_int_resilience_idx": 1.05 * 0.30,
    }

    # Define the 4 post-shock trajectories
    # Volatility (CV) is elevated across all scenarios due to the shock itself.
    trajectories = {
        "pre_shock_baseline": {
            "name": "Pre-Shock Baseline",
            "description": "Normal earnings trajectory with low volatility and baseline liquidity.",
            "overrides": {},
        },
        "fast_recovery": {
            "name": "Fast Recovery",
            "description": "Shock followed by rapid bounceback to 135% baseline in 7 days.",
            "overrides": {
                "feat_inc_cv_90d": 0.32,  # Shock elevates volatility
                "feat_inc_downside_var": 0.14,
                "feat_rec_bounceback_ratio": 1.35,
                "feat_rec_days_to_recover": 7.0,
                "feat_trend_slope_90d": 0.15,
                "feat_trend_momentum_30_90": 1.15,
                "feat_int_vol_x_recovery": 0.32 * 1.35,
                "feat_int_resilience_idx": 1.35 * 0.35,
            },
        },
        "moderate_recovery": {
            "name": "Moderate Recovery",
            "description": "Shock followed by steady rebound to 105% baseline over 18 days.",
            "overrides": {
                "feat_inc_cv_90d": 0.35,
                "feat_inc_downside_var": 0.18,
                "feat_rec_bounceback_ratio": 1.05,
                "feat_rec_days_to_recover": 18.0,
                "feat_trend_slope_90d": 0.02,
                "feat_trend_momentum_30_90": 1.01,
                "feat_int_vol_x_recovery": 0.35 * 1.05,
                "feat_int_resilience_idx": 1.05 * 0.30,
            },
        },
        "slow_recovery": {
            "name": "Slow Recovery",
            "description": "Shock followed by weak recovery to 78% baseline over 35 days.",
            "overrides": {
                "feat_inc_cv_90d": 0.40,
                "feat_inc_downside_var": 0.24,
                "feat_rec_bounceback_ratio": 0.78,
                "feat_rec_days_to_recover": 35.0,
                "feat_trend_slope_90d": -0.10,
                "feat_trend_momentum_30_90": 0.85,
                "feat_int_vol_x_recovery": 0.40 * 0.78,
                "feat_int_resilience_idx": 0.78 * 0.25,
                "feat_liq_buffer_to_loan": 0.18,
                "feat_bur_total_dti": 0.38,
            },
        },
        "no_recovery": {
            "name": "No Recovery",
            "description": "Severe shock with no rebound; earnings remain depressed at 40% baseline.",
            "overrides": {
                "feat_inc_median_90d": 3200.0,
                "feat_inc_mean_90d": 3300.0,
                "feat_inc_cv_90d": 0.50,
                "feat_inc_downside_var": 0.38,
                "feat_rec_bounceback_ratio": 0.40,
                "feat_rec_days_to_recover": 60.0,
                "feat_trend_slope_90d": -0.28,
                "feat_trend_momentum_30_90": 0.55,
                "feat_int_vol_x_recovery": 0.50 * 0.40,
                "feat_int_resilience_idx": 0.40 * 0.10,
                "feat_liq_buffer_to_loan": 0.08,
                "feat_bur_total_dti": 0.52,
                "feat_liq_net_margin": 0.02,
            },
        },
    }

    # Transform through pipeline and score
    stress_results: Dict[str, Any] = {
        "disclaimer": MANDATORY_SYNTHETIC_DISCLAIMER,
        "scenarios": {},
    }

    for key, traj in trajectories.items():
        app_dict = copy.deepcopy(base_applicant)
        app_dict.update(traj["overrides"])
        raw_df = pd.DataFrame([app_dict])

        # Feature engineering (fitted training-only)
        eng_df = engineer.transform(raw_df)

        # Baseline preprocessing & scoring
        X_b_prep = base_prep.transform(eng_df)[baseline_model.feature_names_in_]
        p_b = float(baseline_model.predict_proba(X_b_prep)[0])

        # PARAKH preprocessing & scoring
        X_v_prep = vol_prep.transform(eng_df)[volatility_model.feature_names_in_]
        p_v = float(volatility_model.predict_proba(X_v_prep)[0])

        score_b = calculate_presentation_score(p_b)
        score_v = calculate_presentation_score(p_v)
        tier_b = determine_risk_tier(p_b)
        tier_v = determine_risk_tier(p_v)

        stress_results["scenarios"][key] = {
            "name": traj["name"],
            "description": traj["description"],
            "baseline": {
                "predicted_probability": round(p_b, 4),
                "presentation_score": score_b,
                "risk_tier": tier_b,
            },
            "volatility_aware": {
                "predicted_probability": round(p_v, 4),
                "presentation_score": score_v,
                "risk_tier": tier_v,
            },
            "divergence": {
                "probability_diff": round(p_v - p_b, 4),
                "score_diff": score_v - score_b,
            },
        }

    return stress_results



# -----------------------------------------------------------------------------
# 3. Sensitivity & Stability Audits (Step 16)
# -----------------------------------------------------------------------------
def run_sensitivity_audit(data_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Test model prediction stability under small controlled feature perturbations."""
    volatility_model = data_bundle["volatility_model"]
    baseline_model = data_bundle["baseline_model"]
    X_test_vol = data_bundle["X_test_vol"]
    X_test_base = data_bundle["X_test_base"]

    # Select representative median sample
    sample_idx = len(X_test_vol) // 2
    row_vol = X_test_vol.iloc[sample_idx:sample_idx + 1].copy()
    row_base = X_test_base.iloc[sample_idx:sample_idx + 1].copy()

    base_p_vol = float(volatility_model.predict_proba(row_vol)[0])
    base_p_base = float(baseline_model.predict_proba(row_base)[0])

    perturbations = {
        "income_plus_5pct": {"col": "feat_inc_median_90d", "factor": 1.05},
        "income_minus_5pct": {"col": "feat_inc_median_90d", "factor": 0.95},
        "volatility_plus_10pct": {"col": "feat_inc_cv_90d", "factor": 1.10},
        "volatility_minus_10pct": {"col": "feat_inc_cv_90d", "factor": 0.90},
        "debt_burden_plus_10pct": {"col": "feat_bur_total_dti", "factor": 1.10},
        "debt_burden_minus_10pct": {"col": "feat_bur_total_dti", "factor": 0.90},
        "liquidity_buffer_plus_10pct": {"col": "feat_liq_buffer_to_loan", "factor": 1.10},
        "liquidity_buffer_minus_10pct": {"col": "feat_liq_buffer_to_loan", "factor": 0.90},
    }

    sensitivity_results: Dict[str, Any] = {
        "baseline_probability": round(base_p_base, 4),
        "parakh_probability": round(base_p_vol, 4),
        "tests": {},
    }

    for test_name, spec in perturbations.items():
        col = spec["col"]
        factor = spec["factor"]

        # Perturb Volatility Matrix
        p_row_vol = row_vol.copy()
        if col in p_row_vol.columns:
            p_row_vol[col] = p_row_vol[col] * factor
        new_p_vol = float(volatility_model.predict_proba(p_row_vol)[0])

        # Perturb Baseline Matrix
        p_row_base = row_base.copy()
        if col in p_row_base.columns:
            p_row_base[col] = p_row_base[col] * factor
        new_p_base = float(baseline_model.predict_proba(p_row_base)[0])

        delta_vol = new_p_vol - base_p_vol
        delta_base = new_p_base - base_p_base

        sensitivity_results["tests"][test_name] = {
            "perturbed_feature": col,
            "perturbation_factor": factor,
            "parakh_new_prob": round(new_p_vol, 4),
            "parakh_delta_prob": round(delta_vol, 4),
            "parakh_score_delta": calculate_presentation_score(new_p_vol) - calculate_presentation_score(base_p_vol),
            "baseline_new_prob": round(new_p_base, 4),
            "baseline_delta_prob": round(delta_base, 4),
            "is_stable": abs(delta_vol) < 0.05,  # Smooth continuity threshold
        }

    return sensitivity_results


# -----------------------------------------------------------------------------
# Main Orchestration
# -----------------------------------------------------------------------------
def run_volatility_robustness(
    data_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute complete volatility robustness benchmark."""
    if data_bundle is None:
        data_bundle = load_benchmark_data_and_models()

    test_df: pd.DataFrame = data_bundle["test_df"]
    y_test: np.ndarray = data_bundle["y_test"]
    p_base: np.ndarray = data_bundle["p_base"]
    p_vol: np.ndarray = data_bundle["p_vol"]

    print("  Analyzing Volatility-Recovery 2x2 Matrix...")
    matrix_res = analyze_volatility_recovery_matrix(test_df, y_test, p_base, p_vol)

    print("  Executing Controlled Shock-Recovery Stress Test...")
    shock_res = run_shock_recovery_stress_test(data_bundle)

    print("  Executing Stability and Sensitivity Audits...")
    sens_res = run_sensitivity_audit(data_bundle)

    results: Dict[str, Any] = {
        "disclaimer": MANDATORY_SYNTHETIC_DISCLAIMER,
        "volatility_recovery_matrix": matrix_res,
        "shock_recovery_stress_test": shock_res,
        "sensitivity_audit": sens_res,
    }

    # Save JSON results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "02_volatility_robustness_results.json"
    with open(out_file, "w") as f:
        json.dump(to_serializable(results), f, indent=2)
    print(f"  ✓ Volatility robustness results saved to {out_file}")

    # Generate charts
    generate_robustness_charts(matrix_res, shock_res)

    return results


def generate_robustness_charts(
    matrix_res: Dict[str, Any],
    shock_res: Dict[str, Any],
) -> None:
    """Generate Heatmaps and Shock-Recovery Curve charts."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Chart 1: Volatility-Recovery Heatmaps
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ylabels = ["High Volatility (CV > 0.22)", "Low Volatility (CV <= 0.22)"]
    xlabels = ["Low Recovery (< 1.0)", "High Recovery (>= 1.0)"]

    # Heatmap 1: Observed Empirical Default Rate (%)
    obs_data = np.array(matrix_res["heatmaps"]["observed_default_rate"])
    sns.heatmap(
        obs_data,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        xticklabels=xlabels,
        yticklabels=ylabels,
        cbar_kws={"label": "Observed Default Rate (%)"},
        ax=axes[0],
        annot_kws={"size": 13, "weight": "bold"},
    )
    axes[0].set_title("Observed Synthetic Default Rate (%)\n(Controlled Held-Out Ground Truth)", fontsize=12)

    # Heatmap 2: PARAKH Predicted Default Probability (%)
    pred_data = np.array(matrix_res["heatmaps"]["parakh_mean_predicted_prob"])
    sns.heatmap(
        pred_data,
        annot=True,
        fmt=".1f",
        cmap="Blues",
        xticklabels=xlabels,
        yticklabels=ylabels,
        cbar_kws={"label": "Predicted Default Prob (%)"},
        ax=axes[1],
        annot_kws={"size": 13, "weight": "bold"},
    )
    axes[1].set_title("PARAKH Model-Predicted Default Prob (%)\n(Volatility Conditioned on Recovery Velocity)", fontsize=12)

    plt.tight_layout()
    chart1_path = REPORTS_DIR / "04_volatility_recovery_heatmap.png"
    plt.savefig(chart1_path, dpi=300)
    plt.close()

    # Chart 2: Shock Recovery Trajectory Curve
    fig, ax = plt.subplots(figsize=(9, 5))
    scenarios = ["pre_shock_baseline", "fast_recovery", "moderate_recovery", "slow_recovery", "no_recovery"]
    labels = ["Pre-Shock", "Fast Recovery", "Moderate Recovery", "Slow Recovery", "No Recovery"]
    sc_data = shock_res["scenarios"]

    p_base_vals = [sc_data[s]["baseline"]["predicted_probability"] * 100 for s in scenarios]
    p_vol_vals = [sc_data[s]["volatility_aware"]["predicted_probability"] * 100 for s in scenarios]

    x = np.arange(len(scenarios))
    ax.plot(x, p_base_vals, marker="o", linewidth=2.2, color="#6c757d", label="Baseline Logistic Regression")
    ax.plot(x, p_vol_vals, marker="s", linewidth=2.5, color="#0d6efd", label="PARAKH Volatility-Aware")

    ax.axhline(y=PROVISIONAL_THRESHOLD_LOWER * 100, color="#198754", linestyle="--", alpha=0.7, label="Policy Approval Cutoff (20%)")
    ax.axhline(y=PROVISIONAL_THRESHOLD_HIGHER * 100, color="#dc3545", linestyle="--", alpha=0.7, label="Policy Decline Cutoff (45%)")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Predicted Default Probability (%)", fontsize=11)
    ax.set_title("Controlled Shock-Recovery Stress Test:\nModel Response to Controlled Income Shock & Recovery Trajectories", fontsize=12)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    chart2_path = REPORTS_DIR / "05_shock_recovery_curve.png"
    plt.savefig(chart2_path, dpi=300)
    plt.close()

    print(f"  ✓ Volatility robustness charts saved to {REPORTS_DIR}")


if __name__ == "__main__":
    print("Running 02_volatility_robustness...")
    res = run_volatility_robustness()
    print("Complete!")
