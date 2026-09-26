"""Phase 14C: Analytics Date-Range Filters Test Suite (P2-03).

Verifies end-to-end functionality for date-range filtering on GET /api/v1/analytics/portfolio:
1. Unfiltered backward-compatibility test.
2. Start-date filtering test.
3. End-date filtering test.
4. Inclusive boundary test (records at 00:00:00 and 23:59:59).
5. Both-date filtering test.
6. Equal start/end date test (single-day filter).
7. Invalid date string test (returns HTTP 422).
8. Reversed range validation test (start_date > end_date returns HTTP 422).
9. Filtered population consistency across all metrics (totals, status, risk, scores, completion rate, sector risk).
10. Valid date range with no matching records returns clean empty aggregates.
11. Authorized reviewer access (HTTP 200).
12. Authorized admin access (HTTP 200).
13. Unauthorized applicant access rejected (HTTP 403).
14. Unauthenticated access rejected (HTTP 401).
"""
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    CreditAssessment,
    ModelVersion,
    RiskLevel,
    User,
    UserRole,
)
from app.repositories.user import UserRepository


class TestPhase14CAnalyticsDateFilters(unittest.TestCase):
    """Deterministic verification test suite for analytics date range filtering."""

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

        self.password = "SecurePass123!"

        # Create Users with distinct roles
        with self.SessionFactory() as db:
            user_repo = UserRepository(db=db)

            self.reviewer = user_repo.create({
                "email": "reviewer.phase14c@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)

            self.admin = user_repo.create({
                "email": "admin.phase14c@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.ADMIN,
                "is_active": True,
            }, commit=True)

            self.applicant = user_repo.create({
                "email": "applicant.phase14c@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)

            self.worker2 = user_repo.create({
                "email": "worker2.phase14c@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)

            self.worker3 = user_repo.create({
                "email": "worker3.phase14c@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)

            # Model Version
            mv = ModelVersion(
                model_name="PARAKH-RiskEngine-v1.0",
                version="1.0.0",
                algorithm="Volatility-Aware LightGBM",
                is_active=True,
            )
            db.add(mv)
            db.commit()
            self.model_version_id = mv.id

            # Applicant Profiles
            self.prof1 = ApplicantProfile(
                user_id=self.applicant.id,
                gig_work_type="Food Delivery",
                years_working=Decimal("2.5"),
                average_working_days=25,
            )
            self.prof2 = ApplicantProfile(
                user_id=self.worker2.id,
                gig_work_type="Ride Logistics",
                years_working=Decimal("3.0"),
                average_working_days=26,
            )
            self.prof3 = ApplicantProfile(
                user_id=self.worker3.id,
                gig_work_type="Home Services",
                years_working=Decimal("1.5"),
                average_working_days=20,
            )
            db.add_all([self.prof1, self.prof2, self.prof3])
            db.commit()

            # Deterministic fixtures spanning 3 distinct dates:
            # Date 1: 2026-05-10
            # Date 2: 2026-05-15 (Day 2 with boundary timestamps 00:00:00 and 23:59:59)
            # Date 3: 2026-05-20

            # Record 1 on Date 1: 2026-05-10 10:00:00 UTC
            app1 = Application(
                applicant_profile_id=self.prof1.id,
                requested_loan_amount=Decimal("30000.00"),
                status=ApplicationStatus.COMPLETED,
                created_at=datetime(2026, 5, 10, 10, 0, 0, tzinfo=timezone.utc),
            )
            db.add(app1)
            db.commit()

            asmt1 = CreditAssessment(
                application_id=app1.id,
                model_version_id=self.model_version_id,
                credit_score=750,
                risk_probability=Decimal("0.1500"),
                risk_level=RiskLevel.LOWER,
                created_at=datetime(2026, 5, 10, 10, 5, 0, tzinfo=timezone.utc),
            )
            db.add(asmt1)

            # Record 2 on Date 2: 2026-05-15 00:00:00 UTC (exact start of day boundary)
            app2 = Application(
                applicant_profile_id=self.prof1.id,
                requested_loan_amount=Decimal("40000.00"),
                status=ApplicationStatus.ASSESSED,
                created_at=datetime(2026, 5, 15, 0, 0, 0, tzinfo=timezone.utc),
            )
            db.add(app2)
            db.commit()

            asmt2 = CreditAssessment(
                application_id=app2.id,
                model_version_id=self.model_version_id,
                credit_score=680,
                risk_probability=Decimal("0.3500"),
                risk_level=RiskLevel.MODERATE,
                created_at=datetime(2026, 5, 15, 0, 5, 0, tzinfo=timezone.utc),
            )
            db.add(asmt2)

            # Record 3 on Date 2: 2026-05-15 23:59:59 UTC (exact end of day boundary)
            app3 = Application(
                applicant_profile_id=self.prof2.id,
                requested_loan_amount=Decimal("25000.00"),
                status=ApplicationStatus.MANUAL_REVIEW,
                created_at=datetime(2026, 5, 15, 23, 59, 59, tzinfo=timezone.utc),
            )
            db.add(app3)
            db.commit()

            asmt3 = CreditAssessment(
                application_id=app3.id,
                model_version_id=self.model_version_id,
                credit_score=620,
                risk_probability=Decimal("0.4500"),
                risk_level=RiskLevel.HIGHER,
                created_at=datetime(2026, 5, 15, 23, 59, 59, tzinfo=timezone.utc),
            )
            db.add(asmt3)

            # Record 4 on Date 3: 2026-05-20 12:00:00 UTC (unassessed application)
            app4 = Application(
                applicant_profile_id=self.prof3.id,
                requested_loan_amount=Decimal("15000.00"),
                status=ApplicationStatus.SUBMITTED,
                created_at=datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
            )
            db.add(app4)
            db.commit()

        # Auth headers
        self.reviewer_token = self._login("reviewer.phase14c@example.com", self.password)
        self.reviewer_headers = {"Authorization": f"Bearer {self.reviewer_token}"}

        self.admin_token = self._login("admin.phase14c@example.com", self.password)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        self.applicant_token = self._login("applicant.phase14c@example.com", self.password)
        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}")
        return resp.json()["access_token"]

    def tearDown(self):
        """Clean up dependency overrides and drop tables."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def test_unfiltered_backward_compatibility(self):
        """No dates supplied preserves the existing analytics results and counts exactly."""
        res = self.client.get("/api/v1/analytics/portfolio", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # All 4 applications across all 3 dates
        self.assertEqual(data["total_applications"], 4)
        self.assertEqual(data["total_applicants"], 3)
        self.assertEqual(data["total_assessments"], 3)

        # Status distribution
        self.assertEqual(data["status_distribution"]["COMPLETED"], 1)
        self.assertEqual(data["status_distribution"]["ASSESSED"], 1)
        self.assertEqual(data["status_distribution"]["MANUAL_REVIEW"], 1)
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 1)

        # Risk distribution
        self.assertEqual(data["risk_distribution"]["LOWER"], 1)
        self.assertEqual(data["risk_distribution"]["MODERATE"], 1)
        self.assertEqual(data["risk_distribution"]["HIGHER"], 1)
        self.assertEqual(data["risk_distribution"]["INSUFFICIENT"], 0)

        # Average score: (750 + 680 + 620) / 3 = 683.33... -> 683.3
        self.assertAlmostEqual(data["average_credit_score"], 683.3, places=1)
        # Average risk prob: (0.1500 + 0.3500 + 0.4500) / 3 = 0.3167
        self.assertAlmostEqual(data["average_risk_probability"], 0.3167, places=4)

        # Completion rate: (1 + 1 + 1) / 4 = 75.0%
        self.assertEqual(data["assessment_completion_rate"], 75.0)

        # Sector risk: Food Delivery (total=2), Ride Logistics (total=1)
        sectors = {s["sector"]: s for s in data["sector_risk"]}
        self.assertEqual(sectors["Food Delivery"]["total"], 2)
        self.assertEqual(sectors["Food Delivery"]["lower_risk"], 1)
        self.assertEqual(sectors["Food Delivery"]["moderate_risk"], 1)
        self.assertEqual(sectors["Ride Logistics"]["total"], 1)
        self.assertEqual(sectors["Ride Logistics"]["higher_risk"], 1)

    def test_start_date_filtering(self):
        """Only start_date supplied includes records on or after start_date, excluding earlier records."""
        # Filter starting from 2026-05-15 (excludes 2026-05-10)
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-15",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # app2 (May 15 00:00), app3 (May 15 23:59:59), app4 (May 20) -> 3 applications
        self.assertEqual(data["total_applications"], 3)
        self.assertEqual(data["total_applicants"], 3) # prof1, prof2, prof3
        self.assertEqual(data["total_assessments"], 2) # asmt2, asmt3

        # app1 on May 10 was COMPLETED, so COMPLETED should now be 0
        self.assertEqual(data["status_distribution"]["COMPLETED"], 0)
        self.assertEqual(data["status_distribution"]["ASSESSED"], 1)
        self.assertEqual(data["status_distribution"]["MANUAL_REVIEW"], 1)
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 1)

        # LOWER risk was on May 10, so LOWER should now be 0
        self.assertEqual(data["risk_distribution"]["LOWER"], 0)
        self.assertEqual(data["risk_distribution"]["MODERATE"], 1)
        self.assertEqual(data["risk_distribution"]["HIGHER"], 1)

        # Average score: (680 + 620) / 2 = 650.0
        self.assertEqual(data["average_credit_score"], 650.0)
        self.assertEqual(data["average_risk_probability"], 0.4000)

        # Completion rate: (1 ASSESSED + 1 MANUAL_REVIEW) / 3 = 66.7%
        self.assertEqual(data["assessment_completion_rate"], 66.7)

    def test_end_date_filtering(self):
        """Only end_date supplied includes records on or before end_date (inclusive calendar day), excluding later records."""
        # Filter ending on 2026-05-15 (excludes 2026-05-20)
        res = self.client.get(
            "/api/v1/analytics/portfolio?end_date=2026-05-15",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # app1 (May 10), app2 (May 15 00:00), app3 (May 15 23:59:59) -> 3 applications
        self.assertEqual(data["total_applications"], 3)
        self.assertEqual(data["total_applicants"], 2) # prof1 (app1, app2), prof2 (app3)
        self.assertEqual(data["total_assessments"], 3)

        # SUBMITTED was on May 20, so SUBMITTED should now be 0
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 0)
        self.assertEqual(data["status_distribution"]["COMPLETED"], 1)
        self.assertEqual(data["status_distribution"]["ASSESSED"], 1)
        self.assertEqual(data["status_distribution"]["MANUAL_REVIEW"], 1)

        # Completion rate: (1 + 1 + 1) / 3 = 100.0%
        self.assertEqual(data["assessment_completion_rate"], 100.0)

    def test_inclusive_boundaries_both_dates(self):
        """Both start_date and end_date supplied includes both boundary days in their entirety."""
        # Range: 2026-05-10 to 2026-05-15 (excludes 2026-05-20)
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-10&end_date=2026-05-15",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_applications"], 3)
        self.assertEqual(data["total_assessments"], 3)
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 0)

    def test_equal_start_and_end_date(self):
        """start_date == end_date includes full day records from 00:00:00 to 23:59:59."""
        # Range: 2026-05-15 to 2026-05-15 (only Day 2 records)
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-15&end_date=2026-05-15",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Both app2 (00:00:00) and app3 (23:59:59) must be included
        self.assertEqual(data["total_applications"], 2)
        self.assertEqual(data["total_applicants"], 2) # prof1, prof2
        self.assertEqual(data["total_assessments"], 2)

        # Day 1 (COMPLETED) and Day 3 (SUBMITTED) excluded
        self.assertEqual(data["status_distribution"]["COMPLETED"], 0)
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 0)
        self.assertEqual(data["status_distribution"]["ASSESSED"], 1)
        self.assertEqual(data["status_distribution"]["MANUAL_REVIEW"], 1)

        # Risk distribution: 0 LOWER, 1 MODERATE, 1 HIGHER
        self.assertEqual(data["risk_distribution"]["LOWER"], 0)
        self.assertEqual(data["risk_distribution"]["MODERATE"], 1)
        self.assertEqual(data["risk_distribution"]["HIGHER"], 1)

        # Average score: (680 + 620) / 2 = 650.0
        self.assertEqual(data["average_credit_score"], 650.0)

        # Completion rate: (1 + 1) / 2 = 100.0%
        self.assertEqual(data["assessment_completion_rate"], 100.0)

        # Sector risk: only Food Delivery (1) and Ride Logistics (1)
        sectors = {s["sector"]: s for s in data["sector_risk"]}
        self.assertEqual(sectors["Food Delivery"]["total"], 1)
        self.assertEqual(sectors["Food Delivery"]["moderate_risk"], 1)
        self.assertEqual(sectors["Food Delivery"]["lower_risk"], 0)
        self.assertEqual(sectors["Ride Logistics"]["total"], 1)
        self.assertEqual(sectors["Ride Logistics"]["higher_risk"], 1)

    def test_reversed_range_validation_error(self):
        """start_date > end_date returns HTTP 422 validation error."""
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-20&end_date=2026-05-10",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 422)
        self.assertIn("start_date must not be after end_date", res.json()["detail"])

    def test_invalid_date_format_validation_error(self):
        """Invalid date string formats return standard HTTP 422 validation error."""
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=invalid-date",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 422)

        res_end = self.client.get(
            "/api/v1/analytics/portfolio?end_date=2026-13-45",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res_end.status_code, 422)

    def test_valid_date_range_with_no_records(self):
        """A valid date window with no records returns clean empty aggregates without errors."""
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2025-01-01&end_date=2025-01-31",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_applications"], 0)
        self.assertEqual(data["total_applicants"], 0)
        self.assertEqual(data["total_assessments"], 0)
        self.assertIsNone(data["average_credit_score"])
        self.assertIsNone(data["average_risk_probability"])
        self.assertEqual(data["assessment_completion_rate"], 0.0)

        for status_val in ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "ASSESSED", "MANUAL_REVIEW", "COMPLETED"]:
            self.assertEqual(data["status_distribution"][status_val], 0)

        for risk_val in ["LOWER", "MODERATE", "HIGHER", "INSUFFICIENT"]:
            self.assertEqual(data["risk_distribution"][risk_val], 0)

        self.assertEqual(data["score_distribution"], [])
        self.assertEqual(data["sector_risk"], [])

    def test_all_portfolio_metrics_respect_same_filtered_population(self):
        """Verify that all metrics (totals, distributions, averages, completion rate, histograms, sector risk) consistently respect the filter."""
        # Range targeting Day 1 only: 2026-05-10
        res = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-10&end_date=2026-05-10",
            headers=self.reviewer_headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Day 1 has exactly 1 application (prof1, COMPLETED, score=750, LOWER risk)
        self.assertEqual(data["total_applications"], 1)
        self.assertEqual(data["total_applicants"], 1)
        self.assertEqual(data["total_assessments"], 1)
        self.assertEqual(data["status_distribution"]["COMPLETED"], 1)
        self.assertEqual(sum(data["status_distribution"].values()), 1)

        self.assertEqual(data["risk_distribution"]["LOWER"], 1)
        self.assertEqual(sum(data["risk_distribution"].values()), 1)

        self.assertEqual(data["average_credit_score"], 750.0)
        self.assertEqual(data["average_risk_probability"], 0.1500)
        self.assertEqual(data["assessment_completion_rate"], 100.0)

        # Score distribution: exactly 1 bucket with count=1 (740-799), others 0
        scored_buckets = [b for b in data["score_distribution"] if b["count"] > 0]
        self.assertEqual(len(scored_buckets), 1)
        self.assertEqual(scored_buckets[0]["range"], "740–799")
        self.assertEqual(scored_buckets[0]["count"], 1)
        self.assertEqual(scored_buckets[0]["percentage"], 100.0)

        # Sector risk: only Food Delivery with count 1
        self.assertEqual(len(data["sector_risk"]), 1)
        self.assertEqual(data["sector_risk"][0]["sector"], "Food Delivery")
        self.assertEqual(data["sector_risk"][0]["total"], 1)
        self.assertEqual(data["sector_risk"][0]["lower_risk"], 1)

    def test_rbac_authorization(self):
        """Verify REVIEWER and ADMIN are authorized, while APPLICANT and unauthenticated users are rejected."""
        # 1. Reviewer allowed
        r_resp = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-10",
            headers=self.reviewer_headers,
        )
        self.assertEqual(r_resp.status_code, 200)

        # 2. Admin allowed
        a_resp = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-10",
            headers=self.admin_headers,
        )
        self.assertEqual(a_resp.status_code, 200)

        # 3. Applicant rejected (403 Forbidden)
        app_resp = self.client.get(
            "/api/v1/analytics/portfolio?start_date=2026-05-10",
            headers=self.applicant_headers,
        )
        self.assertEqual(app_resp.status_code, 403)
        self.assertIn("Access denied", app_resp.json()["detail"])

        # 4. Unauthenticated rejected (401 Unauthorized)
        no_auth = self.client.get("/api/v1/analytics/portfolio?start_date=2026-05-10")
        self.assertEqual(no_auth.status_code, 401)


if __name__ == "__main__":
    unittest.main()
