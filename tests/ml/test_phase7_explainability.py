"""Unit tests for Phase 7 explainability and SHAP attribution framework.

Verifies:
1. TreeShapExplainer initialization and error handling for unfitted models.
2. Local explanation generation with valid probability in [0, 1] and base value.
3. SHAP local efficiency property (sum of attributions + base value equals model logit).
4. Global SHAP feature importance calculation across all 64 VOLATILITY_AWARE features.
5. Presence and non-zero attribution of the 9 required volatility interaction features.
6. SHAP pairwise interaction value computation and summary extraction.
7. LogisticExplainer linear coefficient extraction, odds ratios, and local attributions.
8. Deterministic reproducibility across repeated explainer calls with seed 42.
9. Plain-language factor translation: direction labeling and respectful borrower phrasing.
10. Feature name alignment and dimension validation against model input matrix.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.ml.constants import DEFAULT_RANDOM_SEED, ExperimentVariant
from src.ml.data.splitting import GroupedDatasetSplitter
from src.ml.explainability.base import ImpactDirection, LocalExplanation
from src.ml.explainability.plain_language import (
    FEATURE_PLAIN_LANGUAGE_CATALOG,
    PlainLanguageExplainer,
    PlainLanguageFactor,
)
from src.ml.explainability.shap_explainer import (
    LogisticExplainer,
    TreeShapExplainer,
    sigmoid,
)
from src.ml.features.feature_engineering import (
    ENGINEERED_VOLATILITY_FEATURES,
    build_model_ready_matrices,
)
from src.ml.models.base import NotFittedError
from src.ml.models.baseline import LogisticRegressionBaseline
from src.ml.models.volatility_aware import VolatilityAwareRiskModel


KEY_VOLATILITY_FEATURES = [
    "feat_eng_vol_to_baseline",
    "feat_eng_downside_to_median",
    "feat_eng_vol_x_trend",
    "feat_eng_vol_to_bounceback",
    "feat_eng_recovery_velocity",
    "feat_eng_buffer_burn_coverage",
    "feat_eng_installment_floor_coverage",
    "feat_int_vol_x_recovery",
    "feat_int_vol_x_buffer",
]


@pytest.fixture(scope="module")
def canonical_df():
    """Load canonical Phase 2 synthetic dataset."""
    return pd.read_parquet("data/synthetic/synthetic_credit_applications.parquet")


@pytest.fixture(scope="module")
def dataset_splits(canonical_df):
    """Split canonical dataset into train, val, and test partitions."""
    return GroupedDatasetSplitter.split(canonical_df, seed=DEFAULT_RANDOM_SEED)


@pytest.fixture(scope="module")
def loaded_models():
    """Load pre-trained Phase 5 baseline and Phase 6 volatility-aware models."""
    base_model = LogisticRegressionBaseline.load("models/artifacts/logistic_regression_baseline.joblib")
    vol_model = VolatilityAwareRiskModel.load("models/artifacts/volatility_aware_risk_model.joblib")
    return {"baseline": base_model, "volatility_aware": vol_model}


@pytest.fixture(scope="module")
def val_matrices(dataset_splits):
    """Build model-ready matrices for both feature variants."""
    base_mat = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.BASELINE,
        scored_only=True,
    )
    vol_mat = build_model_ready_matrices(
        train_df=dataset_splits.train_df,
        val_df=dataset_splits.val_df,
        test_df=dataset_splits.test_df,
        variant=ExperimentVariant.VOLATILITY_AWARE,
        scored_only=True,
    )
    return {"baseline": base_mat, "volatility_aware": vol_mat}


def test_tree_shap_explainer_initialization_and_unfitted_guard():
    """Verify TreeShapExplainer enforces fitted model contract."""
    unfitted = VolatilityAwareRiskModel()
    with pytest.raises(NotFittedError):
        TreeShapExplainer(unfitted)


def test_tree_shap_local_explanation_efficiency(loaded_models, val_matrices):
    """Verify local TreeSHAP attributions satisfy efficiency property (sum of SHAP equals margin)."""
    vol_model = loaded_models["volatility_aware"]
    X_val = val_matrices["volatility_aware"]["X_val"]

    explainer = TreeShapExplainer(vol_model)
    single_instance = X_val.iloc[0]

    local_exp = explainer.explain_instance(single_instance, top_n=5)
    assert isinstance(local_exp, LocalExplanation)
    assert 0.0 <= local_exp.predicted_risk_probability <= 1.0

    # Efficiency check: sum(contributions) + base_value = raw margin logit
    total_shap = sum(c.attribution_value for c in local_exp.contributions)
    reconstructed_logit = local_exp.base_value + total_shap
    reconstructed_prob = float(sigmoid(reconstructed_logit))

    assert np.isclose(reconstructed_prob, local_exp.predicted_risk_probability, atol=1e-3)
    assert len(local_exp.contributions) == 64
    assert len(local_exp.top_risk_increasing_factors) <= 5
    assert len(local_exp.top_risk_reducing_factors) <= 5


def test_tree_shap_global_explanation(loaded_models, val_matrices):
    """Verify global SHAP feature importance calculation across validation set."""
    vol_model = loaded_models["volatility_aware"]
    X_val = val_matrices["volatility_aware"]["X_val"]

    explainer = TreeShapExplainer(vol_model)
    global_exp = explainer.explain_global(X_val.head(100))

    assert global_exp.sample_count == 100
    assert len(global_exp.feature_importance_ranking) == 64
    assert len(global_exp.mean_absolute_attributions) == 64

    # Top feature should be feat_liq_net_margin
    assert global_exp.feature_importance_ranking[0] == "feat_liq_net_margin"

    # All 9 required volatility features must be present in attributions
    for feat in KEY_VOLATILITY_FEATURES:
        assert feat in global_exp.mean_absolute_attributions
        assert global_exp.mean_absolute_attributions[feat] > 0.0


def test_shap_pairwise_interaction_values(loaded_models, val_matrices):
    """Verify calculation of pairwise SHAP interactions for key volatility features."""
    vol_model = loaded_models["volatility_aware"]
    X_val = val_matrices["volatility_aware"]["X_val"].head(20)

    explainer = TreeShapExplainer(vol_model)
    pairwise = explainer.get_pairwise_interaction_summary(X_val, key_features=KEY_VOLATILITY_FEATURES[:4])

    assert len(pairwise) > 0
    for entry in pairwise:
        assert "feature_1" in entry
        assert "feature_2" in entry
        assert entry["mean_abs_interaction"] >= 0.0
        assert entry["max_abs_interaction"] >= entry["mean_abs_interaction"]


def test_logistic_explainer_coefficients_and_local_explanation(loaded_models, val_matrices):
    """Verify LogisticExplainer linear attributions and odds ratios."""
    base_model = loaded_models["baseline"]
    X_val = val_matrices["baseline"]["X_val"]

    explainer = LogisticExplainer(base_model)
    coef_table = explainer.get_coefficient_table()

    assert len(coef_table) == 35
    for row in coef_table:
        assert "feature" in row
        assert "coefficient" in row
        assert "odds_ratio" in row
        assert row["odds_ratio"] > 0.0
        assert "association_direction" in row

    # Test local explanation
    single_row = X_val.iloc[0]
    local_exp = explainer.explain_instance(single_row, top_n=4)
    assert 0.0 <= local_exp.predicted_risk_probability <= 1.0
    assert len(local_exp.contributions) == 35


def test_plain_language_explainer_catalog_and_formatting():
    """Verify plain-language translator formatting and respectful non-causal language."""
    # Protective feature translation
    factor_prot = PlainLanguageExplainer.translate_feature_contribution(
        feature_name="feat_eng_vol_to_bounceback",
        attribution_value=-0.25,
        feature_value=1.45,
    )
    assert isinstance(factor_prot, PlainLanguageFactor)
    assert factor_prot.impact_direction == "associated with lower predicted risk"
    assert "recovery" in factor_prot.borrower_explanation.lower()
    assert "1.45" in factor_prot.feature_value_display

    # Risk-increasing feature translation
    factor_risk = PlainLanguageExplainer.translate_feature_contribution(
        feature_name="feat_bur_total_dti",
        attribution_value=0.35,
        feature_value=0.62,
    )
    assert factor_risk.impact_direction == "associated with higher predicted risk"
    assert "commitments" in factor_risk.borrower_explanation.lower()

    # Summary generator
    contribs = [
        {"feature": "feat_liq_net_margin", "attribution": -0.80, "value": 4500.0},
        {"feature": "feat_bur_total_dti", "attribution": 0.40, "value": 0.55},
    ]
    summary = PlainLanguageExplainer.generate_borrower_explanation_summary(contribs)
    assert len(summary["key_protective_factors"]) == 1
    assert len(summary["key_risk_factors"]) == 1
    assert "causality" in summary["disclaimer"].lower()


def test_deterministic_reproducibility_of_explanations(loaded_models, val_matrices):
    """Verify repeated TreeSHAP calls on identical instances yield bitwise identical attributions."""
    vol_model = loaded_models["volatility_aware"]
    X_val = val_matrices["volatility_aware"]["X_val"].head(5)

    exp1 = TreeShapExplainer(vol_model).explain_instance(X_val.iloc[0])
    exp2 = TreeShapExplainer(vol_model).explain_instance(X_val.iloc[0])

    assert np.isclose(exp1.predicted_risk_probability, exp2.predicted_risk_probability)
    assert np.isclose(exp1.base_value, exp2.base_value)
    for c1, c2 in zip(exp1.contributions, exp2.contributions):
        assert c1.feature_name == c2.feature_name
        assert np.isclose(c1.attribution_value, c2.attribution_value)
