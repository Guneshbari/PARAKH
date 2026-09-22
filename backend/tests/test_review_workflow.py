"""Phase 8 Review & Audit Workflow Integration Tests.

Validates the complete end-to-end persistent reviewer workflow:
1. Reviewer login -> JWT authentication.
2. Open application -> verify applicant and application data.
3. Obtain credit assessment -> verify assessment exists or can be computed.
4. Choose review action & enter notes -> submit review via POST /api/v1/applications/{id}/reviews.
5. Transactional persistence:
   - ReviewOutcome is persisted to database
   - Application status is updated atomically
   - AuditLog is created with reviewer identity, action, and application reference
6. Applicant visibility:
   - Applicant logs in / uses JWT
   - Retrieves same application via GET /api/v1/applications/{id}
   - Sees updated application status
7. RBAC & Validation:
   - Applicant cannot submit review (403 Forbidden)
   - Reviewer ID cannot be spoofed to another user ID
   - Notes validation: rejects notes shorter than 10 characters (422 Unprocessable Entity)
   - Invalid application ID produces 404 Not Found
   - All supported review outcomes: RECORD_OUTCOME (REVIEWED), MANUAL_REVIEW (ESCALATED), REQUEST_VERIFICATION (ADDITIONAL_INFORMATION_REQUIRED).
"""
import unittest
from datetime import datetime, timezone
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
    Consent,
    CreditAssessment,
    ModelVersion,
    ReviewOutcome,
    ReviewOutcomeType,
    RiskLevel,
    User,
    UserRole,
)
from app.repositories.application import ApplicationRepository
from app.repositories.user import UserRepository


class TestReviewWorkflowIntegration(unittest.TestCase):
    """End-to-end test suite for Reviewer Workflow, Persistence, Audit, and Applicant Visibility."""

    def setUp(self):
        """Set up an in-memory SQLite database, tables, and FastAPI TestClient."""
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
        self.reviewer_password = "ReviewerPass123!"
        self.other_reviewer_password = "OtherReviewerPass123!"

        with self.SessionFactory() as db:
            user_repo = UserRepository(db=db)
            app_repo = ApplicationRepository(db=db)

            # 1. Applicant user + profile
            self.applicant = user_repo.create({
                "email": "applicant.flow@example.com",
                "password_hash": hash_password(self.applicant_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.applicant_id = str(self.applicant.id)

            self.applicant_profile = ApplicantProfile(
                user_id=self.applicant.id,
                gig_work_type="Delivery Partner",
                years_working=2.5,
                average_working_days=24,
                business_or_loan_purpose="Working capital",
            )
            db.add(self.applicant_profile)
            db.commit()

            # 2. Primary Reviewer
            self.reviewer = user_repo.create({
                "email": "senior.reviewer@example.com",
                "password_hash": hash_password(self.reviewer_password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.reviewer_id = str(self.reviewer.id)

            # 3. Secondary Reviewer
            self.other_reviewer = user_repo.create({
                "email": "other.reviewer@example.com",
                "password_hash": hash_password(self.other_reviewer_password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.other_reviewer_id = str(self.other_reviewer.id)

            # 4. Applications under assessment / review
            self.app1 = app_repo.create({
                "applicant_profile_id": self.applicant_profile.id,
                "requested_loan_amount": 50000.0,
                "preferred_repayment_period": 12,
                "loan_purpose": "Working capital",
                "status": ApplicationStatus.ASSESSED,
            }, commit=True)
            self.app1_id = str(self.app1.id)

            # Attach an assessment to app1
            self.model_ver = ModelVersion(
                model_name="MockEngine",
                version="v1.0",
                description="Mock Assessment Engine",
                is_active=True,
            )
            db.add(self.model_ver)
            db.commit()

            self.assessment1 = CreditAssessment(
                application_id=self.app1.id,
                model_version_id=self.model_ver.id,
                credit_score=720,
                risk_level=RiskLevel.LOWER,
                confidence=0.88,
            )
            db.add(self.assessment1)
            db.commit()

            # App 2 for MANUAL_REVIEW escalation testing
            self.app2 = app_repo.create({
                "applicant_profile_id": self.applicant_profile.id,
                "requested_loan_amount": 75000.0,
                "preferred_repayment_period": 18,
                "loan_purpose": "Equipment upgrade",
                "status": ApplicationStatus.MANUAL_REVIEW,
            }, commit=True)
            self.app2_id = str(self.app2.id)

            # App 3 for REQUEST_VERIFICATION testing
            self.app3 = app_repo.create({
                "applicant_profile_id": self.applicant_profile.id,
                "requested_loan_amount": 60000.0,
                "preferred_repayment_period": 12,
                "loan_purpose": "Inventory expansion",
                "status": ApplicationStatus.MANUAL_REVIEW,
            }, commit=True)
            self.app3_id = str(self.app3.id)

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

    def test_01_complete_reviewer_workflow_record_outcome(self):
        """Full flow: Reviewer logs in, views app/assessment, records outcome, updates status & audit, applicant verifies."""
        # 1. Reviewer Login
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        rev_headers = {"Authorization": f"Bearer {reviewer_token}"}

        # 2. Open Application
        app_resp = self.client.get(f"/api/v1/applications/{self.app1_id}", headers=rev_headers)
        self.assertEqual(app_resp.status_code, 200)
        app_data = app_resp.json()
        self.assertEqual(app_data["id"], self.app1_id)
        self.assertEqual(app_data["status"], "ASSESSED")

        # 3. View Assessment
        assess_resp = self.client.get(f"/api/v1/applications/{self.app1_id}/assessments/latest", headers=rev_headers)
        self.assertEqual(assess_resp.status_code, 200)
        assess_data = assess_resp.json()
        self.assertEqual(assess_data["risk_level"], "LOWER")
        self.assertEqual(assess_data["credit_score"], 720)

        # 4. Choose Review Action (RECORD_OUTCOME -> REVIEWED) & enter notes >= 10 chars
        review_payload = {
            "outcome": "REVIEWED",
            "notes": "Verified verified GSTIN and positive cash flows. Approved standard credit line.",
        }
        submit_resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=rev_headers,
            json=review_payload,
        )
        self.assertEqual(submit_resp.status_code, 201)
        review_result = submit_resp.json()
        self.assertEqual(review_result["application_id"], self.app1_id)
        self.assertEqual(review_result["outcome"], "REVIEWED")
        self.assertEqual(review_result["reviewer_id"], self.reviewer_id)

        # 5. Verify Transactional Persistence directly in DB
        with self.SessionFactory() as db:
            # Check ReviewOutcome
            saved_review = db.query(ReviewOutcome).filter_by(application_id=uuid.UUID(self.app1_id)).first()
            self.assertIsNotNone(saved_review)
            self.assertEqual(saved_review.outcome, ReviewOutcomeType.REVIEWED)
            self.assertEqual(str(saved_review.reviewer_id), self.reviewer_id)

            # Check Application status was updated atomically to COMPLETED
            saved_app = db.query(Application).filter_by(id=uuid.UUID(self.app1_id)).first()
            self.assertIsNotNone(saved_app)
            self.assertEqual(saved_app.status, ApplicationStatus.COMPLETED)

            # Check AuditLog records
            audit_events = db.query(AuditLog).filter_by(application_id=uuid.UUID(self.app1_id)).all()
            actions = [e.action for e in audit_events]
            self.assertIn(AuditAction.APPLICATION_STATUS_CHANGED, actions)
            self.assertIn(AuditAction.REVIEW_CREATED, actions)

            status_audit = [e for e in audit_events if e.action == AuditAction.APPLICATION_STATUS_CHANGED][0]
            self.assertEqual(str(status_audit.user_id), self.reviewer_id)
            self.assertEqual(status_audit.audit_metadata.get("new_status"), "COMPLETED")

        # 6. Applicant logs in and sees resulting status
        applicant_token = self._login("applicant.flow@example.com", self.applicant_password)
        app_headers = {"Authorization": f"Bearer {applicant_token}"}

        applicant_view = self.client.get(f"/api/v1/applications/{self.app1_id}", headers=app_headers)
        self.assertEqual(applicant_view.status_code, 200)
        self.assertEqual(applicant_view.json()["status"], "COMPLETED")

    def test_02_reviewer_action_manual_review_escalation(self):
        """Action MANUAL_REVIEW: Review outcome ESCALATED transitions/retains MANUAL_REVIEW status."""
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        rev_headers = {"Authorization": f"Bearer {reviewer_token}"}

        review_payload = {
            "outcome": "ESCALATED",
            "notes": "Escalating to senior risk committee due to high tenure and seasonal gig variance.",
        }
        submit_resp = self.client.post(
            f"/api/v1/applications/{self.app2_id}/reviews",
            headers=rev_headers,
            json=review_payload,
        )
        self.assertEqual(submit_resp.status_code, 201)

        with self.SessionFactory() as db:
            saved_app = db.query(Application).filter_by(id=uuid.UUID(self.app2_id)).first()
            self.assertEqual(saved_app.status, ApplicationStatus.MANUAL_REVIEW)

            saved_review = db.query(ReviewOutcome).filter_by(application_id=uuid.UUID(self.app2_id)).first()
            self.assertEqual(saved_review.outcome, ReviewOutcomeType.ESCALATED)

    def test_03_reviewer_action_request_verification(self):
        """Action REQUEST_VERIFICATION: Review outcome ADDITIONAL_INFORMATION_REQUIRED transitions to UNDER_REVIEW."""
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        rev_headers = {"Authorization": f"Bearer {reviewer_token}"}

        review_payload = {
            "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
            "notes": "Please provide last 3 months electricity bill or alternate address proof for KYC.",
        }
        submit_resp = self.client.post(
            f"/api/v1/applications/{self.app3_id}/reviews",
            headers=rev_headers,
            json=review_payload,
        )
        self.assertEqual(submit_resp.status_code, 201)

        with self.SessionFactory() as db:
            saved_app = db.query(Application).filter_by(id=uuid.UUID(self.app3_id)).first()
            self.assertEqual(saved_app.status, ApplicationStatus.UNDER_REVIEW)

        # Applicant sees UNDER_REVIEW
        applicant_token = self._login("applicant.flow@example.com", self.applicant_password)
        applicant_view = self.client.get(f"/api/v1/applications/{self.app3_id}", headers={"Authorization": f"Bearer {applicant_token}"})
        self.assertEqual(applicant_view.status_code, 200)
        self.assertEqual(applicant_view.json()["status"], "UNDER_REVIEW")

    def test_04_unauthorized_applicant_cannot_submit_review(self):
        """APPLICANT role cannot submit review outcomes -> HTTP 403 Forbidden."""
        applicant_token = self._login("applicant.flow@example.com", self.applicant_password)
        headers = {"Authorization": f"Bearer {applicant_token}"}

        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={
                "outcome": "REVIEWED",
                "notes": "Attempting unauthorized approval from applicant role session.",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_05_reviewer_identity_from_jwt_not_spoofed(self):
        """Reviewer ID is bound to JWT actor; spoofing another reviewer ID in payload is blocked."""
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {reviewer_token}"}

        # Attempt to submit review with other reviewer's ID
        resp = self.client.post(
            f"/api/v1/applications/{self.app2_id}/reviews",
            headers=headers,
            json={
                "reviewer_id": self.other_reviewer_id,
                "outcome": "REVIEWED",
                "notes": "Attempting to attribute this review to another reviewer account.",
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("own reviewer ID", resp.json()["detail"])

    def test_06_notes_minimum_length_validation(self):
        """Review submission requires notes of at least 10 non-whitespace characters."""
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {reviewer_token}"}

        # Short notes (< 10 chars)
        resp = self.client.post(
            f"/api/v1/applications/{self.app1_id}/reviews",
            headers=headers,
            json={"outcome": "REVIEWED", "notes": "ok"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_07_invalid_application_id_returns_404(self):
        """Review submission for nonexistent application produces HTTP 404."""
        reviewer_token = self._login("senior.reviewer@example.com", self.reviewer_password)
        headers = {"Authorization": f"Bearer {reviewer_token}"}

        random_id = str(uuid.uuid4())
        resp = self.client.post(
            f"/api/v1/applications/{random_id}/reviews",
            headers=headers,
            json={
                "outcome": "REVIEWED",
                "notes": "Notes for nonexistent application ID to verify error handling.",
            },
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
