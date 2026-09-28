"""Script to deterministically persist the fitted CreditRiskPreprocessor artifact.

Phase: 13A-4 (Closing gap P1-04)
Generates: models/artifacts/credit_risk_preprocessor.joblib
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import joblib
import pandas as pd

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.preprocessing import CreditRiskPreprocessor
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.features.feature_engineering import FeatureEngineer, build_model_ready_matrices

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATASET_PATH = _PROJECT_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet"
_ARTIFACT_PATH = _PROJECT_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib"


def generate_and_persist_preprocessor() -> Path:
    """Fit CreditRiskPreprocessor on the canonical training split and serialize to disk."""
    print(f"Loading canonical dataset from {_DATASET_PATH}...")
    if not _DATASET_PATH.exists():
        raise FileNotFoundError(f"Canonical dataset not found at '{_DATASET_PATH}'.")

    df = pd.read_parquet(_DATASET_PATH)
    print(f"Loaded {len(df)} rows from canonical dataset.")

    # 1. Deterministic grouped split (matching Phase 6 training protocol exactly)
    print("Partitioning dataset with GroupedDatasetSplitter (seed=42, scored_only=False)...")
    split = GroupedDatasetSplitter.split(df, seed=DEFAULT_RANDOM_SEED, scored_only=False)
    print(f"Training split size: {len(split.train_df)} rows.")

    # 2. Build model-ready matrices to fit the preprocessor
    print("Fitting CreditRiskPreprocessor on scored training observations...")
    pipeline_result = build_model_ready_matrices(
        train_df=split.train_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scaler_type="robust",
        add_missing_indicators=True,
        scored_only=True,
    )

    preprocessor: CreditRiskPreprocessor = pipeline_result["preprocessor"]

    if not getattr(preprocessor, "is_fitted_", False):
        raise RuntimeError("Fitted preprocessor reports is_fitted_=False!")

    # 3. Attach metadata to the preprocessor object
    metadata = {
        "model_name": "volatility-aware-risk-model",
        "model_version": "1.0.0",
        "feature_variant": "VOLATILITY_AWARE",
        "preprocessor_class": "src.ml.data.preprocessing.CreditRiskPreprocessor",
        "feature_contract": "v1.1.0",
        "training_commit": "2d47a35",
        "input_feature_count": 46,
        "output_feature_count": len(preprocessor.feature_names_out_),
        "scaler_type": preprocessor.scaler_type,
        "categorical_columns": list(preprocessor.categorical_feature_names_in_),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creation_phase": "Phase 13A-4: Persist Fitted Preprocessor for Deterministic Inference",
    }

    preprocessor.metadata_ = metadata
    preprocessor.model_name_ = "volatility-aware-risk-model"
    preprocessor.model_version_ = "1.0.0"
    preprocessor.feature_variant_ = "VOLATILITY_AWARE"
    preprocessor.training_commit_ = "2d47a35"

    # 4. Serialize preprocessor artifact
    _ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Serializing preprocessor artifact to {_ARTIFACT_PATH}...")
    joblib.dump(preprocessor, _ARTIFACT_PATH)

    # 5. Compute SHA-256 hash
    with open(_ARTIFACT_PATH, "rb") as fh:
        sha256_hash = hashlib.sha256(fh.read()).hexdigest()

    print(f"Artifact created successfully: {_ARTIFACT_PATH}")
    print(f"Artifact SHA-256: {sha256_hash}")

    # 6. Verify reload
    reloaded = joblib.load(_ARTIFACT_PATH)
    assert isinstance(reloaded, CreditRiskPreprocessor), f"Reloaded type mismatch: {type(reloaded)}"
    assert reloaded.is_fitted_, "Reloaded preprocessor reports is_fitted_=False"
    assert reloaded.model_version_ == "1.0.0", f"Reloaded version mismatch: {reloaded.model_version_}"
    assert len(reloaded.feature_names_out_) == 64, f"Output features count mismatch: {len(reloaded.feature_names_out_)}"
    print("Verification passed: Reloaded artifact matches all requirements.")

    return _ARTIFACT_PATH


if __name__ == "__main__":
    generate_and_persist_preprocessor()
