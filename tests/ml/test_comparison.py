"""Unit tests for the volatility-aware model comparison framework."""
from src.ml.constants import CohortArchetype
from src.ml.evaluation.comparison import compare_models
from src.ml.evaluation.tracking import ExperimentMetadata


def test_model_comparison_framework():
    # Construct mock metadata for Experiment A (Baseline)
    baseline_meta = ExperimentMetadata(
        experiment_id="exp-baseline-001",
        experiment_name="Baseline Logistic Regression",
        dataset_version="v1.0",
        feature_version="feat-v1.0",
        model_type="LOGISTIC_REGRESSION",
        model_version="0.1.0",
        hyperparameters={"C": 1.0},
        random_seed=42,
        evaluation_timestamp="2026-09-23T00:00:00Z",
        metrics={
            "roc_auc": 0.7200,
            "pr_auc": 0.3500,
            "brier_score": 0.1800,
            "precision": 0.6000,
            "recall": 0.5000,
            "f1": 0.5455,
        },
        cohort_metrics={
            CohortArchetype.HEALTHY_VOLATILE.value: {
                "sample_count": 50,
                "empirical_default_rate": 0.0600,
                "metrics": {
                    "roc_auc": 0.6500,
                    "pr_auc": 0.2000,
                    "brier_score": 0.1500,
                    "positive_rate": 0.2500,  # Falsely penalizing 25% as defaults
                },
            },
            CohortArchetype.DECLINING.value: {
                "sample_count": 40,
                "empirical_default_rate": 0.3000,
                "metrics": {
                    "recall": 0.6000,
                    "positive_rate": 0.2500,
                },
            },
        },
    )

    # Construct mock metadata for Experiment B (Volatility-Aware)
    vol_meta = ExperimentMetadata(
        experiment_id="exp-volaware-002",
        experiment_name="Volatility-Aware Gradient Boosting",
        dataset_version="v1.0",
        feature_version="feat-v2.0-volatility",
        model_type="HIST_GRADIENT_BOOSTING",
        model_version="0.2.0",
        hyperparameters={"max_iter": 100},
        random_seed=42,
        evaluation_timestamp="2026-09-23T01:00:00Z",
        metrics={
            "roc_auc": 0.7850,
            "pr_auc": 0.4350,
            "brier_score": 0.1350,
            "precision": 0.6800,
            "recall": 0.6200,
            "f1": 0.6486,
        },
        cohort_metrics={
            CohortArchetype.HEALTHY_VOLATILE.value: {
                "sample_count": 50,
                "empirical_default_rate": 0.0600,
                "metrics": {
                    "roc_auc": 0.7500,
                    "pr_auc": 0.3200,
                    "brier_score": 0.0900,
                    "positive_rate": 0.0800,  # Accurately dropping false positive defaults
                },
            },
            CohortArchetype.DECLINING.value: {
                "sample_count": 40,
                "empirical_default_rate": 0.3000,
                "metrics": {
                    "recall": 0.8500,
                    "positive_rate": 0.3500,
                },
            },
        },
    )

    comparison = compare_models(baseline_meta, vol_meta)

    assert comparison.baseline_id == "exp-baseline-001"
    assert comparison.volatility_aware_id == "exp-volaware-002"

    # Global metric deltas
    assert comparison.global_metric_deltas["delta_roc_auc"] == round(0.7850 - 0.7200, 4)
    assert comparison.global_metric_deltas["delta_brier_score"] == round(0.1350 - 0.1800, 4)

    # Healthy Volatile focus
    hv_impact = comparison.healthy_volatile_impact
    assert hv_impact["cohort_name"] == CohortArchetype.HEALTHY_VOLATILE.value
    # In volatility-aware model, predicted default rate dropped from 0.25 to 0.08
    assert hv_impact["delta_predicted_default_rate"] == round(0.0800 - 0.2500, 4)

    # Declining cohort focus
    dec_impact = comparison.declining_cohort_impact
    assert dec_impact["delta_recall"] == round(0.8500 - 0.6000, 4)

    d = comparison.to_dict()
    assert "global_metric_deltas" in d
    assert "cohort_deltas" in d
