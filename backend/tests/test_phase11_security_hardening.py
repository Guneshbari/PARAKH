"""Phase 11: Error, Loading & Security Hardening Verification Tests.

Verifies:
1. Protected endpoints enforce authentication (401 Unauthorized).
2. Cross-applicant isolation prevents accessing another applicant's data (403 Forbidden).
3. Reviewer endpoints enforce RBAC clearance (403 Forbidden for applicant role).
4. Malformed request payloads return proper validation errors (422 Unprocessable Entity).
5. Unhandled backend exceptions return sanitized 500 responses without leaking traces or DB errors.
6. Multi-step review and status transitions are transactionally safe and atomic.
7. User passwords use secure bcrypt hashing and are never stored or logged in plaintext.
8. Consent enforcement prevents processing financial signals without active consent.
"""

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.api.errors import register_exception_handlers
from app.core.security import hash_password, verify_password
from app.main import app
from app.models import (
    ApplicationStatus,
    ConsentDataSource,
    ReviewOutcome,
    ReviewOutcomeType,
    UserRole,
)
from app.services.review import ReviewService
from tests.helpers import (
    create_admin_user,
    create_applicant_user,
    create_reviewer_user,
    create_test_applicant_profile,
    create_test_application,
    create_test_consent,
    get_auth_token_and_headers,
    in_memory_db_session,
)


@pytest.fixture
def client_with_db():
    """Yield a TestClient bound to an isolated in-memory SQLite database session."""
    with in_memory_db_session() as session:
        def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client, session
        app.dependency_overrides.clear()


class TestPhase11AuthenticationAndAuthorizationHardening:
    """Tests for authentication enforcement and RBAC isolation."""

    def test_unauthenticated_request_rejected(self, client_with_db):
        """Protected endpoints must reject requests lacking Authorization token with 401."""
        client, session = client_with_db
        resp = client.get("/api/v1/applications")
        assert resp.status_code == 401
        assert "detail" in resp.json()

    def test_cross_applicant_isolation_enforced(self, client_with_db):
        """Applicant A cannot view or access Applicant B's application."""
        client, session = client_with_db
        # Create Applicant A
        user_a = create_applicant_user(session, email="applicant_a@example.com")
        profile_a = create_test_applicant_profile(session, user_id=user_a.id)
        app_a = create_test_application(session, applicant_profile_id=profile_a.id)

        # Create Applicant B
        user_b = create_applicant_user(session, email="applicant_b@example.com")
        profile_b = create_test_applicant_profile(session, user_id=user_b.id)
        app_b = create_test_application(session, applicant_profile_id=profile_b.id)

        # Token for Applicant A
        _, headers_a = get_auth_token_and_headers(user_a.id, role=UserRole.APPLICANT)

        # Applicant A can access App A
        resp_own = client.get(f"/api/v1/applications/{app_a.id}", headers=headers_a)
        assert resp_own.status_code == 200

        # Applicant A CANNOT access App B (must receive 403 Forbidden)
        resp_other = client.get(f"/api/v1/applications/{app_b.id}", headers=headers_a)
        assert resp_other.status_code == 403
        assert "access denied" in resp_other.json()["detail"].lower()

    def test_reviewer_endpoint_enforces_role_rbac(self, client_with_db):
        """Applicant users cannot submit underwriter review outcomes (403 Forbidden)."""
        client, session = client_with_db
        user_applicant = create_applicant_user(session)
        profile = create_test_applicant_profile(session, user_id=user_applicant.id)
        application = create_test_application(session, applicant_profile_id=profile.id)

        _, applicant_headers = get_auth_token_and_headers(user_applicant.id, role=UserRole.APPLICANT)

        # Applicant attempts to call reviewer-only review endpoint
        review_payload = {
            "reviewer_id": str(user_applicant.id),
            "outcome": "REVIEWED",
            "notes": "Unauthorized attempt to finalize review",
        }
        resp = client.post(
            f"/api/v1/applications/{application.id}/reviews",
            json=review_payload,
            headers=applicant_headers,
        )
        assert resp.status_code == 403
        detail_msg = resp.json()["detail"].lower()
        assert (
            "permitted" in detail_msg
            or "permission" in detail_msg
            or "clearance" in detail_msg
            or "authorized" in detail_msg
            or "access denied" in detail_msg
        )


class TestPhase11BackendValidationAndSanitization:
    """Tests for payload validation and error response sanitization."""

    def test_malformed_payload_validation_response(self, client_with_db):
        """Malformed or schema-violating request body returns 422 Unprocessable Entity."""
        client, session = client_with_db
        user = create_applicant_user(session)
        _, headers = get_auth_token_and_headers(user.id, role=UserRole.APPLICANT)

        # Negative requested loan amount or missing fields
        invalid_payload = {
            "requested_loan_amount": -1000,
            "loan_purpose": "",
            "preferred_repayment_period": 0,
        }
        resp = client.post("/api/v1/applications", json=invalid_payload, headers=headers)
        assert resp.status_code == 422
        assert "detail" in resp.json()

    def test_unhandled_exception_sanitization(self, client_with_db):
        """Unhandled exceptions return sanitized 500 without leaking stack traces or internal DB details."""
        client, session = client_with_db
        user = create_reviewer_user(session)
        _, headers = get_auth_token_and_headers(user.id, role=UserRole.REVIEWER)

        # Mock an unexpected runtime crash inside a service call
        with patch.object(ReviewService, "create_review", side_effect=RuntimeError("CRITICAL_INTERNAL_DB_CRASH_SECRET_TRACE")):
            profile = create_test_applicant_profile(session, user_id=user.id)
            application = create_test_application(session, applicant_profile_id=profile.id)

            resp = client.post(
                f"/api/v1/applications/{application.id}/reviews",
                json={"reviewer_id": str(user.id), "outcome": "REVIEWED", "notes": "Test notes for review"},
                headers=headers,
            )
            assert resp.status_code == 500
            data = resp.json()
            # Verify the response does NOT leak internal exception message or stack trace
            assert "CRITICAL_INTERNAL_DB_CRASH_SECRET_TRACE" not in str(data)
            assert data.get("detail") == "An internal server error occurred. Please try again later."


class TestPhase11PasswordAndConsentSecurity:
    """Tests for password hashing and consent enforcement."""

    def test_passwords_are_never_plaintext(self, client_with_db):
        """User passwords must be securely hashed via bcrypt and never stored plaintext."""
        _, session = client_with_db
        raw_pw = "SecureP@ssw0rd2026!"
        user = create_applicant_user(session, password=raw_pw)

        # Check DB row directly
        assert user.password_hash != raw_pw
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
        assert verify_password(raw_pw, user.password_hash) is True
        assert verify_password("WrongPassword!", user.password_hash) is False

    def test_consent_enforcement_on_financial_signals(self, client_with_db):
        """Financial signal ingestion requires explicit consent when enforce_consent is requested."""
        client, session = client_with_db
        user = create_applicant_user(session)
        profile = create_test_applicant_profile(session, user_id=user.id)
        application = create_test_application(session, applicant_profile_id=profile.id)

        _, headers = get_auth_token_and_headers(user.id, role=UserRole.APPLICANT)

        # Attempt to insert financial signals before consent is granted
        signal_payload = {
            "source": "PLATFORM",
            "source_id": "swiggy_tx_001",
            "amount": "1250.00",
            "raw_payload": {"trips": 12, "settlement": 1250.00},
        }
        resp = client.post(
            f"/api/v1/applications/{application.id}/financial-signals?enforce_consent=true",
            json=signal_payload,
            headers=headers,
        )
        assert resp.status_code in (400, 403)
        assert "consent" in resp.json()["detail"].lower()


class TestPhase11TransactionRollbackSafety:
    """Tests for multi-step transaction rollback consistency."""

    def test_review_failure_rolls_back_atomically(self, client_with_db):
        """ReviewOutcome, application status transition, and audit log must be atomic."""
        _, session = client_with_db
        user = create_reviewer_user(session)
        profile = create_test_applicant_profile(session, user_id=user.id)
        application = create_test_application(
            session,
            applicant_profile_id=profile.id,
            status=ApplicationStatus.MANUAL_REVIEW,
        )

        review_service = ReviewService(db=session)

        # Simulate update status failure during review creation
        with patch.object(review_service.app_repo, "update_status", side_effect=RuntimeError("Simulated database failure during status update")):
            with pytest.raises(RuntimeError):
                review_service.create_review({
                    "application_id": application.id,
                    "reviewer_id": user.id,
                    "outcome": ReviewOutcomeType.REVIEWED,
                    "notes": "Decision notes for review that should roll back completely",
                })

        # Verify review was rolled back and NOT persisted
        review_count = session.query(ReviewOutcome).filter_by(application_id=application.id).count()
        assert review_count == 0

        # Verify application status was NOT permanently changed
        session.expire_all()
        refreshed_app = session.query(application.__class__).filter_by(id=application.id).one()
        assert refreshed_app.status == ApplicationStatus.MANUAL_REVIEW
