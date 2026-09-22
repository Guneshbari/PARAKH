"""Unit tests for BaseRiskModel abstraction and NotFittedError handling."""
import numpy as np
import pytest

from src.ml.models.base import BaseRiskModel, NotFittedError


class DummyEstimator(BaseRiskModel):
    """Minimal test implementation of BaseRiskModel."""

    def fit(self, X, y, **kwargs):
        self.is_fitted = True
        self.feature_names_in_ = ["feat_1", "feat_2"]
        return self

    def predict_proba(self, X):
        if not self.is_fitted:
            raise NotFittedError("Not fitted yet")
        # Return deterministic probabilities based on input
        return np.full(len(X), 0.35)


def test_base_risk_model_initialization():
    model = DummyEstimator(
        model_name="dummy-risk",
        model_version="0.1.0",
        model_type="TEST_DUMMY",
        hyperparameters={"param_a": 10},
        description="A dummy model for unit testing",
    )
    assert model.model_name == "dummy-risk"
    assert model.model_version == "0.1.0"
    assert model.model_type == "TEST_DUMMY"
    assert model.hyperparameters == {"param_a": 10}
    assert not model.is_fitted
    assert model.feature_names_in_ is None

    metadata = model.get_metadata()
    assert metadata["model_name"] == "dummy-risk"
    assert metadata["is_fitted"] is False


def test_base_risk_model_fit_and_predict():
    model = DummyEstimator(
        model_name="dummy-risk",
        model_version="0.1.0",
        model_type="TEST_DUMMY",
    )

    X_dummy = np.array([[1.0, 2.0], [3.0, 4.0]])

    # Calling predict before fit must raise NotFittedError
    with pytest.raises(NotFittedError):
        model.predict(X_dummy)

    # Calling predict_proba before fit must raise NotFittedError
    with pytest.raises(NotFittedError):
        model.predict_proba(X_dummy)

    # After fitting, predict and predict_proba must succeed
    model.fit(X_dummy, np.array([0, 1]))
    assert model.is_fitted is True

    probs = model.predict_proba(X_dummy)
    assert len(probs) == 2
    assert np.allclose(probs, 0.35)

    preds = model.predict(X_dummy, threshold=0.5)
    assert np.array_equal(preds, [0, 0])

    preds_low_thresh = model.predict(X_dummy, threshold=0.3)
    assert np.array_equal(preds_low_thresh, [1, 1])
