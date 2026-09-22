"""Comprehensive end-to-end persistence and relationship verification tests.

Verifies the complete target entity chain:
User -> ApplicantProfile -> Application -> Consent / FinancialSignal / CreditAssessment / ReviewOutcome / AuditLog
survives across distinct database sessions and connection restarts.
"""
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Generator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.assessment.mock import MockAssessmentEngine
from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    ApplicantProfile,
    Application,
    ApplicationStatus,
    AuditLog,
    Base,
    Consent,
    ConsentDataSource,
    CreditAssessment,
    FinancialSignal,
    ModelVersion,
    ReviewOutcome,
    ReviewOutcomeType,
    RiskLevel,
    SignalSource,
    User,
    UserRole,
)
from app.repositories import (
    ApplicantRepository,
    ApplicationRepository,
    AssessmentRepository,
    AuditRepository,
    ConsentRepository,
    FinancialSignalRepository,
    ModelVersionRepository,
    ReviewRepository,
    UserRepository,
)
from app.services import (
    ApplicantService,
    ApplicationService,
    AssessmentService,
    AuditService,
    ConsentService,
    FinancialSignalService,
    ReviewService,
)


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable without hanging."""
    try:
        engine_pg = create_engine(
            settings.DATABASE_URL,
            connect_args={"connect_timeout": 1},
        )
        with engine_pg.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine_pg.dispose()
        return True
    except Exception:
        return False


class TestEndToEndPersistenceChain(unittest.TestCase):
    """End-to-end persistence integration tests verifying data survival across separate sessions."""

    def setUp(self):
        """Create a shared in-memory SQLite database using StaticPool."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionFactory = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def tearDown(self):
        """Clean up database tables and dispose engine."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_complete_application_persistence_chain_across_sessions(self):
        """Verify the complete 13-step persistence flow across separate database sessions.

        Chain:
        Application -> FinancialSignal -> CreditAssessment -> ReviewOutcome -> AuditLog
        """
        # =====================================================================
        # SESSION 1: Create, orchestrate, and commit the complete chain
        # =====================================================================
        session1: Session = self.SessionFactory()

        try:
            # 1. Create applicant and reviewer users
            user_repo = UserRepository(db=session1)
            applicant_user = user_repo.create(
                {
                    "email": "persist_worker@parakh.in",
                    "password_hash": hash_password("WorkerSecurePass123!"),
                    "role": UserRole.APPLICANT,
                    "is_active": True,
                },
                commit=False,
            )
            reviewer_user = user_repo.create(
                {
                    "email": "persist_reviewer@parakh.in",
                    "password_hash": hash_password("ReviewerSecurePass123!"),
                    "role": UserRole.REVIEWER,
                    "is_active": True,
                },
                commit=False,
            )
            session1.flush()

            applicant_user_id = applicant_user.id
            reviewer_user_id = reviewer_user.id
            self.assertIsNotNone(applicant_user_id)
            self.assertIsNotNone(reviewer_user_id)

            # 2. Create ApplicantProfile linked to applicant user
            applicant_repo = ApplicantRepository(db=session1)
            profile = applicant_repo.create(
                {
                    "user_id": applicant_user_id,
                    "gig_work_type": "quick-commerce delivery",
                    "years_working": Decimal("3.2"),
                    "average_working_days": 26,
                    "business_or_loan_purpose": "Electric two-wheeler battery replacement",
                },
                commit=False,
            )
            session1.flush()
            profile_id = profile.id
            self.assertIsNotNone(profile_id)

            # 3. Create Application linked to profile using ApplicationService
            app_service = ApplicationService(db=session1)
            app = app_service.create_application(
                {
                    "applicant_profile_id": profile_id,
                    "requested_loan_amount": Decimal("35000.00"),
                    "loan_purpose": "Working capital for delivery fleet equipment",
                    "preferred_repayment_period": 12,
                },
                auto_commit=False,
            )
            session1.flush()
            app_id = app.id
            self.assertIsNotNone(app_id)

            # Transition application to SUBMITTED and UNDER_REVIEW for full pipeline
            app = app_service.update_status(app_id, ApplicationStatus.SUBMITTED, auto_commit=False)
            app = app_service.update_status(app_id, ApplicationStatus.UNDER_REVIEW, auto_commit=False)
            session1.flush()

            # 4. Create Consent using ConsentService
            consent_service = ConsentService(db=session1)
            consent = consent_service.create_consent(
                {
                    "application_id": app_id,
                    "applicant_profile_id": profile_id,
                    "data_source": ConsentDataSource.PLATFORM,
                    "purpose": "Alternative credit assessment and scoring",
                    "granted": True,
                },
                auto_commit=False,
            )
            session1.flush()
            consent_id = consent.id
            self.assertIsNotNone(consent_id)

            # 5. Create FinancialSignal data for the application using FinancialSignalService
            signal_service = FinancialSignalService(db=session1, consent_service=consent_service)
            signal = signal_service.create_signal(
                {
                    "application_id": app_id,
                    "applicant_profile_id": profile_id,
                    "source": SignalSource.PLATFORM,
                    "average_income": Decimal("36500.00"),
                    "median_income": Decimal("35000.00"),
                    "income_volatility": Decimal("0.1200"),
                    "income_trend": "positive",
                    "active_days": 28,
                    "payment_regularity": Decimal("0.9400"),
                    "cashflow_buffer": Decimal("7200.00"),
                    "existing_obligation": Decimal("2800.00"),
                    "platform_rating": Decimal("4.88"),
                    "repayment_reliability": Decimal("0.9600"),
                    "signal_metadata": {"verified_orders_count": 420, "platform_tier": "gold"},
                },
                enforce_consent=True,
                auto_commit=False,
            )
            session1.flush()
            signal_id = signal.id
            self.assertIsNotNone(signal_id)

            # 6. Register ModelVersion
            mv_repo = ModelVersionRepository(db=session1)
            model_version = mv_repo.create(
                {
                    "model_name": "parakh-mock-engine",
                    "version": "1.0.0",
                    "algorithm": "DeterministicRuleMock",
                    "description": "Deterministic rule engine for alternative credit scoring",
                    "is_active": True,
                },
                commit=False,
            )
            session1.flush()
            mv_id = model_version.id
            self.assertIsNotNone(mv_id)

            # 7. Run MockAssessmentEngine through AssessmentService
            mock_engine = MockAssessmentEngine()
            assessment_service = AssessmentService(db=session1, engine=mock_engine)
            assessment = assessment_service.assess_application(
                application_id=app_id,
                model_version_id=mv_id,
                auto_commit=False,
            )
            session1.flush()
            assessment_id = assessment.id
            self.assertIsNotNone(assessment_id)

            # 8. Create ReviewOutcome for the application using ReviewService
            review_service = ReviewService(db=session1)
            review = review_service.create_review(
                {
                    "application_id": app_id,
                    "reviewer_id": reviewer_user_id,
                    "outcome": ReviewOutcomeType.REVIEWED,
                    "notes": "Verified verified gig partner metrics; steady income flow with adequate buffer.",
                },
                auto_commit=False,
            )
            session1.flush()
            review_id = review.id
            self.assertIsNotNone(review_id)

            # 9. Verify AuditLog records exist in session 1 before commit
            audit_repo = AuditRepository(db=session1)
            app_audits = audit_repo.get_by_application(app_id)
            self.assertGreaterEqual(len(app_audits), 4)

            # 10. Commit all records to the database and close Session 1
            session1.commit()
        finally:
            session1.close()

        # =====================================================================
        # SESSION 2: Open a completely new session and verify full retrieval
        # =====================================================================
        session2: Session = self.SessionFactory()

        try:
            # 11. Retrieve the application using ApplicationRepository in Session 2
            app_repo2 = ApplicationRepository(db=session2)
            retrieved_app = app_repo2.get_by_id(app_id)

            # 12 & 13. Verify the complete relationship and data chain
            self.assertIsNotNone(retrieved_app, "Application must persist into new session")
            self.assertEqual(retrieved_app.id, app_id)
            self.assertEqual(retrieved_app.requested_loan_amount, Decimal("35000.00"))
            self.assertEqual(retrieved_app.preferred_repayment_period, 12)

            # A. Verify User & ApplicantProfile navigation
            self.assertIsNotNone(retrieved_app.applicant_profile)
            self.assertEqual(retrieved_app.applicant_profile.id, profile_id)
            self.assertEqual(retrieved_app.applicant_profile.gig_work_type, "quick-commerce delivery")
            self.assertEqual(retrieved_app.applicant_profile.years_working, Decimal("3.2"))
            self.assertEqual(retrieved_app.applicant_profile.average_working_days, 26)

            self.assertIsNotNone(retrieved_app.applicant_profile.user)
            self.assertEqual(retrieved_app.applicant_profile.user.id, applicant_user_id)
            self.assertEqual(retrieved_app.applicant_profile.user.email, "persist_worker@parakh.in")
            self.assertEqual(retrieved_app.applicant_profile.user.role, UserRole.APPLICANT)
            self.assertTrue(retrieved_app.applicant_profile.user.is_active)

            # B. Verify Consents navigation
            self.assertEqual(len(retrieved_app.consents), 1)
            persisted_consent = retrieved_app.consents[0]
            self.assertEqual(persisted_consent.id, consent_id)
            self.assertEqual(persisted_consent.data_source, ConsentDataSource.PLATFORM)
            self.assertTrue(persisted_consent.granted)
            self.assertIsNone(persisted_consent.revoked_at)
            self.assertIsNotNone(persisted_consent.granted_at)

            # C. Verify FinancialSignals navigation
            self.assertEqual(len(retrieved_app.financial_signals), 1)
            persisted_signal = retrieved_app.financial_signals[0]
            self.assertEqual(persisted_signal.id, signal_id)
            self.assertEqual(persisted_signal.source, SignalSource.PLATFORM)
            self.assertEqual(persisted_signal.average_income, Decimal("36500.00"))
            self.assertEqual(persisted_signal.median_income, Decimal("35000.00"))
            self.assertEqual(persisted_signal.cashflow_buffer, Decimal("7200.00"))
            self.assertEqual(persisted_signal.existing_obligation, Decimal("2800.00"))
            self.assertEqual(persisted_signal.platform_rating, Decimal("4.88"))
            self.assertEqual(persisted_signal.signal_metadata.get("platform_tier"), "gold")
            self.assertIsNotNone(persisted_signal.created_at)

            # D. Verify CreditAssessments navigation & ModelVersion linkage
            self.assertEqual(len(retrieved_app.credit_assessments), 1)
            persisted_assessment = retrieved_app.credit_assessments[0]
            self.assertEqual(persisted_assessment.id, assessment_id)
            self.assertIsNotNone(persisted_assessment.credit_score)
            self.assertGreaterEqual(persisted_assessment.credit_score, 300)
            self.assertLessEqual(persisted_assessment.credit_score, 850)
            self.assertIn(persisted_assessment.risk_level, [RiskLevel.LOWER, RiskLevel.MODERATE, RiskLevel.HIGHER])
            self.assertIsNotNone(persisted_assessment.confidence)
            self.assertIsNotNone(persisted_assessment.model_version)
            self.assertEqual(persisted_assessment.model_version.id, mv_id)
            self.assertEqual(persisted_assessment.model_version.model_name, "parakh-mock-engine")
            self.assertEqual(persisted_assessment.model_version.version, "1.0.0")

            # E. Verify ReviewOutcomes navigation & Reviewer linkage
            self.assertEqual(len(retrieved_app.review_outcomes), 1)
            persisted_review = retrieved_app.review_outcomes[0]
            self.assertEqual(persisted_review.id, review_id)
            self.assertEqual(persisted_review.outcome, ReviewOutcomeType.REVIEWED)
            self.assertIn("Verified verified gig partner metrics", persisted_review.notes)
            self.assertIsNotNone(persisted_review.reviewer)
            self.assertEqual(persisted_review.reviewer.id, reviewer_user_id)
            self.assertEqual(persisted_review.reviewer.email, "persist_reviewer@parakh.in")
            self.assertEqual(persisted_review.reviewer.role, UserRole.REVIEWER)

            # F. Verify AuditLogs navigation
            self.assertGreaterEqual(len(retrieved_app.audit_logs), 4)
            recorded_actions = {log.action for log in retrieved_app.audit_logs}
            self.assertIn("APPLICATION_CREATED", recorded_actions)
            self.assertIn("CONSENT_GRANTED", recorded_actions)
            self.assertIn("FINANCIAL_SIGNAL_CREATED", recorded_actions)
            self.assertIn("ASSESSMENT_EXECUTED", recorded_actions)
            self.assertIn("REVIEW_CREATED", recorded_actions)

            for log in retrieved_app.audit_logs:
                self.assertEqual(log.application_id, app_id)
                self.assertIsNotNone(log.created_at)
                self.assertIsNotNone(log.audit_metadata)
        finally:
            session2.close()

    def test_disk_file_sqlite_engine_restart_persistence(self):
        """Verify that committed records survive a complete database engine disconnect and restart."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            # 1. First Engine and Session: Initialize schema and insert records
            disk_engine_1 = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(disk_engine_1)
            SessionDisk1 = sessionmaker(bind=disk_engine_1)

            session = SessionDisk1()
            user = User(
                email="disk_restart_worker@parakh.in",
                role=UserRole.APPLICANT,
            )
            session.add(user)
            session.commit()
            user_id = user.id

            profile = ApplicantProfile(
                user_id=user_id,
                gig_work_type="courier delivery",
            )
            session.add(profile)
            session.commit()
            profile_id = profile.id

            application = Application(
                applicant_profile_id=profile_id,
                requested_loan_amount=Decimal("20000.00"),
                status=ApplicationStatus.SUBMITTED,
            )
            session.add(application)
            session.commit()
            app_id = application.id

            session.close()

            # 2. Simulate complete application shutdown: dispose original engine
            disk_engine_1.dispose()

            # 3. Second Engine and Session: Reconnect fresh to the file on disk
            disk_engine_2 = create_engine(f"sqlite:///{db_path}")
            SessionDisk2 = sessionmaker(bind=disk_engine_2)
            fresh_session = SessionDisk2()

            try:
                # Query application using clean session
                recovered_app = fresh_session.get(Application, app_id)
                self.assertIsNotNone(recovered_app)
                self.assertEqual(recovered_app.id, app_id)
                self.assertEqual(recovered_app.requested_loan_amount, Decimal("20000.00"))
                self.assertEqual(recovered_app.status, ApplicationStatus.SUBMITTED)

                # Verify relationship traversal works after restart
                self.assertIsNotNone(recovered_app.applicant_profile)
                self.assertEqual(recovered_app.applicant_profile.id, profile_id)
                self.assertEqual(recovered_app.applicant_profile.user.email, "disk_restart_worker@parakh.in")
            finally:
                fresh_session.close()
                disk_engine_2.dispose()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestPostgreSqlPersistenceIntegration(unittest.TestCase):
    """Live PostgreSQL database persistence integration verification."""

    def test_live_postgresql_persistence_verification(self):
        """Execute the end-to-end chain against live PostgreSQL or report availability."""
        if not can_connect_to_postgres():
            self.skipTest(
                "POSTGRESQL NOT AVAILABLE — PERSISTENCE VERIFICATION NOT COMPLETED. "
                f"Cannot connect to {settings.DATABASE_URL}."
            )

        pg_engine = create_engine(settings.DATABASE_URL)
        PgSession = sessionmaker(bind=pg_engine)
        session = PgSession()

        try:
            # Verify connectivity with raw query
            with pg_engine.connect() as conn:
                res = conn.execute(text("SELECT 1")).scalar()
                self.assertEqual(res, 1)

            # Cleanup helper list
            cleanup_users = []
            test_suffix = uuid.uuid4().hex[:8]

            try:
                user = User(
                    email=f"pg_persist_{test_suffix}@parakh.test",
                    role=UserRole.APPLICANT,
                )
                session.add(user)
                session.commit()
                cleanup_users.append(user.id)

                profile = ApplicantProfile(
                    user_id=user.id,
                    gig_work_type="ride hailing",
                    years_working=Decimal("2.5"),
                    average_working_days=25,
                )
                session.add(profile)
                session.commit()

                app = Application(
                    applicant_profile_id=profile.id,
                    requested_loan_amount=Decimal("40000.00"),
                    status=ApplicationStatus.SUBMITTED,
                )
                session.add(app)
                session.commit()
                app_id = app.id

                # Close session and retrieve via new session
                session.close()

                session2 = PgSession()
                retrieved = session2.get(Application, app_id)
                self.assertIsNotNone(retrieved)
                self.assertEqual(retrieved.requested_loan_amount, Decimal("40000.00"))
                self.assertEqual(retrieved.applicant_profile.user.email, f"pg_persist_{test_suffix}@parakh.test")
                session2.close()

            finally:
                # Cleanup test records
                if cleanup_users:
                    clean_session = PgSession()
                    for uid in cleanup_users:
                        u = clean_session.get(User, uid)
                        if u:
                            clean_session.delete(u)
                    clean_session.commit()
                    clean_session.close()
        finally:
            pg_engine.dispose()


if __name__ == "__main__":
    unittest.main()
