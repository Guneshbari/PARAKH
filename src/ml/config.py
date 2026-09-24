"""Configuration and reproducibility helpers for PARAKH ML experimentation.

Ensures deterministic execution, standard random seeds, and consistent
file paths across all ML experimentation and evaluation workflows.
"""
import os
from pathlib import Path
import random
from typing import Optional
import numpy as np

from src.ml.constants import DEFAULT_RANDOM_SEED

# Root directory of the repository
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

# ML Workspace directories
ML_DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = ML_DATA_DIR / "raw"
SYNTHETIC_DATA_DIR: Path = ML_DATA_DIR / "synthetic"
PROCESSED_DATA_DIR: Path = ML_DATA_DIR / "processed"

EXPERIMENTS_DIR: Path = PROJECT_ROOT / "experiments"
EXPERIMENT_REPORTS_DIR: Path = EXPERIMENTS_DIR / "reports"
NOTEBOOKS_DIR: Path = EXPERIMENTS_DIR / "notebooks"

MODELS_DIR: Path = PROJECT_ROOT / "models"
MODEL_ARTIFACTS_DIR: Path = MODELS_DIR / "artifacts"
MODEL_CHECKPOINTS_DIR: Path = MODELS_DIR / "checkpoints"


def set_seed(seed: int = DEFAULT_RANDOM_SEED) -> int:
    """Set global random seeds for deterministic execution across libraries.

    Args:
        seed: Integer random seed (default 42).

    Returns:
        int: The confirmed seed value.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    return seed
