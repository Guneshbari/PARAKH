"""Test fixtures and reusable helper utilities for the PARAKH test suite."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Generator, Optional, Tuple
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, SessionLocal
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
    ConsentRepository,
    FinancialSignalRepository,
    ModelVersionRepository,
    ReviewRepository,
    UserRepository,
)


def can_connect_to_postgres() -> bool:
    """Helper to detect if live PostgreSQL is reachable."""
    try:
        engine_pg = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 1})
        with engine_pg.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine_pg.dispose()
        return True
    except Exception:
        return False


def create_in_memory_engine() -> Engine:
    """Create an isolated, thread-safe SQLite in-memory engine sharing a single pool."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@contextmanager
def in_memory_db_session() -> Generator[Session, None, None]:
    """Yield a database session bound to an in-memory SQLite schema."""
    engine_mem = create_in_memory_engine()
    Base.metadata.create_all(engine_mem)
    test_sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine_mem)
    session = test_sessionmaker()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine_mem)
        engine_mem.dispose()


# ---------------------------------------------------------------------------
# FACTORY HELPERS
# ---------------------------------------------------------------------------

def create_test_user(
    db: Session,
    email: Optional[str] = None,
    password: str = "Password123!",
    role: UserRole = UserRole.APPLICANT,
    is_active: bool = True,
    commit: bool = True,
) -> User:
    """Create and persist a test User entity."""
    if not email:
        email = f"test_{role.value.lower()}_{uuid.uuid4().hex[:8]}@example.com"
    repo = UserRepository(db=db)
    user = repo.create(
        {
            "email": email,
            "password_hash": hash_password(password),
            "role": role,
            "is_active": is_active,
        },
        commit=commit,
    )
    return user


def create_applicant_user(
    db: Session,
    email: Optional[str] = None,
    password: str = "Password123!",
    commit: bool = True,
) -> User:
    """Convenience helper to create an APPLICANT user."""
    return create_test_user(db, email=email, password=password, role=UserRole.APPLICANT, commit=commit)


def create_reviewer_user(
    db: Session,
    email: Optional[str] = None,
    password: str = "Password123!",
    commit: bool = True,
) -> User:
    """Convenience helper to create a REVIEWER user."""
    return create_test_user(db, email=email, password=password, role=UserRole.REVIEWER, commit=commit)


def create_admin_user(
    db: Session,
    email: Optional[str] = None,
    password: str = "Password123!",
    commit: bool = True,
) -> User:
    """Convenience helper to create an ADMIN user."""
    return create_test_user(db, email=email, password=password, role=UserRole.ADMIN, commit=commit)


def get_auth_token_and_headers(user_id: Any, role: Any = "APPLICANT") -> Tuple[str, Dict[str, str]]:
    """Generate a valid JWT token and bearer authorization headers for testing."""
    role_str = role.value if hasattr(role, "value") else str(role)
    token = create_access_token(subject=str(user_id), role=role_str)
    return token, {"Authorization": f"Bearer {token}"}


def create_test_applicant_profile(
    db: Session,
    user_id: Any,
    gig_work_type: str = "Ride Hailing & Delivery",
    years_working: Decimal = Decimal("2.5"),
    average_working_days: int = 24,
    business_or_loan_purpose: str = "Vehicle repair and fuel advance",
    commit: bool = True,
) -> ApplicantProfile:
    """Create and persist an ApplicantProfile entity."""
    repo = ApplicantRepository(db=db)
    profile = repo.create(
        {
            "user_id": user_id,
            "gig_work_type": gig_work_type,
            "years_working": years_working,
            "average_working_days": average_working_days,
            "business_or_loan_purpose": business_or_loan_purpose,
        },
        commit=commit,
    )
    return profile


def create_test_application(
    db: Session,
    applicant_profile_id: Any,
    requested_loan_amount: Decimal = Decimal("25000.00"),
    loan_purpose: str = "Working capital for delivery gear",
    preferred_repayment_period: int = 6,
    status: ApplicationStatus = ApplicationStatus.DRAFT,
    commit: bool = True,
) -> Application:
    """Create and persist an Application entity."""
    repo = ApplicationRepository(db=db)
    app_entity = repo.create(
        {
            "applicant_profile_id": applicant_profile_id,
            "requested_loan_amount": requested_loan_amount,
            "loan_purpose": loan_purpose,
            "preferred_repayment_period": preferred_repayment_period,
            "status": status,
        },
        commit=commit,
    )
    return app_entity


def create_test_consent(
    db: Session,
    application_id: Any,
    data_source: ConsentDataSource = ConsentDataSource.PLATFORM,
    purpose: str = "Income and platform score assessment",
    granted: bool = True,
    commit: bool = True,
) -> Consent:
    """Create and persist a Consent entity."""
    repo = ConsentRepository(db=db)
    now = datetime.now(timezone.utc)
    consent = repo.create(
        {
            "application_id": application_id,
            "data_source": data_source,
            "purpose": purpose,
            "granted": granted,
            "granted_at": now if granted else None,
            "revoked_at": None,
        },
        commit=commit,
    )
    return consent


def create_test_financial_signal(
    db: Session,
    application_id: Any,
    source: SignalSource = SignalSource.PLATFORM,
    average_income: Decimal = Decimal("32500.00"),
    median_income: Decimal = Decimal("31000.00"),
    income_volatility: Decimal = Decimal("0.12"),
    payment_regularity: Decimal = Decimal("0.96"),
    platform_rating: Decimal = Decimal("4.85"),
    active_days: int = 85,
    commit: bool = True,
) -> FinancialSignal:
    """Create and persist a FinancialSignal entity."""
    repo = FinancialSignalRepository(db=db)
    signal = repo.create(
        {
            "application_id": application_id,
            "source": source,
            "average_income": average_income,
            "median_income": median_income,
            "income_volatility": income_volatility,
            "payment_regularity": payment_regularity,
            "platform_rating": platform_rating,
            "active_days": active_days,
        },
        commit=commit,
    )
    return signal


def create_test_model_version(
    db: Session,
    version_name: Optional[str] = None,
    is_active: bool = True,
    description: str = "PARAKH Deterministic Mock Scoring Engine",
    commit: bool = True,
) -> ModelVersion:
    """Create and persist a ModelVersion entity."""
    if not version_name:
        version_name = f"v-mock-{uuid.uuid4().hex[:6]}"
    repo = ModelVersionRepository(db=db)
    model_ver = repo.create(
        {
            "version_name": version_name,
            "is_active": is_active,
            "description": description,
            "features": {"metrics": ["average_income", "payment_regularity", "platform_rating"]},
        },
        commit=commit,
    )
    return model_ver


def create_test_assessment(
    db: Session,
    application_id: Any,
    model_version_id: Any,
    credit_score: int = 740,
    risk_probability: Decimal = Decimal("0.1200"),
    risk_level: RiskLevel = RiskLevel.LOWER,
    confidence: Decimal = Decimal("0.9200"),
    assessment_status: str = "COMPLETED",
    commit: bool = True,
) -> CreditAssessment:
    """Create and persist a CreditAssessment entity."""
    repo = AssessmentRepository(db=db)
    now = datetime.now(timezone.utc)
    assessment = repo.create(
        {
            "application_id": application_id,
            "model_version_id": model_version_id,
            "credit_score": credit_score,
            "risk_probability": risk_probability,
            "risk_level": risk_level,
            "confidence": confidence,
            "assessment_status": assessment_status,
            "assessed_at": now,
            "raw_output": {
                "decision": "APPROVED",
                "rules_triggered": ["CONSISTENT_EARNINGS", "HIGH_CUSTOMER_RATING"],
            },
        },
        commit=commit,
    )
    return assessment


def create_test_review(
    db: Session,
    application_id: Any,
    reviewer_id: Any,
    outcome: ReviewOutcomeType = ReviewOutcomeType.REVIEWED,
    recommendation: str = "Recommend approval for requested loan amount",
    notes: str = "Steady earnings and strong repayment history verified",
    commit: bool = True,
) -> ReviewOutcome:
    """Create and persist a ReviewOutcome entity."""
    repo = ReviewRepository(db=db)
    review = repo.create(
        {
            "application_id": application_id,
            "reviewer_id": reviewer_id,
            "outcome": outcome,
            "recommendation": recommendation,
            "notes": notes,
        },
        commit=commit,
    )
    return review


# ---------------------------------------------------------------------------
# DATABASE CLEANUP HELPERS
# ---------------------------------------------------------------------------

def cleanup_database_records(db: Session, record_tuples: list) -> None:
    """
    Clean up records by entity type and ID in reverse dependency order.
    record_tuples: list of (entity_type_str, id_or_uuid)
    """
    type_to_table = {
        "review": "review_outcomes",
        "assessment": "credit_assessments",
        "financial_signal": "financial_signals",
        "consent": "consents",
        "application": "applications",
        "applicant": "applicant_profiles",
        "model_version": "model_versions",
        "user": "users",
        "audit_log": "audit_logs",
    }
    for entity_type, entity_id in reversed(record_tuples):
        tbl = type_to_table.get(entity_type)
        if tbl:
            try:
                db.execute(text(f"DELETE FROM {tbl} WHERE id = :id"), {"id": str(entity_id)})
                db.commit()
            except Exception:
                db.rollback()


def truncate_all_test_tables(db: Session) -> None:
    """Truncate or delete all rows across all 9 domain tables plus audit logs."""
    tables = [
        "review_outcomes",
        "credit_assessments",
        "financial_signals",
        "consents",
        "applications",
        "applicant_profiles",
        "model_versions",
        "audit_logs",
        "users",
    ]
    for tbl in tables:
        try:
            db.execute(text(f"DELETE FROM {tbl}"))
            db.commit()
        except Exception:
            db.rollback()
