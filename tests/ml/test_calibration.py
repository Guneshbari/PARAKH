"""Unit tests for probability calibration evaluation and ECE calculations."""
import numpy as np
import pytest

from src.ml.evaluation.calibration import evaluate_calibration


def test_calibration_evaluation_uniform():
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 1])
    y_prob = np.array([0.05, 0.15, 0.25, 0.35, 0.65, 0.75, 0.85, 0.95, 0.45, 0.55])

    result = evaluate_calibration(y_true, y_prob, n_bins=5, strategy="uniform")

    assert result.brier_score >= 0.0
    assert result.expected_calibration_error >= 0.0
    assert result.maximum_calibration_error >= 0.0
    assert result.n_bins_requested == 5
    assert result.n_bins_populated > 0
    assert result.strategy == "uniform"

    # Verify bin structure
    first_bin = result.bins[0]
    assert first_bin.bin_index == 0
    assert first_bin.prob_min == 0.0
    assert first_bin.sample_count > 0

    d = result.to_dict()
    assert "expected_calibration_error" in d
    assert len(d["bins"]) == len(result.bins)


def test_calibration_evaluation_quantile():
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])

    result = evaluate_calibration(y_true, y_prob, n_bins=4, strategy="quantile")
    assert result.strategy == "quantile"
    assert result.n_bins_populated > 0
    assert result.expected_calibration_error >= 0.0


def test_calibration_input_validation():
    with pytest.raises(ValueError, match="cannot be empty"):
        evaluate_calibration([], [])

    with pytest.raises(ValueError, match="Length of y_true and y_prob must match"):
        evaluate_calibration([0, 1], [0.5])

    with pytest.raises(ValueError, match="n_bins must be greater than 1"):
        evaluate_calibration([0, 1], [0.2, 0.8], n_bins=1)

    with pytest.raises(ValueError, match="strategy must be"):
        evaluate_calibration([0, 1], [0.2, 0.8], strategy="invalid_strategy")
