"""Unit tests for explainability data structures and plain-language factor translations."""
from src.ml.explainability.base import (
    FeatureContribution,
    GlobalExplanation,
    ImpactDirection,
    LocalExplanation,
    PlainLanguageTranslator,
)


def test_feature_contribution_and_local_explanation():
    contrib_1 = FeatureContribution(
        feature_name="recovery_duration_days",
        feature_value=6.0,
        attribution_value=-0.12,
        impact_direction=ImpactDirection.DECREASES_RISK,
        plain_language_description=PlainLanguageTranslator.translate_factor(
            "recovery_duration_days", ImpactDirection.DECREASES_RISK
        ),
    )

    contrib_2 = FeatureContribution(
        feature_name="debt_to_income",
        feature_value=0.55,
        attribution_value=0.18,
        impact_direction=ImpactDirection.INCREASES_RISK,
        plain_language_description=PlainLanguageTranslator.translate_factor(
            "debt_to_income", ImpactDirection.INCREASES_RISK
        ),
    )

    explanation = LocalExplanation(
        model_name="parakh-explainer",
        model_version="1.0.0",
        base_value=0.12,
        predicted_risk_probability=0.18,
        contributions=[contrib_1, contrib_2],
        top_risk_increasing_factors=[contrib_2],
        top_risk_reducing_factors=[contrib_1],
        plain_language_summary=[
            contrib_1.plain_language_description,
            contrib_2.plain_language_description,
        ],
    )

    assert explanation.base_value == 0.12
    assert len(explanation.contributions) == 2
    assert len(explanation.top_risk_increasing_factors) == 1
    assert "rapid earning recovery" in contrib_1.plain_language_description

    d = explanation.to_dict()
    assert d["model_name"] == "parakh-explainer"
    assert len(d["contributions"]) == 2
    assert d["contributions"][0]["impact_direction"] == "DECREASES_RISK"


def test_global_explanation():
    g_exp = GlobalExplanation(
        model_name="parakh-gbm",
        model_version="0.2.0",
        mean_absolute_attributions={
            "recovery_duration_days": 0.15,
            "income_cv_90d": 0.11,
            "debt_to_income": 0.09,
        },
        feature_importance_ranking=[
            "recovery_duration_days",
            "income_cv_90d",
            "debt_to_income",
        ],
        sample_count=200,
    )

    assert g_exp.sample_count == 200
    assert g_exp.feature_importance_ranking[0] == "recovery_duration_days"
    d = g_exp.to_dict()
    assert "mean_absolute_attributions" in d


def test_plain_language_translator_fallback():
    # Test fallback for a feature without explicit template
    text = PlainLanguageTranslator.translate_factor(
        "custom_unregistered_metric",
        ImpactDirection.DECREASES_RISK,
    )
    assert "Custom Unregistered Metric presents an favorable pattern" in text
