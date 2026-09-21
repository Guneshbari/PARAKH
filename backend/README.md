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
   Business logic and orchestration layer encapsulating domain workflows, validations, and transaction boundaries.
7. **Repositories (`app/repositories/`)**:
   Data access abstraction isolating database queries and persistence mechanisms from business logic.

> **Note**: Both the repository and service layers are fully implemented and tested. Authentication (JWT), ML scoring algorithms, and domain API routers will be introduced in subsequent tasks.

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
- Repositories **do not** make scoring decisions, calculate financial risk, enforce consent policy, hash passwords, or generate audit events. Orchestration and domain decisions remain strictly in the Service Layer.

---

## 8. Service Layer (`app/services/`)

The service layer is responsible for business logic, validation rules, workflow state machines, and transaction boundaries across the application:

```
HTTP Request / FastAPI
       ↓
 Service Layer (`app/services/`)
       ↓
Repository Layer (`app/repositories/`)
       ↓
SQLAlchemy Models (`app/models/`)
       ↓
PostgreSQL Database
```

### Domain Services & Responsibilities
- **`UserService`**:
  - Normalizes email addresses (lowercase, trimmed).
  - Enforces email uniqueness via `DuplicateEntityError`.
  - Dispatches entity creation and updates through `UserRepository`.
  - Shields sensitive credential attributes from leaking.
- **`ApplicantService`**:
  - Manages gig worker profile creation and updates.
  - Verifies existence of the associated `User` account.
  - Enforces one-to-one constraint between User and `ApplicantProfile`.
- **`ApplicationService`**:
  - Manages alternative credit assessment applications.
  - Validates applicant existence and verifies `requested_loan_amount > 0`.
  - Implements a strict status transition state machine:
    - `DRAFT → SUBMITTED`
    - `SUBMITTED → UNDER_REVIEW`
    - `UNDER_REVIEW → ASSESSED` or `MANUAL_REVIEW`
    - `MANUAL_REVIEW → ASSESSED`
    - `ASSESSED → COMPLETED`
    - Rejects invalid or backward status transitions with `InvalidStateTransitionError`.
- **`ConsentService`**:
  - Enforces explicit consent creation requiring application existence and applicant/profile ownership verification.
  - Guarantees consent cannot be silently implied; requires explicit grant state (`granted=True`) and records `granted_at`.
  - Implements reusable authorization verification: `has_active_consent(application_id, data_source, applicant_profile_id=None)` and `require_active_consent(...)`.
  - Evaluates consent independently per data source category (`PLATFORM`, `FINANCIAL_ACTIVITY`, `UTILITY`).
  - Implements soft revocation: marks `granted=False` and timestamps `revoked_at` without deleting historical audit records.
  - Strictly prevents cross-application authorization leakage (consents for Application A never authorize access for Application B).
- **`FinancialSignalService`**:
  - Persists aggregated and derived platform metrics (`average_income`, `payment_regularity`, `volatility`).
  - Enforces strict data-minimization rules: immediately rejects raw transaction logs, bank account numbers, UPI IDs, raw bank statements, merchant names, GPS coordinates, contacts, and passwords with `ValidationError`.
  - Supports authorization verification via `create_signal(..., enforce_consent=True)` or `create_signal_with_consent(...)` rejecting unauthorized ingestion with `ConsentRequiredError`.
- **`AssessmentService`**:
  - Manages credit evaluation output persistence and history.
  - Validates application and model version linkages.
  - Enforces strict bounds on `risk_probability` (0.0 to 1.0) and `confidence` (0.0 to 1.0).
- **`ModelVersionService`**:
  - Manages algorithmic model registry and metadata.
  - Provides active scoring model resolution and provenance tracking.
- **`ReviewService`**:
  - Captures human credit officer adjudication decisions and notes.
  - Validates reviewer user existence and application association.

### Domain Exception Architecture
Defined in `app/services/exceptions.py`, domain-level exceptions decouple raw database/driver errors from API consumers:
- `ServiceError`: Base application service error.
- `EntityNotFoundError`: Raised when an entity is missing.
- `DuplicateEntityError`: Raised on uniqueness violations (e.g. duplicate email, duplicate profile).
- `InvalidStateTransitionError`: Raised when an illegal lifecycle status change is requested.
- `ValidationError`: Raised on business logic constraint failures (e.g. prohibited raw data, invalid linkages).
- `ConsentRequiredError`: Raised when an operation attempts to access or process a data source without active, unrevoked consent.

### Transaction Boundaries & Rollback
- Repositories default to `flush()` without auto-committing.
- Services define the transaction unit of work boundary: executing repository changes, committing on success, and executing `self.db.rollback()` upon unexpected failures before propagating errors.

---

## 9. Assessment Engine Interface (`app/assessment/`)

The assessment engine interface establishes a framework-independent, decoupled contract defining how alternative credit scoring mechanisms ingest applicant and financial features and produce credit decisions.

### Architecture & Decoupling
```
Application / Financial Signals / Applicant Profile
                       ↓
         AssessmentInput (Adapter / Contract)
                       ↓
          AssessmentEngine (Abstract ABC)
       ┌───────────────┴───────────────┐
       ↓                               ↓
TASK 10 Mock Engine         Future ML / XGBoost Model
       └───────────────┬───────────────┘
                       ↓
         AssessmentResult (Standardized Output)
                       ↓
   CreditAssessment (Persistence / Domain Model)
```

### Core Interface Components
1. **`AssessmentEngine` (`app/assessment/base.py`)**:
   - Abstract Base Class (`abc.ABC`) defining the scoring contract.
   - Requires concrete engines to implement `assess(input_data: AssessmentInput) -> AssessmentResult`.
   - Exposes model provenance properties (`engine_name`, `engine_version`).
   - Completely independent from SQLAlchemy sessions, repositories, FastAPI routes, and external ML frameworks.

2. **`AssessmentInput` (`app/assessment/schemas.py`)**:
   - Strict Pydantic contract encapsulating only the aggregate features required for assessment:
     - Application identifiers and loan terms (`requested_loan_amount`, `loan_tenure_months`, `loan_purpose`).
     - Gig work profile indicators (`gig_work_type`, `years_working`, `average_working_days`).
     - Derived, aggregated financial metrics (`average_income`, `payment_regularity`, `volatility`, `cashflow_buffer`, `existing_obligation`, `platform_rating`).
     - Sanitized custom derived features dictionary (`derived_features`).
   - Features adapter method `AssessmentInput.from_domain_objects(...)` to build inputs directly from application, profile, and signal models.

3. **`AssessmentResult` (`app/assessment/schemas.py`)**:
   - Standardized evaluation output containing:
     - `score`: Alternative credit score bounded `[0, 1000]` (nullable for cold-start / insufficient evidence).
     - `risk_probability`: Estimated probability of default bounded `[0, 1]`.
     - `confidence`: Model confidence level bounded `[0, 1]`.
     - `risk_level`: Categorical risk tier strictly reusing the domain `RiskLevel` enum (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`).
     - Model provenance (`model_name`, `model_version`).
     - Key driving factors and explainability metadata (`key_factors`, `explanation`).
   - Features adapter method `to_credit_assessment_create(...)` to seamlessly bridge output into the `CreditAssessmentCreate` schema.

4. **Engine Exceptions (`app/assessment/exceptions.py`)**:
   - `AssessmentEngineError`: Base exception for engine failures.
   - `AssessmentInputError`: Raised when input data is malformed, missing required fields, or violates privacy policies.
   - `AssessmentNotImplementedError`: Raised when a requested scoring algorithm or mode is unsupported.
   - `AssessmentOutputError`: Raised when an engine returns unexpected or invalid output.

### Privacy & Data Minimization Boundary
The assessment contract strictly enforces PARAKH's data-minimization architecture:
- Declares `model_config = ConfigDict(extra="forbid")` on `AssessmentInput` to prevent unapproved fields.
- Implements recursive validator `validate_privacy_and_prohibited_fields` rejecting any raw or privacy-invasive attributes:
  - Raw bank transactions, statements, or ledger rows
  - Raw UPI logs, transaction IDs, or VPA handles
  - Merchant names, descriptions, or transaction details
  - GPS coordinates, location traces, or travel history
  - Phone contacts or address book entries
  - Bank credentials, passwords, or authentication secrets

### Service Integration & Dependency Injection
`AssessmentService` accepts an optional engine dependency:
```python
service = AssessmentService(db=session, engine=my_engine)
assessment = service.assess_application(application_id=app_id)
```
- Decoupled execution: `AssessmentService` builds `AssessmentInput`, invokes `engine.assess()`, validates output types, and persists the resulting `CreditAssessment` record through standard transactional unit-of-work semantics.

### Mock Assessment Engine (`app/assessment/mock.py`)
Introduced in **TASK 10**, `MockAssessmentEngine` is a concrete, deterministic implementation of `AssessmentEngine`. It provides a predictable rule-based scoring engine for development, integration testing, and UI validation before real machine learning models (TASK 14) are deployed.

> [!WARNING]
> **DEVELOPMENT / DEMO ENGINE ONLY**: The scores and risk probabilities computed by `MockAssessmentEngine` are deterministic rule-based heuristics designed for system verification. They do **NOT** represent actual creditworthiness evaluations or statistical model predictions.

#### Deterministic Scoring Formula & Weights
The engine constructs six normalized component indices `[0.0, 1.0]` using explicit, transparent weights:
- **Income Stability (25%)**: Evaluates monthly income benchmark (40,000 INR baseline), deducted for earnings volatility, and adjusted for income trajectory (growing/stable/declining).
- **Payment Reliability (25%)**: Evaluates gig platform payout regularity and historical platform repayment consistency.
- **Work Stability (15%)**: Evaluates gig economy tenure (4-year benchmark) and active working days per month (26-day benchmark).
- **Cashflow Strength (15%)**: Evaluates cash buffer reserves relative to requested loan principal.
- **Obligation Burden (10%)**: Evaluates debt-to-income (DTI) ratio; lower existing debt yields higher score.
- **Platform Reliability (10%)**: Evaluates composite customer service rating (scaled above 3.0 stars).

#### Score & Risk Mappings
- **Composite Score**: `score = int(300 + composite_index * 550)`, bounded strictly within `[300, 850]` (or `None` if evidence is insufficient).
- **Risk Probability**: Deterministically derived as `1.0 - (composite_index * 0.90 + 0.05)`, bounded within `[0.01, 0.99]`.
- **Risk Level**:
  - `score >= 700`: `RiskLevel.LOWER`
  - `550 <= score < 700`: `RiskLevel.MODERATE`
  - `score < 550`: `RiskLevel.HIGHER`
  - Insufficient data: `RiskLevel.INSUFFICIENT`
- **Confidence**: Evidence completeness metric `[0.20, 0.95]` based on the proportion of populated approved signals.
- **Insufficient Evidence Handling**: If fewer than 2 independent signal categories are populated, the engine returns `score = None`, `risk_level = RiskLevel.INSUFFICIENT`, a baseline neutral probability (`0.5000`), and explanatory factors requesting additional data connections.
- **Explainability Output**:
  - `key_factors`: Deterministic human-readable bullet points highlighting driving indicators (e.g. *"Strong platform payout regularity"*, *"Elevated debt-to-income ratio"*).
  - `explanation`: Detailed dictionary containing raw components, weights, and engine metadata.

---

## 10. Local Setup & Configuration

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

## 11. Database Migrations (Alembic)

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

## 12. Endpoints

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

## 13. Running Tests

Run the full unit and integration test suite:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

- **Unit tests**: Validate configuration, SQLAlchemy engine creation, DeclarativeBase inheritance, `get_db()` lifecycle, domain model relationships, constraints, data minimization, Alembic configuration/offline migrations, Pydantic schema validation/ORM compatibility, repository CRUD/specialized query behavior, service business rules/validations/state machines, consent/privacy authorization enforcement, and assessment engine contracts/validation.
- **Integration tests**: Automatically execute live `SELECT 1`, repository queries, service transactional workflows, end-to-end consent lifecycle/revocation checks, and assessment engine execution/persistence against PostgreSQL if available. If PostgreSQL is offline locally, integration tests skip gracefully without failing the build.

---

## 14. Project Structure
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
│   ├── assessment/
│   │   ├── __init__.py      # Exports AssessmentEngine, MockAssessmentEngine, contracts
│   │   ├── base.py          # Abstract Base Class AssessmentEngine
│   │   ├── mock.py          # MockAssessmentEngine deterministic rule scoring implementation
│   │   ├── schemas.py       # AssessmentInput, AssessmentResult, data minimization
│   │   └── exceptions.py    # AssessmentEngineError, AssessmentInputError, etc.
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
│       ├── __init__.py      # Exports all domain services and exceptions
│       ├── exceptions.py    # Domain service exceptions (EntityNotFoundError, ConsentRequiredError, etc.)
│       ├── user.py          # UserService
│       ├── applicant.py     # ApplicantService
│       ├── application.py   # ApplicationService
│       ├── consent.py       # ConsentService
│       ├── financial_signal.py # FinancialSignalService
│       ├── assessment.py    # AssessmentService
│       ├── model_version.py # ModelVersionService
│       └── review.py        # ReviewService
│
├── tests/
│   ├── __init__.py
│   ├── test_health.py       # API endpoints and database health tests
│   ├── test_database.py     # Database engine, session, and unit/integration tests
│   ├── test_models.py       # Domain model structure, relationship, and constraint tests
│   ├── test_migrations.py   # Alembic configuration and migration generation tests
│   ├── test_schemas.py      # Pydantic request/response schema validation & ORM tests
│   ├── test_repositories.py # Repository CRUD and specialized query tests
│   ├── test_services.py     # Service layer business logic, validation, and workflow tests
│   ├── test_consent_privacy.py # Consent authorization, independent sources & privacy tests
│   ├── test_assessment_engine.py # Assessment engine interface, contracts, & privacy tests
│   └── test_mock_assessment_engine.py # Mock assessment engine deterministic scoring tests
│
├── .env.example             # Example configuration template with DATABASE_URL
├── .gitignore               # Ignored files (.env, .venv, caches)
├── requirements.txt         # Current backend dependencies
└── README.md                # Comprehensive documentation & architecture guide
```

