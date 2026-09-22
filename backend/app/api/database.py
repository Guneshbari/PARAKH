"""Database connectivity and health check router."""
import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.common import DatabaseHealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=DatabaseHealthResponse,
    summary="Database Connectivity Health Check",
    description="Executes a lightweight query (SELECT 1) to verify active database connectivity.",
    responses={
        status.HTTP_200_OK: {
            "description": "Database connection is active and healthy",
            "model": DatabaseHealthResponse,
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database is unreachable or disconnected",
            "model": DatabaseHealthResponse,
        },
    },
)
def check_database_health(db: Session = Depends(get_db)):
    """Verify database connection health via SELECT 1 query."""
    try:
        db.execute(text("SELECT 1"))
        return DatabaseHealthResponse(
            status="healthy",
            database="connected",
        )
    except Exception:
        logger.error("Database health check failed: unable to execute ping query")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
            },
        )
