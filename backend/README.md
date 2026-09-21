# PARAKH — Backend

## 1. Overview
**PARAKH** is an alternative credit-assessment platform and prototype designed for gig and platform workers. It leverages multi-source financial and non-traditional behavioral data (e.g., platform earnings, delivery regularity, cash-flow consistency) to generate transparent, explainable credit scores and facilitate credit inclusion.

This directory (`PARAKH/backend/`) contains the **FastAPI** backend service responsible for serving the core API, orchestrating data ingestion, executing credit assessments, and delivering explanations.

---

## 2. Current Backend Technology Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python web framework for high-performance APIs)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
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
Database / External Sources (app/models/)
```

### Architectural Components:
1. **API Layer (`app/api/`)**:
   Exposes HTTP routes via FastAPI routers. The central router (`api/router.py`) prefixes versioned endpoints (default `/api/v1`) and will aggregate future domain-specific subrouters (e.g., auth, applicants, applications, assessments).
2. **Schemas (`app/schemas/`)**:
   Pydantic models defining input validation rules and output response serialization contracts (e.g., `StatusResponse`).
3. **Services (`app/services/`)**:
   Business logic and orchestration layer. Will house workflows for credit assessment calculations, consent handling, and external integrations.
4. **Repositories (`app/repositories/`)**:
   Data access abstraction isolating database queries and persistence mechanisms from business logic.
5. **Models (`app/models/`)**:
   Domain models and database entity definitions.

> **Note**: `services/`, `repositories/`, and `models/` currently represent architectural boundaries prepared for future implementation. Database (PostgreSQL/SQLAlchemy), authentication (JWT), and ML scoring logic do not exist yet and will be added in subsequent tasks.

---

## 4. Setup and Installation Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- `venv` module for virtual environment management

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
   Copy the example environment file to create your local `.env`:
   ```bash
   cp .env.example .env
   ```
   Modify `.env` as required (defaults work out-of-the-box for local development).

---

## 5. Running the Development Server

Start the FastAPI application with auto-reload:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The application will be accessible at:
- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

---

## 6. Endpoints

| Method | Endpoint | Description | Sample Response |
|---|---|---|---|
| `GET` | `/` | API root message | `{"message": "PARAKH API is running"}` |
| `GET` | `/health` | Health check endpoint | `{"status": "healthy"}` |
| `GET` | `/api/v1/status` | Versioned API service status | `{"status": "ok", "service": "PARAKH API", "version": "0.1.0"}` |

### Testing with curl
```bash
# Check root endpoint
curl -s http://127.0.0.1:8000/

# Check health endpoint
curl -s http://127.0.0.1:8000/health

# Check versioned API status endpoint
curl -s http://127.0.0.1:8000/api/v1/status
```

---

## 7. Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance and router registration
│   ├── api/
│   │   ├── __init__.py
│   │   └── router.py        # Central API router with versioned routes
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Configuration management with pydantic-settings
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py        # Common Pydantic response/request models
│   ├── services/
│   │   └── __init__.py      # Business logic orchestration (placeholder)
│   ├── repositories/
│   │   └── __init__.py      # Data access layer (placeholder)
│   └── models/
│       └── __init__.py      # Database entities (placeholder)
│
├── tests/
│   ├── __init__.py
│   └── test_health.py       # API endpoint test suite
│
├── .env.example             # Example environment configuration
├── .gitignore               # Backend-specific ignore patterns
├── requirements.txt         # Current backend dependencies
└── README.md                # Documentation and architecture guide
```
