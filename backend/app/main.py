from fastapi import FastAPI
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
