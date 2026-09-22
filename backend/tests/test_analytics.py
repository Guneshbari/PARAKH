"""Phase 9 Portfolio Analytics & Sector Risk Aggregation Tests.

Verifies:
1. Portfolio aggregation over Application, ApplicantProfile, and CreditAssessment.
2. Canonical ApplicationStatus pipeline distribution.
3. Canonical RiskLevel distribution from CreditAssessment records.
4. Sector risk aggregation by applicant gig_work_type.
5. Empty database handling (clean null/empty defaults without errors).
6. Strict RBAC enforcement (REVIEWER & ADMIN permitted; APPLICANT forbidden with 403).
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
from app.repositories.application import ApplicationRepository
from app.repositories.user import UserRepository


class TestPortfolioAnalytics(unittest.TestCase):
    """Test suite for portfolio analytics and sector risk aggregations."""

    def setUp(self):
        """Set up an isolated in-memory SQLite database and FastAPI TestClient."""
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

        with self.SessionFactory() as db:
            user_repo = UserRepository(db=db)

            # Reviewer user
            self.reviewer = user_repo.create({
                "email": "reviewer.phase9@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.REVIEWER,
                "is_active": True,
            }, commit=True)

            # Admin user
            self.admin = user_repo.create({
                "email": "admin.phase9@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.ADMIN,
                "is_active": True,
            }, commit=True)

            # Applicant user
            self.applicant = user_repo.create({
                "email": "applicant.phase9@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)

        self.reviewer_token = self._login("reviewer.phase9@example.com", self.password)
        self.reviewer_headers = {"Authorization": f"Bearer {self.reviewer_token}"}

        self.admin_token = self._login("admin.phase9@example.com", self.password)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        self.applicant_token = self._login("applicant.phase9@example.com", self.password)
        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}

    def _login(self, email: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200, f"Login failed for {email}")
        return resp.json()["access_token"]

    def tearDown(self):
        """Clean up database and dependency overrides."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def test_empty_database_analytics(self):
        """When no applications exist, endpoint returns clean empty metrics without errors."""
        res = self.client.get("/api/v1/analytics/portfolio", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_applications"], 0)
        self.assertEqual(data["total_applicants"], 0)
        self.assertEqual(data["total_assessments"], 0)
        self.assertIsNone(data["average_credit_score"])
        self.assertIsNone(data["average_risk_probability"])
        self.assertEqual(data["assessment_completion_rate"], 0.0)

        # Verify all statuses are initialized to 0
        for status_val in ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "ASSESSED", "MANUAL_REVIEW", "COMPLETED"]:
            self.assertEqual(data["status_distribution"].get(status_val), 0)

        # Verify all risk levels are initialized to 0
        for risk_val in ["LOWER", "MODERATE", "HIGHER", "INSUFFICIENT"]:
            self.assertEqual(data["risk_distribution"].get(risk_val), 0)

        self.assertEqual(data["score_distribution"], [])
        self.assertEqual(data["sector_risk"], [])

    def test_populated_portfolio_analytics(self):
        """Verify aggregations when applicants, applications, and assessments exist."""
        with self.SessionFactory() as db:
            # Create two applicant profiles with different gig work types
            prof1 = ApplicantProfile(
                user_id=self.applicant.id,
                gig_work_type="Food Delivery",
                years_working=Decimal("2.0"),
                average_working_days=25,
            )
            db.add(prof1)
            db.commit()

            # Second user + profile
            user_repo = UserRepository(db=db)
            user2 = user_repo.create({
                "email": "worker2@example.com",
                "password_hash": hash_password(self.password),
                "role": UserRole.APPLICANT,
                "is_active": True,
            }, commit=True)
            prof2 = ApplicantProfile(
                user_id=user2.id,
                gig_work_type="Ride Logistics",
                years_working=Decimal("3.5"),
                average_working_days=26,
            )
            db.add(prof2)
            db.commit()

            # Model version
            mv = ModelVersion(
                model_name="PARAKH-MockEngine-v1.0",
                version="1.0.0",
                algorithm="Rule-Based Volatility Blend",
                is_active=True,
            )
            db.add(mv)
            db.commit()

            # Applications
            app1 = Application(
                applicant_profile_id=prof1.id,
                requested_loan_amount=Decimal("30000.00"),
                status=ApplicationStatus.ASSESSED,
            )
            app2 = Application(
                applicant_profile_id=prof1.id,
                requested_loan_amount=Decimal("45000.00"),
                status=ApplicationStatus.MANUAL_REVIEW,
            )
            app3 = Application(
                applicant_profile_id=prof2.id,
                requested_loan_amount=Decimal("20000.00"),
                status=ApplicationStatus.COMPLETED,
            )
            app4 = Application(
                applicant_profile_id=prof2.id,
                requested_loan_amount=Decimal("15000.00"),
                status=ApplicationStatus.SUBMITTED,
            )
            db.add_all([app1, app2, app3, app4])
            db.commit()

            # Assessments for app1, app2, app3
            asmt1 = CreditAssessment(
                application_id=app1.id,
                model_version_id=mv.id,
                credit_score=750,
                risk_probability=Decimal("0.1800"),
                risk_level=RiskLevel.LOWER,
            )
            asmt2 = CreditAssessment(
                application_id=app2.id,
                model_version_id=mv.id,
                credit_score=690,
                risk_probability=Decimal("0.3200"),
                risk_level=RiskLevel.MODERATE,
            )
            asmt3 = CreditAssessment(
                application_id=app3.id,
                model_version_id=mv.id,
                credit_score=580,
                risk_probability=Decimal("0.5500"),
                risk_level=RiskLevel.HIGHER,
            )
            db.add_all([asmt1, asmt2, asmt3])
            db.commit()

        # Query portfolio analytics
        res = self.client.get("/api/v1/analytics/portfolio", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Assert total applications and applicants
        self.assertEqual(data["total_applications"], 4)
        self.assertEqual(data["total_applicants"], 2)
        self.assertEqual(data["total_assessments"], 3)

        # Status distribution
        self.assertEqual(data["status_distribution"]["ASSESSED"], 1)
        self.assertEqual(data["status_distribution"]["MANUAL_REVIEW"], 1)
        self.assertEqual(data["status_distribution"]["COMPLETED"], 1)
        self.assertEqual(data["status_distribution"]["SUBMITTED"], 1)
        self.assertEqual(data["status_distribution"]["DRAFT"], 0)
        self.assertEqual(data["status_distribution"]["UNDER_REVIEW"], 0)

        # Risk distribution
        self.assertEqual(data["risk_distribution"]["LOWER"], 1)
        self.assertEqual(data["risk_distribution"]["MODERATE"], 1)
        self.assertEqual(data["risk_distribution"]["HIGHER"], 1)
        self.assertEqual(data["risk_distribution"]["INSUFFICIENT"], 0)

        # Average score: (750 + 690 + 580) / 3 = 673.3
        self.assertAlmostEqual(data["average_credit_score"], 673.3, places=1)

        # Completion rate: (1 ASSESSED + 1 MANUAL_REVIEW + 1 COMPLETED) / 4 = 75.0%
        self.assertEqual(data["assessment_completion_rate"], 75.0)
        self.assertEqual(data["assessed_applications"], 1)
        self.assertEqual(data["manual_review_applications"], 1)
        self.assertEqual(data["completed_applications"], 1)

        # Score distribution histogram
        buckets = {b["range"]: b for b in data["score_distribution"]}
        self.assertIn("740–799", buckets)
        self.assertEqual(buckets["740–799"]["count"], 1)  # 750
        self.assertIn("680–739", buckets)
        self.assertEqual(buckets["680–739"]["count"], 1)  # 690
        self.assertIn("< 600", buckets)
        self.assertEqual(buckets["< 600"]["count"], 1)    # 580

        # Sector risk
        sector_items = {s["sector"]: s for s in data["sector_risk"]}
        self.assertIn("Food Delivery", sector_items)
        food = sector_items["Food Delivery"]
        self.assertEqual(food["lower_risk"], 1)
        self.assertEqual(food["moderate_risk"], 1)
        self.assertEqual(food["total"], 2)

        self.assertIn("Ride Logistics", sector_items)
        ride = sector_items["Ride Logistics"]
        self.assertEqual(ride["higher_risk"], 1)
        self.assertEqual(ride["total"], 1)

    def test_sector_risk_dedicated_endpoint(self):
        """Verify dedicated GET /api/v1/analytics/sector-risk endpoint."""
        with self.SessionFactory() as db:
            prof = ApplicantProfile(
                user_id=self.applicant.id,
                gig_work_type="Home Salon",
                years_working=Decimal("1.5"),
            )
            db.add(prof)
            db.commit()

            mv = ModelVersion(
                model_name="PARAKH-MockEngine-v1.0",
                version="1.0.0",
                is_active=True,
            )
            db.add(mv)
            db.commit()

            app = Application(
                applicant_profile_id=prof.id,
                requested_loan_amount=Decimal("25000.00"),
                status=ApplicationStatus.MANUAL_REVIEW,
            )
            db.add(app)
            db.commit()

            asmt = CreditAssessment(
                application_id=app.id,
                model_version_id=mv.id,
                credit_score=None,
                risk_probability=None,
                risk_level=RiskLevel.INSUFFICIENT,
            )
            db.add(asmt)
            db.commit()

        res = self.client.get("/api/v1/analytics/sector-risk", headers=self.reviewer_headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["sector"], "Home Salon")
        self.assertEqual(items[0]["manual_review"], 1)
        self.assertEqual(items[0]["lower_risk"], 0)
        self.assertEqual(items[0]["total"], 1)

    def test_rbac_authorization(self):
        """Verify REVIEWER and ADMIN have access; APPLICANT and unauthenticated are blocked."""
        # Unauthenticated -> 401
        res_unauth = self.client.get("/api/v1/analytics/portfolio")
        self.assertEqual(res_unauth.status_code, 401)

        # APPLICANT -> 403
        res_applicant = self.client.get("/api/v1/analytics/portfolio", headers=self.applicant_headers)
        self.assertEqual(res_applicant.status_code, 403)

        res_applicant_sector = self.client.get("/api/v1/analytics/sector-risk", headers=self.applicant_headers)
        self.assertEqual(res_applicant_sector.status_code, 403)

        # REVIEWER -> 200
        res_rev = self.client.get("/api/v1/analytics/portfolio", headers=self.reviewer_headers)
        self.assertEqual(res_rev.status_code, 200)

        # ADMIN -> 200
        res_adm = self.client.get("/api/v1/analytics/portfolio", headers=self.admin_headers)
        self.assertEqual(res_adm.status_code, 200)


if __name__ == "__main__":
    unittest.main()
