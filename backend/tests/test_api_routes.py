"""Integration and unit tests for PARAKH FastAPI API routes."""
import uuid
import unittest
from decimal import Decimal
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.user import UserRole
from app.models.application import ApplicationStatus
from app.models.consent import ConsentDataSource
from app.models.review import ReviewOutcomeType
from app.assessment.mock import MockAssessmentEngine
from app.api.deps import get_assessment_engine


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


class TestApiHealthAndSystemRoutes(unittest.TestCase):
    """Test health, status, database connectivity, and OpenAPI documentation endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """GET / returns 200 and running message."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)

    def test_health_endpoint(self):
        """GET /health returns 200 and healthy status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_v1_status_endpoint(self):
        """GET /api/v1/status returns 200 and ok status."""
        response = self.client.get("/api/v1/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    @unittest.skipUnless(can_connect_to_postgres(), "Live PostgreSQL is not available.")
    def test_database_health_endpoint(self):
        """GET /api/v1/database/health returns 200 and database connected."""
        response = self.client.get("/api/v1/database/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("database"), "connected")

    def test_docs_endpoint(self):
        """GET /docs returns 200 OpenAPI Swagger UI."""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)


class TestApiRoutesWithLivePostgres(unittest.TestCase):
    """Comprehensive test suite testing all API routers against live PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        if not can_connect_to_postgres():
            raise unittest.SkipTest("Live PostgreSQL is not available.")
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "db") and cls.db:
            cls.db.close()

    def setUp(self):
        self.test_suffix = uuid.uuid4().hex[:8]
        self.cleanup_items = []

    def get_auth_header(self, user_id: str, role: str = "APPLICANT") -> dict:
        from app.core.security import create_access_token
        token = create_access_token(subject=str(user_id), role=str(role))
        return {"Authorization": f"Bearer {token}"}

    def create_user_and_headers(self, role: str = "APPLICANT", email: str = None) -> tuple:
        from app.repositories.user import UserRepository
        from app.core.security import hash_password
        if not email:
            email = f"u_{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
        with SessionLocal() as db:
            user = UserRepository(db=db).create({
                "email": email,
                "password_hash": hash_password("Password123!"),
                "role": UserRole(role),
                "is_active": True,
            }, commit=True)
            user_id = str(user.id)
        self.cleanup_items.append(("user", user_id))
        return user_id, self.get_auth_header(user_id, role)

    def tearDown(self):
        # Clean up created resources in reverse order directly via db session
        with SessionLocal() as db:
            for entity_type, entity_id in reversed(self.cleanup_items):
                try:
                    if entity_type == "review":
                        db.execute(text("DELETE FROM review_outcomes WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "assessment":
                        db.execute(text("DELETE FROM credit_assessments WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "financial_signal":
                        db.execute(text("DELETE FROM financial_signals WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "consent":
                        db.execute(text("DELETE FROM consents WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "application":
                        db.execute(text("DELETE FROM applications WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "applicant":
                        db.execute(text("DELETE FROM applicant_profiles WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "model_version":
                        db.execute(text("DELETE FROM model_versions WHERE id = :id"), {"id": str(entity_id)})
                    elif entity_type == "user":
                        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(entity_id)})
                    db.commit()
                except Exception:
                    db.rollback()

    # --- 1. USER ROUTES ---
    def test_user_crud_and_privacy(self):
        """Test user creation, retrieval by id/email, update, and password privacy."""
        email = f"user_{self.test_suffix}@example.com"
        resp = self.client.post(
            "/api/v1/users",
            json={
                "email": email,
                "role": "APPLICANT",
                "password": "SecretPassword123!",
            },
        )
        self.assertEqual(resp.status_code, 201)
        user_data = resp.json()
        user_id = user_data["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        # Verification: password and password_hash must NOT be in response
        self.assertNotIn("password", user_data)
        self.assertNotIn("password_hash", user_data)
        self.assertEqual(user_data["email"], email)
        self.assertEqual(user_data["role"], "APPLICANT")

        # GET by ID
        get_resp = self.client.get(f"/api/v1/users/{user_id}", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], user_id)
        self.assertNotIn("password", get_resp.json())
        self.assertNotIn("password_hash", get_resp.json())

        # GET by email
        email_resp = self.client.get(f"/api/v1/users/by-email/{email}", headers=headers)
        self.assertEqual(email_resp.status_code, 200)
        self.assertEqual(email_resp.json()["id"], user_id)

        # PATCH user
        patch_resp = self.client.patch(
            f"/api/v1/users/{user_id}",
            json={"is_active": False},
            headers=headers,
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertFalse(patch_resp.json()["is_active"])

        # Duplicate email conflict -> 409
        dup_resp = self.client.post(
            "/api/v1/users",
            json={"email": email, "role": "APPLICANT", "password": "Password123!"},
        )
        self.assertEqual(dup_resp.status_code, 409)

        # Non-existent user -> 404 (with admin headers)
        admin_id, admin_headers = self.create_user_and_headers(role="ADMIN")
        nf_resp = self.client.get(f"/api/v1/users/{uuid.uuid4()}", headers=admin_headers)
        self.assertEqual(nf_resp.status_code, 404)


    # --- 2. APPLICANT ROUTES ---
    def test_applicant_crud_and_validations(self):
        """Test applicant profile creation, lookup, update, and duplicate prevention."""
        email = f"app_user_{self.test_suffix}@example.com"
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": email, "role": "APPLICANT", "password": "Password123!"},
        )
        user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        # Create profile
        p_resp = self.client.post(
            "/api/v1/applicants",
            json={
                "user_id": user_id,
                "first_name": "Rohan",
                "last_name": "Sharma",
                "gig_work_type": "Ride Hailing",
                "primary_platform": "Uber",
                "tenure_months": 24,
            },
            headers=headers,
        )
        self.assertEqual(p_resp.status_code, 201)
        prof_data = p_resp.json()
        prof_id = prof_data["id"]
        self.cleanup_items.append(("applicant", prof_id))
        self.assertEqual(prof_data["user_id"], user_id)
        self.assertEqual(prof_data["gig_work_type"], "Ride Hailing")

        # GET by ID
        get_p = self.client.get(f"/api/v1/applicants/{prof_id}", headers=headers)
        self.assertEqual(get_p.status_code, 200)
        self.assertEqual(get_p.json()["id"], prof_id)

        # GET by user_id
        get_u = self.client.get(f"/api/v1/applicants/user/{user_id}", headers=headers)
        self.assertEqual(get_u.status_code, 200)
        self.assertEqual(get_u.json()["id"], prof_id)

        # PATCH profile
        patch_p = self.client.patch(
            f"/api/v1/applicants/{prof_id}",
            json={"years_working": 3.0},
            headers=headers,
        )
        self.assertEqual(patch_p.status_code, 200)
        self.assertEqual(float(patch_p.json()["years_working"]), 3.0)

        # Duplicate profile for same user -> 409
        dup_p = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Food Delivery"},
            headers=headers,
        )
        self.assertEqual(dup_p.status_code, 409)

        # Profile for nonexistent user -> 404 (with admin headers)
        admin_id, admin_headers = self.create_user_and_headers(role="ADMIN")
        nf_user_p = self.client.post(
            "/api/v1/applicants",
            json={"user_id": str(uuid.uuid4()), "gig_work_type": "Courier"},
            headers=admin_headers,
        )
        self.assertEqual(nf_user_p.status_code, 404)

    # --- 3. APPLICATION ROUTES & STATUS TRANSITIONS ---
    def test_application_lifecycle_and_state_transitions(self):
        """Test application creation, retrieval, updates, and status state machine."""
        # Setup user + applicant
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": f"appl_{self.test_suffix}@example.com", "role": "APPLICANT", "password": "Password123!"},
        )
        user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Quick Commerce"},
            headers=headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        # Create application
        app_resp = self.client.post(
            "/api/v1/applications",
            json={
                "applicant_profile_id": prof_id,
                "requested_loan_amount": 35000.0,
                "loan_purpose": "Vehicle Battery Upgrade",
            },
            headers=headers,
        )
        self.assertEqual(app_resp.status_code, 201)
        app_data = app_resp.json()
        app_id = app_data["id"]
        self.cleanup_items.append(("application", app_id))
        self.assertEqual(app_data["status"], "DRAFT")

        # GET application
        get_app = self.client.get(f"/api/v1/applications/{app_id}", headers=headers)
        self.assertEqual(get_app.status_code, 200)
        self.assertEqual(get_app.json()["id"], app_id)

        # List by applicant
        list_app = self.client.get(f"/api/v1/applications/applicant/{prof_id}", headers=headers)
        self.assertEqual(list_app.status_code, 200)
        self.assertIsInstance(list_app.json(), list)
        self.assertTrue(any(a["id"] == app_id for a in list_app.json()))

        # PATCH application details
        patch_app = self.client.patch(
            f"/api/v1/applications/{app_id}",
            json={"loan_purpose": "Vehicle Motor Servicing"},
            headers=headers,
        )
        self.assertEqual(patch_app.status_code, 200)
        self.assertEqual(patch_app.json()["loan_purpose"], "Vehicle Motor Servicing")

        # Valid status transition: DRAFT -> SUBMITTED (applicant)
        st_resp = self.client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "SUBMITTED"},
            headers=headers,
        )
        self.assertEqual(st_resp.status_code, 200)
        self.assertEqual(st_resp.json()["status"], "SUBMITTED")

        # Valid transition: SUBMITTED -> UNDER_REVIEW (reviewer / admin)
        admin_id, admin_headers = self.create_user_and_headers(role="ADMIN")
        st_resp2 = self.client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "UNDER_REVIEW"},
            headers=admin_headers,
        )
        self.assertEqual(st_resp2.status_code, 200)
        self.assertEqual(st_resp2.json()["status"], "UNDER_REVIEW")

        # Valid transition: UNDER_REVIEW -> ASSESSED (reviewer / admin)
        st_resp3 = self.client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "ASSESSED"},
            headers=admin_headers,
        )
        self.assertEqual(st_resp3.status_code, 200)
        self.assertEqual(st_resp3.json()["status"], "ASSESSED")

        # Invalid transition: ASSESSED -> DRAFT (should raise InvalidStateTransitionError -> 409)
        invalid_st = self.client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "DRAFT"},
            headers=admin_headers,
        )
        self.assertEqual(invalid_st.status_code, 409)

    # --- 4. CONSENT ROUTES ---
    def test_consent_routes_and_revocation(self):
        """Test consent creation, listing, active filtering, and revocation."""
        # Setup
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": f"consent_{self.test_suffix}@example.com", "role": "APPLICANT", "password": "Password123!"},
        )
        user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Freelance"},
            headers=headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        app_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 10000.0},
            headers=headers,
        )
        app_id = app_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Create consent
        c_resp = self.client.post(
            "/api/v1/consents",
            json={
                "application_id": app_id,
                "applicant_profile_id": prof_id,
                "data_source": "PLATFORM",
                "purpose": "CREDIT_ASSESSMENT",
                "granted": True,
            },
            headers=headers,
        )
        self.assertEqual(c_resp.status_code, 201)
        consent_data = c_resp.json()
        consent_id = consent_data["id"]
        self.cleanup_items.append(("consent", consent_id))
        self.assertTrue(consent_data["granted"])
        self.assertIsNone(consent_data["revoked_at"])

        # Reject invalid consent (granted=False) -> 400
        inv_c = self.client.post(
            "/api/v1/consents",
            json={
                "application_id": app_id,
                "applicant_profile_id": prof_id,
                "data_source": "PLATFORM",
                "purpose": "CREDIT_ASSESSMENT",
                "granted": False,
            },
            headers=headers,
        )
        self.assertEqual(inv_c.status_code, 400)

        # GET application consents
        all_c = self.client.get(f"/api/v1/applications/{app_id}/consents", headers=headers)
        self.assertEqual(all_c.status_code, 200)
        self.assertEqual(len(all_c.json()), 1)

        # GET active consents
        act_c = self.client.get(f"/api/v1/applications/{app_id}/consents/active", headers=headers)
        self.assertEqual(act_c.status_code, 200)
        self.assertEqual(len(act_c.json()), 1)

        # Revoke consent
        rev_resp = self.client.post(f"/api/v1/consents/{consent_id}/revoke", headers=headers)
        self.assertEqual(rev_resp.status_code, 200)
        self.assertIsNotNone(rev_resp.json()["revoked_at"])

        # Active consents list should now be empty
        act_c_after = self.client.get(f"/api/v1/applications/{app_id}/consents/active", headers=headers)
        self.assertEqual(act_c_after.status_code, 200)
        self.assertEqual(len(act_c_after.json()), 0)

    # --- 5. FINANCIAL SIGNAL ROUTES & PRIVACY ---
    def test_financial_signals_and_privacy_rejection(self):
        """Test financial signal creation, listing, retrieval, privacy rejection, and consent gating."""
        # Setup
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": f"signal_{self.test_suffix}@example.com", "role": "APPLICANT", "password": "Password123!"},
        )
        user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Delivery"},
            headers=headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        app_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 20000.0},
            headers=headers,
        )
        app_id = app_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Attempt to create signal when require_consent=True but no consent exists -> 403
        no_consent_resp = self.client.post(
            f"/api/v1/applications/{app_id}/financial-signals?require_consent=true",
            json={
                "source": "PLATFORM",
                "average_income": 30000.0,
                "cashflow_buffer": 15000.0,
            },
            headers=headers,
        )
        self.assertEqual(no_consent_resp.status_code, 403)

        # Grant consent
        c_resp = self.client.post(
            "/api/v1/consents",
            json={
                "application_id": app_id,
                "applicant_profile_id": prof_id,
                "data_source": "PLATFORM",
                "purpose": "CREDIT_ASSESSMENT",
                "granted": True,
            },
            headers=headers,
        )
        self.cleanup_items.append(("consent", c_resp.json()["id"]))

        # Privacy rejection: prohibited raw data in extra payload -> 400
        prohibited_resp = self.client.post(
            f"/api/v1/applications/{app_id}/financial-signals",
            json={
                "source": "PLATFORM",
                "average_income": 30000.0,
                "raw_transactions": [{"txn_id": "123", "amount": 100}],
            },
            headers=headers,
        )
        self.assertEqual(prohibited_resp.status_code, 400)

        # Valid financial signal creation
        sig_resp = self.client.post(
            f"/api/v1/applications/{app_id}/financial-signals?require_consent=true",
            json={
                "source": "PLATFORM",
                "average_income": 32000.0,
                "cashflow_buffer": 18000.0,
                "income_volatility": 0.12,
                "payment_regularity": 0.95,
                "repayment_reliability": 0.90,
            },
            headers=headers,
        )
        self.assertEqual(sig_resp.status_code, 201)
        sig_data = sig_resp.json()
        sig_id = sig_data["id"]
        self.cleanup_items.append(("financial_signal", sig_id))
        self.assertEqual(float(sig_data["average_income"]), 32000.0)

        # GET signals
        list_sig = self.client.get(f"/api/v1/applications/{app_id}/financial-signals", headers=headers)
        self.assertEqual(list_sig.status_code, 200)
        self.assertEqual(len(list_sig.json()), 1)

        # GET latest signal
        latest_sig = self.client.get(f"/api/v1/applications/{app_id}/financial-signals/latest", headers=headers)
        self.assertEqual(latest_sig.status_code, 200)
        self.assertEqual(latest_sig.json()["id"], sig_id)

    # --- 6. MODEL VERSION ROUTES ---
    def test_model_version_routes(self):
        """Test model version registration, retrieval, listing, and active lookup."""
        admin_id, admin_headers = self.create_user_and_headers(role="ADMIN")
        mv_version = f"1.0.{self.test_suffix}"
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            json={
                "model_name": "mock_rules_v1",
                "version": mv_version,
                "description": "Deterministic mock scoring rules engine",
                "is_active": True,
            },
            headers=admin_headers,
        )
        self.assertEqual(mv_resp.status_code, 201)
        mv_data = mv_resp.json()
        mv_id = mv_data["id"]
        self.cleanup_items.append(("model_version", mv_id))
        self.assertEqual(mv_data["version"], mv_version)
        self.assertTrue(mv_data["is_active"])

        # GET by ID
        get_mv = self.client.get(f"/api/v1/model-versions/{mv_id}", headers=admin_headers)
        self.assertEqual(get_mv.status_code, 200)
        self.assertEqual(get_mv.json()["id"], mv_id)

        # List model versions
        list_mv = self.client.get("/api/v1/model-versions", headers=admin_headers)
        self.assertEqual(list_mv.status_code, 200)
        self.assertTrue(any(m["id"] == mv_id for m in list_mv.json()))

        # GET active by model name
        act_mv = self.client.get("/api/v1/model-versions/active/mock_rules_v1", headers=admin_headers)
        self.assertEqual(act_mv.status_code, 200)
        self.assertEqual(act_mv.json()["model_name"], "mock_rules_v1")

    # --- 7. ASSESSMENT EXECUTION AND RETRIEVAL ROUTES ---
    def test_assessment_flow_and_mock_engine(self):
        """Test assessment execution via MockAssessmentEngine, persistence, and output safety."""
        # Setup User -> Applicant -> Application -> Consent -> Financial Signal -> Model Version
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": f"assess_{self.test_suffix}@example.com", "role": "APPLICANT", "password": "Password123!"},
        )
        user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", user_id))
        headers = self.get_auth_header(user_id, "APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": user_id, "gig_work_type": "Ride Hailing", "tenure_months": 24},
            headers=headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        app_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 25000.0},
            headers=headers,
        )
        app_id = app_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        c_resp = self.client.post(
            "/api/v1/consents",
            json={
                "application_id": app_id,
                "applicant_profile_id": prof_id,
                "data_source": "PLATFORM",
                "purpose": "CREDIT_ASSESSMENT",
                "granted": True,
            },
            headers=headers,
        )
        self.cleanup_items.append(("consent", c_resp.json()["id"]))

        sig_resp = self.client.post(
            f"/api/v1/applications/{app_id}/financial-signals",
            json={
                "source": "PLATFORM",
                "average_income": 45000.0,
                "cashflow_buffer": 25000.0,
                "income_volatility": 0.10,
                "payment_regularity": 0.92,
                "repayment_reliability": 0.88,
            },
            headers=headers,
        )
        self.cleanup_items.append(("financial_signal", sig_resp.json()["id"]))

        # Register active model version
        admin_id, admin_headers = self.create_user_and_headers(role="ADMIN")
        mv_resp = self.client.post(
            "/api/v1/model-versions",
            json={
                "model_name": "mock_rules_v1",
                "version": f"1.0.{self.test_suffix}",
                "description": "Mock Scoring Engine",
                "is_active": True,
            },
            headers=admin_headers,
        )
        mv_id = mv_resp.json()["id"]
        self.cleanup_items.append(("model_version", mv_id))

        # Execute Assessment: POST /api/v1/applications/{application_id}/assess
        assess_resp = self.client.post(f"/api/v1/applications/{app_id}/assess", headers=headers)
        self.assertEqual(assess_resp.status_code, 201)
        assess_data = assess_resp.json()
        assess_id = assess_data["id"]
        self.cleanup_items.append(("assessment", assess_id))

        # Verification of score, risk_level, confidence, key_factors, explanation
        self.assertIn("score", assess_data)
        self.assertIsNotNone(assess_data["score"])
        self.assertGreaterEqual(assess_data["score"], 300)
        self.assertLessEqual(assess_data["score"], 850)
        self.assertIn("risk_level", assess_data)
        self.assertIn("confidence", assess_data)
        self.assertIn("key_factors", assess_data)
        self.assertIsInstance(assess_data["key_factors"], list)
        self.assertIn("explanation", assess_data)
        self.assertIsInstance(assess_data["explanation"], dict)
        self.assertEqual(assess_data["model_name"], "parakh-mock-engine")

        # GET by ID: /api/v1/assessments/{assessment_id}
        get_assess = self.client.get(f"/api/v1/assessments/{assess_id}", headers=headers)
        self.assertEqual(get_assess.status_code, 200)
        self.assertEqual(get_assess.json()["id"], assess_id)

        # GET application assessments: /api/v1/applications/{application_id}/assessments
        list_assess = self.client.get(f"/api/v1/applications/{app_id}/assessments", headers=headers)
        self.assertEqual(list_assess.status_code, 200)
        self.assertEqual(len(list_assess.json()), 1)

        # GET latest: /api/v1/applications/{application_id}/assessments/latest
        latest_assess = self.client.get(f"/api/v1/applications/{app_id}/assessments/latest", headers=headers)
        self.assertEqual(latest_assess.status_code, 200)
        self.assertEqual(latest_assess.json()["id"], assess_id)

    # --- 8. REVIEW ROUTES ---
    def test_review_routes(self):
        """Test human review creation and retrieval by application and reviewer."""
        # Setup application + reviewer user
        u_resp = self.client.post(
            "/api/v1/users",
            json={"email": f"rev_applicant_{self.test_suffix}@example.com", "role": "APPLICANT", "password": "Password123!"},
        )
        applicant_user_id = u_resp.json()["id"]
        self.cleanup_items.append(("user", applicant_user_id))
        app_headers = self.get_auth_header(applicant_user_id, "APPLICANT")

        p_resp = self.client.post(
            "/api/v1/applicants",
            json={"user_id": applicant_user_id, "gig_work_type": "Freelancer"},
            headers=app_headers,
        )
        prof_id = p_resp.json()["id"]
        self.cleanup_items.append(("applicant", prof_id))

        app_resp = self.client.post(
            "/api/v1/applications",
            json={"applicant_profile_id": prof_id, "requested_loan_amount": 15000.0},
            headers=app_headers,
        )
        app_id = app_resp.json()["id"]
        self.cleanup_items.append(("application", app_id))

        # Create Reviewer User
        reviewer_id, rev_headers = self.create_user_and_headers(role="REVIEWER")

        # Create Review: POST /api/v1/applications/{application_id}/reviews
        rev_resp = self.client.post(
            f"/api/v1/applications/{app_id}/reviews",
            json={
                "application_id": app_id,
                "reviewer_id": reviewer_id,
                "outcome": "REVIEWED",
                "notes": "Verified applicant identity and platform delivery history.",
            },
            headers=rev_headers,
        )
        self.assertEqual(rev_resp.status_code, 201)
        rev_data = rev_resp.json()
        rev_id = rev_data["id"]
        self.cleanup_items.append(("review", rev_id))
        self.assertEqual(rev_data["outcome"], "REVIEWED")

        # GET application reviews: /api/v1/applications/{application_id}/reviews
        app_revs = self.client.get(f"/api/v1/applications/{app_id}/reviews", headers=rev_headers)
        self.assertEqual(app_revs.status_code, 200)
        self.assertEqual(len(app_revs.json()), 1)
        self.assertEqual(app_revs.json()[0]["id"], rev_id)

        # GET reviewer reviews: /api/v1/reviewers/{reviewer_id}/reviews
        user_revs = self.client.get(f"/api/v1/reviewers/{reviewer_id}/reviews", headers=rev_headers)
        self.assertEqual(user_revs.status_code, 200)
        self.assertEqual(len(user_revs.json()), 1)
        self.assertEqual(user_revs.json()[0]["id"], rev_id)


class TestApiLivePostgreSqlPipeline(unittest.TestCase):
    """Explicit end-to-end integration test validating the full HTTP -> PostgreSQL lifecycle."""

    @unittest.skipUnless(can_connect_to_postgres(), "Live PostgreSQL is not available.")
    def test_full_live_http_to_postgres_lifecycle(self):
        """Verify:

        POST user -> POST applicant -> POST application -> POST consent
        -> POST financial signal -> POST assessment -> verify persisted directly in PostgreSQL.
        """
        client = TestClient(app)
        test_id = uuid.uuid4().hex[:8]
        cleanup_stack = []

        try:
            # 1. POST user
            u_res = client.post(
                "/api/v1/users",
                json={
                    "email": f"pipeline_{test_id}@example.com",
                    "role": "APPLICANT",
                    "password": "Password123!",
                },
            )
            self.assertEqual(u_res.status_code, 201)
            user_id = u_res.json()["id"]
            cleanup_stack.append(("user", user_id))
            from app.core.security import create_access_token
            token = create_access_token(subject=str(user_id), role="APPLICANT")
            headers = {"Authorization": f"Bearer {token}"}

            # 2. POST applicant profile
            p_res = client.post(
                "/api/v1/applicants",
                json={
                    "user_id": user_id,
                    "first_name": "Kavita",
                    "last_name": "Patel",
                    "gig_work_type": "Logistics",
                    "primary_platform": "Porter",
                    "tenure_months": 18,
                },
                headers=headers,
            )
            self.assertEqual(p_res.status_code, 201)
            profile_id = p_res.json()["id"]
            cleanup_stack.append(("applicant", profile_id))

            # 3. POST application
            a_res = client.post(
                "/api/v1/applications",
                json={
                    "applicant_profile_id": profile_id,
                    "requested_loan_amount": 50000.0,
                    "loan_purpose": "Vehicle Insurance & Gear",
                },
                headers=headers,
            )
            self.assertEqual(a_res.status_code, 201)
            application_id = a_res.json()["id"]
            cleanup_stack.append(("application", application_id))

            # 4. POST consent
            c_res = client.post(
                "/api/v1/consents",
                json={
                    "application_id": application_id,
                    "applicant_profile_id": profile_id,
                    "data_source": "PLATFORM",
                    "purpose": "CREDIT_ASSESSMENT",
                    "granted": True,
                },
                headers=headers,
            )
            self.assertEqual(c_res.status_code, 201)
            consent_id = c_res.json()["id"]
            cleanup_stack.append(("consent", consent_id))

            # 5. POST financial signal
            s_res = client.post(
                f"/api/v1/applications/{application_id}/financial-signals",
                json={
                    "source": "PLATFORM",
                    "average_income": 38000.0,
                    "cashflow_buffer": 12000.0,
                    "income_volatility": 0.15,
                    "payment_regularity": 0.85,
                    "repayment_reliability": 0.82,
                },
                headers=headers,
            )
            self.assertEqual(s_res.status_code, 201)
            signal_id = s_res.json()["id"]
            cleanup_stack.append(("financial_signal", signal_id))

            # 6. Ensure active model version exists
            with SessionLocal() as db:
                from app.repositories.user import UserRepository
                from app.core.security import hash_password
                from app.models.user import UserRole
                pipe_admin = UserRepository(db=db).create({
                    "email": f"pipe_admin_{test_id}@example.com",
                    "password_hash": hash_password("Password123!"),
                    "role": UserRole.ADMIN,
                    "is_active": True,
                }, commit=True)
                pipe_admin_id = str(pipe_admin.id)
            cleanup_stack.append(("user", pipe_admin_id))
            admin_token = create_access_token(subject=pipe_admin_id, role="ADMIN")
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            mv_res = client.post(
                "/api/v1/model-versions",
                json={
                    "model_name": "mock_rules_v1",
                    "version": f"1.0.pipe_{test_id}",
                    "description": "Mock Engine for Pipeline Test",
                    "is_active": True,
                },
                headers=admin_headers,
            )
            self.assertEqual(mv_res.status_code, 201)
            mv_id = mv_res.json()["id"]
            cleanup_stack.append(("model_version", mv_id))

            # 7. POST assessment
            assess_res = client.post(f"/api/v1/applications/{application_id}/assess", headers=headers)
            self.assertEqual(assess_res.status_code, 201)
            assessment_id = assess_res.json()["id"]
            cleanup_stack.append(("assessment", assessment_id))

            # 8. DIRECT POSTGRESQL VERIFICATION: verify every record in PostgreSQL
            with SessionLocal() as db:
                row_user = db.execute(
                    text("SELECT email, role FROM users WHERE id = :id"),
                    {"id": str(user_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_user)
                self.assertEqual(row_user["email"], f"pipeline_{test_id}@example.com")

                row_prof = db.execute(
                    text("SELECT gig_work_type FROM applicant_profiles WHERE id = :id"),
                    {"id": str(profile_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_prof)
                self.assertEqual(row_prof["gig_work_type"], "Logistics")

                row_app = db.execute(
                    text("SELECT status, requested_loan_amount FROM applications WHERE id = :id"),
                    {"id": str(application_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_app)
                self.assertEqual(float(row_app["requested_loan_amount"]), 50000.0)

                row_consent = db.execute(
                    text("SELECT granted, revoked_at FROM consents WHERE id = :id"),
                    {"id": str(consent_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_consent)
                self.assertTrue(row_consent["granted"])
                self.assertIsNone(row_consent["revoked_at"])

                row_signal = db.execute(
                    text("SELECT average_income FROM financial_signals WHERE id = :id"),
                    {"id": str(signal_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_signal)
                self.assertEqual(float(row_signal["average_income"]), 38000.0)

                row_assessment = db.execute(
                    text("SELECT credit_score, risk_level, assessment_status FROM credit_assessments WHERE id = :id"),
                    {"id": str(assessment_id)},
                ).mappings().one_or_none()
                self.assertIsNotNone(row_assessment)
                self.assertIsNotNone(row_assessment["credit_score"])
                self.assertEqual(row_assessment["assessment_status"], "COMPLETED")

        finally:
            # Cleanup in reverse dependency order
            with SessionLocal() as db:
                for entity_type, entity_id in reversed(cleanup_stack):
                    try:
                        if entity_type == "assessment":
                            db.execute(text("DELETE FROM credit_assessments WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "financial_signal":
                            db.execute(text("DELETE FROM financial_signals WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "consent":
                            db.execute(text("DELETE FROM consents WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "application":
                            db.execute(text("DELETE FROM applications WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "applicant":
                            db.execute(text("DELETE FROM applicant_profiles WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "model_version":
                            db.execute(text("DELETE FROM model_versions WHERE id = :id"), {"id": str(entity_id)})
                        elif entity_type == "user":
                            db.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(entity_id)})
                        db.commit()
                    except Exception:
                        db.rollback()


class TestApiExceptionHandlers(unittest.TestCase):
    """Test centralized domain exception to HTTP response mapping."""

    def setUp(self):
        self.client = TestClient(app)
        from app.models.user import User, UserRole
        from app.api.deps import get_current_active_user
        mock_user = User(id=uuid.uuid4(), email="admin_ex@parakh.com", role=UserRole.ADMIN, is_active=True)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_404_entity_not_found(self):
        """EntityNotFoundError maps to 404 Not Found."""
        res = self.client.get(f"/api/v1/users/{uuid.uuid4()}")
        self.assertEqual(res.status_code, 404)
        data = res.json()
        self.assertIn("detail", data)

    def test_422_unprocessable_entity(self):
        """Malformed Pydantic request returns 422 Unprocessable Entity."""
        res = self.client.post("/api/v1/users", json={"email": "not-an-email", "password": "short"})
        self.assertEqual(res.status_code, 422)

    def test_400_and_500_and_501_assessment_engine_exceptions(self):
        """Assessment exceptions map to 400, 500, and 501 status codes."""
        from unittest.mock import MagicMock
        from app.assessment.exceptions import (
            AssessmentInputError,
            AssessmentOutputError,
            AssessmentNotImplementedError,
        )
        from app.api.deps import get_assessment_service
        from app.services.assessment import AssessmentService

        # 1. Test AssessmentInputError -> 400
        mock_svc_400 = MagicMock(spec=AssessmentService)
        mock_svc_400.db = MagicMock()
        mock_svc_400.assess_application.side_effect = AssessmentInputError("Invalid input features")
        app.dependency_overrides[get_assessment_service] = lambda: mock_svc_400
        res = self.client.post(f"/api/v1/applications/{uuid.uuid4()}/assess")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid input features", res.json().get("detail", ""))

        # 2. Test AssessmentOutputError -> 500
        mock_svc_500 = MagicMock(spec=AssessmentService)
        mock_svc_500.db = MagicMock()
        mock_svc_500.assess_application.side_effect = AssessmentOutputError("Engine produced corrupted output")
        app.dependency_overrides[get_assessment_service] = lambda: mock_svc_500
        res = self.client.post(f"/api/v1/applications/{uuid.uuid4()}/assess")
        self.assertEqual(res.status_code, 500)
        self.assertIn("Engine produced corrupted output", res.json().get("detail", ""))

        # 3. Test AssessmentNotImplementedError -> 501
        mock_svc_501 = MagicMock(spec=AssessmentService)
        mock_svc_501.db = MagicMock()
        mock_svc_501.assess_application.side_effect = AssessmentNotImplementedError("Scoring model not implemented")
        app.dependency_overrides[get_assessment_service] = lambda: mock_svc_501
        res = self.client.post(f"/api/v1/applications/{uuid.uuid4()}/assess")
        self.assertEqual(res.status_code, 501)
        self.assertIn("Scoring model not implemented", res.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
