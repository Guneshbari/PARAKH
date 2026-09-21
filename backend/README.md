# PARAKH — Backend

## 1. Overview
**PARAKH** is an alternative credit-assessment platform and prototype designed for gig and platform workers. It leverages multi-source financial and non-traditional behavioral data (e.g., platform earnings, delivery regularity, cash-flow consistency) to generate transparent, explainable credit scores and facilitate credit inclusion.

This directory (`PARAKH/backend/`) contains the **FastAPI** backend service responsible for serving the core API, orchestrating data ingestion, executing credit assessments, and delivering explanations.

---

## 2. Current Backend Technology Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python web framework for high-performance APIs)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Database ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (SQL toolkit and Object Relational Mapper)
- **Database Driver**: [psycopg (v3)](https://www.psycopg.org/) (High-performance PostgreSQL adapter)
- **Relational Database**: [PostgreSQL](https://www.postgresql.org/)
- **Configuration & Validation**: [Pydantic](https://docs.pydantic.dev/) and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Environment Management**: [python-dotenv](https://github.com/theskumar/python-dotenv)

---

## 3. Backend Architecture & Layers

The backend follows a layered architecture to keep concerns cleanly decoupled as features are introduced:

```
HTTP Request
    ↓
API Layer (app/api/)
    ↓
Service Layer (app/services/)
    ↓
Repository Layer (app/repositories/)
    ↓
Database ORM (SQLAlchemy 2.0 + psycopg)
    ↓
PostgreSQL Database
```

### Architectural Components:
1. **API Layer (`app/api/`)**:
   Exposes HTTP routes via FastAPI routers. The central router (`api/router.py`) aggregates versioned domain subrouters (e.g., `api/database.py`).
2. **Database & Core (`app/core/`)**:
   Contains application settings (`config.py`) and database infrastructure (`database.py`), including the engine, session factory (`SessionLocal`), and the request-scoped database dependency (`get_db()`).
3. **Schemas (`app/schemas/`)**:
   Pydantic models defining input validation rules and output response serialization contracts (`StatusResponse`, `DatabaseHealthResponse`).
4. **Models (`app/models/`)**:
   SQLAlchemy 2.0 domain entities and DeclarativeBase providing the data model for accounts, profiles, applications, consents, signals, and assessments.
5. **Services (`app/services/`)**:
   Business logic and orchestration layer. Will house workflows for credit assessment calculations, consent handling, and external integrations.
6. **Repositories (`app/repositories/`)**:
   Data access abstraction isolating database queries and persistence mechanisms from business logic.

> **Note**: `services/` and `repositories/` represent architectural boundaries prepared for future implementation. Database migrations (Alembic), authentication (JWT), and ML scoring logic will be introduced in subsequent tasks.

---

## 4. Database Foundation

- **Relational Database**: PostgreSQL is the primary database for application state, audit logs, and structured assessments.
- **ORM & Abstraction**: SQLAlchemy 2.0 provides declarative modeling, type safety, and connection pool management.
- **Driver**: `psycopg` (v3 with binary extensions) serves as the modern DBAPI driver.
- **Declarative Base**: Defined in `app/models/base.py` with common mixins for UUID primary keys and timezone-aware timestamps.
- **Session Lifecycle**: The `get_db()` dependency yields a scoped SQLAlchemy `Session` per request and ensures it is reliably closed upon completion.

---

## 5. Domain Data Model

The PARAKH domain model represents the core entities required for privacy-preserving, explainable alternative credit assessment for gig workers:

### Conceptual Entity Diagram
```
User
 ↓ (1:1)
ApplicantProfile
 ↓ (1:N)
Application
 ├── Consent (1:N)
 ├── FinancialSignal (1:N)
 ├── CreditAssessment (1:N)
 │      ↓ (N:1)
 │   ModelVersion
 └── ReviewOutcome (1:N)

AuditLog
 ├── User (N:1, SET NULL)
 └── Application (N:1, SET NULL)
```

### Domain Entities Summary:
1. **User (`users`)**: Represents account identities supporting roles (`APPLICANT`, `REVIEWER`). Uses unique email and placeholder storage for future authentication hashes.
2. **ApplicantProfile (`applicant_profiles`)**: One-to-one extension of `User` holding gig worker profile details (`gig_work_type`, `years_working`, `average_working_days`, `business_or_loan_purpose`).
3. **Application (`applications`)**: Credit assessment requests with requested amounts, purpose, repayment period, and lifecycle status (`DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `ASSESSED`, `MANUAL_REVIEW`, `COMPLETED`).
4. **Consent (`consents`)**: Explicit applicant permission tracking per data source (`PLATFORM`, `FINANCIAL_ACTIVITY`, `UTILITY`) and purpose, supporting grant and revocation timestamps (`granted_at`, `revoked_at`).
5. **FinancialSignal (`financial_signals`)**: Aggregated, derived financial metrics (e.g. `average_income`, `median_income`, `income_volatility`, `income_trend`, `active_days`, `payment_regularity`, `cashflow_buffer`, `existing_obligation`, `platform_rating`).
   > **Data Minimization Principle**: `FinancialSignal` strictly contains aggregated and derived indicators. It **does NOT** store raw UPI transaction descriptions, merchant names, contact books, GPS/location history, or raw bank credentials.
6. **CreditAssessment (`credit_assessments`)**: Generated assessment output including `credit_score`, `risk_probability`, `risk_level` (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`), `confidence`, and financial health ratios. Nullable values are supported when evidence is insufficient.
7. **ModelVersion (`model_versions`)**: Traceability record identifying the specific scoring model, version string, algorithm name, and description used to produce an assessment.
8. **ReviewOutcome (`review_outcomes`)**: Decision support record capturing human reviewer evaluation (`REVIEWED`, `ESCALATED`, `ADDITIONAL_INFORMATION_REQUIRED`) with notes.
9. **AuditLog (`audit_logs`)**: Immutable audit trail of system and user events with JSONB metadata. Foreign keys use `ON DELETE SET NULL` to preserve historical integrity.

### Data Model Conventions:
- **Primary Keys**: Universal `UUID` strategy across all entities.
- **Timestamps**: Timezone-aware UTC `DateTime(timezone=True)` with server defaults.
- **Monetary Fields**: Fixed-precision `Numeric(12, 2)` preventing floating-point rounding errors.
- **Constraints**: Non-negative monetary check constraints, risk probability bounds [0, 1], and email uniqueness.

---

## 6. Local Setup & Configuration

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- PostgreSQL 14+ installed and running locally (optional for initial mock/unit testing)

### Step-by-Step Instructions (Linux / macOS)

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure environment variables**:
   Copy `.env.example` to create your local `.env`:
   ```bash
   cp .env.example .env
   ```

6. **PostgreSQL Setup (Local)**:
   - Create a local PostgreSQL user and database (e.g. using `psql`):
     ```sql
     CREATE USER parakh WITH PASSWORD 'parakh_password';
     CREATE DATABASE parakh OWNER parakh;
     GRANT ALL PRIVILEGES ON DATABASE parakh TO parakh;
     ```
   - Update `DATABASE_URL` in `.env`:
     ```env
     DATABASE_URL=postgresql+psycopg://parakh:parakh_password@localhost:5432/parakh
     ```

7. **Start the FastAPI development server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

---

## 7. Endpoints

| Method | Endpoint | Description | Sample Response (Success) |
|---|---|---|---|
| `GET` | `/` | API root message | `{"message": "PARAKH API is running"}` |
| `GET` | `/health` | Health check endpoint | `{"status": "healthy"}` |
| `GET` | `/api/v1/status` | Versioned API service status | `{"status": "ok", "service": "PARAKH API", "version": "0.1.0"}` |
| `GET` | `/api/v1/database/health` | Database connection check (`SELECT 1`) | `{"status": "healthy", "database": "connected"}` |

### Testing Endpoints with curl
```bash
# Root greeting
curl -s http://127.0.0.1:8000/

# Service health
curl -s http://127.0.0.1:8000/health

# API layer status
curl -s http://127.0.0.1:8000/api/v1/status

# Database connectivity health check
curl -s http://127.0.0.1:8000/api/v1/database/health
```

> **Database Health Check Behavior**:
> - If PostgreSQL is connected: returns `HTTP 200` with `{"status": "healthy", "database": "connected"}`.
> - If PostgreSQL is unavailable: returns `HTTP 503` with `{"status": "unhealthy", "database": "disconnected"}` without leaking internal credentials, host details, or tracebacks.
> - Note: This endpoint only verifies raw database connectivity. Business tables do not exist yet.

---

## 8. Running Tests

Run the full unit and integration test suite:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

- **Unit tests**: Validate configuration, SQLAlchemy engine creation, DeclarativeBase inheritance, `get_db()` lifecycle, domain model relationships, constraints, and data minimization.
- **Integration tests**: Automatically attempt live `SELECT 1` queries against PostgreSQL if available. If PostgreSQL is offline locally, integration tests skip gracefully without failing the build.

---

## 9. Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entrypoint
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py        # Central API router aggregating subrouters
│   │   └── database.py      # Database health check router
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings (APP_NAME, DATABASE_URL, etc.)
│   │   └── database.py      # Engine, SessionLocal, get_db session dependency
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py        # StatusResponse and DatabaseHealthResponse schemas
│   ├── models/
│   │   ├── __init__.py      # Exports all domain models and enums
│   │   ├── base.py          # DeclarativeBase, UUIDPrimaryKeyMixin, TimestampMixin
│   │   ├── user.py          # User account entity
│   │   ├── applicant.py     # ApplicantProfile entity
│   │   ├── application.py   # Application entity
│   │   ├── consent.py       # Consent entity
│   │   ├── financial_signal.py # FinancialSignal entity
│   │   ├── assessment.py    # CreditAssessment entity
│   │   ├── model_version.py # ModelVersion entity
│   │   ├── review.py        # ReviewOutcome entity
│   │   └── audit.py         # AuditLog entity
│   ├── services/
│   │   └── __init__.py      # Business logic orchestration (placeholder)
│   └── repositories/
│       └── __init__.py      # Data persistence abstraction (placeholder)
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py       # API endpoints and database health tests
│   ├── test_database.py     # Database engine, session, and unit/integration tests
│   └── test_models.py       # Domain model structure, relationship, and constraint tests
│
├── .env.example             # Example configuration template with DATABASE_URL
├── .gitignore               # Ignored files (.env, .venv, caches)
├── requirements.txt         # Current backend dependencies
└── README.md                # Comprehensive documentation & architecture guide
```
