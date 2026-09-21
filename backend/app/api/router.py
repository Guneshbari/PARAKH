"""Central API router aggregating all versioned domain endpoints."""
from fastapi import APIRouter
from app.api.database import router as database_router
from app.core.config import settings
from app.schemas.common import StatusResponse

api_router = APIRouter()


@api_router.get(
    "/status",
    response_model=StatusResponse,
    summary="API Service Status",
    description="Returns service availability, service name, and current version.",
)
def get_status() -> StatusResponse:
    """Return operational status and metadata for the API layer."""
    return StatusResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.VERSION,
    )


# Database endpoints: /api/v1/database/health
api_router.include_router(
    database_router,
    prefix="/database",
    tags=["database"],
)

# Domain v1 endpoints
from app.api.v1.router import v1_router

api_router.include_router(v1_router)
