"""Unit tests for subgroup fairness auditing and parity calculations."""
import numpy as np
import pytest

from src.ml.evaluation.fairness import audit_subgroup_fairness


def test_subgroup_fairness_auditing():
    y_true = np.array([0, 0, 1, 0, 0, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.7, 0.15, 0.3, 0.8, 0.25, 0.75])
    subgroups = [
        "DELIVERY",
        "DELIVERY",
        "DELIVERY",
        "DELIVERY",
        "RIDE_HAILING",
        "RIDE_HAILING",
        "RIDE_HAILING",
        "RIDE_HAILING",
    ]

    report = audit_subgroup_fairness(
        y_true,
        y_prob,
        subgroups,
        subgroup_field_name="gig_work_type",
        threshold=0.5,
    )

    assert report.subgroup_field == "gig_work_type"
    assert len(report.subgroups) == 2
    assert "DELIVERY" in report.subgroups
    assert "RIDE_HAILING" in report.subgroups

    del_grp = report.subgroups["DELIVERY"]
    assert del_grp.sample_count == 4
    assert del_grp.positive_actual_count == 1
    assert del_grp.favorable_prediction_rate == 0.75

    rh_grp = report.subgroups["RIDE_HAILING"]
    assert rh_grp.sample_count == 4
    assert rh_grp.positive_actual_count == 2
    assert rh_grp.favorable_prediction_rate == 0.50

    # Demographic Parity Ratio = 0.50 / 0.75 = 0.6667
    assert report.demographic_parity_ratio is not None
    assert np.isclose(report.demographic_parity_ratio, 0.6667, atol=1e-3)

    # Disclaimer check
    assert "IMPORTANT LIMITATION" in report.limitations_disclaimer

    d = report.to_dict()
    assert "demographic_parity_ratio" in d
    assert "subgroups" in d


def test_fairness_input_validation():
    with pytest.raises(ValueError, match="cannot be empty"):
        audit_subgroup_fairness([], [], [])

    with pytest.raises(ValueError, match="Length mismatch"):
        audit_subgroup_fairness([0, 1], [0.2], ["A", "A"])
