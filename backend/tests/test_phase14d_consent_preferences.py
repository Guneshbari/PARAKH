"""Phase 14D: DPDP Consent Preferences Persistence Test Suite (P2-04).

Verifies end-to-end functionality for persisting and enforcing DPDP consent preferences:
1. Default state: uninitialized preferences default to False (missing consent is not granted).
2. Authenticated applicant can update preferences via PATCH /api/v1/consents/preferences.
3. Authenticated applicant can replace preferences via PUT /api/v1/consents/preferences.
4. Preference revocation via POST /api/v1/consents/preferences/{key}/revoke.
5. Preference key normalization supports canonical keys, snake_case, and camelCase aliases.
6. Applicant ownership: applicant cannot read another applicant's preferences (HTTP 403).
7. Applicant ownership: applicant cannot modify another applicant's preferences (HTTP 403).
8. Applicant ownership: applicant cannot revoke another applicant's preferences (HTTP 403).
9. Unauthenticated access rejected with HTTP 401.
10. Reviewer access: Reviewers can view applicant preferences but cannot modify them (HTTP 403).
11. Admin access: Admins can view and update applicant preferences on behalf of users.
12. Audit trail: Preference grants and revocations record structured audit events.
13. Assessment consent preservation: Profile preferences never bypass or satisfy assessment consent.
    Missing/revoked application data-source consent continues blocking assessments (HTTP 403).
"""
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
    ConsentPreference,
    CreditAssessment,
    ModelVersion,
    RiskLevel,
    User,
    UserRole,
)
from app.repositories.applicant import ApplicantRepository
from app.repositories.application import ApplicationRepository
from app.repositories.consent import ConsentRepository
from app.repositories.user import UserRepository
from app.services.assessment import AssessmentService
from app.services.consent import ConsentService
from app.services.exceptions import ConsentRequiredError


class TestPhase14DConsentPreferences(unittest.TestCase):
    """Deterministic verification test suite for DPDP consent preferences."""

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
            db = self.SessionFactory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # Seed test actors
        self.password = "SecurePass123!"
        with self.SessionFactory() as db:
            user_repo = UserRepository(db)
            applicant_repo = ApplicantRepository(db)

            # 1. Applicant 1 (Primary)
            u1 = user_repo.create({
                "email": "applicant1@test.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.applicant1_id = u1.id

            p1 = applicant_repo.create({
                "user_id": u1.id,
                "gig_work_type": "Delivery",
                "years_working": Decimal("3.0"),
                "average_working_days": 25,
                "business_or_loan_purpose": "Vehicle repair",
            }, commit=True)
            self.profile1_id = p1.id

            # 2. Applicant 2 (Secondary - for isolation checks)
            u2 = user_repo.create({
                "email": "applicant2@test.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            self.applicant2_id = u2.id

            p2 = applicant_repo.create({
                "user_id": u2.id,
                "gig_work_type": "Rideshare",
                "years_working": Decimal("2.0"),
                "average_working_days": 22,
                "business_or_loan_purpose": "Fuel advance",
            }, commit=True)
            self.profile2_id = p2.id

            # 3. Reviewer
            u3 = user_repo.create({
                "email": "reviewer@test.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)
            self.reviewer_id = u3.id

            # 4. Admin
            u4 = user_repo.create({
                "email": "admin@test.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.ADMIN,
                "is_active": True,
            }, commit=True)
            self.admin_id = u4.id

        # Generate bearer tokens via _login
        self.token_applicant1 = self._login("applicant1@test.com", self.password)
        self.token_applicant2 = self._login("applicant2@test.com", self.password)
        self.token_reviewer = self._login("reviewer@test.com", self.password)
        self.token_admin = self._login("admin@test.com", self.password)

        self.headers_app1 = {"Authorization": f"Bearer {self.token_applicant1}"}
        self.headers_app2 = {"Authorization": f"Bearer {self.token_applicant2}"}
        self.headers_rev = {"Authorization": f"Bearer {self.token_reviewer}"}
        self.headers_adm = {"Authorization": f"Bearer {self.token_admin}"}

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}")
        return resp.json()["access_token"]

    def tearDown(self):
        """Clean up database and dependency overrides."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    # -------------------------------------------------------------------------
    # Test Cases
    # -------------------------------------------------------------------------

    def test_default_preferences_are_false(self):
        """Unset preferences must return False; missing consent is never defaulted to granted."""
        resp = self.client.get("/api/v1/consents/preferences", headers=self.headers_app1)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["user_id"], str(self.applicant1_id))
        self.assertFalse(data["consent_benchmark"])
        self.assertFalse(data["consent_realtime"])
        self.assertFalse(data["consent_alerts"])

        # Check granular preferences list
        self.assertIn("preferences", data)
        self.assertEqual(len(data["preferences"]), 3)
        for item in data["preferences"]:
            self.assertFalse(item["granted"])
            self.assertIsNone(item["consented_at"])
            self.assertIsNone(item["revoked_at"])

    def test_applicant_patch_preferences(self):
        """Applicant can update preferences and persisted state reflects new values."""
        payload = {
            "consent_benchmark": True,
            "consent_realtime": True,
        }
        patch_resp = self.client.patch(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json=payload,
        )
        self.assertEqual(patch_resp.status_code, 200)
        data = patch_resp.json()
        self.assertTrue(data["consent_benchmark"])
        self.assertTrue(data["consent_realtime"])
        self.assertFalse(data["consent_alerts"])

        # Fetch again with GET to ensure database persistence
        get_resp = self.client.get("/api/v1/consents/preferences", headers=self.headers_app1)
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertTrue(get_data["consent_benchmark"])
        self.assertTrue(get_data["consent_realtime"])
        self.assertFalse(get_data["consent_alerts"])

        # Check that consented_at timestamp is populated
        items_map = {item["key"]: item for item in get_data["preferences"]}
        self.assertIsNotNone(items_map["consent_benchmark"]["consented_at"])
        self.assertIsNone(items_map["consent_benchmark"]["revoked_at"])
        self.assertIsNotNone(items_map["consent_realtime"]["consented_at"])
        self.assertIsNone(items_map["consent_alerts"]["consented_at"])

    def test_applicant_put_preferences(self):
        """PUT /api/v1/consents/preferences persists updated preferences."""
        payload = {
            "consent_alerts": True,
        }
        put_resp = self.client.put(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json=payload,
        )
        self.assertEqual(put_resp.status_code, 200)
        data = put_resp.json()
        self.assertTrue(data["consent_alerts"])

    def test_revoke_preference_via_endpoint(self):
        """Revoking a preference sets granted=False and stamps revoked_at."""
        # 1. Grant first
        self.client.patch(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json={"consent_benchmark": True},
        )

        # 2. Revoke via dedicated revoke endpoint
        revoke_resp = self.client.post(
            "/api/v1/consents/preferences/consent_benchmark/revoke",
            headers=self.headers_app1,
        )
        self.assertEqual(revoke_resp.status_code, 200)
        data = revoke_resp.json()
        self.assertFalse(data["consent_benchmark"])

        items_map = {item["key"]: item for item in data["preferences"]}
        self.assertFalse(items_map["consent_benchmark"]["granted"])
        self.assertIsNotNone(items_map["consent_benchmark"]["revoked_at"])

    def test_preference_key_alias_normalization(self):
        """CamelCase and alias payloads normalize to canonical database preference keys."""
        payload = {
            "consentBenchmark": True,
            "consentRealtime": True,
            "consentAlerts": True,
        }
        resp = self.client.patch(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json=payload,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["consent_benchmark"])
        self.assertTrue(data["consent_realtime"])
        self.assertTrue(data["consent_alerts"])

    def test_applicant_cannot_access_other_applicant_preferences(self):
        """Applicant cannot view another applicant's preferences (HTTP 403)."""
        resp = self.client.get(
            f"/api/v1/consents/preferences?user_id={self.applicant2_id}",
            headers=self.headers_app1,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["detail"])

    def test_applicant_cannot_modify_other_applicant_preferences(self):
        """Applicant cannot update another applicant's preferences (HTTP 403)."""
        resp = self.client.patch(
            f"/api/v1/consents/preferences?user_id={self.applicant2_id}",
            headers=self.headers_app1,
            json={"consent_benchmark": True},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["detail"])

    def test_applicant_cannot_revoke_other_applicant_preferences(self):
        """Applicant cannot revoke another applicant's preferences (HTTP 403)."""
        resp = self.client.post(
            f"/api/v1/consents/preferences/consent_benchmark/revoke?user_id={self.applicant2_id}",
            headers=self.headers_app1,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json()["detail"])

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated requests must fail with HTTP 401."""
        get_resp = self.client.get("/api/v1/consents/preferences")
        self.assertEqual(get_resp.status_code, 401)

        patch_resp = self.client.patch(
            "/api/v1/consents/preferences",
            json={"consent_benchmark": True},
        )
        self.assertEqual(patch_resp.status_code, 401)

    def test_reviewer_can_read_but_cannot_modify_applicant_preferences(self):
        """Reviewers can view applicant preferences but are denied modification (HTTP 403)."""
        # Read applicant1 preferences as reviewer
        get_resp = self.client.get(
            f"/api/v1/consents/preferences?user_id={self.applicant1_id}",
            headers=self.headers_rev,
        )
        self.assertEqual(get_resp.status_code, 200)

        # Attempt to modify as reviewer
        patch_resp = self.client.patch(
            f"/api/v1/consents/preferences?user_id={self.applicant1_id}",
            headers=self.headers_rev,
            json={"consent_benchmark": True},
        )
        self.assertEqual(patch_resp.status_code, 403)
        self.assertIn("reviewers cannot modify", patch_resp.json()["detail"])

    def test_admin_can_read_and_modify_preferences(self):
        """Admins can view and update applicant preferences."""
        # Admin modifies applicant1 preferences
        patch_resp = self.client.patch(
            f"/api/v1/consents/preferences?user_id={self.applicant1_id}",
            headers=self.headers_adm,
            json={"consent_alerts": True},
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertTrue(patch_resp.json()["consent_alerts"])

        # Admin reads applicant1 preferences
        get_resp = self.client.get(
            f"/api/v1/consents/preferences?user_id={self.applicant1_id}",
            headers=self.headers_adm,
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertTrue(get_resp.json()["consent_alerts"])

    def test_audit_logging_on_preference_changes(self):
        """Preference grants and revocations record structured audit events."""
        # 1. Grant
        self.client.patch(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json={"consent_benchmark": True},
        )
        # 2. Revoke
        self.client.post(
            "/api/v1/consents/preferences/consent_benchmark/revoke",
            headers=self.headers_app1,
        )

        db = self.SessionFactory()
        audit_records = (
            db.query(AuditLog)
            .filter(AuditLog.entity_type == "ConsentPreference")
            .all()
        )
        actions = [r.action for r in audit_records]
        self.assertIn(AuditAction.CONSENT_GRANTED, actions)
        self.assertIn(AuditAction.CONSENT_REVOKED, actions)
        db.close()

    def test_assessment_consent_enforcement_remains_intact(self):
        """Profile DPDP preferences never satisfy assessment consent.

        AssessmentService must continue requiring active application Consent records.
        """
        db = self.SessionFactory()
        app_repo = ApplicationRepository(db)

        # Create application for applicant 1
        application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile1_id,
            requested_loan_amount=Decimal("15000.00"),
            loan_purpose="Equipment",
            preferred_repayment_period=6,
            status=ApplicationStatus.SUBMITTED,
        )
        app_repo.create(application, commit=True)

        # Grant all DPDP profile preferences
        self.client.patch(
            "/api/v1/consents/preferences",
            headers=self.headers_app1,
            json={
                "consent_benchmark": True,
                "consent_realtime": True,
                "consent_alerts": True,
            },
        )

        # Attempt assessment with enforce_consent=True
        from app.assessment.mock import MockAssessmentEngine
        assessment_service = AssessmentService(db=db, engine=MockAssessmentEngine())
        with self.assertRaises(ConsentRequiredError) as ctx:
            assessment_service.assess_application(
                application_id=application.id,
                enforce_consent=True,
            )
        self.assertIn("Active applicant consent is required", str(ctx.exception))

        # Grant application-level data source consent
        consent_service = ConsentService(db=db)
        consent = consent_service.create_consent({
            "application_id": application.id,
            "applicant_profile_id": self.profile1_id,
            "data_source": ConsentDataSource.PLATFORM,
            "purpose": "Credit underwriting assessment",
            "granted": True,
        })
        self.assertTrue(consent.granted)

        # Active consent check now passes
        active_consents = consent_service.get_active_consents(
            application_id=application.id,
            applicant_profile_id=self.profile1_id,
        )
        self.assertEqual(len(active_consents), 1)

        # Revoke application consent
        consent_service.revoke_consent(consent.id)

        # Assessment is blocked again
        with self.assertRaises(ConsentRequiredError) as ctx2:
            assessment_service.assess_application(
                application_id=application.id,
                enforce_consent=True,
            )
        self.assertIn("Active applicant consent is required", str(ctx2.exception))
        db.close()


if __name__ == "__main__":
    unittest.main()
