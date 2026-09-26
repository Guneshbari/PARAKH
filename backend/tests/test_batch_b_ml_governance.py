"""Batch B — ML Governance Test Suite: P2-06 Model Promotion + P2-07 Offline Fairness.

Verifies:
1. P2-06 Model Promotion/Activation API:
   - Admin activation switches active model version atomically in PostgreSQL.
   - Any prior active version in the same model family is deactivated.
   - Other model families retain their active versions unaffected.
   - Activation is idempotent.
   - Nonexistent model version ID returns HTTP 404.
   - RBAC enforcement: Unauthenticated returns HTTP 401; Applicant and Reviewer return HTTP 403.
   - Audit logging: MODEL_VERSION_ACTIVATED event recorded with provenance metadata.
2. P2-07 Offline Fairness Evaluation Execution:
   - GroupedFairnessAuditor executes offline fairness audit via API.
   - Admin and Reviewer can execute fairness audits.
   - Supports custom evaluation records payload.
   - Supports offline benchmark dataset (data/synthetic/synthetic_credit_applications.parquet).
   - Validates subgroup operational fields (e.g. gig_work_type, cohort_archetype, loan_purpose).
   - Invalid subgroup field returns HTTP 422.
   - Empty records list returns HTTP 422.
   - Nonexistent model version ID returns HTTP 404.
   - RBAC enforcement: Unauthenticated returns HTTP 401; Applicant returns HTTP 403.
   - Audit logging: MODEL_FAIRNESS_EVALUATED event recorded.
3. System Integrity:
   - Active model version is linked by AssessmentService on credit assessments.
   - Promoting a model version updates the linked version ID for subsequent assessments.
   - Frozen ML artifacts remain unchanged with verified SHA-256 hashes.
"""
import hashlib
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator

from fastapi.testclient import TestClient
import numpy as np
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
    FinancialSignal,
    ModelVersion,
    RiskLevel,
    User,
    UserRole,
)
from app.schemas.model_version import FairnessAuditRecord, FairnessAuditRequest
from app.services.assessment import AssessmentService
from src.ml.evaluation.fairness import GroupedFairnessAuditor, audit_subgroup_fairness


class TestBatchBMLGovernance(unittest.TestCase):
    """Deterministic test suite for P2-06 Model Promotion & P2-07 Fairness Evaluation."""

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
            # 1. Admin User
            self.admin_user_id = uuid.uuid4()
            self.admin_user = User(
                id=self.admin_user_id,
                email="admin_gov@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(self.admin_user)

            # 2. Reviewer User
            self.reviewer_user_id = uuid.uuid4()
            self.reviewer_user = User(
                id=self.reviewer_user_id,
                email="reviewer_gov@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.REVIEWER,
                is_active=True,
            )
            session.add(self.reviewer_user)

            # 3. Applicant User
            self.applicant_user_id = uuid.uuid4()
            self.applicant_user = User(
                id=self.applicant_user_id,
                email="applicant_gov@parakh.in",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant_user)

            # 4. Model Versions: Model Family 1 (volatility-aware-risk-model)
            self.mv1_id = uuid.uuid4()
            self.mv1 = ModelVersion(
                id=self.mv1_id,
                model_name="volatility-aware-risk-model",
                version="1.0.0",
                algorithm="LightGBM + RobustScaler + TreeSHAP",
                description="Production baseline volatility-aware credit risk model",
                is_active=True,
            )
            session.add(self.mv1)

            self.mv2_id = uuid.uuid4()
            self.mv2 = ModelVersion(
                id=self.mv2_id,
                model_name="volatility-aware-risk-model",
                version="1.1.0",
                algorithm="LightGBM + RobustScaler + TreeSHAP (Tuned)",
                description="Candidate promotional release",
                is_active=False,
            )
            session.add(self.mv2)

            # 5. Model Versions: Model Family 2 (baseline-risk-model)
            self.mv_other_id = uuid.uuid4()
            self.mv_other = ModelVersion(
                id=self.mv_other_id,
                model_name="baseline-risk-model",
                version="0.9.0",
                algorithm="Logistic Regression",
                description="Alternate model family",
                is_active=True,
            )
            session.add(self.mv_other)

            session.commit()
        finally:
            session.close()

        # Auth headers
        self.admin_token = create_access_token(
            subject=str(self.admin_user_id), role=UserRole.ADMIN.value
        )
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        self.reviewer_token = create_access_token(
            subject=str(self.reviewer_user_id), role=UserRole.REVIEWER.value
        )
        self.reviewer_headers = {"Authorization": f"Bearer {self.reviewer_token}"}

        self.applicant_token = create_access_token(
            subject=str(self.applicant_user_id), role=UserRole.APPLICANT.value
        )
        self.applicant_headers = {"Authorization": f"Bearer {self.applicant_token}"}

    def tearDown(self):
        """Clean up database and dependency overrides."""
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    # =========================================================================
    # P2-06: Model Promotion / Activation API Tests
    # =========================================================================

    def test_p2_06_admin_can_activate_model_version(self):
        """Admin can promote/activate a candidate model version."""
        response = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.mv2_id))
        self.assertEqual(data["version"], "1.1.0")
        self.assertTrue(data["is_active"])

    def test_p2_06_activation_deactivates_prior_active_in_same_family(self):
        """Activating v1.1.0 deactivates prior active v1.0.0 in the same family."""
        response = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)

        session = self.SessionFactory()
        try:
            mv1 = session.get(ModelVersion, self.mv1_id)
            mv2 = session.get(ModelVersion, self.mv2_id)
            mv_other = session.get(ModelVersion, self.mv_other_id)

            self.assertFalse(mv1.is_active, "Prior version v1.0.0 must be deactivated")
            self.assertTrue(mv2.is_active, "Target version v1.1.0 must be active")
            self.assertTrue(
                mv_other.is_active,
                "Model version in different family must remain untouched",
            )

            # Exactly one active version for volatility-aware-risk-model
            active_versions = session.scalars(
                select(ModelVersion)
                .where(ModelVersion.model_name == "volatility-aware-risk-model")
                .where(ModelVersion.is_active.is_(True))
            ).all()
            self.assertEqual(len(active_versions), 1)
            self.assertEqual(active_versions[0].id, self.mv2_id)
        finally:
            session.close()

    def test_p2_06_activation_is_idempotent(self):
        """Calling activate multiple times succeeds and preserves active state."""
        # First activation
        resp1 = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertTrue(resp1.json()["is_active"])

        # Second activation (already active)
        resp2 = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(resp2.json()["is_active"])

        session = self.SessionFactory()
        try:
            mv2 = session.get(ModelVersion, self.mv2_id)
            self.assertTrue(mv2.is_active)
        finally:
            session.close()

    def test_p2_06_activation_rbac_protection(self):
        """Activation route is strictly restricted to ADMIN role."""
        # 1. Unauthenticated -> 401
        resp_unauth = self.client.post(f"/api/v1/model-versions/{self.mv2_id}/activate")
        self.assertEqual(resp_unauth.status_code, 401)

        # 2. Applicant -> 403
        resp_applicant = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.applicant_headers,
        )
        self.assertEqual(resp_applicant.status_code, 403)

        # 3. Reviewer -> 403
        resp_reviewer = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_reviewer.status_code, 403)

    def test_p2_06_activation_nonexistent_model_returns_404(self):
        """Activating nonexistent model version ID returns HTTP 404."""
        nonexistent_id = uuid.uuid4()
        response = self.client.post(
            f"/api/v1/model-versions/{nonexistent_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_p2_06_activation_records_audit_log(self):
        """Activating a model version records a MODEL_VERSION_ACTIVATED audit event."""
        response = self.client.post(
            f"/api/v1/model-versions/{self.mv2_id}/activate",
            headers=self.admin_headers,
        )
        self.assertEqual(response.status_code, 200)

        session = self.SessionFactory()
        try:
            stmt = (
                select(AuditLog)
                .where(AuditLog.action == AuditAction.MODEL_VERSION_ACTIVATED)
                .where(AuditLog.entity_id == str(self.mv2_id))
            )
            audit_entry = session.scalars(stmt).first()
            self.assertIsNotNone(audit_entry, "Audit log entry must be persisted")
            self.assertEqual(audit_entry.user_id, self.admin_user_id)
            self.assertEqual(audit_entry.entity_type, "ModelVersion")
            self.assertEqual(audit_entry.audit_metadata.get("version"), "1.1.0")
            self.assertEqual(audit_entry.audit_metadata.get("previous_active_version"), "1.0.0")
        finally:
            session.close()

    # =========================================================================
    # P2-07: Offline Fairness Evaluation Execution Tests
    # =========================================================================

    def test_p2_07_grouped_fairness_auditor_standalone_accuracy(self):
        """Verify GroupedFairnessAuditor class wraps audit_subgroup_fairness accurately."""
        auditor = GroupedFairnessAuditor(subgroup_field_name="gig_work_type", threshold=0.5)
        y_true = [0, 0, 1, 0, 0, 1, 0, 1]
        y_prob = [0.1, 0.2, 0.7, 0.15, 0.3, 0.8, 0.25, 0.75]
        subgroups = [
            "DELIVERY", "DELIVERY", "DELIVERY", "DELIVERY",
            "RIDE_HAILING", "RIDE_HAILING", "RIDE_HAILING", "RIDE_HAILING",
        ]
        report = auditor.audit(y_true=y_true, y_prob=y_prob, subgroups=subgroups)

        self.assertEqual(report.subgroup_field, "gig_work_type")
        self.assertEqual(len(report.subgroups), 2)
        self.assertIn("DELIVERY", report.subgroups)
        self.assertIn("RIDE_HAILING", report.subgroups)
        self.assertAlmostEqual(report.demographic_parity_ratio, 0.6667, places=3)
        self.assertIn("IMPORTANT LIMITATION", report.limitations_disclaimer)

    def test_p2_07_admin_and_reviewer_can_run_fairness_with_custom_records(self):
        """Admin and Reviewer can execute fairness evaluation with custom records."""
        payload = {
            "subgroup_field": "gig_work_type",
            "threshold": 0.5,
            "records": [
                {"y_true": 0, "y_prob": 0.1, "subgroup": "DELIVERY"},
                {"y_true": 0, "y_prob": 0.2, "subgroup": "DELIVERY"},
                {"y_true": 1, "y_prob": 0.8, "subgroup": "DELIVERY"},
                {"y_true": 0, "y_prob": 0.15, "subgroup": "DELIVERY"},
                {"y_true": 0, "y_prob": 0.3, "subgroup": "RIDE_HAILING"},
                {"y_true": 1, "y_prob": 0.9, "subgroup": "RIDE_HAILING"},
                {"y_true": 0, "y_prob": 0.25, "subgroup": "RIDE_HAILING"},
                {"y_true": 1, "y_prob": 0.85, "subgroup": "RIDE_HAILING"},
            ],
        }

        # Admin execution
        resp_admin = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json=payload,
            headers=self.admin_headers,
        )
        self.assertEqual(resp_admin.status_code, 200)
        data_admin = resp_admin.json()
        self.assertEqual(data_admin["model_version_id"], str(self.mv1_id))
        self.assertEqual(data_admin["sample_count"], 8)
        self.assertEqual(data_admin["subgroup_field"], "gig_work_type")
        self.assertIn("DELIVERY", data_admin["subgroups"])
        self.assertIn("RIDE_HAILING", data_admin["subgroups"])
        self.assertIsNotNone(data_admin["demographic_parity_ratio"])

        # Reviewer execution
        resp_reviewer = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json=payload,
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_reviewer.status_code, 200)
        data_reviewer = resp_reviewer.json()
        self.assertEqual(data_reviewer["sample_count"], 8)
        self.assertEqual(data_reviewer["demographic_parity_ratio"], data_admin["demographic_parity_ratio"])

    def test_p2_07_fairness_audit_with_benchmark_dataset(self):
        """Executing fairness audit with omitted records evaluates against synthetic benchmark dataset."""
        response = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type", "threshold": 0.5},
            headers=self.reviewer_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["model_version_id"], str(self.mv1_id))
        self.assertEqual(data["model_name"], "volatility-aware-risk-model")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["subgroup_field"], "gig_work_type")
        # 11,407 non-null applications in synthetic benchmark
        self.assertEqual(data["sample_count"], 11407)
        self.assertIn("DELIVERY", data["subgroups"])
        self.assertIn("RIDE_HAILING", data["subgroups"])
        self.assertIn("LOGISTICS", data["subgroups"])
        self.assertIn("HOME_SERVICES", data["subgroups"])
        self.assertIn("FREELANCE_MICRO", data["subgroups"])
        self.assertIn("OTHER", data["subgroups"])
        self.assertAlmostEqual(data["demographic_parity_ratio"], 0.9403, places=3)
        self.assertAlmostEqual(data["equal_opportunity_difference"], 0.1333, places=3)
        self.assertIn("IMPORTANT LIMITATION", data["limitations_disclaimer"])

    def test_p2_07_fairness_audit_alternative_operational_subgroups(self):
        """Fairness audit executes across alternative operational cohorts (cohort_archetype, loan_purpose)."""
        # Test cohort_archetype
        resp_cohort = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "cohort_archetype", "threshold": 0.5},
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_cohort.status_code, 200)
        data_cohort = resp_cohort.json()
        self.assertEqual(data_cohort["subgroup_field"], "cohort_archetype")
        self.assertIn("Stable", data_cohort["subgroups"])
        self.assertIn("Healthy Volatile", data_cohort["subgroups"])

        # Test loan_purpose
        resp_purpose = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "loan_purpose", "threshold": 0.5},
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_purpose.status_code, 200)
        data_purpose = resp_purpose.json()
        self.assertEqual(data_purpose["subgroup_field"], "loan_purpose")

    def test_p2_07_fairness_audit_rbac_protection(self):
        """Fairness audit route is restricted to ADMIN and REVIEWER; rejected for unauth and APPLICANT."""
        # 1. Unauthenticated -> 401
        resp_unauth = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type"},
        )
        self.assertEqual(resp_unauth.status_code, 401)

        # 2. Applicant -> 403
        resp_applicant = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type"},
            headers=self.applicant_headers,
        )
        self.assertEqual(resp_applicant.status_code, 403)

    def test_p2_07_fairness_audit_validation_errors(self):
        """Invalid inputs return HTTP 422 Unprocessable Entity."""
        # 1. Invalid subgroup field not in benchmark dataset -> 422
        resp_invalid_field = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "nonexistent_demographic_field"},
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_invalid_field.status_code, 422)

        # 2. Empty records list -> 422
        resp_empty_records = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type", "records": []},
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_empty_records.status_code, 422)

        # 3. Nonexistent model version -> 404
        nonexistent_id = uuid.uuid4()
        resp_404 = self.client.post(
            f"/api/v1/model-versions/{nonexistent_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type"},
            headers=self.reviewer_headers,
        )
        self.assertEqual(resp_404.status_code, 404)

    def test_p2_07_fairness_audit_records_audit_log(self):
        """Executing a fairness audit creates a MODEL_FAIRNESS_EVALUATED audit event."""
        response = self.client.post(
            f"/api/v1/model-versions/{self.mv1_id}/fairness-audit",
            json={"subgroup_field": "gig_work_type", "threshold": 0.5},
            headers=self.reviewer_headers,
        )
        self.assertEqual(response.status_code, 200)

        session = self.SessionFactory()
        try:
            stmt = (
                select(AuditLog)
                .where(AuditLog.action == AuditAction.MODEL_FAIRNESS_EVALUATED)
                .where(AuditLog.entity_id == str(self.mv1_id))
            )
            audit_entry = session.scalars(stmt).first()
            self.assertIsNotNone(audit_entry, "Audit log entry must be persisted")
            self.assertEqual(audit_entry.user_id, self.reviewer_user_id)
            self.assertEqual(audit_entry.entity_type, "ModelVersion")
            self.assertEqual(audit_entry.audit_metadata.get("subgroup_field"), "gig_work_type")
            self.assertIn("demographic_parity_ratio", audit_entry.audit_metadata)
        finally:
            session.close()

    # =========================================================================
    # Live Scoring & Frozen Model Artifacts Integrity
    # =========================================================================

    def test_live_scoring_links_active_model_version(self):
        """AssessmentService correctly resolves and records the currently active model version."""
        from app.assessment.mock import MockAssessmentEngine
        session = self.SessionFactory()
        try:
            # Create applicant profile and application
            profile = ApplicantProfile(
                user_id=self.applicant_user_id,
                gig_work_type="DELIVERY",
                years_working=Decimal("2.0"),
                average_working_days=24,
                business_or_loan_purpose="BIKE_PURCHASE",
            )
            session.add(profile)
            session.flush()

            app_record = Application(
                applicant_profile_id=profile.id,
                status=ApplicationStatus.SUBMITTED,
                requested_loan_amount=Decimal("50000.00"),
                loan_purpose="BIKE_PURCHASE",
                preferred_repayment_period=12,
            )
            session.add(app_record)
            session.commit()

            # Execute assessment with initial active model (v1.0.0)
            service = AssessmentService(db=session, engine=MockAssessmentEngine())
            assessment = service.assess_application(
                application_id=app_record.id,
                enforce_consent=False,
            )
            self.assertIsNotNone(assessment)
            self.assertEqual(
                assessment.model_version_id,
                self.mv1_id,
                "Assessment must reference active model version v1.0.0",
            )

            # Now promote v1.1.0 via API
            resp = self.client.post(
                f"/api/v1/model-versions/{self.mv2_id}/activate",
                headers=self.admin_headers,
            )
            self.assertEqual(resp.status_code, 200)

            app_record_2 = Application(
                applicant_profile_id=profile.id,
                status=ApplicationStatus.SUBMITTED,
                requested_loan_amount=Decimal("30000.00"),
                loan_purpose="EQUIPMENT",
                preferred_repayment_period=6,
            )
            session.add(app_record_2)
            session.commit()

            assessment_2 = service.assess_application(
                application_id=app_record_2.id,
                enforce_consent=False,
            )
            self.assertEqual(
                assessment_2.model_version_id,
                self.mv2_id,
                "Assessment must now reference newly activated model version v1.1.0",
            )
        finally:
            session.close()

    def test_frozen_ml_artifacts_hash_verification(self):
        """Verify that frozen model artifacts have not been modified."""
        expected_hashes = {
            "models/artifacts/volatility_aware_risk_model.joblib": "88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060",
            "models/artifacts/FINAL_MODEL.json": "e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f",
            "models/artifacts/credit_risk_preprocessor.joblib": "bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2",
        }

        for path_str, expected_hash in expected_hashes.items():
            path = Path(path_str)
            self.assertTrue(path.exists(), f"Artifact {path_str} must exist")
            hasher = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            actual_hash = hasher.hexdigest()
            self.assertEqual(
                actual_hash,
                expected_hash,
                f"Artifact {path_str} hash changed! Frozen model constraint violated.",
            )


if __name__ == "__main__":
    unittest.main()
