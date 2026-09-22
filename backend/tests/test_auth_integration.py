"""Integration test suite for PARAKH Authentication & RBAC (Phase 4).

Validates:
1. Valid login with APPLICANT credentials -> returns JWT, user metadata, correct role.
2. Login with invalid password -> 401 Unauthorized.
3. Login with nonexistent user -> 401 Unauthorized.
4. Login with inactive user -> 403 Forbidden.
5. GET /api/v1/auth/me with valid Bearer token -> returns caller profile.
6. GET /api/v1/auth/me without token -> 401 Unauthorized.
7. GET /api/v1/auth/me with invalid token -> 401 Unauthorized.
8. GET /api/v1/auth/me with expired token -> 401 Unauthorized.
9. APPLICANT role authorization: can access own applications, cannot access reviewer/admin endpoints.
10. REVIEWER role authorization: can access applications, can record review actions, cannot access admin-only endpoints.
11. ADMIN role authorization: full access to administrative endpoints (audit logs, model versions).
12. Self-registration via POST /api/v1/users -> immediate login flow.
"""
from datetime import timedelta
from typing import Generator
import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    Consent,
    CreditAssessment,
    FinancialSignal,
    ModelVersion,
    ReviewOutcome,
    ReviewOutcomeType,
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)
from app.repositories.user import UserRepository


class TestAuthIntegration(unittest.TestCase):
    """Integration test suite for FastAPI JWT authentication and RBAC."""

    def setUp(self):
        """Set up an isolated in-memory SQLite database and test client."""
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

        # Seed initial test accounts
        self.applicant_password = "Password123!"
        self.reviewer_password = "Password123!"
        self.admin_password = "Password123!"

        with self.SessionFactory() as db:
            user_repo = UserRepository(db=db)

            # 1. Applicant
            self.applicant = user_repo.create({
                "email": "applicant@example.com",
                "password_hash": hash_password(self.applicant_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.applicant_id = str(self.applicant.id)

            # 2. Reviewer
            self.reviewer = user_repo.create({
                "email": "reviewer@example.com",
                "password_hash": hash_password(self.reviewer_password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.reviewer_id = str(self.reviewer.id)

            # 3. Admin
            self.admin = user_repo.create({
                "email": "admin@example.com",
                "password_hash": hash_password(self.admin_password),
                "role": UserRole.ADMIN,
                "is_active": True,
            }, commit=True)
            self.admin_id = str(self.admin.id)

            # 4. Inactive User
            self.inactive = user_repo.create({
                "email": "inactive@example.com",
                "password_hash": hash_password("Password123!"),
                "role": UserRole.APPLICANT,
                "is_active": False,
            }, commit=True)
            self.inactive_id = str(self.inactive.id)

    def tearDown(self):
        """Clean up dependency overrides and drop tables."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    # --- 1. LOGIN TESTS ---

    def test_01_valid_login_applicant(self):
        """Verify successful login returns valid JWT and APPLICANT metadata."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "applicant@example.com", "password": self.applicant_password},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertGreater(data["expires_in"], 0)
        self.assertEqual(data["user_id"], self.applicant_id)
        self.assertEqual(data["email"], "applicant@example.com")
        self.assertEqual(data["role"], "APPLICANT")

    def test_02_valid_login_reviewer(self):
        """Verify successful login returns valid JWT and REVIEWER metadata."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer@example.com", "password": self.reviewer_password},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["role"], "REVIEWER")
        self.assertEqual(data["user_id"], self.reviewer_id)

    def test_03_login_invalid_password(self):
        """Verify login with incorrect password returns 401 Unauthorized."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "applicant@example.com", "password": "WrongPassword!"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid email or password", resp.json()["detail"])

    def test_04_login_nonexistent_user(self):
        """Verify login with unregistered email returns 401 Unauthorized."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_05_login_inactive_user(self):
        """Verify login for inactive account returns 403 Forbidden."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("inactive", resp.json()["detail"].lower())

    # --- 2. CURRENT USER (GET /auth/me) TESTS ---

    def test_06_get_current_user_valid_token(self):
        """Verify GET /auth/me resolves current authenticated user identity."""
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "applicant@example.com", "password": self.applicant_password},
        )
        token = login_resp.json()["access_token"]

        me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        user_data = me_resp.json()
        self.assertEqual(user_data["id"], self.applicant_id)
        self.assertEqual(user_data["email"], "applicant@example.com")
        self.assertEqual(user_data["role"], "APPLICANT")
        self.assertTrue(user_data["is_active"])

    def test_07_get_current_user_missing_token(self):
        """Verify GET /auth/me without Authorization header returns 401 Unauthorized."""
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 401)

    def test_08_get_current_user_invalid_token(self):
        """Verify GET /auth/me with corrupted token returns 401 Unauthorized."""
        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_09_get_current_user_expired_token(self):
        """Verify GET /auth/me with expired token returns 401 Unauthorized."""
        expired_token = create_access_token(
            subject=self.applicant_id,
            role="APPLICANT",
            expires_delta=timedelta(seconds=-60),
        )
        resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired", resp.json()["detail"].lower())

    # --- 3. RBAC & PROTECTED APPLICATION ENDPOINTS ---

    def test_10_applicant_rbac_permissions(self):
        """Verify APPLICANT can access own profile but cannot access reviewer/admin endpoints."""
        token = create_access_token(subject=self.applicant_id, role="APPLICANT")
        headers = {"Authorization": f"Bearer {token}"}

        # APPLICANT can view own user account
        own_resp = self.client.get(f"/api/v1/users/{self.applicant_id}", headers=headers)
        self.assertEqual(own_resp.status_code, 200)

        # APPLICANT cannot view other user's account -> 403 Forbidden
        other_resp = self.client.get(f"/api/v1/users/{self.reviewer_id}", headers=headers)
        self.assertEqual(other_resp.status_code, 403)

        # Listing all applications requires REVIEWER or ADMIN -> APPLICANT receives 403 Forbidden
        app_resp = self.client.get("/api/v1/applications", headers=headers)
        self.assertEqual(app_resp.status_code, 403)

        # Audit endpoint requires ADMIN role -> 403 Forbidden
        audit_resp = self.client.get("/api/v1/audit-logs", headers=headers)
        self.assertEqual(audit_resp.status_code, 403)

        # Model version creation requires ADMIN role -> 403 Forbidden
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            headers=headers,
            json={"model_name": "CreditScorer", "version": "v1.0", "description": "Test", "is_active": True},
        )
        self.assertEqual(mv_resp.status_code, 403)

    def test_11_reviewer_rbac_permissions(self):
        """Verify REVIEWER can access applications queue but cannot access admin-only endpoints."""
        token = create_access_token(subject=self.reviewer_id, role="REVIEWER")
        headers = {"Authorization": f"Bearer {token}"}

        # Applications endpoint is accessible to REVIEWER
        app_resp = self.client.get("/api/v1/applications", headers=headers)
        self.assertEqual(app_resp.status_code, 200)

        # Admin audit log endpoint is blocked for REVIEWER -> 403 Forbidden
        audit_resp = self.client.get("/api/v1/audit-logs", headers=headers)
        self.assertEqual(audit_resp.status_code, 403)

        # Model version creation requires ADMIN role -> 403 Forbidden
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            headers=headers,
            json={"model_name": "CreditScorer", "version": "v1.0", "description": "Test", "is_active": True},
        )
        self.assertEqual(mv_resp.status_code, 403)

    def test_12_admin_rbac_permissions(self):
        """Verify ADMIN can access administrative endpoints."""
        token = create_access_token(subject=self.admin_id, role="ADMIN")
        headers = {"Authorization": f"Bearer {token}"}

        # Audit logs accessible to ADMIN
        audit_resp = self.client.get("/api/v1/audit-logs", headers=headers)
        self.assertEqual(audit_resp.status_code, 200)

        # Applications accessible to ADMIN
        app_resp = self.client.get("/api/v1/applications", headers=headers)
        self.assertEqual(app_resp.status_code, 200)

        # Model version creation accessible to ADMIN
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            headers=headers,
            json={"model_name": "CreditScorer", "version": "v_admin_test", "description": "Admin created", "is_active": True},
        )
        self.assertEqual(mv_resp.status_code, 201)

    # --- 4. SIGNUP & FLOW VERIFICATION ---

    def test_13_self_registration_flow(self):
        """Verify self-registration via POST /api/v1/users followed by login."""
        new_email = "new_gig_worker@example.com"
        new_password = "SecurePassword123!"

        reg_resp = self.client.post(
            "/api/v1/users",
            json={"email": new_email, "password": new_password, "role": "APPLICANT"},
        )
        self.assertEqual(reg_resp.status_code, 201)
        reg_data = reg_resp.json()
        self.assertEqual(reg_data["email"], new_email)
        self.assertEqual(reg_data["role"], "APPLICANT")
        self.assertNotIn("password", reg_data)
        self.assertNotIn("password_hash", reg_data)

        # Immediate login with newly registered credentials
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": new_email, "password": new_password},
        )
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]

        # Call /api/v1/auth/me with new token
        me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], new_email)


if __name__ == "__main__":
    unittest.main()
