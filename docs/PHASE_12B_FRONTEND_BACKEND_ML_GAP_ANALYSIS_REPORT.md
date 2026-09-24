# Phase 12B — Frontend ↔ Backend ↔ ML Comprehensive Gap Analysis Report

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Branch:** `ml/credit-risk`  
**Role:** System Architecture & Integration Gap Analyst  
**Date:** September 24, 2026  
**Status:** COMPLETED (ANALYSIS ONLY)  

---

## 1. Executive Summary

This report delivers a comprehensive, evidence-based cross-layer gap analysis across the **Frontend** (Next.js 16 / React 19), **Backend** (FastAPI / SQLAlchemy / PostgreSQL 16), and **Machine Learning** (`src/ml` / LightGBM v1.0.0 / TreeSHAP) layers of the PARAKH alternative credit assessment platform.

### Core Findings:
1. **The Verified Core Path Works:** As verified in Phase 11C, the vertical path for applicant authentication, application creation, financial signal ingestion, ML assessment triggering, LightGBM volatility-aware scoring, and human reviewer decisioning is operational end-to-end.
2. **Explainability Persistence Gap (Critical P1):** While the ML inference pipeline generates rich local TreeSHAP explanations (8 driving factors, impact directions, plain-language summaries), the backend PostgreSQL database schema (`CreditAssessment` in [`backend/app/models/assessment.py`](file:///home/gnx/Projects/PARAKH/backend/app/models/assessment.py#L35-L129)) **does not possess columns for explanations, key factors, or SHAP values**. Explanations exist only as transient Python memory attributes attached during the initial `POST /assess` response. The frontend relies on a client-side `sessionStorage` caching workaround ([`frontend/packages/api/index.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/index.ts#L370-L374)); upon session loss or device change, subsequent `GET` requests return a degraded 3-key stub (`score`, `risk_level`, `confidence`), completely losing TreeSHAP attributions.
3. **Feature Engineering Decoupling (Critical P1):** The backend assessment pipeline uses [`PassthroughFeaturePipeline`](file:///home/gnx/Projects/PARAKH/backend/app/assessment/pipeline.py#L41-L69), which only extracts pre-existing metadata. The comprehensive 984-line feature engineering pipeline in [`src/ml/features/feature_engineering.py`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py) is not wired to raw banking/UPI transaction records at runtime. Missing features are substituted by default fallbacks in [`MLModelAdapter`](file:///home/gnx/Projects/PARAKH/backend/app/assessment/ml_model_adapter.py#L234-L284). These fallbacks inadvertently default sufficiency metrics to 90 days, 12 payouts, and 4 signal groups, causing applications lacking explicit metadata to automatically pass data sufficiency gates.
4. **Substantial Unconsumed Surface Area:**
   - **Frontend API Client:** 23 out of 47 methods in [`@parakh/api`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/index.ts) have zero callers in the UI.
   - **Backend API:** 18 out of 42 endpoints have no frontend consumer (including all audit logging endpoints, model version registration, applicant profile updates, and raw signal queries).
   - **Mock & Stale Remnants:** While `/admin/model-insights` was cleaned in Phase 12A, [`/admin/dashboard`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/dashboard/page.tsx#L49-L50) still imports static `mockOperationalAlerts`, and both [`/admin/dashboard`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/dashboard/page.tsx#L617) and [`/admin/analytics`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/analytics/page.tsx#L312) contain stale placeholder text referencing upcoming ML pipelines and `MockAssessmentEngine`.
5. **Governance & Fairness Separation:** The Fairlearn demographic audit code in [`src/ml/explainability/fairness.py`](file:///home/gnx/Projects/PARAKH/src/ml/explainability/fairness.py) is completely unintegrated into backend APIs or runtime dashboards. No backend endpoint executes fairness evaluations or persists group-labeled metrics.

### Quantitative Gap Summary:
- **Total Identified Gaps:** 24
- **P0 Gaps:** 0 (No active security or assessment correctness blocker on the verified path)
- **P1 Gaps:** 6 (Architectural and data persistence bottlenecks)
- **P2 Gaps:** 11 (Unwired endpoints, dead API methods, unpersisted UI state)
- **P3 Gaps:** 7 (Stale UI copy, mock alert imports, local-only filter controls)

---

## 2. Scope and Methodology

### Scope
Every directory and file across the three primary layers was analyzed:
- **Frontend:** [`frontend/apps/web/app/**`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app), [`frontend/packages/api/**`](file:///home/gnx/Projects/PARAKH/frontend/packages/api), [`frontend/packages/types/**`](file:///home/gnx/Projects/PARAKH/frontend/packages/types).
- **Backend:** [`backend/app/api/**`](file:///home/gnx/Projects/PARAKH/backend/app/api), [`backend/app/services/**`](file:///home/gnx/Projects/PARAKH/backend/app/services), [`backend/app/models/**`](file:///home/gnx/Projects/PARAKH/backend/app/models), [`backend/app/schemas/**`](file:///home/gnx/Projects/PARAKH/backend/app/schemas), [`backend/app/repositories/**`](file:///home/gnx/Projects/PARAKH/backend/app/repositories), [`backend/app/assessment/**`](file:///home/gnx/Projects/PARAKH/backend/app/assessment).
- **Machine Learning:** [`src/ml/**`](file:///home/gnx/Projects/PARAKH/src/ml), [`models/artifacts/**`](file:///home/gnx/Projects/PARAKH/models/artifacts), [`docs/**`](file:///home/gnx/Projects/PARAKH/docs).

### Methodology
1. **Static Code Inspection & Cross-Referencing:** Every route, endpoint, service, schema, and ML function was inventoried.
2. **Reverse Call-Graph Tracing:** All 47 API client methods in `@parakh/api` were traced across all `.tsx` and `.ts` files in `apps/web/`.
3. **OpenAPI Schema Extraction:** The complete FastAPI OpenAPI schema was extracted programmatically and cross-matched against frontend consumption.
4. **Data Contract Reconciliation:** The 46-field input contract, 64-column model matrix, and 9-column output contract were matched against frontend form inputs and backend database tables.
5. **Zero-Modification Enforcement:** The repository was analyzed in strict read-only mode; no code or schema files were touched.

---

## 3. Current Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             FRONTEND (Next.js 16)                                │
│                                                                                  │
│   Applicant Portal               Admin / Reviewer Cockpit      Model Governance  │
│   - /user/dashboard             - /admin/dashboard            - /admin/model-    │
│   - /user/applications/new      - /admin/applications           insights         │
│   - /user/results/[id]          - /admin/applications/[id]    - /admin/analytics │
│   - /user/profile               - /admin/profile                                 │
└─────────────────────────┬──────────────────────────────────┬─────────────────────┘
                          │ (HTTP / JSON via @parakh/api)    │
                          ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND (FastAPI)                                    │
│                                                                                  │
│  FastAPI Routers (42 Endpoints)                                                  │
│  ├── /auth (login, register, me)                                                 │
│  ├── /applications (CRUD, status, assess)                                        │
│  ├── /applicants (CRUD by user/id)                                               │
│  ├── /financial-signals (ingest, list)                                           │
│  ├── /consents (create, list, revoke)                                            │
│  ├── /reviews (create review, list by app/reviewer)                              │
│  ├── /analytics (portfolio SQL aggregation, sector risk)                         │
│  └── /model-versions (list, get active)                                          │
│                                                                                  │
│  Service Layer ─── AssessmentService ─── FeaturePipeline (Passthrough)           │
│         │                                        │                               │
│         ▼                                        ▼                               │
│  PostgreSQL 16 DB                         MLModelAdapter                         │
│  (9 Tables: users, apps,                  (Transforms AssessmentInput to         │
│   profiles, assessments,                   46-field flat dict; applies           │
│   signals, consents, reviews,              fallback defaults)                    │
│   model_versions, audit_logs)                    │                               │
└──────────────────────────────────────────────────┼───────────────────────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          MACHINE LEARNING (src/ml)                               │
│                                                                                  │
│  RiskPredictor (Phase 9 Singleton Orchestrator)                                  │
│  ├── InputValidator (46 raw input checks, range & type assertions)               │
│  ├── Data Sufficiency Gate (observed_days >= 30, payouts >= 4, groups >= 2)       │
│  ├── FeatureEngineer (Transforms to 9 engineered volatility features)            │
│  ├── CreditRiskPreprocessor (RobustScaler + OneHotEncoder -> 64 columns)         │
│  ├── LightGBM Model Artifact (volatility_aware_risk_model.joblib)                │
│  ├── TreeShapExplainer (Computes local SHAP attributions per instance)           │
│  ├── PlainLanguageExplainer (Generates protective/risk borrower text)            │
│  └── OutputFormatter (Maps probability to 300-850 presentation score & tiers)    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Frontend Inventory

### 4.1 Route & Page Inventory (16 Pages)

| Route | Page File | Primary Purpose | Role | Data Displayed | API Calls Used | Status |
|---|---|---|---|---|---|---|
| `/` | `app/page.tsx` | Root redirect | Any | Redirect logic | None | `FRONTEND_ONLY` |
| `/login` | `app/login/page.tsx` | Authentication | Public | Email/password form | `api.login` | `LIVE_BACKEND` |
| `/signup` | `app/signup/page.tsx` | Registration | Public | Name, email, password, role | `api.register` | `LIVE_BACKEND` |
| `/unauthorized` | `app/unauthorized/page.tsx` | 403 Forbidden | Any | Error notification | None | `FRONTEND_ONLY` |
| `/user/dashboard` | `app/user/dashboard/page.tsx` | Applicant Overview | APPLICANT | Profile, active apps, latest score/tier | `getApplicantByUserId`, `getApplicationsByApplicant`, `getLatestAssessmentByApplication` | `LIVE_ML_BACKEND` |
| `/user/applications` | `app/user/applications/page.tsx` | Application History | APPLICANT | List of user applications & scores | `getApplicantByUserId`, `getApplicationsByApplicant`, `getLatestAssessmentByApplication` | `LIVE_ML_BACKEND` |
| `/user/applications/new` | `app/user/applications/new/page.tsx` | Loan Application Form | APPLICANT | 5-step application wizard, telemetry inputs | `createApplicant`, `createApplication`, `recordFinancialSignals`, `createConsent`, `triggerAssessment` | `LIVE_ML_BACKEND` |
| `/user/applications/[id]` | `app/user/applications/[id]/page.tsx` | Application Dossier | APPLICANT | Application terms, active consents, review decision | `getApplicationById`, `getApplicantProfile`, `getActiveConsentsByApplication`, `revokeConsent`, `getReviewsByApplication` | `LIVE_BACKEND` |
| `/user/results/[id]` | `app/user/results/[id]/page.tsx` | Assessment Scorecard | APPLICANT | Score (300-850), risk tier, probability, TreeSHAP factors | `sessionStorage` cache, `getLatestAssessmentByApplication`, `getAssessmentById` | `LIVE_ML_BACKEND` |
| `/user/profile` | `app/user/profile/page.tsx` | Applicant Profile | APPLICANT | Identity, linked apps, active consents, telemetry | `getApplicantByUserId`, `getApplicationsByApplicant`, `getActiveConsentsByApplication`, `revokeConsent`, `getFinancialSignals` | `PARTIAL` |
| `/admin/dashboard` | `app/admin/dashboard/page.tsx` | Reviewer Cockpit | REVIEWER / ADMIN | Portfolio KPIs, priority review queue, operational alerts | `getPortfolioAnalyticsAdapted`, `getApplications`, `getLatestAssessmentByApplication` | `PARTIAL` |
| `/admin/applications` | `app/admin/applications/page.tsx` | Application Queue | REVIEWER / ADMIN | Complete application review table with search/filter | `getApplications`, `getLatestAssessmentByApplication` | `LIVE_ML_BACKEND` |
| `/admin/applications/[id]` | `app/admin/applications/[id]/page.tsx` | Reviewer Decisioning | REVIEWER / ADMIN | Full dossier, cashflow telemetry, TreeSHAP drivers, review form | `getApplicationById`, `getApplicantProfile`, `getFinancialSignals`, `getLatestAssessmentByApplication`, `getReviewsByApplication`, `createReview`, `updateApplicationStatus` | `LIVE_ML_BACKEND` |
| `/admin/analytics` | `app/admin/analytics/page.tsx` | Portfolio Analytics | REVIEWER / ADMIN | KPI summary, sector-wise risk breakdown, rebound curves | `getPortfolioAnalyticsAdapted` | `PARTIAL` |
| `/admin/model-insights` | `app/admin/model-insights/page.tsx` | Model Governance | REVIEWER / ADMIN | Active model metadata, PostgreSQL version lineage, SHAP & fairness status | `getModelVersions` | `LIVE_BACKEND` |
| `/admin/profile` | `app/admin/profile/page.tsx` | Reviewer Identity | REVIEWER / ADMIN | Officer identity, review count, authority scope | `getReviewsByReviewer` | `PARTIAL` |

### 4.2 Frontend API Client Method Utilization (47 Methods)

- **Methods Used by UI Pages (24 methods):**
  `login`, `register`, `getMe`, `createApplicant`, `getApplicantByUserId`, `getApplicantProfile`, `createApplication`, `getApplications`, `getApplicationById`, `getApplicationsByApplicant`, `updateApplicationStatus`, `recordFinancialSignals`, `getFinancialSignals`, `createConsent`, `getActiveConsentsByApplication`, `revokeConsent`, `triggerAssessment`, `getAssessmentById`, `getLatestAssessmentByApplication`, `createReview`, `getReviewsByApplication`, `getReviewsByReviewer`, `getModelVersions`, `getPortfolioAnalyticsAdapted`.

- **Methods Unused / Dead in UI (23 methods):**
  1. `getUserById`: Backend `GET /users/{id}` has no UI caller.
  2. `getUserByEmail`: Backend `GET /users/by-email/{email}` has no UI caller.
  3. `updateUser`: Backend `PATCH /users/{id}` has no UI caller.
  4. `updateApplicantProfile`: Backend `PATCH /applicants/{id}` has no UI caller.
  5. `updateApplication`: Backend `PATCH /applications/{id}` has no UI caller.
  6. `getAssessmentsByApplication`: Replaced by `getLatestAssessmentByApplication`.
  7. `getLatestFinancialSignals`: Replaced by `getFinancialSignals`.
  8. `getConsentsByApplication`: Replaced by `getActiveConsentsByApplication`.
  9. `createModelVersion`: No UI form to upload or register new models.
  10. `getActiveModelVersion`: Replaced by `getModelVersions` client-side filtering.
  11. `getModelVersionById`: No UI caller.
  12. `getAuditLogs`: Backend audit log API is completely unused.
  13. `getAuditLogById`: No UI caller.
  14. `getPortfolioAnalytics`: Replaced by `getPortfolioAnalyticsAdapted`.
  15. `getSectorRisk`: Replaced by `getPortfolioAnalyticsAdapted` (sector risk bundled).
  16. `getSectorRiskAdapted`: Redundant with portfolio analytics.
  17. `getApplicationAdapted`: Unused helper.
  18. `getApplicationsAdapted`: Unused helper.
  19. `getAssessmentAdapted`: Unused helper.
  20. `getLatestAssessmentAdapted`: Unused helper.
  21. `triggerAssessmentAdapted`: Unused helper.
  22. `recordReviewOutcomeAdapted`: Unused helper.
  23. `getBorrowerProfileAdapted`: Unused helper.

---

## 5. Backend Inventory

### 5.1 Endpoint Inventory (42 OpenAPI Endpoints)

| HTTP Method | Path | Summary / Purpose | Auth / Role | DB Dependency | ML Dependency | Frontend Consumer |
|---|---|---|---|---|---|---|
| `GET` | `/` | Root service status | None | None | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/health` | Liveness healthcheck | None | None | None | `NOT_CONSUMED_BY_FRONTEND` (Docker only) |
| `GET` | `/api/v1/status` | API version metadata | None | None | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/database/health` | DB connectivity check | None | Direct SQL | None | `NOT_CONSUMED_BY_FRONTEND` |
| `POST` | `/api/v1/auth/login` | User login (JWT) | None | `users` | None | `CONSUMED_BY_FRONTEND` (`AuthContext`) |
| `GET` | `/api/v1/auth/me` | Current user profile | Authenticated | `users` | None | `CONSUMED_BY_FRONTEND` (`AuthContext`) |
| `POST` | `/api/v1/users` | Register user account | None | `users` | None | `CONSUMED_BY_FRONTEND` (`AuthContext`) |
| `GET` | `/api/v1/users/{user_id}` | Read user by UUID | Authenticated | `users` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/users/by-email/{email}` | Read user by email | Authenticated | `users` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `PATCH` | `/api/v1/users/{user_id}` | Update user fields | Authenticated | `users` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `POST` | `/api/v1/applicants` | Create applicant profile | Authenticated | `applicant_profiles` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/new`) |
| `GET` | `/api/v1/applicants/user/{user_id}` | Get profile by user | Authenticated | `applicant_profiles` | None | `CONSUMED_BY_FRONTEND` (Dashboard, Profile) |
| `GET` | `/api/v1/applicants/{profile_id}` | Get profile by UUID | Authenticated | `applicant_profiles` | None | `CONSUMED_BY_FRONTEND` (Dossier views) |
| `PATCH` | `/api/v1/applicants/{profile_id}` | Update profile | Authenticated | `applicant_profiles` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/applications` | List all applications | Reviewer/Admin | `applications` | None | `CONSUMED_BY_FRONTEND` (`/admin/applications`) |
| `POST` | `/api/v1/applications` | Create application | Applicant | `applications` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/new`) |
| `GET` | `/api/v1/applications/applicant/{id}` | Applications by applicant | Authenticated | `applications` | None | `CONSUMED_BY_FRONTEND` (`/user/applications`) |
| `GET` | `/api/v1/applications/{id}` | Read application | Authenticated | `applications` | None | `CONSUMED_BY_FRONTEND` (Dossier views) |
| `PATCH` | `/api/v1/applications/{id}` | Update application terms | Authenticated | `applications` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `PATCH` | `/api/v1/applications/{id}/status` | Update workflow status | Reviewer/Admin | `applications` | None | `CONSUMED_BY_FRONTEND` (`/admin/applications/[id]`) |
| `POST` | `/api/v1/applications/{id}/assess` | **Trigger Assessment** | Authenticated | `credit_assessments` | **RiskPredictor** | `CONSUMED_BY_FRONTEND` (`/user/applications/new`) |
| `GET` | `/api/v1/applications/{id}/assessments` | List app assessments | Authenticated | `credit_assessments` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/applications/{id}/assessments/latest` | Read latest assessment | Authenticated | `credit_assessments` | None | `CONSUMED_BY_FRONTEND` (Dashboards, Results) |
| `GET` | `/api/v1/assessments/{assessment_id}` | Read assessment by UUID | Authenticated | `credit_assessments` | None | `CONSUMED_BY_FRONTEND` (`/user/results/[id]`) |
| `POST` | `/api/v1/applications/{id}/financial-signals` | Ingest signals | Authenticated | `financial_signals` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/new`) |
| `GET` | `/api/v1/applications/{id}/financial-signals` | List app signals | Authenticated | `financial_signals` | None | `CONSUMED_BY_FRONTEND` (`/admin/applications/[id]`) |
| `GET` | `/api/v1/applications/{id}/financial-signals/latest` | Read latest signal | Authenticated | `financial_signals` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `POST` | `/api/v1/consents` | Record DPDP consent | Authenticated | `consents` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/new`) |
| `GET` | `/api/v1/applications/{id}/consents` | List consents | Authenticated | `consents` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/applications/{id}/consents/active` | Read active consents | Authenticated | `consents` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/[id]`) |
| `POST` | `/api/v1/consents/{id}/revoke` | Revoke consent | Authenticated | `consents` | None | `CONSUMED_BY_FRONTEND` (`/user/applications/[id]`) |
| `POST` | `/api/v1/applications/{id}/reviews` | Record review decision | Reviewer/Admin | `underwriter_reviews` | None | `CONSUMED_BY_FRONTEND` (`/admin/applications/[id]`) |
| `GET` | `/api/v1/applications/{id}/reviews` | List app reviews | Authenticated | `underwriter_reviews` | None | `CONSUMED_BY_FRONTEND` (Dossier views) |
| `GET` | `/api/v1/reviewers/{id}/reviews` | List reviewer history | Reviewer/Admin | `underwriter_reviews` | None | `CONSUMED_BY_FRONTEND` (`/admin/profile`) |
| `GET` | `/api/v1/model-versions` | List registered models | Authenticated | `model_versions` | None | `CONSUMED_BY_FRONTEND` (`/admin/model-insights`) |
| `POST` | `/api/v1/model-versions` | Register new model | Admin only | `model_versions` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/model-versions/active/{name}` | Get active model | Authenticated | `model_versions` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/model-versions/{id}` | Read model version | Authenticated | `model_versions` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/audit-logs` | List audit logs | Admin only | `audit_logs` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/audit-logs/{id}` | Read audit log | Admin only | `audit_logs` | None | `NOT_CONSUMED_BY_FRONTEND` |
| `GET` | `/api/v1/analytics/portfolio` | Portfolio aggregations | Reviewer/Admin | Multi-table SQL | None | `CONSUMED_BY_FRONTEND` (Analytics, Dashboard) |
| `GET` | `/api/v1/analytics/sector-risk` | Sector risk breakdown | Reviewer/Admin | Multi-table SQL | None | `NOT_CONSUMED_BY_FRONTEND` (Bundled in portfolio) |

---

## 6. Machine Learning Inventory

### 6.1 ML Subsystem Components (`src/ml/`)

| Subsystem | Primary Modules | Description | Runtime Role |
|---|---|---|---|
| **Data & Splitting** | `src/ml/data/dataset_validator.py`<br>`src/ml/data/splitting.py` | 46-field input boundaries, feature bounds, grouped split | Offline training split replication |
| **Preprocessing** | `src/ml/data/preprocessing.py`<br>`src/ml/preprocessing.py` | `CreditRiskPreprocessor` (RobustScaler, OHE, log1p) | Fits at `RiskPredictor.__init__`, transforms inference input |
| **Feature Engineering** | `src/ml/features/feature_engineering.py`<br>`src/ml/features/feature_manifest.py` | Generates 9 engineered volatility interaction features | Transforms single-row dataframe during inference |
| **Model Architectures** | `src/ml/models/volatility_aware.py`<br>`src/ml/models/baseline.py` | `LightGbmVolatilityRiskModel`, `BaselineRiskModel` | Active frozen model loaded from disk |
| **Inference Pipeline** | `src/ml/inference/predictor.py`<br>`src/ml/inference/input_validator.py`<br>`src/ml/inference/output_formatter.py` | `RiskPredictor`, sufficiency rules, 300-850 score mapping | **Primary runtime inference engine** |
| **Explainability** | `src/ml/explainability/shap_explainer.py`<br>`src/ml/explainability/plain_language.py` | `TreeShapExplainer` (TreeSHAP), `PlainLanguageExplainer` | Generates local factor attributions per scored row |
| **Fairness Auditing** | `src/ml/explainability/fairness.py`<br>`src/ml/explainability/run_phase7_audit.py` | `GroupedFairnessAuditor` (DPR, Equalized Odds) | **Offline evaluation only** (no runtime API) |
| **Evaluation** | `src/ml/evaluation/run_phase8_validation.py` | ROC-AUC, PR-AUC, Brier score, calibration curve | **Offline evaluation only** (no runtime API) |
| **Artifacts** | `models/artifacts/FINAL_MODEL.json`<br>`volatility_aware_risk_model.joblib` | Model manifest (SHA256 verified) and trained joblib | Loaded by `RiskPredictor` |

### 6.2 The 40 Derived + 6 Raw + 9 Engineered Volatility Features (64 Model-Ready Columns)

1. **6 Raw Inputs:** `requested_loan_amount`, `loan_tenure_months`, `years_working`, `average_working_days`, `gig_work_type` (OHE: 6 cols), `loan_purpose` (OHE: 5 cols).
2. **19 Mandatory Derived Features:** `feat_inc_median_90d`, `feat_inc_p25_90d`, `feat_inc_cv_90d`, `feat_inc_downside_var`, `feat_trend_slope_90d`, `feat_trend_momentum_30_90`, `feat_act_active_days_ratio`, `feat_act_zero_earn_weeks`, `feat_rec_bounceback_ratio`, `feat_rec_days_to_recover`, `feat_liq_buffer_to_loan`, `feat_liq_burn_months`, `feat_bur_dti_ratio`, `feat_bur_installment_dti`, `feat_bur_total_dti`, `feat_suf_observed_days`, `feat_suf_payout_count`, `feat_suf_group_count`, `feat_suf_missing_ratio`.
3. **21 Optional Derived Features:** `feat_inc_mean_90d`, `feat_inc_trimmed_mean`, `feat_inc_iqr_ratio`, `feat_inc_min_max_ratio`, `feat_trend_consec_drops`, `feat_act_max_idle_streak`, `feat_act_weekend_intensity`, `feat_rec_max_drawdown`, `feat_ten_years_working`, `feat_ten_platform_rating`, `feat_ten_trips_completed`, `feat_ten_cancellation_rate`, `feat_liq_net_margin`, `feat_pay_utility_on_time`, `feat_pay_max_bill_delay`, `feat_pay_repay_reliability`, `feat_bur_loan_to_income`, `feat_int_vol_x_recovery`, `feat_int_vol_x_buffer`, `feat_int_trend_x_dti`, `feat_int_resilience_idx`.
4. **9 Engineered Volatility Interactions:** `feat_eng_vol_to_baseline`, `feat_eng_downside_to_median`, `feat_eng_vol_x_trend`, `feat_eng_vol_to_bounceback`, `feat_eng_recovery_velocity`, `feat_eng_buffer_burn_coverage`, `feat_eng_vol_cushion_ratio`, `feat_eng_dti_risk_multiplier`, `feat_eng_installment_floor_coverage`.

---

## 7. Frontend → Backend Gap Analysis

### Question A: Which frontend features require backend data or actions that do not exist?
- **Privacy Preference Toggles:** On `/user/profile`, toggles for *Anonymized Industry Volatility Benchmarking*, *Real-Time Telemetry Ingestion*, and *Automated Downside Shock Alerts* have no corresponding backend endpoints or database columns.
- **Analytics Date Filtering:** On `/admin/analytics`, filter buttons for `30D`, `90D`, `6M`, and `ALL` cannot pass time-range queries because `GET /api/v1/analytics/portfolio` does not accept date parameters.
- **Audit Log Inspection:** The admin interface offers no route to view system audit logs, even though the backend provides full audit models and queries.

### Question B: Which frontend API client methods call non-existent or unused endpoints?
- All 47 methods in `@parakh/api` point to valid backend routes. However, **23 methods are dead / unused** by frontend pages.

### Question C: Which backend endpoints exist but have no frontend consumer?
- 18 backend endpoints have zero frontend callers (detailed in Section 5.1).

### Question D: Which frontend views display values not returned by backend?
- **Operational Alerts:** `/admin/dashboard` displays 3 operational alerts sourced entirely from static mock file `@/data/mock/admin`.
- **Reviewer Completed Reviews Count:** `/admin/profile` initializes review count to `218` as a fallback when backend calls fail.
- **Audit Hardware Session:** `/admin/profile` exports hardcoded string `Hardware FIDO2 Token (SHA-256)` and `AUD-2026-904`.

### Question E: Which frontend values are fabricated through fallback/default values?
- On `/admin/dashboard` and `/admin/analytics`, `avgScore ?? 0` causes an empty portfolio to render as an alternative credit score of `0` instead of `null` or `"Unrated"`.

### Question F: Which frontend buttons/actions have no real backend operation?
- Clicking any of the 3 privacy preference switches on `/user/profile` toggles React state only; no network request is sent.
- Clicking time-range buttons on `/admin/analytics` updates React state only; charts do not re-fetch.

---

## 8. Backend → Frontend Gap Analysis

1. **Immutable Audit Trail Inaccessibility:** The backend automatically logs actor actions, IPs, timestamps, and resource mutations into `audit_logs`. The frontend has zero pages to inspect, filter, or export these logs.
2. **Model Version Management Inaccessibility:** While `/admin/model-insights` displays registered model versions via `GET`, Admins cannot register new models (`POST /api/v1/model-versions`) through the UI.
3. **Applicant Profile Updates Inaccessible:** `PATCH /api/v1/applicants/{profile_id}` allows updating income, platform, and phone number, but `/user/profile` provides no edit mode.
4. **Historical Assessment Auditing:** `GET /api/v1/applications/{id}/assessments` returns all historical assessments for an application, but the frontend only ever queries and renders the single latest assessment.

---

## 9. Backend → ML Gap Analysis

### Question A: Which ML inputs are expected by RiskPredictor but not reliably supplied by the backend?
- `RiskPredictor` requires 46 flat input fields. The backend database stores only core financial signals (`average_income`, `median_income`, `income_volatility`, `active_days`, `payment_regularity`, `cashflow_buffer`, `existing_obligation`, `platform_rating`, `repayment_reliability`).
- The remaining 37 features (e.g. `feat_inc_downside_var`, `feat_trend_slope_90d`, `feat_liq_burn_months`, `feat_suf_*`) are **not computed from raw transactions by the backend**.

### Question B: Which backend fields are filled using synthetic/default fallbacks before ML inference?
- In `backend/app/assessment/ml_model_adapter.py`:
  - `feat_suf_observed_days` defaults to `90.0`
  - `feat_suf_payout_count` defaults to `12.0`
  - `feat_suf_group_count` defaults to `4.0`
  - `feat_suf_missing_ratio` defaults to `0.0`
  - `median_income` defaults to `7000.0`
  - `loan_tenure_months` defaults to `12`
  - `years_working` defaults to `0.0`
  - `average_working_days` defaults to `20.0`
  - `platform_rating` defaults to `4.50`
  - `repayment_reliability` defaults to `0.95`
  - `payment_regularity` defaults to `0.90`

### Question C: Can fallbacks bypass data sufficiency checks?
- **YES.** Because `feat_suf_observed_days` (threshold >= 30), `feat_suf_payout_count` (threshold >= 4), and `feat_suf_group_count` (threshold >= 2) default to 90, 12, and 4 respectively, any application submitted without an explicit `signal_metadata` dictionary will **bypass the sufficiency gate** and be scored by LightGBM.

### Question D: Which ML outputs are discarded or not persisted?
- The backend `credit_assessments` table discards:
  - TreeSHAP numerical feature attributions
  - Plain-language key risk and protective factors
  - Missing signals breakdown
  - Diagnostic threshold status

---

## 10. ML → Backend Gap Analysis

1. **Fairness Auditing Unwired:** `src/ml/explainability/fairness.py` implements statutory demographic parity and equalized odds evaluations, but no backend service or route exists to trigger audits or query results.
2. **Global Feature Importance Unpersisted:** `TreeShapExplainer` operates row-by-row. There is no background aggregation job or database table to store global feature rankings.
3. **Offline Preprocessor Re-fitting:** `RiskPredictor.__init__()` deterministically splits and fits the preprocessor on the synthetic dataset at application startup because no serialized preprocessor `.joblib` artifact was persisted during model training.
4. **Baseline Model Inaccessible:** `BaselineRiskModel` (Logistic Regression) is implemented and validated in `src/ml/models/baseline.py`, but `backend/app/assessment/factory.py` only toggles between `MockAssessmentEngine` and `MLModelAdapter` (LightGBM).

---

## 11. ML → Frontend Gap Analysis

1. **TreeSHAP Persistence Loss Across Sessions:** Because the backend does not persist SHAP outputs in PostgreSQL, TreeSHAP explanations are cached in `sessionStorage`. If the user opens `/user/results/[id]` on another device or refreshes in a private window, TreeSHAP drivers cannot be rendered.
2. **Missing Numerical SHAP Attributions:** Frontend only renders qualitative tags (*"Associated with lower predicted risk"*) generated by `PlainLanguageExplainer`; raw SHAP values are not accessible for administrative auditing.
3. **Static Governance Displays:** In `/admin/model-insights`, global SHAP is marked `Not Persisted` and fairness is marked `Evaluation data required` because the backend exposes no API for ML evaluation metrics.

---

## 12. Frontend Feature Contract Matrix

| Field | Source UI Form | Transmitted in API | Backend Model Field | Database Column | Default / Fallback |
|---|---|---|---|---|---|
| `requested_loan_amount` | Step 1 (`/user/applications/new`) | `loan_amount_requested` | `Application.loan_amount_requested` | `applications.loan_amount_requested` | None (Required) |
| `loan_tenure_months` | Step 1 (`/user/applications/new`) | `loan_tenure_months` | `Application.loan_tenure_months` | `applications.loan_tenure_months` | `12` |
| `loan_purpose` | Step 1 (`/user/applications/new`) | `loan_purpose` | `Application.loan_purpose` | `applications.loan_purpose` | `WORKING_CAPITAL` |
| `gig_work_type` | Step 3 (`/user/applications/new`) | `gig_work_type` | `ApplicantProfile.gig_work_type` | `applicant_profiles.gig_work_type` | `OTHER` |
| `average_income` | Step 4 (`/user/applications/new`) | `average_income` | `FinancialSignal.average_income` | `financial_signals.average_income` | `7000.0` |
| `active_days` | Step 4 (`/user/applications/new`) | `active_days` | `FinancialSignal.active_days` | `financial_signals.active_days` | `65` (via 0.65 ratio) |
| `cashflow_buffer` | Step 4 (`/user/applications/new`) | `cashflow_buffer` | `FinancialSignal.cashflow_buffer` | `financial_signals.cashflow_buffer` | `0.20 * loan_amount` |
| `existing_obligation` | Step 4 (`/user/applications/new`) | `existing_obligation` | `FinancialSignal.existing_obligation` | `financial_signals.existing_obligation` | `0.25 * monthly_income` |
| `platform_rating` | Step 3 (`/user/applications/new`) | `platform_rating` | `FinancialSignal.platform_rating` | `financial_signals.platform_rating` | `4.50` |
| `repayment_reliability`| Step 4 (`/user/applications/new`) | `repayment_reliability` | `FinancialSignal.repayment_reliability` | `financial_signals.repayment_reliability` | `0.95` |
| `signal_metadata` | Step 4 (`/user/applications/new`) | `signal_metadata` | `FinancialSignal.signal_metadata` | `financial_signals.signal_metadata` (JSON) | `{}` |

---

## 13. ML Input Contract Matrix

| Input Feature | Expected by ML | Source in Backend | Supplied by Default? | Fallback Value if Absent |
|---|---|---|---|---|
| `requested_loan_amount` | Yes (Raw) | `AssessmentInput.requested_loan_amount` | Yes | None |
| `loan_tenure_months` | Yes (Raw) | `AssessmentInput.loan_tenure_months` | Yes | `12` |
| `years_working` | Yes (Raw) | `AssessmentInput.years_working` | Yes | `0.0` |
| `average_working_days` | Yes (Raw) | `AssessmentInput.average_working_days` | Yes | `20.0` |
| `gig_work_type` | Yes (Raw) | `AssessmentInput.gig_work_type` | Yes | `"OTHER"` |
| `loan_purpose` | Yes (Raw) | `AssessmentInput.loan_purpose` | Yes | `"WORKING_CAPITAL"` |
| `feat_inc_median_90d` | Yes (Mandatory) | `derived_features` or `median_income` | Fallback | `median_income` or `7000.0` |
| `feat_inc_cv_90d` | Yes (Mandatory) | `derived_features` or `income_volatility`| Fallback | `income_volatility` or `0.25` |
| `feat_suf_observed_days`| Yes (Mandatory) | `derived_features` | Fallback | `90.0` (Bypasses sufficiency gate!) |
| `feat_suf_payout_count` | Yes (Mandatory) | `derived_features` | Fallback | `12.0` (Bypasses sufficiency gate!) |
| `feat_suf_group_count` | Yes (Mandatory) | `derived_features` | Fallback | `4.0` (Bypasses sufficiency gate!) |
| `feat_suf_missing_ratio`| Yes (Mandatory) | `derived_features` | Fallback | `0.0` |
| `feat_bur_total_dti` | Yes (Mandatory) | `derived_features` or calculated | Fallback | `dti_ratio + installment_dti` |
| `feat_liq_buffer_to_loan`| Yes (Mandatory) | `derived_features` or calculated | Fallback | `cashflow_buffer / loan_amount` |
| 21 Optional Features | Yes (Optional) | `derived_features` | Fallback | Static defaults in `MLModelAdapter` |

---

## 14. ML Output Contract Matrix

| Output Attribute | Generated by ML | Backend Schema Field | Persisted in DB? | API Response | Frontend Display |
|---|---|---|---|---|---|
| `presentation_score` | Yes (`[300, 850]`) | `CreditAssessment.credit_score` | **Yes** (`credit_score`) | Yes (`score`) | Yes (`ScoreDisplay`) |
| `repayment_risk_probability` | Yes (`[0.0, 1.0]`) | `CreditAssessment.risk_probability` | **Yes** (`risk_probability`) | Yes | Yes (Dossier & Results) |
| `risk_tier` | Yes (`LOWER`, etc.) | `CreditAssessment.risk_level` | **Yes** (`risk_level`) | Yes | Yes (`RiskBadge`) |
| `confidence` | Yes (`[0.0, 1.0]`) | `CreditAssessment.confidence` | **Yes** (`confidence`) | Yes | Yes (Results & Admin) |
| `model_name` | Yes | `CreditAssessmentResponse.model_name` | **No** (Linked via FK) | Yes | Yes (`ModelBadge`) |
| `model_version` | Yes | `CreditAssessmentResponse.model_version`| **No** (Linked via FK) | Yes | Yes (`ModelBadge`) |
| `missing_signals` | Yes (on failure) | `CreditAssessmentResponse.explanation` | **No** | Transient | Yes (Banner if cached) |
| `key_protective_factors`| Yes (TreeSHAP) | `CreditAssessmentResponse.explanation` | **No** (LOST ON RELOAD) | Transient | Yes (via `sessionStorage`) |
| `key_risk_factors` | Yes (TreeSHAP) | `CreditAssessmentResponse.explanation` | **No** (LOST ON RELOAD) | Transient | Yes (via `sessionStorage`) |
| `disclaimer` | Yes | `CreditAssessmentResponse.explanation` | **No** | Transient | Yes (Results Footer) |

---

## 15. Three-Layer Capability Matrix

| Capability | Frontend | Backend | ML | End-to-End Wired? | Evidence | Gap Description | Priority |
|---|---|---|---|---|---|---|---|
| **Authentication** | Implemented | Implemented | N/A | **Yes** | `/login`, `/auth/login`, JWT tokens | None | NO_GAP |
| **Applicant Profile** | Implemented | Implemented | N/A | **Partial** | Profile created; editing disabled | Profile editing unwired (`PATCH` unused) | P2 |
| **Application Creation** | Implemented | Implemented | N/A | **Yes** | 5-step wizard creates DB record | None | NO_GAP |
| **Application Updates** | Partial | Implemented | N/A | **Partial** | Only status transitions wired | Term updates unwired (`PATCH` unused) | P2 |
| **Signal Ingestion** | Implemented | Implemented | Consumed | **Yes** | Ingests to `financial_signals` | Does not trigger raw feature pipeline | P1 |
| **Consent Management** | Implemented | Implemented | N/A | **Yes** | Active consents & revocation live | DPDP toggles on profile are local state | P2 |
| **Assessment Triggering**| Implemented | Implemented | Implemented | **Yes** | `POST /assess` executes predictor | None | NO_GAP |
| **Credit Scoring** | Implemented | Implemented | Implemented | **Yes** | 300-850 presentation score mapped | None | NO_GAP |
| **Risk Probability** | Implemented | Implemented | Implemented | **Yes** | Default probability persisted | None | NO_GAP |
| **Confidence Level** | Implemented | Implemented | Implemented | **Yes** | Boundary distance metric live | None | NO_GAP |
| **Insufficient Evidence**| Implemented | Implemented | Implemented | **Yes** | Unrated status & null score handled | Adapter fallbacks bypass sufficiency | P1 |
| **TreeSHAP Explanations**| Implemented | Transient | Implemented | **Partial** | Live via `sessionStorage` only | **Not persisted in PostgreSQL** | P1 |
| **Global SHAP Rankings** | Stale Notice| None | None | **No** | Marked `Not Persisted` in UI | No aggregation pipeline exists | P2 |
| **Model Versioning** | Read-Only | Implemented | Implemented | **Partial** | PostgreSQL registry displayed | No model registration UI | P2 |
| **Fairness Auditing** | Conceptual | None | Implemented | **No** | Marked `Evaluation data required` | Fairlearn code unintegrated in runtime | P2 |
| **Portfolio Analytics** | Implemented | Implemented | N/A | **Yes** | Real-time SQL GROUP BY aggregation | Time range filter is local state | P3 |
| **Reviewer Workflow** | Implemented | Implemented | N/A | **Yes** | Approvals, rejections, escalations | None | NO_GAP |
| **Audit Logging** | None | Implemented | N/A | **No** | DB table exists; no UI caller | 2 audit endpoints unused | P2 |
| **RBAC Enforcement** | Implemented | Implemented | N/A | **Yes** | Verified across all roles in 11C | None | NO_GAP |

---

## 16. Mock / Hardcoded / Placeholder Audit

1. **`mockOperationalAlerts` Import:** [`frontend/apps/web/app/admin/dashboard/page.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/dashboard/page.tsx#L49-L50) imports static mock alerts from `@/data/mock/admin`.
2. **Stale LightGBM Pipeline Copy in Admin Dashboard:** Line 617 of `admin/dashboard/page.tsx` states: *"Sector-level recovery velocity curves and cyclical volatility indices are computed by Person 2 & 3's LightGBM/XGBoost ML pipeline. In the interim, live assessments are scored through the deterministic MockAssessmentEngine..."*
3. **Stale ML Pipeline Copy in Admin Analytics:** Line 312 of `admin/analytics/page.tsx` states: *"Empirical recovery rebound curves and cyclical variance calibrations depend on Person 3's upcoming LightGBM/XGBoost volatility pipeline. In the interim, live assessments are scored through the deterministic MockAssessmentEngine."*
4. **Hardcoded Fallback Reviews Count:** Line 30 of `admin/profile/page.tsx` initializes `useState<number>(218)`.
5. **Hardcoded Reviewer Audit Session:** Lines 78-79 of `admin/profile/page.tsx` exports hardcoded string `"Hardware FIDO2 Token (SHA-256)"` and `"AUD-2026-904"`.
6. **Local-Only DPDP Preferences:** Lines 53-55 of `user/profile/page.tsx` use pure React `useState(true)` for statutory consent toggles.
7. **Local-Only Analytics Date Filter:** Lines 120-140 of `admin/analytics/page.tsx` use pure React state for `30D`, `90D`, `6M`, `ALL` time range tabs.

---

## 17. Persistence Gaps

1. **Missing `CreditAssessment` Explanation Column:** The PostgreSQL `credit_assessments` table lacks a `JSONB` column to store `explanation_factors`, `key_protective_factors`, `key_risk_factors`, and `missing_signals`.
2. **Missing Consent Scope Preferences:** The `consents` table stores binary active/revoked status, but cannot store granular user toggles for telemetry feeds or benchmarking.
3. **Missing Model Validation & Fairness Audit Tables:** There are no database tables to store historical Fairlearn demographic parity metrics, model evaluation scores (AUC, Brier), or champion/challenger comparison results.

---

## 18. API Gaps

1. **Missing Explainability Persistence in `GET` Endpoints:** `GET /api/v1/applications/{id}/assessments/latest` and `GET /api/v1/assessments/{id}` cannot reconstruct TreeSHAP explanation factors because they are not in the database.
2. **Missing Time-Window Parameters on Analytics:** `GET /api/v1/analytics/portfolio` does not accept `start_date` or `end_date` query parameters.
3. **Missing Model Governance Mutation Endpoints:** No endpoint exists to promote or demote model versions (`POST /api/v1/model-versions/{id}/activate`).
4. **Missing Fairness Evaluation Trigger:** No endpoint exists to run or retrieve Fairlearn audit runs (`POST /api/v1/model-governance/fairness-audit`).

---

## 19. Explainability Gaps

1. **Transient Lifecycle:** TreeSHAP attributions exist for only the duration of the initial HTTP POST response.
2. **Client-Side Dependency:** The frontend is forced to use `window.sessionStorage` as a temporary surrogate for database persistence.
3. **Global vs Local Gap:** Local TreeSHAP is fully operational; global SHAP feature importance is not calculated or persisted.

---

## 20. Fairness / Governance Gaps

1. **Unwired Evaluation Code:** `src/ml/explainability/fairness.py` is capable of computing DPR and Equalized Odds, but is disconnected from the backend API.
2. **Evaluation Dataset Dependency:** Fairness audits cannot be computed until a group-labeled evaluation dataset (containing gender and geographic cohorts) is assembled.
3. **Admin Governance UI Read-Only:** The model insights page is strictly informative; administrators cannot register, evaluate, or deprecate models from the dashboard.

---

## 21. Security / Consent Integration Gaps

1. **Optional Consent Enforcement:** In `AssessmentService.assess_application`, `enforce_consent` defaults to `False`. The production endpoint `POST /api/v1/applications/{id}/assess` does not pass `enforce_consent=True`, allowing assessments to execute even if consent is revoked.
2. **Unpersisted Profile Privacy Toggles:** User choices to opt out of benchmarking or telemetry on `/user/profile` are not enforced by backend ingestion endpoints.

---

## 22. Data Contract Gaps

1. **Feature Engineering Disconnection:** The backend does not execute `src/ml/features/feature_engineering.py` on raw signals. It relies on pre-computed values in `signal_metadata`.
2. **Sufficiency Metric Defaulting:** `MLModelAdapter` defaults sufficiency metrics to sufficient values, inadvertently allowing unconditioned applications to bypass sufficiency checks unless explicit metadata overrides them.
3. **Monetary Denomination Alignment:** Frontend currency formatting uses standard INR, backend models use `Numeric(12, 2)`, and ML models use weekly INR floats. While mathematically compatible, there is no shared cross-layer schema contract definition.

---

## 23. Complete Prioritized Gap List (P0 / P1 / P2 / P3)

### Priority P0 — Critical System Blockers
*(None. The verified core assessment path functions correctly without security or correctness failures.)*

### Priority P1 — Important Architecture & Data Integrity Gaps
1. **[P1-01] Persist TreeSHAP Explanations in Database:** Add `explanation JSONB` column to PostgreSQL `credit_assessments` table and eliminate the frontend `sessionStorage` caching workaround.
2. **[P1-02] Fix MLModelAdapter Sufficiency Defaulting:** Stop defaulting `feat_suf_observed_days`, `feat_suf_payout_count`, and `feat_suf_group_count` to sufficient values; ensure applications without adequate telemetry engage the Refuse-to-Score protocol.
3. **[P1-03] Wire Feature Pipeline to Raw Signals:** Connect `src/ml/features/feature_engineering.py` inside `backend/app/assessment/pipeline.py` to derive the 40 ML features from raw telemetry transactions at runtime.
4. **[P1-04] Enforce DPDP Consent at Assessment Boundary:** Set `enforce_consent=True` by default in `POST /api/v1/applications/{id}/assess`.
5. **[P1-05] Persist Preprocessor Artifact:** Serialise the fitted `CreditRiskPreprocessor` into `models/artifacts/preprocessor.joblib` instead of refitting on synthetic data at server startup.
6. **[P1-06] Reconcile Stale ML Placeholders in Admin Dashboard & Analytics:** Remove misleading claims about upcoming ML models and `MockAssessmentEngine` from `/admin/dashboard` and `/admin/analytics`.

### Priority P2 — Functional & Integration Gaps
7. **[P2-01] Connect Operational Alerts API:** Replace `mockOperationalAlerts` with dynamic system alerts from backend.
8. **[P2-02] Build Audit Log Viewer UI:** Create an Admin audit log viewer consuming `GET /api/v1/audit-logs`.
9. **[P2-03] Implement Date Range Query Parameters on Analytics:** Add `start_date` and `end_date` parameters to `GET /api/v1/analytics/portfolio`.
10. **[P2-04] Wire DPDP Consent Preferences:** Persist profile privacy toggles to backend database.
11. **[P2-05] Wire Applicant Profile Editing:** Connect `/user/profile` to `PATCH /api/v1/applicants/{id}`.
12. **[P2-06] Implement Model Promotion / Activation API:** Add backend endpoint to toggle active model versions in PostgreSQL.
13. **[P2-07] Wire Fairness Audit Execution:** Integrate `GroupedFairnessAuditor` with a backend service endpoint.
14. **[P2-08] Clean Up Dead API Client Methods:** Remove or wire the 23 unused methods in `@parakh/api`.
15. **[P2-09] Clean Up Unconsumed Backend Routes:** Evaluate deprecating or wiring the 18 unconsumed backend endpoints.
16. **[P2-10] Implement Global SHAP Aggregation Job:** Build a periodic aggregation worker to compute and persist global feature importances.
17. **[P2-11] Multi-Model Evaluation & Challenger Support:** Expose baseline vs volatility-aware model performance comparisons in Admin UI.

### Priority P3 — Enhancements & Polish
18. **[P3-01] Remove Fallback Review Count (218) in Admin Profile:** Render zero or loading state instead of a hardcoded number.
19. **[P3-02] Remove Hardcoded FIDO2 Audit String in Profile Export:** Source actual session auth method from JWT claims.
20. **[P3-03] Improve Empty Portfolio Score Rendering:** Render `"Unrated"` instead of `0` when portfolio has no evaluated loans.
21. **[P3-04] Standardize JSON Export Schemas:** Harmonize exported JSON formats between `/admin/profile`, `/user/profile`, and `/admin/model-insights`.
22. **[P3-05] Add Numerical SHAP View for Underwriters:** Provide an expandable table of raw SHAP values in the reviewer dossier.
23. **[P3-06] Refactor Application Term Editing:** Wire `PATCH /api/v1/applications/{id}` for draft loan terms.
24. **[P3-07] Add Export Formats (CSV / PDF):** Implement real PDF / CSV exports for portfolio analytics and model cards.

---

## 24. Recommended Implementation Sequence

```mermaid
flowchart TD
    subgraph Phase 13A: Data Persistence & Contract Integrity
        A1["P1-01: Add explanation JSONB column to credit_assessments"] --> A2["P1-02: Fix MLModelAdapter sufficiency defaulting"]
        A2 --> A3["P1-04: Enforce consent check on POST /assess"]
        A3 --> A4["P1-05: Serialize & load preprocessor.joblib artifact"]
    end

    subgraph Phase 13B: UI Stale Copy & Mock Cleanup
        B1["P1-06: Clean stale ML copy in /admin/dashboard & /admin/analytics"] --> B2["P2-01: Replace mockOperationalAlerts with backend service"]
        B2 --> B3["P3-01: Remove 218 fallback review count and mock session ID"]
        B3 --> B4["P3-03: Render 'Unrated' instead of 0 for empty portfolio"]
    end

    subgraph Phase 13C: Feature Pipeline & Runtime Derivation
        C1["P1-03: Wire FeatureEngineer to runtime signals"] --> C2["P2-03: Add date-range filtering to /analytics/portfolio"]
        C2 --> C3["P2-04: Persist DPDP consent preferences"]
    end

    subgraph Phase 13D: Governance & Audit Expansion
        D1["P2-02: Build Admin Audit Log Viewer UI"] --> D2["P2-06: Model promotion / activation endpoints"]
        D2 --> D3["P2-07: Fairness audit runner with evaluation dataset"]
        D3 --> D4["P2-10: Global SHAP background aggregation"]
    end

    Phase 13A --> Phase 13B --> Phase 13C --> Phase 13D
```

---

## 25. Current System Boundary

### Genuinely Operational & Production-Like
- **Statutory Data Minimization:** Strict avoidance of prohibited fields across ML, backend schemas, and database tables.
- **End-to-End Scored Assessment Flow:** Applicant submission → Feature extraction → Volatility-aware LightGBM scoring → Presentation score mapping → Persisted assessment record → Human reviewer workflow.
- **Role-Based Access Control:** Strict JWT verification separating Applicant, Reviewer, and Admin clearances.
- **PostgreSQL Database Integrity:** Cascading foreign keys, check constraints, and transactional consistency.

### Prototype Limitations
- **TreeSHAP Persistence:** Explanations rely on client `sessionStorage` rather than PostgreSQL persistence.
- **Offline ML Training & Fitting:** Preprocessor is refitted from synthetic Parquet data at server startup.
- **Static Governance Displays:** Fairness audits and global SHAP aggregations are informative rather than backed by active evaluation jobs.
- **Unwired Administrative Features:** Audit logs and model version creation exist in backend code but have no UI.

---

## 26. Conclusion

The PARAKH repository possesses a fully working, mathematically sound alternative credit assessment engine. The core gap is not that ML or backend capabilities are missing, but that **rich ML outputs (TreeSHAP explanations) and backend administrative capabilities (audit logs, model registration) are decoupled from persistent storage and the user interface**.

By executing the prioritized implementation sequence above, PARAKH will transition from an impressive prototype with localized workarounds into a robust, unified, production-grade alternative lending platform.
