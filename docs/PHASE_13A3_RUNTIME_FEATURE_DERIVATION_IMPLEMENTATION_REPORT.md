# Phase 13A-3 Implementation Report: Runtime Telemetry Contract and TelemetryFeaturePipeline

**Document Version:** 1.0.0  
**Phase ID:** `13A-3-IMPL`  
**Gap Closed:** P1-03 (Runtime Raw-Telemetry Feature Derivation)  
**Target Repository:** `Guneshbari/PARAKH`  
**Branch:** `ml/credit-risk`  
**Date:** 2026-09-26  
**Status:** COMPLETE & VERIFIED  

---

## 1. P1-03 Problem Addressed

In the frozen Phase 12B Gap Analysis (`docs/PHASE_12B_FRONTEND_BACKEND_ML_GAP_ANALYSIS_REPORT.md`) and the Phase 13A-3 Analysis (`docs/PHASE_13A3_RUNTIME_FEATURE_DERIVATION_ANALYSIS.md`), gap **P1-03** was identified:
- The ML inference layer (`RiskPredictor` calling `FeatureEngineer`) expects a 64-feature input vector consisting of 6 profile inputs, 19 core derived features, 21 optional derived features, and 18 interaction features.
- At training time, synthetic generation (`src/data/synthetic/feature_derivation.py`) computed these 40 derived features directly from granular daily shifts and weekly settlement payouts.
- At runtime, however, `PassthroughFeaturePipeline` passively forwarded existing values from `signal_metadata`. In the absence of granular telemetry, `MLModelAdapter` relied on static fallback defaults or approximated computations.
- Furthermore, three mathematical train/serve formula discrepancies were confirmed between `src/data/synthetic/feature_derivation.py` and `MLModelAdapter`:
  1. `feat_bur_loan_to_income`: Runtime divided requested loan amount by monthly income instead of annualized median income (`median * 52`).
  2. `feat_int_vol_x_buffer`: Runtime multiplied volatility by buffer (`cv * buffer`), whereas training computed `cv / (buffer + 0.1)`.
  3. `feat_int_trend_x_dti`: Runtime multiplied slope by single DTI (`slope * bur_dti_ratio`), whereas training computed `slope * (1.0 + total_dti)`.

Phase 13A-3-IMPL eliminates this gap by introducing a structured runtime telemetry contract (`telemetry_series`), persisting it in PostgreSQL JSONB, replacing `PassthroughFeaturePipeline` with `TelemetryFeaturePipeline` that reuses the authoritative training feature derivation library, and fixing the three train/serve formula discrepancies.

---

## 2. Before Architecture

```
[Client / API Request]
         │
         ▼
[FinancialSignal] (Only scalar aggregates: average_income, median_income, signal_metadata)
         │
         ▼
[PassthroughFeaturePipeline] (Merged signal_metadata dictionary without derivation)
         │
         ▼
[MLModelAdapter]
         ├── Uses static defaults for missing telemetry features
         ├── Implements 3 skewed mathematical formulas (loan_to_income, vol_x_buffer, trend_x_dti)
         └── Passes 64-feature vector
                  │
                  ▼
         [RiskPredictor / LightGBM]
```

### Limitations of Before Architecture:
1. No schema or database column for granular shift or payout time-series.
2. Runtime features were either fabricated, pre-calculated upstream, or approximated.
3. Train/serve calculation skew on interaction and debt-burden features.
4. Risk of data leakage if timestamps were not strictly checked against an assessment cutoff.

---

## 3. After Architecture

```
[Client / API / Webhook Ingestion]
         │
         ▼
[FinancialSignal]
         ├── Scalar aggregates (for backwards compatibility)
         ├── signal_metadata (JSONB)
         └── telemetry_series (JSONB: WeeklyPayoutRecord[], DailyShiftRecord[])
                  │
                  ▼
[TelemetryFeaturePipeline] (backend/app/assessment/pipeline.py)
         ├── Enforces Anti-Leakage Temporal Cutoff (events >= cutoff_dt strictly excluded)
         ├── Derives 40 ML Features via authoritative src/ml/features/feature_derivation.py
         ├── Computes Data Sufficiency dynamically from event counts & history span
         └── Graceful fallback to signal_metadata for legacy non-telemetry records
                  │
                  ▼
[MLModelAdapter] (backend/app/assessment/ml_model_adapter.py)
         ├── Consumes authoritative derived features from pipeline
         ├── Corrected formulas for feat_bur_loan_to_income, feat_int_vol_x_buffer, feat_int_trend_x_dti
         ├── Preserves Phase 13A-2 Sufficiency Gate (missing telemetry routes to INSUFFICIENT)
         └── Feeds validated 64-feature vector into frozen RiskPredictor
                  │
                  ▼
         [RiskPredictor / LightGBM / TreeSHAP]
                  │
                  ▼
[CreditAssessment] + [credit_assessments.explanation (JSONB TreeSHAP Persistence - Phase 13A-1)]
```

---

## 4. Runtime Telemetry Contract

The telemetry contract is defined as typed Pydantic models in `backend/app/schemas/financial_signal.py`:

### 4.1. WeeklyPayoutRecord
Represents a platform settlement cycle within the observation window:
- `payout_timestamp` (`Union[datetime, str]`): ISO-8601 UTC timestamp of settlement.
- `net_amount` (`Decimal`, `ge=0`): Net payout in INR received by worker.
- `gross_amount` (`Optional[Decimal]`, `ge=0`): Platform earnings before commissions.
- `active_days` (`Optional[int]`, `0 <= x <= 7`): Number of active shift days in payout cycle.
- `payout_id` (`Optional[str]`): Platform unique payout identifier.
- `cycle_index` (`Optional[int]`, `1 <= x <= 52`): Chronological index within horizon.
- `is_settled` (`bool`, default `True`): Confirmation flag.

### 4.2. DailyShiftRecord
Represents daily platform shift activity and engagement:
- `date` (`Union[date, datetime, str]`): Calendar date of activity.
- `hours_worked` (`float`, `0.0 <= x <= 24.0`): Active platform hours on shift.
- `is_active` (`bool`, default `True`): Working shift flag.
- `is_weekend` (`Optional[bool]`): Weekend flag (auto-derived if omitted).
- `gross_earnings` (`Optional[Decimal]`, `ge=0`): Gross earnings for the day.
- `net_earnings` (`Optional[Decimal]`, `ge=0`): Net earnings after platform fees.
- `platform_fee` (`Optional[Decimal]`, `ge=0`): Fee deducted by platform.

### 4.3. TelemetrySeries
Composite container for telemetry ingestion:
- `observed_days` (`Optional[int]`, `0 <= x <= 365`): Observation depth in days.
- `weekly_payouts` (`List[WeeklyPayoutRecord]`): Chronological weekly settlement events.
- `daily_activity` (`List[DailyShiftRecord]`): Chronological daily shift events.
- `active_signal_groups` (`Optional[List[str]]`): Explicit active signal categories.

---

## 5. Database Changes & Migration

1. **Model Addition (`backend/app/models/financial_signal.py`)**:
   Added `telemetry_series` column:
   ```python
   telemetry_series: Mapped[Optional[Dict[str, Any]]] = mapped_column(
       JSON().with_variant(JSONB, "postgresql"),
       nullable=True,
   )
   ```
2. **Alembic Migration (`backend/alembic/versions/c8d1e2f3a4b5_add_telemetry_series_to_financial_signals.py`)**:
   - Revision ID: `c8d1e2f3a4b5`
   - Down Revision: `b7c1e9a24d03`
   - Operation: `op.add_column('financial_signals', sa.Column('telemetry_series', postgresql.JSONB(astext_type=sa.Text()), nullable=True))`
   - Executed against PostgreSQL: `alembic upgrade head` verified.

---

## 6. API Changes & Schemas

- `FinancialSignalBase` and `FinancialSignalCreate` updated to accept `telemetry_series: Optional[Union[TelemetrySeries, Dict[str, Any]]] = None`.
- `FinancialSignalResponse` returns `telemetry_series` when queried.
- Privacy guard: `PROHIBITED_FIELDS` validation recursively rejects protected/demographic attributes (`gender`, `religion`, `caste`, `bank_account_number`, `raw_transactions`, `gps_coordinates`).

---

## 7. TelemetryFeaturePipeline

Implemented in `backend/app/assessment/pipeline.py` (`TelemetryFeaturePipeline(FeaturePipeline)`):
1. **Telemetry Extraction**: Reads `telemetry_series` from domain object or dictionary.
2. **Temporal Guarding**: Resolves cutoff timestamp from `cutoff_timestamp`, `application.created_at`, or `now(UTC)`. Events strictly at or after the cutoff are discarded prior to any feature calculation.
3. **Authoritative Calculation**:
   - Invokes functions from `src.ml.features.feature_derivation`:
     - Income level: `calculate_median_income`, `calculate_p25_income`, `calculate_mean_income`, `calculate_trimmed_mean_income`, `calculate_income_cv`, `calculate_downside_variance`, `calculate_iqr_ratio`, `calculate_min_max_ratio`.
     - Trajectory & Trend: `calculate_trend_slope`, `calculate_trend_momentum`, `calculate_consecutive_drops`.
     - Activity: `calculate_active_days_ratio`, `calculate_max_idle_streak`, `calculate_weekend_intensity`, `calculate_trips_completed`, `calculate_net_margin`, `calculate_zero_earning_weeks`.
     - Recovery: `calculate_recovery_metrics`, `calculate_max_drawdown`.
     - Liquidity & Debt: `calculate_buffer_to_loan`, `calculate_burn_months`, `calculate_dti_ratios`, `calculate_loan_to_income`.
     - Interaction: `calculate_interaction_features`.
4. **Sufficiency Derivation**:
   - `feat_suf_observed_days`: Computed from calendar span between earliest pre-cutoff event and cutoff date.
   - `feat_suf_payout_count`: Count of valid pre-cutoff payout records.
   - `feat_suf_group_count`: Number of distinct alternative signal categories validated.
   - `feat_suf_missing_ratio`: Computed across candidate optional features.
5. **Fallback Path**: When `telemetry_series` is absent, falls back to `_fallback_passthrough` which propagates `signal_metadata` without fabricating sufficiency values (preserving Phase 13A-2 sufficiency gate).

---

## 8. MLModelAdapter Changes

Implemented in `backend/app/assessment/ml_model_adapter.py`:
- Replaced manual, ad-hoc, and static calculations with direct consumption of `derived_features` produced by `TelemetryFeaturePipeline`.
- Updated interaction term fallback calculations to match the authoritative training formulas.
- Set `TelemetryFeaturePipeline` as default pipeline in `AssessmentService`.

---

## 9. Three Formula Discrepancy Corrections

| Feature Name | Training Formula (`feature_derivation.py`) | Old Runtime Skew (`ml_model_adapter.py`) | Corrected Runtime Implementation |
|---|---|---|---|
| `feat_bur_loan_to_income` | `loan / (median * 52)` (annualized income) | `loan / monthly_income` | `calculate_loan_to_income(loan, median)` (loan / (median * 52)) |
| `feat_int_vol_x_buffer` | `cv / (buffer_to_loan + 0.1)` | `cv * buffer_to_loan` | `calculate_interaction_features` (`cv / (buffer + 0.1)`) |
| `feat_int_trend_x_dti` | `slope * (1.0 + total_dti)` | `slope * bur_dti_ratio` | `calculate_interaction_features` (`slope * (1.0 + total_dti)`) |

Additionally, `feat_int_resilience_idx` was verified and aligned with `bounceback / (cv + 0.05)`.

---

## 10. Feature Parity Results

Synthetic 90-day test fixture (13 weekly payouts, 90 daily shifts, 3 active signal groups) was evaluated using both the authoritative training library and `TelemetryFeaturePipeline`:

| Feature Name | Authoritative Value | TelemetryFeaturePipeline Value | Difference | Status |
|---|---|---|---|---|
| `feat_inc_median_90d` | 7100.00 | 7100.00 | 0.0000 | EXACT PARITY |
| `feat_inc_p25_90d` | 6700.00 | 6700.00 | 0.0000 | EXACT PARITY |
| `feat_inc_mean_90d` | 7100.00 | 7100.00 | 0.0000 | EXACT PARITY |
| `feat_inc_cv_90d` | 0.0763 | 0.0763 | 0.0000 | EXACT PARITY |
| `feat_trend_slope_90d` | 2.1978 | 2.1978 | 0.0000 | EXACT PARITY |
| `feat_trend_momentum_30_90` | 1.0188 | 1.0188 | 0.0000 | EXACT PARITY |
| `feat_bur_loan_to_income` | 0.0813 | 0.0813 | 0.0000 | EXACT PARITY |
| `feat_liq_buffer_to_loan` | 0.5000 | 0.5000 | 0.0000 | EXACT PARITY |
| `feat_int_vol_x_buffer` | 0.1272 | 0.1272 | 0.0000 | EXACT PARITY |
| `feat_int_trend_x_dti` | 3.3258 | 3.3258 | 0.0000 | EXACT PARITY |
| `feat_int_resilience_idx` | 6.7725 | 6.7725 | 0.0000 | EXACT PARITY |
| `feat_suf_observed_days` | 90.0 | 90.0 | 0.0 | EXACT PARITY |
| `feat_suf_payout_count` | 13.0 | 13.0 | 0.0 | EXACT PARITY |
| `feat_suf_group_count` | 3.0 | 3.0 | 0.0 | EXACT PARITY |

---

## 11. Temporal Cutoff & Anti-Leakage Protection

The runtime pipeline enforces strict temporal isolation:
- Cutoff timestamp $t_0$ is derived from the application submission time (`application.created_at`).
- For any payout event $e_p$ with timestamp $t(e_p)$, it is admitted if and only if $t(e_p) < t_0$.
- For any daily shift event $e_s$ with date $d(e_s)$, it is admitted if and only if $d(e_s) < \text{date}(t_0)$.
- **Verified via Unit Tests:**
  - Payouts occurring 1 second before cutoff are processed.
  - Payouts occurring exactly at or after cutoff are discarded.
  - 5 future test payouts of INR 50,000 did not alter `feat_inc_median_90d` or `payout_count`.

---

## 12. Sufficiency Gate Integration & Regression

Phase 13A-2 sufficiency enforcement remains 100% intact:
1. **Missing Telemetry (`None`)**: Routes to `INSUFFICIENT`, score is `None`, explanation lists missing observed days, payout count, and signal groups.
2. **Empty Telemetry (`{}`)**: Routes to `INSUFFICIENT`.
3. **Insufficient History (< 30 days)**: Routes to `INSUFFICIENT`.
4. **Insufficient Payouts (< 4 payouts)**: Routes to `INSUFFICIENT`.
5. **Insufficient Groups (< 2 groups)**: Routes to `INSUFFICIENT`.
6. **Sufficient Telemetry (>= 30 days, >= 4 payouts, >= 2 groups)**: Scored normally by LightGBM model, producing calibrated credit score (300-900), risk tier, and TreeSHAP explanation.

---

## 13. Privacy and Security Behavior

- **DPDP Act Compliance**: Demographic attributes (caste, religion, gender) and banking credentials (`bank_account_number`, `raw_transactions`, `gps_coordinates`) remain strictly rejected by `PROHIBITED_FIELDS` scanner.
- **RBAC Ownership**: Tested and verified; unauthorized applicants cannot trigger assessments or read explanation records belonging to another applicant.
- **Consent Check**: Assessments fail if applicant consent is revoked or missing.

---

## 14. Comprehensive Test Results

### Test Suite Execution Summary:
1. **Phase 13A-3 Telemetry Pipeline (`backend/tests/test_phase13a3_telemetry_pipeline.py`)**:
   - **27 passed**, 0 failed (100% pass rate).
2. **Phase 13A-2 Sufficiency Gate (`backend/tests/test_phase13a2_sufficiency_gate.py`)**:
   - **13 passed**, 0 failed (100% pass rate).
3. **Phase 13A-1 Explanation Persistence (`backend/tests/test_phase13a1_explanation_persistence.py`)**:
   - **7 passed**, 1 skipped (live postgres only), 0 failed.
4. **Backend Schema & Service Tests (`backend/tests/test_schemas.py`, `backend/tests/test_services.py`)**:
   - **29 passed**, 1 skipped, 0 failed.
5. **Phase 9 ML Inference Regression (`tests/ml/test_phase9_inference.py`)**:
   - **54 passed**, 0 failed.
6. **Feature Derivation Authoritative Tests (`tests/data/test_feature_derivation.py`)**:
   - **14 passed**, 0 failed.
7. **Full Backend Suite (`backend/tests/`)**:
   - **285 passed**, 40 skipped, 36 subtests passed, 0 failed.

---

## 15. Model Artifact Integrity Verification

Zero modifications were made to ML model binaries, training parameters, or frozen artifacts:
- `models/artifacts/volatility_aware_risk_model.joblib`:
  `sha256: 88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` (UNCHANGED)
- `models/artifacts/FINAL_MODEL.json`:
  `sha256: e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` (UNCHANGED)
- Git diff against `models/artifacts/`: clean, 0 modified files.

---

## 16. Backward Compatibility & Demo System Preservation

- Existing `FinancialSignal` records without `telemetry_series` continue to be queried and processed normally.
- Legacy `signal_metadata` fallback is preserved for existing non-telemetry records.
- Demo accounts (Arjun Verma, Priya Sharma) and existing demo fixtures continue to authenticate and operate without errors.

---

## 17. Known Limitations & Next Steps

1. **Frontend Integration**: The Next.js frontend currently renders aggregate summary signals; future work can optionally wire raw telemetry payload upload or live platform aggregator sync.
2. **Normalized High-Frequency Event Tables**: Current volume is satisfied cleanly by PostgreSQL JSONB column `telemetry_series`. If multi-gigabyte sub-minute telemetry streams are introduced in production, a dedicated TimescaleDB / partitioned PostgreSQL event table can be evaluated.
3. **Next Phase**: Ready to proceed to next scheduled phase according to project roadmap.
