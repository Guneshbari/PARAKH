"""Unit tests for classification evaluation metrics and edge case handling."""
import numpy as np
import pytest

from src.ml.evaluation.metrics import evaluate_predictions


def test_standard_metrics_evaluation():
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])

    metrics = evaluate_predictions(y_true, y_prob, threshold=0.5)

    assert metrics.total_samples == 8
    assert metrics.positive_samples == 4
    assert metrics.negative_samples == 4
    assert metrics.positive_rate == 0.5

    # Perfect ranking in this toy sample
    assert metrics.roc_auc == 1.0
    assert metrics.pr_auc == 1.0
    assert metrics.brier_score is not None
    assert metrics.brier_score < 0.10

    # With threshold 0.5, predictions match y_true exactly
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.true_positives == 4
    assert metrics.true_negatives == 4
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0
    assert metrics.notes is None


def test_single_class_edge_case():
    # Only negative class present
    y_true_all_zeros = np.array([0, 0, 0, 0, 0])
    y_prob = np.array([0.1, 0.2, 0.15, 0.05, 0.3])

    metrics = evaluate_predictions(y_true_all_zeros, y_prob, threshold=0.5)

    # ROC-AUC and PR-AUC must be safely None without raising an uncaught exception
    assert metrics.roc_auc is None
    assert metrics.pr_auc is None
    assert metrics.brier_score is not None
    assert metrics.notes is not None
    assert "Single-class evaluation" in metrics.notes
    assert metrics.positive_samples == 0
    assert metrics.negative_samples == 5


def test_single_class_all_ones():
    # Only positive class present
    y_true_all_ones = np.array([1, 1, 1, 1])
    y_prob = np.array([0.8, 0.9, 0.7, 0.85])

    metrics = evaluate_predictions(y_true_all_ones, y_prob, threshold=0.5)
    assert metrics.roc_auc is None
    assert metrics.pr_auc is None
    assert metrics.notes is not None
    assert metrics.positive_samples == 4
    assert metrics.negative_samples == 0


def test_zero_division_guard():
    # No positive predictions (model predicts all zeros)
    y_true = np.array([0, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.15, 0.25])

    metrics = evaluate_predictions(y_true, y_prob, threshold=0.5)
    # Precision and F1 must be 0.0 without crashing on zero division
    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0


def test_metrics_input_validation():
    # Empty inputs
    with pytest.raises(ValueError, match="must not be empty"):
        evaluate_predictions([], [])

    # Mismatched lengths
    with pytest.raises(ValueError, match="Length mismatch"):
        evaluate_predictions([0, 1], [0.5])

    # Invalid threshold
    with pytest.raises(ValueError, match="Threshold must be in"):
        evaluate_predictions([0, 1], [0.2, 0.8], threshold=1.5)
