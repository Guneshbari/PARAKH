"""Baseline Logistic Regression model for PARAKH credit risk assessment.

Implements an interpretable, regularized baseline classifier anchored to the
Phase 4 BASELINE feature set (26 raw/derived features -> 35 model-ready columns).
Establishes the performance floor and linear benchmark for later comparison
with volatility-aware non-linear models.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.ml.models.base import BaseRiskModel, NotFittedError


class LogisticRegressionBaseline(BaseRiskModel):
    """Interpretable Regularized Logistic Regression baseline risk model.

    Adheres strictly to the BaseRiskModel contract. Implements L2-penalized
    logistic regression to predict calibrated repayment default probability
    P(Default | X).
    """

    def __init__(
        self,
        C: float = 1.0,
        penalty: str = "l2",
        solver: str = "lbfgs",
        max_iter: int = 1000,
        random_state: int = 42,
        class_weight: Optional[Union[Dict[Any, float], str]] = None,
        model_name: str = "baseline-logistic-regression",
        model_version: str = "1.0.0",
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize baseline Logistic Regression model.

        Args:
            C: Inverse of regularization strength (default 1.0). Smaller values
                specify stronger regularization.
            penalty: Regularization norm ('l2' standard default).
            solver: Optimization algorithm ('lbfgs' standard for l2).
            max_iter: Maximum number of solver iterations (default 1000).
            random_state: Seed for reproducible optimization (default 42).
            class_weight: Optional dictionary or 'balanced' for class weighting.
                Default None preserves empirical prior calibration.
            model_name: Identifier name for the baseline model.
            model_version: Model semantic version string.
            description: Narrative description of model specification.
            **kwargs: Additional parameters passed to sklearn LogisticRegression.
        """
        hyperparams: Dict[str, Any] = {
            "C": C,
            "penalty": penalty,
            "solver": solver,
            "max_iter": max_iter,
            "random_state": random_state,
            "class_weight": class_weight,
            **kwargs,
        }
        desc = (
            description
            or "Interpretable regularized L2 logistic regression benchmark on Phase 4 BASELINE features."
        )
        super().__init__(
            model_name=model_name,
            model_version=model_version,
            model_type="LOGISTIC_REGRESSION",
            hyperparameters=hyperparams,
            description=desc,
        )

        self.C = C
        self.penalty = penalty
        self.solver = solver
        self.max_iter = max_iter
        self.random_state = random_state
        self.class_weight = class_weight
        self.extra_kwargs = kwargs

        # In scikit-learn 1.8+, penalty='l2' default is implicit. To prevent deprecation
        # warnings while preserving explicit hyperparameter provenance, pass penalty only
        # if non-l2 or non-default.
        sklearn_kwargs: Dict[str, Any] = {
            "C": self.C,
            "solver": self.solver,
            "max_iter": self.max_iter,
            "random_state": self.random_state,
            "class_weight": self.class_weight,
            **self.extra_kwargs,
        }
        if self.penalty != "l2":
            sklearn_kwargs["penalty"] = self.penalty

        self.estimator = LogisticRegression(**sklearn_kwargs)

        # Fitted estimator attributes
        self.classes_: Optional[np.ndarray] = None
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: Optional[np.ndarray] = None
        self.n_features_in_: Optional[int] = None

    def fit(self, X: Any, y: Any, **kwargs: Any) -> "LogisticRegressionBaseline":
        """Fit the regularized logistic regression model.

        Args:
            X: Training feature matrix (DataFrame or 2D array) of shape (n_samples, n_features).
            y: Binary target vector (0 = repaid, 1 = default) of shape (n_samples,).
            **kwargs: Additional arguments passed to estimator fit.

        Returns:
            self: Fitted LogisticRegressionBaseline instance.

        Raises:
            ValueError: If X or y has zero samples, or contains invalid target classes.
        """
        if hasattr(X, "columns"):
            self.feature_names_in_ = list(X.columns)
            X_arr = X.values
        else:
            X_arr = np.asarray(X)
            if self.feature_names_in_ is None:
                self.feature_names_in_ = [f"x_{i}" for i in range(X_arr.shape[1])]

        y_arr = np.asarray(y)

        if len(X_arr) == 0 or len(y_arr) == 0:
            raise ValueError("Training data X and y must not be empty.")
        if len(X_arr) != len(y_arr):
            raise ValueError(f"Length mismatch: len(X)={len(X_arr)} != len(y)={len(y_arr)}")

        unique_y = np.unique(y_arr)
        if not np.all(np.isin(unique_y, [0, 1])):
            raise ValueError(f"Target y must contain only binary classes {0, 1}, got {unique_y}")

        self.n_features_in_ = int(X_arr.shape[1])

        # Fit underlying estimator
        self.estimator.fit(X_arr, y_arr, **kwargs)

        self.classes_ = self.estimator.classes_
        self.coef_ = self.estimator.coef_.copy()
        self.intercept_ = self.estimator.intercept_.copy()
        self.is_fitted = True

        return self

    def predict_proba(self, X: Any) -> np.ndarray:
        """Predict calibrated repayment default probability P(Default | X).

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            np.ndarray: 1D array of default probabilities bounded in [0.0, 1.0].

        Raises:
            NotFittedError: If model has not been fitted yet.
            ValueError: If input feature dimensions or column names mismatch.
        """
        if not self.is_fitted or self.estimator is None:
            raise NotFittedError(f"Model '{self.model_name}' has not been fitted yet.")

        if hasattr(X, "columns"):
            if self.feature_names_in_ is not None:
                missing_cols = set(self.feature_names_in_) - set(X.columns)
                if missing_cols:
                    raise ValueError(f"Input features missing required columns: {sorted(list(missing_cols))}")
                # Ensure column order aligns identically with training matrix
                X_matrix = X[self.feature_names_in_].values
            else:
                X_matrix = X.values
        else:
            X_matrix = np.asarray(X)

        if X_matrix.shape[1] != self.n_features_in_:
            raise ValueError(
                f"Feature count mismatch: expected {self.n_features_in_} features, got {X_matrix.shape[1]}"
            )

        probabilities = self.estimator.predict_proba(X_matrix)
        # Return probability of positive class (index 1: Default)
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            return np.clip(probabilities[:, 1], 0.0, 1.0)
        return np.clip(probabilities.ravel(), 0.0, 1.0)

    def predict(self, X: Any, threshold: float = 0.5) -> np.ndarray:
        """Predict binary repayment outcome (0 = repaid, 1 = default) based on threshold.

        Args:
            X: Feature matrix.
            threshold: Probability decision boundary (default 0.5).

        Returns:
            np.ndarray: 1D array of binary predictions (0 or 1).
        """
        return super().predict(X, threshold=threshold)

    def get_coefficients_df(self) -> pd.DataFrame:
        """Return structured DataFrame of feature coefficients and odds ratios.

        Returns:
            pd.DataFrame: Columns ['feature', 'coefficient', 'abs_coefficient', 'odds_ratio']
                sorted descending by absolute coefficient magnitude.

        Raises:
            NotFittedError: If model is not yet fitted.
        """
        if not self.is_fitted or self.coef_ is None:
            raise NotFittedError("Cannot extract coefficients from an unfitted model.")

        features = self.feature_names_in_ or [f"feature_{i}" for i in range(self.coef_.shape[1])]
        weights = self.coef_[0]

        df = pd.DataFrame({
            "feature": features,
            "coefficient": weights,
            "abs_coefficient": np.abs(weights),
            "odds_ratio": np.exp(weights),
        })
        return df.sort_values(by="abs_coefficient", ascending=False).reset_index(drop=True)

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized model provenance and coefficient summary."""
        meta = super().get_metadata()
        meta["n_features_in"] = self.n_features_in_
        if self.is_fitted:
            meta["classes"] = [int(c) for c in self.classes_] if self.classes_ is not None else [0, 1]
            meta["intercept"] = float(self.intercept_[0]) if self.intercept_ is not None else None
            meta["coefficient_summary"] = {
                "min": float(np.min(self.coef_)),
                "max": float(np.max(self.coef_)),
                "mean_abs": float(np.mean(np.abs(self.coef_))),
            }
        return meta

    def save(self, filepath: Union[str, Path]) -> None:
        """Serialize model artifact to disk.

        Args:
            filepath: Destination path for joblib binary.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "LogisticRegressionBaseline":
        """Load serialized model artifact from disk.

        Args:
            filepath: Source path of joblib binary.

        Returns:
            LogisticRegressionBaseline instance.

        Raises:
            FileNotFoundError: If filepath does not exist.
            TypeError: If unpickled object is not a LogisticRegressionBaseline.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")

        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is of type {type(obj)}, expected {cls}")
        return obj
