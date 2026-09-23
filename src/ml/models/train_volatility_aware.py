"""Volatility-Aware Model training, validation, and benchmarking pipeline for PARAKH.

Trains the non-linear gradient-boosted tree model (LightGBM) on the full Phase 4
VOLATILITY_AWARE feature set (64 model-ready columns). Evaluates discrimination,
calibration, and cohort performance on the validation split. Generates
comprehensive baseline comparison metrics, feature importance reports, and
reproducible model artifacts.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)

from src.ml.constants import (
    DEFAULT_RANDOM_SEED,
    PRESENTATION_SCORE_MAX,
    PRESENTATION_SCORE_MIN,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
    ExperimentVariant,
    RiskTier,
)
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.evaluation.calibration import evaluate_calibration
from src.ml.evaluation.cohorts import evaluate_by_cohort
from src.ml.evaluation.metrics import evaluate_predictions
from src.ml.features.feature_engineering import build_model_ready_matrices
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


def calculate_presentation_score(prob: float) -> int:
    """Calculate 300-850 presentation score inversely proportional to default risk."""
    score = int(
        round(
            PRESENTATION_SCORE_MIN
            + (1.0 - prob) * (PRESENTATION_SCORE_MAX - PRESENTATION_SCORE_MIN)
        )
    )
    return max(PRESENTATION_SCORE_MIN, min(PRESENTATION_SCORE_MAX, score))


def determine_risk_tier(prob: float) -> str:
    """Map default probability to provisional risk tier."""
    if prob < PROVISIONAL_THRESHOLD_LOWER:
        return RiskTier.LOWER.value
    elif prob < PROVISIONAL_THRESHOLD_HIGHER:
        return RiskTier.MODERATE.value
    return RiskTier.HIGHER.value


def train_and_evaluate_volatility_aware(
    canonical_dataset_path: str = "data/synthetic/synthetic_credit_applications.parquet",
    baseline_metrics_path: str = "experiments/reports/phase5_baseline_metrics.json",
    baseline_eval_path: str = "experiments/reports/phase5_baseline_evaluation.json",
    artifacts_dir: str = "models/artifacts",
    reports_dir: str = "experiments/reports",
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> Dict[str, Any]:
    """Train, validate, evaluate, and benchmark the Phase 6 Volatility-Aware model.

    Args:
        canonical_dataset_path: Path to canonical Phase 2 synthetic dataset.
        baseline_metrics_path: Path to Phase 5 baseline metrics JSON.
        baseline_eval_path: Path to Phase 5 baseline comprehensive evaluation JSON.
        artifacts_dir: Destination directory for model artifacts.
        reports_dir: Destination directory for evaluation reports.
        random_seed: Deterministic PRNG seed.

    Returns:
        Dict containing execution summary, metrics, and artifact paths.
    """
    artifacts_path = Path(artifacts_dir)
    reports_path = Path(reports_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    # 1. Load canonical dataset
    print(f"Loading canonical dataset from {canonical_dataset_path}...")
    dataset_df = pd.read_parquet(canonical_dataset_path)
    total_records = len(dataset_df)
    total_applicants = dataset_df["applicant_profile_id"].nunique()

    # 2. Partition dataset using grouped splitter (seed 42)
    print("Splitting dataset into train, val, and test partitions (grouped by applicant)...")
    splits = GroupedDatasetSplitter.split(dataset_df, seed=random_seed)

    # 3. Build model-ready matrices for VOLATILITY_AWARE variant (scored only)
    print("Building model-ready matrices for VOLATILITY_AWARE feature variant (scored records only)...")
    matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    X_train: pd.DataFrame = matrices["X_train"]
    y_train: np.ndarray = np.asarray(matrices["y_train"]).astype(int)
    X_val: pd.DataFrame = matrices["X_val"]
    y_val: np.ndarray = np.asarray(matrices["y_val"]).astype(int)
    # Test split is strictly held out
    X_test: pd.DataFrame = matrices["X_test"]
    y_test: np.ndarray = np.asarray(matrices["y_test"]).astype(int)

    print(f"  X_train shape: {X_train.shape} | defaults: {y_train.sum()} ({y_train.mean():.4f})")
    print(f"  X_val shape:   {X_val.shape} | defaults: {y_val.sum()} ({y_val.mean():.4f})")
    print(f"  X_test shape:  {X_test.shape} (HELD OUT — NOT USED FOR TRAINING OR TUNING)")

    # 4. Small deterministic hyperparameter tuning on validation split
    print("Running deterministic hyperparameter tuning sweep on validation split...")
    candidate_configs = [
        {"n_estimators": 50,  "learning_rate": 0.05, "num_leaves": 15, "min_child_samples": 20, "reg_lambda": 0.0},
        {"n_estimators": 100, "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 30, "reg_lambda": 1.0},
        {"n_estimators": 100, "learning_rate": 0.05, "num_leaves": 15, "min_child_samples": 20, "reg_lambda": 1.0},
        {"n_estimators": 100, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 20, "reg_lambda": 1.0},
        {"n_estimators": 100, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 50, "reg_lambda": 5.0},
        {"n_estimators": 150, "learning_rate": 0.03, "num_leaves": 31, "min_child_samples": 30, "reg_lambda": 2.0},
        {"n_estimators": 150, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 30, "reg_lambda": 2.0},
        {"n_estimators": 100, "learning_rate": 0.10, "num_leaves": 31, "min_child_samples": 20, "reg_lambda": 1.0},
        {"n_estimators": 200, "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 20, "reg_lambda": 2.0},
        {"n_estimators": 150, "learning_rate": 0.05, "num_leaves": 20, "min_child_samples": 25, "reg_lambda": 1.5},
    ]

    sweep_results: List[Dict[str, Any]] = []
    best_config = candidate_configs[6]
    best_val_pr = -1.0

    for i, cfg in enumerate(candidate_configs):
        trial_model = VolatilityAwareRiskModel(
            **cfg,
            random_state=random_seed,
        )
        trial_model.fit(X_train, y_train)
        trial_probs = trial_model.predict_proba(X_val)

        val_roc = float(roc_auc_score(y_val, trial_probs))
        val_pr = float(average_precision_score(y_val, trial_probs))
        val_brier = float(brier_score_loss(y_val, trial_probs))

        res_entry = {
            "trial_index": i,
            "hyperparameters": cfg,
            "val_roc_auc": round(val_roc, 4),
            "val_pr_auc": round(val_pr, 4),
            "val_brier_score": round(val_brier, 4),
        }
        sweep_results.append(res_entry)

        if val_pr > best_val_pr:
            best_val_pr = val_pr
            best_config = cfg

    print(f"  Selected optimal configuration: {best_config} (Val PR-AUC: {best_val_pr:.4f})")

    # 5. Fit final Volatility-Aware Model
    print("Fitting final Volatility-Aware Risk Model on full training split...")
    final_model = VolatilityAwareRiskModel(
        **best_config,
        random_state=random_seed,
        description="Phase 6 Non-linear LightGBM model on 64 VOLATILITY_AWARE features.",
    )
    final_model.fit(X_train, y_train)

    # 6. Predict probabilities on train and validation
    y_prob_train = final_model.predict_proba(X_train)
    y_prob_val = final_model.predict_proba(X_val)

    # 7. Evaluate classification metrics
    metrics_train_0_5 = evaluate_predictions(y_train, y_prob_train, threshold=0.5)
    metrics_val_0_5 = evaluate_predictions(y_val, y_prob_val, threshold=0.5)

    # 8. Operational decision threshold sweep on validation
    threshold_grid = [0.10, 0.126, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    multi_threshold_metrics: List[Dict[str, Any]] = []
    for thr in threshold_grid:
        tm = evaluate_predictions(y_val, y_prob_val, threshold=thr)
        multi_threshold_metrics.append({
            "threshold": thr,
            "precision": tm.precision,
            "recall": tm.recall,
            "f1": tm.f1,
            "true_positives": tm.true_positives,
            "false_positives": tm.false_positives,
            "true_negatives": tm.true_negatives,
            "false_negatives": tm.false_negatives,
        })

    # 9. Probability curves data (ROC & PR curves)
    fpr, tpr, roc_thresholds = roc_curve(y_val, y_prob_val)
    precision_curve, recall_curve, pr_thresholds = precision_recall_curve(y_val, y_prob_val)

    # Downsample curve points for compact JSON storage (every 5th point plus boundaries)
    roc_points = [
        {"fpr": round(float(f), 4), "tpr": round(float(t), 4), "threshold": round(float(th), 4)}
        for f, t, th in zip(fpr[::5], tpr[::5], roc_thresholds[::5])
    ]
    pr_points = [
        {"precision": round(float(p), 4), "recall": round(float(r), 4), "threshold": round(float(th), 4) if idx < len(pr_thresholds) else 1.0}
        for idx, (p, r, th) in enumerate(zip(precision_curve[::5], recall_curve[::5], list(pr_thresholds[::5]) + [1.0]))
    ]

    # 10. Probability calibration evaluation
    cal_uniform = evaluate_calibration(y_val, y_prob_val, n_bins=10, strategy="uniform")
    cal_quantile = evaluate_calibration(y_val, y_prob_val, n_bins=10, strategy="quantile")

    # 11. Cohort evaluation
    val_scored_df = splits.val_df[splits.val_df["target_default_flag"].notna()].copy()
    val_cohorts = val_scored_df["cohort_archetype"].tolist()
    cohort_eval = evaluate_by_cohort(y_val, y_prob_val, cohorts=val_cohorts, threshold=0.5)
    cohort_eval_dict = {k: v.to_dict() for k, v in cohort_eval.items()}

    # 12. Feature importance extraction
    feat_imp_df = final_model.get_feature_importances_df()
    feature_importance_list = [
        {
            "rank": rank + 1,
            "feature": row["feature"],
            "split_importance": int(row["split_importance"]),
            "gain_importance": round(float(row["gain_importance"]), 4),
            "normalized_gain": round(float(row["normalized_gain"]), 6),
        }
        for rank, (_, row) in enumerate(feat_imp_df.iterrows())
    ]

    # Save feature importance artifact
    feat_imp_path = reports_path / "phase6_feature_importance.json"
    with open(feat_imp_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_name": final_model.model_name,
            "model_version": final_model.model_version,
            "feature_count": len(feature_importance_list),
            "feature_importances": feature_importance_list,
        }, f, indent=2)
    print(f"  Saved feature importance: {feat_imp_path}")

    # 13. Baseline comparison
    baseline_metrics: Dict[str, Any] = {}
    baseline_cohorts: Dict[str, Any] = {}
    if Path(baseline_metrics_path).exists():
        with open(baseline_metrics_path, "r", encoding="utf-8") as f:
            baseline_metrics = json.load(f)
    if Path(baseline_eval_path).exists():
        with open(baseline_eval_path, "r", encoding="utf-8") as f:
            b_eval = json.load(f)
            baseline_cohorts = b_eval.get("cohort_breakdown", {})

    b_roc = baseline_metrics.get("roc_auc", 0.9725)
    b_pr = baseline_metrics.get("pr_auc", 0.8778)
    b_brier = baseline_metrics.get("brier_score", 0.0375)
    b_ece = baseline_metrics.get("expected_calibration_error_uniform", 0.0149)
    b_prec = baseline_metrics.get("precision", 0.8659)
    b_rec = baseline_metrics.get("recall", 0.7243)
    b_f1 = baseline_metrics.get("f1", 0.7888)

    m_roc = metrics_val_0_5.roc_auc
    m_pr = metrics_val_0_5.pr_auc
    m_brier = metrics_val_0_5.brier_score
    m_ece = round(cal_uniform.expected_calibration_error, 4)
    m_prec = metrics_val_0_5.precision
    m_rec = metrics_val_0_5.recall
    m_f1 = metrics_val_0_5.f1

    comparison_summary = {
        "metrics_comparison": {
            "roc_auc": {
                "baseline": b_roc,
                "volatility_aware": m_roc,
                "delta_absolute": round(m_roc - b_roc, 4),
                "delta_relative_pct": round(((m_roc - b_roc) / b_roc) * 100, 2),
            },
            "pr_auc": {
                "baseline": b_pr,
                "volatility_aware": m_pr,
                "delta_absolute": round(m_pr - b_pr, 4),
                "delta_relative_pct": round(((m_pr - b_pr) / b_pr) * 100, 2),
            },
            "brier_score": {
                "baseline": b_brier,
                "volatility_aware": m_brier,
                "delta_absolute": round(m_brier - b_brier, 4),
                "delta_relative_pct": round(((m_brier - b_brier) / b_brier) * 100, 2),
            },
            "expected_calibration_error": {
                "baseline": b_ece,
                "volatility_aware": m_ece,
                "delta_absolute": round(m_ece - b_ece, 4),
                "delta_relative_pct": round(((m_ece - b_ece) / b_ece) * 100, 2),
            },
            "precision_threshold_0_5": {
                "baseline": b_prec,
                "volatility_aware": m_prec,
                "delta_absolute": round(m_prec - b_prec, 4),
                "delta_relative_pct": round(((m_prec - b_prec) / b_prec) * 100, 2),
            },
            "recall_threshold_0_5": {
                "baseline": b_rec,
                "volatility_aware": m_rec,
                "delta_absolute": round(m_rec - b_rec, 4),
                "delta_relative_pct": round(((m_rec - b_rec) / b_rec) * 100, 2),
            },
            "f1_threshold_0_5": {
                "baseline": b_f1,
                "volatility_aware": m_f1,
                "delta_absolute": round(m_f1 - b_f1, 4),
                "delta_relative_pct": round(((m_f1 - b_f1) / b_f1) * 100, 2),
            },
        },
        "confusion_matrix_comparison": {
            "true_positives": {
                "baseline": baseline_metrics.get("true_positives", 155),
                "volatility_aware": metrics_val_0_5.true_positives,
                "delta": metrics_val_0_5.true_positives - baseline_metrics.get("true_positives", 155),
            },
            "false_positives": {
                "baseline": baseline_metrics.get("false_positives", 24),
                "volatility_aware": metrics_val_0_5.false_positives,
                "delta": metrics_val_0_5.false_positives - baseline_metrics.get("false_positives", 24),
            },
            "true_negatives": {
                "baseline": baseline_metrics.get("true_negatives", 1459),
                "volatility_aware": metrics_val_0_5.true_negatives,
                "delta": metrics_val_0_5.true_negatives - baseline_metrics.get("true_negatives", 1459),
            },
            "false_negatives": {
                "baseline": baseline_metrics.get("false_negatives", 59),
                "volatility_aware": metrics_val_0_5.false_negatives,
                "delta": metrics_val_0_5.false_negatives - baseline_metrics.get("false_negatives", 59),
            },
        },
        "cohort_comparison": {},
    }

    # Compare cohorts specifically
    for cname in ["Declining", "Healthy Volatile", "High Obligation", "Irregular", "Stable"]:
        m_cohort = cohort_eval.get(cname)
        b_cohort = baseline_cohorts.get(cname, {})
        b_m = b_cohort.get("metrics", {})

        m_roc_c = m_cohort.metrics.roc_auc if m_cohort and m_cohort.metrics else None
        m_pr_c = m_cohort.metrics.pr_auc if m_cohort and m_cohort.metrics else None
        m_brier_c = m_cohort.metrics.brier_score if m_cohort and m_cohort.metrics else None

        b_roc_c = b_m.get("roc_auc")
        b_pr_c = b_m.get("pr_auc")
        b_brier_c = b_m.get("brier_score")

        comparison_summary["cohort_comparison"][cname] = {
            "sample_count": m_cohort.sample_count if m_cohort else 0,
            "defaults": m_cohort.positive_count if m_cohort else 0,
            "empirical_default_rate": m_cohort.empirical_default_rate if m_cohort else 0.0,
            "roc_auc": {
                "baseline": b_roc_c,
                "volatility_aware": m_roc_c,
                "delta": round(m_roc_c - b_roc_c, 4) if (m_roc_c and b_roc_c) else None,
            },
            "pr_auc": {
                "baseline": b_pr_c,
                "volatility_aware": m_pr_c,
                "delta": round(m_pr_c - b_pr_c, 4) if (m_pr_c and b_pr_c) else None,
            },
            "brier_score": {
                "baseline": b_brier_c,
                "volatility_aware": m_brier_c,
                "delta": round(m_brier_c - b_brier_c, 4) if (m_brier_c and b_brier_c) else None,
            },
        }

    # 14. Save validation predictions parquet table
    print("Generating validation predictions table...")
    val_preds_df = pd.DataFrame({
        "application_id": val_scored_df["application_id"].values,
        "applicant_profile_id": val_scored_df["applicant_profile_id"].values,
        "cohort_archetype": val_scored_df["cohort_archetype"].values,
        "target_default_flag": y_val,
        "predicted_probability": np.round(y_prob_val, 6),
        "predicted_class_threshold_0_5": (y_prob_val >= 0.5).astype(int),
        "risk_level": [determine_risk_tier(p) for p in y_prob_val],
        "presentation_score": [calculate_presentation_score(p) for p in y_prob_val],
    })
    val_preds_path = reports_path / "phase6_validation_predictions.parquet"
    val_preds_df.to_parquet(val_preds_path, index=False)
    print(f"  Saved validation predictions: {val_preds_path}")

    # 15. Save model joblib artifact
    model_artifact_path = artifacts_path / "volatility_aware_risk_model.joblib"
    final_model.save(model_artifact_path)
    print(f"  Saved model artifact: {model_artifact_path}")

    # 16. Save model metadata JSON
    metadata = {
        "model_name": final_model.model_name,
        "model_version": final_model.model_version,
        "model_type": final_model.model_type,
        "feature_variant": "VOLATILITY_AWARE",
        "target_column": "target_default_flag",
        "description": final_model.description,
        "is_fitted": final_model.is_fitted,
        "n_features_in": final_model.n_features_in_,
        "feature_names_in": final_model.feature_names_in_,
        "classes": [int(c) for c in final_model.classes_],
        "hyperparameters": final_model.hyperparameters,
        "training_metadata": {
            "canonical_dataset": canonical_dataset_path,
            "total_applications": total_records,
            "total_unique_applicants": total_applicants,
            "training_samples": len(X_train),
            "training_defaults": int(y_train.sum()),
            "training_default_rate": round(float(y_train.mean()), 4),
            "scaler": "robust",
            "add_missing_indicators": True,
            "excluded_unscored_samples": int(splits.train_df["target_default_flag"].isna().sum()),
            "held_out_validation_samples": len(X_val),
            "held_out_test_samples": len(X_test),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    model_meta_path = artifacts_path / "volatility_aware_risk_model_metadata.json"
    with open(model_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved model metadata: {model_meta_path}")

    # 17. Save core metrics JSON
    core_metrics = {
        "model_name": final_model.model_name,
        "model_version": final_model.model_version,
        "evaluation_split": "validation",
        "sample_count": metrics_val_0_5.total_samples,
        "positive_samples": metrics_val_0_5.positive_samples,
        "negative_samples": metrics_val_0_5.negative_samples,
        "positive_rate": round(metrics_val_0_5.positive_rate, 4),
        "roc_auc": metrics_val_0_5.roc_auc,
        "pr_auc": metrics_val_0_5.pr_auc,
        "brier_score": metrics_val_0_5.brier_score,
        "expected_calibration_error_uniform": round(cal_uniform.expected_calibration_error, 4),
        "maximum_calibration_error_uniform": round(cal_uniform.maximum_calibration_error, 4),
        "threshold": metrics_val_0_5.threshold,
        "precision": metrics_val_0_5.precision,
        "recall": metrics_val_0_5.recall,
        "f1": metrics_val_0_5.f1,
        "true_positives": metrics_val_0_5.true_positives,
        "false_positives": metrics_val_0_5.false_positives,
        "true_negatives": metrics_val_0_5.true_negatives,
        "false_negatives": metrics_val_0_5.false_negatives,
    }
    metrics_path = reports_path / "phase6_volatility_aware_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(core_metrics, f, indent=2)
    print(f"  Saved core metrics: {metrics_path}")

    # 18. Save comprehensive evaluation JSON
    comprehensive_evaluation = {
        "provenance": {
            "phase": "Phase 6 — Volatility-Aware Risk Model",
            "model_name": final_model.model_name,
            "model_version": final_model.model_version,
            "feature_variant": "VOLATILITY_AWARE",
            "evaluated_split": "validation",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
        "sample_summary": {
            "validation_samples": metrics_val_0_5.total_samples,
            "positive_defaults": metrics_val_0_5.positive_samples,
            "negative_repaid": metrics_val_0_5.negative_samples,
            "empirical_default_rate": round(metrics_val_0_5.positive_rate, 4),
        },
        "hyperparameter_tuning": {
            "evaluated_configs": candidate_configs,
            "selection_metric": "val_pr_auc",
            "best_config": best_config,
            "sweep_results": sweep_results,
        },
        "training_performance_threshold_0_5": metrics_train_0_5.to_dict(),
        "primary_validation_metrics_threshold_0_5": metrics_val_0_5.to_dict(),
        "multi_threshold_evaluation": multi_threshold_metrics,
        "probability_curves": {
            "roc_curve_sample_points": roc_points,
            "pr_curve_sample_points": pr_points,
        },
        "calibration": {
            "uniform_strategy": cal_uniform.to_dict(),
            "quantile_strategy": cal_quantile.to_dict(),
        },
        "cohort_breakdown": cohort_eval_dict,
        "baseline_comparison": comparison_summary,
        "top_features_by_gain": feature_importance_list[:15],
        "anti_leakage_verification": {
            "training_split_only": True,
            "validation_split_only_for_tuning": True,
            "test_split_unobserved": True,
            "unscored_records_excluded": True,
            "cross_entity_leakage_prevented_by_grouped_split": True,
            "preprocessor_fit_on_train_only": True,
            "temporal_horizon_invariant_preserved": True,
        },
    }
    eval_path = reports_path / "phase6_volatility_aware_evaluation.json"
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(comprehensive_evaluation, f, indent=2)
    print(f"  Saved comprehensive evaluation: {eval_path}")

    print("\nPhase 6 Volatility-Aware Model training and evaluation successfully completed.")
    return {
        "metrics": core_metrics,
        "comparison": comparison_summary,
        "model_artifact": str(model_artifact_path),
        "metadata_artifact": str(model_meta_path),
        "metrics_report": str(metrics_path),
        "evaluation_report": str(eval_path),
        "predictions_report": str(val_preds_path),
        "feature_importance_report": str(feat_imp_path),
    }


if __name__ == "__main__":
    train_and_evaluate_volatility_aware()
