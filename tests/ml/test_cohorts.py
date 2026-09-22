"""Unit tests for cohort evaluation utilities and safe edge case handling."""
import numpy as np
import pytest

from src.ml.constants import CohortArchetype
from src.ml.evaluation.cohorts import evaluate_by_cohort


def test_evaluate_by_cohort_multi_cohort():
    # 3 cohorts: Healthy Volatile (3 samples), Stable (3 samples), Declining (2 samples)
    y_true = np.array([0, 0, 1, 0, 0, 0, 1, 1])
    y_prob = np.array([0.15, 0.20, 0.40, 0.05, 0.10, 0.12, 0.75, 0.85])
    cohorts = [
        CohortArchetype.HEALTHY_VOLATILE.value,
        CohortArchetype.HEALTHY_VOLATILE.value,
        CohortArchetype.HEALTHY_VOLATILE.value,
        CohortArchetype.STABLE.value,
        CohortArchetype.STABLE.value,
        CohortArchetype.STABLE.value,
        CohortArchetype.DECLINING.value,
        CohortArchetype.DECLINING.value,
    ]

    results = evaluate_by_cohort(y_true, y_prob, cohorts, threshold=0.5, include_calibration=False)

    assert len(results) == 3
    assert CohortArchetype.HEALTHY_VOLATILE.value in results
    assert CohortArchetype.STABLE.value in results
    assert CohortArchetype.DECLINING.value in results

    hv_res = results[CohortArchetype.HEALTHY_VOLATILE.value]
    assert hv_res.sample_count == 3
    assert hv_res.positive_count == 1
    assert hv_res.metrics is not None
    assert hv_res.empirical_default_rate == round(1 / 3, 4)

    stable_res = results[CohortArchetype.STABLE.value]
    assert stable_res.sample_count == 3
    assert stable_res.positive_count == 0  # Single-class cohort
    assert stable_res.metrics is not None
    assert stable_res.metrics.roc_auc is None  # Handled safely

    dec_res = results[CohortArchetype.DECLINING.value]
    assert dec_res.sample_count == 2
    assert dec_res.positive_count == 2  # Single-class cohort


def test_evaluate_by_cohort_small_cohort():
    y_true = [0, 1, 0]
    y_prob = [0.2, 0.8, 0.1]
    cohorts = ["CohortA", "CohortA", "CohortTiny"]

    # min_samples_for_metrics=2 means CohortTiny (1 sample) should not compute metrics
    results = evaluate_by_cohort(y_true, y_prob, cohorts, min_samples_for_metrics=2)

    tiny_res = results["CohortTiny"]
    assert tiny_res.sample_count == 1
    assert tiny_res.metrics is None
    assert "Insufficient sample count" in tiny_res.notes


def test_evaluate_by_cohort_input_validation():
    with pytest.raises(ValueError, match="must not be empty"):
        evaluate_by_cohort([], [], [])

    with pytest.raises(ValueError, match="Mismatched lengths"):
        evaluate_by_cohort([0, 1], [0.2], ["A", "A"])
