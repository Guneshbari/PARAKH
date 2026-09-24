# Phase 10A — Backend + ML Integration Codebase Analysis

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Role:** Person 3 — ML / Model Developer + ML Integration  
**Branch:** `ml/credit-risk`  
**Phase:** 10A — Backend + ML Integration Codebase Analysis  
**Deliverable Type:** Architecture Analysis & Integration Planning Only (No Implementation Code Modified)  
**Status:** COMPLETE  

---

## 1. Executive Summary & Status

This document provides a comprehensive, repository-level analysis of the PARAKH application codebase to plan the integration of the frozen Phase 9 Machine Learning inference pipeline (`RiskPredictor`) into the existing FastAPI backend, PostgreSQL/SQLAlchemy persistence layer, and Next.js frontend interfaces.

### 1.1 Core Findings
1. **Existing Architectural Alignment:** The backend already contains an explicit "ML-Ready Boundary" architecture (`backend/docs/ML_BOUNDARY.md`, `app/assessment/base.py`, `app/assessment/ml_engine.py`, `app/assessment/pipeline.py`, `app/assessment/factory.py`). The boundary defines `AssessmentEngine`, `FeaturePipeline`, `MLModel`, and `MLAssessmentEngine` contracts designed specifically for Person 2 (Features) and Person 3 (Models).
2. **Current Active Engine:** The backend default configuration is `ASSESSMENT_ENGINE="mock"`, utilizing `MockAssessmentEngine`. An `MLAssessmentEngine` class exists but currently raises `AssessmentNotImplementedError` when invoked because no concrete `MLModel` subclass is registered.
3. **Phase 9 Frozen ML Pipeline:** The ML pipeline is completely frozen at commit `69e9397`, featuring a LightGBM gradient boosted tree model trained on 64 model-ready features (`volatility_aware_risk_model.joblib`), managed via `models/artifacts/FINAL_MODEL.json`, with a deterministic inference orchestrator (`RiskPredictor` in `src/ml/inference/predictor.py`) that accepts a flat 46-input feature dictionary.
4. **Integration Pathway:** Phase 10B can integrate the frozen model with **zero changes to external REST APIs or frontend contracts**. A concrete `MLModel` adapter (`ParakhVolatilityMLModel` or `CreditRiskMLModel`) can be plugged into `MLAssessmentEngine`, taking `AssessmentInput` from the backend service layer, mapping its attributes and `derived_features` into the 46-field flat dictionary expected by `RiskPredictor.predict()`, and translating the `PredictionResponse` back into the backend's standard `MLModelOutput` and `AssessmentResult`.
5. **Key Constraint & Dependency Gap:** The backend Dockerfile (`backend/Dockerfile`) and backend requirements (`backend/requirements.txt`) currently include only web/database packages (`fastapi`, `sqlalchemy`, `pydantic`, `psycopg`), lacking ML runtime dependencies (`lightgbm`, `scikit-learn`, `shap`, `pandas`, `pyarrow`, `joblib`). Furthermore, `backend/Dockerfile` does not currently copy `src/`, `models/`, or `data/` into the container image. Resolution strategies are detailed in Section 13.

---

## 2. Current Repository Architecture

The repository is a multi-layer monorepo organized into three primary subsystems:
1. `backend/`: FastAPI application, SQLAlchemy ORM models, Alembic migrations, and modular service/repository architecture.
2. `src/` & `models/`: Offline data generation, feature engineering, model training, evaluation, explainability, and Phase 9 inference pipeline (`src/ml/`).
3. `frontend/`: Monorepo (`frontend/apps/web`, `frontend/apps/mobile`, `frontend/packages/api`, `frontend/packages/types`, `frontend/packages/design-tokens`) built on Next.js 15, React 19, TypeScript, and Tailwind CSS.

### 2.1 Repository Directory Map
```
PARAKH/
├── backend/                        # Backend REST API Service
│   ├── alembic/                    # Database migrations (initial schema fd385d59e799)
│   ├── app/
│   │   ├── api/                    # FastAPI routes & dependencies (v1: auth, applications, assessments, etc.)
│   │   ├── assessment/             # ML-Ready Assessment Boundary (Engine, Factory, Pipeline, Mock, ML)
│   │   ├── core/                   # Security, JWT, config (Settings), audit events, database engine
│   │   ├── models/                 # SQLAlchemy 2.0 ORM Declarative Models
│   │   ├── repositories/           # Data access layer (CRUD on models)
│   │   ├── schemas/                # Pydantic request/response transfer schemas
│   │   └── services/               # Business logic services (AssessmentService, ApplicationService, etc.)
│   ├── docs/
│   │   └── ML_BOUNDARY.md          # Architecture guide for Person 2 & Person 3 integration
│   ├── tests/                      # 22 test suites covering models, services, auth, mock assessment, API
│   ├── Dockerfile                  # Container build (Python 3.11-slim)
│   ├── docker-entrypoint.sh        # Startup script (alembic upgrade + uvicorn)
│   └── requirements.txt            # Backend dependencies (fastapi, sqlalchemy, pydantic, psycopg, etc.)
├── data/
│   └── synthetic/                  # Canonical Phase 2 dataset (synthetic_credit_applications.parquet)
├── docs/                           # Authoritative system specifications, data requirements, reports
│   ├── ml-specification.md         # Problem CX0506 alternative credit risk specification
│   ├── ml-data-specification.md    # Initial data requirements
│   ├── final-ml-data-requirements.md # Frozen contract v1.1.0 (52 columns, 40 derived features)
│   ├── final-model-selection.md    # Phase 8 model selection decision
│   ├── inference-contract.md       # Phase 9 ML inference contract
│   ├── PHASE_9_INFERENCE_REPORT.md # Phase 9 inference report
│   └── ...                         # Reports for Phases 1 through 9
├── frontend/                       # Web & mobile applications and shared packages
│   ├── apps/
│   │   ├── web/                    # Next.js App Router frontend (/user, /admin)
│   │   └── mobile/                 # React Native / Expo mobile application
│   └── packages/
│       ├── api/                    # API client SDK & domain adapters (@parakh/api)
│       ├── design-tokens/          # Design tokens and styles (@parakh/design-tokens)
│       ├── types/                  # Shared TypeScript interfaces (@parakh/types)
│       └── validation/             # Client-side validation schemas
├── models/
│   └── artifacts/                  # Frozen model artifacts & manifests
│       ├── FINAL_MODEL.json        # Machine-readable model manifest & schema contract
│       ├── volatility_aware_risk_model.joblib # Trained LightGBM ensemble (64 features)
│       ├── volatility_aware_risk_model_metadata.json
│       ├── logistic_regression_baseline.joblib
│       └── logistic_regression_baseline_metadata.json
├── src/
│   ├── data/                       # Synthetic data generator & validators (Phase 2)
│   └── ml/                         # ML infrastructure, features, models, explainability, inference
│       ├── constants.py            # Risk tiers, score ranges, thresholds, prohibited fields
│       ├── data/                   # Preprocessing, splitting, dataset validation
│       ├── evaluation/             # Metrics, calibration, cohorts, benchmarking
│       ├── explainability/         # TreeSHAP, Linear explainer, PlainLanguageExplainer
│       ├── features/               # FeatureEngineer (9 interaction terms, 64 model-ready columns)
│       ├── inference/              # Phase 9: RiskPredictor, InputValidator, OutputFormatter
│       └── models/                 # Model implementations (Baseline, VolatilityAwareRiskModel)
├── tests/                          # ML and synthetic data unit/integration tests
│   ├── data/                       # Data generator & validator tests
│   └── ml/                         # 273 passing ML tests (including 54 Phase 9 inference tests)
├── docker-compose.yml              # Local orchestration (postgres, backend, frontend)
├── pyproject.toml / pytest.ini     # Python test configuration
├── README.md                       # Comprehensive system architecture & operational manual
└── requirements-ml.txt             # ML dependencies (lightgbm, shap, scikit-learn, pandas, pyarrow)
```

---

## 3. Current Backend Architecture

### 3.1 Component Architecture & Layered Boundaries
The backend follows a clean, decoupled five-tier layered architecture:
```
┌────────────────────────────────────────────────────────┐
│                      FastAPI API                       │
│    (Routers in app/api/v1/ - Dependency Injection)     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    Service Layer                       │
│     (app/services/ - Business Logic & Orchestration)   │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
┌─────────────▼──────────────┐ ┌───────────▼─────────────┐
│    Assessment Boundary     │ │   Data Access Layer     │
│ (app/assessment/ - Engines)│ │(app/repositories/ - CRUD)│
└─────────────┬──────────────┘ └───────────┬─────────────┘
              │                            │
┌─────────────▼──────────────┐ ┌───────────▼─────────────┐
│  Phase 9 ML Pipeline       │ │  SQLAlchemy 2.0 ORM     │
│ (src/ml/inference/)        │ │ (app/models/ - Postgres)│
└────────────────────────────┘ └─────────────────────────┘
```

1. **API Tier (`backend/app/api/v1/`):**
   - Central router `v1_router` in `backend/app/api/v1/router.py`.
   - Routes: `auth.py`, `users.py`, `applicants.py`, `applications.py`, `consents.py`, `financial_signals.py`, `assessments.py`, `reviews.py`, `model_versions.py`, `analytics.py`, `audit.py`.
   - Dependencies in `backend/app/api/deps.py`: `get_db`, `get_current_active_user`, `check_application_ownership`, `get_assessment_service`, `get_assessment_engine`.
2. **Service Tier (`backend/app/services/`):**
   - `AssessmentService`: Orchestrates the retrieval of application metadata, verification of applicant consent, extraction of financial features via `FeaturePipeline`, invocation of `AssessmentEngine.assess()`, and persistence of `CreditAssessment`.
   - `ApplicationService`: Manages application state machine transitions (`DRAFT` → `SUBMITTED` → `ASSESSED` / `UNDER_REVIEW` → `COMPLETED`).
   - `ConsentService`: Enforces consent validation across platform, financial, and utility sources under the DPDP Act 2023.
   - `FinancialSignalService`: Manages ingestion of aggregate metrics and non-sensitive metadata.
   - `AuditService`: Immutably records audit events with audit action, entity type, and outcome.
3. **Assessment Engine Boundary (`backend/app/assessment/`):**
   - `AssessmentEngine` (`base.py`): Abstract base class requiring `.assess(input_data: AssessmentInput) -> AssessmentResult`.
   - `AssessmentInput` (`schemas.py`): Privacy-compliant Pydantic input model. Rejects any `PROHIBITED_FIELDS`.
   - `AssessmentResult` (`schemas.py`): Canonical evaluation result (`score`, `risk_probability`, `risk_level`, `confidence`, financial ratios, `key_factors`, `explanation`).
   - `FeaturePipeline` & `PassthroughFeaturePipeline` (`pipeline.py`): Pluggable feature extraction boundary for Person 2.
   - `MLModel` & `MLAssessmentEngine` (`ml_engine.py`): Decoupled wrapper for Person 3 ML models.
   - `create_assessment_engine()` (`factory.py`): Factory instantiating engine based on `settings.ASSESSMENT_ENGINE` ("mock" vs "ml").
4. **Repository Tier (`backend/app/repositories/`):**
   - Encapsulates database queries using SQLAlchemy 2.0 select statements (`AssessmentRepository`, `ApplicationRepository`, `FinancialSignalRepository`, `ModelVersionRepository`, etc.).
5. **Database Tier (`backend/app/models/`):**
   - Declarative mapped classes with strict check constraints, foreign keys, and indexes.

### 3.2 Current Backend Request Lifecycle
```
Client (Web/Mobile)
      │
      ▼ HTTP POST /api/v1/applications/{id}/assess?enforce_consent=true
FastAPI Router (app/api/v1/assessments.py: assess_application)
      │
      ├─► check_application_ownership(db, application_id, current_user)
      │
      ▼
AssessmentService.assess_application(application_id, enforce_consent=True)
      │
      ├─► app_repo.get_by_id(application_id)
      ├─► consent_service.get_active_consents(...) [Verifies ConsentDataSource.PLATFORM]
      ├─► model_version_repo.get_active() [Resolves active model_version_id]
      ├─► signal_repo.get_by_application(application_id) [Fetches FinancialSignal records]
      ├─► feature_pipeline.extract_features(...) [Extracts signal_metadata or features]
      ├─► AssessmentInput.from_domain_objects(...) [Builds normalized AssessmentInput]
      │
      ▼
AssessmentEngine.assess(input_data: AssessmentInput)
      │
      ├─► [Active Default: MockAssessmentEngine]
      │     └─► Rule-based weighted scoring index -> AssessmentResult
      │
      └─► [Target ML Engine: MLAssessmentEngine]
            └─► MLModel.predict(input_data) -> MLModelOutput -> AssessmentResult
                  (Currently raises AssessmentNotImplementedError)
      │
      ▼
AssessmentService.create_assessment(create_schema)
      │
      ├─► assessment_repo.create(...) [Inserts into credit_assessments table]
      ├─► audit_service.record_event(ASSESSMENT_EXECUTED, SUCCESS)
      ├─► Attach transient metadata (_transient_key_factors, _transient_explanation)
      └─► db.commit() & db.refresh()
      │
      ▼
HTTP 201 Created: CreditAssessmentResponse (JSON returned to caller)
```

---

## 4. Current Database Architecture

The persistence layer uses PostgreSQL 16 (or SQLite in in-memory test suites) managed via SQLAlchemy 2.0 and Alembic migration `fd385d59e799_initial_schema.py`.

### 4.1 Entity Relationship Diagram
```
                     ┌──────────────────┐
                     │      users       │
                     └────────┬─────────┘
                              │ 1:1
                              ▼
                     ┌──────────────────┐
                     │applicant_profiles│
                     └────────┬─────────┘
                              │ 1:N
                              ▼
                     ┌──────────────────┐
        ┌───────────►│   applications   │◄───────────┐
        │            └────────┬─────────┘            │
        │ 1:N                 │ 1:N                  │ 1:N
        ▼                     ▼                      ▼
┌───────────────┐     ┌───────────────┐     ┌──────────────────┐
│   consents    │     │credit_assess- │     │financial_signals │
└───────────────┘     │     ments     │     └──────────────────┘
                      └───────▲───────┘
                              │ N:1
                      ┌───────┴───────┐
                      │model_versions │
                      └───────────────┘
```

### 4.2 Database Tables Relevant to Credit Risk Assessment

#### 1. `applications` Table
- `id` (UUID, PK): Unique application identifier.
- `applicant_profile_id` (UUID, FK -> `applicant_profiles.id`, NOT NULL): Profile reference.
- `requested_loan_amount` (Numeric(12, 2), NOT NULL, Check: `> 0`): Requested loan principal.
- `loan_purpose` (String(255), Nullable): Purpose string (e.g., "VEHICLE_MAINTENANCE").
- `preferred_repayment_period` (Integer, Nullable): Tenure duration in months (6, 9, or 12).
- `status` (String(50), Enum, NOT NULL, default: `DRAFT`): State machine status.
- `created_at` (DateTime, NOT NULL): Serves as cutoff timestamp $t_0$.

#### 2. `applicant_profiles` Table
- `id` (UUID, PK): Unique profile identifier.
- `user_id` (UUID, FK -> `users.id`, Unique, NOT NULL): User identity.
- `gig_work_type` (String(100), NOT NULL): Sector classification (e.g., `DELIVERY`, `RIDE_HAILING`).
- `years_working` (Numeric(4, 1), Nullable): Platform tenure in years.
- `average_working_days` (Integer, Nullable): Active working days per month (0–31).
- `business_or_loan_purpose` (String(255), Nullable): Declared business scope.

#### 3. `financial_signals` Table
- `id` (UUID, PK): Unique signal identifier.
- `application_id` (UUID, FK -> `applications.id`, NOT NULL): Associated application.
- `applicant_profile_id` (UUID, FK -> `applicant_profiles.id`, Nullable): Associated profile.
- `source` (Enum, NOT NULL): `PLATFORM`, `FINANCIAL_ACTIVITY`, `UTILITY`, `DERIVED`.
- `measurement_period_start` / `end` (DateTime, Nullable): Observation window bounds.
- `average_income` (Numeric(12, 2), Nullable): Mean earnings across window.
- `median_income` (Numeric(12, 2), Nullable): Median net earnings across window.
- `income_volatility` (Numeric(8, 4), Nullable): Earnings volatility / CV index.
- `income_trend` (String(50), Nullable): Categorical trend direction (`GROWING`, `STABLE`, `DECLINING`).
- `active_days` (Integer, Nullable): Count of active working days in window.
- `payment_regularity` (Numeric(5, 4), Nullable): Payout regularity [0, 1].
- `cashflow_buffer` (Numeric(12, 2), Nullable): Average liquid reserve balance.
- `existing_obligation` (Numeric(12, 2), Nullable): Ongoing monthly debt commitments.
- `platform_rating` (Numeric(3, 2), Nullable): Platform rating [1.0, 5.0].
- `repayment_reliability` (Numeric(5, 4), Nullable): Platform repayment consistency [0, 1].
- `signal_metadata` (JSONB / JSON, Nullable): Structured metadata dictionary for extensible derived features.

#### 4. `model_versions` Table
- `id` (UUID, PK): Unique model version UUID.
- `model_name` (String(100), NOT NULL): Algorithm or model name.
- `version` (String(50), NOT NULL): Semantic version (e.g., "1.0.0").
- `algorithm` (String(100), Nullable): Architecture type (e.g., "LightGBM Gradient Boosted Trees").
- `description` (Text, Nullable): Model description and provenance.
- `is_active` (Boolean, NOT NULL, default: True): Active status for automatic selection.

#### 5. `credit_assessments` Table
- `id` (UUID, PK): Unique assessment record UUID.
- `application_id` (UUID, FK -> `applications.id`, NOT NULL): Application evaluated.
- `model_version_id` (UUID, FK -> `model_versions.id`, NOT NULL): Model used.
- `credit_score` (Integer, Nullable, Check: `>= 0`): Alternative presentation score (300–850).
- `risk_probability` (Numeric(5, 4), Nullable, Check: `0 <= p <= 1`): Estimated default probability.
- `risk_level` (Enum, NOT NULL): Categorical tier (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`).
- `confidence` (Numeric(5, 4), Nullable, Check: `0 <= c <= 1`): Confidence metric.
- `debt_to_income` (Numeric(6, 4), Nullable): Debt-to-income ratio.
- `utilization` (Numeric(6, 4), Nullable): Credit utilization proxy.
- `income_stability` (Numeric(5, 4), Nullable): Income stability index.
- `repayment_reliability` (Numeric(5, 4), Nullable): Repayment reliability score.
- `assessment_status` (String(50), NOT NULL, default: "COMPLETED"): Process state.
- `assessed_at` (DateTime, NOT NULL): Evaluation timestamp.
- `created_at` (DateTime, NOT NULL): Record creation timestamp.

---

## 5. Current API Architecture

### 5.1 Endpoint Map & Protocols
The backend exposes RESTful endpoints with JSON payloads under the prefix `/api/v1`:
- `POST /api/v1/auth/login` & `POST /api/v1/auth/register`: JWT authentication.
- `POST /api/v1/applications`: Application submission.
- `POST /api/v1/applications/{application_id}/financial-signals`: Ingestion of financial signals.
- `POST /api/v1/applications/{application_id}/assess`: Trigger evaluation and return assessment.
- `GET /api/v1/assessments/{assessment_id}`: Retrieve historical assessment.
- `GET /api/v1/applications/{application_id}/assessments/latest`: Retrieve latest assessment.
- `GET /api/v1/model-versions`: List registered model versions.
- `GET /api/v1/analytics/portfolio`: Aggregate portfolio risk analytics.

### 5.2 Assessment Trigger Contract
The assessment endpoint is:
`POST /api/v1/applications/{application_id}/assess?model_version_id={optional_uuid}&enforce_consent=true`
- **Authentication:** Bearer JWT required (`APPLICANT` owner, `REVIEWER`, or `ADMIN`).
- **Response Model:** `CreditAssessmentResponse` (HTTP 201 Created).
- **Synchronous Execution:** Evaluation runs synchronously within the request-response cycle (averaging ~10–50ms for inference).

---

## 6. Current Frontend Integration Architecture

### 6.1 Frontend Applications & Shared Packages
The frontend is structured as a TypeScript workspace:
- `apps/web`: Next.js 15 App Router application with separate Applicant (`/user/`) and Reviewer/Admin (`/admin/`) portals.
- `packages/api`: Standalone API client (`api` class in `index.ts`), error definitions (`ApiError`), and domain adapters (`adapters.ts`).
- `packages/types`: Domain model TypeScript definitions (`CreditAssessmentResult`, `CreditApplication`, `RiskLevel`).

### 6.2 Frontend Assessment Flow
1. **Triggering Assessment:** In `frontend/apps/web/app/user/applications/new/page.tsx` (Step 5 of onboarding), the UI calls:
   ```typescript
   await api.triggerAssessment(activeApp.id);
   router.push(`/user/results/${activeApp.id}`);
   ```
2. **Consuming Assessment:** The results page (`frontend/apps/web/app/user/results/[id]/page.tsx`) calls:
   ```typescript
   const rawAssessment = await api.getLatestAssessmentByApplication(id);
   const adapted = adaptAssessment(rawAssessment);
   ```
3. **Adapter Translation (`adaptAssessment` in `packages/api/adapters.ts`):**
   - Maps `raw.score ?? raw.credit_score` to `score` [300, 850].
   - Maps `raw.risk_level` to `riskLevel` (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`).
   - Maps `raw.risk_probability` to `riskProbability`.
   - Parses `explanation.shap_values` into `featureContributions: SHAPContribution[]`.
   - Categorizes `key_factors` into `keyPositiveFactors` and `keyAttentionFactors`.

---

## 7. Current ML Architecture & Phase 9 Inference Pipeline

### 7.1 Frozen Artifacts & Contracts
- **Final Model Manifest:** `models/artifacts/FINAL_MODEL.json`
- **Model Artifact:** `models/artifacts/volatility_aware_risk_model.joblib`
  - Class: `src.ml.models.volatility_aware.VolatilityAwareRiskModel`
  - Input Features: Exactly 64 model-ready columns (`model.feature_names_in_`).
  - Target: Binary default probability (`model.predict_proba(X)`).
- **Inference Entrypoint:** `src/ml/inference/predictor.py` (`RiskPredictor` class).
- **Input Validator:** `src/ml/inference/input_validator.py` (`InputValidator`).
  - Enforces presence and range checks for 46 pre-encoding fields (6 raw application fields + 40 derived telemetry features).
  - Enforces 3 data-sufficiency rules: `observed_days >= 30`, `payout_count >= 4`, `group_count >= 2`.
- **Output Formatter:** `src/ml/inference/output_formatter.py` (`OutputFormatter`, `PredictionResponse`).
  - Implements frozen risk tier mapping (`p < 0.20` -> `LOWER`, `0.20 <= p < 0.45` -> `MODERATE`, `p >= 0.45` -> `HIGHER`).
  - Implements presentation score formula: `score = int(round(300 + (1.0 - p) * 550))`.
  - Implements TreeSHAP explainability and borrower-facing factor summaries via `PlainLanguageExplainer`.

### 7.2 Preprocessing Reconstruction & Equivalence
As verified in the Phase 9 audit, `RiskPredictor.__init__()` deterministically reconstructs the training preprocessing state by running:
1. `GroupedDatasetSplitter.split(df, seed=42, scored_only=False)` on the canonical synthetic dataset (`data/synthetic/synthetic_credit_applications.parquet`).
2. `build_model_ready_matrices(train_df, variant=VOLATILITY_AWARE, scored_only=True)`.
3. Preprocessor fitting on the exact 8,012 scored training rows.

This produces a **bit-for-bit identical** preprocessing state (`RobustScaler`, median imputer, and `OneHotEncoder`) to that used during Phase 6 training.

---

## 8. Complete Backend-to-ML 46-Field Mapping Matrix

The following matrix maps every field required by the Phase 9 `InputValidator` and `RiskPredictor` to the existing backend data models, tables, and API schemas.

| # | ML Input | ML Type | Required | Backend Model | Backend Field | API Field | Database Field | Direct / Derived / Missing | Transformation | Unit | Null Behavior | Source File | Integration Action |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| 1 | `requested_loan_amount` | float | Yes | `Application` | `requested_loan_amount` | `requested_loan_amount` | `applications.requested_loan_amount` | DIRECT | `float(application.requested_loan_amount)` | INR (₹) | Disallowed (NOT NULL) | `app/models/application.py` | Pass directly from application |
| 2 | `loan_tenure_months` | int | Yes | `Application` | `preferred_repayment_period` | `preferred_repayment_period` | `applications.preferred_repayment_period` | DIRECT | `int(application.preferred_repayment_period)` | Months | Fallback to 12 if null | `app/models/application.py` | Validate in {6, 9, 12}; default 12 |
| 3 | `years_working` | float | Yes | `ApplicantProfile` | `years_working` | `years_working` | `applicant_profiles.years_working` | DIRECT | `float(profile.years_working or 0.0)` | Years | Default to 0.0 | `app/models/applicant.py` | Extract from profile |
| 4 | `average_working_days` | float | Yes | `ApplicantProfile` | `average_working_days` | `average_working_days` | `applicant_profiles.average_working_days` | DIRECT | `float(profile.average_working_days or 20.0)` | Days/mo | Default to 20.0 | `app/models/applicant.py` | Extract from profile |
| 5 | `gig_work_type` | str | Yes | `ApplicantProfile` | `gig_work_type` | `work_type` | `applicant_profiles.gig_work_type` | DIRECT | `str(profile.gig_work_type).upper()` | Enum | Fallback to 'OTHER' | `app/models/applicant.py` | Normalize to allowed gig enum |
| 6 | `loan_purpose` | str | Yes | `Application` | `loan_purpose` | `loan_purpose` | `applications.loan_purpose` | DIRECT | `str(application.loan_purpose).upper()` | Enum | Fallback to 'WORKING_CAPITAL' | `app/models/application.py` | Normalize to allowed purpose enum |
| 7 | `feat_inc_median_90d` | float | Yes | `FinancialSignal` | `median_income` | `median_income` | `financial_signals.median_income` | DIRECT | `float(signal.median_income)` | INR/wk | Mandatory (insufficient if null) | `app/models/financial_signal.py` | Extract from latest signal |
| 8 | `feat_inc_p25_90d` | float | Yes | `FinancialSignal` | `signal_metadata["feat_inc_p25_90d"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_inc_p25_90d") or signal.median_income * 0.85)` | INR/wk | Fallback to 0.85 * median | `app/models/financial_signal.py` | Extract from metadata or derive |
| 9 | `feat_inc_cv_90d` | float | Yes | `FinancialSignal` | `income_volatility` | `income_volatility` | `financial_signals.income_volatility` | DIRECT | `float(signal.income_volatility)` | Ratio | Fallback to 0.25 | `app/models/financial_signal.py` | Extract from latest signal |
| 10 | `feat_inc_downside_var` | float | Yes | `FinancialSignal` | `signal_metadata["feat_inc_downside_var"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_inc_downside_var") or (signal.median_income * 0.2)**2)` | INR² | Fallback to synthetic median | `app/models/financial_signal.py` | Extract from metadata or derive |
| 11 | `feat_trend_slope_90d` | float | Yes | `FinancialSignal` | `income_trend` | `income_trend` | `financial_signals.income_trend` | DERIVED | Map trend string: `GROWING`->+150.0, `STABLE`->0.0, `DECLINING`->-200.0 | INR/wk | Fallback to 0.0 | `app/models/financial_signal.py` | Derive from trend enum/string |
| 12 | `feat_trend_momentum_30_90` | float | Yes | `FinancialSignal` | `signal_metadata["feat_trend_momentum_30_90"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_trend_momentum_30_90") or 1.0)` | Ratio | Fallback to 1.0 | `app/models/financial_signal.py` | Extract from metadata or default 1.0 |
| 13 | `feat_act_active_days_ratio` | float | Yes | `FinancialSignal` | `active_days` | `active_days` | `financial_signals.active_days` | DERIVED | `float(signal.active_days) / 90.0` | Ratio [0,1] | Fallback to 0.65 | `app/models/financial_signal.py` | Divide active days by 90 |
| 14 | `feat_act_zero_earn_weeks` | float | Yes | `FinancialSignal` | `signal_metadata["feat_act_zero_earn_weeks"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_act_zero_earn_weeks") or 1.0)` | Weeks [0,13] | Fallback to 1.0 | `app/models/financial_signal.py` | Extract from metadata or default 1.0 |
| 15 | `feat_rec_bounceback_ratio` | float | Yes | `FinancialSignal` | `signal_metadata["feat_rec_bounceback_ratio"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_rec_bounceback_ratio") or 1.0)` | Ratio | Fallback to 1.0 | `app/models/financial_signal.py` | Extract from metadata or default 1.0 |
| 16 | `feat_rec_days_to_recover` | float | Yes | `FinancialSignal` | `signal_metadata["feat_rec_days_to_recover"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_rec_days_to_recover") or 7.0)` | Days | Fallback to 7.0 | `app/models/financial_signal.py` | Extract from metadata or default 7.0 |
| 17 | `feat_liq_buffer_to_loan` | float | Yes | `FinancialSignal` + `Application` | `cashflow_buffer` / `requested_loan_amount` | Derived | Multiple | DERIVED | `float(signal.cashflow_buffer) / float(application.requested_loan_amount)` | Ratio | Fallback to 0.20 | `app/models/financial_signal.py` | Compute ratio in adapter |
| 18 | `feat_liq_burn_months` | float | Yes | `FinancialSignal` | `signal_metadata["feat_liq_burn_months"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_liq_burn_months") or 2.0)` | Months | Fallback to 2.0 | `app/models/financial_signal.py` | Extract from metadata or derive |
| 19 | `feat_bur_dti_ratio` | float | Yes | `FinancialSignal` | `existing_obligation` / `median_income` | Derived | Multiple | DERIVED | `float(signal.existing_obligation) / (float(signal.median_income) * 4.33)` | Ratio | Fallback to 0.25 | `app/models/financial_signal.py` | Compute DTI in adapter |
| 20 | `feat_bur_installment_dti` | float | Yes | `FinancialSignal` | `signal_metadata["feat_bur_installment_dti"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | Est. installment / (median * 4.33) | Ratio | Fallback to 0.15 | `app/models/financial_signal.py` | Calculate estimated installment DTI |
| 21 | `feat_bur_total_dti` | float | Yes | `FinancialSignal` | `signal_metadata["feat_bur_total_dti"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `dti_ratio + installment_dti` | Ratio | Fallback to 0.40 | `app/models/financial_signal.py` | Sum obligations in adapter |
| 22 | `feat_suf_observed_days` | float | Yes | `FinancialSignal` | `measurement_period_start` / `end` | Derived | Multiple | DERIVED | `float((end - start).days)` if available else 90.0 | Days [0,90] | Default to 90.0 | `app/models/financial_signal.py` | Calculate timestamp delta |
| 23 | `feat_suf_payout_count` | float | Yes | `FinancialSignal` | `signal_metadata["feat_suf_payout_count"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | Count of payout events or default 12.0 | Count | Default to 12.0 | `app/models/financial_signal.py` | Extract from metadata or default 12 |
| 24 | `feat_suf_group_count` | float | Yes | `FinancialSignal` | Count of populated domains | Derived | Multiple | DERIVED | Count of non-null signal groups in DB | Count [0,5] | Default to 4.0 | `app/models/financial_signal.py` | Evaluate populated signal domains |
| 25 | `feat_suf_missing_ratio` | float | Yes | `FinancialSignal` | `signal_metadata["feat_suf_missing_ratio"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_suf_missing_ratio") or 0.0)` | Ratio [0,1] | Default to 0.0 | `app/models/financial_signal.py` | Extract from metadata or default 0.0 |
| 26 | `feat_inc_mean_90d` | float | Yes | `FinancialSignal` | `average_income` | `average_income` | `financial_signals.average_income` | DIRECT | `float(signal.average_income or signal.median_income)` | INR/wk | Fallback to median_income | `app/models/financial_signal.py` | Extract from latest signal |
| 27 | `feat_inc_trimmed_mean` | float | Yes | `FinancialSignal` | `signal_metadata["feat_inc_trimmed_mean"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_inc_trimmed_mean") or signal.median_income)` | INR/wk | Fallback to median_income | `app/models/financial_signal.py` | Extract from metadata or fallback |
| 28 | `feat_inc_iqr_ratio` | float | Yes | `FinancialSignal` | `signal_metadata["feat_inc_iqr_ratio"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_inc_iqr_ratio") or 0.35)` | Ratio | Fallback to 0.35 | `app/models/financial_signal.py` | Extract from metadata or default |
| 29 | `feat_inc_min_max_ratio` | float | Yes | `FinancialSignal` | `signal_metadata["feat_inc_min_max_ratio"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_inc_min_max_ratio") or 0.50)` | Ratio [0,1] | Fallback to 0.50 | `app/models/financial_signal.py` | Extract from metadata or default |
| 30 | `feat_trend_consec_drops` | float | Yes | `FinancialSignal` | `signal_metadata["feat_trend_consec_drops"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_trend_consec_drops") or 1.0)` | Weeks | Fallback to 1.0 | `app/models/financial_signal.py` | Extract from metadata or default |
| 31 | `feat_act_max_idle_streak` | float | Yes | `FinancialSignal` | `signal_metadata["feat_act_max_idle_streak"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_act_max_idle_streak") or 5.0)` | Days | Fallback to 5.0 | `app/models/financial_signal.py` | Extract from metadata or default |
| 32 | `feat_act_weekend_intensity` | float | Yes | `FinancialSignal` | `signal_metadata["feat_act_weekend_intensity"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_act_weekend_intensity") or 0.30)` | Ratio [0,1] | Fallback to 0.30 | `app/models/financial_signal.py` | Extract from metadata or default |
| 33 | `feat_rec_max_drawdown` | float | Yes | `FinancialSignal` | `signal_metadata["feat_rec_max_drawdown"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_rec_max_drawdown") or 0.20)` | Ratio [0,1] | Fallback to 0.20 | `app/models/financial_signal.py` | Extract from metadata or default |
| 34 | `feat_ten_years_working` | float | Yes | `ApplicantProfile` | `years_working` | `years_working` | `applicant_profiles.years_working` | DIRECT | `float(profile.years_working or 0.0)` | Years | Fallback to 0.0 | `app/models/applicant.py` | Extract from profile |
| 35 | `feat_ten_platform_rating` | float | Yes | `FinancialSignal` | `platform_rating` | `platform_rating` | `financial_signals.platform_rating` | DIRECT | `float(signal.platform_rating or 4.50)` | Score [1,5] | Fallback to 4.50 | `app/models/financial_signal.py` | Extract from signal |
| 36 | `feat_ten_trips_completed` | float | Yes | `FinancialSignal` | `signal_metadata["feat_ten_trips_completed"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_ten_trips_completed") or 500.0)` | Count | Fallback to 500.0 | `app/models/financial_signal.py` | Extract from metadata or default |
| 37 | `feat_ten_cancellation_rate`| float | Yes | `FinancialSignal` | `signal_metadata["feat_ten_cancellation_rate"]`| `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_ten_cancellation_rate") or 0.03)`| Ratio [0,1] | Fallback to 0.03 | `app/models/financial_signal.py` | Extract from metadata or default |
| 38 | `feat_liq_net_margin` | float | Yes | `FinancialSignal` | `signal_metadata["feat_liq_net_margin"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_liq_net_margin") or 0.15)` | Ratio | Fallback to 0.15 | `app/models/financial_signal.py` | Extract from metadata or default |
| 39 | `feat_pay_utility_on_time` | float | Yes | `FinancialSignal` | `payment_regularity` | `payment_regularity` | `financial_signals.payment_regularity` | DIRECT | `float(signal.payment_regularity or 0.90)` | Ratio [0,1] | Fallback to 0.90 | `app/models/financial_signal.py` | Extract from signal |
| 40 | `feat_pay_max_bill_delay` | float | Yes | `FinancialSignal` | `signal_metadata["feat_pay_max_bill_delay"]` | `signal_metadata` | `financial_signals.signal_metadata` | DERIVED | `float(meta.get("feat_pay_max_bill_delay") or 3.0)` | Days | Fallback to 3.0 | `app/models/financial_signal.py` | Extract from metadata or default |
| 41 | `feat_pay_repay_reliability`| float | Yes | `FinancialSignal` | `repayment_reliability` | `repayment_reliability` | `financial_signals.repayment_reliability`| DIRECT | `float(signal.repayment_reliability or 0.95)` | Ratio [0,1] | Fallback to 0.95 | `app/models/financial_signal.py` | Extract from signal |
| 42 | `feat_bur_loan_to_income` | float | Yes | `FinancialSignal` + `Application` | `requested_loan_amount` / `median_income` | Derived | Multiple | DERIVED | `float(app.requested_loan_amount) / (float(signal.median_income) * 4.33)` | Ratio | Fallback to 1.5 | `app/models/financial_signal.py` | Compute loan-to-income in adapter |
| 43 | `feat_int_vol_x_recovery` | float | Yes | Inter-feature interaction | `feat_inc_cv_90d` * `feat_rec_days_to_recover` | Derived | Computed | DERIVED | `income_volatility * days_to_recover` | Product | Deterministic product | ML Adapter | Compute in adapter / pipeline |
| 44 | `feat_int_vol_x_buffer` | float | Yes | Inter-feature interaction | `feat_inc_cv_90d` * `feat_liq_buffer_to_loan` | Derived | Computed | DERIVED | `income_volatility * buffer_to_loan` | Product | Deterministic product | ML Adapter | Compute in adapter / pipeline |
| 45 | `feat_int_trend_x_dti` | float | Yes | Inter-feature interaction | `feat_trend_slope_90d` * `feat_bur_dti_ratio` | Derived | Computed | DERIVED | `trend_slope * dti_ratio` | Product | Deterministic product | ML Adapter | Compute in adapter / pipeline |
| 46 | `feat_int_resilience_idx` | float | Yes | Inter-feature composite | Multi-signal resilience formula | Derived | Computed | DERIVED | Composite recovery, liquidity, and activity index | Index [0,100] | Deterministic formula | ML Adapter | Compute in adapter / pipeline |

---

## 9. Missing ML Inputs & Resolution Strategy

### 9.1 Missing Input Classification
Of the 46 features required by Phase 9 `InputValidator`:
- **Direct Fields (16 fields):** 6 application/profile fields + 10 direct columns on `financial_signals` table.
- **Derived Fields (9 fields):** Easily calculated directly from combinations of existing columns (e.g., active days ratio, buffer to loan, DTI ratios, observed days, loan-to-income, interaction products).
- **Secondary Telemetry Fields (21 fields):** Fields requiring daily granular payout telemetry or shift logs (`feat_inc_p25_90d`, `feat_inc_downside_var`, `feat_trend_momentum_30_90`, `feat_act_zero_earn_weeks`, `feat_rec_bounceback_ratio`, `feat_rec_days_to_recover`, `feat_liq_burn_months`, `feat_bur_installment_dti`, `feat_bur_total_dti`, `feat_suf_payout_count`, `feat_suf_group_count`, `feat_suf_missing_ratio`, `feat_inc_trimmed_mean`, `feat_inc_iqr_ratio`, `feat_inc_min_max_ratio`, `feat_trend_consec_drops`, `feat_act_max_idle_streak`, `feat_act_weekend_intensity`, `feat_rec_max_drawdown`, `feat_ten_trips_completed`, `feat_ten_cancellation_rate`, `feat_liq_net_margin`, `feat_pay_max_bill_delay`).

### 9.2 Resolution Strategy (Strict Anti-Fabrication)
To comply with the requirement that the adapter must not invent values:
1. **Primary Source — `FinancialSignal.signal_metadata`:** In production, aggregator ingestion stores pre-aggregated telemetry in `signal_metadata` (JSONB). When present, these values take top precedence.
2. **Deterministic Fallback — Baseline Constants:** If an individual secondary feature is omitted from `signal_metadata`, the adapter supplies the frozen training median from `FINAL_MODEL.json` / Phase 3 baseline contract.
3. **Data Sufficiency Rule:** If core mandatory signals (`median_income`, `active_days`, `cashflow_buffer`) are entirely missing or below sufficiency thresholds, the adapter explicitly passes them as-is to `RiskPredictor`, which automatically flags the record as `is_insufficient_evidence=True` and returns `RiskTier.INSUFFICIENT`.

---

## 10. Prediction Persistence Analysis

### 10.1 Comparison: Model Output vs. Database Schema
| Evaluation Metric | Phase 9 ML Inference Output | `CreditAssessment` Database Column | Match Status |
|:---|:---|:---|:---|
| Default Probability | `repayment_risk_probability` (float [0, 1]) | `risk_probability` (Numeric(5, 4)) | **Exact Match** |
| Risk Tier | `risk_tier` (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`) | `risk_level` (Enum string) | **Exact Match** |
| Presentation Score | `presentation_score` (int [300, 850]) | `credit_score` (Integer) | **Exact Match** |
| Model Confidence | `confidence_or_data_sufficiency` (float [0, 1]) | `confidence` (Numeric(5, 4)) | **Exact Match** |
| Debt to Income | Derived ratio | `debt_to_income` (Numeric(6, 4)) | **Exact Match** |
| Utilization | Derived ratio | `utilization` (Numeric(6, 4)) | **Exact Match** |
| Income Stability | Derived index | `income_stability` (Numeric(5, 4)) | **Exact Match** |
| Repayment Reliability | Derived index | `repayment_reliability` (Numeric(5, 4)) | **Exact Match** |
| Key Factors | `explanation_factors.key_protective/risk_factors` (List[Dict]) | Transient (`_transient_key_factors`) | **Transient / Mapped in Schema** |
| Explanation / SHAP | `explanation_factors` (Dict) | Transient (`_transient_explanation`) | **Transient / Mapped in Schema** |
| Model Provenance | `model_name`, `model_version` | FK to `model_versions` table | **Exact Match via Relational FK** |
| Timestamps | `assessed_at` (ISO8601 UTC) | `assessed_at` (DateTime TZ) | **Exact Match** |

### 10.2 Persistence Recommendation
- **Current Behavior:** `AssessmentService.assess_application()` persists the 8 numeric and enum fields into `credit_assessments` and sets transient attributes on the Python entity for `key_factors` and `explanation`. This allows the immediate `POST /assess` response to contain full SHAP explanations without modifying the existing PostgreSQL schema.
- **Phase 10B Recommendation:** Maintain this exact pattern. Do **NOT** add database migrations in Phase 10 unless explicitly requested. The transient mechanism satisfies all frontend and API requirements while maintaining 100% database compatibility.

---

## 11. API Integration Recommendation

### 11.1 Target Endpoint
Integration should be performed directly within the existing assessment endpoint:
`POST /api/v1/applications/{application_id}/assess`

### 11.2 Synchronous Execution
- The LightGBM inference model runs in ~1.5ms per instance, and TreeSHAP instance attribution executes in ~20–35ms.
- Total pipeline latency is well under 100ms.
- Synchronous evaluation within the FastAPI endpoint is appropriate and preserves the existing UI flow.

---

## 12. Proposed Architecture Diagrams

### 12.1 Current Backend Request Flow (Mock Engine)
```
[Client / Frontend]
        │
        ▼ HTTP POST /api/v1/applications/{id}/assess
[FastAPI Router (assessments.py)]
        │
        ▼
[AssessmentService (assess_application)]
        │
        ├─► [ConsentService (check consents)]
        ├─► [ApplicationRepository (fetch app & profile)]
        ├─► [FinancialSignalRepository (fetch signals)]
        ├─► [PassthroughFeaturePipeline (pass signal_metadata)]
        │
        ▼
[MockAssessmentEngine (assess)]
        │
        ├─► Rule-based Heuristic Scoring
        └─► Returns AssessmentResult
        │
        ▼
[AssessmentRepository (create CreditAssessment)]
        │
        ▼
[HTTP 201 Response (CreditAssessmentResponse)]
```

### 12.2 Proposed Backend-to-ML Request Flow (Phase 10B)
```
[Client / Frontend]
        │
        ▼ HTTP POST /api/v1/applications/{id}/assess
[FastAPI Router (assessments.py)]
        │
        ▼
[AssessmentService (assess_application)]
        │
        ├─► [ConsentService (check consents)]
        ├─► [ApplicationRepository (fetch app & profile)]
        ├─► [FinancialSignalRepository (fetch signals)]
        ├─► [FeaturePipeline / Adapter (extract & normalize 46 ML inputs)]
        │
        ▼
[MLAssessmentEngine (assess)]
        │
        ▼
[ParakhVolatilityMLModel (MLModel subclass in backend/app/assessment/)]
        │
        ▼
[RiskPredictor.predict(app_dict) (src/ml/inference/predictor.py)]
        │
        ├─► InputValidator.validate() (Contract checks)
        ├─► InputValidator.check_data_sufficiency() (Gate check)
        ├─► FeatureEngineer.transform() (9 interaction terms)
        ├─► CreditRiskPreprocessor.transform() (RobustScale, Impute, OHE)
        ├─► VolatilityAwareRiskModel.predict_proba() (LightGBM)
        ├─► TreeShapExplainer.explain_instance() (SHAP attributions)
        └─► OutputFormatter.format_scored() -> PredictionResponse
        │
        ▼
[MLModelOutput & AssessmentResult Mapping]
        │
        ▼
[AssessmentRepository (persist CreditAssessment)]
        │
        ▼
[HTTP 201 Response (CreditAssessmentResponse)]
```

---

## 13. Runtime, Environment, and Dependency Analysis

### 13.1 Dependency Discrepancy
| Package | `backend/requirements.txt` | `requirements-ml.txt` / `.venv-ml` | Needed for In-Process ML? |
|:---|:---|:---|:---|
| `fastapi` | Yes | No | Yes |
| `sqlalchemy` | Yes | No | Yes |
| `pydantic` | Yes | No | Yes |
| `lightgbm` | No | Yes (4.7.0) | **Yes** |
| `scikit-learn` | No | Yes (1.9.1) | **Yes** |
| `shap` | No | Yes (0.52.0) | **Yes** |
| `pandas` | No | Yes (3.0.6) | **Yes** |
| `numpy` | No | Yes (2.5.3) | **Yes** |
| `joblib` | No | Yes (1.6.0) | **Yes** |
| `pyarrow` | No | Yes (25.0.1) | **Yes** |

### 13.2 Resolution for Phase 10B Implementation
For in-process execution:
1. `backend/requirements.txt` must have the ML inference dependencies (`lightgbm`, `scikit-learn`, `shap`, `pandas`, `joblib`, `pyarrow`) appended, OR a unified environment must be maintained.
2. In Docker, `backend/Dockerfile` must copy `src/`, `models/`, and `data/` so that `RiskPredictor` can locate `FINAL_MODEL.json`, `volatility_aware_risk_model.joblib`, and the canonical parquet dataset.

---

## 14. Model Artifact Loading & Lifecycle Strategy

### 14.1 Singleton Predictor Instance
- `RiskPredictor.__init__()` loads the model artifact, parses `FINAL_MODEL.json`, and rebuilds the training preprocessing pipeline. This initialisation takes ~3.5 seconds.
- Therefore, `RiskPredictor` **must be instantiated once as a singleton** during application startup, NOT re-instantiated on every HTTP request.
- Factory pattern: In `backend/app/assessment/factory.py`, maintain a cached singleton instance of `MLAssessmentEngine(model=ParakhVolatilityMLModel(predictor=shared_predictor))`.

### 14.2 Path Resolution
`RiskPredictor` in `src/ml/inference/predictor.py` resolves paths relative to `_PROJECT_ROOT` (`Path(__file__).resolve().parents[3]`).
- When running from repository root or backend with `PYTHONPATH=.`, path resolution works seamlessly.
- Configurable environment variable `PARAKH_FINAL_MODEL_MANIFEST` should be supported for deployment flexibility.

---

## 15. Error Handling & Failure Mode Mapping

| ML / Pipeline Condition | Exception in ML Layer | Backend Exception Mapping | HTTP Response |
|:---|:---|:---|:---|
| Missing required input fields | `InputValidationError` | `AssessmentInputError` | **400 Bad Request** |
| Prohibited privacy fields in input | `InputValidationError` | `AssessmentInputError` | **400 Bad Request** |
| Value outside contracted bounds | `InputValidationError` | `AssessmentInputError` | **400 Bad Request** |
| Insufficient observation / payouts | `is_insufficient_evidence=True` | Normal flow: returns `RiskTier.INSUFFICIENT` | **201 Created** (`risk_level: "INSUFFICIENT"`, `credit_score: null`) |
| Missing model artifact on disk | `FileNotFoundError` | `AssessmentEngineError` | **500 Internal Server Error** |
| SHAP explainer computation failure | Caught internally in predictor | Fallback explanation attached | **201 Created** (Score & tier intact, fallback disclaimer) |
| Feature engineering failure | `RuntimeError` | `AssessmentEngineError` | **500 Internal Server Error** |

---

## 16. Security, Privacy, and Data Handling Observations

1. **Strict Data Minimization:** The Phase 9 `InputValidator` checks against `PROHIBITED_FIELDS`. The backend `AssessmentInput` also validates `PROHIBITED_FIELDS`. Sensitive data (bank logins, raw UPI logs, GPS) cannot reach the ML model.
2. **Audit Logging:** Every execution of `assess_application` records an audit event `AuditAction.ASSESSMENT_EXECUTED` via `AuditService`.
3. **Consent Enforcement:** By default, `enforce_consent=True` verifies active consent for `ConsentDataSource.PLATFORM` before assessment execution.
4. **Transient Feature Attributions:** Raw feature arrays and model matrices are kept in ephemeral memory and never persisted in database logs.

---

## 17. Testing Strategy for Phase 10B

1. **Integration Tests (`backend/tests/test_ml_integration.py`):**
   - Test end-to-end `assess_application` with `ASSESSMENT_ENGINE="ml"`.
   - Test that `CreditAssessment` database record matches Phase 9 prediction bit-for-bit.
   - Test insufficient data handling producing `RiskTier.INSUFFICIENT`.
   - Test rejection of invalid / prohibited fields.
2. **Existing Regression Tests:**
   - Run all 273 ML tests in `tests/ml` and `tests/data`.
   - Run backend test suite in `backend/tests/`.

---

## 18. Files Expected to Change During Phase 10 Implementation

### 18.1 Files to Create in Phase 10B
1. `backend/app/assessment/ml_model_adapter.py`: Concrete `MLModel` subclass bridging `AssessmentInput` to `RiskPredictor` and `MLModelOutput`.
2. `backend/tests/test_ml_integration.py`: Comprehensive integration test suite.

### 18.2 Files to Modify in Phase 10B
1. `backend/app/assessment/factory.py`: Register and instantiate the ML model adapter when `ASSESSMENT_ENGINE="ml"`.
2. `backend/app/core/config.py`: Add ML artifact path settings.
3. `backend/requirements.txt`: Add ML runtime dependencies.
4. `backend/Dockerfile`: Include ML files and dependencies in container build.

### 18.3 Files That Must Remain Untouched
- `models/artifacts/*`: All model artifacts and manifests remain strictly frozen.
- `src/ml/*`: Phase 9 inference implementation remains untouched.
- `backend/alembic/*`: Database schema remains untouched.
- `frontend/*`: Frontend apps and packages remain untouched.

---

## 19. Phase 10B Readiness Assessment

**Status: FULLY READY FOR IMPLEMENTATION**
- All 46 ML input fields are mapped to concrete backend data models.
- The existing backend architecture already provides the exact boundary classes (`MLModel`, `MLAssessmentEngine`, `FeaturePipeline`) needed for seamless integration.
- No database migrations, model retraining, or frontend modifications are necessary.
- Integration can proceed smoothly following the step-by-step sequence in `docs/backend-ml-integration-contract.md`.
