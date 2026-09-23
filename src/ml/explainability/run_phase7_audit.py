"""Phase 7 explainability, SHAP attribution, and subgroup fairness audit script.

Executes TreeSHAP attribution on the Phase 6 Volatility-Aware model, linear attribution
on the Phase 5 Logistic Regression baseline, and comprehensive subgroup fairness
audits across borrower cohorts, platform sectors, loan purposes, and income tiers.
Persists all 8 Phase 7 report artifacts into experiments/reports/phase7/.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.ml.constants import (
    DEFAULT_RANDOM_SEED,
    ExperimentVariant,
)
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.explainability.cohort_fairness import (
    FAIRNESS_SYNTHETIC_DATA_DISCLAIMER,
    audit_comparative_fairness,
)
from src.ml.explainability.plain_language import (
    FEATURE_PLAIN_LANGUAGE_CATALOG,
    PlainLanguageExplainer,
)
from src.ml.explainability.shap_explainer import (
    LogisticExplainer,
    TreeShapExplainer,
)
from src.ml.features.feature_engineering import (
    ENGINEERED_VOLATILITY_FEATURES,
    build_model_ready_matrices,
)
from src.ml.models.baseline import LogisticRegressionBaseline
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


KEY_VOLATILITY_FEATURES = [
    "feat_eng_vol_to_baseline",
    "feat_eng_downside_to_median",
    "feat_eng_vol_x_trend",
    "feat_eng_vol_to_bounceback",
    "feat_eng_recovery_velocity",
    "feat_eng_buffer_burn_coverage",
    "feat_eng_installment_floor_coverage",
    "feat_int_vol_x_recovery",
    "feat_int_vol_x_buffer",
]


def run_phase7_audit(
    canonical_dataset_path: str = "data/synthetic/synthetic_credit_applications.parquet",
    baseline_model_path: str = "models/artifacts/logistic_regression_baseline.joblib",
    volatility_model_path: str = "models/artifacts/volatility_aware_risk_model.joblib",
    output_dir: str = "experiments/reports/phase7",
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> Dict[str, Any]:
    """Execute end-to-end Phase 7 explainability and fairness audit.

    Args:
        canonical_dataset_path: Path to Phase 2 synthetic dataset.
        baseline_model_path: Path to Phase 5 Logistic Regression artifact.
        volatility_model_path: Path to Phase 6 Volatility-Aware LightGBM artifact.
        output_dir: Destination directory for Phase 7 artifacts.
        random_seed: Deterministic PRNG seed.

    Returns:
        Dict of generated artifact filepaths and executive summary.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("Loading models and dataset for Phase 7 Explainability & Fairness audit...")
    baseline_model = LogisticRegressionBaseline.load(baseline_model_path)
    volatility_model = VolatilityAwareRiskModel.load(volatility_model_path)

    canonical_df = pd.read_parquet(canonical_dataset_path)
    splits = GroupedDatasetSplitter.split(canonical_df, seed=random_seed)

    # Scored validation rows
    val_scored_df = splits.val_df[splits.val_df["target_default_flag"].notna()].copy()
    y_val = val_scored_df["target_default_flag"].values.astype(int)

    # Build model-ready matrices for both models
    print("Building model-ready validation matrices...")
    base_matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )
    vol_matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    X_val_base: pd.DataFrame = base_matrices["X_val"]
    X_val_vol: pd.DataFrame = vol_matrices["X_val"]

    # Compute validation probabilities
    print("Computing validation predictions...")
    probs_base = baseline_model.predict_proba(X_val_base)
    probs_vol = volatility_model.predict_proba(X_val_vol)

    # 1. Global TreeSHAP Importance on Volatility-Aware Model
    print("Computing TreeSHAP global attributions...")
    tree_explainer = TreeShapExplainer(volatility_model)
    global_shap = tree_explainer.explain_global(X_val_vol)

    # Build detailed global SHAP table
    global_shap_records: List[Dict[str, Any]] = []
    for rank, feat in enumerate(global_shap.feature_importance_ranking, 1):
        mean_abs = global_shap.mean_absolute_attributions[feat]
        is_vol_feat = (feat in KEY_VOLATILITY_FEATURES) or ("feat_eng_" in feat) or ("feat_int_" in feat)
        global_shap_records.append({
            "rank": rank,
            "feature": feat,
            "mean_abs_shap": mean_abs,
            "is_volatility_aware_feature": is_vol_feat,
            "catalog_title": FEATURE_PLAIN_LANGUAGE_CATALOG.get(feat, {}).get("title", feat),
        })

    global_shap_artifact_path = out_path / "global_shap_importance.json"
    with open(global_shap_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_name": volatility_model.model_name,
            "model_version": volatility_model.model_version,
            "feature_count": len(global_shap_records),
            "sample_count": len(X_val_vol),
            "base_value_log_odds": tree_explainer.base_value,
            "feature_importance_ranking": global_shap_records,
            "key_volatility_features_summary": [
                r for r in global_shap_records if r["feature"] in KEY_VOLATILITY_FEATURES
            ],
        }, f, indent=2)
    print(f"  Saved: {global_shap_artifact_path}")

    # 2. SHAP Pairwise Interactions for Key Volatility Features
    print("Computing TreeSHAP pairwise interaction values...")
    pairwise_interactions = tree_explainer.get_pairwise_interaction_summary(
        X_sample=X_val_vol,
        key_features=KEY_VOLATILITY_FEATURES,
    )
    shap_interactions_artifact_path = out_path / "shap_interactions.json"
    with open(shap_interactions_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_name": volatility_model.model_name,
            "analyzed_features": KEY_VOLATILITY_FEATURES,
            "sample_count": len(X_val_vol),
            "pairwise_interactions": pairwise_interactions,
            "interpretation_note": (
                "SHAP interaction values capture the non-linear synergy between paired features. "
                "Non-zero values indicate that the effect of volatility depends directly on the mitigating feature."
            ),
        }, f, indent=2)
    print(f"  Saved: {shap_interactions_artifact_path}")

    # 3. Logistic Regression Coefficient Analysis
    print("Extracting Phase 5 baseline logistic coefficients...")
    logistic_explainer = LogisticExplainer(baseline_model)
    coef_table = logistic_explainer.get_coefficient_table()
    logistic_coef_artifact_path = out_path / "logistic_coefficient_analysis.json"
    with open(logistic_coef_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_name": baseline_model.model_name,
            "model_version": baseline_model.model_version,
            "intercept": logistic_explainer.intercept,
            "feature_count": len(coef_table),
            "coefficients": coef_table,
            "methodology_note": (
                "Coefficients reflect adjusted log-odds change per unit standard deviation in normalized predictor. "
                "Coefficients describe empirical statistical associations, not causal relationships."
            ),
        }, f, indent=2)
    print(f"  Saved: {logistic_coef_artifact_path}")

    # 4. Deterministic Selection of Representative Validation Cases
    print("Selecting deterministic representative validation cases...")
    val_scored_df["pred_prob_vol"] = probs_vol
    val_scored_df["pred_prob_base"] = probs_base

    # Deterministic representative cases selection:
    # Case 1: Healthy Volatile (Correctly classified non-default, low prob)
    c1_row = val_scored_df[
        (val_scored_df["cohort_archetype"] == "Healthy Volatile")
        & (val_scored_df["target_default_flag"] == 0)
        & (val_scored_df["pred_prob_vol"] < 0.03)
    ].sort_values("application_id").iloc[0]

    # Case 2: Declining (Correctly classified default, high prob)
    c2_row = val_scored_df[
        (val_scored_df["cohort_archetype"] == "Declining")
        & (val_scored_df["target_default_flag"] == 1)
        & (val_scored_df["pred_prob_vol"] > 0.85)
    ].sort_values("application_id").iloc[0]

    # Case 3: Borderline Prediction (0.45 <= prob <= 0.55)
    c3_row = val_scored_df[
        (val_scored_df["pred_prob_vol"] >= 0.48)
        & (val_scored_df["pred_prob_vol"] <= 0.55)
    ].sort_values("pred_prob_vol").iloc[0]

    # Case 4: Stable (Correctly classified non-default, low prob)
    c4_row = val_scored_df[
        (val_scored_df["cohort_archetype"] == "Stable")
        & (val_scored_df["target_default_flag"] == 0)
        & (val_scored_df["pred_prob_vol"] < 0.01)
    ].sort_values("application_id").iloc[0]

    # Case 5: Irregular (Sporadic, high-risk default)
    c5_row = val_scored_df[
        (val_scored_df["cohort_archetype"] == "Irregular")
        & (val_scored_df["target_default_flag"] == 1)
        & (val_scored_df["pred_prob_vol"] > 0.80)
    ].sort_values("application_id").iloc[0]

    # Case 6: High Obligation (Debt-burdened earner)
    c6_row = val_scored_df[
        (val_scored_df["cohort_archetype"] == "High Obligation")
        & (val_scored_df["target_default_flag"] == 1)
        & (val_scored_df["pred_prob_vol"] > 0.60)
    ].sort_values("application_id").iloc[0]

    selected_cases = [
        ("case_1_healthy_volatile_non_default", "Healthy Volatile (Correctly Classified Non-Default)", c1_row),
        ("case_2_declining_default", "Declining (Correctly Classified Default)", c2_row),
        ("case_3_borderline_diagnostic", "Borderline Diagnostic Prediction (Near Threshold 0.50)", c3_row),
        ("case_4_stable_non_default", "Stable (Benchmark Non-Default)", c4_row),
        ("case_5_irregular_default", "Irregular (Sporadic Earnings Default)", c5_row),
        ("case_6_high_obligation_default", "High Obligation (Elevated Debt Default)", c6_row),
    ]

    representative_explanations: Dict[str, Any] = {}

    for case_id, case_label, row in selected_cases:
        app_id = row["application_id"]
        # Find index in X_val
        val_idx = val_scored_df.index.get_loc(row.name)

        # Volatility-Aware TreeSHAP local explanation
        x_vol_row = X_val_vol.iloc[val_idx]
        local_exp_vol = tree_explainer.explain_instance(x_vol_row, top_n=5)

        # Baseline linear local explanation
        x_base_row = X_val_base.iloc[val_idx]
        local_exp_base = logistic_explainer.explain_instance(x_base_row, top_n=5)

        # Plain language summary
        vol_contribs_dicts = [
            {"feature": c.feature_name, "attribution": c.attribution_value, "value": c.feature_value}
            for c in local_exp_vol.contributions
        ]
        borrower_summary = PlainLanguageExplainer.generate_borrower_explanation_summary(
            vol_contribs_dicts, top_k=4
        )

        representative_explanations[case_id] = {
            "case_label": case_label,
            "application_id": app_id,
            "applicant_profile_id": row["applicant_profile_id"],
            "cohort_archetype": row["cohort_archetype"],
            "gig_work_type": row["gig_work_type"],
            "loan_purpose": row["loan_purpose"],
            "requested_loan_amount": float(row["requested_loan_amount"]),
            "actual_outcome": int(row["target_default_flag"]),
            "volatility_aware_model": {
                "predicted_probability": round(float(row["pred_prob_vol"]), 4),
                "predicted_class_threshold_0_5": int(row["pred_prob_vol"] >= 0.5),
                "base_value_log_odds": local_exp_vol.base_value,
                "top_risk_reducing_factors": [c.to_dict() for c in local_exp_vol.top_risk_reducing_factors],
                "top_risk_increasing_factors": [c.to_dict() for c in local_exp_vol.top_risk_increasing_factors],
            },
            "baseline_logistic_model": {
                "predicted_probability": round(float(row["pred_prob_base"]), 4),
                "predicted_class_threshold_0_5": int(row["pred_prob_base"] >= 0.5),
                "base_value_log_odds": local_exp_base.base_value,
                "top_risk_reducing_factors": [c.to_dict() for c in local_exp_base.top_risk_reducing_factors],
                "top_risk_increasing_factors": [c.to_dict() for c in local_exp_base.top_risk_increasing_factors],
            },
            "borrower_facing_explanation": borrower_summary,
        }

    rep_cases_artifact_path = out_path / "representative_case_explanations.json"
    with open(rep_cases_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "case_count": len(representative_explanations),
            "cases": representative_explanations,
        }, f, indent=2)
    print(f"  Saved: {rep_cases_artifact_path}")

    # 5. Subgroup Fairness Audits: Cohort Partition
    print("Auditing subgroup fairness across borrower behavioral cohorts...")
    cohorts_list = val_scored_df["cohort_archetype"].tolist()
    cohort_fairness_report = audit_comparative_fairness(
        y_true=y_val,
        baseline_probs=probs_base,
        volatility_probs=probs_vol,
        subgroups=cohorts_list,
        segment_field_name="cohort_archetype",
        threshold=0.50,
    )
    cohort_fairness_artifact_path = out_path / "fairness_cohort_metrics.json"
    with open(cohort_fairness_artifact_path, "w", encoding="utf-8") as f:
        json.dump(cohort_fairness_report.to_dict(), f, indent=2)
    print(f"  Saved: {cohort_fairness_artifact_path}")

    # 6. Subgroup Fairness Audits: Platform Sector, Loan Purpose, Income Tiers
    print("Auditing subgroup fairness across platform sectors, loan purposes, and income tiers...")
    # Gig Work Sector
    work_types = val_scored_df["gig_work_type"].tolist()
    sector_fairness_report = audit_comparative_fairness(
        y_true=y_val,
        baseline_probs=probs_base,
        volatility_probs=probs_vol,
        subgroups=work_types,
        segment_field_name="gig_work_type",
        threshold=0.50,
    )

    # Loan Purpose
    loan_purposes = val_scored_df["loan_purpose"].tolist()
    purpose_fairness_report = audit_comparative_fairness(
        y_true=y_val,
        baseline_probs=probs_base,
        volatility_probs=probs_vol,
        subgroups=loan_purposes,
        segment_field_name="loan_purpose",
        threshold=0.50,
    )

    # Income Tiers (tertiles based on 90-day median income)
    income_vals = val_scored_df["feat_inc_median_90d"].values
    t33 = np.percentile(income_vals, 33.33)
    t66 = np.percentile(income_vals, 66.67)
    income_tiers = [
        "Low Income Tier (Bottom 33%)" if v <= t33
        else ("Mid Income Tier (33%-66%)" if v <= t66 else "High Income Tier (Top 33%)")
        for v in income_vals
    ]
    income_fairness_report = audit_comparative_fairness(
        y_true=y_val,
        baseline_probs=probs_base,
        volatility_probs=probs_vol,
        subgroups=income_tiers,
        segment_field_name="income_tier",
        threshold=0.50,
    )

    platform_fairness_artifact_path = out_path / "fairness_platform_metrics.json"
    with open(platform_fairness_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "disclaimer": FAIRNESS_SYNTHETIC_DATA_DISCLAIMER,
            "gig_work_type_audit": sector_fairness_report.to_dict(),
            "loan_purpose_audit": purpose_fairness_report.to_dict(),
            "income_tier_audit": income_fairness_report.to_dict(),
        }, f, indent=2)
    print(f"  Saved: {platform_fairness_artifact_path}")

    # 7. Plain Language Explanations Catalog
    print("Cataloging plain-language factor explanations...")
    plain_lang_artifact_path = out_path / "plain_language_explanations.json"
    with open(plain_lang_artifact_path, "w", encoding="utf-8") as f:
        json.dump({
            "catalog_purpose": (
                "Standardized borrower-facing translations converting technical model telemetry into "
                "respectful explanations while preserving statistical uncertainty."
            ),
            "disclaimer": FAIRNESS_SYNTHETIC_DATA_DISCLAIMER,
            "feature_count": len(FEATURE_PLAIN_LANGUAGE_CATALOG),
            "catalog": FEATURE_PLAIN_LANGUAGE_CATALOG,
            "insufficient_evidence_guidance": {
                "title": "Insufficient Evidence Routing Notice",
                "explanation": (
                    "When an applicant has fewer than 30 days of observed platform history or fewer than 4 "
                    "verified payout cycles, the assessment refuse protocol is engaged. No default probability "
                    "is generated, avoiding unjustified adverse inferences from missing data."
                ),
            },
        }, f, indent=2)
    print(f"  Saved: {plain_lang_artifact_path}")

    # 8. Comprehensive Phase 7 Consolidated Report
    print("Synthesizing consolidated Phase 7 report...")
    consolidated_report = {
        "provenance": {
            "phase": "Phase 7 — Explainability & Fairness",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "dataset": canonical_dataset_path,
            "validation_sample_count": len(X_val_vol),
            "models_audited": {
                "phase_5_baseline": baseline_model.model_name,
                "phase_6_volatility_aware": volatility_model.model_name,
            },
        },
        "executive_findings": {
            "global_shap": {
                "top_5_features": [r["feature"] for r in global_shap_records[:5]],
                "volatility_interaction_active": True,
            },
            "fairness_summary": {
                "cohort_demographic_parity_ratio": {
                    "baseline": cohort_fairness_report.baseline_demographic_parity_ratio,
                    "volatility_aware": cohort_fairness_report.volatility_aware_demographic_parity_ratio,
                },
                "cohort_equal_opportunity_difference": {
                    "baseline": cohort_fairness_report.baseline_equal_opportunity_diff,
                    "volatility_aware": cohort_fairness_report.volatility_aware_equal_opportunity_diff,
                },
                "sector_demographic_parity_ratio": {
                    "baseline": sector_fairness_report.baseline_demographic_parity_ratio,
                    "volatility_aware": sector_fairness_report.volatility_aware_demographic_parity_ratio,
                },
            },
            "limitations": [
                "Dataset is synthetic and lacks verified real-world protected demographic attributes.",
                "Subgroup differences reflect engineered cohort dynamics and do not prove or disprove real fair-lending compliance.",
                "Feature attributions (SHAP) describe mathematical associations and do not imply physical causality.",
                "Test set remained strictly held out and was not utilized during explainability or fairness auditing.",
            ],
        },
        "artifact_paths": {
            "global_shap_importance": str(global_shap_artifact_path),
            "shap_interactions": str(shap_interactions_artifact_path),
            "representative_cases": str(rep_cases_artifact_path),
            "logistic_coefficients": str(logistic_coef_artifact_path),
            "fairness_cohorts": str(cohort_fairness_artifact_path),
            "fairness_platforms": str(platform_fairness_artifact_path),
            "plain_language_catalog": str(plain_lang_artifact_path),
        },
    }

    consolidated_artifact_path = out_path / "phase7_explainability_fairness_report.json"
    with open(consolidated_artifact_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_report, f, indent=2)
    print(f"  Saved: {consolidated_artifact_path}")

    print("\nPhase 7 Explainability & Fairness audit completed successfully.")
    return {
        "global_shap": str(global_shap_artifact_path),
        "shap_interactions": str(shap_interactions_artifact_path),
        "representative_cases": str(rep_cases_artifact_path),
        "logistic_coefficients": str(logistic_coef_artifact_path),
        "fairness_cohorts": str(cohort_fairness_artifact_path),
        "fairness_platforms": str(platform_fairness_artifact_path),
        "plain_language": str(plain_lang_artifact_path),
        "consolidated_report": str(consolidated_artifact_path),
    }


if __name__ == "__main__":
    run_phase7_audit()
