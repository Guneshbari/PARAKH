"""Phase 14B Regression Tests: Audit Log Retrieval and Viewer RBAC."""
import unittest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.audit_events import AuditAction
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.application import Application, ApplicationStatus
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.services.audit import AuditService


class TestPhase14bAuditViewerEndpoints(unittest.TestCase):
    """Test suite validating RBAC, pagination, filtering, and privacy of audit log endpoints."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        def override_get_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        db = self.Session()
        self.admin_id = uuid.uuid4()
        self.reviewer_id = uuid.uuid4()
        self.applicant_id = uuid.uuid4()

        self.admin = User(
            id=self.admin_id,
            email="admin@parakh.local",
            password_hash=hash_password("adminSecret123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.reviewer = User(
            id=self.reviewer_id,
            email="reviewer@parakh.local",
            password_hash=hash_password("reviewerSecret123"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        self.applicant = User(
            id=self.applicant_id,
            email="applicant@parakh.local",
            password_hash=hash_password("applicantSecret123"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add_all([self.admin, self.reviewer, self.applicant])
        db.commit()

        # Seed sample applicant profile, application and audit events
        self.app_id = uuid.uuid4()
        from app.models.applicant import ApplicantProfile
        profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.applicant_id,
            gig_work_type="Delivery",
        )
        db.add(profile)
        db.commit()

        app_obj = Application(
            id=self.app_id,
            applicant_profile_id=profile.id,
            status=ApplicationStatus.SUBMITTED,
            requested_loan_amount=50000.0,
            loan_purpose="Vehicle repair",
        )
        db.add(app_obj)
        db.commit()

        audit_service = AuditService(db=db)
        self.event_login = audit_service.record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity_type="Authentication",
            user_id=self.reviewer_id,
            metadata={"outcome": "SUCCESS", "actor_role": "REVIEWER"},
            commit=True,
        )
        event_app = audit_service.record_event(
            action=AuditAction.APPLICATION_CREATED,
            entity_type="Application",
            entity_id=str(self.app_id),
            user_id=self.applicant_id,
            application_id=self.app_id,
            metadata={"amount": 50000.0, "status": "SUBMITTED"},
            commit=True,
        )
        self.event_app_id = event_app.id
        self.event_app_action = event_app.action

        self.event_assessment = audit_service.record_event(
            action=AuditAction.ASSESSMENT_EXECUTED,
            entity_type="CreditAssessment",
            application_id=self.app_id,
            user_id=self.reviewer_id,
            metadata={"score": 720, "risk_tier": "MODERATE"},
            commit=True,
        )
        db.close()

        self.admin_token = create_access_token(subject=self.admin_id, role=UserRole.ADMIN.value)
        self.reviewer_token = create_access_token(subject=self.reviewer_id, role=UserRole.REVIEWER.value)
        self.applicant_token = create_access_token(subject=self.applicant_id, role=UserRole.APPLICANT.value)

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_01_unauthenticated_request_rejected(self):
        """Unauthenticated requests must receive 401 Unauthorized."""
        res = self.client.get("/api/v1/audit-logs")
        self.assertEqual(res.status_code, 401)

    def test_02_applicant_role_rejected(self):
        """Applicant callers must receive 403 Forbidden."""
        res = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.applicant_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_03_reviewer_role_allowed(self):
        """Reviewer callers must receive 200 OK with list of audit logs."""
        res = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 3)

    def test_04_admin_role_allowed(self):
        """Admin callers must receive 200 OK with list of audit logs."""
        res = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 3)

    def test_05_filter_by_action(self):
        """Filtering by action returns only matching audit records."""
        res = self.client.get(
            f"/api/v1/audit-logs?action={AuditAction.LOGIN_SUCCESS}",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["action"], str(AuditAction.LOGIN_SUCCESS))

    def test_06_filter_by_entity_type(self):
        """Filtering by entity_type returns only matching audit records."""
        res = self.client.get(
            "/api/v1/audit-logs?entity_type=Application",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["entity_type"], "Application")

    def test_07_filter_by_application_id(self):
        """Filtering by application_id returns only audit logs linked to that application."""
        res = self.client.get(
            f"/api/v1/audit-logs?application_id={self.app_id}",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertEqual(item["application_id"], str(self.app_id))

    def test_08_pagination_skip_and_limit(self):
        """Pagination skip and limit return the exact window of records."""
        res_limit1 = self.client.get(
            "/api/v1/audit-logs?limit=1&skip=0",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res_limit1.status_code, 200)
        items1 = res_limit1.json()
        self.assertEqual(len(items1), 1)

        res_limit2 = self.client.get(
            "/api/v1/audit-logs?limit=1&skip=1",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res_limit2.status_code, 200)
        items2 = res_limit2.json()
        self.assertEqual(len(items2), 1)
        self.assertNotEqual(items1[0]["id"], items2[0]["id"])

    def test_09_get_single_audit_log_by_id(self):
        """GET /api/v1/audit-logs/{id} returns the specific event for reviewer and admin."""
        res = self.client.get(
            f"/api/v1/audit-logs/{self.event_app_id}",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        item = res.json()
        self.assertEqual(item["id"], str(self.event_app_id))
        self.assertEqual(item["action"], str(self.event_app_action))
        self.assertEqual(item["entity_type"], "Application")

        # Applicant forbidden
        res_app = self.client.get(
            f"/api/v1/audit-logs/{self.event_app_id}",
            headers={"Authorization": f"Bearer {self.applicant_token}"},
        )
        self.assertEqual(res_app.status_code, 403)

    def test_10_privacy_and_zero_pii_assurance(self):
        """Audit payloads must never leak credentials, password hashes, or prohibited raw data."""
        res = self.client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {self.reviewer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        for log in res.json():
            meta = log.get("metadata") or {}
            self.assertNotIn("password", meta)
            self.assertNotIn("password_hash", meta)
            self.assertNotIn("raw_transactions", meta)
            self.assertNotIn("bank_account", meta)
            self.assertNotIn("secret_key", meta)
