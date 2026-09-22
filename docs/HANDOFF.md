# PARAKH — Project Handoff Documentation

This document serves as the formal project handoff guide for the **PARAKH** platform, detailing system architecture, data models, workflows, testing suites, and instructions for integrating Person 2's feature engineering and Person 3's machine learning pipelines.

---

## 1. Architecture

PARAKH is organized as a decoupled, multi-tier full-stack application:

```
[ Client Browser ]
        │  (HTTP / Port 3000)
        ▼
┌────────────────────────────────────────────────────────┐
│  Frontend (Next.js 16 + React 19)                      │
│  - Location: frontend/apps/web                         │
│  - Monorepo packages: @parakh/api, @parakh/types,      │
│    @parakh/validation, @parakh/design-tokens           │
│  - Dual URL Resolution:                                │
│    Client browser -> NEXT_PUBLIC_API_URL (port 8000)   │
│    Container SSR  -> INTERNAL_API_URL (backend:8000)   │
└───────────────────────┬────────────────────────────────┘
                        │ HTTP / JSON
                        ▼
┌────────────────────────────────────────────────────────┐
│  Backend (FastAPI + Python 3.11)                       │
│  - Location: backend/app                               │
│  - Layered Architecture:                               │
│    1. API Routers (app/api/v1/)                        │
│    2. Pydantic Schemas (app/schemas/)                  │
│    3. Domain Services (app/services/)                  │
│    4. Data Repositories (app/repositories/)            │
│    5. SQLAlchemy Models (app/models/)                  │
│  - Cross-Cutting: Security, RBAC, Audit, DPDP Privacy  │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       SQLAlchemy 2.0                    │ Interface Boundary
                ▼                        ▼
┌────────────────────────┐   ┌───────────────────────────┐
│  PostgreSQL 16         │   │  AssessmentEngine (Mock)  │
│  - Host: postgres:5432 │   │  - Factory injection      │
│  - Persistent Volume:  │   │  - Standard result schema │
│    postgres_data       │   │  - Location:              │
│  - Alembic Migrations  │   │    backend/app/assessment │
└────────────────────────┘   └───────────────────────────┘
```

---

## 2. API Documentation

The FastAPI backend exposes an interactive OpenAPI specification at `http://localhost:8000/docs`. The key versioned API endpoints are:

### Authentication & Users
- `POST /api/v1/users`: Register a new platform account (`role: APPLICANT` allowed for self-registration; `REVIEWER`/`ADMIN` require admin authorization).
- `POST /api/v1/auth/login`: Authenticate email and password, returning Bearer JWT access token and user claims.
- `GET /api/v1/auth/me`: Validate caller session identity and retrieve assigned role.
- `GET /api/v1/users/{id}`: Fetch user metadata.

### Applicant Profile & Applications
- `POST /api/v1/applicants`: Create or update gig worker profile (`gig_work_type`, `years_working`, `average_working_days`).
- `GET /api/v1/applicants/{id}`: Retrieve applicant profile.
- `POST /api/v1/applications`: Submit new credit application (`requested_loan_amount`, `loan_purpose`, `preferred_repayment_period`).
- `GET /api/v1/applications`: List applications (restricted to `REVIEWER` and `ADMIN`).
- `GET /api/v1/applications/{id}`: Retrieve full application dossier.
- `GET /api/v1/applications/applicant/{profile_id}`: Fetch all applications for a given applicant profile.

### Statutory DPDP Consent
- `POST /api/v1/consents`: Record applicant consent for external data ingestion (`data_source: PLATFORM`).
- `GET /api/v1/applications/{id}/consents`: List consent records for an application.
- `POST /api/v1/consents/{id}/revoke`: Revoke an existing consent grant.

### Financial Signals
- `POST /api/v1/applications/{id}/financial-signals`: Ingest derived indicators (`average_income`, `platform_rating`, `active_days`). Supports `?enforce_consent=true` query flag.
- `GET /api/v1/applications/{id}/financial-signals`: Retrieve ingested signals.

### Assessment Workflow
- `POST /api/v1/applications/{id}/assess`: Trigger credit assessment execution. Normalizes inputs, runs the engine, persists results, and updates application state.
- `GET /api/v1/applications/{id}/assessments/latest`: Retrieve most recent evaluation score and explanation.
- `GET /api/v1/applications/{id}/assessments`: List assessment history.

### Human Review Adjudication
- `POST /api/v1/applications/{id}/reviews`: Record human credit officer adjudication outcome. Supported outcomes: `REVIEWED`, `ESCALATED`, `ADDITIONAL_INFORMATION_REQUIRED`.
- `GET /api/v1/applications/{id}/reviews`: List review history.

### Governance & Audit
- `GET /api/v1/audit-logs`: Query immutable compliance audit logs (admin only). Filterable by `application_id`, `user_id`, and `action`.
- `GET /api/v1/model-versions`: Inspect registered scoring models and active version.

---

## 3. Database Schema

Schema evolution is strictly managed via Alembic (`fd385d59e799_initial_schema.py`). The relational entities include:

1. **`users`**: Platform accounts (`id`, `email`, `password_hash`, `role`, `is_active`, timestamps).
2. **`applicant_profiles`**: Gig worker profile (`id`, `user_id`, `gig_work_type`, `years_working`, `average_working_days`, `business_or_loan_purpose`).
3. **`applications`**: Financing requests (`id`, `applicant_profile_id`, `status`, `requested_loan_amount`, `loan_purpose`, `preferred_repayment_period`).
   - Status Enum: `DRAFT`, `SUBMITTED`, `ASSESSED`, `UNDER_REVIEW`, `MANUAL_REVIEW`, `COMPLETED`, `REJECTED`, `WITHDRAWN`.
4. **`consents`**: Statutory privacy records (`id`, `application_id`, `applicant_profile_id`, `data_source`, `purpose`, `granted`, `granted_at`, `revoked_at`).
5. **`financial_signals`**: Privacy-minimized indicators (`id`, `application_id`, `applicant_profile_id`, `source`, `average_income`, `median_income`, `platform_rating`, `active_days`, `signal_metadata`). Prohibits raw bank accounts, passwords, contact lists, and GPS traces.
6. **`model_versions`**: Algorithmic model registry (`id`, `model_name`, `version`, `algorithm`, `description`, `is_active`).
7. **`credit_assessments`**: Output records (`id`, `application_id`, `model_version_id`, `credit_score`, `risk_level`, `confidence_score`, `raw_model_output`, `feature_contributions`).
8. **`review_outcomes`**: Human officer decisions (`id`, `application_id`, `reviewer_id`, `outcome`, `notes`).
9. **`audit_logs`**: Immutable event trail (`id`, `user_id`, `application_id`, `action`, `entity_type`, `entity_id`, `actor_role`, `outcome`, `audit_metadata`, `created_at`).

---

## 4. Environment Setup

Copy [.env.example](file:///.env.example) to `.env` or set in your container runtime:

```bash
# Database Configuration
POSTGRES_DB=parakh
POSTGRES_USER=parakh
POSTGRES_PASSWORD=parakh_password
DATABASE_URL=postgresql+psycopg://parakh:parakh_password@postgres:5432/parakh

# Security / JWT
SECRET_KEY=parakh-super-secret-key-change-in-production-0987654321
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Assessment Engine Configuration
ASSESSMENT_ENGINE=mock

# Application Diagnostics
DEBUG=false
APP_ENV=production

# Frontend API Resolution
NEXT_PUBLIC_API_URL=http://localhost:8000
INTERNAL_API_URL=http://backend:8000
```

---

## 5. Docker Instructions

### Starting the Stack
```bash
docker compose up -d
```

### Verifying Service Health
```bash
docker compose ps
```
All three services (`postgres`, `backend`, `frontend`) will report `(healthy)`:
- Frontend on `http://localhost:3000`
- Backend API on `http://localhost:8000`
- PostgreSQL on internal network `postgres:5432`

### Container Lifecycle & Persistence
The database utilizes a named Docker volume `parakh_postgres_data`. To stop and resume while guaranteeing 100% data persistence:
```bash
docker compose stop
docker compose start
```

To tear down containers and network while preserving data volume:
```bash
docker compose down
```

---

## 6. Authentication & RBAC

PARAKH implements stateless HMAC-SHA256 JWT tokens with role-based access control:

- **`APPLICANT`**: Self-registers via `POST /api/v1/users`. Can only read/write own profile, applications, consents, and assessment outcomes. Blocked from other applicants' records (403), reviewer queues (403), review submissions (403), and audit logs (403).
- **`REVIEWER`**: Created by administrator. Can view priority queue, inspect applicant dossiers, and record review actions. Blocked from administrator audit logs (403).
- **`ADMIN`**: Pre-seeded default admin account (`admin@parakh.com` / `AdminPassword123!`). Has full access to audit trails, model registry, and user account creation.

---

## 7. Applicant Workflow

1. **Signup & Login**: Create account via `/signup` or `POST /api/v1/users` and log in via `POST /api/v1/auth/login`.
2. **Profile Submission**: Provide gig economy context at `/user/profile` (`POST /api/v1/applicants`).
3. **Application**: Enter loan amount and purpose at `/user/applications/new` (`POST /api/v1/applications`).
4. **Consent Grant**: Provide explicit statutory consent (`POST /api/v1/consents`). Pre-consent ingestion is rejected.
5. **Financial Telemetry**: Ingest derived income and delivery performance signals.
6. **Assessment**: Trigger credit assessment (`POST /api/v1/applications/{id}/assess`).
7. **Results**: View explainable credit score and risk factors at `/user/results/[id]`. Persists across page refresh.

---

## 8. Reviewer Workflow

1. **Login**: Authenticate at `/login` with Reviewer credentials.
2. **Reviewer Dashboard**: Access queue at `/admin/dashboard` or `/admin/applications`.
3. **Dossier Inspection**: Open applicant file at `/admin/applications/[id]`.
4. **Adjudication**: Submit review decision:
   - `RECORD_OUTCOME` -> Transitions status to `COMPLETED`.
   - `MANUAL_REVIEW` -> Transitions status to `MANUAL_REVIEW`.
   - `REQUEST_VERIFICATION` -> Transitions status to `UNDER_REVIEW`.
5. **Audit Recording**: Action logged with reviewer user ID and timestamp in `audit_logs`.

---

## 9. AssessmentEngine / ML Integration Interface

The ML boundary is isolated in `backend/app/assessment/`:
- **`AssessmentEngine`** (`backend/app/assessment/base.py`): Abstract base class requiring `assess(input: AssessmentInput) -> AssessmentResult`.
- **`AssessmentInput`** (`backend/app/assessment/schemas.py`): Strongly-typed input contract containing applicant profile and aggregated financial signals.
- **`AssessmentResult`** (`backend/app/assessment/schemas.py`): Standardized output contract with `credit_score` (300-900), `risk_level`, `confidence_score`, `key_factors`, and `feature_contributions`.
- **`MockAssessmentEngine`** (`backend/app/assessment/mock_engine.py`): Current deterministic rule-based implementation.

---

## 10. Testing Instructions

Run all verification suites:

```bash
# 1. Full-Stack End-to-End Test Suite (52 checks against live Docker stack)
python3 scripts/test_docker_integration.py

# 2. Database Volume Restart Persistence Check
python3 scripts/test_docker_integration.py --verify-persistence

# 3. Backend Test Suite (219 Unit and Integration tests)
cd backend && python3 -m pytest -v

# 4. Frontend Hardening & Workflow Suites
cd frontend/apps/web
npx tsx test-phase11-hardening.ts
npx tsx test-phase8-workflow.ts
npx tsx test-phase9-analytics.ts
npx tsx test-applicant-flow.ts
npx tsx test-reviewer-flow.ts

# 5. Frontend Typecheck and Production Build
npx tsc --noEmit
npm run build
```

---

## 11. Known Limitations

- **Assessment Engine**: Currently executes `MockAssessmentEngine`. Person 2's feature engineering pipeline and Person 3's ML models (XGBoost/LightGBM/SHAP/Fairlearn) are designated for future integration.
- **Aggregator Sandboxes**: Local demonstration uses simulated gig platform payloads rather than live production OAuth account aggregator connectors.
- **Database Exposure**: PostgreSQL is intentionally not exposed externally to host ports.

---

## 12. Person 2/3 Integration Notes

When Person 2 (Feature Engineering) and Person 3 (Machine Learning Model) integrate their work, the target end-to-end architecture is:

```
Financial Signals
       ↓
Person 2 Feature Pipeline (FeatureEngineeringPipeline)
       ↓
Person 3 ML Model (XGBoost / LightGBM / LogisticRegression)
       ↓
AssessmentEngine (RealAssessmentEngine / MLAssessmentEngine)
       ↓
Standard Assessment Result (Pydantic AssessmentResult)
       ↓
PostgreSQL (credit_assessments table)
       ↓
Existing API (/api/v1/applications/{id}/assess)
       ↓
Existing Frontend (@parakh/api client & React adapters)
```

### Steps for Person 2 & 3:
1. Implement the feature pipeline in `backend/app/assessment/pipeline.py` adhering to `FeaturePipeline`.
2. Implement `MLAssessmentEngine` inheriting from `AssessmentEngine` in `backend/app/assessment/`.
3. In `backend/app/assessment/factory.py`, register `EngineType.ML` to return `MLAssessmentEngine`.
4. Update `ASSESSMENT_ENGINE=ml` in `.env`.
5. **No frontend or database changes are required.** The existing API endpoints, Pydantic schemas, database tables, and frontend React components will continue to function seamlessly.
