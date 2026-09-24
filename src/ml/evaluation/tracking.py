"""Lightweight reproducible experiment tracking metadata structures for PARAKH.

Provides structured JSON serialization and tracking for model evaluation runs,
hyperparameters, dataset versions, and cohort metrics without heavy external dependencies.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class ExperimentMetadata:
    """Standardized metadata record for an ML experiment run."""

    experiment_id: str
    experiment_name: str
    dataset_version: str
    feature_version: str
    model_type: str
    model_version: str
    hyperparameters: Dict[str, Any]
    random_seed: int
    evaluation_timestamp: str
    metrics: Dict[str, Any]

    # Optional metadata
    training_timestamp: Optional[str] = None
    cohort_metrics: Optional[Dict[str, Any]] = None
    subgroup_metrics: Optional[Dict[str, Any]] = None
    feature_names: Optional[List[str]] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize metadata to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save_to_file(self, filepath: Union[str, Path]) -> Path:
        """Persist metadata to a JSON file.

        Args:
            filepath: Destination file path.

        Returns:
            Path: Confirmed path where metadata was saved.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return path

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentMetadata":
        """Deserialize from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ExperimentMetadata":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def load_from_file(cls, filepath: Union[str, Path]) -> "ExperimentMetadata":
        """Load experiment metadata from a JSON file.

        Args:
            filepath: Path to the JSON metadata file.

        Returns:
            ExperimentMetadata instance.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"Experiment metadata file not found at: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
