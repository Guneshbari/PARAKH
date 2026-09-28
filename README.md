# PARAKH — Alternative Credit Assessment Platform

**PARAKH** is an explainable alternative credit assessment platform purpose-built for gig and platform economy workers (delivery partners, rideshare drivers, quick-commerce agents, and independent micro-contractors). Traditional underwriting relies on fixed monthly paystubs, formal tax filings, and conventional bureau scores, systematically excluding or under-scoring non-traditional earners. PARAKH bridges this gap by ingesting multi-source financial and non-traditional behavioral data (daily earnings regularity, customer ratings, active working days, and cashflow volatility) to generate fair, transparent, and auditable credit assessments.

---

## 1. Project Overview

PARAKH operates on three core principles:
1. **Financial Inclusion**: Evaluate creditworthiness using real-time gig telemetry and bank-aggregated cashflow volatility instead of rigid bureau history.
2. **Statutory Privacy & Consent**: Strict compliance with India's Digital Personal Data Protection (DPDP) Act. All external data ingestion requires explicit applicant consent, and storage of invasive raw data (passwords, bank credentials, raw UPI logs, contact books, GPS history) is strictly prohibited at both schema and service boundaries.
3. **Human-in-the-Loop Governance & Auditability**: Algorithmic scoring provides transparent score factors and risk categories. Human credit officers review applications in an authorized adjudication workflow, with all transitions and review actions captured in an immutable audit log.

---

## 2. Architecture

PARAKH is engineered as a decoupled full-stack platform:

```
[ Web Browser Client ]
       │  (Port 3000)
       ▼
┌────────────────────────────────────────────────────────┐
│  Next.js 16 Web Application (frontend/apps/web)        │
│  - Modern TypeScript + React 19 UI                     │
│  - Tailwind CSS + Lucide Icons + Recharts Analytics     │
│  - Dual-mode API resolution (Browser client vs SSR)    │
└───────────────────────┬────────────────────────────────┘
                        │ HTTP / JSON
                        ▼
┌────────────────────────────────────────────────────────┐
│  FastAPI Backend Service (backend/app)                 │
│  - Layered API -> Schemas -> Services -> Repositories  │
│  - JWT Authentication & Role-Based Access Control      │
│  - Statutory DPDP Consent Enforcement Engine           │
│  - Transactional Boundary & Atomic Rollback Safety     │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       SQLAlchemy 2.0                    │ Injected Engine
                ▼                        ▼
┌────────────────────────┐   ┌──────────────────────────────────────────────┐
│  PostgreSQL 16         │   │  ML Assessment Engine (Active Production)    │
│  - Multi-table schema  │   │  - TelemetryFeaturePipeline (40 features)    │
│  - Alembic migrations  │   │  - Persisted CreditRiskPreprocessor (joblib) │
│  - Persistent storage  │   │  - Frozen Volatility-Aware LightGBM (v1.0.0) │
│  - JSONB explanations  │   │  - Persisted TreeSHAP explanations           │
└────────────────────────┘   │  - MockAssessmentEngine (testing fallback)   │
                             └──────────────────────────────────────────────┘
```

---

## 3. Technology Stack

- **Frontend**: Next.js 16 (Turbopack), React 19, TypeScript, Tailwind CSS, TanStack Query, Recharts, Lucide Icons.
- **Shared Packages (`frontend/packages`)**:
  - `@parakh/api`: Canonical HTTP client with automatic retry for idempotent GETs, non-retry for mutations, and domain adapters (`adaptApplication`, `adaptAssessment`, `adaptBorrowerProfile`, `adaptPortfolioAnalytics`).
  - `@parakh/types`: Shared TypeScript interfaces and contracts.
  - `@parakh/validation`: Shared validation utilities.
  - `@parakh/design-tokens`: Shared styling and visual constants.
- **Backend**: FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2, Alembic, psycopg v3.
- **Database**: PostgreSQL 16 (isolated on private Docker bridge network).
- **Authentication**: Stateless HMAC-SHA256 JWT bearer tokens with password hashing via bcrypt.

---

## 4. Environment Variables

All services are configured using environment variables. See [.env.example](file:///.env.example) for the complete template:

| Variable | Description | Default / Example |
|---|---|---|
| `POSTGRES_DB` | Database name | `parakh` |
| `POSTGRES_USER` | Database user | `parakh` |
| `POSTGRES_PASSWORD` | Database password | `parakh_password` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URI | `postgresql+psycopg://parakh:parakh_password@postgres:5432/parakh` |
| `SECRET_KEY` | JWT signing secret | `parakh-super-secret-key-change-in-production-0987654321` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT validity lifetime | `1440` (24 hours) |
| `ASSESSMENT_ENGINE` | Assessment engine implementation | `ml` (production/prototype default) or `mock` (unit test fallback) |
| `ML_MANIFEST_PATH` | Path to FINAL_MODEL.json | `models/artifacts/FINAL_MODEL.json` (optional override) |
| `ML_PREPROCESSOR_PATH` | Path to fitted CreditRiskPreprocessor | `models/artifacts/credit_risk_preprocessor.joblib` (optional override) |
| `DEBUG` | FastAPI debug mode | `false` |
| `APP_ENV` | Application environment | `production` or `development` |
| `NEXT_PUBLIC_API_URL` | Browser-accessible backend URL | `http://localhost:8000` |
| `INTERNAL_API_URL` | Docker SSR backend URL | `http://backend:8000` |

---

## 5. Docker Setup (Recommended)

The entire platform brings up with a single command:

```bash
# 1. Start all containers in background
docker compose up -d

# 2. Inspect container status
docker compose ps

# 3. View logs
docker compose logs -f backend
```

Published Ports:
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL**: Kept strictly internal on `postgres:5432` (`parakh_network`).

To stop and start while preserving all database data:
```bash
docker compose stop
docker compose start
```

---

## 6. Local Development Setup

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install

# Start development server
npm --workspace=web run dev
```

---

## 7. Authentication & Role-Based Access Control (RBAC)

PARAKH enforces three discrete user roles:
- **`APPLICANT`**:
  - Permitted: Self-registration (`POST /api/v1/users`), own profile creation, own credit application creation, statutory consent management, viewing own assessment results.
  - Denied: Accessing another applicant's applications (403), accessing priority review queue (403), submitting review decisions (403), accessing audit logs (403).
- **`REVIEWER`**:
  - Permitted: Accessing priority queue (`GET /api/v1/applications`), inspecting applicant dossiers and evaluations, submitting adjudication review outcomes.
  - Denied: Accessing administrative audit trails (403), provisioning user accounts (403).
- **`ADMIN`**:
  - Permitted: System governance, model version registry (`/api/v1/model-versions`), administrative audit logs (`/api/v1/audit-logs`), provisioning Reviewer/Admin accounts.

Default seeded administrator:
- Email: `admin@parakh.com`
- Password: `AdminPassword123!`

---

## 8. Applicant Workflow

1. **Registration & Auth**: Applicant registers (`POST /api/v1/users`), authenticates (`POST /api/v1/auth/login`), and validates session (`GET /api/v1/auth/me`).
2. **Profile Submission**: Enters gig details (work type, active days, platform experience) via `POST /api/v1/applicants`.
3. **Application Creation**: Specifies requested loan amount and purpose via `POST /api/v1/applications`.
4. **Statutory Consent**: Grants explicit DPDP consent via `POST /api/v1/consents` (`granted: true`). Attempting to ingest data or assess before granting consent is blocked with HTTP 403.
5. **Financial Telemetry Ingestion**: Platform data (earnings, platform rating, active days) ingested via `POST /api/v1/applications/{id}/financial-signals`.
6. **Assessment Generation**: Invokes `POST /api/v1/applications/{id}/assess`. The engine computes credit score and risk level, persisting the record to PostgreSQL.
7. **Result Retrieval**: View assessment dossier via `GET /api/v1/applications/{id}/assessments/latest`. Browser refreshes retrieve persisted data from PostgreSQL without reverting.

---

## 9. Reviewer Workflow

1. **Authentication**: Credit officer logs in with assigned `REVIEWER` credentials.
2. **Priority Queue**: Accesses unassigned applications via `GET /api/v1/applications`.
3. **Dossier & Risk Analysis**: Inspects applicant information, earnings telemetry, and credit assessment.
4. **Adjudication**: Submits a review outcome via `POST /api/v1/applications/{id}/reviews`. The supported canonical review actions are:
   - `RECORD_OUTCOME` (`outcome: REVIEWED`) -> Canonical status transitions to `COMPLETED`.
   - `MANUAL_REVIEW` (`outcome: ESCALATED`) -> Canonical status transitions to `MANUAL_REVIEW`.
   - `REQUEST_VERIFICATION` (`outcome: ADDITIONAL_INFORMATION_REQUIRED`) -> Canonical status transitions to `UNDER_REVIEW`.
5. **Audit Logging**: Each review event automatically creates audit entries with the reviewer's JWT identity and timestamp.

---

## 10. ML Integration Boundary

### Active Production Architecture
The machine learning pipeline is fully integrated into the backend assessment flow:

```
Financial Telemetry (telemetry_series JSONB)
        ↓
TelemetryFeaturePipeline (backend/app/assessment/pipeline.py)
        ↓
AssessmentInput with 40 Derived Features
        ↓
MLModelAdapter (app/assessment/ml_model_adapter.py)
        ↓ Data Sufficiency Gate (observed_days >= 30, payout_count >= 4, group_count >= 2)
RiskPredictor (src/ml/inference/predictor.py)
        ↓ FeatureEngineer (9 interaction/volatility features)
Persisted CreditRiskPreprocessor (models/artifacts/credit_risk_preprocessor.joblib)
        ↓ 64 model-ready columns
Frozen Volatility-Aware LightGBM Model (models/artifacts/volatility_aware_risk_model.joblib v1.0.0)
        ↓ TreeShapExplainer
Persisted Assessment Record (credit_assessments table with explanation JSONB)
        ↓
CreditAssessmentResponse (score, risk_level, confidence, key_factors, explanation)
```

- **Data Sufficiency Governance (Phase 13A-2)**: Strictly evaluates active observation days and payout cycles from real telemetry. Missing telemetry is never fabricated with synthetic defaults.
- **Deterministic Inference (Phase 13A-4)**: Loads the serialized, fitted `CreditRiskPreprocessor` directly (<1ms startup) without coupling runtime inference to training datasets.
- **Auditable Explanations (Phase 13A-1)**: TreeSHAP local instance explanations and plain-language protective/risk factors are permanently persisted in PostgreSQL JSONB.
- **Testing Engine**: `MockAssessmentEngine` remains available for offline development and isolated unit testing via `ASSESSMENT_ENGINE=mock`.

---

## 11. Testing & Verification

Execute the test suites using the repository commands:

```bash
# 1. Full-Stack End-to-End Docker Verification (52 comprehensive checks)
python3 scripts/test_docker_integration.py

# 2. Container Volume Restart Persistence Verification
docker compose stop
docker compose start
python3 scripts/test_docker_integration.py --verify-persistence

# 3. Backend Test Suite (219 Unit and Integration Tests)
cd backend && python3 -m pytest -v

# 4. Frontend Security & Workflow Test Suites
cd frontend/apps/web
npx tsx test-phase11-hardening.ts     # 19/19 Hardening tests passed
npx tsx test-phase8-workflow.ts        # Phase 8 Review & Audit workflow
npx tsx test-phase9-analytics.ts       # Phase 9 Analytics & Governance
npx tsx test-applicant-flow.ts         # Applicant Portal integration
npx tsx test-reviewer-flow.ts          # Reviewer Portal integration

# 5. Frontend TypeScript Verification & Production Build
npx tsc --noEmit                       # 0 TypeScript errors
npm run build                          # Successful production build
```

---

## 12. Known Limitations

1. **Alternative Credit Assessment Engine**: Powered by the frozen `volatility-aware-risk-model` v1.0.0 (`models/artifacts/volatility_aware_risk_model.joblib`) with deterministic `TelemetryFeaturePipeline` feature derivation, persisted `CreditRiskPreprocessor` artifact, and persisted TreeSHAP explanations.
2. **External Gateway Mocking**: In local demonstration mode, external platform account aggregators (Swiggy, Zomato, AA gateways) are simulated through synthetic API payloads rather than live sandbox OAuth connections.
3. **Database Port Exposure**: PostgreSQL is intentionally not exposed on the host machine to enforce network security. All database interaction occurs via the backend container or Docker network.
