# Phase 14F: Batch B — ML Governance (P2-06 & P2-07)

**Gaps Closed:** P2-06 (Model Promotion/Activation API) and P2-07 (Offline Fairness Evaluation Execution) from the frozen Phase 12B Gap Analysis  
**Branch:** `ml/credit-risk`  
**Commit Message:** `feat: add model governance and offline fairness evaluation`  
**Previous Phase:** 14E (`31e7f35` — Wire Applicant Profile Editing)

---

## 1. Executive Summary & Gaps Addressed

In Phase 12B, the comprehensive Gap Analysis identified two critical ML governance capabilities that were missing or unexposed at the backend service layer:

1. **P2-06: Model Promotion/Activation API**  
   > *"Model Promotion/Activation API: `is_active` exists on `ModelVersion`, but no endpoint exists to activate/promote a model version or deactivate prior versions."*  
   > — *Phase 12B Gap Analysis Report (Section 9.3, Section 20, Line 541)*

2. **P2-07: Offline Fairness Evaluation Execution**  
   > *"Wire Offline Fairness Evaluation Execution: Integrate `GroupedFairnessAuditor` with a backend service endpoint for demographic parity ratio (DPR) and equalized-odds evaluation."*  
   > — *Phase 12B Gap Analysis Report (Section 9.3, Section 20, Line 542)*

Phase 14F resolves both gaps simultaneously in a single, coherent ML governance phase while strictly preserving the frozen credit-risk model artifacts, live assessment scoring formulas, preprocessing pipelines, and assessment-consent enforcement rules.

---

## 2. Architecture & Design

### 2.1 P2-06: Model Promotion & Version Activation Architecture

```mermaid
flowchart TD
    Req["POST /api/v1/model-versions/{id}/activate"] --> Auth{"Authenticated?"}
    Auth -->|No| R401["HTTP 401 Unauthorized"]
    Auth -->|Yes| Role{"Role == ADMIN?"}
    Role -->|No (APPLICANT / REVIEWER)| R403["HTTP 403 Forbidden"]
    Role -->|Yes| Resolve["Find ModelVersion by ID"]
    Resolve -->|Not Found| R404["HTTP 404 Not Found"]
    Resolve -->|Found| Atomic["Atomic PostgreSQL Transaction"]
    Atomic --> Deact["Deactivate prior active version in same model_name family"]
    Atomic --> Act["Set target ModelVersion is_active = True"]
    Atomic --> Audit["AuditLog: AuditAction.MODEL_VERSION_ACTIVATED"]
    Atomic --> Commit["Commit Transaction"]
    Commit --> Resp["HTTP 200 OK: ModelVersionResponse (is_active=True)"]
```

- **Family-Scoped Uniqueness**: Exactly one active model version is active per model family (`model_name`) at any given time. Activating a candidate version deactivates the prior active version in that family while leaving other model families unaffected.
- **Idempotence**: Promoting an already-active version succeeds idempotently without error and preserves consistency.
- **Strict RBAC**: Restricted exclusively to `ADMIN` users via `require_role(UserRole.ADMIN)`. Unauthenticated requests return `HTTP 401`; `APPLICANT` and `REVIEWER` roles return `HTTP 403`.
- **Audit Logging**: Successful promotions record `AuditAction.MODEL_VERSION_ACTIVATED` in `audit_logs` storing target ID, model name, activated version, and previous active version.
- **Live Scoring Integration**: `AssessmentService` dynamically resolves the active model version (`model_version_repo.get_active()`) during credit assessments, immediately associating new assessments with the promoted version ID.

---

### 2.2 P2-07: Offline Fairness Evaluation Architecture

```mermaid
flowchart TD
    Req["POST /api/v1/model-versions/{id}/fairness-audit"] --> Auth{"Authenticated?"}
    Auth -->|No| R401["HTTP 401 Unauthorized"]
    Auth -->|Yes| Role{"Role in (ADMIN, REVIEWER)?"}
    Role -->|No (APPLICANT)| R403["HTTP 403 Forbidden"]
    Role -->|Yes| Resolve["Find ModelVersion by ID"]
    Resolve -->|Not Found| R404["HTTP 404 Not Found"]
    Resolve -->|Found| InputCheck{"Payload records provided?"}
    InputCheck -->|Empty List| R422["HTTP 422 Unprocessable Entity"]
    InputCheck -->|Custom Records| CustArrays["Extract y_true, y_prob, subgroups"]
    InputCheck -->|None / Omitted| BenchLoad["Load data/synthetic/synthetic_credit_applications.parquet"]
    BenchLoad --> FieldCheck{"subgroup_field in columns?"}
    FieldCheck -->|No| R422F["HTTP 422 Unprocessable Entity"]
    FieldCheck -->|Yes| DropNA["Filter valid records (drop nulls)"]
    DropNA --> BenchArrays["Extract benchmark y_true, y_prob, subgroups"]
    CustArrays --> Auditor["GroupedFairnessAuditor.audit(y_true, y_prob, subgroups)"]
    BenchArrays --> Auditor
    Auditor --> Calc["Compute Demographic Parity Ratio (DPR) & Equal Opportunity Diff (EOD)"]
    Calc --> AuditLog["AuditLog: AuditAction.MODEL_FAIRNESS_EVALUATED"]
    AuditLog --> Resp["HTTP 200 OK: FairnessAuditResponse"]
```

- **Fairness Engine Integration**: Reuses and exposes the core fairness auditor via `GroupedFairnessAuditor` wrapping `audit_subgroup_fairness` in [`src/ml/evaluation/fairness.py`](file:///home/gnx/Projects/PARAKH/src/ml/evaluation/fairness.py).
- **Execution Modes**:
  1. *Benchmark Mode (Default)*: When `records` is omitted or empty body is sent, the auditor loads the offline synthetic benchmark dataset (`data/synthetic/synthetic_credit_applications.parquet`), filtering nulls across the target flag, predicted probability, and selected subgroup operational field.
  2. *Caller-Supplied Mode*: Callers can supply explicit evaluation records (`List[FairnessAuditRecord]`) with ground-truth outcomes, predicted probabilities, and cohort identifiers.
- **Approved Operational Variables**: Supports operational grouping fields (`gig_work_type`, `cohort_archetype`, `loan_purpose`) without inferring or collecting prohibited personal demographic characteristics. Invalid fields return `HTTP 422`.
- **Role Permissions**: Accessible by both `ADMIN` and `REVIEWER` roles via `require_role(UserRole.ADMIN, UserRole.REVIEWER)`. Unauthenticated returns `HTTP 401`; `APPLICANT` returns `HTTP 403`.
- **Regulatory Disclaimers**: Every response includes an explicit statutory disclaimer distinguishing synthetic offline benchmark audits from empirical human population fair-lending testing.

---

## 3. Implementation Summary

### 3.1 ML Evaluation Package (`src/ml/evaluation/`)
- **`GroupedFairnessAuditor`** ([`src/ml/evaluation/fairness.py`](file:///home/gnx/Projects/PARAKH/src/ml/evaluation/fairness.py)): Wrapped `audit_subgroup_fairness` into an object-oriented auditor with `.audit(y_true, y_prob, subgroups, subgroup_field_name, threshold)` method and string-safe subgroup dictionary serialization.
- **Package Exports** ([`src/ml/evaluation/__init__.py`](file:///home/gnx/Projects/PARAKH/src/ml/evaluation/__init__.py)): Exported `GroupedFairnessAuditor` in `__all__`.

### 3.2 Audit & Security Infrastructure (`backend/app/core/`)
- **Audit Action Constant** ([`backend/app/core/audit_events.py`](file:///home/gnx/Projects/PARAKH/backend/app/core/audit_events.py)): Added `MODEL_FAIRNESS_EVALUATED = "MODEL_FAIRNESS_EVALUATED"` under the Model Version audit action group.

### 3.3 Schemas (`backend/app/schemas/`)
- **Fairness Transport Schemas** ([`backend/app/schemas/model_version.py`](file:///home/gnx/Projects/PARAKH/backend/app/schemas/model_version.py)):
  - `FairnessAuditRecord`: Validates binary `y_true` (0 or 1), probability `y_prob` (0.0 to 1.0), and non-empty `subgroup`.
  - `FairnessAuditRequest`: Validates operational `subgroup_field`, `threshold`, and ensures `records` is non-empty when provided.
  - `SubgroupFairnessMetricsResponse`: Per-subgroup counts, empirical default rate, favorable prediction rate, TPR, FPR, and precision.
  - `FairnessAuditResponse`: Model provenance metadata, evaluation timestamp, sample count, subgroup metrics map, DPR, EOD, disclaimers, and audit notes.

### 3.4 Repository Layer (`backend/app/repositories/`)
- **Atomic Activation** ([`backend/app/repositories/model_version.py`](file:///home/gnx/Projects/PARAKH/backend/app/repositories/model_version.py)): Added `activate(model_version, commit=False)` to deactivate other versions in the same `model_name` family and activate the target version within a single database transaction.

### 3.5 Service Layer (`backend/app/services/`)
- **Model Version Service** ([`backend/app/services/model_version.py`](file:///home/gnx/Projects/PARAKH/backend/app/services/model_version.py)):
  - `activate_model_version(model_version_id, actor, auto_commit=True)`: Resolves model version, performs family-scoped deactivation and activation, records `AuditAction.MODEL_VERSION_ACTIVATED`, and commits.
  - `evaluate_fairness(model_version_id, audit_request, actor, auto_commit=True)`: Loads benchmark parquet data or custom records, validates subgroup fields, executes `GroupedFairnessAuditor`, records `AuditAction.MODEL_FAIRNESS_EVALUATED`, and returns `FairnessAuditResponse`.

### 3.6 API Routes (`backend/app/api/v1/`)
- **Promotion & Fairness Routes** ([`backend/app/api/v1/model_versions.py`](file:///home/gnx/Projects/PARAKH/backend/app/api/v1/model_versions.py)):
  - `POST /api/v1/model-versions/{model_version_id}/activate`: Admin-only promotion route returning updated `ModelVersionResponse`.
  - `POST /api/v1/model-versions/{model_version_id}/fairness-audit`: Admin & Reviewer offline fairness audit execution route returning `FairnessAuditResponse`. (Also aliased at `POST /api/v1/model-versions/{model_version_id}/fairness`).

### 3.7 Frontend Integration (`@parakh/api` & Web App)
- **API Client Types & Methods** ([`frontend/packages/api/types.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/types.ts), [`frontend/packages/api/index.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/index.ts)):
  - Defined `BackendFairnessAuditRecord`, `BackendFairnessAuditRequest`, `BackendSubgroupFairnessMetrics`, and `BackendFairnessAuditResponse`.
  - Added `api.activateModelVersion(id)` and `api.runFairnessAudit(id, data)` methods to `ParakhApiClient`.
- **Model Insights Page** ([`frontend/apps/web/app/admin/model-insights/page.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/model-insights/page.tsx)):
  - Added interactive "Activate" button for archived/candidate model versions, enabling administrators to promote versions in PostgreSQL directly with immediate UI state refresh.
  - Added "Run Subgroup Audit" button in the fairness section to execute real backend audits and display live DPR, EOD, sample count, and disclaimer metadata.

---

## 4. Verification & Testing Evidence

### 4.1 Batch B Focused Test Suite
A dedicated verification test suite was executed via `pytest backend/tests/test_batch_b_ml_governance.py`:

```
backend/tests/test_batch_b_ml_governance.py ...............              [100%]
======================= 15 passed, 2 warnings in 10.51s ========================
```

The suite deterministically verifies:
1. `test_p2_06_admin_can_activate_model_version`: Admin successfully activates candidate version v1.1.0.
2. `test_p2_06_activation_deactivates_prior_active_in_same_family`: Activating v1.1.0 deactivates v1.0.0; exactly one version remains active in `volatility-aware-risk-model`; other model families remain unaffected.
3. `test_p2_06_activation_is_idempotent`: Multiple activation calls preserve active state without error.
4. `test_p2_06_activation_rbac_protection`: Unauthenticated requests yield 401; Applicant and Reviewer calls yield 403.
5. `test_p2_06_activation_nonexistent_model_returns_404`: Nonexistent ID returns 404.
6. `test_p2_06_activation_records_audit_log`: `AuditAction.MODEL_VERSION_ACTIVATED` is logged with provenance metadata.
7. `test_p2_07_grouped_fairness_auditor_standalone_accuracy`: `GroupedFairnessAuditor` accurately computes DPR and EOD.
8. `test_p2_07_admin_and_reviewer_can_run_fairness_with_custom_records`: Both roles can execute audits on custom record arrays.
9. `test_p2_07_fairness_audit_with_benchmark_dataset`: Evaluates against `synthetic_credit_applications.parquet` (11,407 samples, DPR ~0.9403, EOD ~0.1333).
10. `test_p2_07_fairness_audit_alternative_operational_subgroups`: Evaluates across `cohort_archetype` and `loan_purpose`.
11. `test_p2_07_fairness_audit_rbac_protection`: Unauthenticated yields 401; Applicant yields 403.
12. `test_p2_07_fairness_audit_validation_errors`: Invalid subgroup field returns 422; empty records returns 422; nonexistent ID returns 404.
13. `test_p2_07_fairness_audit_records_audit_log`: `AuditAction.MODEL_FAIRNESS_EVALUATED` is persisted in `audit_logs`.
14. `test_live_scoring_links_active_model_version`: Live assessments link to active model version ID; model promotion updates the linked version ID for subsequent assessments.
15. `test_frozen_ml_artifacts_hash_verification`: SHA-256 hashes of all frozen model artifacts match baselines.

### 4.2 Full Regression Suite
Full regression across Phases 14E, 14D, 14C, and the ML fairness modules was executed:

```
backend/tests/test_phase14e_applicant_profile_editing.py ............    [ 29%]
backend/tests/test_phase14d_consent_preferences.py .............         [ 60%]
backend/tests/test_phase14c_analytics_date_filters.py ..........         [ 85%]
tests/ml/test_fairness.py ..                                             [ 90%]
tests/ml/test_phase7_fairness.py ....                                    [100%]
======================= 41 passed, 5 warnings in 57.96s ========================
```

### 4.3 Frontend TypeScript Verification
Type-checking completed with zero errors inside the container:
```bash
docker exec -w /app/apps/web parakh-frontend /app/node_modules/.bin/tsc --noEmit
# Exit code: 0
```

### 4.4 Frozen Model Integrity Verification
SHA-256 hashes of all frozen ML artifacts were verified byte-for-byte:

| Artifact Path | Expected Hash | Verified Hash | Status |
| :--- | :--- | :--- | :--- |
| `models/artifacts/volatility_aware_risk_model.joblib` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | Identical |
| `models/artifacts/FINAL_MODEL.json` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | Identical |
| `models/artifacts/credit_risk_preprocessor.joblib` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | Identical |

---

## 5. Conclusion & Gap Status

With Phase 14F completed:
- **P2-06 (Model Promotion/Activation API)** is **CLOSED**.
- **P2-07 (Offline Fairness Evaluation Execution)** is **CLOSED**.
- Live assessment scoring and frozen ML artifacts remain completely untouched.
