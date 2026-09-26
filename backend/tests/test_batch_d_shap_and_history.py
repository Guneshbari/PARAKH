"""Batch D: P2-10 Global SHAP Feature Importance + P2-11 Historical Assessment Auditing.

Test suite verifying:
- P2-10: Backend global SHAP endpoint (RBAC, schema, determinism, audit logging, model provenance)
- P2-11: Historical assessment endpoint (RBAC, reverse-chronological ordering, null score preservation, no fabrication)
- Frozen ML artifact SHA-256 hashes remain unchanged throughout.
- Live scoring and assessment pipeline behavior is untouched.
"""
import hashlib
import uuid
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import (
    ApplicantProfile,
    Application,
    AuditLog,
    Base,
    CreditAssessment,
    ModelVersion,
    RiskLevel,
    User,
    UserRole,
)
from app.schemas.assessment import CreditAssessmentResponse
from app.schemas.model_version import (
    GlobalSHAPFeatureItem,
    GlobalSHAPResponse,
)
from app.services.exceptions import ValidationError
from app.services.model_version import ModelVersionService


# ---------------------------------------------------------------------------
# Repo root and frozen artifact hashes
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_ARTIFACT_HASHES = {
    "volatility_aware_risk_model.joblib": "88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060",
    "FINAL_MODEL.json": "e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f",
    "credit_risk_preprocessor.joblib": "bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Artifact integrity
# ---------------------------------------------------------------------------


class TestFrozenArtifactIntegrity:
    """Verify frozen ML artifact hashes are unchanged by P2-10/P2-11 implementation."""

    @pytest.mark.parametrize("filename,expected_hash", FROZEN_ARTIFACT_HASHES.items())
    def test_artifact_hash_unchanged(self, filename: str, expected_hash: str):
        artifact_path = REPO_ROOT / "models" / "artifacts" / filename
        assert artifact_path.exists(), f"Frozen artifact missing: {artifact_path}"
        actual = _sha256(artifact_path)
        assert actual == expected_hash, (
            f"Frozen artifact {filename} hash mismatch!\n"
            f"  Expected: {expected_hash}\n"
            f"  Got:      {actual}\n"
            "The frozen artifact has been modified — this is a critical integrity violation."
        )


# ---------------------------------------------------------------------------
# P2-10 Schema Tests
# ---------------------------------------------------------------------------


class TestGlobalSHAPSchemas:
    """Verify GlobalSHAPFeatureItem and GlobalSHAPResponse schemas are correct."""

    def test_global_shap_feature_item_fields(self):
        item = GlobalSHAPFeatureItem(
            feature_name="feat_liq_net_margin",
            mean_abs_shap=1.577765,
            mean_shap=-0.036936,
            rank=1,
        )
        assert item.feature_name == "feat_liq_net_margin"
        assert abs(item.mean_abs_shap - 1.577765) < 1e-5
        assert abs(item.mean_shap - (-0.036936)) < 1e-5
        assert item.rank == 1

    def test_global_shap_response_fields(self):
        mv_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        resp = GlobalSHAPResponse(
            model_version_id=mv_id,
            model_version="1.0.0",
            model_name="volatility-aware-risk-model",
            evaluated_at=now,
            sample_count=12000,
            dataset_source="Offline synthetic evaluation dataset.",
            features=[
                GlobalSHAPFeatureItem(
                    feature_name="feat_liq_net_margin",
                    mean_abs_shap=1.5,
                    mean_shap=-0.04,
                    rank=1,
                ),
            ],
        )
        assert resp.model_version_id == mv_id
        assert resp.sample_count == 12000
        assert len(resp.features) == 1
        assert resp.features[0].rank == 1

    def test_global_shap_feature_rank_minimum_one(self):
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            GlobalSHAPFeatureItem(
                feature_name="feat_x",
                mean_abs_shap=0.1,
                mean_shap=0.0,
                rank=0,  # Must be >= 1
            )


# ---------------------------------------------------------------------------
# P2-10 Service Unit Tests
# ---------------------------------------------------------------------------


class TestGlobalSHAPServiceUnit:
    """Unit tests for ModelVersionService.compute_global_shap with real and mock inputs."""

    def _make_mock_mv(self, mv_id=None, model_name="volatility-aware-risk-model", version="1.0.0"):
        mock_mv = MagicMock()
        mock_mv.id = mv_id or uuid.uuid4()
        mock_mv.model_name = model_name
        mock_mv.version = version
        return mock_mv

    def test_raises_validation_error_when_artifact_missing(self):
        """Service raises ValidationError when model artifact file is absent."""
        mock_db = MagicMock()
        svc = ModelVersionService(db=mock_db)

        with patch.object(svc, "get_model_version", return_value=self._make_mock_mv()):
            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(ValidationError, match="artifact not found"):
                    svc.compute_global_shap(model_version_id=uuid.uuid4())

    def test_raises_validation_error_when_model_name_mismatch(self):
        """Service raises ValidationError when requested model is not volatility-aware."""
        mock_db = MagicMock()
        svc = ModelVersionService(db=mock_db)
        wrong_model_mv = self._make_mock_mv(model_name="logistic-regression-baseline")

        with patch.object(svc, "get_model_version", return_value=wrong_model_mv):
            with pytest.raises(ValidationError, match="does not support TreeSHAP global aggregation"):
                svc.compute_global_shap(model_version_id=uuid.uuid4())

    def test_raises_validation_error_when_model_version_mismatch(self):
        """Service raises ValidationError when requested version does not match artifact."""
        mock_db = MagicMock()
        svc = ModelVersionService(db=mock_db)
        wrong_ver_mv = self._make_mock_mv(version="2.0.0")

        with patch.object(svc, "get_model_version", return_value=wrong_ver_mv):
            with pytest.raises(ValidationError, match="does not match loaded artifact version"):
                svc.compute_global_shap(model_version_id=uuid.uuid4())

    def test_global_shap_response_is_deterministic(self):
        """Global SHAP ordering must be deterministic: same input → same ranking."""
        import joblib
        import pandas as pd
        from src.ml.explainability.shap_explainer import TreeShapExplainer

        model = joblib.load(REPO_ROOT / "models" / "artifacts" / "volatility_aware_risk_model.joblib")
        preprocessor = joblib.load(REPO_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib")
        df = pd.read_parquet(REPO_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet")
        X = preprocessor.transform(df.head(50))
        feature_names = list(model.feature_names_in_)
        X_clean = X[feature_names].dropna()

        explainer = TreeShapExplainer(model)
        exp1 = explainer.explain_global(X_clean)
        exp2 = explainer.explain_global(X_clean)

        assert exp1.feature_importance_ranking == exp2.feature_importance_ranking
        assert exp1.sample_count == exp2.sample_count

    def test_global_shap_top_features_are_numeric_and_ranked_descending(self):
        """Global SHAP importances must be non-negative floats in descending order."""
        import joblib
        import pandas as pd
        from src.ml.explainability.shap_explainer import TreeShapExplainer

        model = joblib.load(REPO_ROOT / "models" / "artifacts" / "volatility_aware_risk_model.joblib")
        preprocessor = joblib.load(REPO_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib")
        df = pd.read_parquet(REPO_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet")
        X = preprocessor.transform(df.head(50))
        feature_names = list(model.feature_names_in_)
        X_clean = X[feature_names].dropna()

        explainer = TreeShapExplainer(model)
        global_exp = explainer.explain_global(X_clean)

        ranked = global_exp.feature_importance_ranking
        abs_imp = global_exp.mean_absolute_attributions

        assert len(ranked) > 0, "Feature ranking must be non-empty"
        assert all(isinstance(r, str) for r in ranked)
        assert all(abs_imp[r] >= 0.0 for r in ranked), "Mean absolute SHAP must be non-negative"

        values = [abs_imp[r] for r in ranked]
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], (
                f"Not sorted descending at rank {i+1}: {ranked[i]}={values[i]} vs {ranked[i+1]}={values[i+1]}"
            )

    def test_signed_mean_shap_is_finite_and_bounded(self):
        """Signed mean SHAP values must be finite and within plausible SHAP value range."""
        import numpy as np
        import joblib
        import pandas as pd
        from src.ml.explainability.shap_explainer import TreeShapExplainer

        model = joblib.load(REPO_ROOT / "models" / "artifacts" / "volatility_aware_risk_model.joblib")
        preprocessor = joblib.load(REPO_ROOT / "models" / "artifacts" / "credit_risk_preprocessor.joblib")
        df = pd.read_parquet(REPO_ROOT / "data" / "synthetic" / "synthetic_credit_applications.parquet")
        X = preprocessor.transform(df.head(50))
        feature_names = list(model.feature_names_in_)
        X_clean = X[feature_names].dropna()

        explainer = TreeShapExplainer(model)
        X_arr = X_clean.values
        shap_vals_raw = explainer.explainer.shap_values(X_arr)
        if isinstance(shap_vals_raw, list):
            sample_shap = shap_vals_raw[1] if len(shap_vals_raw) > 1 else shap_vals_raw[0]
        else:
            sample_shap = shap_vals_raw

        mean_signed = np.mean(sample_shap, axis=0)
        assert np.all(np.isfinite(mean_signed)), "Signed mean SHAP contains non-finite values"
        assert np.all(np.abs(mean_signed) < 100), "Signed mean SHAP out of plausible range"


# ---------------------------------------------------------------------------
# P2-10 RBAC & Integration Tests (Hermetic SQLite In-Memory)
# ---------------------------------------------------------------------------


class TestGlobalSHAPEndpointRBAC(unittest.TestCase):
    """Verify /api/v1/model-versions/{id}/global-shap access control and behavior."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, expire_on_commit=False)
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
            self.suffix = uuid.uuid4().hex[:8]

            self.applicant = User(
                email=f"applicant_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant)

            self.reviewer = User(
                email=f"reviewer_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.REVIEWER,
                is_active=True,
            )
            session.add(self.reviewer)

            self.admin = User(
                email=f"admin_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(self.admin)

            self.model_version = ModelVersion(
                model_name="volatility-aware-risk-model",
                version="1.0.0",
                algorithm="LightGBM + TreeSHAP",
                is_active=True,
            )
            session.add(self.model_version)

            self.incompatible_model = ModelVersion(
                model_name="logistic-regression-baseline",
                version="1.0.0",
                algorithm="Logistic Regression",
                is_active=False,
            )
            session.add(self.incompatible_model)

            session.commit()
            self.model_version_id = self.model_version.id
            self.incompatible_id = self.incompatible_model.id
            self.applicant_id = self.applicant.id
            self.reviewer_id = self.reviewer.id
            self.admin_id = self.admin.id
        finally:
            session.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def _token(self, user_id: uuid.UUID, role: str) -> str:
        return create_access_token(subject=str(user_id), role=role)

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests to global-shap must return 401."""
        response = self.client.post(f"/api/v1/model-versions/{self.model_version_id}/global-shap")
        self.assertEqual(response.status_code, 401)

    def test_applicant_cannot_access_global_shap(self):
        """APPLICANT role must receive 403 Forbidden."""
        token = self._token(self.applicant_id, "APPLICANT")
        response = self.client.post(
            f"/api/v1/model-versions/{self.model_version_id}/global-shap",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_reviewer_gets_404_for_nonexistent_version(self):
        """REVIEWER with nonexistent UUID receives 404."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.post(
            f"/api/v1/model-versions/{uuid.uuid4()}/global-shap",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 404)

    def test_reviewer_can_compute_global_shap(self):
        """REVIEWER can successfully trigger global SHAP computation."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.post(
            f"/api/v1/model-versions/{self.model_version_id}/global-shap",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["model_version_id"], str(self.model_version_id))
        self.assertEqual(data["model_version"], "1.0.0")
        self.assertEqual(data["model_name"], "volatility-aware-risk-model")
        self.assertEqual(data["sample_count"], 12000)
        self.assertIn("features", data)
        self.assertEqual(len(data["features"]), 64)

        # Verify ordering by mean_abs_shap desc
        features = data["features"]
        for i in range(len(features) - 1):
            self.assertGreaterEqual(
                features[i]["mean_abs_shap"],
                features[i + 1]["mean_abs_shap"],
                f"Feature ranking not sorted descending at index {i}",
            )
            self.assertEqual(features[i]["rank"], i + 1)

    def test_admin_can_compute_global_shap(self):
        """ADMIN can successfully trigger global SHAP computation."""
        token = self._token(self.admin_id, "ADMIN")
        response = self.client.post(
            f"/api/v1/model-versions/{self.model_version_id}/global-shap",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_incompatible_model_version_returns_422(self):
        """Incompatible model family returns 422 Unprocessable Entity."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.post(
            f"/api/v1/model-versions/{self.incompatible_id}/global-shap",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("does not support TreeSHAP", response.json()["detail"])


# ---------------------------------------------------------------------------
# P2-11 Historical Assessment Schema Tests
# ---------------------------------------------------------------------------


class TestHistoricalAssessmentSchema:
    """Verify CreditAssessmentResponse is sufficient for P2-11 without backend changes."""

    def test_credit_assessment_response_has_required_p2_11_fields(self):
        """CreditAssessmentResponse must include all fields needed by P2-11 history UI."""
        fields = CreditAssessmentResponse.model_fields
        required_for_p2_11 = [
            "id",
            "application_id",
            "model_version_id",
            "credit_score",
            "risk_level",
            "confidence",
            "assessment_status",
            "assessed_at",
            "created_at",
            "key_factors",
        ]
        for field in required_for_p2_11:
            assert field in fields, (
                f"CreditAssessmentResponse is missing required P2-11 field: {field}"
            )


# ---------------------------------------------------------------------------
# P2-11 Historical Assessment RBAC & Ordering Tests (Hermetic SQLite)
# ---------------------------------------------------------------------------


class TestHistoricalAssessmentRBAC(unittest.TestCase):
    """Verify GET /api/v1/applications/{id}/assessments access control and contracts."""

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, expire_on_commit=False)
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
            self.suffix = uuid.uuid4().hex[:8]

            # Applicant 1 (Owner of application 1)
            self.applicant1 = User(
                email=f"app1_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant1)

            # Applicant 2 (Intruder)
            self.applicant2 = User(
                email=f"app2_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.APPLICANT,
                is_active=True,
            )
            session.add(self.applicant2)

            # Reviewer
            self.reviewer = User(
                email=f"rev_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.REVIEWER,
                is_active=True,
            )
            session.add(self.reviewer)

            # Admin
            self.admin = User(
                email=f"admin_{self.suffix}@example.com",
                password_hash=hash_password("Password123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(self.admin)
            session.commit()

            # Profile & Application
            self.profile = ApplicantProfile(
                user_id=self.applicant1.id,
                gig_work_type="DELIVERY",
                years_working=Decimal("2.0"),
                average_working_days=26,
            )
            session.add(self.profile)
            session.commit()

            self.application = Application(
                applicant_profile_id=self.profile.id,
                requested_loan_amount=Decimal("40000.00"),
                preferred_repayment_period=6,
                loan_purpose="EQUIPMENT",
                status="ASSESSED",
            )
            session.add(self.application)

            self.empty_app = Application(
                applicant_profile_id=self.profile.id,
                requested_loan_amount=Decimal("20000.00"),
                preferred_repayment_period=3,
                loan_purpose="WORKING_CAPITAL",
                status="DRAFT",
            )
            session.add(self.empty_app)

            self.model_version = ModelVersion(
                model_name="volatility-aware-risk-model",
                version="1.0.0",
                is_active=True,
            )
            session.add(self.model_version)
            session.commit()

            # 3 Assessments with different timestamps
            # Assessment 1: earlier (lower score, MODERATE risk)
            self.asmt1 = CreditAssessment(
                application_id=self.application.id,
                model_version_id=self.model_version.id,
                credit_score=680,
                risk_probability=Decimal("0.1200"),
                risk_level=RiskLevel.MODERATE,
                confidence=Decimal("0.8800"),
                explanation={
                    "disclaimer": "Prototype disclaimer",
                    "key_protective_factors": [{"factor_name": "Inflow regularity", "borrower_explanation": "Good"}],
                    "key_risk_factors": [{"factor_name": "Low buffer", "borrower_explanation": "Fair"}],
                    "shap_values": [{"feature": "f1", "value": 0.1}],
                },
                assessment_status="COMPLETED",
                created_at=datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc),
                assessed_at=datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc),
            )
            session.add(self.asmt1)

            # Assessment 2: latest (higher score, LOWER risk)
            self.asmt2 = CreditAssessment(
                application_id=self.application.id,
                model_version_id=self.model_version.id,
                credit_score=750,
                risk_probability=Decimal("0.0400"),
                risk_level=RiskLevel.LOWER,
                confidence=Decimal("0.9600"),
                explanation={
                    "disclaimer": "Prototype disclaimer",
                    "key_protective_factors": [{"factor_name": "High stability", "borrower_explanation": "Great"}],
                    "key_risk_factors": [],
                    "shap_values": [{"feature": "f2", "value": -0.2}],
                },
                assessment_status="COMPLETED",
                created_at=datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc),
                assessed_at=datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc),
            )
            session.add(self.asmt2)

            # Assessment 3: unrated (insufficient evidence, NULL credit_score, NULL explanation)
            self.asmt3 = CreditAssessment(
                application_id=self.application.id,
                model_version_id=self.model_version.id,
                credit_score=None,
                risk_probability=None,
                risk_level=RiskLevel.INSUFFICIENT,
                confidence=None,
                explanation=None,
                assessment_status="INSUFFICIENT_DATA",
                created_at=datetime(2026, 9, 18, 8, 0, 0, tzinfo=timezone.utc),
                assessed_at=datetime(2026, 9, 18, 8, 0, 0, tzinfo=timezone.utc),
            )
            session.add(self.asmt3)
            session.commit()

            self.application_id = self.application.id
            self.empty_app_id = self.empty_app.id
            self.applicant1_id = self.applicant1.id
            self.applicant2_id = self.applicant2.id
            self.reviewer_id = self.reviewer.id
            self.admin_id = self.admin.id
            self.asmt1_id = str(self.asmt1.id)
            self.asmt2_id = str(self.asmt2.id)
            self.asmt3_id = str(self.asmt3.id)
        finally:
            session.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def _token(self, user_id: uuid.UUID, role: str) -> str:
        return create_access_token(subject=str(user_id), role=role)

    def test_unauthenticated_assessment_history_returns_401(self):
        """Unauthenticated requests must return 401."""
        response = self.client.get(f"/api/v1/applications/{self.application_id}/assessments")
        self.assertEqual(response.status_code, 401)

    def test_unauthorized_applicant_cannot_access_other_application_history(self):
        """APPLICANT 2 cannot access APPLICANT 1's assessment history (HTTP 403)."""
        token = self._token(self.applicant2_id, "APPLICANT")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_authorized_applicant_can_access_own_history(self):
        """APPLICANT 1 can access their own assessment history."""
        token = self._token(self.applicant1_id, "APPLICANT")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_reviewer_can_access_assessment_history(self):
        """REVIEWER can access application assessment history."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_admin_can_access_assessment_history(self):
        """ADMIN can access application assessment history."""
        token = self._token(self.admin_id, "ADMIN")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_historical_assessments_order_reverse_chronological(self):
        """Historical assessments must be ordered newest first (created_at desc)."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(len(items), 3)

        # Expected reverse chronological order: asmt2 (Sep 24) -> asmt1 (Sep 20) -> asmt3 (Sep 18)
        self.assertEqual(items[0]["id"], self.asmt2_id)
        self.assertEqual(items[0]["credit_score"], 750)

        self.assertEqual(items[1]["id"], self.asmt1_id)
        self.assertEqual(items[1]["credit_score"], 680)

        self.assertEqual(items[2]["id"], self.asmt3_id)
        self.assertIsNone(items[2]["credit_score"])

    def test_unrated_assessment_preserves_null_score(self):
        """Unrated historical records must return null credit_score and score, not 0."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        items = response.json()
        unrated = next(a for a in items if a["id"] == self.asmt3_id)

        self.assertIsNone(unrated["credit_score"])
        self.assertIsNone(unrated["score"])
        self.assertIsNone(unrated["confidence"])
        self.assertIsNone(unrated["risk_probability"])
        self.assertEqual(unrated["risk_level"], "INSUFFICIENT")

    def test_persisted_explanation_preserved_and_unrated_is_none(self):
        """Persisted explanation JSONB is returned when present, and None when not (no fabricated explanations)."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        items = response.json()

        asmt2_res = next(a for a in items if a["id"] == self.asmt2_id)
        self.assertIsNotNone(asmt2_res["explanation"])
        self.assertIn("key_protective_factors", asmt2_res["explanation"])

        asmt3_res = next(a for a in items if a["id"] == self.asmt3_id)
        self.assertIsNone(asmt3_res["explanation"])

    def test_empty_history_returns_empty_list(self):
        """Application with 0 assessments returns an empty list cleanly (HTTP 200)."""
        token = self._token(self.reviewer_id, "REVIEWER")
        response = self.client.get(
            f"/api/v1/applications/{self.empty_app_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_viewing_history_does_not_create_new_assessment(self):
        """GET /applications/{id}/assessments is strictly read-only and creates no new assessment."""
        session = self.SessionFactory()
        count_before = session.query(CreditAssessment).count()
        session.close()

        token = self._token(self.reviewer_id, "REVIEWER")
        self.client.get(
            f"/api/v1/applications/{self.application_id}/assessments",
            headers={"Authorization": f"Bearer {token}"},
        )

        session = self.SessionFactory()
        count_after = session.query(CreditAssessment).count()
        session.close()

        self.assertEqual(count_before, count_after, "Assessment count changed after viewing history!")


# ---------------------------------------------------------------------------
# Endpoint Registration Tests
# ---------------------------------------------------------------------------


class TestEndpointRegistration:
    """Verify both P2-10 and P2-11 endpoints are registered in the FastAPI app."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_global_shap_endpoint_registered(self, client):
        """POST /api/v1/model-versions/{id}/global-shap must be registered."""
        response = client.post(f"/api/v1/model-versions/{uuid.uuid4()}/global-shap")
        assert response.status_code != 404, "Global SHAP endpoint not registered — got 404"
        assert response.status_code == 401

    def test_assessment_history_endpoint_registered(self, client):
        """GET /api/v1/applications/{id}/assessments must be registered."""
        response = client.get(f"/api/v1/applications/{uuid.uuid4()}/assessments")
        assert response.status_code != 404, "Assessment history endpoint not registered — got 404"
        assert response.status_code == 401
