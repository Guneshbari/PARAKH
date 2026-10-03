"""Common utilities, data loaders, cohort definitions, and integrity verifiers for Phase 19.

Provides shared constants, hash checkers, evaluation loaders, bootstrap confidence interval
calculators, and synthetic data disclaimers for the PARAKH Real-World Impact Benchmark.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.ml.config import PROJECT_ROOT, set_seed
from src.ml.constants import (
    DEFAULT_RANDOM_SEED,
    PRESENTATION_SCORE_MAX,
    PRESENTATION_SCORE_MIN,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
    ExperimentVariant,
    RiskTier,
)
from src.ml.data.splitting import GroupedDatasetSplitter, GroupedSplitResult
from src.ml.features.feature_engineering import build_model_ready_matrices
from src.ml.models.baseline import LogisticRegressionBaseline
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


# -----------------------------------------------------------------------------
# Benchmark Paths & Constants
# -----------------------------------------------------------------------------
BENCHMARK_DIR: Path = PROJECT_ROOT / "experiments" / "benchmarks" / "impact"
RESULTS_DIR: Path = BENCHMARK_DIR / "results"
REPORTS_DIR: Path = BENCHMARK_DIR / "reports"
DATA_DIR: Path = BENCHMARK_DIR / "data"

CANONICAL_DATASET_PATH: Path = (
    PROJECT_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet"
)
BASELINE_MODEL_PATH: Path = (
    PROJECT_ROOT / "models" / "artifacts" / "logistic_regression_baseline.joblib"
)
BASELINE_METADATA_PATH: Path = (
    PROJECT_ROOT / "models" / "artifacts" / "logistic_regression_baseline_metadata.json"
)
VOLATILITY_MODEL_PATH: Path = (
    PROJECT_ROOT / "models" / "artifacts" / "volatility_aware_risk_model.joblib"
)
VOLATILITY_METADATA_PATH: Path = (
    PROJECT_ROOT / "models" / "artifacts" / "volatility_aware_risk_model_metadata.json"
)
PREPROCESSOR_PATH: Path = (
    PROJECT_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib"
)
MANIFEST_PATH: Path = PROJECT_ROOT / "models" / "artifacts" / "FINAL_MODEL.json"

FROZEN_ARTIFACT_HASHES: Dict[str, str] = {
    "models/artifacts/volatility_aware_risk_model.joblib": "88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060",
    "models/artifacts/FINAL_MODEL.json": "e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f",
    "models/artifacts/credit_risk_preprocessor.joblib": "bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2",
}

MANDATORY_SYNTHETIC_DISCLAIMER: str = (
    "MANDATORY SCIENTIFIC & REGULATORY DISCLAIMER: The evaluations, portfolio simulations, "
    "approval rates, expected-loss estimates, and financial inclusion coverage numbers reported "
    "herein are controlled synthetic benchmarks derived from synthetic gig-worker profiles and "
    "held-out test partitions. They do not constitute actual commercial banking outcomes, "
    "empirical bank-loss reductions, regulatory compliance approvals, or legal fair-lending certification."
)


# -----------------------------------------------------------------------------
# Integrity Verification
# -----------------------------------------------------------------------------
def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Compute hex SHA-256 digest of a file."""
    p = Path(filepath)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_frozen_hashes() -> Dict[str, bool]:
    """Verify that frozen model artifacts have not been modified.

    Returns:
        Dict mapping artifact path to validation status (True if match).

    Raises:
        RuntimeError: If any frozen artifact hash does not match expected value.
    """
    results: Dict[str, bool] = {}
    mismatches: List[str] = []

    for rel_path, expected_hash in FROZEN_ARTIFACT_HASHES.items():
        actual_hash = compute_file_sha256(rel_path)
        is_match = (actual_hash == expected_hash)
        results[rel_path] = is_match
        if not is_match:
            mismatches.append(
                f"{rel_path}: expected {expected_hash}, got {actual_hash}"
            )

    if mismatches:
        err_msg = "FROZEN ARTIFACT INTEGRITY VIOLATION:\n" + "\n".join(mismatches)
        raise RuntimeError(err_msg)

    return results


# -----------------------------------------------------------------------------
# Cohort Definitions (Step 3)
# -----------------------------------------------------------------------------
# Observable feature boundary rules for the Four Impact Cohorts:
# 1. Stable: Low income volatility (CV <= 0.22), reasonable recovery (bounceback >= 0.8),
#    manageable debt (DTI <= 0.35), adequate liquidity (buffer >= 0.20).
# 2. Healthy Volatile: High income volatility (CV > 0.22), strong recovery (bounceback >= 1.0),
#    reasonable debt (DTI <= 0.35), adequate liquidity (buffer >= 0.25).
# 3. Distressed Volatile: High income volatility (CV > 0.22), poor recovery (bounceback < 0.90)
#    and/or high debt burden (DTI > 0.35) or weak liquidity (buffer < 0.25).
# 4. Weak Income: Lower baseline earnings (feat_inc_median_90d <= 4000.0, bottom ~30% of distribution).

COHORT_RULES_DOCUMENTATION: Dict[str, Any] = {
    "stable": {
        "description": "Low income volatility with reasonable recovery, manageable debt, and adequate liquidity.",
        "purpose": "Reference population representing traditional predictable income earners.",
        "rules": [
            "feat_inc_cv_90d <= 0.22",
            "feat_bur_total_dti <= 0.35",
            "feat_liq_buffer_to_loan >= 0.20",
            "feat_rec_bounceback_ratio >= 0.80",
        ],
    },
    "healthy_volatile": {
        "description": "High income volatility combined with strong recovery, reasonable debt burden, and adequate liquidity.",
        "purpose": "Test whether volatility-aware modeling avoids unnecessarily penalizing healthy gig-worker income variability.",
        "rules": [
            "feat_inc_cv_90d > 0.22",
            "feat_rec_bounceback_ratio >= 1.00",
            "feat_bur_total_dti <= 0.35",
            "feat_liq_buffer_to_loan >= 0.25",
        ],
    },
    "distressed_volatile": {
        "description": "High income volatility combined with poor recovery, high debt burden, and/or weak liquidity.",
        "purpose": "Test whether the model still identifies genuinely concerning volatile profiles.",
        "rules": [
            "feat_inc_cv_90d > 0.22",
            "(feat_rec_bounceback_ratio < 0.90) OR (feat_bur_total_dti > 0.35) OR (feat_liq_buffer_to_loan < 0.25)",
        ],
    },
    "weak_income": {
        "description": "Lower earning baseline with varying degrees of volatility and recovery.",
        "purpose": "Provide an additional comparison cohort and avoid making the benchmark solely about volatility.",
        "rules": [
            "feat_inc_median_90d <= 4000.0",
        ],
    },
}


def assign_impact_cohorts(df: pd.DataFrame) -> pd.DataFrame:
    """Assign observable-feature-grounded impact cohorts to each application.

    Args:
        df: DataFrame containing pre-t0 features.

    Returns:
        DataFrame with added boolean cohort mask columns and primary_impact_cohort string.
    """
    out_df = df.copy()

    # Feature definitions
    cv = out_df["feat_inc_cv_90d"].fillna(0.0)
    bounceback = out_df["feat_rec_bounceback_ratio"].fillna(0.0)
    dti = out_df["feat_bur_total_dti"].fillna(0.0)
    buffer_ratio = out_df["feat_liq_buffer_to_loan"].fillna(0.0)
    median_inc = out_df["feat_inc_median_90d"].fillna(0.0)

    # Boolean masks
    is_stable = (cv <= 0.22) & (dti <= 0.35) & (buffer_ratio >= 0.20) & (bounceback >= 0.80)
    is_healthy_vol = (cv > 0.22) & (bounceback >= 1.00) & (dti <= 0.35) & (buffer_ratio >= 0.25)
    is_distressed_vol = (cv > 0.22) & ((bounceback < 0.90) | (dti > 0.35) | (buffer_ratio < 0.25))
    is_weak_income = (median_inc <= 4000.0)

    out_df["cohort_stable"] = is_stable
    out_df["cohort_healthy_volatile"] = is_healthy_vol
    out_df["cohort_distressed_volatile"] = is_distressed_vol
    out_df["cohort_weak_income"] = is_weak_income

    # Assign primary mutually exclusive category for primary reporting
    # Priority: Distressed Volatile > Healthy Volatile > Stable > Weak Income > Other
    primary = pd.Series("Other", index=out_df.index)
    primary[is_weak_income] = "Weak Income"
    primary[is_stable] = "Stable"
    primary[is_healthy_vol] = "Healthy Volatile"
    primary[is_distressed_vol] = "Distressed Volatile"
    out_df["primary_impact_cohort"] = primary

    return out_df


# -----------------------------------------------------------------------------
# Data & Model Loader
# -----------------------------------------------------------------------------
def load_benchmark_data_and_models(
    seed: int = DEFAULT_RANDOM_SEED,
) -> Dict[str, Any]:
    """Load canonical dataset, perform deterministic grouped split, load frozen models,
    and build exact test feature matrices.

    Args:
        seed: Deterministic random seed (default 42).

    Returns:
        Dict containing loaded models, metadata, splits, test DataFrames, feature matrices,
        and predictions.
    """
    set_seed(seed)
    verify_frozen_hashes()

    # Load models
    baseline_model: LogisticRegressionBaseline = joblib.load(BASELINE_MODEL_PATH)
    volatility_model: VolatilityAwareRiskModel = joblib.load(VOLATILITY_MODEL_PATH)

    with open(BASELINE_METADATA_PATH, "r") as f:
        baseline_meta = json.load(f)
    with open(VOLATILITY_METADATA_PATH, "r") as f:
        volatility_meta = json.load(f)
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    # Load dataset
    dataset_df = pd.read_parquet(CANONICAL_DATASET_PATH)
    splits: GroupedSplitResult = GroupedDatasetSplitter.split(dataset_df, seed=seed)

    # Build model-ready matrices
    matrices_base = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )
    matrices_vol = build_model_ready_matrices(
        train_df=splits.train_df,
        val_df=splits.val_df,
        test_df=splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )

    X_test_base = matrices_base["X_test"][baseline_model.feature_names_in_]
    X_test_vol = matrices_vol["X_test"][volatility_model.feature_names_in_]
    y_test = np.asarray(matrices_base["y_test"])

    # Extract scored test records
    test_scored_df = splits.test_df[splits.test_df["target_default_flag"].notnull()].copy().reset_index(drop=True)
    test_scored_df = assign_impact_cohorts(test_scored_df)

    # Predict probabilities
    p_base = baseline_model.predict_proba(X_test_base)
    p_vol = volatility_model.predict_proba(X_test_vol)

    test_scored_df["pred_prob_baseline"] = p_base
    test_scored_df["pred_prob_volatility"] = p_vol
    test_scored_df["score_baseline"] = [calculate_presentation_score(p) for p in p_base]
    test_scored_df["score_volatility"] = [calculate_presentation_score(p) for p in p_vol]
    test_scored_df["tier_baseline"] = [determine_risk_tier(p) for p in p_base]
    test_scored_df["tier_volatility"] = [determine_risk_tier(p) for p in p_vol]

    return {
        "dataset_df": dataset_df,
        "splits": splits,
        "test_df": test_scored_df,
        "baseline_model": baseline_model,
        "volatility_model": volatility_model,
        "baseline_meta": baseline_meta,
        "volatility_meta": volatility_meta,
        "manifest": manifest,
        "base_preprocessor": matrices_base["preprocessor"],
        "vol_preprocessor": joblib.load(PREPROCESSOR_PATH),
        "X_test_base": X_test_base,
        "X_test_vol": X_test_vol,
        "y_test": y_test,
        "p_base": p_base,
        "p_vol": p_vol,
    }


# -----------------------------------------------------------------------------
# Score & Tier Helpers
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Statistical & Bootstrap CI Helpers
# -----------------------------------------------------------------------------
def compute_bootstrap_ci(
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: int = DEFAULT_RANDOM_SEED,
) -> Tuple[float, float, float]:
    """Compute empirical point estimate and 95% bootstrap confidence interval.

    Args:
        metric_fn: Callable metric function accepting (y_true, y_pred).
        y_true: Array of ground-truth outcomes.
        y_pred: Array of predictions or probabilities.
        n_bootstraps: Number of bootstrap iterations (default 1000).
        alpha: Two-tailed significance level (0.05 yields 95% CI).
        seed: Random seed for deterministic resampling.

    Returns:
        Tuple of (point_estimate, ci_lower, ci_upper).
    """
    y_t = np.asarray(y_true)
    y_p = np.asarray(y_pred)
    n = len(y_t)
    if n == 0:
        return (0.0, 0.0, 0.0)

    try:
        point = float(metric_fn(y_t, y_p))
    except Exception:
        return (0.0, 0.0, 0.0)

    rng = np.random.default_rng(seed)
    boot_estimates: List[float] = []

    for _ in range(n_bootstraps):
        idx = rng.integers(0, n, size=n)
        sample_t = y_t[idx]
        sample_p = y_p[idx]
        # Skip if single-class when multi-class required
        if len(np.unique(sample_t)) < 2 and metric_fn in (roc_auc_score, average_precision_score):
            continue
        try:
            val = float(metric_fn(sample_t, sample_p))
            boot_estimates.append(val)
        except Exception:
            continue

    if not boot_estimates:
        return (point, point, point)

    lower = float(np.percentile(boot_estimates, 100 * (alpha / 2)))
    upper = float(np.percentile(boot_estimates, 100 * (1 - alpha / 2)))
    return (point, lower, upper)


def to_serializable(val: Any) -> Any:
    """Recursively convert NumPy, Pandas, and dataclass objects to JSON-serializable types."""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, np.ndarray):
        return [to_serializable(x) for x in val.tolist()]
    if isinstance(val, pd.Series):
        return [to_serializable(x) for x in val.tolist()]
    if isinstance(val, pd.DataFrame):
        return val.to_dict(orient="records")
    if isinstance(val, Path):
        return str(val)
    if isinstance(val, dict):
        return {str(k): to_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [to_serializable(x) for x in val]
    return val
