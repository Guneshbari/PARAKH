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

## 3. Current Scope (Task 1 — Backend Project Setup)
Task 1 establishes the initial backend foundation and minimal skeleton:
- FastAPI application initialization with metadata and OpenAPI documentation.
- Environment-based configuration with Pydantic Settings.
- Standard health check (`/health`) and root (`/`) endpoints.
- Isolated project structure and dependency specifications.

> **Note**: Database (PostgreSQL/SQLAlchemy/Alembic), Authentication (JWT), ML scoring models (LightGBM/XGBoost/SHAP), and background workers are deferred to subsequent implementation tasks.

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
| `GET` | `/` | API status and greeting | `{"message": "PARAKH API is running"}` |
| `GET` | `/health` | Health check endpoint | `{"status": "healthy"}` |

### Testing with curl
```bash
# Check root endpoint
curl -s http://127.0.0.1:8000/

# Check health endpoint
curl -s http://127.0.0.1:8000/health
```

---

## 7. Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance and route definitions
│   └── core/
│       ├── __init__.py
│       └── config.py        # Settings management with pydantic-settings
│
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Basic API endpoint tests
│
├── .env.example             # Example environment configuration
├── .gitignore               # Backend-specific ignore patterns
├── requirements.txt         # Current backend dependencies
└── README.md                # Documentation and setup instructions
```
