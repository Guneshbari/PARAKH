"""Test suite for Phase 14A: Operational Alerts (P2-01).

Validates:
- Persistent operational alert lifecycle (OPEN, ACKNOWLEDGED, RESOLVED)
- Operational signal semantics (insufficient data, consent blocked, engine failure, system health)
- Decoupling from ML risk predictions (ordinary risk/low score does NOT create operational alert)
- Deduplication behavior for recurring operational events on the same application
- Metadata sanitization (zero PII, no raw transactions, no demographic fields)
- RBAC protection (Reviewer/Admin allowed, Applicant rejected with 403, unauthenticated with 401)
- API endpoint contracts and filtering
- Confirmation that mockOperationalAlerts is not actively imported in admin dashboard
"""
import uuid
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    Base,
    CreditAssessment,
    ModelVersion,
    OperationalAlert,
    OperationalAlertSeverity,
    OperationalAlertStatus,
    OperationalAlertType,
    RiskLevel,
    User,
    UserRole,
)
from app.schemas.operational_alert import OperationalAlertCreate
from app.services.assessment import AssessmentService
from app.services.operational_alert import OperationalAlertService, sanitize_alert_metadata
from app.assessment.base import AssessmentEngine
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.assessment.exceptions import AssessmentEngineError
from app.services.exceptions import ConsentRequiredError, EntityNotFoundError


class TestPhase14AOperationalAlerts(unittest.TestCase):
    """Exhaustive test suite for Phase 14A operational alert implementation."""

    def setUp(self):
        """Set up in-memory SQLite database, FastAPI TestClient, and base test records."""
        self.db_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.db_engine)
        self.SessionLocal = sessionmaker(bind=self.db_engine, autoflush=False, autocommit=False)
        self.db = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Seed ModelVersion
        self.model_version = ModelVersion(
            id=uuid.uuid4(),
            model_name="VolatilityAwareRiskModel",
            version="1.0.0",
            algorithm="lightgbm",
            is_active=True,
        )
        self.db.add(self.model_version)

        # Seed Users: Admin, Reviewer, Applicant
        self.admin_user = User(
            id=uuid.uuid4(),
            email="admin.alerts@example.com",
            password_hash=hash_password("admin_pass"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.reviewer_user = User(
            id=uuid.uuid4(),
            email="reviewer.alerts@example.com",
            password_hash=hash_password("reviewer_pass"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        self.applicant_user = User(
            id=uuid.uuid4(),
            email="applicant.alerts@example.com",
            password_hash=hash_password("applicant_pass"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        self.db.add_all([self.admin_user, self.reviewer_user, self.applicant_user])
        self.db.commit()

        # Seed Profile & Application
        self.profile = ApplicantProfile(
            id=uuid.uuid4(),
            user_id=self.applicant_user.id,
            gig_work_type="Delivery Partner",
            business_or_loan_purpose="Working Capital",
            years_working=Decimal("2.5"),
            average_working_days=24,
        )
        self.db.add(self.profile)
        self.db.commit()

        self.application = Application(
            id=uuid.uuid4(),
            applicant_profile_id=self.profile.id,
            requested_loan_amount=Decimal("35000.00"),
            loan_purpose="Working Capital",
            status=ApplicationStatus.SUBMITTED,
        )
        self.db.add(self.application)
        self.db.commit()

        # Create JWT Tokens
        self.admin_token = create_access_token(str(self.admin_user.id), role=self.admin_user.role.value)
        self.reviewer_token = create_access_token(str(self.reviewer_user.id), role=self.reviewer_user.role.value)
        self.applicant_token = create_access_token(str(self.applicant_user.id), role=self.applicant_user.role.value)

        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.reviewer_headers = {"Authorization": f"Bearer {self.reviewer_token}"}
        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}

    def tearDown(self):
        """Clean up database session and dependency overrides."""
        self.db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.db_engine)

    def test_create_operational_alert_direct(self):
        """Verify direct operational alert creation and field persistence."""
        service = OperationalAlertService(db=self.db)
        alert_in = OperationalAlertCreate(
            alert_type=OperationalAlertType.SYSTEM_HEALTH,
            severity=OperationalAlertSeverity.CRITICAL,
            title="Model Artifact Unavailable",
            message="Required model artifact file missing on disk.",
            status=OperationalAlertStatus.OPEN,
            application_id=self.application.id,
            alert_metadata={"component": "model_loader"},
        )
        alert = service.create_alert(alert_in)

        self.assertIsNotNone(alert.id)
        self.assertEqual(alert.alert_type, OperationalAlertType.SYSTEM_HEALTH)
        self.assertEqual(alert.severity, OperationalAlertSeverity.CRITICAL)
        self.assertEqual(alert.title, "Model Artifact Unavailable")
        self.assertEqual(alert.status, OperationalAlertStatus.OPEN)
        self.assertEqual(alert.application_id, self.application.id)
        self.assertEqual(alert.alert_metadata, {"component": "model_loader"})
        self.assertIsNotNone(alert.created_at)
        self.assertIsNone(alert.resolved_at)

    def test_deduplication_on_open_alert(self):
        """Verify that multiple alerts for the same app and alert_type update existing instead of duplicating."""
        service = OperationalAlertService(db=self.db)
        alert_in1 = OperationalAlertCreate(
            alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
            severity=OperationalAlertSeverity.WARNING,
            title="Insufficient Data: Attempt 1",
            message="Missing telemetry payout count.",
            status=OperationalAlertStatus.OPEN,
            application_id=self.application.id,
        )
        created1 = service.create_alert(alert_in1, deduplicate=True)

        alert_in2 = OperationalAlertCreate(
            alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
            severity=OperationalAlertSeverity.WARNING,
            title="Insufficient Data: Attempt 2",
            message="Missing telemetry payout count and observed days.",
            status=OperationalAlertStatus.OPEN,
            application_id=self.application.id,
        )
        created2 = service.create_alert(alert_in2, deduplicate=True)

        # Same alert ID updated
        self.assertEqual(created1.id, created2.id)
        self.assertEqual(created2.title, "Insufficient Data: Attempt 2")
        self.assertEqual(created2.message, "Missing telemetry payout count and observed days.")

        # Ensure database count is 1
        all_alerts = service.list_alerts()
        self.assertEqual(len(all_alerts), 1)

    def test_different_alert_types_or_apps_not_deduplicated(self):
        """Verify distinct alert types or applications generate separate alert entries."""
        service = OperationalAlertService(db=self.db)
        service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
                severity=OperationalAlertSeverity.WARNING,
                title="Insufficient Data",
                message="Telemetry sparse.",
                application_id=self.application.id,
            )
        )
        service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.CONSENT_BLOCKED,
                severity=OperationalAlertSeverity.WARNING,
                title="Consent Blocked",
                message="Consent revoked.",
                application_id=self.application.id,
            )
        )
        alerts = service.list_alerts()
        self.assertEqual(len(alerts), 2)

    def test_status_transitions(self):
        """Verify lifecycle status transitions: OPEN -> ACKNOWLEDGED -> RESOLVED."""
        service = OperationalAlertService(db=self.db)
        alert = service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.SYSTEM_HEALTH,
                severity=OperationalAlertSeverity.INFO,
                title="Heartbeat Monitoring",
                message="System monitor active.",
            )
        )
        self.assertEqual(alert.status, OperationalAlertStatus.OPEN)
        self.assertIsNone(alert.resolved_at)

        ack = service.acknowledge_alert(alert.id)
        self.assertEqual(ack.status, OperationalAlertStatus.ACKNOWLEDGED)
        self.assertIsNone(ack.resolved_at)

        res = service.resolve_alert(alert.id)
        self.assertEqual(res.status, OperationalAlertStatus.RESOLVED)
        self.assertIsNotNone(res.resolved_at)

    def test_metadata_sanitization_removes_prohibited_pii(self):
        """Verify sensitive keys (pan, aadhaar, raw_transactions, coordinates, passwords) are purged."""
        raw_metadata = {
            "component": "telemetry_processor",
            "password": "super_secret_cleartext",
            "pan": "ABCDE1234F",
            "aadhaar": "1234-5678-9012",
            "bank_account": "9876543210",
            "raw_transactions": [{"amount": 500, "txn_id": "TXN999"}],
            "coordinates": {"lat": 12.9716, "lng": 77.5946},
            "gender": "M",
            "safe_metric": 42,
        }
        sanitized = sanitize_alert_metadata(raw_metadata)
        self.assertIn("component", sanitized)
        self.assertIn("safe_metric", sanitized)
        self.assertNotIn("password", sanitized)
        self.assertNotIn("pan", sanitized)
        self.assertNotIn("aadhaar", sanitized)
        self.assertNotIn("bank_account", sanitized)
        self.assertNotIn("raw_transactions", sanitized)
        self.assertNotIn("coordinates", sanitized)
        self.assertNotIn("gender", sanitized)

    def test_insufficient_data_alert_triggered_during_assessment(self):
        """Verify assess_application automatically creates an INSUFFICIENT_DATA_REVIEW alert when evidence is insufficient."""
        mock_engine = MagicMock(spec=AssessmentEngine)
        insufficient_result = AssessmentResult(
            score=None,
            risk_probability=None,
            risk_level=RiskLevel.INSUFFICIENT,
            confidence=Decimal("0.0"),
            debt_to_income=None,
            utilization=None,
            income_stability=None,
            repayment_reliability=None,
            model_name="LightGBM_V1",
            model_version="1.0.0",
            key_factors=[],
            explanation={
                "is_insufficient_evidence": True,
                "missing_signals": ["observed_days_below_minimum", "insufficient_payout_count"],
            },
        )
        mock_engine.assess.return_value = insufficient_result

        assessment_service = AssessmentService(
            db=self.db,
            engine=mock_engine,
        )
        assessment = assessment_service.assess_application(
            application_id=self.application.id,
            model_version_id=self.model_version.id,
            enforce_consent=False,
        )

        self.assertEqual(assessment.risk_level, RiskLevel.INSUFFICIENT)

        # Verify operational alert was created
        alert_service = OperationalAlertService(db=self.db)
        alerts = alert_service.list_alerts()
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.alert_type, OperationalAlertType.INSUFFICIENT_DATA_REVIEW)
        self.assertEqual(alert.severity, OperationalAlertSeverity.WARNING)
        self.assertEqual(alert.application_id, self.application.id)
        self.assertEqual(alert.assessment_id, assessment.id)
        self.assertIn("observed_days_below_minimum", alert.alert_metadata["missing_reasons"])

    def test_consent_blocked_alert_triggered_when_consent_missing(self):
        """Verify assess_application creates CONSENT_BLOCKED alert when consent is enforced and missing."""
        mock_engine = MagicMock(spec=AssessmentEngine)
        assessment_service = AssessmentService(
            db=self.db,
            engine=mock_engine,
        )

        with self.assertRaises(ConsentRequiredError):
            assessment_service.assess_application(
                application_id=self.application.id,
                model_version_id=self.model_version.id,
                enforce_consent=True,
            )

        alert_service = OperationalAlertService(db=self.db)
        alerts = alert_service.list_alerts()
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.alert_type, OperationalAlertType.CONSENT_BLOCKED)
        self.assertEqual(alert.severity, OperationalAlertSeverity.WARNING)
        self.assertEqual(alert.application_id, self.application.id)

    def test_assessment_failure_alert_triggered_on_engine_error(self):
        """Verify assess_application creates ASSESSMENT_FAILURE alert when engine fails."""
        mock_engine = MagicMock(spec=AssessmentEngine)
        mock_engine.assess.side_effect = AssessmentEngineError("Feature computation matrix shape mismatch.")

        assessment_service = AssessmentService(
            db=self.db,
            engine=mock_engine,
        )

        with self.assertRaises(AssessmentEngineError):
            assessment_service.assess_application(
                application_id=self.application.id,
                model_version_id=self.model_version.id,
                enforce_consent=False,
            )

        alert_service = OperationalAlertService(db=self.db)
        alerts = alert_service.list_alerts()
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.alert_type, OperationalAlertType.ASSESSMENT_FAILURE)
        self.assertEqual(alert.severity, OperationalAlertSeverity.CRITICAL)
        self.assertEqual(alert.application_id, self.application.id)

    def test_standard_scored_assessment_does_not_trigger_operational_alert(self):
        """Verify that high-risk prediction with sufficient data does NOT create an operational alert (principle: alert != ML prediction)."""
        mock_engine = MagicMock(spec=AssessmentEngine)
        high_risk_result = AssessmentResult(
            score=450,
            risk_probability=Decimal("0.78"),
            risk_level=RiskLevel.HIGHER,
            confidence=Decimal("0.91"),
            debt_to_income=Decimal("0.68"),
            utilization=Decimal("0.85"),
            income_stability=Decimal("0.25"),
            repayment_reliability=Decimal("0.35"),
            model_name="LightGBM_V1",
            model_version="1.0.0",
            key_factors=[],
            explanation={"top_risk_factors": ["debt_to_income", "low_stability"]},
        )
        mock_engine.assess.return_value = high_risk_result

        assessment_service = AssessmentService(
            db=self.db,
            engine=mock_engine,
        )
        assessment = assessment_service.assess_application(
            application_id=self.application.id,
            model_version_id=self.model_version.id,
            enforce_consent=False,
        )

        self.assertEqual(assessment.risk_level, RiskLevel.HIGHER)

        alert_service = OperationalAlertService(db=self.db)
        alerts = alert_service.list_alerts()
        # Ordinary high risk prediction must NOT trigger an operational alert!
        self.assertEqual(len(alerts), 0)

    def test_api_list_alerts_authorized_roles(self):
        """Verify Reviewer and Admin can access GET /api/v1/operational-alerts."""
        service = OperationalAlertService(db=self.db)
        service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.SYSTEM_HEALTH,
                severity=OperationalAlertSeverity.INFO,
                title="Service Status OK",
                message="Telemetry ingestion functioning.",
            )
        )

        # Reviewer access
        rev_res = self.client.get("/api/v1/operational-alerts", headers=self.reviewer_headers)
        self.assertEqual(rev_res.status_code, 200)
        data = rev_res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Service Status OK")

        # Admin access
        admin_res = self.client.get("/api/v1/operational-alerts", headers=self.admin_headers)
        self.assertEqual(admin_res.status_code, 200)

    def test_api_status_filtering(self):
        """Verify status parameter filtering on GET /api/v1/operational-alerts."""
        service = OperationalAlertService(db=self.db)
        a1 = service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
                severity=OperationalAlertSeverity.WARNING,
                title="Alert Open",
                message="Test open.",
                status=OperationalAlertStatus.OPEN,
            )
        )
        a2 = service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.SYSTEM_HEALTH,
                severity=OperationalAlertSeverity.INFO,
                title="Alert Resolved",
                message="Test resolved.",
                status=OperationalAlertStatus.OPEN,
            )
        )
        service.resolve_alert(a2.id)

        # Fetch only OPEN
        res = self.client.get("/api/v1/operational-alerts?status=OPEN", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Alert Open")

        # Fetch only RESOLVED
        res_resolved = self.client.get("/api/v1/operational-alerts?status=RESOLVED", headers=self.reviewer_headers)
        self.assertEqual(res_resolved.status_code, 200)
        resolved_items = res_resolved.json()
        self.assertEqual(len(resolved_items), 1)
        self.assertEqual(resolved_items[0]["title"], "Alert Resolved")

    def test_api_acknowledge_and_resolve_endpoints(self):
        """Verify PATCH /acknowledge and PATCH /resolve endpoints."""
        service = OperationalAlertService(db=self.db)
        alert = service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.INSUFFICIENT_DATA_REVIEW,
                severity=OperationalAlertSeverity.WARNING,
                title="Review Required",
                message="Manual intervention needed.",
            )
        )

        # Acknowledge
        ack_res = self.client.patch(
            f"/api/v1/operational-alerts/{alert.id}/acknowledge",
            headers=self.reviewer_headers,
        )
        self.assertEqual(ack_res.status_code, 200)
        self.assertEqual(ack_res.json()["status"], "ACKNOWLEDGED")

        # Resolve
        resolve_res = self.client.patch(
            f"/api/v1/operational-alerts/{alert.id}/resolve",
            headers=self.reviewer_headers,
        )
        self.assertEqual(resolve_res.status_code, 200)
        self.assertEqual(resolve_res.json()["status"], "RESOLVED")
        self.assertIsNotNone(resolve_res.json()["resolved_at"])

    def test_api_unauthorized_applicant_rejected(self):
        """Verify APPLICANT role is rejected with HTTP 403 Forbidden."""
        res = self.client.get("/api/v1/operational-alerts", headers=self.applicant_headers)
        self.assertEqual(res.status_code, 403)

    def test_api_unauthenticated_rejected(self):
        """Verify unauthenticated requests receive HTTP 401 Unauthorized."""
        res = self.client.get("/api/v1/operational-alerts")
        self.assertEqual(res.status_code, 401)

    def test_api_get_by_id(self):
        """Verify GET /api/v1/operational-alerts/{id} and 404 for missing IDs."""
        service = OperationalAlertService(db=self.db)
        alert = service.create_alert(
            OperationalAlertCreate(
                alert_type=OperationalAlertType.SYSTEM_HEALTH,
                severity=OperationalAlertSeverity.INFO,
                title="Single Alert",
                message="Fetching by ID.",
            )
        )

        res = self.client.get(f"/api/v1/operational-alerts/{alert.id}", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], str(alert.id))

        missing_id = uuid.uuid4()
        res_missing = self.client.get(f"/api/v1/operational-alerts/{missing_id}", headers=self.reviewer_headers)
        self.assertEqual(res_missing.status_code, 404)

    def test_empty_state_returns_empty_list(self):
        """Verify API returns [] when no operational alerts are present."""
        res = self.client.get("/api/v1/operational-alerts", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_frontend_does_not_import_mock_operational_alerts(self):
        """Verify frontend admin dashboard no longer imports or uses mockOperationalAlerts."""
        import os
        dashboard_path = os.path.abspath("frontend/apps/web/app/admin/dashboard/page.tsx")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("mockOperationalAlerts", content)
        self.assertIn("api.getOperationalAlerts", content)
