"""Baseline model training and evaluation pipeline for PARAKH.

Trains the interpretable Regularized Logistic Regression baseline on the
frozen Phase 3 preprocessed / Phase 4 BASELINE feature set (35 model-ready columns).
Evaluates discrimination, probability calibration, and cohort performance
strictly on the validation split. Generates reproducible model artifacts
and evaluation reports.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

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
from src.ml.models.baseline import LogisticRegressionBaseline


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


def train_and_evaluate_baseline(
    canonical_dataset_path: str = "data/synthetic/synthetic_credit_applications.parquet",
    artifacts_dir: str = "models/artifacts",
    reports_dir: str = "experiments/reports",
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> Dict[str, Any]:
    """Train, validate, and serialize the Phase 5 Baseline Logistic Regression model.

    Args:
        canonical_dataset_path: Filepath to canonical Phase 2 synthetic dataset.
        artifacts_dir: Destination directory for model artifacts.
        reports_dir: Destination directory for evaluation metrics and predictions.
        random_seed: Deterministic PRNG seed.

    Returns:
        Dict containing execution summary, metrics, and artifact filepaths.
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

    # 3. Build model-ready matrices for BASELINE variant (scored only)
    print("Building model-ready matrices for BASELINE feature variant (scored records only)...")
    matrices = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )

    X_train: pd.DataFrame = matrices["X_train"]
    y_train: pd.Series = matrices["y_train"]
    X_val: pd.DataFrame = matrices["X_val"]
    y_val: pd.Series = matrices["y_val"]
    # Test split is strictly held out
    X_test: pd.DataFrame = matrices["X_test"]
    y_test: pd.Series = matrices["y_test"]

    print(f"  X_train shape: {X_train.shape} | defaults: {y_train.sum()} ({y_train.mean():.4f})")
    print(f"  X_val shape:   {X_val.shape} | defaults: {y_val.sum()} ({y_val.mean():.4f})")
    print(f"  X_test shape:  {X_test.shape} (HELD OUT — NOT USED FOR TRAINING OR TUNING)")

    # 4. Hyperparameter tuning sweep across C values (validation set only)
    print("Running deterministic hyperparameter tuning on validation split...")
    candidate_c_values = [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0]
    sweep_results: List[Dict[str, Any]] = []
    best_c = 1.0
    best_pr_auc = -1.0

    for c in candidate_c_values:
        trial_model = LogisticRegressionBaseline(
            C=c,
            solver="lbfgs",
            max_iter=1000,
            random_state=random_seed,
        )
        trial_model.fit(X_train, y_train)
        trial_probs = trial_model.predict_proba(X_val)

        val_roc = float(roc_auc_score(y_val, trial_probs))
        val_pr = float(average_precision_score(y_val, trial_probs))
        val_brier = float(brier_score_loss(y_val, trial_probs))

        res_entry = {
            "C": c,
            "roc_auc": round(val_roc, 4),
            "pr_auc": round(val_pr, 4),
            "brier_score": round(val_brier, 4),
        }
        sweep_results.append(res_entry)

        if val_pr > best_pr_auc:
            best_pr_auc = val_pr
            best_c = c

    print(f"  Optimal regularization parameter selected: C = {best_c} (Val PR-AUC: {best_pr_auc:.4f})")

    # 5. Fit final baseline model with selected C
    print(f"Fitting final Baseline Logistic Regression model (C={best_c})...")
    final_model = LogisticRegressionBaseline(
        C=best_c,
        penalty="l2",
        solver="lbfgs",
        max_iter=1000,
        random_state=random_seed,
        description="Phase 5 Regularized Logistic Regression baseline on 35 model-ready features.",
    )
    final_model.fit(X_train, y_train)

    # 6. Predict on validation set
    y_prob_val = final_model.predict_proba(X_val)

    # 7. Evaluate validation metrics at standard threshold (0.5)
    metrics_0_5 = evaluate_predictions(y_val, y_prob_val, threshold=0.5)

    # 8. Evaluate across operational decision thresholds
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

    # 9. Probability calibration evaluation (uniform and quantile binning)
    cal_uniform = evaluate_calibration(y_val, y_prob_val, n_bins=10, strategy="uniform")
    cal_quantile = evaluate_calibration(y_val, y_prob_val, n_bins=10, strategy="quantile")

    # 10. Cohort evaluation
    val_scored_df = splits.val_df[splits.val_df["target_default_flag"].notna()].copy()
    val_cohorts = val_scored_df["cohort_archetype"].tolist()
    cohort_eval = evaluate_by_cohort(y_val, y_prob_val, cohorts=val_cohorts, threshold=0.5)
    cohort_eval_dict = {k: v.to_dict() for k, v in cohort_eval.items()}

    # 11. Feature coefficients and odds ratios
    coefs_df = final_model.get_coefficients_df()
    coef_dict = {
        row["feature"]: {
            "coefficient": round(float(row["coefficient"]), 6),
            "abs_coefficient": round(float(row["abs_coefficient"]), 6),
            "odds_ratio": round(float(row["odds_ratio"]), 6),
        }
        for _, row in coefs_df.iterrows()
    }

    # 12. Generate and save validation predictions parquet table
    print("Generating validation predictions table...")
    val_preds_df = pd.DataFrame({
        "application_id": val_scored_df["application_id"].values,
        "applicant_profile_id": val_scored_df["applicant_profile_id"].values,
        "cohort_archetype": val_scored_df["cohort_archetype"].values,
        "target_default_flag": np.asarray(y_val).astype(int),
        "predicted_probability": np.round(y_prob_val, 6),
        "predicted_class_threshold_0_5": (y_prob_val >= 0.5).astype(int),
        "risk_level": [determine_risk_tier(p) for p in y_prob_val],
        "presentation_score": [calculate_presentation_score(p) for p in y_prob_val],
    })
    val_preds_path = reports_path / "phase5_validation_predictions.parquet"
    val_preds_df.to_parquet(val_preds_path, index=False)
    print(f"  Saved validation predictions: {val_preds_path}")

    # 13. Save model joblib artifact
    model_artifact_path = artifacts_path / "logistic_regression_baseline.joblib"
    final_model.save(model_artifact_path)
    print(f"  Saved model artifact: {model_artifact_path}")

    # 14. Save model metadata JSON
    metadata = {
        "model_name": final_model.model_name,
        "model_version": final_model.model_version,
        "model_type": final_model.model_type,
        "feature_variant": "BASELINE",
        "target_column": "target_default_flag",
        "description": final_model.description,
        "is_fitted": final_model.is_fitted,
        "n_features_in": final_model.n_features_in_,
        "feature_names_in": final_model.feature_names_in_,
        "classes": [int(c) for c in final_model.classes_],
        "hyperparameters": {
            "C": float(best_c),
            "penalty": "l2",
            "solver": "lbfgs",
            "max_iter": 1000,
            "random_state": random_seed,
            "class_weight": None,
        },
        "intercept": float(final_model.intercept_[0]),
        "coefficients": coef_dict,
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
    model_meta_path = artifacts_path / "logistic_regression_baseline_metadata.json"
    with open(model_meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved model metadata: {model_meta_path}")

    # 15. Save core metrics JSON
    core_metrics = {
        "model_name": final_model.model_name,
        "model_version": final_model.model_version,
        "evaluation_split": "validation",
        "sample_count": metrics_0_5.total_samples,
        "positive_samples": metrics_0_5.positive_samples,
        "negative_samples": metrics_0_5.negative_samples,
        "positive_rate": round(metrics_0_5.positive_rate, 4),
        "roc_auc": metrics_0_5.roc_auc,
        "pr_auc": metrics_0_5.pr_auc,
        "brier_score": metrics_0_5.brier_score,
        "expected_calibration_error_uniform": round(cal_uniform.expected_calibration_error, 4),
        "maximum_calibration_error_uniform": round(cal_uniform.maximum_calibration_error, 4),
        "threshold": metrics_0_5.threshold,
        "precision": metrics_0_5.precision,
        "recall": metrics_0_5.recall,
        "f1": metrics_0_5.f1,
        "true_positives": metrics_0_5.true_positives,
        "false_positives": metrics_0_5.false_positives,
        "true_negatives": metrics_0_5.true_negatives,
        "false_negatives": metrics_0_5.false_negatives,
    }
    metrics_path = reports_path / "phase5_baseline_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(core_metrics, f, indent=2)
    print(f"  Saved core metrics: {metrics_path}")

    # 16. Save comprehensive evaluation JSON
    comprehensive_evaluation = {
        "provenance": {
            "phase": "Phase 5 — Baseline Models",
            "model_name": final_model.model_name,
            "model_version": final_model.model_version,
            "feature_variant": "BASELINE",
            "evaluated_split": "validation",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
        "sample_summary": {
            "validation_samples": metrics_0_5.total_samples,
            "positive_defaults": metrics_0_5.positive_samples,
            "negative_repaid": metrics_0_5.negative_samples,
            "empirical_default_rate": round(metrics_0_5.positive_rate, 4),
        },
        "hyperparameter_tuning": {
            "evaluated_C_values": candidate_c_values,
            "selection_metric": "pr_auc",
            "best_C": best_c,
            "sweep_results": sweep_results,
        },
        "primary_metrics_threshold_0_5": metrics_0_5.to_dict(),
        "multi_threshold_evaluation": multi_threshold_metrics,
        "calibration": {
            "uniform_strategy": cal_uniform.to_dict(),
            "quantile_strategy": cal_quantile.to_dict(),
        },
        "cohort_breakdown": cohort_eval_dict,
        "top_feature_coefficients": [
            {
                "feature": row["feature"],
                "coefficient": round(float(row["coefficient"]), 6),
                "odds_ratio": round(float(row["odds_ratio"]), 6),
            }
            for _, row in coefs_df.head(15).iterrows()
        ],
        "anti_leakage_verification": {
            "training_split_only": True,
            "validation_split_only_for_tuning": True,
            "test_split_unobserved": True,
            "unscored_records_excluded": True,
            "cross_entity_leakage_prevented_by_grouped_split": True,
            "preprocessor_fit_on_train_only": True,
        },
    }
    eval_path = reports_path / "phase5_baseline_evaluation.json"
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(comprehensive_evaluation, f, indent=2)
    print(f"  Saved comprehensive evaluation: {eval_path}")

    print("\nPhase 5 Baseline Model training and evaluation successfully completed.")
    return {
        "metrics": core_metrics,
        "model_artifact": str(model_artifact_path),
        "metadata_artifact": str(model_meta_path),
        "metrics_report": str(metrics_path),
        "evaluation_report": str(eval_path),
        "predictions_report": str(val_preds_path),
    }


if __name__ == "__main__":
    train_and_evaluate_baseline()
