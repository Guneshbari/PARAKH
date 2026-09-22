"""Pydantic schemas for AuditLog entity."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuditLogResponse(BaseModel):
    """Response schema for immutable audit trail events."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    action: str = Field(..., description="Action name or event identifier")
    entity_type: str = Field(..., description="Entity category affected by event")
    entity_id: Optional[str] = Field(None, description="Identifier of modified entity")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured non-sensitive audit metadata",
    )
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def extract_audit_metadata(cls, data: Any) -> Any:
        """Extract audit_metadata from ORM objects to avoid collision with SQLAlchemy Base.metadata."""
        if hasattr(data, "audit_metadata"):
            return {
                "id": getattr(data, "id", None),
                "user_id": getattr(data, "user_id", None),
                "application_id": getattr(data, "application_id", None),
                "action": getattr(data, "action", None),
                "entity_type": getattr(data, "entity_type", None),
                "entity_id": getattr(data, "entity_id", None),
                "metadata": getattr(data, "audit_metadata", None),
                "created_at": getattr(data, "created_at", None),
            }
        return data
