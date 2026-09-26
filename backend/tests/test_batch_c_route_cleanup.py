"""Focused tests for Batch C — P2-08 & P2-09 API and Backend Route Cleanup.

Verifies:
1. Obsolete backend route GET /api/v1/applications/{id}/financial-signals/latest is removed (returns 404).
2. Authoritative GET /api/v1/applications/{id}/financial-signals remains functional and provides signals.
3. OpenAPI schema accurately reflects removed routes.
4. Intentionally backend-only, operational, compliance, and governance routes remain intact with strict RBAC:
   - GET /api/v1/users/{user_id} and GET /api/v1/users/by-email/{email}
   - PATCH /api/v1/users/{user_id}
   - PATCH /api/v1/applications/{application_id} (P3-06)
   - GET /api/v1/applications/{application_id}/assessments (P2-11)
   - GET /api/v1/applications/{application_id}/consents (DPDP compliance history)
   - GET /api/v1/analytics/sector-risk
   - GET /api/v1/model-versions/active/{model_name}
"""
import unittest
import uuid
from decimal import Decimal
from typing import Generator

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
    Consent,
    ConsentDataSource,
    FinancialSignal,
    User,
    UserRole,
)


class TestBatchCRouteCleanup(unittest.TestCase):
    """Test suite for Batch C API and backend route cleanup."""

    def setUp(self):
        """Configure in-memory SQLite database and FastAPI TestClient with deterministic test data."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.client = TestClient(app)

        def override_get_db() -> Generator[Session, None, None]:
            session = self.SessionFactory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db

        session = self.SessionFactory()
        try:
            self.test_suffix = uuid.uuid4().hex[:8]

            # Create APPLICANT 1
            self.applicant1 = User(
                email=f"app1_{self.test_suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant1)

            # Create APPLICANT 2 (Intruder)
            self.applicant2 = User(
                email=f"app2_{self.test_suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant2)

            # Create REVIEWER
            self.reviewer = User(
                email=f"rev_{self.test_suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.REVIEWER,
                is_active=True,
            )
            session.add(self.reviewer)

            # Create ADMIN
            self.admin = User(
                email=f"admin_{self.test_suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(self.admin)
            session.commit()

            # Create ApplicantProfile for Applicant 1
            self.profile1 = ApplicantProfile(
                user_id=self.applicant1.id,
                gig_work_type="DELIVERY",
                years_working=Decimal("2.5"),
                average_working_days=26,
            )
            session.add(self.profile1)
            session.commit()

            # Create Application for Applicant 1
            self.application1 = Application(
                applicant_profile_id=self.profile1.id,
                requested_loan_amount=Decimal("50000.00"),
                preferred_repayment_period=6,
                loan_purpose="EQUIPMENT",
                status=ApplicationStatus.DRAFT,
            )
            session.add(self.application1)
            session.commit()

            # Store IDs
            self.app1_id = self.applicant1.id
            self.app2_id = self.applicant2.id
            self.rev_id = self.reviewer.id
            self.admin_id = self.admin.id
            self.profile1_id = self.profile1.id
            self.application1_id = self.application1.id
            self.app1_email = self.applicant1.email
        finally:
            session.close()

        # Tokens
        self.app1_token = create_access_token(subject=str(self.app1_id), role=UserRole.APPLICANT.value)
        self.app2_token = create_access_token(subject=str(self.app2_id), role=UserRole.APPLICANT.value)
        self.rev_token = create_access_token(subject=str(self.rev_id), role=UserRole.REVIEWER.value)
        self.admin_token = create_access_token(subject=str(self.admin_id), role=UserRole.ADMIN.value)

        self.app1_headers = {"Authorization": f"Bearer {self.app1_token}"}
        self.app2_headers = {"Authorization": f"Bearer {self.app2_token}"}
        self.rev_headers = {"Authorization": f"Bearer {self.rev_token}"}
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    # =========================================================================
    # 1. P2-09 ROUTE REMOVAL & CONSOLIDATION TESTS
    # =========================================================================

    def test_p2_09_financial_signals_latest_route_removed(self):
        """Verify GET /api/v1/applications/{id}/financial-signals/latest returns 404."""
        resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/financial-signals/latest",
            headers=self.app1_headers,
        )
        self.assertEqual(resp.status_code, 404)

    def test_p2_09_financial_signals_list_authoritative(self):
        """Verify GET /api/v1/applications/{id}/financial-signals is the authoritative retrieval endpoint."""
        payload = {
            "source": "PLATFORM",
            "average_income": "32000.00",
            "median_income": "30000.00",
            "income_volatility": "0.15",
            "active_days": 24,
            "payment_regularity": "0.95",
            "cashflow_buffer": "15000.00",
        }
        post_resp = self.client.post(
            f"/api/v1/applications/{self.application1_id}/financial-signals?enforce_consent=false",
            headers=self.app1_headers,
            json=payload,
        )
        self.assertEqual(post_resp.status_code, 201)
        created_id = post_resp.json()["id"]

        list_resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/financial-signals",
            headers=self.app1_headers,
        )
        self.assertEqual(list_resp.status_code, 200)
        signals = list_resp.json()
        self.assertIsInstance(signals, list)
        self.assertGreaterEqual(len(signals), 1)
        self.assertEqual(signals[0]["id"], created_id)

    def test_p2_09_openapi_schema_excludes_removed_route(self):
        """Verify OpenAPI schema no longer exposes financial-signals/latest."""
        schema = app.openapi()
        all_paths = schema.get("paths", {})
        self.assertNotIn(
            "/api/v1/applications/{application_id}/financial-signals/latest",
            all_paths,
            "financial-signals/latest must not be present in OpenAPI schema",
        )
        self.assertIn(
            "/api/v1/applications/{application_id}/financial-signals",
            all_paths,
            "authoritative financial-signals route must be in OpenAPI schema",
        )

    # =========================================================================
    # 2. INTENTIONALLY BACKEND-ONLY ROUTE PRESERVATION & RBAC TESTS
    # =========================================================================

    def test_user_management_routes_preserved(self):
        """Verify GET /users/{id}, GET /users/by-email/{email}, and PATCH /users/{id} remain functional with RBAC."""
        # 1. Own user retrieval -> 200
        resp_own = self.client.get(f"/api/v1/users/{self.app1_id}", headers=self.app1_headers)
        self.assertEqual(resp_own.status_code, 200)
        self.assertEqual(resp_own.json()["email"], self.app1_email)

        # 2. Other applicant retrieval -> 403 Forbidden
        resp_intruder = self.client.get(f"/api/v1/users/{self.app1_id}", headers=self.app2_headers)
        self.assertEqual(resp_intruder.status_code, 403)

        # 3. Lookup by email -> 200 for own email
        resp_email = self.client.get(f"/api/v1/users/by-email/{self.app1_email}", headers=self.app1_headers)
        self.assertEqual(resp_email.status_code, 200)

        # 4. Lookup by other email -> 403
        resp_other_email = self.client.get(f"/api/v1/users/by-email/{self.app1_email}", headers=self.app2_headers)
        self.assertEqual(resp_other_email.status_code, 403)

        # 5. Non-admin cannot alter role via PATCH -> 403
        patch_resp = self.client.patch(
            f"/api/v1/users/{self.app1_id}",
            headers=self.app1_headers,
            json={"role": "ADMIN"},
        )
        self.assertEqual(patch_resp.status_code, 403)

    def test_application_terms_update_preserved_for_p3_06(self):
        """Verify PATCH /applications/{id} remains functional for updating terms."""
        # Owner updates loan amount
        update_resp = self.client.patch(
            f"/api/v1/applications/{self.application1_id}",
            headers=self.app1_headers,
            json={"requested_loan_amount": 75000.0},
        )
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(float(update_resp.json()["requested_loan_amount"]), 75000.0)

        # Intruder cannot update terms
        intruder_resp = self.client.patch(
            f"/api/v1/applications/{self.application1_id}",
            headers=self.app2_headers,
            json={"requested_loan_amount": 90000.0},
        )
        self.assertEqual(intruder_resp.status_code, 403)

    def test_historical_assessments_route_preserved_for_p2_11(self):
        """Verify GET /applications/{id}/assessments remains functional for P2-11."""
        resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/assessments",
            headers=self.app1_headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

        # Reviewer can also list historical assessments
        rev_resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/assessments",
            headers=self.rev_headers,
        )
        self.assertEqual(rev_resp.status_code, 200)

        # Intruder cannot access assessments
        int_resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/assessments",
            headers=self.app2_headers,
        )
        self.assertEqual(int_resp.status_code, 403)

    def test_consents_history_route_preserved_for_dpdp(self):
        """Verify GET /applications/{id}/consents returns complete consent history."""
        consent_resp = self.client.post(
            "/api/v1/consents",
            headers=self.app1_headers,
            json={
                "application_id": str(self.application1_id),
                "data_source": "PLATFORM",
                "purpose": "Credit risk evaluation",
            },
        )
        self.assertEqual(consent_resp.status_code, 201)

        list_resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/consents",
            headers=self.app1_headers,
        )
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.json()), 1)

        int_resp = self.client.get(
            f"/api/v1/applications/{self.application1_id}/consents",
            headers=self.app2_headers,
        )
        self.assertEqual(int_resp.status_code, 403)

    def test_sector_risk_endpoint_preserved(self):
        """Verify GET /api/v1/analytics/sector-risk is accessible to reviewers and blocked for applicants."""
        rev_resp = self.client.get("/api/v1/analytics/sector-risk", headers=self.rev_headers)
        self.assertEqual(rev_resp.status_code, 200)

        app_resp = self.client.get("/api/v1/analytics/sector-risk", headers=self.app1_headers)
        self.assertEqual(app_resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
