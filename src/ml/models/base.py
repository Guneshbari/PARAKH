"""Base abstraction and contract for PARAKH risk models.

Defines the common interface that all future risk models (Baseline Logistic Regression,
Tree Ensembles, and Volatility-Aware models) must implement.
No model training is performed in this phase.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np


class NotFittedError(Exception):
    """Raised when an estimator is used before fit has been called."""
    pass


class BaseRiskModel(ABC):
    """Abstract base class for all credit repayment risk models in PARAKH.

    Provides a uniform interface for fitting, probability prediction, and model metadata
    extraction to allow consistent comparison across baseline and volatility-aware models.
    """

    def __init__(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Initialize base model attributes.

        Args:
            model_name: Unique human-readable name of the model (e.g. 'baseline-logistic').
            model_version: Semantic version of the model specification/artifact.
            model_type: Model family identifier (e.g. 'LOGISTIC_REGRESSION', 'HIST_GRADIENT_BOOSTING').
            hyperparameters: Configuration dictionary passed to the underlying estimator.
            description: Concise description of model objectives and architecture.
        """
        self.model_name = model_name
        self.model_version = model_version
        self.model_type = model_type
        self.hyperparameters = hyperparameters or {}
        self.description = description or ""
        self.is_fitted: bool = False
        self.feature_names_in_: Optional[List[str]] = None

    @abstractmethod
    def fit(self, X: Any, y: Any, **kwargs: Any) -> "BaseRiskModel":
        """Fit the risk model to training features and ground truth labels.

        Args:
            X: Training feature matrix (DataFrame or 2D array).
            y: Binary repayment outcome labels (1 = default, 0 = repaid).
            **kwargs: Additional fitting options (sample weights, validation splits, etc.).

        Returns:
            self: Fitted estimator instance.
        """
        pass

    @abstractmethod
    def predict_proba(self, X: Any) -> np.ndarray:
        """Predict calibrated repayment risk probability P(Default | X).

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            np.ndarray: 1D array of default probabilities bounded in [0.0, 1.0].
                If underlying estimator outputs 2D array of shape (N, 2), returns positive class column.
        """
        pass

    def predict(self, X: Any, threshold: float = 0.5) -> np.ndarray:
        """Predict binary classification outcome based on a decision threshold.

        Args:
            X: Feature matrix.
            threshold: Probability decision boundary (default 0.5).

        Returns:
            np.ndarray: 1D array of binary predictions (0 or 1).
        """
        if not self.is_fitted:
            raise NotFittedError(f"Model '{self.model_name}' has not been fitted yet.")
        probabilities = self.predict_proba(X)
        return (probabilities >= threshold).astype(int)

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized model provenance and configuration dictionary.

        Returns:
            Dict containing model metadata suitable for experiment tracking and model registration.
        """
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "hyperparameters": self.hyperparameters,
            "description": self.description,
            "is_fitted": self.is_fitted,
            "feature_names_in": self.feature_names_in_,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='{self.model_name}', "
            f"version='{self.model_version}', type='{self.model_type}', "
            f"is_fitted={self.is_fitted})"
        )
