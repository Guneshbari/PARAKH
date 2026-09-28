# Phase 13A-2: MLModelAdapter Sufficiency Gate Enforcement Report

**Status:** Completed & Verified  
**Branch:** `ml/credit-risk`  
**Gap Analysis Reference:** P1-02 (`docs/PHASE_12B_FRONTEND_BACKEND_ML_GAP_ANALYSIS_REPORT.md`)  
**Commit Message:** `fix: enforce ml data sufficiency`  

---

## 1. Executive Summary

Phase 13A-2 implements **P1-02** from the frozen Phase 12B Gap Analysis: preventing missing, empty, or partial telemetry metadata from receiving fabricated sufficient-looking values and bypassing the machine learning data sufficiency gate.

Prior to this fix, `MLModelAdapter.transform_input_to_ml_dict` defaulted missing sufficiency parameters (`feat_suf_observed_days`, `feat_suf_payout_count`, `feat_suf_group_count`, `feat_suf_missing_ratio`) to `90.0`, `12.0`, `4.0`, and `0.0`. These fabricated numbers satisfied the model's data sufficiency rules, allowing applications with zero or incomplete telemetry to be scored rather than routed to `INSUFFICIENT` evidence.

With this update:
- Telemetry sufficiency values are strictly extracted from input metadata without synthetic fallback values.
- Missing values are represented as `None`, which `InputValidator.check_data_sufficiency` explicitly detects and reports as missing telemetry.
- Applications with absent, empty, or incomplete mandatory sufficiency telemetry are deterministically routed to `INSUFFICIENT` (resulting in `credit_score = NULL`, `risk_probability = NULL`, and an un-scored explanation payload).
- Applications with genuinely sufficient telemetry continue to score normally with local TreeSHAP explanations.
- All 258 backend tests and 54 ML inference tests pass with zero regressions.

---

## 2. Sufficiency Contract Discovered in Code

Inspection of `src/ml/inference/input_validator.py` and `src/ml/constants.py` established the exact frozen contract:

| Metric | Field Name | Contract Threshold | Purpose |
|---|---|---|---|
| **Observed History** | `feat_suf_observed_days` (alias: `observed_days`) | $\ge 30.0$ days | Minimum historical telemetry observation window |
| **Payout Frequency** | `feat_suf_payout_count` (alias: `payout_count`) | $\ge 4.0$ cycles | Minimum recurring earnings payout batches |
| **Signal Group Coverage** | `feat_suf_group_count` (alias: `group_count`) | $\ge 2.0$ groups (`MIN_REQUIRED_CORE_SIGNAL_GROUPS`) | Minimum distinct financial telemetry sources |
| **Telemetry Missing Ratio** | `feat_suf_missing_ratio` (alias: `missing_ratio`) | Bounded $[0.0, 1.0]$ | Tracking telemetry completeness |

If any of these conditions fails, the application must be declared `INSUFFICIENT`.

---

## 3. Comparison of Before vs. After Behavior

### 3.1. Before Change
```python
# PREVIOUS CODE in backend/app/assessment/ml_model_adapter.py
observed_days = 90.0
payout_count = 12.0
group_count = 4.0

f_suf_observed_days = float(derived.get("feat_suf_observed_days", observed_days))
f_suf_payout_count = float(derived.get("feat_suf_payout_count", payout_count))
f_suf_group_count = float(derived.get("feat_suf_group_count", group_count))
f_suf_missing_ratio = float(derived.get("feat_suf_missing_ratio", 0.0))
```
**Flaw:** If `signal_metadata` was `None` or `{}`, `f_suf_observed_days` became `90.0`, `f_suf_payout_count` became `12.0`, and `f_suf_group_count` became `4.0`. The sufficiency gate evaluated $90 \ge 30$, $12 \ge 4$, $4 \ge 2$, concluded the data was sufficient, and ran LightGBM inference on an applicant who had provided no telemetry.

### 3.2. After Change
```python
# UPDATED CODE in backend/app/assessment/ml_model_adapter.py
def _extract_suf_metric(primary_key: str, alias_key: str) -> Optional[float]:
    val = derived.get(primary_key)
    if val is None:
        val = derived.get(alias_key)
    if val is None:
        return None
    try:
        f_val = float(val)
        return f_val if not (math.isnan(f_val) or math.isinf(f_val)) else None
    except (ValueError, TypeError):
        return None

f_suf_observed_days = _extract_suf_metric("feat_suf_observed_days", "observed_days")
f_suf_payout_count = _extract_suf_metric("feat_suf_payout_count", "payout_count")
f_suf_group_count = _extract_suf_metric("feat_suf_group_count", "group_count")
f_suf_missing_ratio = _extract_suf_metric("feat_suf_missing_ratio", "missing_ratio")

if f_suf_missing_ratio is None:
    if (
        f_suf_observed_days is not None
        and f_suf_observed_days >= 30.0
        and f_suf_payout_count is not None
        and f_suf_payout_count >= 4.0
        and f_suf_group_count is not None
        and f_suf_group_count >= 2.0
    ):
        f_suf_missing_ratio = 0.0
    else:
        f_suf_missing_ratio = 1.0
```

And in `src/ml/inference/input_validator.py`:
- `InputValidator.validate` allows `None` on the four sufficiency fields so they are not rejected with generic type errors.
- `InputValidator.check_data_sufficiency` explicitly checks for `None`:
  - `observed_days is None` $\rightarrow$ `"Observed history telemetry is missing or unavailable (minimum 30 days required)."`
  - `payout_count is None` $\rightarrow$ `"Payout cycle count telemetry is missing or unavailable (minimum 4 cycles required)."`
  - `group_count is None` $\rightarrow$ `"Core signal group count telemetry is missing or unavailable (minimum 2 signal groups required)."`

---

## 4. Scenario Matrix Verification

| Scenario | Input Condition | Output Risk Tier | Credit Score | Risk Probability | Missing Signals Reported | Model Scored? |
|---|---|---|---|---|---|---|
| **1. Missing Metadata** | `signal_metadata: None` | `INSUFFICIENT` | `NULL` | `NULL` | All 3 missing | **No** (Bypassed) |
| **2. Empty Metadata** | `signal_metadata: {}` | `INSUFFICIENT` | `NULL` | `NULL` | All 3 missing | **No** (Bypassed) |
| **3. Partial (Only Days)** | `observed_days: 90.0` | `INSUFFICIENT` | `NULL` | `NULL` | Payout count & group count missing | **No** (Bypassed) |
| **4. Partial (Only Payouts)**| `payout_count: 12.0` | `INSUFFICIENT` | `NULL` | `NULL` | Observed history & group count missing | **No** (Bypassed) |
| **5. Partial (Only Groups)** | `group_count: 4.0` | `INSUFFICIENT` | `NULL` | `NULL` | Observed history & payout count missing | **No** (Bypassed) |
| **6. Explicit Insufficient**| `14d, 2 payouts, 1 group`| `INSUFFICIENT` | `NULL` | `NULL` | Below-threshold reasons for each | **No** (Bypassed) |
| **7. Explicit Sufficient** | `90d, 12 payouts, 4 groups`| `LOWER`/`MODERATE`/`HIGHER` | `300–850` | `0.0–1.0` | None (`[]`) | **Yes** (LightGBM) |
| **8. Friendly Aliases** | `{"observed_days": 90, ...}`| `LOWER`/`MODERATE`/`HIGHER` | `300–850` | `0.0–1.0` | None (`[]`) | **Yes** (LightGBM) |

---

## 5. Security, Consent, & Data Integrity Verification

1. **DPDP Consent Enforcement**:
   Consent verification occurs in `AssessmentService.assess_application` before engine invocation. Revoked or absent consent rejects requests with HTTP 403 / DPDP violation error without evaluating metadata.
2. **RBAC Ownership**:
   Applicants cannot initiate assessments or view assessments for other users.
3. **Phase 13A-1 TreeSHAP Persistence**:
   - For scored assessments, TreeSHAP explanations and attributions are durably stored in PostgreSQL JSONB.
   - For insufficient assessments, no fabricated SHAP explanations are created (`shap_values = []`), and the refusal reasons are persisted under `missing_signals`.

---

## 6. Test Execution Summary

### 6.1. New Test Suite
- **File:** `backend/tests/test_phase13a2_sufficiency_gate.py`
- **Result:** **13 passed in 9.74s**
  - `test_01_missing_signal_metadata_routes_to_insufficient` ✅
  - `test_02_empty_signal_metadata_routes_to_insufficient` ✅
  - `test_03_partial_metadata_only_observed_days_routes_to_insufficient` ✅
  - `test_04_partial_metadata_only_payout_count_routes_to_insufficient` ✅
  - `test_05_partial_metadata_only_group_count_routes_to_insufficient` ✅
  - `test_06_explicit_insufficient_metadata_routes_to_insufficient` ✅
  - `test_07_explicit_sufficient_metadata_produces_scored_assessment` ✅
  - `test_08_alias_keys_supported_for_sufficiency` ✅
  - `test_09_ml_model_adapter_transform_does_not_fabricate_defaults` ✅
  - `test_10_no_lightgbm_scoring_occurs_for_insufficient_evidence` ✅
  - `test_11_persisted_insufficient_assessment_schema_consistency` ✅
  - `test_12_consent_enforcement_blocks_before_sufficiency_check` ✅
  - `test_13_rbac_unauthorized_user_cannot_assess` ✅

### 6.2. Full Backend Regression
- **Command:** `./.venv-ml/bin/pytest backend/tests/`
- **Result:** **258 passed, 40 skipped in 54.21s** (0 failures).

### 6.3. ML Inference Regression
- **Command:** `./.venv-ml/bin/pytest tests/ml/test_phase9_inference.py`
- **Result:** **54 passed in 1.50s** (0 failures).

---

## 7. Model Artifact Confirmation

- `models/artifacts/volatility_aware_risk_model.joblib`: **UNCHANGED** (SHA256 verified)
- `models/artifacts/FINAL_MODEL.json`: **UNCHANGED**
- No retraining, score calibration, or feature set modifications were performed.
