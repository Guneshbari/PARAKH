# Phase 9 — Inference Pipeline Report

**Project:** PARAKH — Credit Score for the Invisible (CX0506)  
**Phase:** 9 — Prediction / Inference Pipeline  
**Role:** Person 3 — ML / Model Developer  
**Branch:** `ml/credit-risk`  
**Commit:** (see git log)  
**Previous Phase Commit:** `d1bf704` (Phase 8 — Final Model Validation & Selection)

---

## 1. Objective

Build a deterministic, production-style ML inference pipeline around the frozen Phase 8 Volatility-Aware LightGBM model so that a single applicant assessment can be transformed into a validated risk prediction and a stable structured output ready for Phase 10 backend integration.

---

## 2. Deliverables

| File | Description |
|------|-------------|
| `src/ml/inference/__init__.py` | Package init — exports `RiskPredictor`, `InputValidator`, `InputValidationError`, `OutputFormatter`, `PredictionResponse` |
| `src/ml/inference/input_validator.py` | Validates raw application dict against frozen data contract |
| `src/ml/inference/output_formatter.py` | Constructs `PredictionResponse` using frozen formulas |
| `src/ml/inference/predictor.py` | `RiskPredictor` — full pipeline orchestrator |
| `tests/ml/test_phase9_inference.py` | 54 tests covering all three inference modules |
| `docs/inference-contract.md` | Phase 10 integration-ready inference contract |
| `docs/PHASE_9_INFERENCE_REPORT.md` | This report |

---

## 3. Pipeline Architecture

```
application_dict (46 fields)
        │
        ▼
  InputValidator.validate()
  ├─ Prohibited field check (PROHIBITED_FIELDS)
  ├─ Excluded non-predictor check (EXCLUDED_NON_PREDICTORS)
  ├─ Required field presence (46 fields)
  ├─ Type checks (numeric / categorical)
  ├─ Range bounds (FEATURE_BOUNDS)
  └─ Categorical domain checks (gig_work_type, loan_purpose, loan_tenure_months)
        │
        ▼
  InputValidator.check_data_sufficiency()
  ├─ feat_suf_observed_days ≥ 30
  ├─ feat_suf_payout_count ≥ 4
  └─ feat_suf_group_count ≥ 2
        │
   ┌────┴─────────────────────────────────────────────────┐
   │ INSUFFICIENT                                         │ SUFFICIENT
   ▼                                                      ▼
OutputFormatter.format_insufficient()         FeatureEngineer.transform()
→ PredictionResponse (INSUFFICIENT)                 (9 feat_eng_* columns added)
                                                          │
                                              CreditRiskPreprocessor.transform()
                                                (training-fitted: scale/impute/OHE)
                                                          │
                                              model.predict_proba(X_64col)
                                                          │
                                              TreeShapExplainer.explain_instance()
                                                          │
                                              PlainLanguageExplainer.generate_summary()
                                                          │
                                              OutputFormatter.format_scored()
                                                          │
                                                          ▼
                                                PredictionResponse (scored)
```

---

## 4. Module Design

### 4.1 `InputValidator`

A stateless class that enforces the frozen Phase 2 data contract on a raw `Dict[str, Any]`.

**`validate(application)` checks:**
1. Prohibited fields (data-minimisation policy) → hard error
2. Excluded non-predictor columns (target, IDs, timestamps) → hard error
3. 46 required field presence → hard error (early exit if missing)
4. Numeric type + finiteness for all numeric inputs
5. Range bounds from `FEATURE_BOUNDS`
6. Categorical domain values for `gig_work_type`, `loan_purpose`, `loan_tenure_months`

All violations are collected before raising a single `InputValidationError` with the full error list.

**`check_data_sufficiency(application)` → `(bool, List[str])`:**
- `feat_suf_observed_days < 30`
- `feat_suf_payout_count < 4`
- `feat_suf_group_count < 2` (frozen from `MIN_REQUIRED_CORE_SIGNAL_GROUPS`)

### 4.2 `OutputFormatter`

Stateless class implementing the frozen output formulas.

**Risk tier mapping** (from `src/ml/constants.py`):

| Probability | Tier |
|-------------|------|
| `p < 0.20` | `LOWER` |
| `0.20 ≤ p < 0.45` | `MODERATE` |
| `p ≥ 0.45` | `HIGHER` |

**Presentation score formula** (frozen from all training scripts + constants):
```python
score = int(round(300 + (1.0 - p) * (850 - 300)))
score = max(300, min(850, score))
```

**Confidence** — normalised distance from the nearest tier boundary, in [0, 1]. Measures how unambiguously the probability falls within its tier.

### 4.3 `RiskPredictor`

Session-level orchestrator. Expensive initialisation is done once:

1. Load `FINAL_MODEL.json` manifest
2. Load `volatility_aware_risk_model.joblib`
3. Deterministically rebuild the fitted preprocessor by re-running the training split (seed=42) on the canonical Phase 2 dataset — identical to the training pipeline
4. Initialise `TreeShapExplainer`

The `predict(application_dict)` method then:
1. Validates input
2. Routes INSUFFICIENT applications
3. Applies `FeatureEngineer.transform()` (never `fit_transform`)
4. Applies `preprocessor.transform()` (never `fit`)
5. Calls `model.predict_proba(X_64col)`
6. Generates SHAP + plain-language explanation
7. Returns `PredictionResponse`

**SHAP failure handling:** If SHAP fails for any individual application, the pipeline returns an empty explanation with a fallback disclaimer. The risk probability and tier remain valid.

---

## 5. Test Results

```
273 passed, 17 warnings in 8.54s
```

**Phase 9 tests: 54 new tests**

| Test Group | Tests | Coverage |
|------------|-------|----------|
| `TestInputValidator` | 19 | Prohibited fields, excluded predictors, missing fields, type errors, range violations, categorical domains, sufficiency rules, boundary conditions |
| `TestOutputFormatter` | 15 | Risk tier parametrised mapping, score formula, score clamping, confidence bounds, scored/insufficient response structure, JSON serialisation |
| `TestRiskPredictor` | 20 | Initialisation, valid prediction, INSUFFICIENT routing, invalid input rejection, determinism, model provenance, JSON serialisation, explanation structure, tier/probability consistency |

**Pre-existing tests: 219** — all continue to pass without modification.

---

## 6. Output Schema (Sample — Scored Application)

```json
{
  "repayment_risk_probability": 0.123456,
  "risk_tier": "LOWER",
  "presentation_score": 731,
  "is_insufficient_evidence": false,
  "confidence_or_data_sufficiency": 0.3827,
  "missing_or_insufficient_signals": [],
  "explanation_factors": {
    "key_protective_factors": [
      {
        "factor_name": "Liquidity Buffer Coverage",
        "technical_feature": "feat_liq_buffer_to_loan",
        "impact_direction": "associated with lower predicted risk",
        "feature_value_display": "2.50",
        "borrower_explanation": "Strong liquid reserve relative to loan amount...",
        "underwriting_context": "The model placed 0.312 log-odds weight on this factor..."
      }
    ],
    "key_risk_factors": [],
    "disclaimer": "Notice: These explanations describe empirical statistical associations..."
  },
  "model_name": "volatility-aware-risk-model",
  "model_version": "1.0.0",
  "feature_variant": "VOLATILITY_AWARE",
  "diagnostic_threshold_status": "Diagnostic threshold 0.50 is used for this prototype assessment...",
  "assessed_at": "2026-09-24T00:00:00+00:00"
}
```

---

## 7. Output Schema (Sample — INSUFFICIENT Application)

```json
{
  "repayment_risk_probability": null,
  "risk_tier": "INSUFFICIENT",
  "presentation_score": null,
  "is_insufficient_evidence": true,
  "confidence_or_data_sufficiency": 0.0,
  "missing_or_insufficient_signals": [
    "Observed history (10 days) is below the minimum required 30 days.",
    "Payout cycle count (2) is below the minimum required 4 cycles."
  ],
  "explanation_factors": {
    "key_protective_factors": [],
    "key_risk_factors": [],
    "disclaimer": "This application could not be scored due to insufficient observation history..."
  },
  "model_name": "volatility-aware-risk-model",
  "model_version": "1.0.0",
  "feature_variant": "VOLATILITY_AWARE",
  "diagnostic_threshold_status": "...",
  "assessed_at": "2026-09-24T00:00:00+00:00"
}
```

---

## 8. Constraints Honoured

| Constraint | Status |
|-----------|--------|
| No model retraining | ✅ Frozen model loaded from joblib artifact |
| No preprocessing fitted on inference data | ✅ Preprocessor fitted on training split only |
| No API endpoint created | ✅ Phase 10 scope |
| Backend/frontend untouched | ✅ |
| Phase 2 canonical dataset unmodified | ✅ |
| All formulas sourced from existing code | ✅ No invented formulas |
| Deterministic pipeline | ✅ Seed=42 preprocessor rebuild produces identical parameters |

---

## 9. Phase 10 Handoff

Phase 10 (backend integration) must:

1. `from src.ml.inference import RiskPredictor`
2. Instantiate once at startup: `predictor = RiskPredictor()`
3. Per request: `response = predictor.predict(application_dict)` → `response.to_dict()`
4. Map `PredictionResponse` fields to the backend `Assessment` schema

Full integration specification: [`docs/inference-contract.md`](inference-contract.md)
