# Phase 14A Execution Report: Implement Operational Alerts

**Phase:** 14A  
**Title:** Implement Operational Alerts  
**Repository:** `Guneshbari/PARAKH`  
**Branch:** `ml/credit-risk`  
**Target Gap:** P2-01 (Phase 12B Gap Analysis)  
**Status:** Complete & Verified  

---

## 1. P2-01 Gap Definition

In the frozen **Phase 12B Frontend ↔ Backend ↔ ML Gap Analysis** (`docs/PHASE_12B_FRONTEND_BACKEND_ML_GAP_ANALYSIS_REPORT.md`), gap **P2-01** was defined as:
> *"Replace static `mockOperationalAlerts` with dynamic system alerts from the backend. Connect Operational Alerts API / Backend Service: Currently, `/admin/dashboard` imports static mock alerts from `@/data/mock/admin` instead of receiving dynamic system events from the backend."*

### Key Operational Principle
**Alerts are operational signals, not ML predictions.**  
Operational alerts represent system, pipeline, governance, and data sufficiency events requiring human attention or administrative awareness. They are strictly decoupled from standard predictive risk outputs:
- **Never Alert On:** Low credit score alone, high default probability alone, high DTI alone, high utilization alone, income volatility alone, or any ordinary model prediction.
- **Valid Alert Scenarios:**
  1. `INSUFFICIENT_DATA_REVIEW`: Telemetry sparse or refuse-to-score protocol triggered (< 30 days observed, < 4 payouts), diverting case to manual review.
  2. `CONSENT_BLOCKED`: Assessment attempt blocked by missing or revoked DPDP applicant consent.
  3. `ASSESSMENT_FAILURE`: Assessment engine or pipeline exception encountered during evaluation.
  4. `SYSTEM_HEALTH`: Model/preprocessor artifact unavailable or pipeline component monitoring exception.

---

## 2. Existing Architecture Discovered & Root Cause Analysis

### Prior Frontend State
- In `frontend/apps/web/app/admin/dashboard/page.tsx`:
  - Directly imported `mockOperationalAlerts` from `@/data/mock/admin`.
  - Statically mapped over 3 hardcoded mock items (`ALT-901`, `ALT-902`, `ALT-903`) with hardcoded categories (`VOLATILITY_ALERT`, `TELEMETRY_STATUS`, `FAIRNESS_AUDIT`).
  - No connection to backend API or actual application events.
- In `@parakh/types` and `@parakh/api`:
  - No domain types, transport schemas, or client methods existed for operational alerts.

### Prior Backend State
- No `operational_alerts` table existed in the PostgreSQL database.
- No repository, service, or API endpoints existed for managing operational alerts.
- In `backend/app/services/assessment.py`:
  - When refuse-to-score or `ConsentRequiredError` was encountered, exceptions or insufficient assessments were recorded, but no operational alert was dispatched to reviewer/admin dashboards.

### Root Cause
Operational alerts had never been modeled in the backend or exposed via the API client. The frontend dashboard relied entirely on static mock data placeholders to present a populated UI layout during initial prototyping.

---

## 3. Database Changes & Persistence Architecture

A new PostgreSQL table `operational_alerts` was added via Alembic migration `d9e2f3a4b5c6_add_operational_alerts_table.py` (revising head `c8d1e2f3a4b5`):

```sql
CREATE TABLE operational_alerts (
    id UUID NOT NULL, 
    alert_type VARCHAR(50) NOT NULL, 
    severity VARCHAR(20) NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    message TEXT NOT NULL, 
    status VARCHAR(20) DEFAULT 'OPEN' NOT NULL, 
    application_id UUID, 
    assessment_id UUID, 
    metadata JSONB, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE SET NULL, 
    FOREIGN KEY(assessment_id) REFERENCES credit_assessments (id) ON DELETE SET NULL
);
```

### Indexed Columns
- `ix_operational_alerts_alert_type` on `alert_type`
- `ix_operational_alerts_severity` on `severity`
- `ix_operational_alerts_status` on `status`
- `ix_operational_alerts_application_id` on `application_id`
- `ix_operational_alerts_assessment_id` on `assessment_id`
- `ix_operational_alerts_created_at` on `created_at`

### Lifecycle Status Semantics
- `OPEN`: Incident is active and requires administrative or reviewer attention.
- `ACKNOWLEDGED`: Reviewer/admin has reviewed the alert; incident remains under observation.
- `RESOLVED`: Incident is resolved or dismissed; `resolved_at` timestamp is populated.

---

## 4. Backend Service & API Implementation

### 1. Model & Schemas
- `backend/app/models/operational_alert.py`: SQLAlchemy entity `OperationalAlert` and enums `OperationalAlertType`, `OperationalAlertSeverity`, `OperationalAlertStatus`.
- `backend/app/schemas/operational_alert.py`: Pydantic schemas `OperationalAlertCreate`, `OperationalAlertUpdate`, `OperationalAlertResponse`.

### 2. Repository & Service Layer
- `backend/app/repositories/operational_alert.py`: `OperationalAlertRepository` providing `create`, `get_by_id`, `list_alerts`, `find_open_by_type_and_app`, and `update_status`.
- `backend/app/services/operational_alert.py`: `OperationalAlertService` providing:
  - **Deduplication Engine:** When an active (`OPEN` or `ACKNOWLEDGED`) alert exists for the same `(alert_type, application_id)`, the existing alert's message, title, metadata, and timestamp are refreshed rather than creating duplicate spam records.
  - **Metadata Sanitization:** Scrubbing prohibited PII/demographic fields (`password`, `pan`, `aadhaar`, `bank_account`, `raw_transactions`, `coordinates`, `gender`, `caste`, `religion`).
  - **Lifecycle Methods:** `acknowledge_alert(id)` and `resolve_alert(id)`.
  - **Helper Methods:** `create_insufficient_data_alert`, `create_consent_blocked_alert`, `create_assessment_failure_alert`.

### 3. Pipeline Integration
- `backend/app/services/assessment.py`:
  - Automatically emits `INSUFFICIENT_DATA_REVIEW` (`WARNING`) when evaluation triggers refuse-to-score (`RiskLevel.INSUFFICIENT` or `is_insufficient_evidence=True`).
  - Automatically emits `CONSENT_BLOCKED` (`WARNING`) when evaluation is blocked due to missing/revoked DPDP consent.
  - Automatically emits `ASSESSMENT_FAILURE` (`CRITICAL`) when evaluation engine encounters unexpected execution failure.

### 4. API Endpoints
Protected by `require_role(UserRole.REVIEWER, UserRole.ADMIN)`:
- `GET /api/v1/operational-alerts`: List active/historical alerts, with query params `status`, `limit`, and `skip`.
- `GET /api/v1/operational-alerts/{id}`: Fetch single alert by ID.
- `PATCH /api/v1/operational-alerts/{id}/acknowledge`: Mark alert as acknowledged.
- `PATCH /api/v1/operational-alerts/{id}/resolve`: Mark alert as resolved and populate `resolved_at`.

---

## 5. Frontend Integration

### 1. Types & Client
- `frontend/packages/types/index.ts`: Exported `OperationalAlert`, `OperationalAlertType`, `OperationalAlertSeverity`, and `OperationalAlertStatus`.
- `frontend/packages/api/types.ts`: Exported transport models `BackendOperationalAlertResponse`, etc.
- `frontend/packages/api/adapters.ts`: Added `adaptOperationalAlert` contract mapper.
- `frontend/packages/api/index.ts`: Added `getOperationalAlerts`, `getOperationalAlert`, `acknowledgeOperationalAlert`, and `resolveOperationalAlert`.

### 2. Admin Dashboard (`/admin/dashboard`)
- Removed `import { mockOperationalAlerts } from '@/data/mock/admin'`.
- Added dynamic state hooks: `alerts`, `alertsLoading`, `alertsError`.
- In `loadDashboardData`: Fetches active alerts from backend via `api.getOperationalAlerts({ status: 'OPEN' })`.
- Replaced static list rendering with dynamic component:
  - **Loading State:** Animated skeleton placeholder matching card layout.
  - **Error State:** Non-crashing error banner indicating operational alert service status.
  - **Empty State:** Clean normal-status card (*"Operational Status Normal: No active operational alerts or manual-review pipeline exceptions detected."*).
  - **Active Alerts:** Rendered with severity-coded accent borders, badges (`alertType` and `severity`), title, sanitized description, formatted timestamp, **direct application link** (`/admin/applications/${alert.applicationId}`) with `ExternalLink` icon, and an **Acknowledge** action button.

---

## 6. Seed Data Synchronization

- Updated `scripts/seed_demo_data.py`:
  - When seeding applicant `insufficient.new@example.com` (`MANUAL_REVIEW`, `RiskLevel.INSUFFICIENT`), generates an operational alert `INSUFFICIENT_DATA_REVIEW` linked to the application and assessment.
  - Seeds canonical `SYSTEM_HEALTH` alert for telemetry partner ingestion stream monitoring.
  - Cleans up existing demo alerts idempotently when re-running.

---

## 7. Verification & Test Results

### Dedicated Operational Alerts Test Suite (`backend/tests/test_operational_alerts.py`)
17 exhaustive unit and integration tests passing:
1. `test_create_operational_alert_direct`: Direct creation, status, and timestamp verification.
2. `test_deduplication_on_open_alert`: Deduplication preserves single record while refreshing metadata.
3. `test_different_alert_types_or_apps_not_deduplicated`: Distinct incidents create distinct records.
4. `test_status_transitions`: OPEN -> ACKNOWLEDGED -> RESOLVED status lifecycle with `resolved_at`.
5. `test_metadata_sanitization_removes_prohibited_pii`: Confirms PAN, Aadhaar, account numbers, raw transactions, coordinates, and demographic fields are purged.
6. `test_insufficient_data_alert_triggered_during_assessment`: Confirms automated alert creation on refuse-to-score.
7. `test_consent_blocked_alert_triggered_when_consent_missing`: Confirms automated alert on blocked consent.
8. `test_assessment_failure_alert_triggered_on_engine_error`: Confirms automated alert on pipeline exception.
9. `test_standard_scored_assessment_does_not_trigger_operational_alert`: **Decoupling verified**: high risk score does NOT generate operational alert.
10. `test_api_list_alerts_authorized_roles`: Reviewer and Admin receive HTTP 200.
11. `test_api_status_filtering`: Querying `?status=OPEN` excludes resolved alerts.
12. `test_api_acknowledge_and_resolve_endpoints`: Status transitions via PATCH endpoints.
13. `test_api_unauthorized_applicant_rejected`: Applicant receives HTTP 403 Forbidden.
14. `test_api_unauthenticated_rejected`: Unauthenticated request receives HTTP 401 Unauthorized.
15. `test_api_get_by_id`: Single alert retrieval and 404 behavior.
16. `test_empty_state_returns_empty_list`: Empty response handled cleanly without failure.
17. `test_frontend_does_not_import_mock_operational_alerts`: Static assertion that `frontend/apps/web/app/admin/dashboard/page.tsx` has zero imports of `mockOperationalAlerts`.

### Regression Test Suite
All 132 tests in the suite passed cleanly:
- `backend/tests/test_phase13a1_explanation_persistence.py` (TreeSHAP persistence)
- `backend/tests/test_phase13a2_sufficiency_gate.py` (Sufficiency gating)
- `backend/tests/test_phase13a3_telemetry_pipeline.py` (Runtime telemetry feature derivation)
- `tests/ml/test_phase13a4_preprocessor_persistence.py` (Persisted preprocessor artifact)
- `tests/ml/test_phase9_inference.py` (End-to-end inference)
- `backend/tests/test_operational_alerts.py` (Operational alerts)

### TypeScript Compilation & Linting
- Monorepo typecheck passed cleanly: `npm run typecheck --workspaces --if-present`.
- `frontend/apps/web/app/admin/dashboard/page.tsx` compiled with zero TypeScript or ESLint errors.

---

## 8. Frozen ML Artifact Integrity Verification

SHA-256 hashes of all frozen model artifacts were verified before and after Phase 14A execution:

| Artifact | Expected SHA-256 | Verified SHA-256 | Status |
| :--- | :--- | :--- | :--- |
| `models/artifacts/volatility_aware_risk_model.joblib` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | **IDENTICAL** |
| `models/artifacts/FINAL_MODEL.json` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | **IDENTICAL** |
| `models/artifacts/credit_risk_preprocessor.joblib` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | **IDENTICAL** |

Zero machine learning code, model hyperparameters, preprocessor pipelines, or feature definitions were altered.

---

## 9. Remaining P2 / P3 Gaps

Following completion of **P2-01**, the remaining gaps from Phase 12B are:
- **P2-02**: Build Audit Log Viewer UI (`GET /api/v1/audit-logs`)
- **P2-03**: Add `start_date` and `end_date` parameters to `GET /api/v1/analytics/portfolio`
- **P2-04**: Wire DPDP consent preferences persistence
- **P2-05**: Wire applicant profile editing (`PATCH /api/v1/applicants/{id}`)
- **P2-06**: Implement Model Promotion / Activation API
- **P2-07**: Wire offline fairness evaluation runner with backend endpoint
- **P2-08**: Reconcile unused/redundant API client methods in `@parakh/api`
- **P2-09**: Clean up or wire unconsumed backend application routes
- **P2-10**: Implement global SHAP aggregation background job
- **P2-11**: Historical assessment auditing UI (`GET /api/v1/applications/{id}/assessments`)
- **P3-01 through P3-06**: UI polish, review count fallback removal, standardized export schemas, raw SHAP underwriter views.
