#!/usr/bin/env python3
"""PARAKH Full-Stack Docker Integration Test.

Verifies end-to-end functionality across Docker containers:
  - Frontend (Next.js) on port 3000
  - Backend (FastAPI) on port 8000
  - PostgreSQL (private on Docker network)
  - MockAssessmentEngine boundary execution
  - Statutory Consent and Financial Signal Ingestion
  - Reviewer RBAC and Decision Workflow
  - Database Volume Persistence across Container Restarts
"""

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
import jwt

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"
SECRET_KEY = "parakh-super-secret-key-change-in-production-0987654321"
ALGORITHM = "HS256"

TOTAL_COUNT = 0
PASSED_COUNT = 0


def log_assert(condition: bool, message: str) -> None:
    global TOTAL_COUNT, PASSED_COUNT
    TOTAL_COUNT += 1
    if condition:
        PASSED_COUNT += 1
        print(f"✅ PASSED: {message}")
    else:
        print(f"❌ FAILED: {message}")
        sys.exit(1)


def create_admin_jwt() -> str:
    """Generate a signed administrative JWT for provisioning."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "role": "ADMIN",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


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


def run_full_stack_verification() -> Dict[str, Any]:
    print("\n==================================================")
    print("RUNNING PARAKH FULL-STACK DOCKER INTEGRATION TEST")
    print("==================================================\n")

    # 1. Health Checks
    code, health_data = api_request("/health", method="GET")
    log_assert(code == 200 and health_data.get("status") == "healthy", "Backend /health reports healthy status")

    code, frontend_html = api_request("/", method="GET", base_url=FRONTEND_URL)
    log_assert(code == 200 and len(frontend_html) > 0, "Frontend / is reachable on port 3000")

    # 2. Database connectivity check via API status
    code, db_status = api_request("/api/v1/database/health", method="GET")
    log_assert(code == 200, "Backend can query PostgreSQL database successfully")

    # 3. User Authentication
    test_email = f"docker_applicant_{int(time.time())}@example.com"
    test_password = "SecurePassword123!"

    # Signup new applicant via /api/v1/users
    code, signup_resp = api_request(
        "/api/v1/users",
        method="POST",
        data={"email": test_email, "password": test_password, "role": "APPLICANT"},
    )
    log_assert(code == 201, f"Applicant user registered via container: {test_email}")
    user_id = signup_resp["id"]

    # Login and obtain JWT
    code, login_resp = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": test_email, "password": test_password},
    )
    log_assert(code == 200 and "access_token" in login_resp, "JWT issued successfully via /api/v1/auth/login")
    token = login_resp["access_token"]

    # Verify session identity
    code, me_resp = api_request("/api/v1/auth/me", method="GET", token=token)
    log_assert(code == 200 and me_resp["email"] == test_email, "Session identity confirmed via /api/v1/auth/me")

    # 4. Create Applicant Profile
    code, profile_resp = api_request(
        "/api/v1/applicants",
        method="POST",
        token=token,
        data={
            "user_id": user_id,
            "gig_work_type": "Food Delivery",
            "years_working": 2.0,
            "average_working_days": 26,
            "business_or_loan_purpose": "Battery replacement",
        },
    )
    log_assert(code == 201, "Applicant profile created successfully")
    profile_id = profile_resp["id"]

    # 5. Create Credit Application
    code, app_resp = api_request(
        "/api/v1/applications",
        method="POST",
        token=token,
        data={
            "applicant_profile_id": profile_id,
            "requested_loan_amount": 35000.00,
            "loan_purpose": "Electric two-wheeler battery replacement",
            "preferred_repayment_period": 12,
        },
    )
    log_assert(code == 201, f"Credit application created: {app_resp['id']}")
    app_id = app_resp["id"]

    # 6. Statutory Consent Registration
    code, consent_resp = api_request(
        "/api/v1/consents",
        method="POST",
        token=token,
        data={
            "application_id": app_id,
            "data_source": "PLATFORM",
            "purpose": "Alternative cashflow volatility assessment",
            "granted": True,
        },
    )
    log_assert(code == 201, "Statutory DPDP consent registered")

    # 7. Financial Signal Ingestion
    code, signal_resp = api_request(
        f"/api/v1/applications/{app_id}/financial-signals",
        method="POST",
        token=token,
        data={
            "source": "PLATFORM",
            "average_income": 38500.00,
            "platform_rating": 4.88,
            "active_days": 26,
        },
    )
    log_assert(code == 201, "Financial signal telemetry ingested under consent")

    # 8. Assessment Execution (invoking MockAssessmentEngine via boundary)
    code, assess_resp = api_request(
        f"/api/v1/applications/{app_id}/assess",
        method="POST",
        token=token,
    )
    log_assert(code == 201, "Assessment executed via MockAssessmentEngine")
    score = assess_resp.get("credit_score")
    risk_level = assess_resp.get("risk_level")
    log_assert(score is not None and score >= 300, f"Valid credit score computed: {score}")
    log_assert(risk_level is not None, f"Risk level computed: {risk_level}")

    # 9. Verify Assessment Persistence in PostgreSQL
    code, latest_resp = api_request(
        f"/api/v1/applications/{app_id}/assessments/latest",
        method="GET",
        token=token,
    )
    log_assert(code == 200 and latest_resp["credit_score"] == score, "Assessment persisted in PostgreSQL and retrievable")

    # 10. Reviewer Workflow & RBAC
    code, admin_login = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": "admin@parakh.com", "password": "AdminPassword123!"},
    )
    log_assert(code == 200 and "access_token" in admin_login, "Admin logged in successfully via container")
    admin_token = admin_login["access_token"]

    reviewer_email = f"docker_reviewer_{int(time.time())}@example.com"
    code, _ = api_request(
        "/api/v1/users",
        method="POST",
        token=admin_token,
        data={"email": reviewer_email, "password": test_password, "role": "REVIEWER"},
    )
    log_assert(code == 201, "Reviewer user created with administrator authorization")

    code, rev_login = api_request(
        "/api/v1/auth/login",
        method="POST",
        data={"email": reviewer_email, "password": test_password},
    )
    log_assert(code == 200 and "access_token" in rev_login, "Reviewer logged in successfully")
    reviewer_token = rev_login["access_token"]
    reviewer_user_id = rev_login.get("user", {}).get("id")

    # Reviewer inspects applications queue
    code, queue_resp = api_request("/api/v1/applications", method="GET", token=reviewer_token)
    log_assert(code == 200 and len(queue_resp) > 0, "Reviewer can access applications queue")

    # Reviewer submits review outcome
    code, review_resp = api_request(
        f"/api/v1/applications/{app_id}/reviews",
        method="POST",
        token=reviewer_token,
        data={
            "reviewer_id": reviewer_user_id,
            "outcome": "REVIEWED",
            "notes": "Verified verified GSTIN and steady delivery earnings across Swiggy.",
        },
    )
    log_assert(code == 201, "Reviewer recorded adjudication outcome (REVIEWED)")

    # 11. Applicant sees updated status
    code, updated_app = api_request(f"/api/v1/applications/{app_id}", method="GET", token=token)
    log_assert(code == 200 and updated_app["status"] == "COMPLETED", "Application status updated to COMPLETED")

    print("\n--------------------------------------------------")
    print(f"Full-Stack Smoke Test Passed: {PASSED_COUNT}/{TOTAL_COUNT} Checks Succeeded!")
    print("--------------------------------------------------\n")

    return {
        "app_id": app_id,
        "token": token,
        "score": score,
        "applicant_email": test_email,
    }


def verify_persisted_data(test_data: Dict[str, Any]) -> None:
    print("\n==================================================")
    print("VERIFYING DATABASE PERSISTENCE AFTER RESTART")
    print("==================================================")

    app_id = test_data["app_id"]
    token = test_data["token"]
    expected_score = test_data["score"]

    code, app_resp = api_request(f"/api/v1/applications/{app_id}", method="GET", token=token)
    log_assert(code == 200 and app_resp["id"] == app_id, f"Application {app_id} retrieved after container restart")
    log_assert(app_resp["status"] == "COMPLETED", "Application status remains COMPLETED after restart")

    code, assess_resp = api_request(f"/api/v1/applications/{app_id}/assessments/latest", method="GET", token=token)
    log_assert(code == 200 and assess_resp["credit_score"] == expected_score, f"Assessment score {expected_score} persisted in PostgreSQL volume across restart")

    print("\n✅ PostgreSQL volume persistence verified successfully!\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--verify-persistence":
        with open("/tmp/parakh_docker_test.json", "r") as f:
            data = json.load(f)
        verify_persisted_data(data)
    else:
        if not wait_for_services():
            print("❌ Timed out waiting for Docker services.")
            sys.exit(1)
        test_info = run_full_stack_verification()
        with open("/tmp/parakh_docker_test.json", "w") as f:
            json.dump(test_info, f)
