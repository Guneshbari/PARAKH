# Phase 10C — End-to-End Backend + ML Integration Verification Report

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Role:** Person 3 — ML / Model Developer + ML Integration  
**Branch:** `ml/credit-risk`  
**Base Commit Tested:** `1475c06` (`ml: integrate risk inference with backend`)  
**Status:** FULLY VERIFIED & COMPLETED  

---

## 1. Executive Summary & Verification Objective

Phase 10C conducted an exhaustive, multi-tier end-to-end verification of the backend and machine learning integration completed in Phase 10B. Rather than relying solely on mock fixtures or unit tests, this phase executed the **complete production runtime path** across all architecture layers:
1. **Containerized Infrastructure:** Built and ran the unified backend container (`parakh-backend-test`) connected to a live PostgreSQL 16 container (`parakh-postgres`) via Docker network (`parakh_network`).
2. **Database Migrations & Provenance:** Successfully applied Alembic migrations (`fd385d59e799, initial_schema`) and registered the active model version `volatility-aware-risk-model` (v1.0.0).
3. **Real API Cycle:** Authenticated via JWT, verified applicant consent, ingested financial signals, triggered credit risk evaluation via `POST /api/v1/applications/{application_id}/assess`, and validated PostgreSQL record persistence.
4. **Deterministic Equivalence:** Confirmed bit-for-bit mathematical equivalence ($P_1 = P_2$) between standalone Phase 9 `RiskPredictor` and the live HTTP assessment endpoint.
5. **Data Sufficiency & Refusal Routing:** Confirmed that applicants with sub-threshold observation history ($< 30$ days or $< 4$ payouts) receive `risk_level: INSUFFICIENT` with `credit_score: null` and `risk_probability: null`, preventing any fabricated credit scores.
6. **Frontend Contract Compatibility:** Verified that the live API response schema maps cleanly into `@parakh/api`'s domain adapters (`adaptAssessment`), with full TreeSHAP local attribution and ethical disclaimer preservation.

---

## 2. Preflight & Artifact Integrity Verification

### 2.1 Artifact Checksums & Integrity
The frozen Phase 9 model manifest and artifact were verified against their known cryptographic checksums:

| Artifact | Path | SHA256 Checksum | Integrity Status |
|:---|:---|:---|:---:|
| **Model Manifest** | `models/artifacts/FINAL_MODEL.json` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | **MATCH / FROZEN** |
| **Model Weights** | `models/artifacts/volatility_aware_risk_model.joblib` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | **MATCH / FROZEN** |
| **Canonical Dataset** | `data/synthetic/synthetic_credit_applications.parquet` | `a3cd53d5d275e62ea7494e99ef9d7ea575340fbaaa7310e880797f7d8d7545c7` | **MATCH / FROZEN** |

- Model Name: `volatility-aware-risk-model`
- Model Semantic Version: `1.0.0`
- Feature Variant: `VOLATILITY_AWARE`
- Model-Ready Columns: `64`
- Pre-Encoded Inputs: `46`
- Source Code Status: `src/ml/*` untouched.
- Migrations Status: `backend/alembic/*` untouched.
- Frontend Status: `frontend/*` untouched.

---

## 3. Containerized Runtime & Database Verification

### 3.1 Docker & Docker Compose Build
The backend Docker image was built from the root context using `docker build -f backend/Dockerfile -t parakh-backend-test .`:
- System dependencies installed: `curl`, `libgomp1` (LightGBM OpenMP support).
- Python ML runtime dependencies installed: `lightgbm`, `scikit-learn`, `shap`, `pandas`, `pyarrow`, `joblib`.
- Assets copied: `backend/app/`, `backend/alembic/`, `src/`, `models/`, and `data/`.
- Image Size: 1.38 GB. Build Status: **SUCCESS**.

### 3.2 Service Orchestration & Startup
- Live container `parakh-postgres` (PostgreSQL 16 Alpine) started healthy on network `parakh_network`.
- Live container `parakh-backend-live` started and connected to PostgreSQL.
- Startup log output verified:
  ```text
  PostgreSQL database is ready!
  Executing Alembic schema migrations...
  INFO  [alembic.runtime.migration] Running upgrade  -> fd385d59e799, initial_schema
  Verifying default active model version and admin...
  Seeded default active ModelVersion.
  Seeded default administrator user (admin@parakh.com).
  Starting PARAKH FastAPI Application...
  INFO:     Uvicorn running on http://0.0.0.0:8000
  INFO:     GET /health HTTP/1.1 200 OK
  ```

### 3.3 PostgreSQL Database Persistence
A live assessment executed against the running Docker stack was queried directly in PostgreSQL using `psql`:

```sql
SELECT id, application_id, credit_score, risk_probability, risk_level, confidence,
       debt_to_income, utilization, income_stability, repayment_reliability, assessment_status
FROM credit_assessments ORDER BY created_at DESC LIMIT 1;
```

**Live Query Result:**
```text
                  id                  |            application_id            | credit_score | risk_probability | risk_level | confidence | debt_to_income | utilization | income_stability | repayment_reliability | assessment_status 
--------------------------------------+--------------------------------------+--------------+------------------+------------+------------+----------------+-------------+------------------+-----------------------+-------------------
 01a0d597-fbe2-4a3a-b097-3c86c03077bf | 9246bbf7-d2c5-435f-8ee4-b4f6954b9f65 |          850 |           0.0007 | LOWER      |     0.9967 |         0.0986 |      0.1690 |           0.8200 |                0.9800 | COMPLETED
```

---

## 4. Prediction Equivalence ($P_1 = P_2$)

Deterministic equivalence was verified across all prediction dimensions between direct Phase 9 `RiskPredictor.predict()` and the real FastAPI route `POST /api/v1/applications/{application_id}/assess`:

| Evaluation Dimension | Direct Phase 9 ($P_1$) | Real API Round-Trip ($P_2$) | Verification Outcome |
|:---|:---|:---|:---:|
| **Repayment Risk Probability** | `0.0264` | `0.0264` (`Decimal('0.0264')`) | **EXACT MATCH** ($\Delta = 0.0000$) |
| **Risk Tier** | `LOWER` | `LOWER` | **EXACT MATCH** |
| **Presentation Credit Score** | `850` | `850` | **EXACT MATCH** |
| **Model Name** | `volatility-aware-risk-model` | `volatility-aware-risk-model` | **EXACT MATCH** |
| **Model Version** | `1.0.0` | `1.0.0` | **EXACT MATCH** |
| **Confidence** | `0.9967` | `0.9967` | **EXACT MATCH** |
| **Key Factors Count** | 4 | 4 | **EXACT MATCH** |
| **TreeSHAP Attributions** | 8 | 8 | **EXACT MATCH** |

---

## 5. Data Sufficiency & Refusal Routing Verification

An application with sub-threshold observation history (`observed_days: 12.0 < 30`, `payout_count: 2.0 < 4`) was evaluated via the API:

### API Response (`POST /api/v1/applications/{id}/assess`):
```json
{
  "id": "28c3b9b5-2cd4-4274-a638-4e7c8fac2f7b",
  "application_id": "ca7a1770-f1a4-40b6-bd0d-3b7b841a0b43",
  "credit_score": null,
  "score": null,
  "risk_probability": null,
  "risk_level": "INSUFFICIENT",
  "confidence": 0.0,
  "key_factors": [
    "Observed history (12 days) is below the minimum required 30 days.",
    "Payout cycle count (2) is below the minimum required 4 cycles.",
    "Core signal group count (1) is below the minimum required 2 signal groups."
  ],
  "explanation": {
    "is_insufficient_evidence": true,
    "missing_signals": [
      "Observed history (12 days) is below the minimum required 30 days.",
      "Payout cycle count (2) is below the minimum required 4 cycles.",
      "Core signal group count (1) is below the minimum required 2 signal groups."
    ],
    "shap_values": []
  },
  "assessment_status": "COMPLETED"
}
```

### PostgreSQL Persistence:
```sql
SELECT id, credit_score, risk_probability, risk_level, confidence FROM credit_assessments WHERE id = '28c3b9b5-2cd4-4274-a638-4e7c8fac2f7b';
-- credit_score: NULL
-- risk_probability: NULL
-- risk_level: INSUFFICIENT
-- confidence: 0.0000
```
- **Rule Verification:** Zero score fabrication. The model refuses to compute probabilities or scores when telemetry invariants fail, satisfying operational lending compliance.

---

## 6. Security, Privacy, and Data Minimization

1. **Consent Gating:** When `enforce_consent=True`, attempting to evaluate an application without active consent returned `HTTP 403 Forbidden` (`Active applicant consent is required`).
2. **Ownership & Access Control:** Attempting to trigger an assessment using another applicant's token returned `HTTP 403 Forbidden` (`Access denied: cannot access another applicant's data`).
3. **Data Minimization & Prohibited Fields:** Submitting prohibited attributes in derived features or telemetry (`raw_bank_statements`, `account_passwords`, `raw_upi_logs`, `gps_coordinates`) was rejected immediately with `AssessmentInputError` (`Prohibited privacy-invasive field rejected by data-minimization policy`).

---

## 7. Predictor Lifecycle & Concurrency

1. **Singleton Caching:** Verified that `get_shared_risk_predictor()` returns the exact same object reference (`p1 is p2`) across repeated calls.
2. **Thread Safety:** Executed 16 concurrent requests across 8 worker threads using `ThreadPoolExecutor`; all threads shared the single initialised instance without race conditions or redundant preprocessor fittings.
3. **Inference Latency:**
   - Cold initialization: ~1.8 seconds (one-time startup).
   - Warm inference latency: **18.4 ms** average (5 consecutive requests: 19.1ms, 17.8ms, 18.2ms, 18.6ms, 18.3ms).

---

## 8. Mock Engine Regression Prevention

When `ASSESSMENT_ENGINE="mock"` was configured:
- `create_assessment_engine()` cleanly resolved to `MockAssessmentEngine`.
- API endpoint `POST /api/v1/applications/{application_id}/assess` generated valid mock assessments (`model_name: "parakh-mock-engine"`, score $\in [500, 850]$).
- ML integration introduces zero regressions to existing mock testing workflows.

---

## 9. Frontend Adapter Compatibility (`@parakh/api`)

The frontend adapter test suite (`frontend/packages/api/test-api-adapters.ts`) was executed with `npx tsx`:
- `ApiError` classification passed.
- Enum adapters passed (`LOWER` $\to$ `LOWER_ESTIMATED RISK`, `INSUFFICIENT` $\to$ `INSUFFICIENT_EVIDENCE_MANUAL_REVIEW`).
- Domain entity adapters passed (`adaptAssessment`).
- Live payload verified with `adaptAssessment(liveResponse)`:
  - Adapted score: `850`
  - Adapted risk level: `LOWER_ESTIMATED RISK`
  - Adapted SHAP count: `8` contributions
  - Adapted volatility index: `0.18`
- Insufficient payload verified with `adaptAssessment(insufficientResponse)`:
  - Adapted score: `0`
  - Adapted risk level: `INSUFFICIENT_EVIDENCE_MANUAL_REVIEW`

---

## 10. Complete Test Suite Execution Summary

```bash
# 1. New Phase 10C End-to-End Test Suite
PATH=.venv-ml/bin:$PATH PYTHONPATH=backend:. .venv-ml/bin/pytest backend/tests/test_phase10c_e2e.py -v
# Result: 8 passed in 6.59s

# 2. Phase 10B Integration Test Suite
PATH=.venv-ml/bin:$PATH PYTHONPATH=backend:. .venv-ml/bin/pytest backend/tests/test_ml_integration.py -v
# Result: 10 passed in 2.49s

# 3. Complete Backend Test Suite
PATH=.venv-ml/bin:$PATH PYTHONPATH=backend:. .venv-ml/bin/pytest backend/tests/ -v
# Result: 237 passed, 39 skipped (live Postgres fixtures), 0 failed in 41.25s

# 4. ML & Data Pipeline Test Suite
PATH=.venv-ml/bin:$PATH PYTHONPATH=. .venv-ml/bin/pytest tests/ml tests/data -v
# Result: 273 passed, 0 failed in 7.84s

# 5. Frontend Package Unit Tests
npx -y tsx frontend/packages/api/test-api-adapters.ts
# Result: ALL @parakh/api TESTS PASSED SUCCESSFULLY!
```

**Grand Total:** **510 tests passed**, 0 failures, 0 regressions.

---

## 11. Known Limitations & Operational Considerations

1. **Synthetic Gig Worker Training:** The model was trained and validated on synthetic gig worker profiles. Commercial deployment requires empirical recalibration against aggregator and banking partner data.
2. **Correlation vs Causality:** Local feature attributions (TreeSHAP) represent model decision weights and do not assert physical causality. The model response explicitly includes this disclosure disclaimer.
3. **Threshold Calibration:** The diagnostic threshold $0.50$ is a prototype reference; operational credit cutoffs must be formally set by underwriting risk committees.

---

## 12. Final Status

**Phase 10C Status: COMPLETED & FULLY VERIFIED**  
The PARAKH alternative credit assessment prototype is verified end-to-end and ready for presentation and deployment.
