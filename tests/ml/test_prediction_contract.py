"""Unit tests for PredictionResult contract and validation rules."""
import pytest

from src.ml.constants import RiskTier
from src.ml.models.prediction import PredictionResult


def test_scored_prediction_result_creation():
    result = PredictionResult.create_scored_result(
        model_name="parakh-test-model",
        model_version="1.0.0",
        risk_probability=0.15,
        confidence=0.88,
        key_factors=["Rapid income recovery observed", "Low debt burden"],
        income_archetype="Healthy Volatile",
        volatility_interpretation="Healthy seasonal variation with rapid rebound",
        application_id="app-1234",
    )

    assert result.model_name == "parakh-test-model"
    assert result.risk_probability == 0.15
    assert result.risk_level == RiskTier.LOWER
    assert result.score is not None
    assert 300 <= result.score <= 850
    assert result.confidence == 0.88
    assert not result.is_insufficient_evidence
    assert len(result.key_factors) == 2
    assert result.income_archetype == "Healthy Volatile"

    # Serialization test
    d = result.to_dict()
    assert d["risk_level"] == "LOWER"
    assert d["risk_probability"] == 0.15

    # Deserialization test
    deserialized = PredictionResult.from_dict(d)
    assert deserialized.risk_level == RiskTier.LOWER
    assert deserialized.score == result.score


def test_insufficient_evidence_prediction_result():
    result = PredictionResult.create_insufficient_evidence_result(
        model_name="parakh-test-model",
        model_version="1.0.0",
        confidence=0.25,
        key_factors=["Insufficient observation history (< 30 days)"],
        missing_signal_guidance=["Connect platform account with at least 30 days history"],
        application_id="app-5678",
    )

    assert result.is_insufficient_evidence is True
    assert result.risk_level == RiskTier.INSUFFICIENT
    assert result.score is None
    assert result.risk_probability is None
    assert result.confidence == 0.25
    assert result.missing_signal_guidance is not None
    assert len(result.missing_signal_guidance) == 1

    d = result.to_dict()
    assert d["score"] is None
    assert d["is_insufficient_evidence"] is True


def test_prediction_contract_validation_errors():
    # Confidence out of bounds
    with pytest.raises(ValueError, match="Confidence must be between"):
        PredictionResult(
            model_name="test",
            model_version="1.0",
            risk_level=RiskTier.LOWER,
            confidence=1.5,
            risk_probability=0.2,
        )

    # Scored result with null probability
    with pytest.raises(ValueError, match="risk_probability must be provided"):
        PredictionResult(
            model_name="test",
            model_version="1.0",
            risk_level=RiskTier.LOWER,
            confidence=0.8,
            is_insufficient_evidence=False,
            risk_probability=None,
        )

    # Insufficient result with invalid risk level
    with pytest.raises(ValueError, match="risk_level must be INSUFFICIENT"):
        PredictionResult(
            model_name="test",
            model_version="1.0",
            risk_level=RiskTier.LOWER,
            confidence=0.2,
            is_insufficient_evidence=True,
            risk_probability=None,
        )

    # Insufficient result with a non-null score
    with pytest.raises(ValueError, match="score must be None"):
        PredictionResult(
            model_name="test",
            model_version="1.0",
            risk_level=RiskTier.INSUFFICIENT,
            confidence=0.2,
            is_insufficient_evidence=True,
            score=700,
        )
