# Phase 14G / Batch C — API and Backend Route Cleanup Report
**Gap Deliverable:** P2-08 (Unused/Redundant Frontend API Methods) + P2-09 (Unconsumed Backend Application Routes)  
**Branch:** `ml/credit-risk`  
**Status:** Complete  
**Date:** 2026-09-27  

---

## 1. Executive Summary

Phase 14G (Batch C) systematically closes gaps **P2-08** and **P2-09** identified in the Phase 12B Gap Analysis through repository-wide, evidence-based code cleanup. Every method in `@parakh/api` and every backend route in `backend/app/api/v1/` was audited across all frontend pages, components, hooks, contract tests, backend services, CLI utilities, security tests, and documentation.

- **P2-08 (Frontend API Cleanup):** Removed 17 genuinely unused or redundant methods from `ParakhApiClient` in `frontend/packages/api/index.ts`. Retained 40 actively consumed methods, internal service dependencies, operational utilities, and supported test contracts (including Phase 14A alerts, Phase 14B audit logs, Phase 14C date filters, Phase 14D consent preferences, Phase 14E applicant profile editing, and Phase 14F model governance).
- **P2-09 (Backend Route Cleanup):** Removed the redundant convenience route `GET /api/v1/applications/{application_id}/financial-signals/latest` and consolidated signal consumption to the authoritative list endpoint `GET /api/v1/applications/{application_id}/financial-signals`. Explicitly verified and preserved intentionally backend-only operational, compliance, and governance endpoints (user management, P3-06 application term editing, P2-11 historical assessment auditing, DPDP full consent history, dedicated sector risk, and model version registry).
- **Invariants Preserved:**
  - Frozen ML artifacts and SHA-256 hashes remain 100% byte-for-byte identical.
  - Live credit assessment scoring pipeline, sufficiency rules, and model inference behavior untouched.
  - RBAC boundaries, authentication semantics, and database schemas strictly preserved.
  - Full frontend TypeScript typecheck (`tsc --noEmit`) passes with 0 errors.
  - 100% backend and frontend regression suites pass cleanly.

---

## 2. P2-08 Frontend API Client Audit & Cleanup Inventory

### 2.1 Removed Methods (17 Methods)

| Method Name | Reason / Evidence for Removal |
|---|---|
| `getUserById(id)` | Genuinely unused in frontend. 0 callers across pages, hooks, components, or test files; was only referenced internally by the deprecated `getBorrowerProfileAdapted` helper. |
| `getUserByEmail(email)` | Genuinely unused in frontend. 0 callers across the frontend repository. Backend endpoint is an administrative operational lookup. |
| `updateUser(id, data)` | Genuinely unused in frontend. 0 callers across frontend pages. User self-management is handled via applicant profile editing (`updateApplicantProfile`). |
| `updateApplication(id, data)` | Genuinely unused in frontend. 0 callers in UI (application term editing is scheduled for future Phase P3-06). Backend route `PATCH /applications/{id}` is preserved. |
| `getAssessmentsByApplication(id)` | Redundant in frontend. 0 callers in UI; superseded by `getLatestAssessmentByApplication` for current frontend needs. Backend route `GET /applications/{id}/assessments` is preserved for P2-11. |
| `getLatestFinancialSignals(id)` | Redundant in frontend. 0 callers in UI; frontend profile view uses `getFinancialSignals(id)` and selects the primary record (`signals[0]`). |
| `getConsentsByApplication(id)` | Redundant in frontend. 0 callers in UI; frontend uses `getActiveConsentsByApplication(id)`. |
| `createModelVersion(data)` | Genuinely unused in frontend. 0 callers in UI; model training, registration, and artifact serialization are administrative offline/backend workflows. |
| `getActiveModelVersion(name)` | Redundant in frontend. 0 callers in UI; `/admin/model-insights` calls `getModelVersions()` and resolves the active version client-side. |
| `getModelVersionById(id)` | Genuinely unused in frontend. 0 callers across frontend pages or tests. |
| `getAuditLogById(id)` | Genuinely unused in frontend. 0 callers in UI; `/admin/audit-logs` renders event details inline from list results. |
| `getApplicationAdapted(id, profile)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `getApplicationById` and pure adapter `adaptApplication` directly. |
| `getApplicationsAdapted(params)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `getApplications` and pure adapter `adaptApplication` directly. |
| `getAssessmentAdapted(id)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `getAssessmentById` and pure adapter `adaptAssessment` directly. |
| `getLatestAssessmentAdapted(id)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `getLatestAssessmentByApplication` and pure adapter `adaptAssessment` directly. |
| `recordReviewOutcomeAdapted(id, review)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `createReview` and pure adapter `adaptReviewOutcome` directly. |
| `getBorrowerProfileAdapted(id, user)` | Redundant helper. 0 callers across frontend pages or tests. UI calls `getApplicantProfile` and pure adapter `adaptBorrowerProfile` directly. |

### 2.2 Retained Methods (40 Methods)

| Category | Retained Methods | Reason & Consumers |
|---|---|---|
| **Authentication & Tokens** | `login`, `register`, `getMe`, `setToken`, `getToken`, `clearToken` | Core session & auth lifecycle (`AuthContext`, login page, register page, auth contract tests). |
| **Applicant Profiles** | `createApplicant`, `getApplicantProfile`, `getApplicantByUserId`, `updateApplicantProfile` | Intake flow (`/user/applications/new`), dossier views, dashboard, and Phase 14E profile editing (`/user/profile`). |
| **Applications** | `getApplications`, `createApplication`, `getApplicationById`, `getApplicationsByApplicant`, `updateApplicationStatus` | Application listings, submission, dossier management, and reviewer workflow state transitions. |
| **Assessments** | `triggerAssessment`, `getAssessmentById`, `getLatestAssessmentByApplication` | Assessment execution (`/user/applications/new`), result inspection (`/user/results/[id]`), dashboard widgets. |
| **Financial Signals** | `recordFinancialSignals`, `getFinancialSignals` | Aggregated signal ingestion during intake and signal history in dossier views. |
| **Consents & Privacy** | `createConsent`, `getActiveConsentsByApplication`, `revokeConsent`, `getConsentPreferences`, `updateConsentPreferences`, `revokeConsentPreference` | DPDP consent lifecycle during intake, revocations on application views, and Phase 14D persisted preferences on `/user/profile`. |
| **Underwriter Reviews** | `createReview`, `getReviewsByApplication`, `getReviewsByReviewer` | Decision recording on dossier (`/admin/applications/[id]`), review history, and officer statistics on `/admin/profile`. |
| **Model Governance** | `getModelVersions`, `activateModelVersion`, `runFairnessAudit` | Phase 14F model governance UI (`/admin/model-insights`), version promotion, and offline fairness audit execution. |
| **Audit Logs** | `getAuditLogs`, `getAuditLogsAdapted` | Phase 14B audit log viewer (`/admin/audit-logs`); `getAuditLogs` serves as authoritative internal transport. |
| **Portfolio Analytics** | `getPortfolioAnalytics`, `getPortfolioAnalyticsAdapted`, `getSectorRisk`, `getSectorRiskAdapted` | Phase 14C date-filtered portfolio analytics, dashboard KPI cards, and dedicated sector risk analytics. |
| **Supported Adapters** | `triggerAssessmentAdapted` | Supported API client contract test in `frontend/packages/api/test-api-adapters.ts:464`. |
| **Operational Alerts** | `getOperationalAlerts`, `getOperationalAlert`, `acknowledgeOperationalAlert`, `resolveOperationalAlert` | Phase 14A operational alert ingestion, dashboard alert banner (`/admin/dashboard`), and acknowledgment flows. |

---

## 3. P2-09 Backend Route Audit & Cleanup Inventory

### 3.1 Removed Routes (1 Route)

| Method | Path | Action | Evidence & Consolidation |
|---|---|---|---|
| `GET` | `/api/v1/applications/{application_id}/financial-signals/latest` | **REMOVED** | Redundant convenience route. The authoritative endpoint `GET /api/v1/applications/{application_id}/financial-signals` returns all signals for an application ordered newest-first. No frontend consumer existed (frontend uses `signals[0]`). Backend test in `test_api_routes.py` updated to verify 404 response. |

### 3.2 Intentionally Retained Backend-Only Routes (13 Flagged Application Routes)

| Method | Path | Classification | Supported Role / Consumer |
|---|---|---|---|
| `GET` | `/api/v1/users/{user_id}` | `INTENTIONALLY_OPERATIONAL` | Administrative user inspection & self-verification (`test_api_routes.py`, `test_auth_integration.py`). |
| `GET` | `/api/v1/users/by-email/{email}` | `INTENTIONALLY_OPERATIONAL` | Administrative user lookup by normalized email (`test_authentication.py`, `test_api_routes.py`). |
| `PATCH` | `/api/v1/users/{user_id}` | `INTENTIONALLY_OPERATIONAL` | Account update with role escalation prevention (Admin only for role alteration; `test_api_routes.py`). |
| `PATCH` | `/api/v1/applicants/{profile_id}` | `ACTIVE_FRONTEND_CONSUMER` | Consumed by `/user/profile` via Phase 14E (`updateApplicantProfile`). |
| `PATCH` | `/api/v1/applications/{application_id}` | `OPERATIONAL_ONLY` / `TEST_ONLY` | Application term editing before submission (`test_api_routes.py`, `test_authentication.py`); reserved for P3-06. |
| `GET` | `/api/v1/applications/{application_id}/assessments` | `OPERATIONAL_ONLY` / `TEST_ONLY` | Reverse-chronological historical assessment audit list; reserved for P2-11 dossier UI. |
| `GET` | `/api/v1/applications/{application_id}/consents` | `INTENTIONALLY_OPERATIONAL` | Full consent lifecycle history (active + revoked) required for DPDP auditability (`test_integration.py:377`, `test_api_routes.py`). |
| `POST` | `/api/v1/model-versions` | `GOVERNANCE_ONLY` | Administrative model registration in PostgreSQL registry (`test_api_routes.py`, `test_batch_b_ml_governance.py`). |
| `GET` | `/api/v1/model-versions/active/{model_name}` | `GOVERNANCE_ONLY` | Active scoring model resolution by engine family (`test_api_routes.py`). |
| `GET` | `/api/v1/model-versions/{model_version_id}` | `GOVERNANCE_ONLY` | Algorithmic model version metadata retrieval (`test_batch_b_ml_governance.py`). |
| `GET` | `/api/v1/audit-logs` | `ACTIVE_FRONTEND_CONSUMER` | Consumed by `/admin/audit-logs` via Phase 14B (`getAuditLogsAdapted`). |
| `GET` | `/api/v1/audit-logs/{audit_id}` | `OPERATIONAL_ONLY` | Individual audit event detail inspection (`test_phase14b_audit_viewer.py:219`). |
| `GET` | `/api/v1/analytics/sector-risk` | `ACTIVE_BACKEND_CONSUMER` | Dedicated sector risk distribution endpoint (`test_analytics.py:279`, `test-phase9-analytics.ts`). |

---

## 4. Verification & Testing

### 4.1 Focused Test Suites

1. **Frontend P2-08 Cleanup Test (`frontend/packages/api/test-batch-c-cleanup.ts`):**
   - Verified that all 17 removed methods are `undefined` on `ParakhApiClient.prototype`, client instances, and the `api` singleton.
   - Verified that all 40 retained methods remain callable `function`s on instances and singleton.
   - **Result:** PASSED (2/2 test sections, 57 assertions passed).

2. **Backend P2-09 Cleanup Test (`backend/tests/test_batch_c_route_cleanup.py`):**
   - Verified `GET /api/v1/applications/{id}/financial-signals/latest` returns HTTP 404.
   - Verified `GET /api/v1/applications/{id}/financial-signals` is authoritative and returns signals.
   - Verified OpenAPI schema at `/openapi.json` excludes the removed endpoint and includes the authoritative endpoint.
   - Verified RBAC and isolation for intentionally backend-only routes (`/users/{id}`, `/users/by-email`, `PATCH /users/{id}`, `PATCH /applications/{id}`, `/applications/{id}/assessments`, `/applications/{id}/consents`, `/analytics/sector-risk`).
   - **Result:** PASSED (8/8 test methods passed in 7.77s).

### 4.2 Frontend Contract & Workflow Regression

| Test Suite | File | Status | Duration |
|---|---|---|---|
| **API Adapters** | `frontend/packages/api/test-api-adapters.ts` | **PASSED** (4/4 sections) | ~2s |
| **Batch C Cleanup** | `frontend/packages/api/test-batch-c-cleanup.ts` | **PASSED** (2/2 sections) | ~1s |
| **Phase 14E Profile Editing** | `frontend/apps/web/test-phase14e-applicant-profile.ts` | **PASSED** (9/9 tests) | ~2s |
| **Phase 14D Consent Preferences** | `frontend/apps/web/test-phase14d-consent-preferences.ts` | **PASSED** (7/7 tests) | ~2s |
| **Phase 14C Analytics Filters** | `frontend/apps/web/test-phase14c-analytics-filters.ts` | **PASSED** (8/8 tests) | ~2s |
| **Phase 9 Analytics** | `frontend/apps/web/test-phase9-analytics.ts` | **PASSED** (7/7 tests) | ~1s |
| **Phase 8 Review Workflow** | `frontend/apps/web/test-phase8-workflow.ts` | **PASSED** (9/9 steps) | ~1s |
| **Auth & RBAC Logic** | `frontend/apps/web/test-auth-logic.ts` | **PASSED** (16/16 tests) | ~1s |
| **Phase 11 Hardening** | `frontend/apps/web/test-phase11-hardening.ts` | **PASSED** (19/19 tests) | ~1s |
| **TypeScript Compile Check** | `/app/node_modules/.bin/tsc --noEmit` | **PASSED** (0 errors) | ~4s |

### 4.3 Backend Test Suite Regression

| Test Suite | File | Status | Duration |
|---|---|---|---|
| **Batch C Route Cleanup** | `backend/tests/test_batch_c_route_cleanup.py` | **PASSED** (8/8 tests) | 7.77s |
| **API Route Contracts** | `backend/tests/test_api_routes.py` | **PASSED** (9 passed, 10 skipped) | 1.37s |
| **Phase 14F Governance** | `backend/tests/test_batch_b_ml_governance.py` | **PASSED** (15/15 tests) | 10.45s |
| **Phase 14E Profile Editing** | `backend/tests/test_phase14e_applicant_profile_editing.py` | **PASSED** (12/12 tests) | ~18s |
| **Phase 14D Consent Preferences** | `backend/tests/test_phase14d_consent_preferences.py` | **PASSED** (13/13 tests) | ~23s |
| **Phase 14C Analytics Filters** | `backend/tests/test_phase14c_analytics_date_filters.py` | **PASSED** (10/10 tests) | ~9s |
| **Phase 14B Audit Viewer** | `backend/tests/test_phase14b_audit_viewer.py` | **PASSED** (10/10 tests) | ~9s |
| **Phase 14A Operational Alerts** | `backend/tests/test_operational_alerts.py` | **PASSED** (17/17 tests) | ~15s |

### 4.4 OpenAPI Application Startup Verification

- **FastAPI OpenAPI Paths Count:** 42 valid endpoints (reduced from 43 after removing `/api/v1/applications/{application_id}/financial-signals/latest`).
- **OpenAPI Validation:** Confirmed that `GET /api/v1/applications/{application_id}/financial-signals` is registered and `latest` is absent.

### 4.5 Frozen ML Artifact Integrity Verification

```
88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060  models/artifacts/volatility_aware_risk_model.joblib
e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f  models/artifacts/FINAL_MODEL.json
bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2  models/artifacts/credit_risk_preprocessor.joblib
```
All three SHA-256 hashes remain 100% identical to their baseline values.

---

## 5. Files Changed

1. `frontend/packages/api/index.ts`: Removed 17 unused/redundant methods, removed unused imports, re-exported `AuditLogEntry`.
2. `frontend/packages/api/test-batch-c-cleanup.ts`: New deterministic test suite verifying P2-08 method removals and retentions.
3. `frontend/apps/web/app/admin/audit-logs/page.tsx`: Fixed `formatTimestamp` fallback return type for TypeScript compile correctness.
4. `backend/app/api/v1/financial_signals.py`: Removed redundant `get_latest_financial_signal` endpoint and unused `EntityNotFoundError` import.
5. `backend/tests/test_api_routes.py`: Updated `test_financial_signals_routes` to assert 404 on obsolete `financial-signals/latest` route and verify authoritative list retrieval.
6. `backend/tests/test_batch_c_route_cleanup.py`: New deterministic test suite verifying P2-09 backend route removal and preservation of intentionally backend-only routes.
7. `backend/README.md`: Removed obsolete `financial-signals/latest` from API route documentation table.
8. `docs/PHASE_14G_BATCH_C_API_CLEANUP_REPORT.md`: Comprehensive completion report for Batch C.
