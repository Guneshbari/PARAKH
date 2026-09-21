"""Comprehensive test suite for TASK 12 — Authentication & Roles.

Validates:
1. Password hashing
2. Password verification success
3. Password verification failure
4. Password never stored in plaintext
5. Password hash never exposed in API response
6. Successful login
7. Invalid email/password
8. JWT generation
9. JWT contains required claims
10. JWT validation
11. Expired JWT
12. Invalid JWT
13. Missing Authorization header
14. Current-user dependency
15. Applicant role authorization
16. Reviewer role authorization
17. Admin role authorization
18. Insufficient role returns 403
19. Protected endpoint without authentication returns 401
20. Public endpoints remain accessible
21. Applicant ownership enforcement
22. Cross-applicant access denied
23. Reviewer access to review workflow
24. Admin access to administrative functionality
25. Live PostgreSQL authentication flow
"""
from datetime import timedelta
import time
import unittest
import uuid

from fastapi.testclient import TestClient
import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app
from app.models.user import User, UserRole
from app.repositories.user import UserRepository


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable."""
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


class TestPasswordSecurity(unittest.TestCase):
    """Test password hashing, verification, plaintext safety, and response secrecy."""

    def test_01_password_hashing(self):
        """Verify secure password hashing using bcrypt produces valid salt & hash."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(password, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))

    def test_02_password_verification_success(self):
        """Verify matching plain password validates against hashed string."""
        password = "ValidPassword456$"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))

    def test_03_password_verification_failure(self):
        """Verify invalid or empty password fails verification."""
        hashed = hash_password("ValidPassword456$")
        self.assertFalse(verify_password("WrongPassword!", hashed))
        self.assertFalse(verify_password("", hashed))
        self.assertFalse(verify_password("ValidPassword456$", ""))

    def test_04_password_never_stored_in_plaintext(self):
        """Verify password stored in database is always hashed and plaintext is never persisted."""
        if not can_connect_to_postgres():
            self.skipTest("Live PostgreSQL not available")

        test_email = f"pwd_plain_{uuid.uuid4().hex[:8]}@example.com"
        plain_password = "MySuperSecret123!"
        with SessionLocal() as db:
            user_repo = UserRepository(db=db)
            user = user_repo.create({
                "email": test_email,
                "password_hash": hash_password(plain_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            user_id = str(user.id)

        try:
            with SessionLocal() as db:
                row = db.execute(
                    text("SELECT password_hash FROM users WHERE id = :id"),
                    {"id": user_id},
                ).mappings().one()
                stored_hash = row["password_hash"]
                self.assertNotEqual(stored_hash, plain_password)
                self.assertTrue(verify_password(plain_password, stored_hash))
        finally:
            with SessionLocal() as db:
                raw_uuid = uuid.UUID(user_id)
                db.execute(text("DELETE FROM audit_logs WHERE user_id = :u OR entity_id = :s"), {"u": raw_uuid, "s": user_id})
                db.execute(text("DELETE FROM users WHERE id = :id"), {"id": raw_uuid})
                db.commit()

    def test_05_password_hash_never_exposed_in_api_response(self):
        """Verify API response schemas completely exclude password and password_hash."""
        if not can_connect_to_postgres():
            self.skipTest("Live PostgreSQL not available")

        client = TestClient(app)
        test_email = f"pwd_expose_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/api/v1/users",
            json={"email": test_email, "role": "APPLICANT", "password": "Secret123Password!"},
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        user_id = data["id"]

        try:
            self.assertNotIn("password", data)
            self.assertNotIn("password_hash", data)

            # Test login response secrecy
            login_resp = client.post(
                "/api/v1/auth/login",
                json={"email": test_email, "password": "Secret123Password!"},
            )
            self.assertEqual(login_resp.status_code, 200)
            login_data = login_resp.json()
            self.assertNotIn("password", login_data)
            self.assertNotIn("password_hash", login_data)

            # Test /auth/me response secrecy
            token = login_data["access_token"]
            me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(me_resp.status_code, 200)
            me_data = me_resp.json()
            self.assertNotIn("password", me_data)
            self.assertNotIn("password_hash", me_data)
        finally:
            with SessionLocal() as db:
                raw_uuid = uuid.UUID(user_id)
                db.execute(text("DELETE FROM audit_logs WHERE user_id = :u OR entity_id = :s"), {"u": raw_uuid, "s": user_id})
                db.execute(text("DELETE FROM users WHERE id = :id"), {"id": raw_uuid})
                db.commit()


class TestJwtLifecycle(unittest.TestCase):
    """Test JWT token generation, claims verification, decoding, and expiration behavior."""

    def test_08_jwt_generation(self):
        """Verify create_access_token produces a 3-part signed JWT string."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="APPLICANT")
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

    def test_09_jwt_contains_required_claims(self):
        """Verify generated JWT contains subject, role, expiration, issued-at, and type claims."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="REVIEWER")
        payload = decode_access_token(token)

        self.assertEqual(payload["sub"], user_id)
        self.assertEqual(payload["role"], "REVIEWER")
        self.assertEqual(payload["type"], "access")
        self.assertIn("exp", payload)
        self.assertIn("iat", payload)

    def test_10_jwt_validation(self):
        """Verify decode_access_token successfully validates and returns claims for valid tokens."""
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, role="ADMIN")
        decoded = decode_access_token(token)
        self.assertEqual(decoded["sub"], user_id)
        self.assertEqual(decoded["role"], "ADMIN")

    def test_11_expired_jwt(self):
        """Verify expired JWT triggers ExpiredSignatureError."""
        user_id = str(uuid.uuid4())
        expired_token = create_access_token(
            subject=user_id,
            role="APPLICANT",
            expires_delta=timedelta(seconds=-10),
        )
        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)

    def test_12_invalid_jwt(self):
        """Verify malformed or forged JWT raises PyJWTError."""
        invalid_tokens = [
            "completely.invalid.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
        ]
        for bad_token in invalid_tokens:
            with self.assertRaises(jwt.PyJWTError):
                decode_access_token(bad_token)


class TestAuthenticationEndpoints(unittest.TestCase):
    """Test login, current-user resolution, missing auth headers, and public routes."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL not available")
        cls.client = TestClient(app)

    def setUp(self):
        self.test_suffix = uuid.uuid4().hex[:8]
        self.test_email = f"auth_{self.test_suffix}@example.com"
        self.test_password = "Password123!"
        with SessionLocal() as db:
            user = UserRepository(db=db).create({
                "email": self.test_email,
                "password_hash": hash_password(self.test_password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.user_id = str(user.id)

    def tearDown(self):
        with SessionLocal() as db:
            try:
                raw_uuid = uuid.UUID(self.user_id)
                db.execute(
                    text("DELETE FROM audit_logs WHERE user_id = :uuid_id OR entity_id = :str_id"),
                    {"uuid_id": raw_uuid, "str_id": self.user_id},
                )
                db.execute(
                    text("DELETE FROM audit_logs WHERE metadata->>'attempted_email' = :email OR metadata->>'attempted_email' = 'nonexistent@example.com'"),
                    {"email": self.test_email},
                )
                db.execute(text("DELETE FROM users WHERE id = :id"), {"id": raw_uuid})
                db.commit()
            except Exception:
                db.rollback()

    def test_06_successful_login(self):
        """Verify successful login returns 200 with JWT access token and metadata."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.test_email, "password": self.test_password},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["role"], "APPLICANT")
        self.assertGreater(data["expires_in"], 0)

    def test_07_invalid_email_or_password(self):
        """Verify incorrect email or password returns 401 with generic error."""
        # Wrong password
        resp1 = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.test_email, "password": "WrongPassword123!"},
        )
        self.assertEqual(resp1.status_code, 401)
        self.assertEqual(resp1.json().get("detail"), "Invalid email or password")

        # Non-existent email
        resp2 = self.client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": self.test_password},
        )
        self.assertEqual(resp2.status_code, 401)
        self.assertEqual(resp2.json().get("detail"), "Invalid email or password")

    def test_13_missing_authorization_header(self):
        """Verify calling protected endpoints without Authorization header returns 401."""
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("detail", resp.json())

    def test_14_current_user_dependency(self):
        """Verify get_current_user resolves authenticated identity from JWT token."""
        token = create_access_token(subject=self.user_id, role="APPLICANT")
        resp = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], self.user_id)
        self.assertEqual(data["email"], self.test_email)
        self.assertEqual(data["role"], "APPLICANT")

    def test_20_public_endpoints_remain_accessible(self):
        """Verify system health, status, documentation, and login endpoints are accessible without auth."""
        public_routes = [
            ("/", 200),
            ("/health", 200),
            ("/api/v1/status", 200),
            ("/api/v1/database/health", 200),
            ("/docs", 200),
            ("/openapi.json", 200),
        ]
        for path, expected_status in public_routes:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, expected_status, f"Route {path} failed with {resp.status_code}")


class TestRoleBasedAuthorizationAndOwnership(unittest.TestCase):
    """Test RBAC and ownership isolation for Applicant, Reviewer, and Admin actors."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL not available")
        cls.client = TestClient(app)

    def setUp(self):
        self.test_suffix = uuid.uuid4().hex[:8]
        self.cleanup_items = []

    def tearDown(self):
        with SessionLocal() as db:
            for entity_type, entity_id in reversed(self.cleanup_items):
                try:
                    raw_uuid = entity_id if isinstance(entity_id, uuid.UUID) else uuid.UUID(str(entity_id))
                    db.execute(
                        text("DELETE FROM audit_logs WHERE entity_id = :str_id OR application_id = :uuid_id OR user_id = :uuid_id"),
                        {"str_id": str(raw_uuid), "uuid_id": raw_uuid},
                    )
                    if entity_type == "review":
                        db.execute(text("DELETE FROM review_outcomes WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "assessment":
                        db.execute(text("DELETE FROM credit_assessments WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "financial_signal":
                        db.execute(text("DELETE FROM financial_signals WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "consent":
                        db.execute(text("DELETE FROM consents WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "application":
                        db.execute(text("DELETE FROM applications WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "applicant":
                        db.execute(text("DELETE FROM applicant_profiles WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "model_version":
                        db.execute(text("DELETE FROM model_versions WHERE id = :id"), {"id": raw_uuid})
                    elif entity_type == "user":
                        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": raw_uuid})
                    db.commit()
                except Exception:
                    db.rollback()
            try:
                db.execute(text("DELETE FROM audit_logs WHERE entity_type = 'Security'"))
                db.commit()
            except Exception:
                db.rollback()

    def create_user_with_role(self, role: str) -> tuple:
        email = f"user_{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
        with SessionLocal() as db:
            user = UserRepository(db=db).create({
                "email": email,
                "password_hash": hash_password("Password123!"),
                "role": UserRole(role),
                "is_active": True,
            }, commit=True)
            user_id = str(user.id)
        self.cleanup_items.append(("user", user_id))
        token = create_access_token(subject=user_id, role=role)
        headers = {"Authorization": f"Bearer {token}"}
        return user_id, headers

    def test_15_applicant_role_authorization(self):
        """Applicant can manage their own profile and submit credit application."""
        user_id, headers = self.create_user_with_role("APPLICANT")

        # Create profile
        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Ride Hailing", "tenure_months": 12},
            headers=headers,
        )
        self.assertEqual(p_resp.status_code, 201)
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        # Submit application
        a_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 25000.0},
            headers=headers,
        )
        self.assertEqual(a_resp.status_code, 201)
        app_id = a_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

    def test_16_reviewer_role_authorization(self):
        """Reviewer can access applications and submit review outcomes."""
        # Setup applicant and application
        app_user_id, app_headers = self.create_user_with_role("APPLICANT")
        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": app_user_id, "gig_work_type": "Delivery"},
            headers=app_headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        a_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 10000.0},
            headers=app_headers,
        )
        app_id = a_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Reviewer actor
        rev_id, rev_headers = self.create_user_with_role("REVIEWER")

        # Reviewer can view the application
        get_app = self.client.get(f"/api/v1/applications/{app_id}", headers=rev_headers)
        self.assertEqual(get_app.status_code, 200)

        # Reviewer can submit a review
        rev_resp = self.client.post(
            f"/api/v1/applications/{app_id}/reviews",
            json={
                "application_id": app_id,
                "reviewer_id": rev_id,
                "outcome": "REVIEWED",
                "notes": "Verified gig delivery earnings history.",
            },
            headers=rev_headers,
        )
        self.assertEqual(rev_resp.status_code, 201)
        self.cleanup_items.append(("review", rev_resp.json()["id"]))

    def test_17_admin_role_authorization(self):
        """Admin has operational privileges including registering model versions."""
        admin_id, admin_headers = self.create_user_with_role("ADMIN")

        mv_version = f"admin_test_{uuid.uuid4().hex[:6]}"
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            json={
                "model_name": "mock_rules_v1",
                "version": mv_version,
                "description": "Admin created model version",
                "is_active": True,
            },
            headers=admin_headers,
        )
        self.assertEqual(mv_resp.status_code, 201)
        self.cleanup_items.append(("model_version", mv_resp.json()["id"]))

    def test_18_insufficient_role_returns_403(self):
        """Verify user with insufficient role receives 403 Forbidden."""
        applicant_id, applicant_headers = self.create_user_with_role("APPLICANT")

        # Applicant attempts to register a model version (Admin only) -> 403
        resp = self.client.post(
            "/api/v1/model-versions",
            json={
                "model_name": "mock_rules_v1",
                "version": "illegal_ver",
                "description": "Applicant attempting admin action",
            },
            headers=applicant_headers,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Required role: ADMIN", resp.json().get("detail", ""))

    def test_19_protected_endpoint_without_authentication_returns_401(self):
        """Verify accessing protected routes without authentication returns 401."""
        endpoints = [
            ("GET", "/api/v1/users/by-email/test@example.com"),
            ("GET", f"/api/v1/applicants/{uuid.uuid4()}"),
            ("POST", "/api/v1/applications"),
            ("POST", "/api/v1/consents"),
            ("GET", f"/api/v1/applications/{uuid.uuid4()}/financial-signals"),
            ("POST", f"/api/v1/applications/{uuid.uuid4()}/assess"),
            ("POST", "/api/v1/model-versions"),
            ("POST", f"/api/v1/applications/{uuid.uuid4()}/reviews"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = self.client.get(path)
            else:
                resp = self.client.post(path, json={})
            self.assertEqual(resp.status_code, 401, f"Expected 401 for {method} {path}, got {resp.status_code}")

    def test_21_applicant_ownership_enforcement(self):
        """Applicant can retrieve and update their own application."""
        user_id, headers = self.create_user_with_role("APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Freelance"},
            headers=headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        a_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 15000.0},
            headers=headers,
        )
        app_id = a_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Access own application -> 200
        get_app = self.client.get(f"/api/v1/applications/{app_id}", headers=headers)
        self.assertEqual(get_app.status_code, 200)
        self.assertEqual(get_app.json()["id"], app_id)

    def test_22_cross_applicant_access_denied(self):
        """Applicant A cannot access Applicant B's application or profile."""
        # Create Applicant A
        user_a_id, headers_a = self.create_user_with_role("APPLICANT")
        p_a = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_a_id, "gig_work_type": "Logistics"},
            headers=headers_a,
        )
        prof_a_id = p_a.json()["id"]
        self.cleanup_items.append(("applicant", prof_a_id))

        # Create Applicant B
        user_b_id, headers_b = self.create_user_with_role("APPLICANT")
        p_b = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_b_id, "gig_work_type": "Ride Hailing"},
            headers=headers_b,
        )
        prof_b_id = p_b.json()["id"]
        self.cleanup_items.append(("applicant", prof_b_id))

        app_b = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_b_id, "requested_loan_amount": 30000.0},
            headers=headers_b,
        )
        app_b_id = app_b.json()["id"]
        self.cleanup_items.append(("application", app_b_id))

        # Applicant A tries to GET Applicant B's profile -> 403
        resp_prof = self.client.get(f"/api/v1/applicants/{prof_b_id}", headers=headers_a)
        self.assertEqual(resp_prof.status_code, 403)
        self.assertIn("Access denied", resp_prof.json().get("detail", ""))

        # Applicant A tries to GET Applicant B's application -> 403
        resp_app = self.client.get(f"/api/v1/applications/{app_b_id}", headers=headers_a)
        self.assertEqual(resp_app.status_code, 403)
        self.assertIn("Access denied", resp_app.json().get("detail", ""))

        # Applicant A tries to PATCH Applicant B's application -> 403
        patch_app = self.client.patch(
            f"/api/v1/applications/{app_b_id}",
            json={"requested_loan_amount": 1000.0},
            headers=headers_a,
        )
        self.assertEqual(patch_app.status_code, 403)

    def test_23_reviewer_access_to_review_workflow(self):
        """Reviewer can view reviews, but cannot view other reviewers' personal review history."""
        # Setup application
        app_user_id, app_headers = self.create_user_with_role("APPLICANT")
        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": app_user_id, "gig_work_type": "Freelancer"},
            headers=app_headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        app_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 12000.0},
            headers=app_headers,
        )
        app_id = app_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Reviewer 1
        rev1_id, rev1_headers = self.create_user_with_role("REVIEWER")
        # Reviewer 2
        rev2_id, rev2_headers = self.create_user_with_role("REVIEWER")

        # Reviewer 1 submits review
        rev_resp = self.client.post(
            f"/api/v1/applications/{app_id}/reviews",
            json={
                "application_id": app_id,
                "reviewer_id": rev1_id,
                "outcome": "REVIEWED",
                "notes": "Reviewer 1 evaluation.",
            },
            headers=rev1_headers,
        )
        self.assertEqual(rev_resp.status_code, 201)
        self.cleanup_items.append(("review", rev_resp.json()["id"]))

        # Reviewer 1 can view their own reviews -> 200
        own_revs = self.client.get(f"/api/v1/reviewers/{rev1_id}/reviews", headers=rev1_headers)
        self.assertEqual(own_revs.status_code, 200)

        # Reviewer 2 tries to view Reviewer 1's reviews -> 403
        other_revs = self.client.get(f"/api/v1/reviewers/{rev1_id}/reviews", headers=rev2_headers)
        self.assertEqual(other_revs.status_code, 403)
        self.assertIn("Access denied", other_revs.json().get("detail", ""))

    def test_24_admin_access_to_administrative_functionality(self):
        """Admin can list and view all applications, model versions, and reviewer queues."""
        admin_id, admin_headers = self.create_user_with_role("ADMIN")
        rev_id, rev_headers = self.create_user_with_role("REVIEWER")

        # Admin can view reviewer 1's queue
        rev_list = self.client.get(f"/api/v1/reviewers/{rev_id}/reviews", headers=admin_headers)
        self.assertEqual(rev_list.status_code, 200)

        # Admin can list all model versions
        mv_list = self.client.get("/api/v1/model-versions", headers=admin_headers)
        self.assertEqual(mv_list.status_code, 200)

    def test_25_live_postgresql_authentication_flow(self):
        """Complete live PostgreSQL authentication flow: registration -> login -> JWT -> auth/me -> cleanup."""
        email = f"live_flow_{uuid.uuid4().hex[:8]}@example.com"
        password = "LiveFlowPassword123!"

        # 1. Register user
        reg_resp = self.client.post(
            "/api/v1/users",
            json={"email": email, "password": password, "role": "APPLICANT"},
        )
        self.assertEqual(reg_resp.status_code, 201)
        user_id = reg_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))

        # 2. Login
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Access current user
        me_resp = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], email)
        self.assertEqual(me_resp.json()["id"], user_id)

        # 4. Create profile and application
        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Courier", "tenure_months": 15},
            headers=headers,
        )
        self.assertEqual(p_resp.status_code, 201)
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        a_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 20000.0},
            headers=headers,
        )
        self.assertEqual(a_resp.status_code, 201)
        app_id = a_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # 5. Direct DB verification of user password_hash
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT password_hash, role FROM users WHERE id = :id"),
                {"id": user_id},
            ).mappings().one()
            self.assertTrue(verify_password(password, row["password_hash"]))
            self.assertEqual(row["role"], "APPLICANT")


if __name__ == "__main__":
    unittest.main()
