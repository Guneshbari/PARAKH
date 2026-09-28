# Phase 13A-4 Implementation Report: Persist Fitted Preprocessor for Deterministic Inference

**Document Version:** 1.0.0  
**Phase ID:** `13A-4`  
**Gap Closed:** P1-04 (Persist Fitted CreditRiskPreprocessor)  
**Target Repository:** `Guneshbari/PARAKH`  
**Branch:** `ml/credit-risk`  
**Date:** 2026-09-26  
**Status:** COMPLETE & VERIFIED  

---

## 1. P1-04 Problem Statement

In the frozen Phase 12B Gap Analysis (`docs/PHASE_12B_FRONTEND_BACKEND_ML_GAP_ANALYSIS_REPORT.md`), gap **P1-04** was identified:
- The fitted `CreditRiskPreprocessor` instance was not persisted as a dedicated model artifact.
- At runtime inference, `RiskPredictor` reconstructed the preprocessing state dynamically by loading the canonical training dataset Parquet file (`data/synthetic/synthetic_credit_applications.parquet`), performing a grouped 70/15/15 split with `seed=42`, and fitting the continuous `RobustScaler`, categorical `OneHotEncoder`, and feature imputers on the 8,012 scored training rows.
- This created unnecessary architectural coupling between inference and training data availability:
  - Inference could not run in lightweight container environments where training datasets are excluded.
  - Runtime initialization was slower and consumed substantial memory for splitting and fitting.
  - Any accidental deviation in dataset rows or splitting logic risked introducing silent feature scaling or category encoding shifts.

Phase 13A-4 closes gap P1-04 by serializing the exact fitted `CreditRiskPreprocessor` used by the frozen model into `models/artifacts/credit_risk_preprocessor.joblib`, attaching explicit version/metadata guardrails, and updating `RiskPredictor` to load and reuse this persisted artifact directly without runtime refitting or dataset access.

---

## 2. Old Inference Reconstruction Path vs. New Persisted Preprocessor Path

### Before (Reconstruction from Dataset):
```
RiskPredictor.__init__()
  │
  ├── Loads FINAL_MODEL.json
  ├── Loads volatility_aware_risk_model.joblib
  └── Calls _build_fitted_pipeline()
        │
        ├── Reads synthetic_credit_applications.parquet (12,000 rows)
        ├── Runs GroupedDatasetSplitter.split(seed=42, scored_only=False) -> 8,412 rows
        ├── Calls build_model_ready_matrices(train_df, scored_only=True)
        │     ├── FeatureEngineer.fit_transform on 8,412 rows
        │     ├── Filters to 8,012 scored rows
        │     └── CreditRiskPreprocessor.fit on 8,012 rows (fits RobustScaler + OneHotEncoder)
        └── Returns (FeatureEngineer, CreditRiskPreprocessor)
```
*Failure mode when training dataset is absent: `FileNotFoundError` during inference startup.*

### After (Direct Persisted Artifact Loading):
```
RiskPredictor.__init__()
  │
  ├── Loads FINAL_MODEL.json
  ├── Loads volatility_aware_risk_model.joblib
  ├── Loads models/artifacts/credit_risk_preprocessor.joblib directly via joblib
  │     │
  │     ├── Validates file existence (explicit FileNotFoundError on missing file)
  │     ├── Validates artifact type is CreditRiskPreprocessor
  │     ├── Validates is_fitted_ is True
  │     ├── Validates model_version matches "1.0.0"
  │     ├── Validates feature_variant matches "VOLATILITY_AWARE"
  │     └── Validates 64 output feature names match model.feature_names_in_ exactly
  └── Initializes FeatureEngineer(include_engineered_interactions=True)
```
*No dataset read, no splitting, and no refitting occurs during inference initialization or prediction.*

---

## 3. Artifact Details & Integrity Hashes

### 3.1. Persisted Preprocessor Artifact
- **File Path:** `models/artifacts/credit_risk_preprocessor.joblib`
- **Format:** `joblib`
- **File Size:** ~21 KB
- **SHA-256 Hash:** `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2`

### 3.2. Frozen Model & Manifest Hashes (Unchanged)
- **Model Artifact:** `models/artifacts/volatility_aware_risk_model.joblib`  
  SHA-256: `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` (**Unchanged**)
- **Model Manifest:** `models/artifacts/FINAL_MODEL.json`  
  SHA-256: `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` (**Unchanged**)

---

## 4. Preprocessor Metadata & State Specification

The persisted `CreditRiskPreprocessor` instance stores the following fitted attributes:
- `is_fitted_`: `True`
- `model_name_`: `"volatility-aware-risk-model"`
- `model_version_`: `"1.0.0"`
- `feature_variant_`: `"VOLATILITY_AWARE"`
- `training_commit_`: `"2d47a35"`
- `preprocessor_class_`: `"src.ml.data.preprocessing.CreditRiskPreprocessor"`
- `scaler_type`: `"robust"` (`fitted_scaler_` is fitted `RobustScaler`)
- `fitted_encoder_`: Fitted `OneHotEncoder(handle_unknown='ignore', sparse_output=False)`
- `numeric_feature_names_in_`: 53 continuous/numeric predictor columns
- `categorical_feature_names_in_`: `['gig_work_type', 'loan_purpose']`
- `feature_names_in_`: 55 post-engineering input columns
- `feature_names_out_`: 64 output model-ready feature columns (matching `model.feature_names_in_` in exact order)
- `metadata_`: Structured dictionary containing all version, provenance, and configuration attributes.

---

## 5. Artifact Generation Protocol

The artifact was generated via [`scripts/persist_fitted_preprocessor.py`](file:///home/gnx/Projects/PARAKH/scripts/persist_fitted_preprocessor.py) using the exact Phase 6 training protocol:
1. Canonical dataset loaded: `data/synthetic/synthetic_credit_applications.parquet` (12,000 rows).
2. Deterministic grouping by `applicant_profile_id` via `GroupedDatasetSplitter.split(seed=42, scored_only=False)` yielding 8,412 training rows.
3. Feature engineering on all 8,412 rows with `FeatureEngineer(include_engineered_interactions=True)`.
4. Filtered to 8,012 scored training rows (`target_default_flag.notnull()`).
5. Fitted `CreditRiskPreprocessor` on the 8,012 scored rows with `scaler_type='robust'`, `apply_log_transform=True`, `clip_leverage_ratios=True`, and `add_missing_indicators=True`.
6. Attached metadata attributes and serialized to disk with `joblib.dump()`.

---

## 6. Inference Loading & Validation Guardrails

In [`src/ml/inference/predictor.py`](file:///home/gnx/Projects/PARAKH/src/ml/inference/predictor.py), `_load_preprocessor()` enforces rigorous validation:
1. **File Presence**: Raises `FileNotFoundError` if the artifact file is missing. No silent fallback to fitting is permitted.
2. **Deserialization Integrity**: Raises `RuntimeError` if the file is corrupted or cannot be read by joblib.
3. **Type Safety**: Raises `TypeError` if the loaded object is not a `CreditRiskPreprocessor`.
4. **Fitting State**: Raises `RuntimeError` if `is_fitted_` is not `True`.
5. **Version Match**: Raises `ValueError` if `model_version` does not match the model's expected version (`1.0.0`).
6. **Variant Match**: Raises `ValueError` if `feature_variant` does not match `VOLATILITY_AWARE`.
7. **Dimensionality & Order**: Raises `ValueError` if `len(feature_names_out_) != 64` or if output column names do not match `model.feature_names_in_`.

---

## 7. Deterministic Parity Verification Results

A comprehensive audit was performed across representative application fixtures (low risk, medium risk, higher risk):

| Test Aspect | Reconstructed Pipeline | Persisted Preprocessor | Delta / Difference | Result |
|---|---|---|---|---|
| Transformed Feature Matrix | 64 columns | 64 columns | `max abs delta = 0.0000000000` | **BIT-FOR-BIT IDENTICAL** |
| Low-Risk Default Probability | 0.000637 | 0.000637 | `0.000000` | **EXACT MATCH** |
| Low-Risk Credit Score | 850 | 850 | `0` | **EXACT MATCH** |
| Low-Risk Risk Tier | `LOWER` | `LOWER` | None | **EXACT MATCH** |
| High-Risk Default Probability | 0.655906 | 0.655906 | `0.000000` | **EXACT MATCH** |
| High-Risk Credit Score | 300 | 300 | `0` | **EXACT MATCH** |
| High-Risk Risk Tier | `HIGHER` | `HIGHER` | None | **EXACT MATCH** |

---

## 8. Regression Suite Execution Summary

All test suites passed with zero regressions:
1. **Phase 13A-4 Preprocessor Persistence (`tests/ml/test_phase13a4_preprocessor_persistence.py`)**:
   - **14 passed**, 0 failed (100% pass rate).
2. **Phase 9 ML Inference Regression (`tests/ml/test_phase9_inference.py`)**:
   - **54 passed**, 0 failed (100% pass rate).
3. **Phase 13A-3 Telemetry Pipeline (`backend/tests/test_phase13a3_telemetry_pipeline.py`)**:
   - **27 passed**, 0 failed (100% pass rate).
4. **Phase 13A-2 Sufficiency Gate (`backend/tests/test_phase13a2_sufficiency_gate.py`)**:
   - **13 passed**, 0 failed (100% pass rate).
5. **Phase 13A-1 Explanation Persistence (`backend/tests/test_phase13a1_explanation_persistence.py`)**:
   - **7 passed**, 1 skipped (live postgres only), 0 failed.
6. **Synthetic Feature Derivation Tests (`tests/data/test_feature_derivation.py`)**:
   - **14 passed**, 0 failed (100% pass rate).
7. **Combined ML & Backend Phase Suite**:
   - **115 passed**, 1 skipped, 0 failed.
8. **Full Backend Regression Suite (`backend/tests/`)**:
   - **285 passed**, 40 skipped, 36 subtests passed, 0 failed.

---

## 9. Confirmation of Non-Goals & Integrity

- **No Retraining**: LightGBM model was not retrained; hyperparameter configurations were not altered.
- **Artifact Hashes**: `volatility_aware_risk_model.joblib` and `FINAL_MODEL.json` remained byte-for-byte identical.
- **No Feature List Changes**: The 40 derived features, 9 interaction features, and 11 OHE columns remain identical.
- **Sufficiency & Privacy Intact**: Applications with insufficient history or evidence continue to route to `INSUFFICIENT` without invoking the preprocessor or model prediction.
- **TreeSHAP Persistence Intact**: Explanations continue to be generated and persisted durably in `credit_assessments.explanation`.

---

## 10. Remaining Known Gaps

With P1-01, P1-02, P1-03, and P1-04 now closed:
- **P1-05**: Dynamic Model Promotion / Manifest Sync (if designated in subsequent phases).
- System is ready for subsequent roadmap phases.
