import io
import os
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.audit_events import AuditAction, AuditOutcome
from app.core.config import settings
from app.models.document_request import (
    AllowedFileType,
    DocumentRequest,
    DocumentRequestStatus,
    DocumentType,
)
from app.models.submitted_document import SubmittedDocument
from app.models.user import User, UserRole
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.repositories.document_request import DocumentRequestRepository
from app.repositories.review import ReviewRepository
from app.repositories.submitted_document import SubmittedDocumentRepository
from app.repositories.user import UserRepository
from app.schemas.document_request import DocumentRequestCreate
from app.services.audit import AuditService
from app.services.exceptions import (
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    ValidationError,
)
from app.services.storage import DocumentStorageService


def _extract_dict(obj: Union[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert Pydantic schema or dict into a clean dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_unset=True)
    if isinstance(obj, dict):
        return dict(obj)
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


class DocumentRequestService:
    """Business service orchestrating structured document verification requests."""

    def __init__(
        self,
        db: Session,
        doc_repo: Optional[DocumentRequestRepository] = None,
        app_repo: Optional[ApplicationRepository] = None,
        review_repo: Optional[ReviewRepository] = None,
        user_repo: Optional[UserRepository] = None,
        submitted_doc_repo: Optional[SubmittedDocumentRepository] = None,
        applicant_repo: Optional[ApplicantRepository] = None,
        audit_service: Optional[AuditService] = None,
        storage_service: Optional[DocumentStorageService] = None,
    ) -> None:
        """Initialize DocumentRequestService with required repositories and audit service."""
        self.db = db
        self.doc_repo = doc_repo or DocumentRequestRepository(db=db)
        self.app_repo = app_repo or ApplicationRepository(db=db)
        self.review_repo = review_repo or ReviewRepository(db=db)
        self.user_repo = user_repo or UserRepository(db=db)
        self.submitted_doc_repo = submitted_doc_repo or SubmittedDocumentRepository(db=db)
        self.applicant_repo = applicant_repo or ApplicantRepository(db=db)
        self.audit_service = audit_service or AuditService(db=db)
        self.storage_service = storage_service or DocumentStorageService()

    def create_document_request(
        self,
        request_in: Union[DocumentRequestCreate, Dict[str, Any]],
        current_user: User,
        auto_commit: bool = True,
    ) -> DocumentRequest:
        """Create a structured document request for an application.

        Args:
            request_in: Document request details.
            current_user: The authenticated reviewer or admin submitting the request.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            DocumentRequest: Created document request entity.

        Raises:
            AuthorizationError: If current_user is not a REVIEWER or ADMIN.
            ValidationError: If input validation fails.
            EntityNotFoundError: If application or referenced review does not exist.
        """
        if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise AuthorizationError("Only reviewers and administrators can create document requests.")

        data = _extract_dict(request_in)

        application_id = data.get("application_id")
        if not application_id:
            raise ValidationError("application_id is required.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Document type validation
        doc_type = data.get("document_type")
        if not doc_type:
            raise ValidationError("document_type is required.")
        valid_doc_types = {t.value for t in DocumentType}
        doc_type_val = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
        if doc_type_val not in valid_doc_types:
            raise ValidationError(
                f"Invalid document_type '{doc_type_val}'. Supported types: {sorted(list(valid_doc_types))}"
            )

        # Allowed file types validation
        file_types = data.get("allowed_file_types")
        if not file_types or not isinstance(file_types, (list, set, tuple)):
            raise ValidationError("allowed_file_types must be a non-empty list.")
        valid_file_types = {f.value for f in AllowedFileType}
        normalized_file_types = []
        for ft in file_types:
            val = ft.value if hasattr(ft, "value") else str(ft)
            if val not in valid_file_types:
                raise ValidationError(
                    f"Unsupported file type '{val}'. Supported formats are: {sorted(list(valid_file_types))}"
                )
            if val not in normalized_file_types:
                normalized_file_types.append(val)

        if not normalized_file_types:
            raise ValidationError("At least one valid file type must be specified in allowed_file_types.")

        # Description validation
        description = data.get("description")
        if not description or not isinstance(description, str) or len(description.strip()) < 5:
            raise ValidationError("description must contain at least 5 meaningful characters.")
        cleaned_description = description.strip()

        # Review validation if review_id is supplied
        review_id = data.get("review_id")
        if review_id:
            review = self.review_repo.get_by_id(review_id, db=self.db)
            if not review:
                raise EntityNotFoundError(f"Review outcome with id '{review_id}' not found.")
            # Verify review belongs to the same application
            if str(review.application_id) != str(app.id):
                raise ValidationError(
                    f"Review outcome '{review_id}' does not belong to application '{application_id}'."
                )

        requested_by = current_user.id
        status = DocumentRequestStatus.PENDING

        record_data = {
            "application_id": app.id,
            "review_id": uuid.UUID(str(review_id)) if review_id else None,
            "requested_by": requested_by,
            "document_type": DocumentType(doc_type_val),
            "description": cleaned_description,
            "allowed_file_types": normalized_file_types,
            "status": status,
        }

        try:
            doc_req = self.doc_repo.create(record_data, commit=False, db=self.db)

            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.DOCUMENT_REQUESTED,
                        entity_type="DocumentRequest",
                        entity_id=getattr(doc_req, "id", None),
                        application_id=app.id,
                        user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "document_type": doc_type_val,
                            "allowed_file_types": normalized_file_types,
                            "review_id": str(review_id) if review_id else None,
                        },
                        commit=False,
                    )
                except Exception:
                    pass

            if auto_commit:
                self.db.commit()
                self.db.refresh(doc_req)
            return doc_req
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

    def get_application_document_requests(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> List[DocumentRequest]:
        """Retrieve all document requests associated with an application.

        Args:
            application_id: Application primary key UUID.

        Returns:
            List[DocumentRequest]: Document requests ordered by creation date descending.

        Raises:
            EntityNotFoundError: If application does not exist.
        """
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")
        return self.doc_repo.get_by_application(application_id, db=self.db)

    def get_document_request(
        self,
        request_id: Union[uuid.UUID, str],
    ) -> DocumentRequest:
        """Fetch a specific document request by ID.

        Args:
            request_id: DocumentRequest primary key UUID.

        Returns:
            DocumentRequest: Found document request entity.

        Raises:
            EntityNotFoundError: If the document request does not exist.
        """
        req = self.doc_repo.get_by_id(request_id, db=self.db)
        if not req:
            raise EntityNotFoundError(f"Document request with id '{request_id}' not found.")
        return req

    def submit_document(
        self,
        application_id: Union[uuid.UUID, str],
        request_id: Union[uuid.UUID, str],
        file_bytes: bytes,
        original_filename: str,
        content_type: Optional[str],
        current_user: User,
    ) -> Tuple[SubmittedDocument, DocumentRequest]:
        """Validate, store, and record applicant document submission for a pending document request.

        Args:
            application_id: Application UUID.
            request_id: DocumentRequest UUID.
            file_bytes: Raw binary file contents.
            original_filename: Original client filename.
            content_type: Client reported MIME type.
            current_user: Authenticated applicant user.

        Returns:
            Tuple[SubmittedDocument, DocumentRequest]: Persisted document record and updated request.

        Raises:
            EntityNotFoundError: If application or document request does not exist.
            AuthorizationError: If user does not own the application.
            ValidationError: If request does not belong to application or file is empty.
            InvalidStateTransitionError: If request is not in PENDING status.
            HTTPException: For file size (413) or format/type (415) validation failures.
        """
        # 1. Verify application existence
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # 2. Verify applicant ownership
        applicant_user_id = None
        if hasattr(app, "applicant_profile") and app.applicant_profile:
            applicant_user_id = app.applicant_profile.user_id
        elif getattr(app, "applicant_profile_id", None):
            profile = self.applicant_repo.get_by_id(app.applicant_profile_id, db=self.db)
            if profile:
                applicant_user_id = profile.user_id

        if not applicant_user_id or str(applicant_user_id) != str(current_user.id):
            raise AuthorizationError("You are not authorized to submit documents for this application.")

        # 3. Verify document request existence (with row-lock to prevent concurrent double-submission race conditions)
        doc_req = (
            self.db.query(DocumentRequest)
            .filter(DocumentRequest.id == request_id)
            .with_for_update()
            .first()
        )
        if not doc_req:
            raise EntityNotFoundError(f"Document request with id '{request_id}' not found.")

        # 4. Verify request belongs to the application
        if str(doc_req.application_id) != str(app.id):
            raise ValidationError(
                f"Document request '{request_id}' does not belong to application '{application_id}'."
            )

        # 5. Verify request is currently PENDING or REJECTED (for replacement submission)
        if doc_req.status not in (DocumentRequestStatus.PENDING, DocumentRequestStatus.REJECTED):
            raise InvalidStateTransitionError(
                f"Document request is in '{doc_req.status.value}' status and no longer accepts submissions."
            )

        # 6. Validate file content and size
        if not file_bytes or len(file_bytes) == 0:
            raise ValidationError("Uploaded file is empty.")

        if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of 10 MB ({len(file_bytes)} bytes uploaded).",
            )

        # Sanitize filename to prevent directory traversal
        safe_original_filename = (
            os.path.basename(original_filename.replace("\\", "/"))
            if original_filename
            else "document"
        )
        if not safe_original_filename:
            safe_original_filename = "document"

        # Validate extension
        parts = safe_original_filename.rsplit(".", 1)
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File has no extension. Allowed extensions are: .pdf, .xls, .xlsx",
            )
        ext = parts[1].lower()
        if ext not in ("pdf", "xls", "xlsx"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file extension '.{ext}'. Allowed formats: PDF, XLS, XLSX.",
            )

        # Inspect binary magic bytes
        detected_type: Optional[str] = None
        detected_mime: Optional[str] = None

        if file_bytes.startswith(b"%PDF") or b"%PDF" in file_bytes[:1024]:
            detected_type = "PDF"
            detected_mime = "application/pdf"
        elif file_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            detected_type = "XLS"
            detected_mime = "application/vnd.ms-excel"
        elif file_bytes.startswith(b"PK\x03\x04"):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    names = zf.namelist()
                    if any(n.startswith("xl/") or n == "[Content_Types].xml" for n in names) and not any(
                        n.startswith("word/") for n in names
                    ):
                        detected_type = "XLSX"
                        detected_mime = (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Uploaded file is a zip archive but not a valid Excel (XLSX) spreadsheet.",
                        )
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Corrupted or invalid XLSX archive.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported or invalid file content. Expected valid PDF, XLS, or XLSX document.",
            )

        # Verify extension matches detected format
        if ext == "pdf" and detected_type != "PDF":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File extension (.pdf) does not match binary content.",
            )
        if ext in ("xls", "xlsx") and detected_type not in ("XLS", "XLSX"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File extension does not match Excel binary content.",
            )

        # Verify detected format is in document request's allowed_file_types
        allowed_types = {t.upper() for t in doc_req.allowed_file_types}
        if detected_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"File format '{detected_type}' is not allowed for this document request. "
                    f"Accepted formats are: {sorted(list(allowed_types))}."
                ),
            )

        # 7. File storage via DocumentStorageService
        doc_id = uuid.uuid4()
        safe_ext = f".{detected_type.lower()}"
        stored_filename = self.storage_service.generate_stored_filename(
            document_id=doc_id,
            original_filename=safe_original_filename,
            detected_extension=safe_ext,
        )
        file_path = self.storage_service.save_file(
            application_id=app.id,
            stored_filename=stored_filename,
            content=file_bytes,
        )

        # 8. Database persistence & Status transition in atomic transaction
        try:
            existing_sub = (
                self.db.query(SubmittedDocument)
                .filter(SubmittedDocument.document_request_id == doc_req.id)
                .first()
            )
            if existing_sub:
                existing_sub.original_filename = safe_original_filename
                existing_sub.stored_filename = stored_filename
                existing_sub.file_path = file_path
                existing_sub.file_type = detected_type
                existing_sub.mime_type = detected_mime
                existing_sub.file_size = len(file_bytes)
                existing_sub.uploaded_by = current_user.id
                submitted_doc = existing_sub
            else:
                submitted_doc = self.submitted_doc_repo.create(
                    {
                        "id": doc_id,
                        "application_id": app.id,
                        "document_request_id": doc_req.id,
                        "uploaded_by": current_user.id,
                        "original_filename": safe_original_filename,
                        "stored_filename": stored_filename,
                        "file_path": file_path,
                        "file_type": detected_type,
                        "mime_type": detected_mime,
                        "file_size": len(file_bytes),
                    },
                    commit=False,
                    db=self.db,
                )

            # Transition status PENDING -> SUBMITTED
            doc_req.status = DocumentRequestStatus.SUBMITTED

            # Audit event
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.DOCUMENT_SUBMITTED,
                        entity_type="SubmittedDocument",
                        entity_id=str(submitted_doc.id),
                        application_id=app.id,
                        user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "document_request_id": str(doc_req.id),
                            "document_type": doc_req.document_type.value,
                            "original_filename": safe_original_filename,
                            "file_type": detected_type,
                            "file_size": len(file_bytes),
                        },
                        commit=False,
                    )
                except Exception:
                    pass

            self.db.commit()
            self.db.refresh(submitted_doc)
            self.db.refresh(doc_req)
            return submitted_doc, doc_req
        except Exception:
            self.db.rollback()
            self.storage_service.delete_file(file_path)
            raise

    def get_submitted_document(
        self,
        application_id: Union[uuid.UUID, str],
        request_id: Union[uuid.UUID, str],
        current_user: User,
    ) -> SubmittedDocument:
        """Retrieve submitted document metadata for an application and request.

        Enforces authentication and authorization: Reviewers and Admins can view any,
        applicants can only view documents belonging to their own applications.
        """
        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        # Role and ownership check
        if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            applicant_user_id = None
            if hasattr(app, "applicant_profile") and app.applicant_profile:
                applicant_user_id = app.applicant_profile.user_id
            elif getattr(app, "applicant_profile_id", None):
                profile = self.applicant_repo.get_by_id(app.applicant_profile_id, db=self.db)
                if profile:
                    applicant_user_id = profile.user_id

            if not applicant_user_id or str(applicant_user_id) != str(current_user.id):
                raise AuthorizationError("You are not authorized to view documents for this application.")

        doc_req = self.doc_repo.get_by_id(request_id, db=self.db)
        if not doc_req or str(doc_req.application_id) != str(app.id):
            raise EntityNotFoundError(f"Document request with id '{request_id}' not found for this application.")

        submitted = (
            self.db.query(SubmittedDocument)
            .filter(SubmittedDocument.document_request_id == doc_req.id)
            .order_by(SubmittedDocument.created_at.desc())
            .first()
        )
        if not submitted:
            raise EntityNotFoundError(f"No document has been submitted for request '{request_id}'.")

        return submitted

    def get_submitted_document_file(
        self,
        application_id: Union[uuid.UUID, str],
        request_id: Union[uuid.UUID, str],
        current_user: User,
    ) -> Tuple[SubmittedDocument, str]:
        """Retrieve physical file path and metadata for a submitted document.

        Verifies permissions, existence, and physical file presence on the persistent storage volume.
        """
        submitted = self.get_submitted_document(application_id, request_id, current_user)
        try:
            file_path = self.storage_service.get_file_path(
                application_id=submitted.application_id,
                stored_filename=submitted.stored_filename,
            )
        except FileNotFoundError:
            raise EntityNotFoundError(f"Stored document file '{submitted.stored_filename}' was not found on disk.")

        return submitted, file_path

    def review_document(
        self,
        application_id: Union[uuid.UUID, str],
        request_id: Union[uuid.UUID, str],
        decision: str,
        notes: Optional[str],
        current_user: User,
    ) -> DocumentRequest:
        """Review an applicant's submitted document (ACCEPT or REJECT).

        Args:
            application_id: Application UUID.
            request_id: Document request UUID.
            decision: "ACCEPT" or "REJECT".
            notes: Reviewer notes (mandatory for REJECT, at least 5 chars).
            current_user: Authenticated reviewer or admin.

        Returns:
            DocumentRequest: Updated document request.

        Raises:
            AuthorizationError: If current_user is not REVIEWER or ADMIN.
            EntityNotFoundError: If application or request not found.
            ValidationError: If decision is invalid or notes are missing for REJECT.
            InvalidStateTransitionError: If document request is not in SUBMITTED state.
        """
        if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise AuthorizationError("Only reviewers and administrators can review documents.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        doc_req = self.doc_repo.get_by_id(request_id, db=self.db)
        if not doc_req or str(doc_req.application_id) != str(app.id):
            raise EntityNotFoundError(f"Document request with id '{request_id}' not found for this application.")

        # Verify state transition: Only SUBMITTED -> ACCEPTED or SUBMITTED -> REJECTED
        if doc_req.status == DocumentRequestStatus.PENDING:
            raise InvalidStateTransitionError("Cannot review a document request that is still PENDING.")
        elif doc_req.status == DocumentRequestStatus.ACCEPTED:
            raise InvalidStateTransitionError("Document request has already been ACCEPTED.")
        elif doc_req.status == DocumentRequestStatus.REJECTED:
            raise InvalidStateTransitionError("Document request is already REJECTED. Awaiting applicant replacement submission.")
        elif doc_req.status != DocumentRequestStatus.SUBMITTED:
            raise InvalidStateTransitionError(f"Cannot review document request in '{doc_req.status.value}' status.")

        # Verify a submitted document exists
        submitted = (
            self.db.query(SubmittedDocument)
            .filter(SubmittedDocument.document_request_id == doc_req.id)
            .order_by(SubmittedDocument.created_at.desc())
            .first()
        )
        if not submitted:
            raise ValidationError("No submitted document found to review.")

        clean_decision = decision.upper().strip() if decision else ""
        if clean_decision not in ("ACCEPT", "REJECT"):
            raise ValidationError(f"Invalid decision '{decision}'. Must be 'ACCEPT' or 'REJECT'.")

        cleaned_notes = notes.strip() if notes else None
        if clean_decision == "REJECT":
            if not cleaned_notes or len(cleaned_notes) < 5:
                raise ValidationError("Reviewer notes of at least 5 characters are required when requesting replacement / rejecting a document.")

        try:
            if clean_decision == "ACCEPT":
                doc_req.status = DocumentRequestStatus.ACCEPTED
                doc_req.reviewer_notes = cleaned_notes
                action = AuditAction.DOCUMENT_ACCEPTED
            else:
                doc_req.status = DocumentRequestStatus.REJECTED
                doc_req.reviewer_notes = cleaned_notes
                action = AuditAction.DOCUMENT_REJECTED

            # Audit event
            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=action,
                        entity_type="DocumentRequest",
                        entity_id=str(doc_req.id),
                        application_id=app.id,
                        user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "document_request_id": str(doc_req.id),
                            "submitted_document_id": str(submitted.id),
                            "document_type": doc_req.document_type.value,
                            "decision": clean_decision,
                            "reviewer_notes": cleaned_notes,
                            "original_filename": submitted.original_filename,
                        },
                        commit=False,
                    )
                except Exception:
                    pass

            self.db.commit()
            self.db.refresh(doc_req)
            return doc_req
        except Exception:
            self.db.rollback()
            raise

    def has_pending_document_requests(
        self,
        application_id: Union[uuid.UUID, str],
    ) -> bool:
        """Determine whether an application has unresolved evidence requests.

        Treats PENDING and SUBMITTED as unresolved.
        Treats ACCEPTED as resolved.
        Treats REJECTED as unresolved unless an ACCEPTED request exists for the same document_type.

        Args:
            application_id: Application UUID.

        Returns:
            bool: True if application has unresolved requests, False otherwise.
        """
        return self.doc_repo.has_pending_document_requests(application_id, db=self.db)

    def create_replacement_request(
        self,
        application_id: Union[uuid.UUID, str],
        request_id: Union[uuid.UUID, str],
        current_user: User,
        notes: Optional[str] = None,
        auto_commit: bool = True,
    ) -> DocumentRequest:
        """Create a new replacement DocumentRequest for a REJECTED document request.

        Preserves the original REJECTED request and its submitted document intact for auditability.
        Enforces that only one active replacement request can exist per rejected request.

        Args:
            application_id: Application UUID.
            request_id: The ID of the REJECTED DocumentRequest to replace.
            current_user: Reviewer or Admin requesting replacement.
            notes: Optional updated instructions / reason for replacement.
            auto_commit: Whether to commit at the service boundary.

        Returns:
            DocumentRequest: The newly created replacement DocumentRequest in PENDING status.

        Raises:
            AuthorizationError: If current_user is not REVIEWER or ADMIN.
            EntityNotFoundError: If application or request not found.
            InvalidStateTransitionError: If target request is not REJECTED.
            DuplicateEntityError: If an active replacement request already exists.
        """
        if current_user.role not in (UserRole.REVIEWER, UserRole.ADMIN):
            raise AuthorizationError("Only reviewers and administrators can request document replacements.")

        app = self.app_repo.get_by_id(application_id, db=self.db)
        if not app:
            raise EntityNotFoundError(f"Application with id '{application_id}' not found.")

        old_req = self.doc_repo.get_by_id(request_id, db=self.db)
        if not old_req or str(old_req.application_id) != str(app.id):
            raise EntityNotFoundError(f"Document request with id '{request_id}' not found for this application.")

        if old_req.status != DocumentRequestStatus.REJECTED:
            raise InvalidStateTransitionError(
                f"Cannot request replacement for document request in '{old_req.status.value}' status. Must be 'REJECTED'."
            )

        # Enforce Section 12: Do not automatically create duplicate requests
        existing_requests = self.doc_repo.get_by_application(app.id, db=self.db)
        for r in existing_requests:
            if r.id != old_req.id and r.document_type == old_req.document_type:
                if r.status in (DocumentRequestStatus.PENDING, DocumentRequestStatus.SUBMITTED):
                    raise DuplicateEntityError(
                        f"An active replacement request for '{old_req.document_type.value}' is already pending review."
                    )

        replacement_description = (
            notes.strip()
            if notes and len(notes.strip()) >= 5
            else (old_req.reviewer_notes or old_req.description)
        )

        new_req_data = {
            "application_id": app.id,
            "review_id": old_req.review_id,
            "requested_by": current_user.id,
            "document_type": old_req.document_type,
            "description": replacement_description,
            "allowed_file_types": old_req.allowed_file_types,
            "status": DocumentRequestStatus.PENDING,
            "reviewer_notes": f"Replacement for prior rejection: {old_req.reviewer_notes}" if old_req.reviewer_notes else None,
        }

        try:
            new_doc_req = self.doc_repo.create(new_req_data, commit=False, db=self.db)

            if self.audit_service:
                try:
                    self.audit_service.record_event(
                        action=AuditAction.DOCUMENT_REQUESTED,
                        entity_type="DocumentRequest",
                        entity_id=getattr(new_doc_req, "id", None),
                        application_id=app.id,
                        user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome=AuditOutcome.SUCCESS,
                        metadata={
                            "document_type": old_req.document_type.value,
                            "allowed_file_types": [f.value if hasattr(f, "value") else str(f) for f in old_req.allowed_file_types],
                            "replacement_for_request_id": str(old_req.id),
                            "reason": replacement_description,
                        },
                        commit=False,
                    )
                except Exception:
                    pass

            if auto_commit:
                self.db.commit()
                self.db.refresh(new_doc_req)

            return new_doc_req
        except Exception:
            if auto_commit:
                self.db.rollback()
            raise

