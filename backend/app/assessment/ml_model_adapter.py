"""Concrete MLModel adapter integrating Phase 9 RiskPredictor into PARAKH backend.

Bridges the backend's AssessmentEngine/MLModel boundary with the frozen Phase 9
RiskPredictor, translating AssessmentInput into the exact 46-field flat inference contract
and formatting PredictionResponse into standard MLModelOutput.
"""
from decimal import Decimal
import logging
import threading
from typing import Any, Dict, Optional, Tuple

from app.assessment.exceptions import (
    AssessmentEngineError,
    AssessmentInputError,
)
from app.assessment.ml_engine import MLModel, MLModelOutput
from app.assessment.schemas import AssessmentInput
from app.core.config import settings
from app.models.assessment import RiskLevel
from src.ml.constants import PROHIBITED_FIELDS
from src.ml.inference.input_validator import InputValidationError
from src.ml.inference.output_formatter import PredictionResponse
from src.ml.inference.predictor import RiskPredictor

logger = logging.getLogger(__name__)

# Module-level thread-safe singleton cache for RiskPredictor
_PREDICTOR_LOCK = threading.Lock()
_SHARED_PREDICTOR: Optional[RiskPredictor] = None


def get_shared_risk_predictor(
    manifest_path: Optional[str] = None,
    dataset_path: Optional[str] = None,
) -> RiskPredictor:
    """Retrieve or lazily initialize the shared singleton RiskPredictor instance.

    Guarantees expensive pipeline initialization and artifact loading occur only once
    across the entire application lifecycle.

    Args:
        manifest_path: Optional explicit manifest path. Defaults to settings.ML_MANIFEST_PATH.
        dataset_path: Optional explicit dataset path. Defaults to settings.ML_DATASET_PATH.

    Returns:
        RiskPredictor: Shared thread-safe inference predictor instance.
    """
    global _SHARED_PREDICTOR
    if _SHARED_PREDICTOR is not None:
        return _SHARED_PREDICTOR

    with _PREDICTOR_LOCK:
        if _SHARED_PREDICTOR is None:
            resolved_manifest = manifest_path or settings.ML_MANIFEST_PATH
            resolved_dataset = dataset_path or settings.ML_DATASET_PATH
            logger.info(
                "Initializing shared RiskPredictor singleton (manifest=%s, dataset=%s)",
                resolved_manifest,
                resolved_dataset,
            )
            try:
                _SHARED_PREDICTOR = RiskPredictor(
                    manifest_path=resolved_manifest,
                    dataset_path=resolved_dataset,
                )
            except FileNotFoundError as exc:
                raise AssessmentEngineError(
                    f"ML model artifact or manifest not found: {exc}"
                ) from exc
            except Exception as exc:
                raise AssessmentEngineError(
                    f"Failed to initialize ML inference pipeline: {exc}"
                ) from exc
        return _SHARED_PREDICTOR


def reset_shared_risk_predictor() -> None:
    """Reset shared predictor singleton. Intended strictly for test fixture teardown."""
    global _SHARED_PREDICTOR
    with _PREDICTOR_LOCK:
        _SHARED_PREDICTOR = None


class MLModelAdapter(MLModel):
    """Production MLModel implementation wrapping Phase 9 RiskPredictor.

    Implements the abstract MLModel boundary contract defined in app.assessment.ml_engine.
    Preserves all 46 input features, handles data sufficiency routing, and translates
    rich TreeSHAP explanations into backend and frontend-compatible schemas.
    """

    def __init__(self, predictor: Optional[RiskPredictor] = None) -> None:
        """Initialize MLModelAdapter with an optional or shared RiskPredictor instance."""
        self._predictor = predictor or get_shared_risk_predictor()

    @property
    def model_name(self) -> str:
        """Identifier of the active frozen model."""
        return getattr(self._predictor, "_model_name", "volatility-aware-risk-model")

    @property
    def model_version(self) -> str:
        """Semantic version string of the active frozen model."""
        return getattr(self._predictor, "_model_version", "1.0.0")

    def predict(self, input_data: AssessmentInput) -> MLModelOutput:
        """Execute ML model inference on backend assessment input.

        Args:
            input_data: Validated, privacy-compliant AssessmentInput from service layer.

        Returns:
            MLModelOutput: Standardized evaluation output matching persistence model.

        Raises:
            AssessmentInputError: If input data violates contract ranges or rules.
            AssessmentEngineError: If model inference or pipeline execution fails.
        """
        # 1. Transform AssessmentInput into flat 46-field ML dictionary
        app_dict = self.transform_input_to_ml_dict(input_data)

        # 2. Invoke frozen Phase 9 RiskPredictor
        try:
            prediction_response: PredictionResponse = self._predictor.predict(app_dict)
        except InputValidationError as exc:
            logger.warning("ML input validation rejected assessment input: %s", exc)
            raise AssessmentInputError(str(exc)) from exc
        except Exception as exc:
            logger.error("ML inference pipeline execution failed: %s", exc, exc_info=True)
            raise AssessmentEngineError(f"ML inference pipeline error: {exc}") from exc

        # 3. Translate PredictionResponse to standard MLModelOutput
        return self.map_prediction_to_output(prediction_response, app_dict)

    @classmethod
    def transform_input_to_ml_dict(cls, input_data: AssessmentInput) -> Dict[str, Any]:
        """Transform backend AssessmentInput into flat 46-field dict for RiskPredictor.

        Adheres strictly to docs/backend-ml-integration-contract.md.
        """
        derived = dict(input_data.derived_features or {})

        # Security check: ensure no prohibited keys leaked into derived features
        for key in derived:
            if key in PROHIBITED_FIELDS:
                raise AssessmentInputError(
                    f"Prohibited privacy-invasive field '{key}' rejected by data-minimization policy."
                )

        # --- 1. Raw loan terms & profile inputs (6 fields) ---
        req_amount = float(input_data.requested_loan_amount)

        # Loan tenure: must be in {6, 9, 12}
        tenure = input_data.loan_tenure_months
        if tenure not in (6, 9, 12):
            # Fallback to closest valid tenure or standard 12 months
            tenure = 12 if tenure is None else (6 if tenure < 8 else (9 if tenure < 11 else 12))

        years_work = float(input_data.years_working) if input_data.years_working is not None else 0.0
        years_work = max(0.0, min(50.0, years_work))

        avg_days = float(input_data.average_working_days) if input_data.average_working_days is not None else 20.0
        avg_days = max(0.0, min(31.0, avg_days))

        # Gig work type normalization
        allowed_gig_types = {
            "DELIVERY",
            "RIDE_HAILING",
            "LOGISTICS",
            "HOME_SERVICES",
            "FREELANCE_MICRO",
            "OTHER",
        }
        raw_gig = str(input_data.gig_work_type or "OTHER").upper().strip()
        gig_work_type = raw_gig if raw_gig in allowed_gig_types else "OTHER"

        # Loan purpose normalization
        allowed_purposes = {
            "VEHICLE_MAINTENANCE",
            "WORKING_CAPITAL",
            "EQUIPMENT_PURCHASE",
            "PERSONAL_EMERGENCY",
            "OTHER",
        }
        raw_purpose = str(input_data.loan_purpose or "WORKING_CAPITAL").upper().strip()
        loan_purpose = raw_purpose if raw_purpose in allowed_purposes else "WORKING_CAPITAL"

        # --- Base financial signals ---
        median_inc = (
            float(input_data.median_income)
            if input_data.median_income is not None
            else (float(input_data.average_income) if input_data.average_income is not None else None)
        )
        avg_inc = (
            float(input_data.average_income)
            if input_data.average_income is not None
            else (median_inc if median_inc is not None else None)
        )
        vol_cv = float(input_data.income_volatility) if input_data.income_volatility is not None else None
        active_days = input_data.active_days
        buffer_val = float(input_data.cashflow_buffer) if input_data.cashflow_buffer is not None else None
        obligation_val = float(input_data.existing_obligation) if input_data.existing_obligation is not None else None
        platform_rating = float(input_data.platform_rating) if input_data.platform_rating is not None else None
        pay_regularity = float(input_data.payment_regularity) if input_data.payment_regularity is not None else None
        repay_reliability = float(input_data.repayment_reliability) if input_data.repayment_reliability is not None else None

        # Resolve median income baseline (safe default 7000.0/wk if totally unrecorded)
        safe_median = median_inc if median_inc is not None else 7000.0

        # Trend slope derivation
        trend_slope = 0.0
        if input_data.income_trend:
            t = str(input_data.income_trend).upper()
            if "GROW" in t or "UP" in t:
                trend_slope = 150.0
            elif "DECLIN" in t or "DOWN" in t:
                trend_slope = -200.0
            elif "STABLE" in t:
                trend_slope = 15.0

        # Active days ratio
        act_ratio = min(1.0, max(0.0, float(active_days) / 90.0)) if active_days is not None else 0.65

        # Liquidity buffer to loan
        liq_buffer = (buffer_val / max(1.0, req_amount)) if buffer_val is not None else 0.20

        # DTI ratios (using monthly denominator = median_weekly * 4.33)
        monthly_income_est = max(1.0, safe_median * 4.33)
        dti_ratio = (obligation_val / monthly_income_est) if obligation_val is not None else 0.25
        est_installment = req_amount / float(max(1, tenure))
        installment_dti = est_installment / monthly_income_est
        total_dti = dti_ratio + installment_dti

        # Telemetry sufficiency defaults
        observed_days = 90.0
        payout_count = 12.0
        group_count = 4.0

        # --- 2. Mandatory Core Derived Features (19 fields) ---
        f_inc_median_90d = float(derived.get("feat_inc_median_90d", safe_median))
        f_inc_p25_90d = float(derived.get("feat_inc_p25_90d", safe_median * 0.85))
        f_inc_cv_90d = float(derived.get("feat_inc_cv_90d", vol_cv if vol_cv is not None else 0.25))
        f_inc_downside_var = float(derived.get("feat_inc_downside_var", (safe_median * 0.20) ** 2))
        f_trend_slope_90d = float(derived.get("feat_trend_slope_90d", trend_slope))
        f_trend_momentum_30_90 = float(derived.get("feat_trend_momentum_30_90", 1.0))
        f_act_active_days_ratio = float(derived.get("feat_act_active_days_ratio", act_ratio))
        f_act_zero_earn_weeks = float(derived.get("feat_act_zero_earn_weeks", 1.0))
        f_rec_bounceback_ratio = float(derived.get("feat_rec_bounceback_ratio", 1.0))
        f_rec_days_to_recover = float(derived.get("feat_rec_days_to_recover", 7.0))
        f_liq_buffer_to_loan = float(derived.get("feat_liq_buffer_to_loan", liq_buffer))
        f_liq_burn_months = float(derived.get("feat_liq_burn_months", 2.0))
        f_bur_dti_ratio = float(derived.get("feat_bur_dti_ratio", dti_ratio))
        f_bur_installment_dti = float(derived.get("feat_bur_installment_dti", installment_dti))
        f_bur_total_dti = float(derived.get("feat_bur_total_dti", total_dti))
        f_suf_observed_days = float(derived.get("feat_suf_observed_days", observed_days))
        f_suf_payout_count = float(derived.get("feat_suf_payout_count", payout_count))
        f_suf_group_count = float(derived.get("feat_suf_group_count", group_count))
        f_suf_missing_ratio = float(derived.get("feat_suf_missing_ratio", 0.0))

        # --- 3. Optional Derived Features (21 fields) ---
        f_inc_mean_90d = float(derived.get("feat_inc_mean_90d", avg_inc if avg_inc is not None else safe_median))
        f_inc_trimmed_mean = float(derived.get("feat_inc_trimmed_mean", safe_median))
        f_inc_iqr_ratio = float(derived.get("feat_inc_iqr_ratio", 0.35))
        f_inc_min_max_ratio = float(derived.get("feat_inc_min_max_ratio", 0.50))
        f_trend_consec_drops = float(derived.get("feat_trend_consec_drops", 1.0))
        f_act_max_idle_streak = float(derived.get("feat_act_max_idle_streak", 5.0))
        f_act_weekend_intensity = float(derived.get("feat_act_weekend_intensity", 0.30))
        f_rec_max_drawdown = float(derived.get("feat_rec_max_drawdown", 0.20))
        f_ten_years_working = float(derived.get("feat_ten_years_working", years_work))
        f_ten_platform_rating = float(derived.get("feat_ten_platform_rating", platform_rating if platform_rating is not None else 4.50))
        f_ten_trips_completed = float(derived.get("feat_ten_trips_completed", 500.0))
        f_ten_cancellation_rate = float(derived.get("feat_ten_cancellation_rate", 0.03))
        f_liq_net_margin = float(derived.get("feat_liq_net_margin", 0.15))
        f_pay_utility_on_time = float(derived.get("feat_pay_utility_on_time", pay_regularity if pay_regularity is not None else 0.90))
        f_pay_max_bill_delay = float(derived.get("feat_pay_max_bill_delay", 3.0))
        f_pay_repay_reliability = float(derived.get("feat_pay_repay_reliability", repay_reliability if repay_reliability is not None else 0.95))
        f_bur_loan_to_income = float(derived.get("feat_bur_loan_to_income", req_amount / monthly_income_est))

        # Interaction terms
        f_int_vol_x_recovery = float(derived.get("feat_int_vol_x_recovery", f_inc_cv_90d * f_rec_days_to_recover))
        f_int_vol_x_buffer = float(derived.get("feat_int_vol_x_buffer", f_inc_cv_90d * f_liq_buffer_to_loan))
        f_int_trend_x_dti = float(derived.get("feat_int_trend_x_dti", f_trend_slope_90d * f_bur_dti_ratio))
        f_int_resilience_idx = float(derived.get("feat_int_resilience_idx", 50.0))

        return {
            # 6 raw profile/loan inputs
            "requested_loan_amount": req_amount,
            "loan_tenure_months": tenure,
            "years_working": years_work,
            "average_working_days": avg_days,
            "gig_work_type": gig_work_type,
            "loan_purpose": loan_purpose,
            # 19 core mandatory derived features
            "feat_inc_median_90d": f_inc_median_90d,
            "feat_inc_p25_90d": f_inc_p25_90d,
            "feat_inc_cv_90d": f_inc_cv_90d,
            "feat_inc_downside_var": f_inc_downside_var,
            "feat_trend_slope_90d": f_trend_slope_90d,
            "feat_trend_momentum_30_90": f_trend_momentum_30_90,
            "feat_act_active_days_ratio": f_act_active_days_ratio,
            "feat_act_zero_earn_weeks": f_act_zero_earn_weeks,
            "feat_rec_bounceback_ratio": f_rec_bounceback_ratio,
            "feat_rec_days_to_recover": f_rec_days_to_recover,
            "feat_liq_buffer_to_loan": f_liq_buffer_to_loan,
            "feat_liq_burn_months": f_liq_burn_months,
            "feat_bur_dti_ratio": f_bur_dti_ratio,
            "feat_bur_installment_dti": f_bur_installment_dti,
            "feat_bur_total_dti": f_bur_total_dti,
            "feat_suf_observed_days": f_suf_observed_days,
            "feat_suf_payout_count": f_suf_payout_count,
            "feat_suf_group_count": f_suf_group_count,
            "feat_suf_missing_ratio": f_suf_missing_ratio,
            # 21 optional derived features
            "feat_inc_mean_90d": f_inc_mean_90d,
            "feat_inc_trimmed_mean": f_inc_trimmed_mean,
            "feat_inc_iqr_ratio": f_inc_iqr_ratio,
            "feat_inc_min_max_ratio": f_inc_min_max_ratio,
            "feat_trend_consec_drops": f_trend_consec_drops,
            "feat_act_max_idle_streak": f_act_max_idle_streak,
            "feat_act_weekend_intensity": f_act_weekend_intensity,
            "feat_rec_max_drawdown": f_rec_max_drawdown,
            "feat_ten_years_working": f_ten_years_working,
            "feat_ten_platform_rating": f_ten_platform_rating,
            "feat_ten_trips_completed": f_ten_trips_completed,
            "feat_ten_cancellation_rate": f_ten_cancellation_rate,
            "feat_liq_net_margin": f_liq_net_margin,
            "feat_pay_utility_on_time": f_pay_utility_on_time,
            "feat_pay_max_bill_delay": f_pay_max_bill_delay,
            "feat_pay_repay_reliability": f_pay_repay_reliability,
            "feat_bur_loan_to_income": f_bur_loan_to_income,
            "feat_int_vol_x_recovery": f_int_vol_x_recovery,
            "feat_int_vol_x_buffer": f_int_vol_x_buffer,
            "feat_int_trend_x_dti": f_int_trend_x_dti,
            "feat_int_resilience_idx": f_int_resilience_idx,
        }

    @classmethod
    def map_prediction_to_output(
        cls,
        pred: PredictionResponse,
        app_dict: Dict[str, Any],
    ) -> MLModelOutput:
        """Map PredictionResponse into standard MLModelOutput."""
        # 1. Human-readable key factors list
        key_factors = []
        expl = pred.explanation_factors or {}
        protective = expl.get("key_protective_factors", [])
        risk_factors = expl.get("key_risk_factors", [])

        for factor in protective:
            name = factor.get("factor_name", "Protective Factor")
            borrower_exp = factor.get("borrower_explanation", "")
            key_factors.append(f"{name}: {borrower_exp}" if borrower_exp else name)

        for factor in risk_factors:
            name = factor.get("factor_name", "Risk Factor")
            borrower_exp = factor.get("borrower_explanation", "")
            key_factors.append(f"{name}: {borrower_exp}" if borrower_exp else name)

        if not key_factors:
            if pred.is_insufficient_evidence and pred.missing_or_insufficient_signals:
                key_factors = list(pred.missing_or_insufficient_signals)
            else:
                key_factors = [
                    "Assessment evaluated against frozen alternative credit risk model.",
                    "Repayment consistency and activity evaluated.",
                ]

        # 2. Format SHAP values array for frontend adaptAssessment (@parakh/api)
        shap_items = []
        for factor in protective:
            val = factor.get("attribution_value", -0.15)
            shap_items.append({
                "feature": factor.get("technical_feature", "signal"),
                "displayName": factor.get("factor_name", "Indicator"),
                "value": float(val),
                "contributionValue": float(val),
                "explanation": factor.get("borrower_explanation", ""),
            })
        for factor in risk_factors:
            val = factor.get("attribution_value", 0.15)
            shap_items.append({
                "feature": factor.get("technical_feature", "signal"),
                "displayName": factor.get("factor_name", "Indicator"),
                "value": float(val),
                "contributionValue": float(val),
                "explanation": factor.get("borrower_explanation", ""),
            })

        structured_explanation = {
            "disclaimer": expl.get("disclaimer", ""),
            "key_protective_factors": protective,
            "key_risk_factors": risk_factors,
            "diagnostic_threshold_status": pred.diagnostic_threshold_status,
            "is_insufficient_evidence": pred.is_insufficient_evidence,
            "missing_signals": pred.missing_or_insufficient_signals,
            "shap_values": shap_items,
        }

        # 3. Numeric probabilities and scores
        risk_prob = (
            Decimal(str(round(pred.repayment_risk_probability, 4)))
            if pred.repayment_risk_probability is not None
            else None
        )
        conf = (
            Decimal(str(round(pred.confidence_or_data_sufficiency, 4)))
            if pred.confidence_or_data_sufficiency is not None
            else None
        )
        score = pred.presentation_score  # None if insufficient
        risk_level = RiskLevel(pred.risk_tier)

        # 4. Financial health indicators
        dti = Decimal(str(round(min(20.0, max(0.0, float(app_dict.get("feat_bur_dti_ratio", 0.25)))), 4)))
        utilization = Decimal(str(round(min(1.0, max(0.0, float(app_dict.get("feat_bur_total_dti", 0.40)))), 4)))
        inc_stability = Decimal(str(round(max(0.0, min(1.0, 1.0 - float(app_dict.get("feat_inc_cv_90d", 0.25)))), 4)))
        repay_reliability = Decimal(str(round(min(1.0, max(0.0, float(app_dict.get("feat_pay_repay_reliability", 0.95)))), 4)))

        return MLModelOutput(
            risk_probability=risk_prob,
            confidence=conf,
            credit_score=score,
            risk_level=risk_level,
            key_factors=key_factors[:4],
            explanation=structured_explanation,
            debt_to_income=dti,
            utilization=utilization,
            income_stability=inc_stability,
            repayment_reliability=repay_reliability,
        )
