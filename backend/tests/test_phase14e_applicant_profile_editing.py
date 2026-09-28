"""Phase 14E: Wire Applicant Profile Editing Test Suite (P2-05).

Verifies end-to-end functionality for applicant profile editing:
1. Authenticated applicant can PATCH their own supported profile fields.
2. PATCH persists updated values to the database.
3. Partial PATCH leaves unspecified/omitted fields unchanged.
4. Cross-applicant isolation: applicant cannot PATCH another applicant's profile (HTTP 403).
5. Unauthenticated PATCH is rejected (HTTP 401).
6. Reviewer access: Reviewers cannot mutate applicant profiles (HTTP 403).
7. Admin access: Admins can update applicant profiles.
8. Nonexistent profile PATCH returns HTTP 404.
9. Invalid field values (negative years, >31 working days, <2 char work type) return HTTP 422.
10. Audit logging: APPLICANT_PROFILE_UPDATED event is recorded on update.
11. Aliased field mappings (work_type, experience_months, preferred_loan_purpose, average_working_days_per_week) are honored.
12. Assessment consent preservation: Profile updates do not bypass or weaken assessment consent enforcement.
"""
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.audit_events import AuditAction
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    Consent,
    ConsentDataSource,
    CreditAssessment,
    ModelVersion,
    RiskLevel,
    User,
    UserRole,
)
from app.services.assessment import AssessmentService
from app.services.exceptions import ConsentRequiredError


class TestPhase14EApplicantProfileEditing(unittest.TestCase):
    """Deterministic verification test suite for applicant profile editing."""

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

        # Wire dependency override for get_db
        def override_get_db() -> Generator[Session, None, None]:
            session = self.SessionFactory()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db

        # Seed initial deterministic test users and applicant profile
        session = self.SessionFactory()
        try:
            # 1. Primary Applicant User
            self.applicant_user_id = uuid.uuid4()
            self.applicant_user = User(
                id=self.applicant_user_id,
                email="applicant14e@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant_user)

            # Primary Applicant Profile
            self.applicant_profile_id = uuid.uuid4()
            self.applicant_profile = ApplicantProfile(
                id=self.applicant_profile_id,
                user_id=self.applicant_user_id,
                gig_work_type="Food Delivery",
                years_working=Decimal("2.0"),
                average_working_days=24,
                business_or_loan_purpose="Electric Scooter Battery Swap",
            )
            session.add(self.applicant_profile)

            # 2. Second Applicant User (for isolation testing)
            self.other_applicant_user_id = uuid.uuid4()
            self.other_applicant_user = User(
                id=self.other_applicant_user_id,
                email="other_applicant14e@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.other_applicant_user)

            self.other_applicant_profile_id = uuid.uuid4()
            self.other_applicant_profile = ApplicantProfile(
                id=self.other_applicant_profile_id,
                user_id=self.other_applicant_user_id,
                gig_work_type="Logistics",
                years_working=Decimal("1.0"),
                average_working_days=20,
                business_or_loan_purpose="Working Capital",
            )
            session.add(self.other_applicant_profile)

            # 3. Reviewer User
            self.reviewer_user_id = uuid.uuid4()
            self.reviewer_user = User(
                id=self.reviewer_user_id,
                email="reviewer14e@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.REVIEWER,
                is_active=True,
            )
            session.add(self.reviewer_user)

            # 4. Admin User
            self.admin_user_id = uuid.uuid4()
            self.admin_user = User(
                id=self.admin_user_id,
                email="admin14e@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(self.admin_user)

            session.commit()
        finally:
            session.close()

        # Generate bearer tokens via _login
        self.password = "Password123!"
        self.applicant_token = self._login("applicant14e@parakh.in", self.password)
        self.other_applicant_token = self._login("other_applicant14e@parakh.in", self.password)
        self.reviewer_token = self._login("reviewer14e@parakh.in", self.password)
        self.admin_token = self._login("admin14e@parakh.in", self.password)

        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}
        self.other_applicant_headers = {"Authorization": f"Bearer {self.other_applicant_token}"}
        self.reviewer_headers = {"Authorization": f"Bearer {self.reviewer_token}"}
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}")
        return resp.json()["access_token"]

    def tearDown(self):
        """Clean up database and reset dependency overrides."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_applicant_patch_own_profile_success(self):
        """Verify applicant can update their own supported profile fields and changes persist in DB."""
        payload = {
            "gig_work_type": "Ride Hailing",
            "years_working": 3.5,
            "average_working_days": 26,
            "business_or_loan_purpose": "Commercial Vehicle Maintenance",
        }

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.applicant_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.applicant_profile_id))
        self.assertEqual(data["user_id"], str(self.applicant_user_id))
        self.assertEqual(data["gig_work_type"], "Ride Hailing")
        self.assertEqual(float(data["years_working"]), 3.5)
        self.assertEqual(data["average_working_days"], 26)
        self.assertEqual(data["business_or_loan_purpose"], "Commercial Vehicle Maintenance")
        self.assertEqual(data["work_type"], "Ride Hailing")

        # Authoritative persistence verification via separate database query
        session = self.SessionFactory()
        try:
            persisted = session.scalar(
                select(ApplicantProfile).where(ApplicantProfile.id == self.applicant_profile_id)
            )
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted.gig_work_type, "Ride Hailing")
            self.assertEqual(float(persisted.years_working), 3.5)
            self.assertEqual(persisted.average_working_days, 26)
            self.assertEqual(persisted.business_or_loan_purpose, "Commercial Vehicle Maintenance")
        finally:
            session.close()

    def test_partial_patch_preserves_omitted_fields(self):
        """Verify partial update modifies only specified fields, leaving omitted fields intact."""
        # Initial values: gig_work_type="Food Delivery", average_working_days=24, business_or_loan_purpose="Electric Scooter Battery Swap"
        partial_payload = {
            "years_working": 4.5
        }

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=partial_payload,
            headers=self.applicant_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(float(data["years_working"]), 4.5)
        # Omitted fields must be preserved exactly
        self.assertEqual(data["gig_work_type"], "Food Delivery")
        self.assertEqual(data["average_working_days"], 24)
        self.assertEqual(data["business_or_loan_purpose"], "Electric Scooter Battery Swap")

        # Database verification
        session = self.SessionFactory()
        try:
            persisted = session.scalar(
                select(ApplicantProfile).where(ApplicantProfile.id == self.applicant_profile_id)
            )
            self.assertEqual(float(persisted.years_working), 4.5)
            self.assertEqual(persisted.gig_work_type, "Food Delivery")
            self.assertEqual(persisted.average_working_days, 24)
            self.assertEqual(persisted.business_or_loan_purpose, "Electric Scooter Battery Swap")
        finally:
            session.close()

    def test_applicant_cannot_patch_other_applicant_profile(self):
        """Verify an applicant cannot mutate another applicant's profile (HTTP 403 Forbidden)."""
        payload = {"gig_work_type": "Tampered Work Type"}

        # other_applicant attempts to modify applicant_profile_id
        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.other_applicant_headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.json()["detail"])

        # Database verification: profile remained untouched
        session = self.SessionFactory()
        try:
            persisted = session.scalar(
                select(ApplicantProfile).where(ApplicantProfile.id == self.applicant_profile_id)
            )
            self.assertEqual(persisted.gig_work_type, "Food Delivery")
        finally:
            session.close()

    def test_unauthenticated_patch_rejected(self):
        """Verify unauthenticated PATCH requests are rejected with HTTP 401 Unauthorized."""
        payload = {"years_working": 5.0}

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
        )

        self.assertEqual(response.status_code, 401)

    def test_reviewer_cannot_patch_applicant_profile(self):
        """Verify reviewers cannot mutate applicant profiles (HTTP 403 Forbidden)."""
        payload = {"gig_work_type": "Reviewer Modified Type"}

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.reviewer_headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.json()["detail"])

        # Database verification
        session = self.SessionFactory()
        try:
            persisted = session.scalar(
                select(ApplicantProfile).where(ApplicantProfile.id == self.applicant_profile_id)
            )
            self.assertEqual(persisted.gig_work_type, "Food Delivery")
        finally:
            session.close()

    def test_admin_can_patch_applicant_profile(self):
        """Verify admins have authority to update applicant profiles on behalf of the platform."""
        payload = {
            "gig_work_type": "Admin Verified Fleet Logistics",
            "business_or_loan_purpose": "Commercial Expansion Grant",
        }

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["gig_work_type"], "Admin Verified Fleet Logistics")
        self.assertEqual(data["business_or_loan_purpose"], "Commercial Expansion Grant")

        # Database verification
        session = self.SessionFactory()
        try:
            persisted = session.scalar(
                select(ApplicantProfile).where(ApplicantProfile.id == self.applicant_profile_id)
            )
            self.assertEqual(persisted.gig_work_type, "Admin Verified Fleet Logistics")
        finally:
            session.close()

    def test_patch_nonexistent_profile_returns_404(self):
        """Verify PATCH on nonexistent profile UUID returns HTTP 404 Not Found."""
        random_id = uuid.uuid4()
        payload = {"years_working": 2.0}

        response = self.client.patch(
            f"/api/v1/applicants/{random_id}",
            json=payload,
            headers=self.applicant_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_profile_values_rejected(self):
        """Verify Pydantic request validation rejects out-of-bounds or malformed values with HTTP 422."""
        # 1. Negative years_working
        r1 = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json={"years_working": -1.0},
            headers=self.applicant_headers,
        )
        self.assertEqual(r1.status_code, 422)

        # 2. Excess years_working (> 50)
        r2 = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json={"years_working": 55.0},
            headers=self.applicant_headers,
        )
        self.assertEqual(r2.status_code, 422)

        # 3. Excess average_working_days (> 31)
        r3 = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json={"average_working_days": 35},
            headers=self.applicant_headers,
        )
        self.assertEqual(r3.status_code, 422)

        # 4. Negative average_working_days (< 0)
        r4 = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json={"average_working_days": -2},
            headers=self.applicant_headers,
        )
        self.assertEqual(r4.status_code, 422)

        # 5. Work type too short (< 2 chars)
        r5 = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json={"gig_work_type": "x"},
            headers=self.applicant_headers,
        )
        self.assertEqual(r5.status_code, 422)

    def test_audit_logging_on_profile_update(self):
        """Verify successful profile update generates an APPLICANT_PROFILE_UPDATED audit log."""
        payload = {"business_or_loan_purpose": "Audit Verification Purpose"}

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.applicant_headers,
        )
        self.assertEqual(response.status_code, 200)

        # Check audit_logs table
        session = self.SessionFactory()
        try:
            logs = session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id == str(self.applicant_profile_id),
                    AuditLog.action == AuditAction.APPLICANT_PROFILE_UPDATED,
                )
            ).all()
            self.assertGreaterEqual(len(logs), 1)
            latest_log = logs[-1]
            self.assertEqual(latest_log.entity_type, "ApplicantProfile")
            self.assertEqual(latest_log.user_id, self.applicant_user_id)
        finally:
            session.close()

    def test_aliased_fields_mapping_on_patch(self):
        """Verify legacy/frontend aliases map properly into authoritative ApplicantProfile attributes."""
        payload = {
            "work_type": "Quick Commerce Grocery Delivery",
            "experience_months": 36,  # Should map to 3.0 years
            "preferred_loan_purpose": "High-Efficiency EV Cargo Scooter",
            "average_working_days_per_week": 6,  # 6 * 4.33 -> 26 days
        }

        response = self.client.patch(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            json=payload,
            headers=self.applicant_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["gig_work_type"], "Quick Commerce Grocery Delivery")
        self.assertEqual(float(data["years_working"]), 3.0)
        self.assertEqual(data["business_or_loan_purpose"], "High-Efficiency EV Cargo Scooter")
        self.assertEqual(data["average_working_days"], 26)

    def test_get_profile_by_user_id_and_by_id_endpoints(self):
        """Verify GET endpoints return authoritative profile and respect applicant isolation."""
        # 1. GET by profile ID
        r1 = self.client.get(
            f"/api/v1/applicants/{self.applicant_profile_id}",
            headers=self.applicant_headers,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["id"], str(self.applicant_profile_id))

        # 2. GET by user ID
        r2 = self.client.get(
            f"/api/v1/applicants/user/{self.applicant_user_id}",
            headers=self.applicant_headers,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["id"], str(self.applicant_profile_id))

        # 3. Isolation: applicant cannot GET other applicant's profile
        r3 = self.client.get(
            f"/api/v1/applicants/{self.other_applicant_profile_id}",
            headers=self.applicant_headers,
        )
        self.assertEqual(r3.status_code, 403)

        r4 = self.client.get(
            f"/api/v1/applicants/user/{self.other_applicant_user_id}",
            headers=self.applicant_headers,
        )
        self.assertEqual(r4.status_code, 403)

    def test_assessment_consent_enforcement_remains_intact(self):
        """Verify applicant profile updates do not satisfy or bypass application-level assessment consent."""
        session = self.SessionFactory()
        try:
            # Create active model version
            model_ver = ModelVersion(
                id=uuid.uuid4(),
                model_name="risk_scoring_xgboost",
                version="v1.0.0-test",
                algorithm="XGBoost",
                is_active=True,
            )
            session.add(model_ver)

            # Create an application without consent
            app_id = uuid.uuid4()
            application = Application(
                id=app_id,
                applicant_profile_id=self.applicant_profile_id,
                requested_loan_amount=Decimal("25000.00"),
                status=ApplicationStatus.SUBMITTED,
            )
            session.add(application)
            session.commit()

            # Attempt assessment without required application consent
            from app.assessment.mock import MockAssessmentEngine
            assessment_service = AssessmentService(db=session, engine=MockAssessmentEngine())
            with self.assertRaises(ConsentRequiredError) as ctx:
                assessment_service.assess_application(
                    application_id=app_id,
                    enforce_consent=True,
                )
            self.assertIn("Active applicant consent is required", str(ctx.exception))
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
