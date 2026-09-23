"""Volatility-Aware Non-Linear Risk Model for PARAKH Credit Assessment.

Implements a gradient-boosted tree model (LightGBM) trained on the full Phase 4
VOLATILITY_AWARE feature set (64 model-ready columns). Captures non-linear
interactions between earnings volatility, directional trend, recovery elasticity,
and liquidity buffers without arbitrary polynomial expansions.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from src.ml.models.base import BaseRiskModel, NotFittedError

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    from sklearn.ensemble import HistGradientBoostingClassifier


class VolatilityAwareRiskModel(BaseRiskModel):
    """Non-linear, volatility-aware credit risk model using gradient-boosted trees.

    Adheres strictly to the BaseRiskModel interface contract. Employs LightGBM
    (with HistGradientBoostingClassifier fallback) to predict calibrated
    repayment default probability P(Default | X) on the 64-feature VOLATILITY_AWARE
    matrix.
    """

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        min_child_samples: int = 30,
        reg_lambda: float = 2.0,
        reg_alpha: float = 0.0,
        max_depth: int = -1,
        subsample: float = 1.0,
        colsample_bytree: float = 1.0,
        random_state: int = 42,
        class_weight: Optional[Union[Dict[Any, float], str]] = None,
        model_name: str = "volatility-aware-risk-model",
        model_version: str = "1.0.0",
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Volatility-Aware risk model with deterministic hyperparameters.

        Args:
            n_estimators: Number of boosting trees / iterations (default 150).
            learning_rate: Boosting shrinkage factor (default 0.05).
            num_leaves: Maximum tree leaves for base learners (default 31).
            min_child_samples: Minimum data required in a child node (default 30).
            reg_lambda: L2 regularization on weights (default 2.0).
            reg_alpha: L1 regularization on weights (default 0.0).
            max_depth: Maximum tree depth limit, -1 for unlimited (default -1).
            subsample: Row subsampling fraction (default 1.0).
            colsample_bytree: Column subsampling fraction (default 1.0).
            random_state: Deterministic PRNG seed (default 42).
            class_weight: Class weighting specification. None preserves natural prior.
            model_name: Unique identifier for model tracking.
            model_version: Semantic version of model artifact.
            description: Narrative description of model architecture and purpose.
            **kwargs: Additional parameters passed to estimator.
        """
        hyperparams: Dict[str, Any] = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "min_child_samples": min_child_samples,
            "reg_lambda": reg_lambda,
            "reg_alpha": reg_alpha,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "class_weight": class_weight,
            "backend": "lightgbm" if HAS_LIGHTGBM else "hist_gradient_boosting",
            **kwargs,
        }
        desc = (
            description
            or "Non-linear gradient-boosted tree model capturing joint volatility-recovery-trend dynamics on 64 features."
        )
        super().__init__(
            model_name=model_name,
            model_version=model_version,
            model_type="GRADIENT_BOOSTED_TREES",
            hyperparameters=hyperparams,
            description=desc,
        )

        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.reg_lambda = reg_lambda
        self.reg_alpha = reg_alpha
        self.max_depth = max_depth
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.class_weight = class_weight
        self.extra_kwargs = kwargs

        # Initialize underlying estimator
        if HAS_LIGHTGBM:
            self.estimator = lgb.LGBMClassifier(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                num_leaves=self.num_leaves,
                min_child_samples=self.min_child_samples,
                reg_lambda=self.reg_lambda,
                reg_alpha=self.reg_alpha,
                max_depth=self.max_depth,
                subsample=self.subsample,
                colsample_bytree=self.colsample_bytree,
                random_state=self.random_state,
                class_weight=self.class_weight,
                verbosity=-1,
                n_jobs=1,
                **self.extra_kwargs,
            )
        else:
            self.estimator = HistGradientBoostingClassifier(
                max_iter=self.n_estimators,
                learning_rate=self.learning_rate,
                max_leaf_nodes=self.num_leaves,
                min_samples_leaf=self.min_child_samples,
                l2_regularization=self.reg_lambda,
                max_depth=None if self.max_depth == -1 else self.max_depth,
                random_state=self.random_state,
                class_weight=self.class_weight,
                **self.extra_kwargs,
            )

        self.classes_: Optional[np.ndarray] = None
        self.n_features_in_: Optional[int] = None
        self.feature_importances_split_: Optional[np.ndarray] = None
        self.feature_importances_gain_: Optional[np.ndarray] = None

    def fit(self, X: Any, y: Any, **kwargs: Any) -> "VolatilityAwareRiskModel":
        """Fit the gradient-boosted tree model.

        Args:
            X: Training feature matrix of shape (n_samples, n_features).
            y: Binary repayment outcome vector (0 = repaid, 1 = default).
            **kwargs: Additional parameters passed to estimator fit.

        Returns:
            self: Fitted VolatilityAwareRiskModel instance.

        Raises:
            ValueError: If X or y is empty, lengths mismatch, or y is not binary {0, 1}.
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

        # Fit estimator
        self.estimator.fit(X_arr, y_arr, **kwargs)

        self.classes_ = self.estimator.classes_
        self.is_fitted = True

        # Extract feature importances if LightGBM
        if HAS_LIGHTGBM and hasattr(self.estimator, "booster_"):
            self.feature_importances_split_ = self.estimator.booster_.feature_importance(
                importance_type="split"
            )
            self.feature_importances_gain_ = self.estimator.booster_.feature_importance(
                importance_type="gain"
            )
        elif hasattr(self.estimator, "feature_importances_"):
            self.feature_importances_gain_ = self.estimator.feature_importances_
            self.feature_importances_split_ = None

        return self

    def predict_proba(self, X: Any) -> np.ndarray:
        """Predict calibrated repayment default probability P(Default | X).

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            np.ndarray: 1D array of default probabilities bounded in [0.0, 1.0].

        Raises:
            NotFittedError: If model has not been fitted yet.
            ValueError: If feature dimension or column names mismatch.
        """
        if not self.is_fitted or self.estimator is None:
            raise NotFittedError(f"Model '{self.model_name}' has not been fitted yet.")

        if hasattr(X, "columns"):
            if self.feature_names_in_ is not None:
                missing_cols = set(self.feature_names_in_) - set(X.columns)
                if missing_cols:
                    raise ValueError(f"Input features missing required columns: {sorted(list(missing_cols))}")
                # Enforce identical column ordering
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
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            return np.clip(probabilities[:, 1], 0.0, 1.0)
        return np.clip(probabilities.ravel(), 0.0, 1.0)

    def predict(self, X: Any, threshold: float = 0.5) -> np.ndarray:
        """Predict binary repayment outcome based on decision threshold.

        Args:
            X: Feature matrix.
            threshold: Probability decision boundary (default 0.5).

        Returns:
            np.ndarray: 1D array of binary predictions (0 or 1).
        """
        return super().predict(X, threshold=threshold)

    def get_feature_importances_df(self) -> pd.DataFrame:
        """Return structured DataFrame of feature importances sorted descending by gain.

        Returns:
            pd.DataFrame: Columns ['feature', 'split_importance', 'gain_importance', 'normalized_gain'].

        Raises:
            NotFittedError: If model is not yet fitted.
        """
        if not self.is_fitted:
            raise NotFittedError("Cannot extract feature importances from an unfitted model.")

        features = self.feature_names_in_ or [f"feature_{i}" for i in range(self.n_features_in_ or 0)]
        gain = (
            self.feature_importances_gain_
            if self.feature_importances_gain_ is not None
            else np.zeros(len(features))
        )
        split = (
            self.feature_importances_split_
            if self.feature_importances_split_ is not None
            else np.zeros(len(features), dtype=int)
        )

        total_gain = np.sum(gain)
        norm_gain = (gain / total_gain) if total_gain > 0 else np.zeros_like(gain)

        df = pd.DataFrame({
            "feature": features,
            "split_importance": split,
            "gain_importance": gain,
            "normalized_gain": norm_gain,
        })
        return df.sort_values(by="gain_importance", ascending=False).reset_index(drop=True)

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized model provenance, hyperparameters, and feature metadata."""
        meta = super().get_metadata()
        meta["n_features_in"] = self.n_features_in_
        if self.is_fitted:
            meta["classes"] = [int(c) for c in self.classes_] if self.classes_ is not None else [0, 1]
            if self.feature_importances_gain_ is not None:
                top_df = self.get_feature_importances_df().head(10)
                meta["top_features_by_gain"] = top_df.to_dict(orient="records")
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
    def load(cls, filepath: Union[str, Path]) -> "VolatilityAwareRiskModel":
        """Load serialized model artifact from disk.

        Args:
            filepath: Source path of joblib binary.

        Returns:
            VolatilityAwareRiskModel instance.

        Raises:
            FileNotFoundError: If filepath does not exist.
            TypeError: If unpickled object is not a VolatilityAwareRiskModel.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")

        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"Loaded object is of type {type(obj)}, expected {cls}")
        return obj
