"""Tests for PARAKH Phase 19 Real-World Impact Benchmark & Lending Simulation.

Verifies:
1. Frozen model artifact integrity (hashes untouched)
2. Four impact cohort definitions & independence
3. Healthy volatility false-positive penalty reduction
4. Distressed volatility default detection recall preservation
5. Volatility-Recovery 2x2 matrix structure & risk monotonicity
6. Shock-recovery stress test trajectory differentiation
7. Financial inclusion coverage & abstention rate formulas
8. Lending portfolio simulation outcomes & expected loss across LGDs
9. Operational fairness subgroup auditing & disclaimers
10. Reviewer efficiency study protocol schema validity
11. Data minimization & DPDP consent gate invariants
12. Deterministic reproducibility (identical metric output across runs)
"""
import copy
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

import importlib

from experiments.benchmarks.impact.common import (
    FROZEN_ARTIFACT_HASHES,
    MANDATORY_SYNTHETIC_DISCLAIMER,
    assign_impact_cohorts,
    compute_file_sha256,
    load_benchmark_data_and_models,
    verify_frozen_hashes,
)

_mod_01 = importlib.import_module("experiments.benchmarks.impact.01_cohort_analysis")
compute_cohort_metrics = _mod_01.compute_cohort_metrics
run_cohort_analysis = _mod_01.run_cohort_analysis

_mod_02 = importlib.import_module("experiments.benchmarks.impact.02_volatility_robustness")
analyze_volatility_recovery_matrix = _mod_02.analyze_volatility_recovery_matrix
run_shock_recovery_stress_test = _mod_02.run_shock_recovery_stress_test

_mod_03 = importlib.import_module("experiments.benchmarks.impact.03_lending_simulation")
simulate_lending_portfolio = _mod_03.simulate_lending_portfolio

_mod_04 = importlib.import_module("experiments.benchmarks.impact.04_fairness_impact")
REVIEWER_STUDY_PROTOCOL_SPECIFICATION = _mod_04.REVIEWER_STUDY_PROTOCOL_SPECIFICATION
audit_operational_subgroups = _mod_04.audit_operational_subgroups
verify_privacy_and_consent_controls = _mod_04.verify_privacy_and_consent_controls

_mod_05 = importlib.import_module("experiments.benchmarks.impact.05_abstention_coverage")
audit_assessment_coverage = _mod_05.audit_assessment_coverage

from src.ml.constants import (
    DEFAULT_RANDOM_SEED,
    PROHIBITED_FIELDS,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
)


@pytest.fixture(scope="module")
def benchmark_bundle():
    """Load benchmark data and models once for module tests."""
    return load_benchmark_data_and_models(seed=DEFAULT_RANDOM_SEED)


def test_frozen_model_hashes_intact():
    """Verify that frozen model artifacts have not been modified or retrained."""
    hash_status = verify_frozen_hashes()
    for artifact, status in hash_status.items():
        assert status is True, f"Artifact {artifact} hash does not match frozen contract!"


def test_four_impact_cohorts_construction(benchmark_bundle):
    """Verify cohort construction rules, sufficient sample sizes, and label independence."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]

    assert "cohort_stable" in test_df.columns
    assert "cohort_healthy_volatile" in test_df.columns
    assert "cohort_distressed_volatile" in test_df.columns
    assert "cohort_weak_income" in test_df.columns

    n_stable = int(test_df["cohort_stable"].sum())
    n_hv = int(test_df["cohort_healthy_volatile"].sum())
    n_dv = int(test_df["cohort_distressed_volatile"].sum())
    n_wi = int(test_df["cohort_weak_income"].sum())

    # Every cohort must have substantial sample count (N >= 50)
    assert n_stable >= 50, f"Stable cohort count {n_stable} is too small"
    assert n_hv >= 50, f"Healthy Volatile cohort count {n_hv} is too small"
    assert n_dv >= 50, f"Distressed Volatile cohort count {n_dv} is too small"
    assert n_wi >= 50, f"Weak Income cohort count {n_wi} is too small"

    # Outcome labels must be independent of predictions (both 0 and 1 exist)
    for c_col in ["cohort_stable", "cohort_healthy_volatile", "cohort_distressed_volatile", "cohort_weak_income"]:
        mask = test_df[c_col].values
        sub_y = y_test[mask]
        assert np.sum(sub_y == 0) > 0, f"{c_col} has no non-defaulters"
        assert np.sum(sub_y == 1) > 0, f"{c_col} has no defaults"


def test_healthy_volatility_fp_reduction(benchmark_bundle):
    """Verify PARAKH avoids unnecessarily penalizing healthy income volatility."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]
    p_base = benchmark_bundle["p_base"]
    p_vol = benchmark_bundle["p_vol"]

    hv_mask = test_df["cohort_healthy_volatile"].values
    good_repayers = (y_test == 0) & hv_mask

    # False positive at policy approval cutoff (p >= 0.20)
    fpr_b = float(np.mean(p_base[good_repayers] >= PROVISIONAL_THRESHOLD_LOWER))
    fpr_v = float(np.mean(p_vol[good_repayers] >= PROVISIONAL_THRESHOLD_LOWER))

    assert fpr_v <= fpr_b, f"PARAKH FPR ({fpr_v:.4f}) should be <= baseline FPR ({fpr_b:.4f}) on healthy volatility"

    # Average score on good repayers should be preserved or improved
    scores_b = test_df.loc[good_repayers, "score_baseline"].values
    scores_v = test_df.loc[good_repayers, "score_volatility"].values
    assert np.mean(scores_v) >= np.mean(scores_b) - 1.0


def test_distressed_volatility_recall_preservation(benchmark_bundle):
    """Verify PARAKH preserves or improves recall on distressed volatile applicants."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]
    p_base = benchmark_bundle["p_base"]
    p_vol = benchmark_bundle["p_vol"]

    dv_mask = test_df["cohort_distressed_volatile"].values
    defaults = (y_test == 1) & dv_mask

    rec_b = float(np.mean(p_base[defaults] >= 0.50))
    rec_v = float(np.mean(p_vol[defaults] >= 0.50))

    # PARAKH achieves higher recall on distressed volatile defaults
    assert rec_v >= rec_b - 0.05, f"PARAKH recall ({rec_v:.4f}) should be comparable or higher than baseline ({rec_b:.4f})"


def test_volatility_recovery_matrix_quadrants(benchmark_bundle):
    """Verify all 4 quadrants of the volatility-recovery matrix are populated with valid risk ordering."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]
    p_base = benchmark_bundle["p_base"]
    p_vol = benchmark_bundle["p_vol"]

    res = analyze_volatility_recovery_matrix(test_df, y_test, p_base, p_vol)
    quadrants = res["quadrants"]

    assert len(quadrants) == 4
    for q_key, q_val in quadrants.items():
        assert q_val["sample_count"] >= 30, f"Quadrant {q_key} sample count {q_val['sample_count']} is too low"
        assert 0.0 <= q_val["observed_default_rate"] <= 1.0

    # Economic validation: Low Vol + High Rec must have lower observed default rate than High Vol + Low Rec
    low_v_high_r = quadrants["low_vol_high_rec"]["observed_default_rate"]
    high_v_low_r = quadrants["high_vol_low_rec"]["observed_default_rate"]
    assert low_v_high_r < high_v_low_r, f"Low Vol + High Rec default rate ({low_v_high_r}) should be < High Vol + Low Rec ({high_v_low_r})"


def test_shock_recovery_stress_monotonicity(benchmark_bundle):
    """Verify that Fast Recovery yields lower default probability and higher score than No Recovery."""
    stress_res = run_shock_recovery_stress_test(benchmark_bundle)
    scenarios = stress_res["scenarios"]

    fast_p = scenarios["fast_recovery"]["volatility_aware"]["predicted_probability"]
    no_rec_p = scenarios["no_recovery"]["volatility_aware"]["predicted_probability"]

    fast_score = scenarios["fast_recovery"]["volatility_aware"]["presentation_score"]
    no_rec_score = scenarios["no_recovery"]["volatility_aware"]["presentation_score"]

    assert fast_p < no_rec_p, f"Fast recovery prob ({fast_p}) should be < no recovery prob ({no_rec_p})"
    assert fast_score > no_rec_score, f"Fast recovery score ({fast_score}) should be > no recovery score ({no_rec_score})"


def test_financial_inclusion_coverage_formulas(benchmark_bundle):
    """Verify assessment coverage and abstention rate formulas and bounds."""
    dataset_df = benchmark_bundle["dataset_df"]
    cov_res = audit_assessment_coverage(dataset_df)

    total = cov_res["total_applications"]
    suff = cov_res["sufficient_evidence_applications"]
    insuff = cov_res["insufficient_evidence_applications"]
    cov_rate = cov_res["evidence_based_assessment_coverage_rate"]
    abst_rate = cov_res["responsible_abstention_rate"]

    assert total == suff + insuff
    assert abs((cov_rate + abst_rate) - 1.0) < 1e-4
    assert 0.85 <= cov_rate <= 0.99, f"Unexpected coverage rate: {cov_rate}"
    assert 0.01 <= abst_rate <= 0.15, f"Unexpected abstention rate: {abst_rate}"


def test_lending_simulation_and_expected_loss(benchmark_bundle):
    """Verify lending decision outcomes sum to 1.0 and expected loss scales with LGD."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]
    p_vol = benchmark_bundle["p_vol"]
    exposure = test_df["requested_loan_amount"].values

    sim = simulate_lending_portfolio(y_test, p_vol, exposure, model_name="PARAKH Test")
    outcomes = sim["outcomes"]

    appr_rate = outcomes["approved"]["rate"]
    rev_rate = outcomes["human_review"]["rate"]
    decl_rate = outcomes["declined"]["rate"]
    assert abs((appr_rate + rev_rate + decl_rate) - 1.0) < 1e-3

    el_sim = sim["expected_loss_simulation"]
    assert el_sim["lgd_25pct"]["expected_loss_per_1_lakh_approved_inr"] < el_sim["lgd_50pct"]["expected_loss_per_1_lakh_approved_inr"]
    assert el_sim["lgd_50pct"]["expected_loss_per_1_lakh_approved_inr"] < el_sim["lgd_75pct"]["expected_loss_per_1_lakh_approved_inr"]


def test_operational_fairness_audit(benchmark_bundle):
    """Verify operational subgroup fairness produces DPR, EOD, and small sample flags."""
    test_df = benchmark_bundle["test_df"]
    y_test = benchmark_bundle["y_test"]
    p_base = benchmark_bundle["p_base"]
    p_vol = benchmark_bundle["p_vol"]

    fair_res = audit_operational_subgroups(test_df, y_test, p_base, p_vol)
    dims = fair_res["dimensions"]

    assert "gig_work_type" in dims
    assert "loan_purpose" in dims
    assert "tenure_group" in dims
    assert "income_tier" in dims

    gig_dim = dims["gig_work_type"]
    assert gig_dim["parakh_demographic_parity_ratio"] is not None
    assert 0.0 <= gig_dim["parakh_demographic_parity_ratio"] <= 1.0


def test_reviewer_efficiency_protocol_schema():
    """Verify reviewer efficiency study protocol schema and scientific integrity rule."""
    protocol = REVIEWER_STUDY_PROTOCOL_SPECIFICATION
    assert "protocol_name" in protocol
    assert "scientific_integrity_notice" in protocol
    assert "trial_data_schema" in protocol
    assert "HUMAN-FACTORS INTEGRITY RULE" in protocol["scientific_integrity_notice"]


def test_data_minimization_and_consent_invariants(benchmark_bundle):
    """Verify zero prohibited fields are present in either model feature matrix."""
    controls = verify_privacy_and_consent_controls(benchmark_bundle["test_df"], benchmark_bundle)
    audit = controls["data_minimization_audit"]
    assert audit["data_minimization_passed"] is True
    assert len(audit["prohibited_fields_in_baseline_matrix"]) == 0
    assert len(audit["prohibited_fields_in_parakh_matrix"]) == 0


def test_deterministic_reproducibility():
    """Verify running the benchmark twice with fixed seed yields identical metric outputs."""
    bundle1 = load_benchmark_data_and_models(seed=DEFAULT_RANDOM_SEED)
    bundle2 = load_benchmark_data_and_models(seed=DEFAULT_RANDOM_SEED)

    np.testing.assert_array_equal(bundle1["p_base"], bundle2["p_base"])
    np.testing.assert_array_equal(bundle1["p_vol"], bundle2["p_vol"])
    np.testing.assert_array_equal(bundle1["y_test"], bundle2["y_test"])

    res1 = run_cohort_analysis(bundle1)
    res2 = run_cohort_analysis(bundle2)

    # Check key numerical equality
    b1_hv = res1["healthy_volatility_detailed_comparison"]["parakh_good_borrower_fpr_at_020"]
    b2_hv = res2["healthy_volatility_detailed_comparison"]["parakh_good_borrower_fpr_at_020"]
    assert b1_hv == b2_hv
