# Phase 12A — Model Insights Governance Dashboard Truthfulness Update Report

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Branch:** `ml/credit-risk`  
**Role:** Frontend Engineer  
**Date:** September 24, 2026  
**Status:** COMPLETED & VERIFIED  

---

## 1. Problem Identified

In previous phases, the machine learning inference pipeline (Phase 9), backend ML integration (Phase 10B/10C), and frontend assessment UI (Phase 11B/11C) were implemented and verified with the frozen `volatility-aware-risk-model` v1.0.0 (LightGBM + RobustScaler + TreeSHAP).

However, an audit of the Admin Model Insights governance page (`frontend/apps/web/app/admin/model-insights/page.tsx`) revealed legacy placeholder content that directly contradicted the verified operational reality:
1. **Misleading Training Banner:** Displayed *"ML Training Pipeline & Fairlearn Demographic Audit in Progress"* claiming that LightGBM calibration was *"actively being trained"* and that assessments were scored through *"deterministic MockAssessmentEngine"*.
2. **Stale Architecture Card Fallback:** Fallback labels referenced `"MockAssessmentEngine"` and `"Deterministic Engine"`.
3. **Stale Explainability Status:** Labeled SHAP explainability as *"Pending ML Calibration"* and stated that SHAP calculations awaited LightGBM training connection, even though local TreeSHAP explanations were already live and serving feature attributions in assessment views.
4. **Stale / Misleading Fairness Status:** Labeled statutory fairness audits as *"Pending ML Calibration"* and suggested audits would run dynamically upon model training completion, rather than truthfully explaining that fairness evaluation requires a curated protected-group evaluation dataset.
5. **Stale Exported Governance Card:** Exported JSON card (`handleDownloadModelCard`) contained hardcoded statuses of `"PENDING_ML_CALIBRATION"` and fallback to `"PARAKH Assessment Engine"`.
6. **Unsupported Regulatory / Audit Claims:** Footer claimed that *"PARAKH algorithms undergo quarterly third-party algorithmic fairness audits"*, which is an unsupported capability claim for an early prototype.

---

## 2. Root Cause

The root cause was purely hardcoded placeholder copy and initial fallback strings written during initial frontend UI scaffolding before Person 3 delivered the frozen ML model and FastAPI backend integration. While the backend model registry endpoint (`GET /api/v1/model-versions`) was connected to display registered versions, the surrounding static cards, status badges, and explanatory banners had not been refreshed to reflect the operational LightGBM v1.0.0 model.

---

## 3. Strict Boundary Compliance & Invariants

This update strictly adhered to the Phase 12A architectural and governance boundaries:
- **No ML Code Modified:** `src/ml/**` untouched.
- **No Artifact Modified:** `models/artifacts/**` untouched (SHA256 verified).
- **No Synthetic Data Modified:** `data/**` untouched.
- **No Backend Assessment Logic Modified:** `backend/app/assessment/**` untouched.
- **No Database Schema or Alembic Migrations Modified:** PostgreSQL schemas and migrations untouched.
- **No Fabricated Data:** Did NOT invent demographic parity ratios (DPR), equalized odds numbers, or global SHAP rankings.
- **No False Claims:** Did NOT claim regulatory compliance, production readiness, or that Fairlearn audits had passed.

---

## 4. Summary of Changes

### File Modified:
- `frontend/apps/web/app/admin/model-insights/page.tsx`

### Key Implementations:

#### 1. Active Model Selection & Prioritization
Updated `fetchModelData` to prioritize the active production model `volatility-aware-risk-model` v1.0.0 from PostgreSQL registry:
```tsx
const active =
  versions.find((v) => v.is_active && v.model_name === 'volatility-aware-risk-model') ||
  versions.find((v) => v.is_active) ||
  versions[0];
setActiveModel(active);
```

#### 2. Truthful Production Prototype Banner
Replaced the amber *"ML Training Pipeline in Progress"* warning banner with a verified emerald status notification:
- **Title:** `Production Prototype ML Model Active`
- **Body:** Dynamically references `activeModel.model_name` and `activeModel.version` (`volatility-aware-risk-model (v1.0.0)`):
  > *"The active assessment model volatility-aware-risk-model (v1.0.0) is registered and serving live prototype credit assessments. LightGBM inference and local TreeSHAP explanations have been verified through the end-to-end assessment pipeline."*

#### 3. Architecture Card Fallback Neutrality
Updated the architecture card to display the active registered model (`LightGBM + RobustScaler + TreeSHAP` / `volatility-aware-risk-model`) and replaced mock fallbacks with neutral `"Model metadata unavailable"` for scenarios where backend metadata is temporarily unreachable.

#### 4. TreeSHAP Explainability Section
- **Title:** `TreeSHAP Explainability — Active`
- **Status Badge:** `ACTIVE` (mint badge)
- **Description:** *"Local TreeSHAP feature attributions are generated for scored assessments and are displayed in applicant and reviewer assessment views."*
- **Global Feature Importance Aggregation:** Truthfully designated as `Not Persisted` with clear explanation:
  > *"Local TreeSHAP explanations are operational for individual scored assessments. A persisted global feature-importance aggregation is not currently available in the governance registry."*
- Preserved key feature domain clusters evaluated by the model (Cashflow Volatility & Buffer, Platform Continuity & Rating, Multi-Gig Income Resilience, BBPS Utility Payment Cadence).

#### 5. Fairness Audit Section
- **Title:** `Fairness Audit — Evaluation Dataset Required`
- **Status Badge:** `Evaluation data required`
- **Body:** Truthfully states the operational status without claiming audit completion or execution:
  > *"The active LightGBM model is operational, but demographic parity and equalized-odds metrics require a defined protected-group evaluation dataset and computed audit results. Target benchmarks and disparate impact verification will be rendered once an authoritative evaluation dataset is compiled."*
- **Retained Conceptual Framework:** Documented intended evaluation benchmarks (0.80 – 1.25 DPR Four-Fifths Rule target framework), protected attributes (Gender & Geography cohorts), and statutory guidance alignment (DPDP Act & RBI Fair Practice guidance).

#### 6. Exported Model Governance Card (JSON)
Updated `handleDownloadModelCard` payload to output truthful statuses:
- `modelName`: `volatility-aware-risk-model`
- `modelVersion`: `v1.0.0`
- `algorithm`: `LightGBM + RobustScaler + TreeSHAP`
- `status`: `ACTIVE_PROTOTYPE`
- `fairnessAudit.status`: `EVALUATION_DATA_REQUIRED`
- `fairnessAudit.note`: *"Demographic parity and equalized-odds metrics require a defined protected-group evaluation dataset and computed audit results."*
- `explainability.status`: `LOCAL_TREESHAP_ACTIVE`
- `explainability.note`: *"Local TreeSHAP feature attributions are available for scored assessments. Persisted global feature-importance aggregation is not currently available unless sourced from an existing authoritative artifact."*

#### 7. Algorithmic Accountability Footnote
Replaced unsupported third-party quarterly audit claims with a truthful declaration:
> *"PARAKH exposes model lineage and local explainability for assessment transparency. Fairness evaluation requires a defined protected-group evaluation dataset and should be performed before any production lending deployment."*

---

## 5. Verification & Test Results

### 1. Static Anti-Regression Grep Checks
Executed comprehensive grep checks against `frontend/apps/web/app/admin/model-insights/`:
- `ML Training Pipeline & Fairlearn Demographic Audit in Progress` → **0 occurrences (CLEAN)**
- `Pending ML Calibration` → **0 occurrences (CLEAN)**
- `MockAssessmentEngine` → **0 occurrences (CLEAN)**
- `Deterministic Engine` → **0 occurrences (CLEAN)**
- `actively being trained` → **0 occurrences (CLEAN)**
- `once the production assessment model is integrated` → **0 occurrences (CLEAN)**
- `Pending Calibration` → **0 occurrences (CLEAN)**
- `quarterly third-party` → **0 occurrences (CLEAN)**

### 2. Frontend TypeScript Typecheck
Executed in Docker frontend container:
```bash
docker compose exec frontend npx tsc --noEmit -p apps/web/tsconfig.json
```
- **Result:** Exit code 0 (Zero type errors).

### 3. Frontend Unit & Lifecycle Tests
Executed in Docker frontend container:
- `packages/api/test-api-adapters.ts` → **All adapter tests passed (100%)**
- `apps/web/test-phase11-hardening.ts` → **19/19 tests passed (100%)**
- `apps/web/test-reviewer-flow.ts` → **8/8 tests passed (100%)**

### 4. Full Machine Learning Test Suite
Executed in local ML environment:
```bash
pytest tests/ml/ -q
pytest tests/ -q
```
- **`tests/ml/`:** 155 passed in 7.34s (100%)
- **`tests/`:** 273 passed in 8.33s (100%)

### 5. Backend Test Suite
Executed in local environment:
```bash
PATH="$(pwd)/.venv-ml/bin:$PATH" pytest backend/tests/ -q
```
- **Result:** 237 passed, 39 skipped, 36 subtests passed in 42.00s (100%)

### 6. Live Browser Verification via Chromium CDP
Executed automated end-to-end browser inspection using Headless Chromium (Chrome/152.0.7977.82) interacting with live `parakh-frontend` (`http://localhost:3000`), `parakh-backend` (`http://localhost:8000`), and `parakh-postgres`:
- Authenticated as `admin@parakh.com` and injected credentials into browser `localStorage`.
- Navigated to `http://localhost:3000/admin/model-insights`.
- Verified live DOM elements:
  - Banner: `Production Prototype ML Model Active` → **PASS**
  - Model Name: `volatility-aware-risk-model` → **PASS**
  - Model Version: `v1.0.0` → **PASS**
  - Architecture: `LightGBM + RobustScaler + TreeSHAP` → **PASS**
  - TreeSHAP Explainability Badge: `ACTIVE` → **PASS**
  - Global SHAP Aggregation: `Not Persisted` → **PASS**
  - Fairness Audit Badge: `Evaluation data required` → **PASS**
  - Truthful Footnote: **PASS**
  - Negative assertions (no stale phrases): **PASS**
- Full-page screenshot captured to scratch directory.

---

## 6. Documented Limitations

In accordance with strict truthfulness requirements, the following operational realities remain accurately documented in the UI and governance artifacts:
1. **Fairness Audit Evaluation Data:** The active LightGBM model is operational, but demographic parity and equalized-odds audits cannot be finalized without a designated protected-group evaluation dataset.
2. **Global SHAP Aggregation:** Local TreeSHAP attributions are generated per scored assessment, but aggregate global feature-importance rankings are not persisted in the database registry.

---

## 7. Zero Modification Confirmation

It is explicitly confirmed that:
- No machine learning model files (`src/ml/**`) were modified.
- No model artifact files (`models/artifacts/**`) were modified.
- No synthetic datasets (`data/**`) were modified.
- No backend assessment logic or adapters (`backend/app/**`) were modified.
- No database schemas or Alembic migrations (`backend/alembic/**`) were modified.
- Only the frontend governance UI (`frontend/apps/web/app/admin/model-insights/page.tsx`) and this report were changed.
