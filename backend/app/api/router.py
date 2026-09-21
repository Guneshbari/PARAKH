"""Central API router aggregating all versioned domain endpoints."""
from fastapi import APIRouter
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


# Future domain routers will be included here:
# e.g., api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# e.g., api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
