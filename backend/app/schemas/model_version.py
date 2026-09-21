"""Pydantic schemas for ModelVersion entity."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ModelVersionBase(BaseModel):
    """Base fields for algorithmic model version tracking."""

    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    version: str = Field(..., min_length=1, max_length=50, description="Semantic version string")
    algorithm: Optional[str] = Field(None, max_length=100, description="Algorithm architecture or family")
    description: Optional[str] = Field(None, description="Detailed model purpose and features")
    is_active: bool = Field(default=True, description="Whether this version is available for active scoring")


class ModelVersionCreate(ModelVersionBase):
    """Schema for registering a new model version."""

    pass


class ModelVersionResponse(ModelVersionBase):
    """Response schema for model version provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
