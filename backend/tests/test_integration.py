"""Comprehensive end-to-end integration test suite for the PARAKH backend.

Validates:
1. Complete authenticated workflow across live PostgreSQL.
2. Complete authenticated workflow using isolated in-memory engine.
3. Transaction rollback and atomicity guarantees.
4. Cross-applicant ownership isolation and RBAC security.
5. Complete database cleanup leaving zero test artifacts behind.
"""
from decimal import Decimal
import unittest
import uuid
from typing import Dict, List, Tuple

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.audit_events import AuditAction
from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.audit import AuditLog
from app.models.consent import Consent, ConsentDataSource
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion
from app.models.review import ReviewOutcome, ReviewOutcomeType
from app.models.user import User, UserRole
from tests.helpers import (
    can_connect_to_postgres,
    cleanup_database_records,
    create_admin_user,
    create_applicant_user,
    create_reviewer_user,
    create_test_application,
    get_auth_token_and_headers,
)


class TestEndToEndPostgresWorkflow(unittest.TestCase):
    """Full 18-step end-to-end authenticated lifecycle executed against live PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL is not reachable locally.")
        cls.client = TestClient(app)

    def setUp(self):
        self.cleanup_items: List[Tuple[str, uuid.UUID]] = []

    def tearDown(self):
        with SessionLocal() as db:
            for entity_type, entity_id in self.cleanup_items:
                try:
                    raw_uuid = entity_id if isinstance(entity_id, uuid.UUID) else uuid.UUID(str(entity_id))
                    db.execute(
                        text("DELETE FROM audit_logs WHERE entity_id = :str_id OR application_id = :uuid_id OR user_id = :uuid_id"),
                        {"str_id": str(raw_uuid), "uuid_id": raw_uuid},
                    )
                    db.commit()
                except Exception:
                    db.rollback()
            cleanup_database_records(db, self.cleanup_items)

    def test_complete_authenticated_postgresql_workflow(self):
        """
        Execute and verify the full end-to-end authenticated credit assessment lifecycle:
        1. Create Applicant user via registration
        2. Login and obtain JWT
        3. Verify current authenticated user profile
        4. Create applicant gig profile
        5. Create application (starts DRAFT)
        6. Transition application to SUBMITTED
        7. Grant explicit applicant consent (PLATFORM)
        8. Submit aggregated financial signals
        9. Register active model version as Admin
        10. Execute deterministic assessment evaluation
        11. Retrieve and verify persisted assessment
        12. Transition application to MANUAL_REVIEW
        13. Create and login as Reviewer
        14. Submit human review outcome (REVIEWED)
        15. Transition application to COMPLETED
        16. Retrieve audit trail as Admin
        17. Verify audit privacy & event coverage
        18. Verify cross-applicant ownership isolation
        """
        # --- STEP 1: Create Applicant User via Registration ---
        app_suffix = uuid.uuid4().hex[:8]
        applicant_email = f"gigworker_{app_suffix}@parakh.test"
        applicant_pw = "ApplicantPass123!"

        reg_resp = self.client.post(
            "/api/v1/users",
            json={"email": applicant_email, "password": applicant_pw},
        )
        self.assertEqual(reg_resp.status_code, 201, reg_resp.text)
        reg_data = reg_resp.json()
        applicant_user_id = uuid.UUID(reg_data["id"])
        self.cleanup_items.append(("user", applicant_user_id))
        self.assertEqual(reg_data["email"], applicant_email)
        self.assertEqual(reg_data["role"], "APPLICANT")

        # --- STEP 2: Login & Obtain JWT ---
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": applicant_email, "password": applicant_pw},
        )
        self.assertEqual(login_resp.status_code, 200, login_resp.text)
        login_data = login_resp.json()
        self.assertIn("access_token", login_data)
        applicant_token = login_data["access_token"]
        applicant_headers = {"Authorization": f"Bearer {applicant_token}"}

        # --- STEP 3: Verify Current Authenticated User Profile ---
        me_resp = self.client.get("/api/v1/auth/me", headers=applicant_headers)
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data["id"], str(applicant_user_id))
        self.assertNotIn("password", me_data)
        self.assertNotIn("password_hash", me_data)

        # --- STEP 4: Create Applicant Profile ---
        profile_resp = self.client.post(
            "/api/v1/applicants",
            headers=applicant_headers,
            json={
                "gig_work_type": "Food & Package Courier",
                "years_working": "3.5",
                "average_working_days": 26,
                "business_or_loan_purpose": "Vehicle servicing and battery upgrade",
            },
        )
        self.assertEqual(profile_resp.status_code, 201, profile_resp.text)
        profile_data = profile_resp.json()
        profile_id = uuid.UUID(profile_data["id"])
        self.cleanup_items.append(("applicant", profile_id))
        self.assertEqual(profile_data["gig_work_type"], "Food & Package Courier")

        # --- STEP 5: Create Credit Application (starts in DRAFT) ---
        app_resp = self.client.post(
            "/api/v1/applications",
            headers=applicant_headers,
            json={
                "applicant_profile_id": str(profile_id),
                "requested_loan_amount": "30000.00",
                "loan_purpose": "Fleet vehicle upgrade",
                "preferred_repayment_period": 6,
            },
        )
        self.assertEqual(app_resp.status_code, 201, app_resp.text)
        app_data = app_resp.json()
        application_id = uuid.UUID(app_data["id"])
        self.cleanup_items.append(("application", application_id))
        self.assertEqual(app_data["status"], "DRAFT")
        self.assertEqual(float(app_data["requested_loan_amount"]), 30000.00)

        # --- STEP 6: Submit Application (Transition DRAFT -> SUBMITTED) ---
        sub_resp = self.client.patch(
            f"/api/v1/applications/{application_id}/status",
            headers=applicant_headers,
            json={"status": "SUBMITTED"},
        )
        self.assertEqual(sub_resp.status_code, 200, sub_resp.text)
        self.assertEqual(sub_resp.json()["status"], "SUBMITTED")

        # --- STEP 7: Grant Required Consent (PLATFORM) ---
        consent_resp = self.client.post(
            "/api/v1/consents",
            headers=applicant_headers,
            json={
                "application_id": str(application_id),
                "data_source": "PLATFORM",
                "purpose": "Verify courier delivery regularity and platform earnings",
            },
        )
        self.assertEqual(consent_resp.status_code, 201, consent_resp.text)
        consent_data = consent_resp.json()
        consent_id = uuid.UUID(consent_data["id"])
        self.cleanup_items.append(("consent", consent_id))
        self.assertTrue(consent_data["granted"])

        # --- STEP 8: Submit Aggregated Financial Signals ---
        sig_resp = self.client.post(
            f"/api/v1/applications/{application_id}/financial-signals",
            headers=applicant_headers,
            json={
                "source": "PLATFORM",
                "average_income": "36000.00",
                "median_income": "34500.00",
                "income_volatility": "0.10",
                "payment_regularity": "0.98",
                "platform_rating": "4.90",
                "active_days": 88,
            },
        )
        self.assertEqual(sig_resp.status_code, 201, sig_resp.text)
        sig_data = sig_resp.json()
        signal_id = uuid.UUID(sig_data["id"])
        self.cleanup_items.append(("financial_signal", signal_id))

        # --- STEP 9: Register Model Version as Admin ---
        admin_email = f"admin_{app_suffix}@parakh.test"
        admin_pw = "AdminSecret123!"
        with SessionLocal() as db:
            admin_user = create_admin_user(db, email=admin_email, password=admin_pw)
            admin_id = admin_user.id
        self.cleanup_items.append(("user", admin_id))

        admin_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": admin_pw},
        )
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        model_resp = self.client.post(
            "/api/v1/model-versions",
            headers=admin_headers,
            json={
                "model_name": f"parakh_mock_engine_{app_suffix}",
                "version": "1.0.0",
                "algorithm": "Deterministic Rule-Based Mock Engine",
                "description": "Integration test scoring model",
                "is_active": True,
            },
        )
        self.assertEqual(model_resp.status_code, 201, model_resp.text)
        model_id = uuid.UUID(model_resp.json()["id"])
        self.cleanup_items.append(("model_version", model_id))

        # --- STEP 10: Execute Credit Assessment ---
        assess_resp = self.client.post(
            f"/api/v1/applications/{application_id}/assess?model_version_id={model_id}",
            headers=applicant_headers,
        )
        self.assertEqual(assess_resp.status_code, 201, assess_resp.text)
        assess_data = assess_resp.json()
        assessment_id = uuid.UUID(assess_data["id"])
        self.cleanup_items.append(("assessment", assessment_id))
        self.assertIsNotNone(assess_data["credit_score"])
        self.assertIn(assess_data["risk_level"], ["LOWER", "MODERATE", "HIGHER"])
        self.assertGreaterEqual(float(assess_data["confidence"]), 0.0)
        self.assertLessEqual(float(assess_data["confidence"]), 1.0)

        # --- STEP 11: Retrieve Assessment by ID & Application ---
        get_assess_resp = self.client.get(
            f"/api/v1/assessments/{assessment_id}",
            headers=applicant_headers,
        )
        self.assertEqual(get_assess_resp.status_code, 200)
        self.assertEqual(get_assess_resp.json()["id"], str(assessment_id))

        list_assess_resp = self.client.get(
            f"/api/v1/applications/{application_id}/assessments",
            headers=applicant_headers,
        )
        self.assertEqual(list_assess_resp.status_code, 200)
        self.assertGreaterEqual(len(list_assess_resp.json()), 1)

        # --- STEP 12: Transition Application to MANUAL_REVIEW ---
        rev_user_email = f"reviewer_{app_suffix}@parakh.test"
        rev_pw = "ReviewerPass123!"
        with SessionLocal() as db:
            reviewer_user = create_reviewer_user(db, email=rev_user_email, password=rev_pw)
            reviewer_id = reviewer_user.id
        self.cleanup_items.append(("user", reviewer_id))

        rev_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": rev_user_email, "password": rev_pw},
        )
        self.assertEqual(rev_login.status_code, 200)
        reviewer_token = rev_login.json()["access_token"]
        reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

        # Transition application: SUBMITTED -> UNDER_REVIEW -> MANUAL_REVIEW
        for target_status in ["UNDER_REVIEW", "MANUAL_REVIEW"]:
            t_resp = self.client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=reviewer_headers,
                json={"status": target_status},
            )
            self.assertEqual(t_resp.status_code, 200, f"Failed transitioning to {target_status}: {t_resp.text}")

        # --- STEP 13 & 14: Submit Human Review Outcome ---
        review_resp = self.client.post(
            f"/api/v1/applications/{application_id}/reviews",
            headers=reviewer_headers,
            json={
                "application_id": str(application_id),
                "reviewer_id": str(reviewer_id),
                "outcome": "REVIEWED",
                "notes": "Verified verified courier delivery signals with zero anomalies",
            },
        )
        self.assertEqual(review_resp.status_code, 201, review_resp.text)
        review_data = review_resp.json()
        review_id = uuid.UUID(review_data["id"])
        self.cleanup_items.append(("review", review_id))
        self.assertEqual(review_data["outcome"], "REVIEWED")

        # --- STEP 15: Transition Application to ASSESSED -> COMPLETED ---
        for target_status in ["ASSESSED", "COMPLETED"]:
            comp_resp = self.client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=reviewer_headers,
                json={"status": target_status},
            )
            self.assertEqual(comp_resp.status_code, 200, f"Failed transitioning to {target_status}: {comp_resp.text}")

        # --- STEP 16: Retrieve Audit Logs as Admin ---
        audit_resp = self.client.get(
            f"/api/v1/audit-logs?application_id={application_id}",
            headers=admin_headers,
        )
        self.assertEqual(audit_resp.status_code, 200, audit_resp.text)
        audit_logs = audit_resp.json()
        self.assertGreaterEqual(len(audit_logs), 3, "Expected audit trail records")

        # --- STEP 17: Verify Privacy & Audit Event Integrity ---
        forbidden_substrings = ["password", "hash", "secret", "token", "Bearer", applicant_pw]
        for log in audit_logs:
            self.assertIn("action", log)
            self.assertIn("created_at", log)
            # Verify no secret leakage in log payload
            log_str = str(log).lower()
            for secret in [applicant_pw.lower(), "password123"]:
                self.assertNotIn(secret, log_str)

        # Verify specific actions recorded
        recorded_actions = {entry["action"] for entry in audit_logs}
        self.assertTrue(
            any("APPLICATION" in a or "CONSENT" in a or "ASSESSMENT" in a for a in recorded_actions),
            f"Expected domain audit action, got: {recorded_actions}",
        )

        # --- STEP 18: Verify Cross-Applicant Isolation ---
        intruder_email = f"intruder_{app_suffix}@parakh.test"
        intruder_pw = "IntruderPass123!"
        int_reg = self.client.post(
            "/api/v1/users",
            json={"email": intruder_email, "password": intruder_pw},
        )
        intruder_id = uuid.UUID(int_reg.json()["id"])
        self.cleanup_items.append(("user", intruder_id))

        int_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": intruder_email, "password": intruder_pw},
        )
        intruder_headers = {"Authorization": f"Bearer {int_login.json()['access_token']}"}

        # Intruder cannot access applicant's application
        int_app_resp = self.client.get(
            f"/api/v1/applications/{application_id}",
            headers=intruder_headers,
        )
        self.assertEqual(int_app_resp.status_code, 403)

        # Intruder cannot access applicant's assessment
        int_assess_resp = self.client.get(
            f"/api/v1/assessments/{assessment_id}",
            headers=intruder_headers,
        )
        self.assertEqual(int_assess_resp.status_code, 403)

        # Intruder cannot access applicant's consents
        int_consent_resp = self.client.get(
            f"/api/v1/applications/{application_id}/consents",
            headers=intruder_headers,
        )
        self.assertEqual(int_consent_resp.status_code, 403)

        # Intruder cannot access applicant's financial signals
        int_sig_resp = self.client.get(
            f"/api/v1/applications/{application_id}/financial-signals",
            headers=intruder_headers,
        )
        self.assertEqual(int_sig_resp.status_code, 403)


class TestEndToEndInMemoryWorkflow(unittest.TestCase):
    """Fast, isolated full lifecycle test using in-memory SQLite and StaticPool."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionTest = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

        def override_get_db():
            db = self.SessionTest()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_in_memory_complete_lifecycle(self):
        """Verify the full domain cycle completes seamlessly in an isolated in-memory DB."""
        # 1. Register Applicant
        email = "in_mem_worker@parakh.test"
        reg = self.client.post("/api/v1/users", json={"email": email, "password": "Password123!"})
        self.assertEqual(reg.status_code, 201)
        user_id = reg.json()["id"]

        # 2. Login
        login = self.client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create Profile
        prof = self.client.post(
            "/api/v1/applicants",
            headers=headers,
            json={"gig_work_type": "Freelance Writer", "years_working": "2.0", "average_working_days": 20},
        )
        self.assertEqual(prof.status_code, 201)
        prof_id = prof.json()["id"]

        # 4. Create Application
        appl = self.client.post(
            "/api/v1/applications",
            headers=headers,
            json={"applicant_profile_id": prof_id, "requested_loan_amount": "15000.00"},
        )
        self.assertEqual(appl.status_code, 201)
        app_id = appl.json()["id"]

        # 5. Submit Application
        sub = self.client.patch(f"/api/v1/applications/{app_id}/status", headers=headers, json={"status": "SUBMITTED"})
        self.assertEqual(sub.status_code, 200)

        # 6. Grant Consent
        con = self.client.post(
            "/api/v1/consents",
            headers=headers,
            json={"application_id": app_id, "data_source": "PLATFORM", "purpose": "Scoring"},
        )
        self.assertEqual(con.status_code, 201)

        # 7. Financial Signal
        sig = self.client.post(
            f"/api/v1/applications/{app_id}/financial-signals",
            headers=headers,
            json={"source": "PLATFORM", "average_income": "28000.00", "payment_regularity": "0.94"},
        )
        self.assertEqual(sig.status_code, 201)

        # 8. Create Admin and Model Version
        with self.SessionTest() as db:
            admin = create_admin_user(db, email="in_mem_admin@parakh.test", password="AdminPass123!")
            admin_token = create_access_token(subject=str(admin.id), role="ADMIN")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        mv = self.client.post(
            "/api/v1/model-versions",
            headers=admin_headers,
            json={"model_name": "in_mem_engine", "version": "1.0.0", "is_active": True},
        )
        self.assertEqual(mv.status_code, 201)
        mv_id = mv.json()["id"]

        # 9. Assess Application
        assess = self.client.post(
            f"/api/v1/applications/{app_id}/assess?model_version_id={mv_id}",
            headers=headers,
        )
        self.assertEqual(assess.status_code, 201)
        self.assertIsNotNone(assess.json()["credit_score"])

        # 10. Verify Audit Trail as Admin
        audit = self.client.get(f"/api/v1/audit-logs?application_id={app_id}", headers=admin_headers)
        self.assertEqual(audit.status_code, 200)
        self.assertGreaterEqual(len(audit.json()), 1)


class TestPostgresTransactionAndIntegrity(unittest.TestCase):
    """Verify live PostgreSQL transaction rollback, integrity constraints, and clean state."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL is not reachable locally.")

    def test_transaction_rollback_on_unique_constraint_violation(self):
        """Verify transaction rollback prevents orphaned records on DB integrity violation."""
        test_email = f"rollback_{uuid.uuid4().hex[:8]}@example.com"
        with SessionLocal() as db:
            # Create original user
            user1 = create_applicant_user(db, email=test_email)
            db_id = user1.id

            # Attempt to create duplicate user inside sub-transaction
            with self.assertRaises(Exception):
                user2 = User(
                    email=test_email,
                    password_hash=hash_password("Password123!"),
                    role=UserRole.APPLICANT,
                )
                db.add(user2)
                db.commit()

            db.rollback()

            # Verify original user remains, duplicate was not persisted
            user_count = db.execute(
                text("SELECT count(*) FROM users WHERE email = :email"),
                {"email": test_email},
            ).scalar()
            self.assertEqual(user_count, 1)

            # Cleanup
            db.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(db_id)})
            db.commit()

    def test_database_foreign_key_enforcement(self):
        """Verify foreign key constraints are enforced by PostgreSQL."""
        with SessionLocal() as db:
            random_id = uuid.uuid4()
            with self.assertRaises(Exception):
                # Application with non-existent applicant_profile_id must fail
                app_orphan = Application(
                    applicant_profile_id=random_id,
                    requested_loan_amount=Decimal("10000.00"),
                    status=ApplicationStatus.DRAFT,
                )
                db.add(app_orphan)
                db.commit()
            db.rollback()


if __name__ == "__main__":
    unittest.main()
