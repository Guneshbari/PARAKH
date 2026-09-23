# PARAKH ML Inference Contract — Phase 9

**Model:** Volatility-Aware LightGBM (`volatility-aware-risk-model v1.0.0`)  
**Feature Variant:** `VOLATILITY_AWARE` (64 model-ready columns)  
**Frozen Since:** Phase 8 — Final Model Validation & Selection (commit `d1bf704`)

---

## 1. Overview

The inference contract defines the complete input/output specification for the `RiskPredictor` class (`src/ml/inference/predictor.py`).  It is binding for Phase 10 backend integration and any downstream consumer of ML risk scores.

The predictor runs **entirely offline** — no API endpoint, no network calls, no real-time data fetching.

---

## 2. Input Specification

### 2.1 Required Fields

Every call to `RiskPredictor.predict(application_dict)` must supply exactly **46 raw input fields**:

| Group | Count | Fields |
|-------|-------|--------|
| Raw application inputs | 6 | `requested_loan_amount`, `loan_tenure_months`, `years_working`, `average_working_days`, `gig_work_type`, `loan_purpose` |
| Mandatory derived features | 19 | `feat_inc_*`, `feat_trend_*`, `feat_act_*`, `feat_rec_*`, `feat_liq_*`, `feat_bur_*`, `feat_suf_*` |
| Optional derived features | 21 | `feat_inc_mean_90d`, `feat_inc_trimmed_mean`, `feat_inc_iqr_ratio`, `feat_inc_min_max_ratio`, `feat_trend_consec_drops`, `feat_act_max_idle_streak`, `feat_act_weekend_intensity`, `feat_rec_max_drawdown`, `feat_ten_*`, `feat_liq_net_margin`, `feat_pay_*`, `feat_bur_loan_to_income`, `feat_int_*` |

Full field list defined in `src/ml/inference/input_validator.py::REQUIRED_INPUT_COLUMNS`.

### 2.2 Categorical Field Domains

| Field | Allowed Values |
|-------|---------------|
| `gig_work_type` | `DELIVERY`, `RIDE_HAILING`, `LOGISTICS`, `HOME_SERVICES`, `FREELANCE_MICRO`, `OTHER` |
| `loan_purpose` | `VEHICLE_MAINTENANCE`, `WORKING_CAPITAL`, `EQUIPMENT_PURCHASE`, `PERSONAL_EMERGENCY`, `OTHER` |
| `loan_tenure_months` | `6`, `9`, `12` (integer) |

### 2.3 Numeric Bounds

All numeric fields must fall within the bounds specified in `src/ml/data/dataset_validator.py::FEATURE_BOUNDS`.  Key bounds:

| Field | Min | Max |
|-------|-----|-----|
| `requested_loan_amount` | 1,000 | 500,000 |
| `feat_inc_median_90d` | 0 | 500,000 |
| `feat_inc_cv_90d` | 0 | 5.0 |
| `feat_suf_observed_days` | 0 | 90 |
| `feat_suf_payout_count` | 0 | 90 |
| `feat_bur_total_dti` | 0 | 20 |

### 2.4 Forbidden Fields

The following must **never** appear in the input dict:

- **Excluded non-predictors:** `applicant_profile_id`, `application_id`, `cutoff_timestamp`, `cohort_archetype`, `target_default_flag`, `repayment_risk_probability`
- **Prohibited data-minimisation fields:** See `src/ml/constants.py::PROHIBITED_FIELDS` (raw bank statements, GPS coordinates, contacts, etc.)

---

## 3. Data Sufficiency Gate

Before scoring, the predictor evaluates three data sufficiency thresholds:

| Rule | Threshold | On Failure |
|------|-----------|------------|
| `feat_suf_observed_days` | ≥ 30 days | → INSUFFICIENT |
| `feat_suf_payout_count` | ≥ 4 cycles | → INSUFFICIENT |
| `feat_suf_group_count` | ≥ 2 core signal groups | → INSUFFICIENT |

Applications failing any rule receive an `INSUFFICIENT` response with `repayment_risk_probability=null` and `presentation_score=null`.  They are **not** scored by the model.

---

## 4. Output Specification

### 4.1 Response Fields

| Field | Type | Notes |
|-------|------|-------|
| `repayment_risk_probability` | `float \| null` | Default probability in [0, 1]; `null` for INSUFFICIENT |
| `risk_tier` | `str` | `"LOWER"`, `"MODERATE"`, `"HIGHER"`, or `"INSUFFICIENT"` |
| `presentation_score` | `int \| null` | [300, 850] credit-style score; `null` for INSUFFICIENT |
| `is_insufficient_evidence` | `bool` | `True` when application could not be scored |
| `confidence_or_data_sufficiency` | `float` | [0, 1] normalised distance from nearest tier boundary; `0.0` for INSUFFICIENT |
| `missing_or_insufficient_signals` | `list[str]` | Sufficiency failure reasons; empty for scored applications |
| `explanation_factors` | `dict` | Plain-language protective/risk factors + disclaimer |
| `model_name` | `str` | `"volatility-aware-risk-model"` |
| `model_version` | `str` | `"1.0.0"` |
| `feature_variant` | `str` | `"VOLATILITY_AWARE"` |
| `diagnostic_threshold_status` | `str` | Threshold provenance notice |
| `assessed_at` | `str` | ISO 8601 UTC timestamp |

### 4.2 Risk Tier Thresholds (Frozen)

| Tier | Condition |
|------|-----------|
| `LOWER` | `p < 0.20` |
| `MODERATE` | `0.20 ≤ p < 0.45` |
| `HIGHER` | `p ≥ 0.45` |

> [!WARNING]
> These thresholds are **provisional prototype cutoffs only**.  Operational lending thresholds require formal credit policy approval and empirical calibration against real portfolio data.

### 4.3 Presentation Score Formula (Frozen)

```python
score = int(round(300 + (1.0 - probability) * (850 - 300)))
score = max(300, min(850, score))
```

Higher default probability → lower score.  Formula is identical across Phase 5, 6, and 9.

### 4.4 Explanation Factors Structure

```json
{
  "key_protective_factors": [
    {
      "factor_name": "...",
      "technical_feature": "feat_liq_buffer_to_loan",
      "impact_direction": "associated with lower predicted risk",
      "feature_value_display": "2.50",
      "borrower_explanation": "...",
      "underwriting_context": "..."
    }
  ],
  "key_risk_factors": [ ... ],
  "disclaimer": "Notice: These explanations describe empirical statistical associations ..."
}
```

SHAP attributions are computed by `TreeShapExplainer` using the frozen LightGBM model.  If SHAP fails for any individual application, the predictor returns an empty explanation with a fallback disclaimer while keeping the probability and tier intact.

---

## 5. Diagnostic Threshold

The diagnostic threshold is **0.50** (from `FINAL_MODEL.json`).  This is for reference only and is not used in any internal computation.  Risk tiers are determined solely by the provisional thresholds in Section 4.2.

---

## 6. Pipeline Architecture

```
application_dict
       │
       ▼
 InputValidator.validate()              ← contract + type + range + categorical checks
       │
       ▼
 InputValidator.check_data_sufficiency() ← sufficiency gate
       │
  ┌────┴────────────────────────────────────┐
  │ INSUFFICIENT                            │ SUFFICIENT
  ▼                                         ▼
OutputFormatter.format_insufficient()   FeatureEngineer.transform()      ← 9 engineered features
                                              │
                                         preprocessor.transform()         ← scale/impute/encode
                                              │
                                         model.predict_proba()            ← 64-col model input
                                              │
                                         TreeShapExplainer.explain_instance()
                                              │
                                         PlainLanguageExplainer.generate_summary()
                                              │
                                         OutputFormatter.format_scored()
                                              │
                                              ▼
                                       PredictionResponse
```

---

## 7. Preprocessor Initialisation Strategy

The predictor does **not** fit the preprocessor on inference data.  At `RiskPredictor.__init__()`:

1. The canonical Phase 2 dataset is loaded from `data/synthetic/synthetic_credit_applications.parquet`
2. The deterministic 70/15/15 grouped split is applied (seed=42, scored_only=True)
3. `build_model_ready_matrices(train_df=split.train_df, variant=VOLATILITY_AWARE)` is called
4. The returned fitted `CreditRiskPreprocessor` is stored for all subsequent `predict()` calls

This is identical to the preprocessing path used during model training, guaranteeing that fitted medians, scaler parameters, and OHE category lists are consistent with the frozen model.

> [!NOTE]
> A production deployment would serialise the fitted preprocessor to a joblib artifact alongside the model and load it directly, avoiding the dataset dependency at inference time.

---

## 8. Phase 10 Integration Notes

Phase 10 (backend integration) must:

1. Import `from src.ml.inference import RiskPredictor`
2. Instantiate `RiskPredictor()` once at application startup (expensive: loads model + fits preprocessor)
3. Call `predictor.predict(application_dict)` per assessment request
4. Map `PredictionResponse.to_dict()` to the backend `Assessment` schema

The 46 required input fields must be sourced entirely from the backend application record and telemetry summary — no forward-looking or target-derived fields are permitted.

---

## 9. Error Handling

| Error Type | Condition | Consumer Action |
|------------|-----------|-----------------|
| `InputValidationError` | Contract violation in input dict | Return 422 / reject request |
| `FileNotFoundError` | Model artifact or dataset missing | Fatal startup error — do not serve |
| `RuntimeError` | Feature engineering or preprocessing failure | Log + return 500 |
| SHAP exception | Explanation unavailable | Non-fatal — score/tier remain valid; return with empty explanation |
