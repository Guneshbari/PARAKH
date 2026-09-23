"""Phase 9 — Inference Pipeline Tests.

Tests the full PARAKH credit risk inference pipeline including:
  - InputValidator (field presence, type checks, range bounds, categorical domains, sufficiency)
  - OutputFormatter (risk tier mapping, presentation score, confidence, insufficient formatting)
  - RiskPredictor (end-to-end prediction, INSUFFICIENT routing, input rejection)

All tests run deterministically without network access or model retraining.
The RiskPredictor is expensive to initialise (loads model + fits preprocessor), so
a session-scoped fixture is used to share a single predictor instance across tests.
"""
import math
import uuid
from typing import Any, Dict

import pytest

from src.ml.constants import (
    PRESENTATION_SCORE_MAX,
    PRESENTATION_SCORE_MIN,
    PROVISIONAL_THRESHOLD_HIGHER,
    PROVISIONAL_THRESHOLD_LOWER,
    RiskTier,
)
from src.ml.inference.input_validator import (
    REQUIRED_INPUT_COLUMNS,
    InputValidationError,
    InputValidator,
)
from src.ml.inference.output_formatter import OutputFormatter, PredictionResponse


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

def _make_valid_application(**overrides) -> Dict[str, Any]:
    """Return a valid, contract-compliant application dict.

    All field values are mid-range legal values that satisfy data sufficiency rules,
    so the predictor should produce a scored (non-INSUFFICIENT) response.
    """
    base: Dict[str, Any] = {
        # Raw application inputs
        "requested_loan_amount": 50000.0,
        "loan_tenure_months": 12,
        "years_working": 3.5,
        "average_working_days": 22.0,
        "gig_work_type": "DELIVERY",
        "loan_purpose": "WORKING_CAPITAL",
        # Mandatory derived features
        "feat_inc_median_90d": 25000.0,
        "feat_inc_p25_90d": 18000.0,
        "feat_inc_cv_90d": 0.30,
        "feat_inc_downside_var": 15000000.0,
        "feat_trend_slope_90d": 200.0,
        "feat_trend_momentum_30_90": 1.05,
        "feat_act_active_days_ratio": 0.75,
        "feat_act_zero_earn_weeks": 1.0,
        "feat_rec_bounceback_ratio": 1.2,
        "feat_rec_days_to_recover": 5.0,
        "feat_liq_buffer_to_loan": 2.5,
        "feat_liq_burn_months": 6.0,
        "feat_bur_dti_ratio": 0.3,
        "feat_bur_installment_dti": 0.2,
        "feat_bur_total_dti": 0.35,
        "feat_suf_observed_days": 80.0,
        "feat_suf_payout_count": 12.0,
        "feat_suf_group_count": 4.0,
        "feat_suf_missing_ratio": 0.05,
        # Optional derived features
        "feat_inc_mean_90d": 26000.0,
        "feat_inc_trimmed_mean": 25500.0,
        "feat_inc_iqr_ratio": 0.4,
        "feat_inc_min_max_ratio": 0.6,
        "feat_trend_consec_drops": 1.0,
        "feat_act_max_idle_streak": 7.0,
        "feat_act_weekend_intensity": 0.3,
        "feat_rec_max_drawdown": 0.15,
        "feat_ten_years_working": 3.5,
        "feat_ten_platform_rating": 4.2,
        "feat_ten_trips_completed": 1500.0,
        "feat_ten_cancellation_rate": 0.05,
        "feat_liq_net_margin": 0.15,
        "feat_pay_utility_on_time": 0.9,
        "feat_pay_max_bill_delay": 5.0,
        "feat_pay_repay_reliability": 0.85,
        "feat_bur_loan_to_income": 2.0,
        "feat_int_vol_x_recovery": 6.0,
        "feat_int_vol_x_buffer": 7.5,
        "feat_int_trend_x_dti": 60.0,
        "feat_int_resilience_idx": 55.0,
    }
    base.update(overrides)
    return base


def _make_insufficient_application(**overrides) -> Dict[str, Any]:
    """Return a valid application that triggers INSUFFICIENT routing."""
    app = _make_valid_application()
    app["feat_suf_observed_days"] = 10.0   # < 30
    app["feat_suf_payout_count"] = 2.0     # < 4
    app["feat_suf_group_count"] = 1.0      # < 2
    app.update(overrides)
    return app


# ---------------------------------------------------------------------------
# Session-scoped predictor fixture (expensive initialisation done once)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def predictor():
    """Session-scoped RiskPredictor — initialised once for all tests."""
    from src.ml.inference.predictor import RiskPredictor
    return RiskPredictor()


# ===========================================================================
# 1. InputValidator tests
# ===========================================================================

class TestInputValidator:
    """Tests for InputValidator.validate and InputValidator.check_data_sufficiency."""

    def test_valid_application_passes(self):
        """A fully-populated, in-range application must raise no errors."""
        InputValidator.validate(_make_valid_application())

    def test_missing_required_field_raises(self):
        """Removing a required field must raise InputValidationError."""
        app = _make_valid_application()
        del app["feat_inc_median_90d"]
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "feat_inc_median_90d" in str(exc_info.value)

    def test_all_required_columns_listed(self):
        """REQUIRED_INPUT_COLUMNS must contain all 46 expected fields."""
        assert len(REQUIRED_INPUT_COLUMNS) == 46

    def test_prohibited_field_raises(self):
        """A prohibited field present in the dict must raise InputValidationError."""
        app = _make_valid_application()
        app["bank_account_number"] = "1234567890"
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "bank_account_number" in str(exc_info.value)

    def test_excluded_non_predictor_raises(self):
        """An excluded non-predictor column must raise InputValidationError."""
        app = _make_valid_application()
        app["target_default_flag"] = 0
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "target_default_flag" in str(exc_info.value)

    def test_excluded_application_id_raises(self):
        """application_id in the dict must raise InputValidationError."""
        app = _make_valid_application()
        app["application_id"] = str(uuid.uuid4())
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "application_id" in str(exc_info.value)

    def test_invalid_gig_work_type_raises(self):
        """An invalid gig_work_type value must raise InputValidationError."""
        app = _make_valid_application(gig_work_type="FAKE_GIG")
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "gig_work_type" in str(exc_info.value)

    def test_invalid_loan_purpose_raises(self):
        """An invalid loan_purpose value must raise InputValidationError."""
        app = _make_valid_application(loan_purpose="BUY_CAR")
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "loan_purpose" in str(exc_info.value)

    def test_invalid_loan_tenure_raises(self):
        """A loan_tenure_months value not in {6, 9, 12} must raise InputValidationError."""
        app = _make_valid_application(loan_tenure_months=18)
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "loan_tenure_months" in str(exc_info.value)

    def test_out_of_range_numeric_raises(self):
        """A numeric feature outside its contracted bounds must raise InputValidationError."""
        app = _make_valid_application(feat_inc_cv_90d=99.0)  # max = 5.0
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "feat_inc_cv_90d" in str(exc_info.value)

    def test_nan_value_raises(self):
        """A NaN value in a numeric field must raise InputValidationError."""
        app = _make_valid_application(feat_inc_median_90d=float("nan"))
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "feat_inc_median_90d" in str(exc_info.value)

    def test_inf_value_raises(self):
        """An infinite value in a numeric field must raise InputValidationError."""
        app = _make_valid_application(feat_trend_slope_90d=float("inf"))
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "feat_trend_slope_90d" in str(exc_info.value)

    def test_wrong_type_for_numeric_field_raises(self):
        """Passing a string for a numeric field must raise InputValidationError."""
        app = _make_valid_application(feat_inc_cv_90d="high")
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert "feat_inc_cv_90d" in str(exc_info.value)

    def test_multiple_errors_reported(self):
        """Multiple violations must all be reported in a single InputValidationError."""
        app = _make_valid_application(gig_work_type="BAD", loan_purpose="BAD")
        del app["feat_inc_median_90d"]
        # Remove one more
        del app["feat_bur_dti_ratio"]
        with pytest.raises(InputValidationError) as exc_info:
            InputValidator.validate(app)
        assert exc_info.value.errors  # must have multiple errors

    # Data sufficiency checks

    def test_sufficient_application_passes_sufficiency(self):
        """A fully-observed application must pass the sufficiency check."""
        app = _make_valid_application()
        is_insuf, reasons = InputValidator.check_data_sufficiency(app)
        assert not is_insuf
        assert reasons == []

    def test_low_observed_days_flags_insufficient(self):
        """feat_suf_observed_days < 30 must trigger INSUFFICIENT."""
        app = _make_valid_application(feat_suf_observed_days=20.0)
        is_insuf, reasons = InputValidator.check_data_sufficiency(app)
        assert is_insuf
        assert any("observed" in r.lower() for r in reasons)

    def test_low_payout_count_flags_insufficient(self):
        """feat_suf_payout_count < 4 must trigger INSUFFICIENT."""
        app = _make_valid_application(feat_suf_payout_count=3.0)
        is_insuf, reasons = InputValidator.check_data_sufficiency(app)
        assert is_insuf
        assert any("payout" in r.lower() for r in reasons)

    def test_low_group_count_flags_insufficient(self):
        """feat_suf_group_count < 2 must trigger INSUFFICIENT."""
        app = _make_valid_application(feat_suf_group_count=1.0)
        is_insuf, reasons = InputValidator.check_data_sufficiency(app)
        assert is_insuf
        assert any("signal group" in r.lower() for r in reasons)

    def test_boundary_observed_days_exact_30_passes(self):
        """feat_suf_observed_days = 30.0 must NOT trigger insufficient (boundary inclusive)."""
        app = _make_valid_application(feat_suf_observed_days=30.0)
        is_insuf, _ = InputValidator.check_data_sufficiency(app)
        assert not is_insuf


# ===========================================================================
# 2. OutputFormatter tests
# ===========================================================================

class TestOutputFormatter:
    """Tests for OutputFormatter tier mapping, score, confidence, and formatting."""

    @pytest.mark.parametrize("prob,expected_tier", [
        (0.0, RiskTier.LOWER),
        (0.10, RiskTier.LOWER),
        (0.1999, RiskTier.LOWER),
        (0.20, RiskTier.MODERATE),
        (0.30, RiskTier.MODERATE),
        (0.4499, RiskTier.MODERATE),
        (0.45, RiskTier.HIGHER),
        (0.70, RiskTier.HIGHER),
        (1.00, RiskTier.HIGHER),
    ])
    def test_risk_tier_mapping(self, prob, expected_tier):
        """Risk tier must match the frozen threshold contract."""
        assert OutputFormatter._map_risk_tier(prob) == expected_tier

    @pytest.mark.parametrize("prob,expected_score", [
        (0.0, PRESENTATION_SCORE_MAX),   # p=0 → score=850
        (1.0, PRESENTATION_SCORE_MIN),   # p=1 → score=300
        (0.5, 575),                      # midpoint
    ])
    def test_presentation_score_formula(self, prob, expected_score):
        """Presentation score formula must match the frozen contract."""
        score = OutputFormatter._compute_presentation_score(prob)
        assert score == expected_score

    def test_presentation_score_clamped_lower(self):
        """Score must be clamped to PRESENTATION_SCORE_MIN at very high probability."""
        score = OutputFormatter._compute_presentation_score(1.0)
        assert score == PRESENTATION_SCORE_MIN

    def test_presentation_score_clamped_upper(self):
        """Score must be clamped to PRESENTATION_SCORE_MAX at very low probability."""
        score = OutputFormatter._compute_presentation_score(0.0)
        assert score == PRESENTATION_SCORE_MAX

    def test_presentation_score_in_bounds_for_any_prob(self):
        """Presentation score must lie in [300, 850] for any valid probability."""
        for prob in [0.0, 0.01, 0.1, 0.2, 0.45, 0.8, 0.99, 1.0]:
            score = OutputFormatter._compute_presentation_score(prob)
            assert PRESENTATION_SCORE_MIN <= score <= PRESENTATION_SCORE_MAX

    def test_confidence_in_bounds(self):
        """Confidence must be in [0, 1] for all probabilities."""
        for prob in [0.0, 0.10, 0.20, 0.32, 0.45, 0.70, 1.0]:
            conf = OutputFormatter._compute_confidence(prob)
            assert 0.0 <= conf <= 1.0, f"Confidence out of bounds for prob={prob}: {conf}"

    def test_format_scored_response_structure(self):
        """format_scored must return a PredictionResponse with all required fields."""
        response = OutputFormatter.format_scored(
            probability=0.30,
            explanation_factors={"key_protective_factors": [], "key_risk_factors": [], "disclaimer": ""},
            model_name="volatility-aware-risk-model",
            model_version="1.0.0",
            feature_variant="VOLATILITY_AWARE",
        )
        assert isinstance(response, PredictionResponse)
        assert response.risk_tier == RiskTier.MODERATE.value
        assert response.presentation_score is not None
        assert response.repayment_risk_probability == pytest.approx(0.30, abs=1e-5)
        assert not response.is_insufficient_evidence
        assert response.missing_or_insufficient_signals == []
        assert response.model_name == "volatility-aware-risk-model"
        assert response.feature_variant == "VOLATILITY_AWARE"
        assert "assessed_at" in response.to_dict()

    def test_format_insufficient_response_structure(self):
        """format_insufficient must return INSUFFICIENT tier with null probability/score."""
        response = OutputFormatter.format_insufficient(
            reasons=["Observed days 10 < 30 days minimum."],
            model_name="volatility-aware-risk-model",
            model_version="1.0.0",
            feature_variant="VOLATILITY_AWARE",
        )
        assert response.risk_tier == RiskTier.INSUFFICIENT.value
        assert response.repayment_risk_probability is None
        assert response.presentation_score is None
        assert response.is_insufficient_evidence
        assert response.confidence_or_data_sufficiency == 0.0
        assert len(response.missing_or_insufficient_signals) > 0

    def test_to_dict_is_json_serialisable(self):
        """PredictionResponse.to_dict() must be JSON-serialisable."""
        import json
        response = OutputFormatter.format_scored(
            probability=0.15,
            explanation_factors={"key_protective_factors": [], "key_risk_factors": [], "disclaimer": "x"},
            model_name="test-model",
            model_version="1.0.0",
            feature_variant="VOLATILITY_AWARE",
        )
        # Must not raise
        serialised = json.dumps(response.to_dict())
        loaded = json.loads(serialised)
        assert loaded["risk_tier"] == "LOWER"


# ===========================================================================
# 3. RiskPredictor end-to-end tests
# ===========================================================================

class TestRiskPredictor:
    """End-to-end tests for the RiskPredictor pipeline."""

    def test_predictor_initialises(self, predictor):
        """RiskPredictor must initialise without error."""
        assert predictor is not None

    def test_predict_valid_application_returns_response(self, predictor):
        """predict() must return a PredictionResponse for a valid application."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert isinstance(response, PredictionResponse)

    def test_predict_scored_not_insufficient(self, predictor):
        """A sufficient application must NOT be flagged as INSUFFICIENT."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert not response.is_insufficient_evidence
        assert response.risk_tier != RiskTier.INSUFFICIENT.value

    def test_predict_probability_in_unit_interval(self, predictor):
        """Predicted probability must lie in [0, 1]."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert response.repayment_risk_probability is not None
        assert 0.0 <= response.repayment_risk_probability <= 1.0

    def test_predict_score_in_bounds(self, predictor):
        """Presentation score must be in [300, 850] for a scored application."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert response.presentation_score is not None
        assert PRESENTATION_SCORE_MIN <= response.presentation_score <= PRESENTATION_SCORE_MAX

    def test_predict_insufficient_application_returns_insufficient_tier(self, predictor):
        """An application failing sufficiency checks must return INSUFFICIENT tier."""
        app = _make_insufficient_application()
        response = predictor.predict(app)
        assert response.is_insufficient_evidence
        assert response.risk_tier == RiskTier.INSUFFICIENT.value

    def test_predict_insufficient_has_null_probability(self, predictor):
        """An INSUFFICIENT response must have null probability and score."""
        app = _make_insufficient_application()
        response = predictor.predict(app)
        assert response.repayment_risk_probability is None
        assert response.presentation_score is None

    def test_predict_insufficient_has_reasons(self, predictor):
        """An INSUFFICIENT response must contain at least one reason string."""
        app = _make_insufficient_application()
        response = predictor.predict(app)
        assert len(response.missing_or_insufficient_signals) > 0

    def test_predict_invalid_input_raises_validation_error(self, predictor):
        """predict() with a missing required field must raise InputValidationError."""
        app = _make_valid_application()
        del app["feat_inc_median_90d"]
        with pytest.raises(InputValidationError):
            predictor.predict(app)

    def test_predict_with_prohibited_field_raises(self, predictor):
        """predict() with a prohibited field must raise InputValidationError."""
        app = _make_valid_application()
        app["raw_bank_statements"] = "..."
        with pytest.raises(InputValidationError):
            predictor.predict(app)

    def test_predict_deterministic(self, predictor):
        """Two calls with identical input must produce identical output."""
        app = _make_valid_application()
        r1 = predictor.predict(app)
        r2 = predictor.predict(app)
        assert r1.repayment_risk_probability == r2.repayment_risk_probability
        assert r1.risk_tier == r2.risk_tier
        assert r1.presentation_score == r2.presentation_score

    def test_response_contains_model_provenance(self, predictor):
        """Response must include model_name, model_version, and feature_variant."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert response.model_name == "volatility-aware-risk-model"
        assert response.model_version == "1.0.0"
        assert response.feature_variant == "VOLATILITY_AWARE"

    def test_response_to_dict_is_json_serialisable(self, predictor):
        """Response.to_dict() must be fully JSON-serialisable."""
        import json
        app = _make_valid_application()
        response = predictor.predict(app)
        serialised = json.dumps(response.to_dict())
        loaded = json.loads(serialised)
        assert "risk_tier" in loaded
        assert "assessed_at" in loaded

    def test_response_has_diagnostic_threshold_status(self, predictor):
        """Response must include the diagnostic_threshold_status field."""
        app = _make_valid_application()
        response = predictor.predict(app)
        assert response.diagnostic_threshold_status
        assert "0.50" in response.diagnostic_threshold_status or "provisional" in response.diagnostic_threshold_status.lower()

    def test_explanation_factors_present(self, predictor):
        """A scored response must have explanation_factors with the expected keys."""
        app = _make_valid_application()
        response = predictor.predict(app)
        expl = response.explanation_factors
        assert isinstance(expl, dict)
        assert "key_protective_factors" in expl
        assert "key_risk_factors" in expl
        assert "disclaimer" in expl

    def test_risk_tier_consistent_with_probability(self, predictor):
        """Risk tier must be consistent with the returned probability."""
        app = _make_valid_application()
        response = predictor.predict(app)
        prob = response.repayment_risk_probability
        tier = response.risk_tier

        if prob < PROVISIONAL_THRESHOLD_LOWER:
            assert tier == RiskTier.LOWER.value
        elif prob < PROVISIONAL_THRESHOLD_HIGHER:
            assert tier == RiskTier.MODERATE.value
        else:
            assert tier == RiskTier.HIGHER.value
