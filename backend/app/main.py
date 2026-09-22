from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Backend API for the PARAKH alternative credit-assessment prototype for gig workers.",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register centralized exception handlers for domain & assessment errors
register_exception_handlers(app)


@app.get("/", summary="Root Status")
def read_root() -> dict:
    """Root endpoint returning basic service status."""
    return {"message": "PARAKH API is running"}


@app.get("/health", summary="Health Check")
def health_check() -> dict:
    """Health check endpoint for service monitoring."""
    return {"status": "healthy"}


# Mount the central API router with configured prefix (default: /api/v1)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
