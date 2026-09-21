"""Common Pydantic schemas across the application."""
from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Response schema for API status check."""

    status: str
    service: str
    version: str
