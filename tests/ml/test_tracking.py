"""Unit tests for experiment tracking metadata serialization and persistence."""
from pathlib import Path

from src.ml.evaluation.tracking import ExperimentMetadata


def test_experiment_metadata_serialization(tmp_path: Path):
    meta = ExperimentMetadata(
        experiment_id="exp-20260923-001",
        experiment_name="Baseline Model Evaluation",
        dataset_version="synthetic-v1.0",
        feature_version="feat-base-v1.0",
        model_type="LOGISTIC_REGRESSION",
        model_version="1.0.0",
        hyperparameters={"C": 0.5, "penalty": "l2"},
        random_seed=42,
        evaluation_timestamp="2026-09-23T02:00:00Z",
        metrics={"roc_auc": 0.74, "pr_auc": 0.38, "brier_score": 0.16},
        notes="Testing lightweight experiment tracker",
    )

    json_str = meta.to_json()
    assert "exp-20260923-001" in json_str
    assert "synthetic-v1.0" in json_str

    deserialized = ExperimentMetadata.from_json(json_str)
    assert deserialized.experiment_id == meta.experiment_id
    assert deserialized.metrics == meta.metrics
    assert deserialized.hyperparameters == meta.hyperparameters

    # File persistence test
    out_file = tmp_path / "reports" / "exp_001.json"
    saved_path = meta.save_to_file(out_file)
    assert saved_path.is_file()

    loaded = ExperimentMetadata.load_from_file(saved_path)
    assert loaded.experiment_id == meta.experiment_id
    assert loaded.random_seed == 42
