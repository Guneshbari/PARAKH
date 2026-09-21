# PARAKH — Backend

## 1. Overview
**PARAKH** is an alternative credit-assessment platform and prototype designed for gig and platform workers. It leverages multi-source financial and non-traditional behavioral data (e.g., platform earnings, delivery regularity, cash-flow consistency) to generate transparent, explainable credit scores and facilitate credit inclusion.

This directory (`PARAKH/backend/`) contains the **FastAPI** backend service responsible for serving the core API, orchestrating data ingestion, executing credit assessments, and delivering explanations.

---

## 2. Current Backend Technology Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python web framework for high-performance APIs)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Data Validation & Contracts**: [Pydantic v2](https://docs.pydantic.dev/) and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- **Database ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (SQL toolkit and Object Relational Mapper)
- **Database Migrations**: [Alembic](https://alembic.sqlalchemy.org/) (Schema migration environment)
- **Database Driver**: [psycopg (v3)](https://www.psycopg.org/) (High-performance PostgreSQL adapter)
- **Relational Database**: [PostgreSQL](https://www.postgresql.org/)
- **Environment Management**: [python-dotenv](https://github.com/theskumar/python-dotenv)

---

## 3. Backend Architecture & Layers

The backend follows a layered architecture to keep concerns cleanly decoupled as features are introduced:

```
HTTP Request
    ↓
API Layer (app/api/)
    ↓
Pydantic Request Schemas (app/schemas/)
    ↓
Service Layer (app/services/)
    ↓
Repository Layer (app/repositories/)
    ↓
SQLAlchemy Models (app/models/)
    ↓
PostgreSQL Database
    ↓
Pydantic Response Schemas (app/schemas/)
    ↓
HTTP Response
```

### Architectural Components:
1. **API Layer (`app/api/`)**:
   Exposes HTTP routes via FastAPI routers. The central router (`api/router.py`) aggregates versioned domain subrouters (e.g., `api/database.py`).
2. **Schemas Layer (`app/schemas/`)**:
   Pydantic v2 contracts defining strong typing, input validation, and output serialization separate from database models.
3. **Database & Core (`app/core/`)**:
   Contains application settings (`config.py`) and database infrastructure (`database.py`), including the engine, session factory (`SessionLocal`), and the request-scoped database dependency (`get_db()`).
4. **Models (`app/models/`)**:
   SQLAlchemy 2.0 domain entities and DeclarativeBase providing the data model for accounts, profiles, applications, consents, signals, and assessments.
5. **Migrations (`alembic/`)**:
   Managed schema evolution using Alembic revisions tied to `Base.metadata`.
6. **Services (`app/services/`)**:
   Business logic and orchestration layer. Will house workflows for credit assessment calculations, consent handling, and external integrations.
7. **Repositories (`app/repositories/`)**:
   Data access abstraction isolating database queries and persistence mechanisms from business logic.

> **Note**: `services/` represents an architectural boundary prepared for upcoming tasks. The repository layer is fully implemented and tested. Authentication (JWT) and ML scoring logic will be introduced in subsequent tasks.

---

## 4. Database Foundation

- **Relational Database**: PostgreSQL is the primary database for application state, audit logs, and structured assessments.
- **ORM & Abstraction**: SQLAlchemy 2.0 provides declarative modeling, type safety, and connection pool management.
- **Driver**: `psycopg` (v3 with binary extensions) serves as the modern DBAPI driver.
- **Declarative Base**: Defined in `app/models/base.py` with common mixins for UUID primary keys and timezone-aware timestamps.
- **Session Lifecycle**: The `get_db()` dependency yields a scoped SQLAlchemy `Session` per request and ensures it is reliably closed upon completion.
- **Schema Migrations**: Schema evolution is strictly managed via Alembic (never `Base.metadata.create_all()`).

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
6. **CreditAssessment (`credit_assessments`)**: Generated assessment output including `credit_score`, `risk_probability`, `risk_level` (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`), `confidence`, and financial health ratios. Nullable values are supported when evidence is insufficient.
7. **ModelVersion (`model_versions`)**: Traceability record identifying the specific scoring model, version string, algorithm name, and description used to produce an assessment.
8. **ReviewOutcome (`review_outcomes`)**: Decision support record capturing human reviewer evaluation (`REVIEWED`, `ESCALATED`, `ADDITIONAL_INFORMATION_REQUIRED`) with notes.
9. **AuditLog (`audit_logs`)**: Immutable audit trail of system and user events with JSONB metadata. Foreign keys use `ON DELETE SET NULL` to preserve historical integrity.

---

## 6. Pydantic Schema Layer

The schema layer (`app/schemas/`) defines explicit API request and response contracts, decoupled from the internal database models:

### Schema Roles:
1. **Request Schemas** (e.g. `UserCreate`, `ApplicantProfileCreate`, `ApplicationCreate`, `ConsentCreate`, `FinancialSignalCreate`, `ReviewOutcomeCreate`):
   Validate incoming payload data from API consumers, applying boundary constraints (e.g. loan amount > 0, email format check, string length limits).
2. **Response Schemas** (e.g. `UserResponse`, `ApplicantProfileResponse`, `ApplicationResponse`, `CreditAssessmentResponse`, `ReviewOutcomeResponse`, `AuditLogResponse`):
   Define serialization contracts sent back to clients, ensuring sensitive internal attributes are omitted.
3. **Summary Schemas** (e.g. `UserSummary`, `ApplicationSummary`):
   Lightweight projections optimized for listing and summary endpoints.

### ORM Serialization & Compatibility:
All response schemas declare:
```python
model_config = ConfigDict(from_attributes=True)
```
This enables seamless conversion from SQLAlchemy ORM entities via `Schema.model_validate(orm_instance)` without manual dict mapping.

### Validation Rules:
- **Loan Amount**: `requested_loan_amount > 0`
- **Probabilities & Confidence**: `risk_probability` and `confidence` bounded strictly between `0` and `1`.
- **Experience & Activity**: `years_working >= 0`, `average_working_days` between `0` and `31`.
- **Monetary Signals**: `average_income`, `median_income`, `cashflow_buffer`, and `existing_obligation` must be `>= 0`.
- **Email Validation**: Case-normalized and regex-validated without third-party external dependencies.

### Privacy Boundary & Data Minimization:
- **Zero Credential Exposure**: `UserResponse` and `UserSummary` strictly exclude `password_hash` and plaintext passwords.
- **Aggregated Indicators Only**: `FinancialSignal` schemas contain only derived summary metrics (`average_income`, `payment_regularity`, `volatility`). They strictly forbid raw bank transactions, raw UPI descriptions, merchant names, GPS/location coordinates, contacts, or bank login credentials.

---

## 7. Repository Layer (`app/repositories/`)

The repository layer isolates database access from business logic and service orchestration. Built with SQLAlchemy 2.0, it provides type-safe, generic persistence methods and entity-specific query abstractions.

### BaseRepository Pattern
Located in `app/repositories/base.py`, `BaseRepository[ModelType]` provides reusable generic CRUD operations:
- `create(obj_in, commit=False, db=None)`: Accepts entity instances or attribute dictionaries, flushes to populate primary keys and default values, and optionally commits.
- `get_by_id(id, db=None)`: Retrieves an entity by UUID, string UUID, or integer primary key.
- `get_all(skip=0, limit=100, db=None)`: Fetches paginated records.
- `update(db_obj, obj_in, commit=False, db=None)`: Updates attributes from dictionaries, Pydantic schemas, or object instances.
- `delete(id, commit=False, db=None)`: Deletes an entity by primary key.

### Domain Repositories
Domain-specific repositories inherit from `BaseRepository` to encapsulate specialized domain queries:
- **`UserRepository`**: User lookup by normalized email (`get_by_email`).
- **`ApplicantRepository`** (alias `ApplicantProfileRepository`): Profile lookup by user ID (`get_by_user_id`).
- **`ApplicationRepository`**: Listing by applicant profile with descending sort, status transitions (`update_status`).
- **`ConsentRepository`**: Application consent retrieval, active consent filtering (`get_active_consents`), and revocation stamping (`revoke`).
- **`FinancialSignalRepository`**: Application signals retrieval, most recent signal lookup (`get_latest`).
- **`AssessmentRepository`** (alias `CreditAssessmentRepository`): Application assessment history, latest evaluation retrieval (`get_latest`).
- **`ModelVersionRepository`**: Active algorithmic model version retrieval (`get_active`), version listing (`list_versions`).
- **`ReviewRepository`** (alias `ReviewOutcomeRepository`): Human adjudication queries by application and reviewer (`get_by_reviewer`).
- **`AuditRepository`** (alias `AuditLogRepository`): Immutable audit trails queried by application and user ID.

### Session Management & Dependency Injection
Repositories support flexible session binding:
1. **Instance-scoped session**: `repo = UserRepository(db)` initialized within a request lifecycle or dependency.
2. **Method-scoped session**: `repo.get_by_email(email, db=db)` allowing dynamic session injection or transactional overrides.

### Transaction Handling & Unit of Work
- By default, repository operations call `session.flush()` rather than `session.commit()`.
- This ensures generated primary keys (UUIDs) and database defaults are populated while allowing the caller (e.g. Service Layer) to compose multi-repository operations atomically within a single transaction.
- When independent single-record operations require immediate persistence, `commit=True` may be explicitly requested.

### Decoupling from Business Logic
- Repositories perform database access only.
- Repositories **do not** make scoring decisions, calculate financial risk, enforce consent policy, hash passwords, or generate audit events. Orchestration and domain decisions remain strictly in the upcoming Service Layer.

---

## 8. Local Setup & Configuration

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- PostgreSQL 14+ installed and running locally (optional for offline testing and SQL generation)

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

## 9. Database Migrations (Alembic)

Schema migrations are managed with Alembic. The database connection URL is dynamically read from `app.core.config.settings.DATABASE_URL` without hardcoding credentials into source files.

### Common Migration Commands

1. **Activate the virtual environment**:
   ```bash
   cd backend
   source .venv/bin/activate
   ```

2. **Check current applied revision**:
   ```bash
   alembic current
   ```

3. **View revision history**:
   ```bash
   alembic history --verbose
   ```

4. **Apply migrations to latest version (when PostgreSQL is active)**:
   ```bash
   alembic upgrade head
   ```

5. **Generate future migrations automatically from models**:
   ```bash
   alembic revision --autogenerate -m "description_of_changes"
   ```

6. **Generate SQL offline (without connecting to PostgreSQL)**:
   ```bash
   alembic upgrade base:head --sql
   ```

7. **Revert the last migration**:
   ```bash
   alembic downgrade -1
   ```

---

## 10. Endpoints

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

---

## 11. Running Tests

Run the full unit and integration test suite:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

- **Unit tests**: Validate configuration, SQLAlchemy engine creation, DeclarativeBase inheritance, `get_db()` lifecycle, domain model relationships, constraints, data minimization, Alembic configuration/offline migrations, Pydantic schema validation/ORM compatibility, and repository CRUD/specialized query behavior.
- **Integration tests**: Automatically attempt live `SELECT 1` and repository queries against PostgreSQL if available. If PostgreSQL is offline locally, integration tests skip gracefully without failing the build.

---

## 12. Project Structure
```
backend/
├── alembic.ini               # Alembic CLI configuration (credentials omitted)
├── alembic/
│   ├── env.py                # Migration runtime environment configured with Base.metadata
│   ├── script.py.mako        # Migration script generation template
│   └── versions/
│       └── fd385d59e799_initial_schema.py  # Initial PARAKH schema migration
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
│   │   ├── __init__.py      # Exports all public request/response schemas
│   │   ├── common.py        # StatusResponse and DatabaseHealthResponse schemas
│   │   ├── user.py          # UserCreate, UserResponse, UserSummary, UserUpdate
│   │   ├── applicant.py     # ApplicantProfileCreate, ApplicantProfileResponse, etc.
│   │   ├── application.py   # ApplicationCreate, ApplicationResponse, etc.
│   │   ├── consent.py       # ConsentCreate, ConsentResponse
│   │   ├── financial_signal.py # FinancialSignalCreate, FinancialSignalResponse
│   │   ├── assessment.py    # CreditAssessmentCreate, CreditAssessmentResponse
│   │   ├── model_version.py # ModelVersionCreate, ModelVersionResponse
│   │   ├── review.py        # ReviewOutcomeCreate, ReviewOutcomeResponse
│   │   └── audit.py         # AuditLogResponse
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
│   ├── repositories/
│   │   ├── __init__.py      # Exports all domain repositories and BaseRepository
│   │   ├── base.py          # BaseRepository generic CRUD implementation
│   │   ├── user.py          # UserRepository
│   │   ├── applicant.py     # ApplicantRepository & ApplicantProfileRepository
│   │   ├── application.py   # ApplicationRepository
│   │   ├── consent.py       # ConsentRepository
│   │   ├── financial_signal.py # FinancialSignalRepository
│   │   ├── assessment.py    # AssessmentRepository & CreditAssessmentRepository
│   │   ├── model_version.py # ModelVersionRepository
│   │   ├── review.py        # ReviewRepository & ReviewOutcomeRepository
│   │   └── audit.py         # AuditRepository & AuditLogRepository
│   └── services/
│       └── __init__.py      # Business logic orchestration (placeholder)
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py       # API endpoints and database health tests
│   ├── test_database.py     # Database engine, session, and unit/integration tests
│   ├── test_models.py       # Domain model structure, relationship, and constraint tests
│   ├── test_migrations.py   # Alembic configuration and migration generation tests
│   ├── test_schemas.py      # Pydantic request/response schema validation & ORM tests
│   └── test_repositories.py # Repository CRUD and specialized query unit/integration tests
│
├── .env.example             # Example configuration template with DATABASE_URL
├── .gitignore               # Ignored files (.env, .venv, caches)
├── requirements.txt         # Current backend dependencies
└── README.md                # Comprehensive documentation & architecture guide
```

