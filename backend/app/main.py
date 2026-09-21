from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Backend API for the PARAKH alternative credit-assessment prototype for gig workers.",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/")
def read_root() -> dict:
    """Root endpoint returning basic service status."""
    return {"message": "PARAKH API is running"}


@app.get("/health")
def health_check() -> dict:
    """Health check endpoint for service monitoring."""
    return {"status": "healthy"}
