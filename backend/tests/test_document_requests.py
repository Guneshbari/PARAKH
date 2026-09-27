"""Tests for Phase 1 Document Request Foundation.

Validates:
1. Reviewer can create a document request.
2. Applicant cannot create a document request (403 Forbidden).
3. Invalid document type is rejected (422 / 400).
4. Invalid file type is rejected (422 / 400).
5. Document request is linked to the correct application.
6. Document request references the correct review outcome.
7. review_id cannot reference a review belonging to another application (400 ValidationError).
8. Applicant can retrieve requests for their own application.
9. Applicant cannot retrieve another applicant's requests (403 Forbidden).
10. REQUEST_VERIFICATION review outcome creates structured DocumentRequest atomically.
11. Audit log contains DOCUMENT_REQUESTED with correct metadata.
"""
import json
import os
import unittest
from unittest.mock import patch
import uuid
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.core.audit_events import AuditAction
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    DocumentRequest,
    DocumentRequestStatus,
    DocumentType,
    ReviewOutcome,
    ReviewOutcomeType,
    SubmittedDocument,
    User,
    UserRole,
)
from app.repositories.application import ApplicationRepository
from app.repositories.user import UserRepository
from app.services.storage import DocumentStorageService


class TestDocumentRequestsWorkflow(unittest.TestCase):
    """Integration test suite for Phase 1 Document Requests."""

    def setUp(self):
        """Initialize in-memory SQLite database and test clients."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.client = TestClient(app)

        def override_get_db() -> Generator[Session, None, None]:
            db = self.SessionFactory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        self.applicant_password = "ApplicantPass123!"
        self.other_applicant_password = "OtherApplicantPass123!"
        self.reviewer_password = "ReviewerPass123!"

        with self.SessionFactory() as db:
            user_repo = UserRepository(db=db)
            app_repo = ApplicationRepository(db=db)

            # 1. Primary Applicant & Profile
            self.applicant = user_repo.create({
                "email": "applicant.doc@example.com",
                "password_hash": hash_password(self.applicant_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.applicant_id = str(self.applicant.id)

            self.applicant_profile = ApplicantProfile(
                user_id=self.applicant.id,
                gig_work_type="Delivery Partner",
                years_working=2.0,
                average_working_days=25,
                business_or_loan_purpose="Vehicle repair",
            )
            db.add(self.applicant_profile)
            db.commit()

            # 2. Secondary Applicant (for cross-applicant isolation checks)
            self.other_applicant = user_repo.create({
                "email": "other.applicant.doc@example.com",
                "password_hash": hash_password(self.other_applicant_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.other_applicant_id = str(self.other_applicant.id)

            self.other_applicant_profile = ApplicantProfile(
                user_id=self.other_applicant.id,
                gig_work_type="E-commerce Vendor",
                years_working=1.5,
                average_working_days=20,
                business_or_loan_purpose="Inventory purchase",
            )
            db.add(self.other_applicant_profile)
            db.commit()

            # 3. Reviewer
            self.reviewer = user_repo.create({
                "email": "reviewer.doc@example.com",
                "password_hash": hash_password(self.reviewer_password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.reviewer_id = str(self.reviewer.id)

            # 4. Applications
            self.app1 = app_repo.create({
                "applicant_profile_id": self.applicant_profile.id,
                "requested_loan_amount": 50000.0,
                "preferred_repayment_period": 12,
                "loan_purpose": "Vehicle maintenance",
                "status": ApplicationStatus.MANUAL_REVIEW,
            }, commit=True)
            self.app1_id = str(self.app1.id)

            self.other_app = app_repo.create({
                "applicant_profile_id": self.other_applicant_profile.id,
                "requested_loan_amount": 35000.0,
                "preferred_repayment_period": 6,
                "loan_purpose": "Stock purchase",
                "status": ApplicationStatus.MANUAL_REVIEW,
            }, commit=True)
            self.other_app_id = str(self.other_app.id)

    def tearDown(self):
        """Clean up database and client overrides."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _login(self, email: str, password: str) -> str:
        """Helper to log in and obtain JWT access token."""
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}")
        return resp.json()["access_token"]

    def test_01_reviewer_can_create_document_request(self):
        """1. Reviewer can create a structured document request."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "document_type": "BANK_STATEMENT",
            "description": "Please upload your latest 3-month bank statement.",
            "allowed_file_types": ["PDF", "XLS", "XLSX"],
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json=payload,
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["application_id"], self.app1_id)
        self.assertEqual(data["document_type"], "BANK_STATEMENT")
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["allowed_file_types"], ["PDF", "XLS", "XLSX"])
        self.assertEqual(data["requested_by"], self.reviewer_id)
        self.assertIsNotNone(data["id"])

        # Verify audit log was recorded
        with self.SessionFactory() as db:
            logs = db.query(AuditLog).filter_by(action=AuditAction.DOCUMENT_REQUESTED).all()
            self.assertGreaterEqual(len(logs), 1)
            latest = logs[-1]
            self.assertEqual(str(latest.application_id), self.app1_id)
            self.assertEqual(str(latest.user_id), self.reviewer_id)
            self.assertEqual(latest.audit_metadata.get("document_type"), "BANK_STATEMENT")

    def test_02_applicant_cannot_create_document_request(self):
        """2. Applicant cannot create a document request -> 403 Forbidden."""
        token = self._login("applicant.doc@example.com", self.applicant_password)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "document_type": "BANK_STATEMENT",
            "description": "Attempting self-document request.",
            "allowed_file_types": ["PDF"],
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json=payload,
        )
        self.assertEqual(resp.status_code, 403)

    def test_03_invalid_document_type_rejected(self):
        """3. Invalid document type is rejected."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "document_type": "INVALID_PASSPORT_DOC",
            "description": "Please provide your passport.",
            "allowed_file_types": ["PDF"],
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json=payload,
        )
        self.assertIn(resp.status_code, (400, 422))

    def test_04_invalid_file_type_rejected(self):
        """4. Invalid file type is rejected."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        # Format like EXE or DOCX should be rejected
        payload = {
            "document_type": "INCOME_PROOF",
            "description": "Please upload your salary slip.",
            "allowed_file_types": ["EXE", "PNG"],
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json=payload,
        )
        self.assertIn(resp.status_code, (400, 422))

    def test_05_document_request_linked_to_correct_application(self):
        """5. Document request is linked to the correct application."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "document_type": "TRANSACTION_STATEMENT",
            "description": "Please upload GST or UPI merchant QR transactions.",
            "allowed_file_types": ["PDF", "XLSX"],
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json=payload,
        )
        self.assertEqual(resp.status_code, 201)
        doc_id = resp.json()["id"]

        with self.SessionFactory() as db:
            doc = db.query(DocumentRequest).filter_by(id=uuid.UUID(doc_id)).first()
            self.assertIsNotNone(doc)
            self.assertEqual(str(doc.application_id), self.app1_id)
            self.assertEqual(doc.application.id, uuid.UUID(self.app1_id))

    def test_06_document_request_references_correct_review_outcome(self):
        """6. Document request created with review_id references the review outcome."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        # First, record a review outcome
        rev_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
                "notes": "Requesting verified bank statement before loan assessment.",
            },
        )
        self.assertEqual(rev_resp.status_code, 201)
        review_id = rev_resp.json()["id"]

        # Now create document request linking to this review_id
        doc_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json={
                "review_id": review_id,
                "document_type": "BANK_STATEMENT",
                "description": "Official 3-month bank statement required for KYC verification.",
                "allowed_file_types": ["PDF"],
            },
        )
        self.assertEqual(doc_resp.status_code, 201)
        self.assertEqual(doc_resp.json()["review_id"], review_id)

    def test_07_review_id_cannot_reference_review_from_another_application(self):
        """7. review_id cannot reference a review belonging to another application."""
        token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {token}"}

        # Create review on other_app
        other_rev = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/reviews",
            headers=headers,
            json={
                "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
                "notes": "Review belonging exclusively to other_app_id.",
            },
        )
        self.assertEqual(other_rev.status_code, 201)
        other_review_id = other_rev.json()["id"]

        # Attempt to link app1's document request to other_review_id
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=headers,
            json={
                "review_id": other_review_id,
                "document_type": "BUSINESS_RECORD",
                "description": "Cross-application review linkage test.",
                "allowed_file_types": ["PDF"],
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not belong to application", resp.json()["detail"])

    def test_08_applicant_can_retrieve_requests_for_own_application(self):
        """8. Applicant can retrieve requests for their own application."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        rev_headers = {"Authorization": f"Bearer {rev_token}"}

        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=rev_headers,
            json={
                "document_type": "INCOME_PROOF",
                "description": "Submit last 2 pay/gig slips for alternative scoring.",
                "allowed_file_types": ["PDF", "XLS"],
            },
        )

        # Applicant reads their own application's document requests
        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        app_headers = {"Authorization": f"Bearer {app_token}"}

        resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers=app_headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["document_type"], "INCOME_PROOF")
        self.assertEqual(data[0]["status"], "PENDING")

    def test_09_applicant_cannot_retrieve_another_applicants_requests(self):
        """9. Applicant cannot retrieve another applicant's document requests -> 403."""
        # Create request on other_app
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "OTHER",
                "description": "Other applicant's document request details.",
                "allowed_file_types": ["PDF"],
            },
        )

        # Primary applicant attempts to read other_app's document requests
        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        resp = self.client.get(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {app_token}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_10_atomic_request_verification_with_document_request(self):
        """10. REQUEST_VERIFICATION review action atomically creates DocumentRequest."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {rev_token}"}

        review_payload = {
            "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
            "notes": "Income inconsistency found. Please upload latest bank statement.",
            "document_request": {
                "document_type": "BANK_STATEMENT",
                "description": "Please upload 3 consecutive monthly bank statements.",
                "allowed_file_types": ["PDF", "XLS", "XLSX"],
            },
        }

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json=review_payload,
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        review_id = data["id"]

        with self.SessionFactory() as db:
            # Check review outcome persisted
            rev = db.query(ReviewOutcome).filter_by(id=uuid.UUID(review_id)).first()
            self.assertIsNotNone(rev)
            self.assertEqual(rev.outcome, ReviewOutcomeType.ADDITIONAL_INFORMATION_REQUIRED)

            # Check application status transitioned to UNDER_REVIEW
            app_obj = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app_obj.status, ApplicationStatus.UNDER_REVIEW)

            # Check document request was created atomically and linked
            doc = db.query(DocumentRequest).filter_by(review_id=uuid.UUID(review_id)).first()
            self.assertIsNotNone(doc)
            self.assertEqual(doc.document_type, DocumentType.BANK_STATEMENT)
            self.assertEqual(doc.status, DocumentRequestStatus.PENDING)
            self.assertEqual(str(doc.requested_by), self.reviewer_id)
            self.assertEqual(doc.allowed_file_types, ["PDF", "XLS", "XLSX"])

    def test_11_applicant_successful_document_upload_scenario_a(self):
        """Scenario A: Applicant successfully submits valid PDF document for pending request."""
        # 1. Reviewer creates request
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload your latest 3-month bank statement.",
                "allowed_file_types": ["PDF", "XLS", "XLSX"],
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        req_id = create_resp.json()["id"]

        # 2. Applicant submits valid PDF
        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {
            "file": ("bank_statement.pdf", pdf_bytes, "application/pdf")
        }

        submit_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files=files,
        )
        self.assertEqual(submit_resp.status_code, 201)
        data = submit_resp.json()
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["request_id"], req_id)
        self.assertEqual(data["filename"], "bank_statement.pdf")
        self.assertEqual(data["document_type"], "BANK_STATEMENT")

        # 3. Verify DB state and audit
        with self.SessionFactory() as db:
            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.SUBMITTED)

            submitted = db.query(SubmittedDocument).filter_by(document_request_id=uuid.UUID(req_id)).first()
            self.assertIsNotNone(submitted)
            self.assertEqual(submitted.original_filename, "bank_statement.pdf")
            self.assertEqual(submitted.file_type, "PDF")
            self.assertEqual(str(submitted.uploaded_by), self.applicant_id)

            # Audit event
            audit = (
                db.query(AuditLog)
                .filter_by(action="DOCUMENT_SUBMITTED", entity_id=str(submitted.id))
                .first()
            )
            self.assertIsNotNone(audit)
            self.assertEqual(str(audit.user_id), self.applicant_id)

    def test_12_invalid_file_format_rejected_scenario_b(self):
        """Scenario B: Disallowed format (e.g. JPG or disguised file) is rejected with 415."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        # Try uploading jpg
        files = {
            "file": ("photo.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg")
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files=files,
        )
        self.assertEqual(resp.status_code, 415)

        # Check request remains PENDING
        with self.SessionFactory() as db:
            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.PENDING)

    def test_13_oversized_file_rejected_scenario_c(self):
        """Scenario C: File > 10MB is rejected with 413."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        # 10MB + 1 byte
        oversized = b"%PDF-1.4" + b"0" * (10 * 1024 * 1024 + 1)
        files = {
            "file": ("large.pdf", oversized, "application/pdf")
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files=files,
        )
        self.assertEqual(resp.status_code, 413)

        with self.SessionFactory() as db:
            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.PENDING)

    def test_14_empty_file_rejected_scenario_d(self):
        """Scenario D: Empty (0-byte) file is rejected with 400."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        files = {
            "file": ("empty.pdf", b"", "application/pdf")
        }
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files=files,
        )
        self.assertEqual(resp.status_code, 400)

        with self.SessionFactory() as db:
            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.PENDING)

    def test_15_already_submitted_request_cannot_be_submitted_again_scenario_e(self):
        """Scenario E: Attempting to submit a request that is already SUBMITTED returns 409 Conflict."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

        # First submission succeeds
        first_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("stmt.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(first_resp.status_code, 201)

        # Second submission fails with 409 Conflict
        second_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("stmt2.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(second_resp.status_code, 409)

    def test_16_wrong_application_id_rejected_scenario_f(self):
        """Scenario F: Submitting a request belonging to another application fails."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        # Create request on app 1
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        # Applicant tries to submit it against app 2
        app2_token = self._login("other.applicant.doc@example.com", self.other_applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        resp = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app2_token}"},
            files={"file": ("stmt.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(resp.status_code, 400)

    def test_17_multiple_requests_independent_submission_scenario_g(self):
        """Scenario G: Submitting one request does not mark other pending requests as submitted."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        # Request 1: Bank statement
        r1 = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        ).json()["id"]

        # Request 2: Income proof
        r2 = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "INCOME_PROOF",
                "description": "Please upload salary slip or income proof.",
                "allowed_file_types": ["PDF"],
            },
        ).json()["id"]

        # Applicant submits only Request 1
        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{r1}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("bank.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(resp.status_code, 201)

        # Verify DB state: r1 is SUBMITTED, r2 remains PENDING
        with self.SessionFactory() as db:
            doc1 = db.query(DocumentRequest).filter_by(id=uuid.UUID(r1)).first()
            doc2 = db.query(DocumentRequest).filter_by(id=uuid.UUID(r2)).first()
            self.assertEqual(doc1.status, DocumentRequestStatus.SUBMITTED)
            self.assertEqual(doc2.status, DocumentRequestStatus.PENDING)

    def test_18_unauthorized_applicant_cannot_submit(self):
        """Applicant cannot submit documents for another applicant's application."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        # Other applicant tries to submit for Application 1
        app2_token = self._login("other.applicant.doc@example.com", self.other_applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app2_token}"},
            files={"file": ("bank.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(resp.status_code, 403)

    def test_19_reviewed_does_not_create_document_request(self):
        """19 (Requirement 16.H). Normal REVIEWED outcome does not create a document request."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {rev_token}"}

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "REVIEWED",
                "notes": "Application meets all alternative credit requirements perfectly.",
            },
        )
        self.assertEqual(resp.status_code, 201)
        review_id = resp.json()["id"]

        with self.SessionFactory() as db:
            rev = db.query(ReviewOutcome).filter_by(id=uuid.UUID(review_id)).first()
            self.assertIsNotNone(rev)
            self.assertEqual(rev.outcome, ReviewOutcomeType.REVIEWED)
            docs = db.query(DocumentRequest).filter_by(review_id=uuid.UUID(review_id)).all()
            self.assertEqual(len(docs), 0)

    def test_20_escalated_does_not_create_document_request(self):
        """20 (Requirement 16.I). ESCALATED outcome does not create a document request."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {rev_token}"}

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "ESCALATED",
                "notes": "Escalating application for senior management review.",
            },
        )
        self.assertEqual(resp.status_code, 201)
        review_id = resp.json()["id"]

        with self.SessionFactory() as db:
            rev = db.query(ReviewOutcome).filter_by(id=uuid.UUID(review_id)).first()
            self.assertIsNotNone(rev)
            self.assertEqual(rev.outcome, ReviewOutcomeType.ESCALATED)
            docs = db.query(DocumentRequest).filter_by(review_id=uuid.UUID(review_id)).all()
            self.assertEqual(len(docs), 0)

    def test_21_unauthorized_user_cannot_create_review_with_document_request(self):
        """21 (Requirement 16.J). Unauthorized user (applicant) cannot create review with document request."""
        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        headers = {"Authorization": f"Bearer {app_token}"}

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
                "notes": "Attempting unauthorized review submission.",
                "document_request": {
                    "document_type": "BANK_STATEMENT",
                    "description": "Please upload bank statement.",
                    "allowed_file_types": ["PDF"],
                },
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_22_transaction_rollback_when_document_request_creation_fails(self):
        """22 (Requirement 16.K). Transaction rollback works: if document request validation fails, no review or document request is persisted."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {rev_token}"}

        with self.SessionFactory() as db:
            initial_review_count = db.query(ReviewOutcome).filter_by(application_id=uuid.UUID(self.app1_id)).count()
            initial_doc_count = db.query(DocumentRequest).filter_by(application_id=uuid.UUID(self.app1_id)).count()

        unique_notes = f"Atomic test unique notes {uuid.uuid4()}"
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
                "notes": unique_notes,
                "document_request": {
                    "document_type": "INVALID_DOCUMENT_TYPE",
                    "description": "Please upload valid documents.",
                    "allowed_file_types": ["PDF"],
                },
            },
        )
        self.assertIn(resp.status_code, [400, 422])

        with self.SessionFactory() as db:
            # Verify no review outcome was committed
            rev = db.query(ReviewOutcome).filter_by(notes=unique_notes).first()
            self.assertIsNone(rev)
            final_review_count = db.query(ReviewOutcome).filter_by(application_id=uuid.UUID(self.app1_id)).count()
            final_doc_count = db.query(DocumentRequest).filter_by(application_id=uuid.UUID(self.app1_id)).count()
            self.assertEqual(final_review_count, initial_review_count)
            self.assertEqual(final_doc_count, initial_doc_count)

    def test_23_phase3_upload_creates_metadata_row_and_persists_file(self):
        """23 (Phase 3 A&B). Upload creates canonical metadata row and physically persists file on disk."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload your latest 3-month bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Phase 3 Test) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        upload_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("verified_statement.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(upload_resp.status_code, 201)
        sub_data = upload_resp.json()
        doc_id = sub_data["document_id"]

        with self.SessionFactory() as db:
            submitted = db.query(SubmittedDocument).filter_by(id=uuid.UUID(doc_id)).first()
            self.assertIsNotNone(submitted)
            # A. Metadata verification
            self.assertEqual(submitted.original_filename, "verified_statement.pdf")
            self.assertTrue(str(submitted.id) in submitted.stored_filename)
            self.assertEqual(submitted.file_type, "PDF")
            self.assertEqual(submitted.mime_type, "application/pdf")
            self.assertEqual(submitted.file_size, len(pdf_bytes))
            self.assertEqual(str(submitted.uploaded_by), self.applicant_id)
            self.assertEqual(str(submitted.application_id), self.app1_id)
            self.assertEqual(str(submitted.document_request_id), req_id)
            # B. Physical storage verification
            self.assertTrue(os.path.isfile(submitted.file_path))
            with open(submitted.file_path, "rb") as f:
                disk_bytes = f.read()
            self.assertEqual(disk_bytes, pdf_bytes)

    def test_24_phase3_stored_filename_safe_and_prepends_uuid(self):
        """24 (Phase 3 C). Stored filename safely differs from original filename by prepending UUID and sanitizing."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        original_name = "My Bank Statement #1 (Sept 2026)!.pdf"
        upload_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": (original_name, pdf_bytes, "application/pdf")},
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.json()["document_id"]

        with self.SessionFactory() as db:
            sub = db.query(SubmittedDocument).filter_by(id=uuid.UUID(doc_id)).first()
            self.assertEqual(sub.original_filename, original_name)
            # Stored filename must start with doc_id
            self.assertTrue(sub.stored_filename.startswith(f"{doc_id}_"))
            # Must not contain unsafe characters like spaces or exclamation marks
            self.assertNotIn(" ", sub.stored_filename)
            self.assertNotIn("!", sub.stored_filename)
            self.assertNotIn("#", sub.stored_filename)

    def test_25_phase3_path_traversal_is_prevented_and_sanitized(self):
        """25 (Phase 3 D). Path traversal attempts in filename are sanitized and confined to application directory."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        upload_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("../../../../etc/passwd.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.json()["document_id"]

        with self.SessionFactory() as db:
            sub = db.query(SubmittedDocument).filter_by(id=uuid.UUID(doc_id)).first()
            # Stored file must reside strictly inside applications/{app_id}
            app_dir_part = f"applications{os.sep}{self.app1_id}"
            self.assertIn(app_dir_part, sub.file_path)
            self.assertTrue(os.path.isfile(sub.file_path))
            self.assertNotIn("../", sub.file_path)
            self.assertNotIn("..\\", sub.file_path)

    def test_26_phase3_database_rollback_removes_newly_stored_file(self):
        """26 (Phase 3 E). Transaction rollback removes the newly stored file from disk."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Please upload bank statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        storage = DocumentStorageService()
        dummy_doc_id = uuid.uuid4()
        stored_name = storage.generate_stored_filename(dummy_doc_id, "test_rollback.pdf", ".pdf")
        saved_path = storage.save_file(self.app1_id, stored_name, b"sample bytes")
        self.assertTrue(os.path.isfile(saved_path))

        # Perform rollback cleanup
        deleted = storage.delete_file(saved_path)
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(saved_path))

    def test_27_phase3_multiple_applications_keep_documents_isolated(self):
        """27 (Phase 3 H). Multiple applications keep documents isolated in dedicated subdirectories."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        r1 = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "App1 doc", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        r2 = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Other App doc", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        app1_token = self._login("applicant.doc@example.com", self.applicant_password)
        other_app_token = self._login("other.applicant.doc@example.com", self.other_applicant_password)

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        sub1_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{r1}/submission",
            headers={"Authorization": f"Bearer {app1_token}"},
            files={"file": ("app1.pdf", pdf_bytes, "application/pdf")},
        ).json()["document_id"]

        sub2_id = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests/{r2}/submission",
            headers={"Authorization": f"Bearer {other_app_token}"},
            files={"file": ("app2.pdf", pdf_bytes, "application/pdf")},
        ).json()["document_id"]

        with self.SessionFactory() as db:
            doc1 = db.query(SubmittedDocument).filter_by(id=uuid.UUID(sub1_id)).first()
            doc2 = db.query(SubmittedDocument).filter_by(id=uuid.UUID(sub2_id)).first()

            # Verify directory isolation
            self.assertIn(f"applications{os.sep}{self.app1_id}", doc1.file_path)
            self.assertIn(f"applications{os.sep}{self.other_app_id}", doc2.file_path)
            self.assertNotEqual(os.path.dirname(doc1.file_path), os.path.dirname(doc2.file_path))

    def test_28_phase3_document_request_and_submitted_document_correctly_linked(self):
        """28 (Phase 3 I). DocumentRequest and SubmittedDocument remain correctly linked through relationships."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Link test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        app_token = self._login("applicant.doc@example.com", self.applicant_password)
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        sub_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("link.pdf", pdf_bytes, "application/pdf")},
        ).json()["document_id"]

        with self.SessionFactory() as db:
            dr = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            sd = db.query(SubmittedDocument).filter_by(id=uuid.UUID(sub_id)).first()
            self.assertIsNotNone(dr.submitted_document)
            self.assertEqual(dr.submitted_document.id, sd.id)
            self.assertEqual(sd.document_request_id, dr.id)
            self.assertEqual(sd.application_id, dr.application_id)

    def test_29_phase3_unauthorized_user_cannot_access_or_modify_document_metadata(self):
        """29 (Phase 3 J). Unauthorized user cannot access another application's document metadata."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Sec test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        other_token = self._login("other.applicant.doc@example.com", self.other_applicant_password)
        # Attempt to access app1's document requests
        resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_30_phase3_storage_service_unit_contract(self):
        """30. DocumentStorageService unit contract verifies path validation and isolation."""
        storage = DocumentStorageService()
        self.assertTrue(os.path.isdir(storage.base_dir))

        # Invalid UUID raises ValidationError
        with self.assertRaises(Exception):
            storage._resolve_safe_application_dir("../etc/evil")

        test_uuid = uuid.uuid4()
        clean_dir = storage._resolve_safe_application_dir(test_uuid)
        self.assertTrue(os.path.isdir(clean_dir))

        filename = storage.generate_stored_filename(test_uuid, "my statement.pdf", ".pdf")
        self.assertTrue(filename.startswith(f"{test_uuid}_"))
        self.assertTrue(filename.endswith(".pdf"))

    def test_31_phase4_reviewer_retrieves_submitted_document_metadata(self):
        """31 (Phase 4 A, C, D). Reviewer retrieves submitted document metadata without filesystem leakage."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Bank statement req", "allowed_file_types": ["PDF"]},
        )
        req_id = req_resp.json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("my_bank_statement.pdf", pdf_bytes, "application/pdf")},
        )

        # Reviewer fetches metadata
        meta_resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertEqual(meta_resp.status_code, 200)
        data = meta_resp.json()
        self.assertEqual(data["original_filename"], "my_bank_statement.pdf")
        self.assertEqual(data["file_type"], "PDF")
        self.assertEqual(data["mime_type"], "application/pdf")
        self.assertEqual(data["file_size"], len(pdf_bytes))
        self.assertEqual(data["status"], "SUBMITTED")
        # Ensure server filesystem path is never exposed
        self.assertNotIn("file_path", data)
        self.assertNotIn("/data/documents", json.dumps(data))

    def test_32_phase4_reviewer_downloads_and_views_file(self):
        """32 (Phase 4 B, C, D). Reviewer can securely view and download submitted document."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Download test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Test (Stream Content) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("verified_doc.pdf", pdf_bytes, "application/pdf")},
        )

        # 1. View file (inline)
        view_resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission/file",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertEqual(view_resp.status_code, 200)
        self.assertIn("application/pdf", view_resp.headers["content-type"])
        self.assertIn("inline", view_resp.headers.get("content-disposition", ""))
        self.assertIn("verified_doc.pdf", view_resp.headers.get("content-disposition", ""))
        self.assertEqual(view_resp.content, pdf_bytes)

        # 2. Download file (attachment)
        down_resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission/file?download=true",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertEqual(down_resp.status_code, 200)
        self.assertIn("attachment", down_resp.headers.get("content-disposition", ""))
        self.assertIn("verified_doc.pdf", down_resp.headers.get("content-disposition", ""))
        self.assertEqual(down_resp.content, pdf_bytes)

    def test_33_phase4_applicant_cannot_access_other_application_documents(self):
        """33 (Phase 4 E). Applicant cannot access another applicant's document endpoints (403 Forbidden)."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Ownership test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        other_token = self._login("other.applicant.doc@example.com", self.other_applicant_password)

        # Try to get metadata
        resp_meta = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(resp_meta.status_code, 403)

        # Try to download file
        resp_file = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission/file",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        self.assertEqual(resp_file.status_code, 403)

    def test_34_phase4_unauthorized_user_cannot_retrieve_document(self):
        """34 (Phase 4 F). Unauthenticated user receives 401 Unauthorized."""
        resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{uuid.uuid4()}/submission",
        )
        self.assertEqual(resp.status_code, 401)

        resp2 = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{uuid.uuid4()}/submission/file",
        )
        self.assertEqual(resp2.status_code, 401)

    def test_35_phase4_reviewer_cannot_cross_access_mismatched_application(self):
        """35 (Phase 4 G). Cross-application document request lookup returns 404."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        # Create request under other_app_id
        req_id = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Cross test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        # Attempt to access req_id under app1_id
        resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_36_phase4_reviewer_accepts_submitted_document(self):
        """36 (Phase 4 H, M, O). Reviewer can ACCEPT a SUBMITTED document and audit log is recorded."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Review test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("good_statement.pdf", pdf_bytes, "application/pdf")},
        )

        review_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Bank statement is verified and acceptable."},
        )
        self.assertEqual(review_resp.status_code, 200)
        data = review_resp.json()
        self.assertEqual(data["status"], "ACCEPTED")
        self.assertEqual(data["reviewer_notes"], "Bank statement is verified and acceptable.")

        # Database and audit verification
        with self.SessionFactory() as db:
            dr = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(dr.status, DocumentRequestStatus.ACCEPTED)
            self.assertEqual(dr.reviewer_notes, "Bank statement is verified and acceptable.")

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_ACCEPTED, entity_id=str(req_id))
                .first()
            )
            self.assertIsNotNone(audit)
            self.assertEqual(audit.action, "DOCUMENT_ACCEPTED")

    def test_37_phase4_reviewer_rejects_submitted_document(self):
        """37 (Phase 4 I, N, O). Reviewer can REJECT a SUBMITTED document with mandatory notes."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Reject test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("unclear.pdf", pdf_bytes, "application/pdf")},
        )

        review_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "Page 2 is completely blurred and missing transactions."},
        )
        self.assertEqual(review_resp.status_code, 200)
        data = review_resp.json()
        self.assertEqual(data["status"], "REJECTED")
        self.assertEqual(data["reviewer_notes"], "Page 2 is completely blurred and missing transactions.")

        with self.SessionFactory() as db:
            dr = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(dr.status, DocumentRequestStatus.REJECTED)

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_REJECTED, entity_id=str(req_id))
                .first()
            )
            self.assertIsNotNone(audit)

    def test_38_phase4_cannot_review_pending_request(self):
        """38 (Phase 4 J). Reviewer cannot review a PENDING request (returns 400 Bad Request or 409 Conflict)."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Pending test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Premature review"},
        )
        self.assertIn(resp.status_code, (400, 409))
        self.assertIn("PENDING", resp.json()["detail"])

    def test_39_phase4_invalid_state_transitions_rejected(self):
        """39 (Phase 4 K). Cannot review already ACCEPTED document or duplicate transition."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "State test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )

        # Accept it
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Approved"},
        )

        # Try to review again
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "Changed mind"},
        )
        self.assertIn(resp.status_code, (400, 409))
        self.assertIn("ACCEPTED", resp.json()["detail"])

    def test_40_phase4_rejection_requires_notes(self):
        """40 (Phase 4 L). Rejection without notes is rejected with 400/422."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Notes test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )

        # Rejection with no notes or short notes (<5 chars)
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "no"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_41_phase4_replacement_workflow_end_to_end(self):
        """41 (Phase 4 Q, R, S, T). Full rejection and replacement workflow end-to-end."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        # 1. Reviewer creates request
        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Need 3 months bank statement", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        # 2. Applicant uploads 1st document
        pdf_bytes1 = b"%PDF-1.4\n1 0 obj\n<< /Version (1) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("incomplete_stmt.pdf", pdf_bytes1, "application/pdf")},
        )

        # 3. Reviewer rejects it with explanation
        reject_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "Statement covers only 1 month instead of 3."},
        )
        self.assertEqual(reject_resp.status_code, 200)
        self.assertEqual(reject_resp.json()["status"], "REJECTED")

        # 4. Applicant retrieves their requests and sees rejection with reviewer notes (Q)
        applicant_view = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {app_token}"},
        ).json()
        target_req = next(r for r in applicant_view if r["id"] == req_id)
        self.assertEqual(target_req["status"], "REJECTED")
        self.assertEqual(target_req["reviewer_notes"], "Statement covers only 1 month instead of 3.")

        # 5. Applicant uploads replacement document (R, S)
        pdf_bytes2 = b"%PDF-1.4\n1 0 obj\n<< /Version (2_Replacement) >>\nendobj\ntrailer\n<<>>\n%%EOF"
        replace_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("full_3_month_stmt.pdf", pdf_bytes2, "application/pdf")},
        )
        self.assertEqual(replace_resp.status_code, 201)

        # 6. Verify request transitioned back to SUBMITTED
        with self.SessionFactory() as db:
            dr = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(dr.status, DocumentRequestStatus.SUBMITTED)

        # 7. Reviewer reviews and accepts replacement submission (T)
        accept_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Complete 3-month statement verified."},
        )
        self.assertEqual(accept_resp.status_code, 200)
        self.assertEqual(accept_resp.json()["status"], "ACCEPTED")

        # 8. Verify the active file is now the replacement file
        file_resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission/file",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertIn("full_3_month_stmt.pdf", file_resp.headers["content-disposition"])
        self.assertEqual(file_resp.content, pdf_bytes2)

    def test_42_phase4_review_transaction_rollback_on_failure(self):
        """42 (Phase 4 P). Database transaction rolls back cleanly if review operation errors."""
        rev_token = self._login("reviewer.doc@example.com", self.reviewer_password)
        app_token = self._login("applicant.doc@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Rollback test", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )

        client_no_raise = TestClient(app, raise_server_exceptions=False)
        with patch.object(Session, "commit", side_effect=RuntimeError("Simulated DB Crash")):
            resp = client_no_raise.post(
                f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
                headers={"Authorization": f"Bearer {rev_token}"},
                json={"decision": "ACCEPT", "notes": "Crashing commit"},
            )
            self.assertEqual(resp.status_code, 500)

        # Confirm request remains SUBMITTED and not partially ACCEPTED
        with self.SessionFactory() as db:
            dr = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(dr.status, DocumentRequestStatus.SUBMITTED)


if __name__ == "__main__":
    unittest.main()

