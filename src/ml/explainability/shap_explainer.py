"""TreeSHAP and Linear model explainers for PARAKH credit risk assessments.

Implements TreeSHAP explainer for the Phase 6 Volatility-Aware LightGBM model and
linear attribution explainer for the Phase 5 Logistic Regression baseline.
Provides local instance attributions, global mean absolute SHAP importance,
and SHAP pairwise interaction calculations for key volatility features.
"""
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd
import shap

from src.ml.explainability.base import (
    BaseExplainer,
    FeatureContribution,
    GlobalExplanation,
    ImpactDirection,
    LocalExplanation,
    PlainLanguageTranslator,
)
from src.ml.explainability.plain_language import PlainLanguageExplainer
from src.ml.models.base import BaseRiskModel, NotFittedError


def sigmoid(z: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Logistic sigmoid link function converting log-odds to probability."""
    return 1.0 / (1.0 + np.exp(-z))


class TreeShapExplainer(BaseExplainer):
    """TreeSHAP model explainer for gradient-boosted tree risk models."""

    def __init__(self, model: BaseRiskModel) -> None:
        """Initialize TreeSHAP explainer with a fitted risk model.

        Args:
            model: Fitted BaseRiskModel instance (e.g. VolatilityAwareRiskModel).

        Raises:
            NotFittedError: If model is not yet fitted.
            ValueError: If model lacks an accessible tree booster or estimator.
        """
        super().__init__(model)
        if not getattr(model, "is_fitted", False):
            raise NotFittedError(f"Model '{model.model_name}' must be fitted before initializing TreeSHAP.")

        # Access underlying estimator
        estimator = getattr(model, "estimator", model)
        self.explainer = shap.TreeExplainer(estimator)
        self.feature_names = model.feature_names_in_

        # Expected value in log-odds space
        ev = self.explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            self.base_value = float(ev[1] if len(ev) > 1 else ev[0])
        else:
            self.base_value = float(ev)

    def _prepare_matrix(self, X: Any) -> np.ndarray:
        """Convert input to 2D numpy array aligning with model features."""
        if hasattr(X, "columns"):
            if self.feature_names is not None:
                missing = set(self.feature_names) - set(X.columns)
                if missing:
                    raise ValueError(f"Input features missing required columns: {sorted(list(missing))}")
                return X[self.feature_names].values
            return X.values
        arr = np.asarray(X)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr

    def explain_instance(
        self,
        features: Union[pd.Series, pd.DataFrame, np.ndarray, Dict[str, Any]],
        top_n: int = 5,
    ) -> LocalExplanation:
        """Generate local TreeSHAP feature attributions for a single applicant observation.

        Args:
            features: 1D Series/dict or single-row DataFrame/array.
            top_n: Number of leading positive/negative driving factors to extract.

        Returns:
            LocalExplanation: Structured local SHAP breakdown.
        """
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
            X_arr = self._prepare_matrix(features_df)
            feature_vals = features_df.iloc[0].to_dict()
        elif isinstance(features, pd.Series):
            features_df = pd.DataFrame([features])
            X_arr = self._prepare_matrix(features_df)
            feature_vals = features.to_dict()
        elif isinstance(features, pd.DataFrame):
            X_arr = self._prepare_matrix(features)
            feature_vals = features.iloc[0].to_dict()
        else:
            X_arr = self._prepare_matrix(features)
            feature_vals = {
                (self.feature_names[i] if self.feature_names else f"x_{i}"): float(X_arr[0, i])
                for i in range(X_arr.shape[1])
            }

        # Compute SHAP values for single instance
        shap_vals = self.explainer.shap_values(X_arr)
        if isinstance(shap_vals, list):
            instance_shap = shap_vals[1][0] if len(shap_vals) > 1 else shap_vals[0][0]
        else:
            instance_shap = shap_vals[0]

        total_margin = self.base_value + float(np.sum(instance_shap))
        pred_prob = float(sigmoid(total_margin))

        names = self.feature_names or [f"feature_{i}" for i in range(len(instance_shap))]
        contributions: List[FeatureContribution] = []

        for name, val, sv in zip(names, [feature_vals.get(n, 0.0) for n in names], instance_shap):
            # Direction: positive SHAP in log-odds space increases default risk
            if sv > 1e-4:
                direction = ImpactDirection.INCREASES_RISK
            elif sv < -1e-4:
                direction = ImpactDirection.DECREASES_RISK
            else:
                direction = ImpactDirection.NEUTRAL

            desc = PlainLanguageTranslator.translate_factor(name, direction, feature_value=val)
            contributions.append(
                FeatureContribution(
                    feature_name=name,
                    feature_value=val,
                    attribution_value=round(float(sv), 6),
                    impact_direction=direction,
                    plain_language_description=desc,
                )
            )

        # Sort by absolute SHAP magnitude
        contributions.sort(key=lambda c: abs(c.attribution_value), reverse=True)

        # Separate risk-increasing and risk-reducing factors
        risk_increasing = sorted(
            [c for c in contributions if c.attribution_value > 0],
            key=lambda c: c.attribution_value,
            reverse=True,
        )[:top_n]

        risk_reducing = sorted(
            [c for c in contributions if c.attribution_value < 0],
            key=lambda c: c.attribution_value,
        )[:top_n]

        summary_statements = [
            f"Risk-reducing: {c.feature_name} (SHAP={c.attribution_value:+.4f}) - {c.plain_language_description}"
            for c in risk_reducing[:3]
        ] + [
            f"Risk-increasing: {c.feature_name} (SHAP={c.attribution_value:+.4f}) - {c.plain_language_description}"
            for c in risk_increasing[:3]
        ]

        return LocalExplanation(
            model_name=self.model.model_name,
            model_version=self.model.model_version,
            base_value=round(self.base_value, 6),
            predicted_risk_probability=round(pred_prob, 6),
            contributions=contributions,
            top_risk_increasing_factors=risk_increasing,
            top_risk_reducing_factors=risk_reducing,
            plain_language_summary=summary_statements,
        )

    def explain_global(
        self,
        X_sample: Union[pd.DataFrame, np.ndarray],
    ) -> GlobalExplanation:
        """Compute global mean absolute SHAP importance across a representative background sample.

        Args:
            X_sample: Evaluation matrix of shape (n_samples, n_features).

        Returns:
            GlobalExplanation: Ranked features and mean absolute SHAP attributions.
        """
        X_arr = self._prepare_matrix(X_sample)
        shap_vals = self.explainer.shap_values(X_arr)
        if isinstance(shap_vals, list):
            sample_shap = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]
        else:
            sample_shap = shap_vals

        mean_abs = np.mean(np.abs(sample_shap), axis=0)
        names = self.feature_names or [f"feature_{i}" for i in range(len(mean_abs))]

        attributions = {name: round(float(ma), 6) for name, ma in zip(names, mean_abs)}
        ranked = sorted(names, key=lambda n: attributions[n], reverse=True)

        return GlobalExplanation(
            model_name=self.model.model_name,
            model_version=self.model.model_version,
            mean_absolute_attributions=attributions,
            feature_importance_ranking=ranked,
            sample_count=int(X_arr.shape[0]),
        )

    def compute_shap_interaction_values(
        self,
        X_sample: Union[pd.DataFrame, np.ndarray],
    ) -> np.ndarray:
        """Calculate pairwise SHAP interaction matrices across sample instances.

        Args:
            X_sample: Sample feature matrix.

        Returns:
            np.ndarray: 3D array of shape (n_samples, n_features, n_features).
        """
        X_arr = self._prepare_matrix(X_sample)
        interactions = self.explainer.shap_interaction_values(X_arr)
        if isinstance(interactions, list):
            return interactions[1] if len(interactions) > 1 else interactions[0]
        return interactions

    def get_pairwise_interaction_summary(
        self,
        X_sample: Union[pd.DataFrame, np.ndarray],
        key_features: List[str],
    ) -> List[Dict[str, Any]]:
        """Calculate mean absolute pairwise interaction strength between key volatility features.

        Args:
            X_sample: Sample feature matrix.
            key_features: List of feature names to audit.

        Returns:
            List[Dict[str, Any]]: Ranked pairwise interaction entries.
        """
        interactions = self.compute_shap_interaction_values(X_sample)
        names = self.feature_names or []
        name_to_idx = {name: i for i, name in enumerate(names)}

        valid_keys = [f for f in key_features if f in name_to_idx]
        pairwise_results: List[Dict[str, Any]] = []

        for i, f1 in enumerate(valid_keys):
            idx1 = name_to_idx[f1]
            for f2 in valid_keys[i + 1:]:
                idx2 = name_to_idx[f2]
                # Extract off-diagonal interaction term across all samples
                interaction_vals = interactions[:, idx1, idx2]
                mean_abs_inter = float(np.mean(np.abs(interaction_vals)))
                pairwise_results.append({
                    "feature_1": f1,
                    "feature_2": f2,
                    "mean_abs_interaction": round(mean_abs_inter, 6),
                    "max_abs_interaction": round(float(np.max(np.abs(interaction_vals))), 6),
                })

        return sorted(pairwise_results, key=lambda x: x["mean_abs_interaction"], reverse=True)


class LogisticExplainer(BaseExplainer):
    """Linear model attribution explainer for regularized Logistic Regression."""

    def __init__(self, model: BaseRiskModel) -> None:
        """Initialize linear explainer.

        Args:
            model: Fitted LogisticRegressionBaseline instance.

        Raises:
            NotFittedError: If model is not fitted.
        """
        super().__init__(model)
        if not getattr(model, "is_fitted", False):
            raise NotFittedError(f"Model '{model.model_name}' must be fitted before initializing explainer.")

        self.feature_names = model.feature_names_in_
        self.coef = model.coef_[0] if model.coef_.ndim == 2 else model.coef_
        self.intercept = float(model.intercept_[0]) if hasattr(model.intercept_, "__len__") else float(model.intercept_)

    def explain_global(
        self,
        X_sample: Optional[Union[pd.DataFrame, np.ndarray]] = None,
    ) -> GlobalExplanation:
        """Extract global linear importance based on absolute coefficient magnitudes."""
        names = self.feature_names or [f"feature_{i}" for i in range(len(self.coef))]
        abs_weights = np.abs(self.coef)

        attributions = {name: round(float(w), 6) for name, w in zip(names, abs_weights)}
        ranked = sorted(names, key=lambda n: attributions[n], reverse=True)

        count = len(X_sample) if X_sample is not None else 0
        return GlobalExplanation(
            model_name=self.model.model_name,
            model_version=self.model.model_version,
            mean_absolute_attributions=attributions,
            feature_importance_ranking=ranked,
            sample_count=count,
        )

    def explain_instance(
        self,
        features: Union[pd.Series, pd.DataFrame, np.ndarray, Dict[str, Any]],
        top_n: int = 5,
    ) -> LocalExplanation:
        """Compute linear log-odds feature contributions (beta_j * x_j) for single instance."""
        if isinstance(features, (pd.Series, dict)):
            row = dict(features)
            names = self.feature_names or list(row.keys())
            x_vec = np.array([float(row.get(n, 0.0)) for n in names])
        elif isinstance(features, pd.DataFrame):
            row = features.iloc[0].to_dict()
            names = self.feature_names or list(features.columns)
            x_vec = np.array([float(row.get(n, 0.0)) for n in names])
        else:
            x_vec = np.asarray(features).ravel()
            names = self.feature_names or [f"x_{i}" for i in range(len(x_vec))]
            row = {n: float(v) for n, v in zip(names, x_vec)}

        contributions_arr = self.coef * x_vec
        total_logit = self.intercept + float(np.sum(contributions_arr))
        pred_prob = float(sigmoid(total_logit))

        contrib_list: List[FeatureContribution] = []
        for name, val, c_val in zip(names, [row.get(n, 0.0) for n in names], contributions_arr):
            direction = ImpactDirection.INCREASES_RISK if c_val > 0 else ImpactDirection.DECREASES_RISK
            desc = PlainLanguageTranslator.translate_factor(name, direction, feature_value=val)
            contrib_list.append(
                FeatureContribution(
                    feature_name=name,
                    feature_value=val,
                    attribution_value=round(float(c_val), 6),
                    impact_direction=direction,
                    plain_language_description=desc,
                )
            )

        contrib_list.sort(key=lambda c: abs(c.attribution_value), reverse=True)

        risk_inc = sorted([c for c in contrib_list if c.attribution_value > 0], key=lambda c: c.attribution_value, reverse=True)[:top_n]
        risk_red = sorted([c for c in contrib_list if c.attribution_value < 0], key=lambda c: c.attribution_value)[:top_n]

        return LocalExplanation(
            model_name=self.model.model_name,
            model_version=self.model.model_version,
            base_value=round(self.intercept, 6),
            predicted_risk_probability=round(pred_prob, 6),
            contributions=contrib_list,
            top_risk_increasing_factors=risk_inc,
            top_risk_reducing_factors=risk_red,
            plain_language_summary=[c.plain_language_description for c in (risk_red[:2] + risk_inc[:2]) if c.plain_language_description],
        )

    def get_coefficient_table(self) -> List[Dict[str, Any]]:
        """Return full table of features, coefficients, odds ratios, and risk direction."""
        names = self.feature_names or [f"feature_{i}" for i in range(len(self.coef))]
        records: List[Dict[str, Any]] = []

        for name, weight in zip(names, self.coef):
            or_val = float(np.exp(weight))
            records.append({
                "feature": name,
                "coefficient": round(float(weight), 6),
                "abs_coefficient": round(float(abs(weight)), 6),
                "odds_ratio": round(or_val, 6),
                "association_direction": "Protective (Reduces Default Odds)" if weight < 0 else "Risk Driver (Increases Default Odds)",
                "interpretation_note": "Describes model association, not direct causality.",
            })

        return sorted(records, key=lambda x: x["abs_coefficient"], reverse=True)
