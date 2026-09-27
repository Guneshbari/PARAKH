"""Document request API routes for structured verification evidence requests."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from app.api.deps import (
    check_application_ownership,
    get_current_active_user,
    get_document_request_service,
    require_role,
)
from app.models.user import User, UserRole
from app.schemas.document_request import (
    DocumentReplacementRequest,
    DocumentRequestCreate,
    DocumentRequestResponse,
    DocumentReviewRequest,
    DocumentSubmissionResponse,
    SubmittedDocumentResponse,
)
from app.services.document_request import DocumentRequestService

router = APIRouter(tags=["document-requests"])


@router.post(
    "/applications/{application_id}/document-requests",
    response_model=DocumentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Document Request",
    description="Create a structured document verification request (e.g. Bank Statement, Income Proof) for an application. Requires REVIEWER or ADMIN role.",
)
def create_document_request(
    application_id: UUID,
    request_in: DocumentRequestCreate,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> DocumentRequestResponse:
    """Create a structured document verification request."""
    data = request_in.model_dump()
    data["application_id"] = application_id
    doc_req = doc_service.create_document_request(data, current_user=current_user)
    return DocumentRequestResponse.model_validate(doc_req)


@router.get(
    "/applications/{application_id}/document-requests",
    response_model=List[DocumentRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List Application Document Requests",
    description="Fetch all document verification requests associated with an application. Reviewers/Admins can access any application; applicants can only access their own.",
)
def get_application_document_requests(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> List[DocumentRequestResponse]:
    """List document verification requests for an application with ownership enforcement."""
    check_application_ownership(
        doc_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    requests = doc_service.get_application_document_requests(application_id)
    return [DocumentRequestResponse.model_validate(r) for r in requests]


@router.get(
    "/applications/{application_id}/document-requests/{request_id}",
    response_model=DocumentRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Request",
    description="Fetch a specific document request by ID with ownership enforcement.",
)
def get_document_request(
    application_id: UUID,
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> DocumentRequestResponse:
    """Fetch a single document request by ID."""
    check_application_ownership(
        doc_service.db,
        application_id,
        current_user,
        allow_reviewers=True,
    )
    doc_req = doc_service.get_document_request(request_id)
    if str(doc_req.application_id) != str(application_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document request not found for this application.",
        )
    return DocumentRequestResponse.model_validate(doc_req)


@router.post(
    "/applications/{application_id}/document-requests/{request_id}/submission",
    response_model=DocumentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Document Verification Evidence",
    description="Upload and submit requested document (PDF, XLS, XLSX) for a pending document request. Requires applicant ownership.",
)
async def submit_document(
    application_id: UUID,
    request_id: UUID,
    file: UploadFile = File(..., description="Uploaded verification document (PDF, XLS, or XLSX, max 10MB)"),
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> DocumentSubmissionResponse:
    """Submit document for a pending document request."""
    content = await file.read()
    submitted_doc, doc_req = doc_service.submit_document(
        application_id=application_id,
        request_id=request_id,
        file_bytes=content,
        original_filename=file.filename or "document",
        content_type=file.content_type,
        current_user=current_user,
    )
    return DocumentSubmissionResponse(
        status="submitted",
        request_id=doc_req.id,
        document_id=submitted_doc.id,
        document_type=doc_req.document_type,
        filename=submitted_doc.original_filename,
        file_size=submitted_doc.file_size,
        submitted_at=submitted_doc.created_at,
    )


@router.get(
    "/applications/{application_id}/document-requests/{request_id}/submission",
    response_model=SubmittedDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Submitted Document Metadata",
    description="Retrieve metadata for a submitted document. Accessible by reviewers, admins, or the owning applicant.",
)
def get_submitted_document(
    application_id: UUID,
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> SubmittedDocumentResponse:
    """Retrieve metadata for a submitted document."""
    submitted_doc = doc_service.get_submitted_document(
        application_id=application_id,
        request_id=request_id,
        current_user=current_user,
    )
    doc_req = doc_service.get_document_request(request_id)
    resp = SubmittedDocumentResponse.model_validate(submitted_doc)
    resp.status = doc_req.status.value
    return resp


@router.get(
    "/applications/{application_id}/document-requests/{request_id}/submission/file",
    status_code=status.HTTP_200_OK,
    summary="View or Download Submitted Document File",
    description="Securely stream or download a submitted document file. Requires reviewer/admin or applicant application ownership.",
)
def get_submitted_document_file(
    application_id: UUID,
    request_id: UUID,
    download: bool = False,
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
):
    """Securely stream or download a submitted document file."""
    submitted_doc, file_path = doc_service.get_submitted_document_file(
        application_id=application_id,
        request_id=request_id,
        current_user=current_user,
    )
    media_type = submitted_doc.mime_type or "application/octet-stream"
    disposition = "attachment" if (download or submitted_doc.file_type in ("XLS", "XLSX")) else "inline"
    filename = submitted_doc.original_filename
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"'
    }
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename if disposition == "attachment" else None,
        headers=headers,
    )


@router.post(
    "/applications/{application_id}/document-requests/{request_id}/review",
    response_model=DocumentRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Review Submitted Document",
    description="Review an applicant's submitted document with ACCEPT or REJECT decision. Requires REVIEWER or ADMIN role.",
)
def review_document(
    application_id: UUID,
    request_id: UUID,
    review_in: DocumentReviewRequest,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> DocumentRequestResponse:
    """Submit a review decision on a submitted verification document."""
    doc_req = doc_service.review_document(
        application_id=application_id,
        request_id=request_id,
        decision=review_in.decision.value,
        notes=review_in.notes,
        current_user=current_user,
    )
    return DocumentRequestResponse.model_validate(doc_req)


@router.post(
    "/applications/{application_id}/document-requests/{request_id}/replacement",
    response_model=DocumentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request Replacement Document",
    description="Create a replacement document request for a rejected document request. Requires REVIEWER or ADMIN role.",
)
def create_replacement_document_request(
    application_id: UUID,
    request_id: UUID,
    replacement_in: Optional[DocumentReplacementRequest] = None,
    current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN)),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> DocumentRequestResponse:
    """Create a new replacement DocumentRequest for a REJECTED document request."""
    notes = replacement_in.notes if replacement_in else None
    new_doc_req = doc_service.create_replacement_request(
        application_id=application_id,
        request_id=request_id,
        current_user=current_user,
        notes=notes,
    )
    return DocumentRequestResponse.model_validate(new_doc_req)


@router.get(
    "/applications/{application_id}/document-requests/pending-check",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Check Unresolved Document Requests",
    description="Check whether an application has unresolved document verification requests.",
)
def check_pending_document_requests(
    application_id: UUID,
    current_user: User = Depends(get_current_active_user),
    doc_service: DocumentRequestService = Depends(get_document_request_service),
) -> dict:
    """Check if application has unresolved document requests."""
    check_application_ownership(
        doc_service.db,
        application_id,
        current_user,
        app_repo=doc_service.app_repo,
    )
    has_pending = doc_service.has_pending_document_requests(application_id)
    return {"has_pending": has_pending}


