# Backend + ML Integration Contract — Phase 10

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Role:** Person 3 — ML / Model Developer + ML Integration  
**Model Name:** `volatility-aware-risk-model`  
**Model Version:** `1.0.0`  
**Feature Variant:** `VOLATILITY_AWARE` (64 model-ready columns)  
**Status:** FROZEN BINDING CONTRACT  

---

## 1. Overview & Purpose

This contract defines the binding interface between the PARAKH FastAPI backend application and the frozen Phase 9 Machine Learning inference pipeline (`RiskPredictor`). It specifies:
1. The exact format of data transferred from backend domain models into the ML adapter.
2. The invocation protocol for `RiskPredictor`.
3. The translation of `PredictionResponse` into backend domain entities and HTTP responses.
4. Data sufficiency, risk tiering, presentation scoring, explainability, and error handling guarantees.

---

## 2. Architecture & Boundary Overview

```
[FastAPI Request: POST /api/v1/applications/{id}/assess]
                           │
                           ▼
              [AssessmentService.assess_application]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
[Application + ApplicantProfile]  [FinancialSignal records]
             └─────────────┬─────────────┘
                           │
                           ▼
          [AssessmentInput (app/assessment/schemas.py)]
                           │
                           ▼
        [MLModelAdapter (app/assessment/ml_engine.py)]
                           │
      Transforms AssessmentInput -> 46-field flat dict
                           │
                           ▼
    [RiskPredictor.predict (src/ml/inference/predictor.py)]
                           │
             Returns PredictionResponse
                           │
                           ▼
          [MLModelOutput (app/assessment/ml_engine.py)]
                           │
                           ▼
        [AssessmentResult (app/assessment/schemas.py)]
                           │
                           ▼
   [CreditAssessment persisted in PostgreSQL DB via SQLAlchemy]
                           │
                           ▼
[HTTP 201 Response: CreditAssessmentResponse (JSON)]
```

---

## 3. Backend Request Contract (`AssessmentInput`)

When an assessment is requested, `AssessmentService` builds an `AssessmentInput` instance from domain models:

```python
class AssessmentInput(BaseModel):
    application_id: Optional[UUID]
    applicant_profile_id: Optional[UUID]
    
    # Loan terms
    requested_loan_amount: Decimal           # Mandatory, > 0
    loan_tenure_months: Optional[int]        # 6, 9, or 12
    loan_purpose: Optional[str]              # e.g., 'VEHICLE_MAINTENANCE'
    
    # Work profile
    gig_work_type: Optional[str]             # e.g., 'DELIVERY', 'RIDE_HAILING'
    years_working: Optional[Decimal]         # e.g., 3.5
    average_working_days: Optional[int]      # e.g., 22
    
    # Aggregated financial indicators
    average_income: Optional[Decimal]
    median_income: Optional[Decimal]
    income_volatility: Optional[Decimal]
    income_trend: Optional[str]
    active_days: Optional[int]
    payment_regularity: Optional[Decimal]
    cashflow_buffer: Optional[Decimal]
    existing_obligation: Optional[Decimal]
    platform_rating: Optional[Decimal]
    repayment_reliability: Optional[Decimal]
    
    # Extensible derived telemetry features dictionary
    derived_features: Dict[str, Any]
```

---

## 4. ML Adapter Input Contract (Flat 46-Field Dict)

The ML adapter maps `AssessmentInput` into a flat Python dictionary containing all 46 fields required by `InputValidator.validate()`:

```python
{
    # 1. Raw loan and profile inputs (6 fields)
    "requested_loan_amount": float,          # [1000.0, 500000.0]
    "loan_tenure_months": int,               # in {6, 9, 12}
    "years_working": float,                  # [0.0, 50.0]
    "average_working_days": float,           # [0.0, 31.0]
    "gig_work_type": str,                    # in {'DELIVERY', 'RIDE_HAILING', 'LOGISTICS', 'HOME_SERVICES', 'FREELANCE_MICRO', 'OTHER'}
    "loan_purpose": str,                     # in {'VEHICLE_MAINTENANCE', 'WORKING_CAPITAL', 'EQUIPMENT_PURCHASE', 'PERSONAL_EMERGENCY', 'OTHER'}

    # 2. Mandatory Core Derived Features (19 fields)
    "feat_inc_median_90d": float,            # [0.0, 500000.0]
    "feat_inc_p25_90d": float,               # [0.0, 500000.0]
    "feat_inc_cv_90d": float,                # [0.0, 5.0]
    "feat_inc_downside_var": float,          # [0.0, 1.0e10]
    "feat_trend_slope_90d": float,           # [-50000.0, 50000.0]
    "feat_trend_momentum_30_90": float,      # [0.0, 5.0]
    "feat_act_active_days_ratio": float,     # [0.0, 1.0]
    "feat_act_zero_earn_weeks": float,       # [0.0, 13.0]
    "feat_rec_bounceback_ratio": float,      # [0.0, 10.0]
    "feat_rec_days_to_recover": float,       # [0.0, 90.0]
    "feat_liq_buffer_to_loan": float,        # [0.0, 50.0]
    "feat_liq_burn_months": float,           # [0.0, 60.0]
    "feat_bur_dti_ratio": float,             # [0.0, 20.0]
    "feat_bur_installment_dti": float,       # [0.0, 20.0]
    "feat_bur_total_dti": float,             # [0.0, 20.0]
    "feat_suf_observed_days": float,         # [0.0, 90.0]
    "feat_suf_payout_count": float,          # [0.0, 90.0]
    "feat_suf_group_count": float,           # [0.0, 5.0]
    "feat_suf_missing_ratio": float,         # [0.0, 1.0]

    # 3. Optional Derived Features (21 fields)
    "feat_inc_mean_90d": float,              # [0.0, 500000.0]
    "feat_inc_trimmed_mean": float,          # [0.0, 500000.0]
    "feat_inc_iqr_ratio": float,             # [0.0, 10.0]
    "feat_inc_min_max_ratio": float,         # [0.0, 1.0]
    "feat_trend_consec_drops": float,        # [0.0, 13.0]
    "feat_act_max_idle_streak": float,       # [0.0, 90.0]
    "feat_act_weekend_intensity": float,     # [0.0, 1.0]
    "feat_rec_max_drawdown": float,          # [0.0, 1.0]
    "feat_ten_years_working": float,         # [0.0, 50.0]
    "feat_ten_platform_rating": float,       # [1.0, 5.0]
    "feat_ten_trips_completed": float,       # [0.0, 100000.0]
    "feat_ten_cancellation_rate": float,     # [0.0, 1.0]
    "feat_liq_net_margin": float,            # [-2.0, 1.0]
    "feat_pay_utility_on_time": float,       # [0.0, 1.0]
    "feat_pay_max_bill_delay": float,        # [0.0, 180.0]
    "feat_pay_repay_reliability": float,     # [0.0, 1.0]
    "feat_bur_loan_to_income": float,        # [0.0, 10.0]
    "feat_int_vol_x_recovery": float,        # [0.0, 450.0]
    "feat_int_vol_x_buffer": float,          # [0.0, 50.0]
    "feat_int_trend_x_dti": float,           # [-50000.0, 50000.0]
    "feat_int_resilience_idx": float,        # [0.0, 100.0]
}
```

### 4.1 Prohibited Fields Policy
The input payload **MUST NEVER** contain:
- `applicant_profile_id`, `application_id`, `cutoff_timestamp`, `cohort_archetype`, `target_default_flag`, `repayment_risk_probability`
- Any field in `PROHIBITED_FIELDS` (bank account numbers, credentials, raw bank statements, raw UPI logs, UPI VPAs, merchant details, GPS coordinates, contacts).

---

## 5. RiskPredictor Invocation Protocol

```python
# Singleton instantiation at application startup:
from src.ml.inference import RiskPredictor
predictor = RiskPredictor()

# Per assessment request:
prediction_response = predictor.predict(app_dict)
```

- **Thread Safety:** The underlying LightGBM booster and TreeSHAP explainer are thread-safe for read-only inference.
- **Exceptions:**
  - `InputValidationError`: Raised if fields are missing, prohibited, or out of bounds. Maps to `AssessmentInputError` (HTTP 400).
  - `RuntimeError` / `FileNotFoundError`: Raised if pipeline execution fails. Maps to `AssessmentEngineError` (HTTP 500).

---

## 6. ML Output Contract (`PredictionResponse`)

The response returned by `RiskPredictor.predict()` has the following structure:

```python
@dataclass
class PredictionResponse:
    repayment_risk_probability: Optional[float]  # float in [0.0, 1.0], or None if insufficient
    risk_tier: str                               # 'LOWER' | 'MODERATE' | 'HIGHER' | 'INSUFFICIENT'
    presentation_score: Optional[int]            # int in [300, 850], or None if insufficient
    is_insufficient_evidence: bool               # True if data sufficiency rules failed
    confidence_or_data_sufficiency: float        # float in [0.0, 1.0]
    missing_or_insufficient_signals: List[str]   # Specific sufficiency failure messages
    explanation_factors: Dict[str, Any]          # Borrower-facing factors + SHAP summary
    model_name: str                              # 'volatility-aware-risk-model'
    model_version: str                           # '1.0.0'
    feature_variant: str                         # 'VOLATILITY_AWARE'
    diagnostic_threshold_status: str             # Threshold provenance notice
    assessed_at: str                             # ISO 8601 UTC timestamp
```

---

## 7. Translation to Backend Domain Model (`MLModelOutput` & `AssessmentResult`)

The ML adapter translates `PredictionResponse` into `MLModelOutput`:

```python
def map_prediction_to_model_output(pred: PredictionResponse, app_dict: dict) -> MLModelOutput:
    # 1. Flatten key factor strings for backend key_factors list
    key_factor_strings = []
    expl = pred.explanation_factors
    for factor in expl.get("key_protective_factors", []):
        key_factor_strings.append(f"{factor['factor_name']}: {factor['borrower_explanation']}")
    for factor in expl.get("key_risk_factors", []):
        key_factor_strings.append(f"{factor['factor_name']}: {factor['borrower_explanation']}")
        
    if not key_factor_strings:
        key_factor_strings = pred.missing_or_insufficient_signals or ["Assessment completed."]

    # 2. Structure explanation payload for frontend consumption
    structured_explanation = {
        "disclaimer": expl.get("disclaimer", ""),
        "key_protective_factors": expl.get("key_protective_factors", []),
        "key_risk_factors": expl.get("key_risk_factors", []),
        "diagnostic_threshold_status": pred.diagnostic_threshold_status,
        # SHAP values array formatted for frontend @parakh/api adaptAssessment:
        "shap_values": [
            {
                "feature": f["technical_feature"],
                "displayName": f["factor_name"],
                "value": float(f.get("attribution_value", 0.0) if "attribution_value" in f else (-0.1 if "protective" in f.get("impact_direction", "") else 0.1)),
                "explanation": f["borrower_explanation"]
            }
            for f in (expl.get("key_protective_factors", []) + expl.get("key_risk_factors", []))
        ]
    }

    return MLModelOutput(
        risk_probability=Decimal(str(round(pred.repayment_risk_probability, 4))) if pred.repayment_risk_probability is not None else Decimal("0.5000"),
        confidence=Decimal(str(round(pred.confidence_or_data_sufficiency, 4))),
        credit_score=pred.presentation_score,
        risk_level=RiskLevel(pred.risk_tier),
        key_factors=key_factor_strings[:4],
        explanation=structured_explanation,
        debt_to_income=Decimal(str(round(app_dict["feat_bur_dti_ratio"], 4))),
        utilization=Decimal(str(round(min(1.0, app_dict["feat_bur_total_dti"]), 4))),
        income_stability=Decimal(str(round(max(0.0, min(1.0, 1.0 - app_dict["feat_inc_cv_90d"])), 4))),
        repayment_reliability=Decimal(str(round(app_dict["feat_pay_repay_reliability"], 4))),
    )
```

---

## 8. Frozen Risk Tier & Presentation Score Contracts

### 8.1 Risk Tier Mapping
The risk tier is strictly determined by:
- `LOWER`: `probability < 0.20`
- `MODERATE`: `0.20 <= probability < 0.45`
- `HIGHER`: `probability >= 0.45`
- `INSUFFICIENT`: Data sufficiency failure (`is_insufficient_evidence=True`)

### 8.2 Presentation Score Formula
The alternative credit score is strictly mapped as:
$$\text{Score} = \text{clamp}\left(300 + \text{round}\left((1.0 - p) \times 550\right), 300, 850\right)$$
- If $p = 0.0 \rightarrow \text{Score} = 850$
- If $p = 1.0 \rightarrow \text{Score} = 300$
- If $p = \text{None}$ (Insufficient) $\rightarrow \text{Score} = \text{None}$

---

## 9. Data Sufficiency & Cold-Start Gate

The pipeline implements an automated gate prior to model feature engineering. An application is routed to `INSUFFICIENT` if any of the following apply:
1. `feat_suf_observed_days < 30` (Less than 30 days active history).
2. `feat_suf_payout_count < 4` (Fewer than 4 payout cycles).
3. `feat_suf_group_count < 2` (Fewer than 2 core signal groups).

**Contract Behavior on Insufficiency:**
- `repayment_risk_probability`: `None` (persisted as NULL).
- `credit_score`: `None` (persisted as NULL).
- `risk_level`: `RiskLevel.INSUFFICIENT`.
- `confidence`: `0.0`.
- `key_factors`: Explanations listing the missing requirements.

---

## 10. Database Persistence Contract

`AssessmentService.create_assessment()` persists the evaluation into the PostgreSQL `credit_assessments` table:

```sql
INSERT INTO credit_assessments (
    id,
    application_id,
    model_version_id,
    credit_score,
    risk_probability,
    risk_level,
    confidence,
    debt_to_income,
    utilization,
    income_stability,
    repayment_reliability,
    assessment_status,
    assessed_at,
    created_at
) VALUES (
    :id,
    :application_id,
    :model_version_id,
    :credit_score,          -- Nullable int
    :risk_probability,       -- Nullable numeric(5,4)
    :risk_level,             -- 'LOWER' | 'MODERATE' | 'HIGHER' | 'INSUFFICIENT'
    :confidence,             -- Nullable numeric(5,4)
    :debt_to_income,         -- Nullable numeric(6,4)
    :utilization,            -- Nullable numeric(6,4)
    :income_stability,       -- Nullable numeric(5,4)
    :repayment_reliability,  -- Nullable numeric(5,4)
    'COMPLETED',
    NOW(),
    NOW()
);
```

Transient metadata (`_transient_key_factors`, `_transient_explanation`, `_transient_model_name`, `_transient_model_version`) is attached to the Python object for serialization into the immediate `CreditAssessmentResponse`.

---

## 11. Backend API Response Contract (`CreditAssessmentResponse`)

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "application_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "model_version_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "credit_score": 735,
  "score": 735,
  "risk_probability": 0.1250,
  "risk_level": "LOWER",
  "confidence": 0.8850,
  "debt_to_income": 0.2200,
  "utilization": 0.1800,
  "income_stability": 0.8500,
  "repayment_reliability": 0.9600,
  "assessment_status": "COMPLETED",
  "model_name": "volatility-aware-risk-model",
  "model_version": "1.0.0",
  "key_factors": [
    "Liquidity Buffer Coverage: Strong liquid reserve relative to loan amount.",
    "Repayment Consistency: High platform repayment regularity."
  ],
  "explanation": {
    "disclaimer": "Notice: These explanations describe empirical statistical associations...",
    "shap_values": [
      {
        "feature": "feat_liq_buffer_to_loan",
        "displayName": "Liquidity Buffer Coverage",
        "value": -0.312,
        "explanation": "Strong liquid reserve relative to loan amount."
      }
    ]
  },
  "assessed_at": "2026-09-24T00:00:00Z",
  "created_at": "2026-09-24T00:00:00Z"
}
```

---

## 12. Frontend Consumption Contract

The frontend `@parakh/api` adapter (`adaptAssessment`) parses `CreditAssessmentResponse` into `CreditAssessmentResult`:
- `score` -> Displayed in `CreditScoreCard` hero gauge.
- `risk_level` -> Renders color-coded risk badge (`LOWER` = green, `MODERATE` = amber, `HIGHER` = rose, `INSUFFICIENT` = slate).
- `key_factors` -> Categorized into `keyPositiveFactors` and `keyAttentionFactors`.
- `explanation.shap_values` -> Visualized in `FeatureContributionCard`.
- `explanation.disclaimer` -> Displayed in underwriting transparency notice.

---

## 13. Audit & Compliance Contract

Every assessment execution:
1. Emits `AuditAction.ASSESSMENT_EXECUTED` event with `AuditOutcome.SUCCESS` to `audit_logs`.
2. Associates `model_version_id` to provide model traceability.
3. Records no raw banking credentials, GPS coordinates, or unmasked personal data.
