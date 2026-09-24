#!/bin/sh
set -e

echo "Waiting for PostgreSQL database connection..."
python - << 'EOF'
import os
import sys
import time

db_url = os.environ.get("DATABASE_URL", "")
# Convert SQLAlchemy dialect format to standard PostgreSQL URI for psycopg
clean_url = db_url.replace("postgresql+psycopg://", "postgresql://")

import psycopg

max_retries = 30
for i in range(max_retries):
    try:
        with psycopg.connect(clean_url, connect_timeout=3) as conn:
            print("PostgreSQL database is ready!")
            sys.exit(0)
    except Exception as exc:
        print(f"Waiting for PostgreSQL... ({i+1}/{max_retries})")
        time.sleep(1)

print("Timed out waiting for PostgreSQL database.")
sys.exit(1)
EOF

echo "Executing Alembic schema migrations..."
alembic upgrade head

echo "Verifying default active model version and admin..."
python - << 'EOF'
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.model_version import ModelVersion
from app.core.security import hash_password

with SessionLocal() as db:
    if not db.query(ModelVersion).first():
        mv = ModelVersion(
            model_name="mock-assessment-engine",
            version="1.0.0",
            algorithm="rule-based-mock",
            description="Default assessment scoring model version",
            is_active=True,
        )
        db.add(mv)
        print("Seeded default active ModelVersion.")

    admin_email = "admin@parakh.com"
    if not db.query(User).filter(User.email == admin_email).first():
        admin_user = User(
            email=admin_email,
            password_hash=hash_password("AdminPassword123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        print(f"Seeded default administrator user ({admin_email}).")

    # Seed Demo Applicant: arjun.verma@example.com
    from app.models.applicant import ApplicantProfile
    from decimal import Decimal

    applicant_email = "arjun.verma@example.com"
    app_user = db.query(User).filter(User.email == applicant_email).first()
    if not app_user:
        app_user = User(
            email=applicant_email,
            password_hash=hash_password("Password123!"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add(app_user)
        db.flush()
        print(f"Seeded demo applicant user ({applicant_email}).")
    else:
        app_user.password_hash = hash_password("Password123!")
        app_user.is_active = True
        db.flush()

    if not db.query(ApplicantProfile).filter(ApplicantProfile.user_id == app_user.id).first():
        profile = ApplicantProfile(
            user_id=app_user.id,
            gig_work_type="GIG_WORKER",
            years_working=Decimal("1.5"),
            average_working_days=24,
            business_or_loan_purpose="Two-Wheeler EV Battery Upgrade & Gear",
        )
        db.add(profile)
        print(f"Seeded demo applicant profile for ({applicant_email}).")

    # Seed Demo Reviewer: reviewer@parakh.internal
    reviewer_email = "reviewer@parakh.internal"
    rev_user = db.query(User).filter(User.email == reviewer_email).first()
    if not rev_user:
        rev_user = User(
            email=reviewer_email,
            password_hash=hash_password("Password123!"),
            role=UserRole.REVIEWER,
            is_active=True,
        )
        db.add(rev_user)
        print(f"Seeded demo reviewer user ({reviewer_email}).")
    else:
        rev_user.password_hash = hash_password("Password123!")
        rev_user.is_active = True
        rev_user.role = UserRole.REVIEWER

    db.commit()
EOF

echo "Starting PARAKH FastAPI Application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
