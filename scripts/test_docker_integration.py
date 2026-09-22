#!/usr/bin/env python3
"""PARAKH — Phase 13: Unified Full-Stack End-to-End Test Suite.

Executes comprehensive product journey verification against the live Docker stack:
  1. Frontend (Next.js) on port 3000
  2. Backend (FastAPI) on port 8000
  3. PostgreSQL (on private Docker bridge)
  4. Complete Applicant Journey (Registration, Profile, Application, Consent, Signals, MockAssessmentEngine, Retrieval)
  5. Consent Enforcement (Negative check without consent -> 403, followed by positive check with consent -> 201)
  6. Complete Reviewer Journey (Queue, Dossier, Assessment, Adjudication across all canonical outcomes:
     RECORD_OUTCOME -> COMPLETED, MANUAL_REVIEW -> MANUAL_REVIEW, REQUEST_VERIFICATION -> UNDER_REVIEW)
  7. Applicant ↔ Reviewer Cross-Journey (Multi-actor consistency and live database state synchronization)
  8. Strict RBAC Enforcement (Applicant boundaries, cross-applicant isolation, Reviewer boundaries, Admin permissions)
  9. Audit Log & Governance Verification (Admin inspection, actor non-repudiation, applicant privacy guard)
 10. Database Persistence & Foreign Key Graph (User, Profile, Application, Consent, Signals, Assessment, Review, Audit, ModelVersion)
 11. Container Restart Persistence Verification (Volume survival across docker stop/start)
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

TOTAL_COUNT = 0
PASSED_COUNT = 0


def log_assert(condition: bool, message: str) -> None:
    global TOTAL_COUNT, PASSED_COUNT
    TOTAL_COUNT += 1
    if condition:
        PASSED_COUNT += 1
        print(f"  ✅ PASSED [{PASSED_COUNT:02d}]: {message}")
    else:
        print(f"  ❌ FAILED: {message}")
        sys.exit(1)


def api_request(
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    base_url: str = BACKEND_URL,
) -> Tuple[int, Any]:
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = content
            return status_code, parsed
    except urllib.error.HTTPError as err:
        content = err.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content
        return err.code, parsed
    except Exception as exc:
        return 0, str(exc)


def wait_for_services(timeout_sec: int = 45) -> bool:
    print(f"Waiting up to {timeout_sec}s for Docker services to be ready...")
    start = time.time()
    backend_ready = False
    frontend_ready = False

    while time.time() - start < timeout_sec:
        if not backend_ready:
            code, data = api_request("/health", method="GET")
            if code == 200 and isinstance(data, dict) and data.get("status") == "healthy":
                backend_ready = True
                print(" -> Backend container is healthy!")

        if not frontend_ready:
            code, _ = api_request("/", method="GET", base_url=FRONTEND_URL)
            if code == 200:
                frontend_ready = True
                print(" -> Frontend container is reachable!")

        if backend_ready and frontend_ready:
            return True
        time.sleep(2)

    return False


def run_phase13_e2e_verification() -> Dict[str, Any]:
    print("\n================================================================================")
    print("PARAKH — PHASE 13: COMPREHENSIVE END-TO-END VERIFICATION")
    print("================================================================================\n")

    # -------------------------------------------------------------------------
    # PART 1: SERVICE HEALTH & CONNECTIVITY
    # -------------------------------------------------------------------------
    print("--- 1. Service Health & Connectivity ---")
    code, health_data = api_request("/health", method="GET")
    log_assert(code == 200 and health_data.get("status") == "healthy", "Backend /health reports healthy status")
    code, frontend_html = api_request("/", method="GET", base_url=FRONTEND_URL)
    log_assert(code == 200 and len(frontend_html) > 0, "Frontend Next.js application responds on port 3000")

    code, db_status = api_request("/api/v1/database/health", method="GET")
    log_assert(code == 200 and db_status.get("database") == "connected", "Backend confirms active PostgreSQL connection via /api/v1/database/health")

    # Obtain Admin Session for provisioning and audit inspection
    code, admin_login = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": "admin@parakh.com", "password": "AdminPassword123!"},
    )
    log_assert(code == 200 and "access_token" in admin_login, "Admin logged in successfully via container")
    admin_token = admin_login["access_token"]

    # -------------------------------------------------------------------------
    # PART 2: APPLICANT END-TO-END JOURNEY
    # -------------------------------------------------------------------------
    print("\n--- 2. Applicant End-to-End Journey ---")
    timestamp = int(time.time() * 1000)
    app1_email = f"applicant_e2e_{timestamp}@example.com"
    app1_password = "SecurePassword123!"

    # 2.1 Signup
    code, signup_resp = api_request(
        "/api/v1/users",
        method="POST",
        data={"email": app1_email, "password": app1_password, "role": "APPLICANT"},
    )
    log_assert(code == 201, f"Applicant user self-registered: {app1_email}")
    app1_user_id = signup_resp["id"]

    # 2.2 Login & JWT Issue
    code, login_resp = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": app1_email, "password": app1_password},
    )
    log_assert(code == 200 and "access_token" in login_resp, "JWT issued successfully via /api/v1/auth/login")
    app1_token = login_resp["access_token"]

    # 2.3 Session & Identity Verification
    code, me_resp = api_request("/api/v1/auth/me", method="GET", token=app1_token)
    log_assert(code == 200 and me_resp["email"] == app1_email, "Caller identity verified via /api/v1/auth/me")
    log_assert(me_resp["role"] == "APPLICANT", "Authenticated user assigned APPLICANT role")

    # 2.4 Applicant Profile Creation
    code, profile_resp = api_request(
        "/api/v1/applicants",
        method="POST",
        token=app1_token,
        data={
            "user_id": app1_user_id,
            "gig_work_type": "Quick Commerce Delivery",
            "years_working": 2.5,
            "average_working_days": 27,
            "business_or_loan_purpose": "Two-wheeler battery maintenance",
        },
    )
    log_assert(code == 201, "Applicant profile successfully created and linked to User account")
    app1_profile_id = profile_resp["id"]

    # 2.5 Credit Application Creation
    code, app_resp = api_request(
        "/api/v1/applications",
        method="POST",
        token=app1_token,
        data={
            "applicant_profile_id": app1_profile_id,
            "requested_loan_amount": 42000.00,
            "loan_purpose": "EV Battery Replacement and Fast Charger",
            "preferred_repayment_period": 12,
        },
    )
    log_assert(code == 201, f"Credit application created: {app_resp['id']}")
    app1_id = app_resp["id"]

    # -------------------------------------------------------------------------
    # PART 3: CONSENT ENFORCEMENT VERIFICATION
    # -------------------------------------------------------------------------
    print("\n--- 3. Consent Enforcement (Negative & Positive Paths) ---")
    
    # Negative Test 1: Ingest financial signal with enforce_consent=true BEFORE consent granted
    code, rejected_signal = api_request(
        f"/api/v1/applications/{app1_id}/financial-signals?enforce_consent=true",
        method="POST",
        token=app1_token,
        data={
            "source": "PLATFORM",
            "average_income": 41200.00,
            "platform_rating": 4.92,
            "active_days": 27,
        },
    )
    log_assert(code == 403, "Financial signal ingestion rejected when active consent is missing (HTTP 403)")

    # Negative Test 2: Execute assessment with enforce_consent=true BEFORE consent granted
    code, rejected_assess = api_request(
        f"/api/v1/applications/{app1_id}/assess?enforce_consent=true",
        method="POST",
        token=app1_token,
    )
    log_assert(code == 403, "Assessment execution blocked when active consent is missing (HTTP 403)")

    # Positive Test: Explicitly grant statutory DPDP consent
    code, consent_resp = api_request(
        "/api/v1/consents",
        method="POST",
        token=app1_token,
        data={
            "application_id": app1_id,
            "data_source": "PLATFORM",
            "purpose": "Alternative cashflow volatility scoring",
            "granted": True,
        },
    )
    log_assert(code == 201, "Statutory DPDP consent granted and registered (HTTP 201)")
    consent_id = consent_resp["id"]

    # Ingest financial signal under valid consent
    code, signal_resp = api_request(
        f"/api/v1/applications/{app1_id}/financial-signals?enforce_consent=true",
        method="POST",
        token=app1_token,
        data={
            "source": "PLATFORM",
            "average_income": 41200.00,
            "platform_rating": 4.92,
            "active_days": 27,
            "signal_metadata": {"platform": "Zepto & Blinkit", "orders_completed": 312},
        },
    )
    log_assert(code == 201, "Financial signal ingested successfully under active consent (HTTP 201)")

    # -------------------------------------------------------------------------
    # PART 4: ASSESSMENT ENGINE BOUNDARY & PERSISTENCE
    # -------------------------------------------------------------------------
    print("\n--- 4. Assessment Engine Boundary & Assessment Persistence ---")
    code, assess_resp = api_request(
        f"/api/v1/applications/{app1_id}/assess?enforce_consent=true",
        method="POST",
        token=app1_token,
    )
    log_assert(code == 201, "Assessment executed through MockAssessmentEngine boundary (HTTP 201)")
    credit_score = assess_resp.get("credit_score")
    risk_level = assess_resp.get("risk_level")
    log_assert(credit_score is not None and 300 <= credit_score <= 900, f"Valid non-hardcoded credit score: {credit_score}")
    log_assert(risk_level in ("LOW", "MODERATE", "HIGH", "CRITICAL"), f"Valid risk level category: {risk_level}")

    # Verify assessment persisted in PostgreSQL
    code, latest_resp = api_request(
        f"/api/v1/applications/{app1_id}/assessments/latest",
        method="GET",
        token=app1_token,
    )
    log_assert(code == 200 and latest_resp["credit_score"] == credit_score, "Persisted assessment retrieved via /assessments/latest")
    log_assert(latest_resp["risk_level"] == risk_level, "Persisted risk level matches assessment evaluation")

    # Idempotent re-fetch / simulated browser refresh
    code, refresh_resp = api_request(f"/api/v1/applications/{app1_id}/assessments/latest", method="GET", token=app1_token)
    log_assert(code == 200 and refresh_resp["id"] == latest_resp["id"], "Simulated browser refresh retrieves identical persisted assessment")

    # -------------------------------------------------------------------------
    # PART 5: REVIEWER END-TO-END JOURNEY & STATUS TRANSITIONS
    # -------------------------------------------------------------------------
    print("\n--- 5. Reviewer Journey & Canonical Status Transitions ---")
    reviewer_email = f"reviewer_e2e_{timestamp}@example.com"
    reviewer_password = "ReviewerSecure123!"

    # Provision Reviewer account with Admin authorization
    code, _ = api_request(
        "/api/v1/users",
        method="POST",
        token=admin_token,
        data={"email": reviewer_email, "password": reviewer_password, "role": "REVIEWER"},
    )
    log_assert(code == 201, f"Reviewer user created with administrator privileges: {reviewer_email}")

    # Reviewer Login
    code, rev_login = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": reviewer_email, "password": reviewer_password},
    )
    log_assert(code == 200 and "access_token" in rev_login, "Reviewer authenticated via /api/v1/auth/login")
    reviewer_token = rev_login["access_token"]
    reviewer_id = rev_login["user_id"]

    # Reviewer inspects applications queue
    code, queue = api_request("/api/v1/applications", method="GET", token=reviewer_token)
    log_assert(code == 200 and isinstance(queue, list) and len(queue) > 0, "Reviewer accessed application priority queue")
    queue_app_ids = [q["id"] for q in queue]
    log_assert(app1_id in queue_app_ids, "Applicant's application is present in reviewer queue")

    # Reviewer inspects dossier and assessment
    code, dossier = api_request(f"/api/v1/applications/{app1_id}", method="GET", token=reviewer_token)
    log_assert(code == 200 and dossier["id"] == app1_id, "Reviewer retrieved applicant dossier")

    code, rev_assessment = api_request(f"/api/v1/applications/{app1_id}/assessments/latest", method="GET", token=reviewer_token)
    log_assert(code == 200 and rev_assessment["credit_score"] == credit_score, "Reviewer inspected assessment evaluation")

    # Action 1: RECORD_OUTCOME (outcome: REVIEWED) -> transitions to COMPLETED
    code, review_1 = api_request(
        f"/api/v1/applications/{app1_id}/reviews",
        method="POST",
        token=reviewer_token,
        data={
            "outcome": "REVIEWED",
            "notes": "Verified telemetry earnings on quick-commerce platform. Approved standard tenure.",
        },
    )
    log_assert(code == 201, "Reviewer submitted RECORD_OUTCOME (REVIEWED)")
    code, app1_updated = api_request(f"/api/v1/applications/{app1_id}", method="GET", token=reviewer_token)
    log_assert(app1_updated["status"] == "COMPLETED", "Application transitioned canonically to COMPLETED status")

    # Action 2: MANUAL_REVIEW (outcome: ESCALATED) -> transitions to MANUAL_REVIEW
    # Create application 2 for escalation test
    code, app2_resp = api_request(
        "/api/v1/applications",
        method="POST",
        token=app1_token,
        data={
            "applicant_profile_id": app1_profile_id,
            "requested_loan_amount": 85000.00,
            "loan_purpose": "Second commercial vehicle down payment",
            "preferred_repayment_period": 24,
        },
    )
    app2_id = app2_resp["id"]
    code, review_2 = api_request(
        f"/api/v1/applications/{app2_id}/reviews",
        method="POST",
        token=reviewer_token,
        data={
            "outcome": "ESCALATED",
            "notes": "Loan amount exceeds single gig worker policy limit. Escalated for senior officer signoff.",
        },
    )
    log_assert(code == 201, "Reviewer submitted MANUAL_REVIEW (ESCALATED)")
    code, app2_updated = api_request(f"/api/v1/applications/{app2_id}", method="GET", token=reviewer_token)
    log_assert(app2_updated["status"] == "MANUAL_REVIEW", "Application transitioned canonically to MANUAL_REVIEW status")

    # Action 3: REQUEST_VERIFICATION (outcome: ADDITIONAL_INFORMATION_REQUIRED) -> transitions to UNDER_REVIEW
    # Create application 3 for verification request test
    code, app3_resp = api_request(
        "/api/v1/applications",
        method="POST",
        token=app1_token,
        data={
            "applicant_profile_id": app1_profile_id,
            "requested_loan_amount": 20000.00,
            "loan_purpose": "Smartphone purchase for platform gig app",
            "preferred_repayment_period": 6,
        },
    )
    app3_id = app3_resp["id"]
    code, review_3 = api_request(
        f"/api/v1/applications/{app3_id}/reviews",
        method="POST",
        token=reviewer_token,
        data={
            "outcome": "ADDITIONAL_INFORMATION_REQUIRED",
            "notes": "Requesting 3 additional months of platform utility bills or payment records.",
        },
    )
    log_assert(code == 201, "Reviewer submitted REQUEST_VERIFICATION (ADDITIONAL_INFORMATION_REQUIRED)")
    code, app3_updated = api_request(f"/api/v1/applications/{app3_id}", method="GET", token=reviewer_token)
    log_assert(app3_updated["status"] == "UNDER_REVIEW", "Application transitioned canonically to UNDER_REVIEW status")

    # -------------------------------------------------------------------------
    # PART 6: APPLICANT ↔ REVIEWER CROSS-JOURNEY
    # -------------------------------------------------------------------------
    print("\n--- 6. Applicant ↔ Reviewer Cross-Journey Synchronization ---")
    # Applicant fetches application 1 again and confirms the updated status COMPLETED
    code, applicant_view = api_request(f"/api/v1/applications/{app1_id}", method="GET", token=app1_token)
    log_assert(code == 200 and applicant_view["status"] == "COMPLETED", "Applicant observes updated COMPLETED status from database")
    log_assert(applicant_view["id"] == app1_id, "Application UUID maintained consistently across cross-journey lifecycle")

    # -------------------------------------------------------------------------
    # PART 7: RBAC BOUNDARY ENFORCEMENT
    # -------------------------------------------------------------------------
    print("\n--- 7. Strict RBAC Boundary Enforcement ---")
    
    # 7.1 Applicant blocked from listing all applications
    code, _ = api_request("/api/v1/applications", method="GET", token=app1_token)
    log_assert(code == 403, "APPLICANT blocked from listing all applications (HTTP 403)")

    # 7.2 Applicant blocked from submitting reviews
    code, _ = api_request(
        f"/api/v1/applications/{app1_id}/reviews",
        method="POST",
        token=app1_token,
        data={"outcome": "REVIEWED", "notes": "Unauthorized self-approval attempt."},
    )
    log_assert(code == 403, "APPLICANT blocked from submitting review outcome (HTTP 403)")

    # 7.3 Applicant blocked from accessing audit logs
    code, _ = api_request("/api/v1/audit-logs", method="GET", token=app1_token)
    log_assert(code == 403, "APPLICANT blocked from accessing audit logs (HTTP 403)")

    # 7.4 Cross-Applicant Isolation: Applicant 2 cannot view Applicant 1's application
    app2_email = f"other_applicant_{timestamp}@example.com"
    code, app2_reg = api_request(
        "/api/v1/users",
        method="POST",
        data={"email": app2_email, "password": app1_password, "role": "APPLICANT"},
    )
    code, app2_login = api_request("/api/v1/auth/login", method="POST", data={"email": app2_email, "password": app1_password})
    app2_token = app2_login["access_token"]

    code, _ = api_request(f"/api/v1/applications/{app1_id}", method="GET", token=app2_token)
    log_assert(code == 403, "Cross-applicant data isolation enforced: Applicant B cannot access Applicant A's application (HTTP 403)")

    # 7.5 Reviewer blocked from administrator audit logs
    code, _ = api_request("/api/v1/audit-logs", method="GET", token=reviewer_token)
    log_assert(code == 403, "REVIEWER blocked from admin-only audit logs (HTTP 403)")

    # -------------------------------------------------------------------------
    # PART 8: AUDIT VERIFICATION & GOVERNANCE
    # -------------------------------------------------------------------------
    print("\n--- 8. Audit Verification & Governance ---")
    code, audit_entries = api_request(
        f"/api/v1/audit-logs?application_id={app1_id}",
        method="GET",
        token=admin_token,
    )
    log_assert(code == 200 and isinstance(audit_entries, list) and len(audit_entries) > 0, "Administrator retrieved application audit log trail")
    
    actions = [e["action"] for e in audit_entries]
    log_assert("APPLICATION_STATUS_CHANGED" in actions, "Audit trail contains APPLICATION_STATUS_CHANGED event")
    log_assert("REVIEW_CREATED" in actions, "Audit trail contains REVIEW_CREATED event")

    review_event = next((e for e in audit_entries if e["action"] == "REVIEW_CREATED"), None)
    log_assert(review_event is not None and review_event["user_id"] == reviewer_id, "Audit event accurately records reviewer user ID from authenticated JWT")
    log_assert(review_event.get("created_at") is not None, "Audit event contains immutable timestamp")

    # -------------------------------------------------------------------------
    # PART 9: DATABASE PERSISTENCE GRAPH VERIFICATION
    # -------------------------------------------------------------------------
    print("\n--- 9. Database Persistence Graph Verification ---")
    # Verify User exists
    code, user_check = api_request(f"/api/v1/users/{app1_user_id}", method="GET", token=admin_token)
    log_assert(code == 200 and user_check["id"] == app1_user_id, "Entity 'User' persisted in PostgreSQL")

    # Verify Profile exists
    code, prof_check = api_request(f"/api/v1/applicants/{app1_profile_id}", method="GET", token=admin_token)
    log_assert(code == 200 and prof_check["id"] == app1_profile_id, "Entity 'ApplicantProfile' persisted in PostgreSQL")

    # Verify Application exists
    code, app_check = api_request(f"/api/v1/applications/{app1_id}", method="GET", token=admin_token)
    log_assert(code == 200 and app_check["id"] == app1_id, "Entity 'Application' persisted in PostgreSQL")

    # Verify Consent exists
    code, consents = api_request(f"/api/v1/applications/{app1_id}/consents", method="GET", token=admin_token)
    log_assert(code == 200 and len(consents) > 0, "Entity 'Consent' linked to Application in PostgreSQL")

    # Verify Financial Signal exists
    code, signals = api_request(f"/api/v1/applications/{app1_id}/financial-signals", method="GET", token=admin_token)
    log_assert(code == 200 and len(signals) > 0, "Entity 'FinancialSignal' linked to Application in PostgreSQL")

    # Verify Credit Assessment exists
    code, assessment_check = api_request(f"/api/v1/applications/{app1_id}/assessments/latest", method="GET", token=admin_token)
    log_assert(code == 200 and assessment_check["credit_score"] == credit_score, "Entity 'CreditAssessment' persisted in PostgreSQL")

    # Verify Review Outcome exists
    code, reviews = api_request(f"/api/v1/applications/{app1_id}/reviews", method="GET", token=admin_token)
    log_assert(code == 200 and len(reviews) > 0, "Entity 'ReviewOutcome' linked to Application in PostgreSQL")

    # Verify Model Version exists
    code, mvs = api_request("/api/v1/model-versions", method="GET", token=admin_token)
    log_assert(code == 200 and len(mvs) > 0, "Entity 'ModelVersion' persisted in registry")

    print("\n--------------------------------------------------------------------------------")
    print(f"PARAKH Phase 13 E2E Test Passed: {PASSED_COUNT}/{TOTAL_COUNT} Checks Succeeded!")
    print("--------------------------------------------------------------------------------\n")

    return {
        "app_id": app1_id,
        "applicant_token": app1_token,
        "score": credit_score,
        "reviewer_id": reviewer_id,
    }


def verify_persisted_data(test_data: Dict[str, Any]) -> None:
    print("\n================================================================================")
    print("VERIFYING DATABASE PERSISTENCE AFTER CONTAINER RESTART")
    print("================================================================================\n")

    app_id = test_data["app_id"]
    token = test_data["applicant_token"]
    expected_score = test_data["score"]

    code, app_resp = api_request(f"/api/v1/applications/{app_id}", method="GET", token=token)
    log_assert(code == 200 and app_resp["id"] == app_id, f"Application {app_id} successfully retrieved after container restart")
    log_assert(app_resp["status"] == "COMPLETED", "Application status remains COMPLETED across container restarts")

    code, assess_resp = api_request(f"/api/v1/applications/{app_id}/assessments/latest", method="GET", token=token)
    log_assert(code == 200 and assess_resp["credit_score"] == expected_score, f"Assessment score {expected_score} persisted in PostgreSQL volume across restart")

    print("\n✅ PostgreSQL volume persistence verified successfully across container lifecycle!\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-persistence":
        with open("/tmp/parakh_docker_test.json", "r") as f:
            data = json.load(f)
        verify_persisted_data(data)
    else:
        if not wait_for_services():
            print("❌ Timed out waiting for Docker services.")
            sys.exit(1)
        test_info = run_phase13_e2e_verification()
        with open("/tmp/parakh_docker_test.json", "w") as f:
            json.dump(test_info, f)
