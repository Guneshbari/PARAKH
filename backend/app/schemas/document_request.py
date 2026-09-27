"""Pydantic schemas for DocumentRequest entity."""
from datetime import datetime
import enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.document_request import AllowedFileType, DocumentRequestStatus, DocumentType


class DocumentRequestBase(BaseModel):
    """Base schema for document verification request."""

    document_type: DocumentType = Field(..., description="Type of verification document required")
    description: str = Field(..., min_length=5, description="Clear details and instructions for the document request")
    allowed_file_types: List[AllowedFileType] = Field(..., min_length=1, description="List of accepted file formats (PDF, XLS, XLSX)")

    @field_validator("description")
    @classmethod
    def validate_description_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 5:
            raise ValueError("Description must contain at least 5 meaningful characters.")
        return cleaned

    @field_validator("allowed_file_types")
    @classmethod
    def validate_allowed_file_types(cls, v: List[AllowedFileType]) -> List[AllowedFileType]:
        if not v:
            raise ValueError("At least one allowed file type must be specified.")
        valid_values = {f.value for f in AllowedFileType}
        for item in v:
            val = item.value if hasattr(item, "value") else str(item)
            if val not in valid_values:
                raise ValueError(f"Unsupported file format '{val}'. Allowed formats are: {sorted(list(valid_values))}")
        # Return unique preserved order
        seen = set()
        deduped = []
        for item in v:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped


class DocumentRequestCreate(DocumentRequestBase):
    """Schema for creating a document request directly."""

    application_id: Optional[UUID] = Field(None, description="Application UUID (inferred from URL route)")
    review_id: Optional[UUID] = Field(None, description="Associated ReviewOutcome UUID if created via review workflow")


class DocumentRequestCreateNested(DocumentRequestBase):
    """Schema for embedded document request creation inside ReviewOutcomeCreate."""

    pass


class SubmittedDocumentResponse(BaseModel):
    """Public API response schema representing an applicant submitted document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    document_request_id: UUID
    original_filename: str
    stored_filename: str
    file_type: str
    mime_type: str
    file_size: int
    uploaded_by: UUID
    status: Optional[str] = "SUBMITTED"
    created_at: datetime


class DocumentRequestResponse(DocumentRequestBase):
    """Public API response schema representing a DocumentRequest record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    review_id: Optional[UUID] = None
    requested_by: UUID
    status: DocumentRequestStatus
    reviewer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_document: Optional[SubmittedDocumentResponse] = None


class DocumentSubmissionResponse(BaseModel):
    """Structured response returned upon successful document upload submission."""

    status: str = "submitted"
    request_id: UUID
    document_id: UUID
    document_type: DocumentType
    filename: str
    file_size: int
    submitted_at: datetime


class DocumentReviewDecision(str, enum.Enum):
    """Reviewer decision on a submitted verification document."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class DocumentReviewRequest(BaseModel):
    """Schema for reviewer document verification decision."""

    decision: DocumentReviewDecision = Field(..., description="Reviewer decision: ACCEPT or REJECT")
    notes: Optional[str] = Field(None, description="Reviewer notes or reason for rejection")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None


class DocumentReplacementRequest(BaseModel):
    """Schema for requesting a replacement document for a rejected request."""

    notes: Optional[str] = Field(None, description="Optional updated instructions or replacement reason")


# Conceptual alias as mentioned in prompt
CreateDocumentRequest = DocumentRequestCreate

