"""Tests for Phase 5 Complete Document Verification Lifecycle Integration.

Validates Requirements A through L from Section 27:
- Test A: Reviewer requests document -> review_outcome created, document_request created,
          application remains UNDER_REVIEW, document_request = PENDING.
- Test B: Applicant submits document -> submitted_document created, document_request = SUBMITTED,
          application = UNDER_REVIEW, DOCUMENT_SUBMITTED audit exists.
- Test C: Reviewer accepts document -> document_request = ACCEPTED, application remains UNDER_REVIEW,
          DOCUMENT_ACCEPTED audit exists.
- Test D: Reviewer rejects document -> document_request = REJECTED, application remains UNDER_REVIEW,
          DOCUMENT_REJECTED audit exists.
- Test E: Replacement request -> old request = REJECTED, new request = PENDING,
          old document remains preserved.
- Test F: Applicant cannot submit to another application -> 403 or 404.
- Test G: Applicant cannot accept/reject documents -> 403 Forbidden.
- Test H: Reviewer cannot access unauthorized application/document -> 404 or 403.
- Test I: Double submission remains blocked -> 409 Conflict.
- Test J: Multiple requests remain independent.
- Test K: Application cannot prematurely progress to completion while required document requests remain unresolved.
- Test L: Accepted evidence allows the existing assessment workflow to continue when all other prerequisites are satisfied.
"""
import io
import json
import os
import unittest
import uuid
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.audit_events import AuditAction
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
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


class TestDocumentLifecyclePhase5(unittest.TestCase):
    """Integration test suite for Phase 5 Document Verification Lifecycle Integration."""

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
                "email": "applicant.phase5@example.com",
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
                business_or_loan_purpose="Vehicle maintenance",
            )
            db.add(self.applicant_profile)
            db.commit()

            # 2. Other Applicant (for cross-access isolation checks)
            self.other_applicant = user_repo.create({
                "email": "other.applicant.phase5@example.com",
                "password_hash": hash_password(self.other_applicant_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)

            self.other_profile = ApplicantProfile(
                user_id=self.other_applicant.id,
                gig_work_type="Courier",
                years_working=1.5,
                average_working_days=22,
                business_or_loan_purpose="Equipment purchase",
            )
            db.add(self.other_profile)
            db.commit()

            # 3. Reviewer User
            self.reviewer = user_repo.create({
                "email": "reviewer.phase5@example.com",
                "password_hash": hash_password(self.reviewer_password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.reviewer_id = str(self.reviewer.id)

            # 4. Primary Application in UNDER_REVIEW status
            self.app1 = app_repo.create({
                "applicant_profile_id": self.applicant_profile.id,
                "requested_loan_amount": 25000.0,
                "status": ApplicationStatus.UNDER_REVIEW,
            }, commit=True)
            self.app1_id = str(self.app1.id)

            # 5. Other Application
            self.other_app = app_repo.create({
                "applicant_profile_id": self.other_profile.id,
                "requested_loan_amount": 15000.0,
                "status": ApplicationStatus.UNDER_REVIEW,
            }, commit=True)
            self.other_app_id = str(self.other_app.id)

    def tearDown(self):
        """Clean up app dependency overrides and tables."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def _login(self, email: str, password: str) -> str:
        """Authenticate user and retrieve Bearer JWT."""
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}: {resp.text}")
        return resp.json()["access_token"]

    def _create_sample_pdf(self, content_str: str = "Test PDF Document") -> bytes:
        """Generate valid minimal PDF byte stream."""
        return (
            f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            f"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents ({content_str}) >>\nendobj\n"
            f"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
            f"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n167\n%%EOF"
        ).encode("utf-8")

    # =========================================================================
    # Test A: Reviewer requests document
    # =========================================================================
    def test_a_reviewer_requests_document_creates_models_and_keeps_app_under_review(self):
        """Test A: Reviewer requests document -> review_outcome created, document_request created,
        application remains UNDER_REVIEW, document_request = PENDING."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
                "notes": "Requesting 3 months bank statement to verify inflow stability.",
                "document_request": {
                    "document_type": "BANK_STATEMENT",
                    "description": "Please provide latest 3 months bank statements.",
                    "allowed_file_types": ["PDF"],
                },
            },
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["outcome"], "ADDITIONAL_INFORMATION_REQUIRED")
        self.assertTrue(data.get("document_requests") and len(data["document_requests"]) > 0)
        self.assertEqual(data["document_requests"][0]["status"], "PENDING")

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)

            doc_req = db.query(DocumentRequest).filter_by(application_id=uuid.UUID(self.app1_id)).first()
            self.assertIsNotNone(doc_req)
            self.assertEqual(doc_req.status, DocumentRequestStatus.PENDING)

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_REQUESTED, entity_id=str(doc_req.id))
                .first()
            )
            self.assertIsNotNone(audit)

    # =========================================================================
    # Test B: Applicant submits document
    # =========================================================================
    def test_b_applicant_submits_document_transitions_request_and_keeps_app_under_review(self):
        """Test B: Applicant submits document -> submitted_document created, document_request = SUBMITTED,
        application = UNDER_REVIEW, DOCUMENT_SUBMITTED audit exists."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        create_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "document_type": "BANK_STATEMENT",
                "description": "Upload statement.",
                "allowed_file_types": ["PDF"],
            },
        )
        req_id = create_resp.json()["id"]

        pdf_bytes = self._create_sample_pdf("Bank Statement Data")
        upload_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("stmt.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(upload_resp.status_code, 201)

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)

            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.SUBMITTED)

            sub = db.query(SubmittedDocument).filter_by(document_request_id=uuid.UUID(req_id)).first()
            self.assertIsNotNone(sub)
            self.assertEqual(sub.original_filename, "stmt.pdf")

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_SUBMITTED, entity_id=str(sub.id))
                .first()
            )
            self.assertIsNotNone(audit)

    # =========================================================================
    # Test C: Reviewer accepts document
    # =========================================================================
    def test_c_reviewer_accepts_document_transitions_request_and_keeps_app_under_review(self):
        """Test C: Reviewer accepts document -> document_request = ACCEPTED, application remains UNDER_REVIEW,
        DOCUMENT_ACCEPTED audit exists."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Upload statement.", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("stmt.pdf", self._create_sample_pdf(), "application/pdf")},
        )

        review_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Statement is clear and meets requirements."},
        )
        self.assertEqual(review_resp.status_code, 200)
        self.assertEqual(review_resp.json()["status"], "ACCEPTED")

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)

            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.ACCEPTED)

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_ACCEPTED, entity_id=str(req_id))
                .first()
            )
            self.assertIsNotNone(audit)

    # =========================================================================
    # Test D: Reviewer rejects document
    # =========================================================================
    def test_d_reviewer_rejects_document_transitions_request_and_keeps_app_under_review(self):
        """Test D: Reviewer rejects document -> document_request = REJECTED, application remains UNDER_REVIEW,
        DOCUMENT_REJECTED audit exists."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Upload statement.", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("blurry.pdf", self._create_sample_pdf(), "application/pdf")},
        )

        review_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "Page 2 transactions are unreadable."},
        )
        self.assertEqual(review_resp.status_code, 200)
        self.assertEqual(review_resp.json()["status"], "REJECTED")

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)

            doc_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req_id)).first()
            self.assertEqual(doc_req.status, DocumentRequestStatus.REJECTED)

            audit = (
                db.query(AuditLog)
                .filter_by(action=AuditAction.DOCUMENT_REJECTED, entity_id=str(req_id))
                .first()
            )
            self.assertIsNotNone(audit)

    # =========================================================================
    # Test E: Replacement request workflow
    # =========================================================================
    def test_e_replacement_request_preserves_old_and_creates_new_pending(self):
        """Test E: Replacement request -> old request = REJECTED, new request = PENDING,
        old document remains preserved."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        # 1. Create request
        req1_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Need bank statement", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        # 2. Upload document 1
        pdf1 = self._create_sample_pdf("Document 1 Content")
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("initial_stmt.pdf", pdf1, "application/pdf")},
        )

        # 3. Reviewer rejects document 1
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "REJECT", "notes": "Need clearer document with bank seal."},
        )

        # 4. Reviewer creates replacement request via dedicated endpoint
        replacement_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/replacement",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"notes": "Please provide official e-statement directly from internet banking."},
        )
        self.assertEqual(replacement_resp.status_code, 201)
        req2_id = replacement_resp.json()["id"]
        self.assertNotEqual(req1_id, req2_id)
        self.assertEqual(replacement_resp.json()["status"], "PENDING")

        # 5. Assert database invariant: old request is REJECTED, new request is PENDING, old document is preserved
        with self.SessionFactory() as db:
            old_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req1_id)).first()
            self.assertEqual(old_req.status, DocumentRequestStatus.REJECTED)

            new_req = db.query(DocumentRequest).filter_by(id=uuid.UUID(req2_id)).first()
            self.assertEqual(new_req.status, DocumentRequestStatus.PENDING)

            old_sub = db.query(SubmittedDocument).filter_by(document_request_id=uuid.UUID(req1_id)).first()
            self.assertIsNotNone(old_sub, "Old submitted document must remain preserved")
            self.assertEqual(old_sub.original_filename, "initial_stmt.pdf")

        # 6. Cannot create duplicate replacement while new request is pending (Section 12)
        dup_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/replacement",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"notes": "Duplicate replacement attempt"},
        )
        self.assertEqual(dup_resp.status_code, 409)

    # =========================================================================
    # Test F: Cross-application submission isolation
    # =========================================================================
    def test_f_applicant_cannot_submit_to_another_application(self):
        """Test F: Applicant cannot submit to another application (returns 403 or 404)."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        other_req_id = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Other doc", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        resp = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests/{other_req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("hack.pdf", self._create_sample_pdf(), "application/pdf")},
        )
        self.assertIn(resp.status_code, (403, 404))

    # =========================================================================
    # Test G: Applicant cannot review documents
    # =========================================================================
    def test_g_applicant_cannot_accept_or_reject_documents(self):
        """Test G: Applicant cannot accept/reject documents (returns 403 Forbidden)."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Test doc", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {app_token}"},
            json={"decision": "ACCEPT", "notes": "Self approval attempt"},
        )
        self.assertEqual(resp.status_code, 403)

    # =========================================================================
    # Test H: Reviewer cross-application mismatch isolation
    # =========================================================================
    def test_h_reviewer_cannot_cross_access_mismatched_application_request(self):
        """Test H: Reviewer cannot access document belonging to another application (404/403)."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)

        other_req_id = self.client.post(
            f"/api/v1/applications/{self.other_app_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Other request", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        resp = self.client.get(
            f"/api/v1/applications/{self.app1_id}/document-requests/{other_req_id}/submission",
            headers={"Authorization": f"Bearer {rev_token}"},
        )
        self.assertIn(resp.status_code, (404, 403))

    # =========================================================================
    # Test I: Double submission blocked
    # =========================================================================
    def test_i_double_submission_remains_blocked(self):
        """Test I: Double submission against an already SUBMITTED request is rejected with 409 Conflict."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Test request", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        sub1 = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("doc1.pdf", self._create_sample_pdf(), "application/pdf")},
        )
        self.assertEqual(sub1.status_code, 201)

        # Attempt second upload on same request while SUBMITTED
        sub2 = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("doc2.pdf", self._create_sample_pdf(), "application/pdf")},
        )
        self.assertEqual(sub2.status_code, 409)

    # =========================================================================
    # Test J: Multiple requests remain independent
    # =========================================================================
    def test_j_multiple_requests_remain_independent(self):
        """Test J: Multiple requests remain independent:
        BANK_STATEMENT = ACCEPTED, INCOME_PROOF = PENDING, BUSINESS_RECORD = SUBMITTED.
        No cross-contamination of status."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        req1_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Req 1", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        req2_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "INCOME_PROOF", "description": "Req 2", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        req3_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BUSINESS_RECORD", "description": "Req 3", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        # Submit req1 and accept it
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("b1.pdf", self._create_sample_pdf(), "application/pdf")},
        )
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req1_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Accepted statement"},
        )

        # Leave req2 PENDING

        # Submit req3
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req3_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("b3.pdf", self._create_sample_pdf(), "application/pdf")},
        )

        # Verify all statuses are exact and independent
        with self.SessionFactory() as db:
            r1 = db.query(DocumentRequest).filter_by(id=uuid.UUID(req1_id)).first()
            r2 = db.query(DocumentRequest).filter_by(id=uuid.UUID(req2_id)).first()
            r3 = db.query(DocumentRequest).filter_by(id=uuid.UUID(req3_id)).first()

            self.assertEqual(r1.status, DocumentRequestStatus.ACCEPTED)
            self.assertEqual(r2.status, DocumentRequestStatus.PENDING)
            self.assertEqual(r3.status, DocumentRequestStatus.SUBMITTED)

    # =========================================================================
    # Test K: Application cannot prematurely complete while requests unresolved
    # =========================================================================
    def test_k_application_cannot_prematurely_complete_with_unresolved_requests(self):
        """Test K: Application cannot prematurely progress to completion while required
        document requests remain unresolved."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)

        # Create document request (PENDING)
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Need statement", "allowed_file_types": ["PDF"]},
        )

        # Attempt to complete review
        complete_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "outcome": "REVIEWED",
                "notes": "Premature attempt to complete review without evidence.",
            },
        )
        self.assertIn(complete_resp.status_code, (400, 409))
        self.assertIn("unresolved", complete_resp.json()["detail"].lower())

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.UNDER_REVIEW)

    # =========================================================================
    # Test L: Accepted evidence allows progression
    # =========================================================================
    def test_l_accepted_evidence_allows_assessment_workflow_to_continue(self):
        """Test L: Accepted evidence allows the existing assessment workflow to continue
        when all other prerequisites are satisfied."""
        rev_token = self._login("reviewer.phase5@example.com", self.reviewer_password)
        app_token = self._login("applicant.phase5@example.com", self.applicant_password)

        # 1. Request document
        req_id = self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"document_type": "BANK_STATEMENT", "description": "Need statement", "allowed_file_types": ["PDF"]},
        ).json()["id"]

        # 2. Upload document
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/submission",
            headers={"Authorization": f"Bearer {app_token}"},
            files={"file": ("verified_stmt.pdf", self._create_sample_pdf(), "application/pdf")},
        )

        # 3. Reviewer accepts document
        self.client.post(
            f"/api/v1/applications/{self.app1_id}/document-requests/{req_id}/review",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={"decision": "ACCEPT", "notes": "Bank statement fully verified."},
        )

        # 4. Now reviewer can complete the review
        complete_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers={"Authorization": f"Bearer {rev_token}"},
            json={
                "outcome": "REVIEWED",
                "notes": "All requested documents verified and accepted. Application approved.",
            },
        )
        self.assertEqual(complete_resp.status_code, 201)

        with self.SessionFactory() as db:
            app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertEqual(app.status, ApplicationStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
