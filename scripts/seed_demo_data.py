import sys
import os
import uuid
from datetime import datetime, timedelta
import logging

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment, RiskLevel
from app.models.consent import Consent, ConsentDataSource
from app.models.financial_signal import FinancialSignal, SignalSource
from app.models.model_version import ModelVersion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_or_create_user(db, email, role, password_hash="fake_hash"):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            role=role,
            password_hash=password_hash,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created user: {email}")
    else:
        logger.info(f"User exists: {email}")
    return user

def get_or_create_profile(db, user_id, gig_work_type, years_working, avg_working_days):
    profile = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == user_id).first()
    if not profile:
        profile = ApplicantProfile(
            user_id=user_id,
            gig_work_type=gig_work_type,
            years_working=years_working,
            average_working_days=avg_working_days,
            business_or_loan_purpose="Working Capital"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        profile.gig_work_type = gig_work_type
        profile.years_working = years_working
        profile.average_working_days = avg_working_days
        db.commit()
    return profile

def get_or_create_model(db):
    model = db.query(ModelVersion).filter(ModelVersion.model_name == "LightGBM_V1").first()
    if not model:
        model = ModelVersion(
            model_name="LightGBM_V1",
            version="1.0.0",
            description="Active credit risk model",
            algorithm="lightgbm",
            is_active=True
        )
        db.add(model)
        db.commit()
        db.refresh(model)
    return model

def create_application_and_assessment(
    db, profile_id, model_id, status, requested_amount, 
    risk_level, credit_score, risk_prob, debt_to_income,
    utilization, income_stability, repayment_reliability,
    created_days_ago=0
):
    app_date = datetime.utcnow() - timedelta(days=created_days_ago)
    
    app = Application(
        applicant_profile_id=profile_id,
        requested_loan_amount=requested_amount,
        loan_purpose="Working Capital",
        preferred_repayment_period=12,
        status=status,
    )
    # Bypass auto-timestamps for demo
    app.created_at = app_date
    app.updated_at = app_date
    
    db.add(app)
    db.flush()
    
    if status in [ApplicationStatus.ASSESSED, ApplicationStatus.MANUAL_REVIEW, ApplicationStatus.COMPLETED]:
        assessment = CreditAssessment(
            application_id=app.id,
            model_version_id=model_id,
            credit_score=credit_score,
            risk_probability=risk_prob,
            risk_level=risk_level,
            confidence=0.85,
            debt_to_income=debt_to_income,
            utilization=utilization,
            income_stability=income_stability,
            repayment_reliability=repayment_reliability,
            explanation={"top_features": ["income_stability", "years_working"]}
        )
        assessment.created_at = app_date + timedelta(minutes=5)
        assessment.assessed_at = app_date + timedelta(minutes=5)
        db.add(assessment)
        
    # Consents
    consent1 = Consent(
        applicant_profile_id=profile_id,
        application_id=app.id,
        data_source=ConsentDataSource.FINANCIAL_ACTIVITY,
        purpose="Credit Assessment via AA",
        granted=True
    )
    db.add(consent1)
    
    # Financial signals
    signal = FinancialSignal(
        application_id=app.id,
        source=SignalSource.FINANCIAL_ACTIVITY,
        average_income=round(requested_amount * 1.5, 2),
        income_volatility=0.2,
        cashflow_buffer=round(requested_amount * 0.5, 2)
    )
    db.add(signal)
    
    db.commit()

def seed():
    db = SessionLocal()
    
    model = get_or_create_model(db)
    
    # Ensure Arjun and Priya exist
    arjun = get_or_create_user(db, "arjun.verma@example.com", UserRole.APPLICANT)
    priya = get_or_create_user(db, "priya.sharma@example.com", UserRole.REVIEWER)
    
    # Additional Demo Applicants
    applicants = [
        {
            "email": "arjun.verma@example.com", # Arjun
            "role": UserRole.APPLICANT,
            "gig": "Delivery Partner",
            "years": 2.5,
            "days": 24,
            "amount": 25000,
            "status": ApplicationStatus.COMPLETED,
            "risk_level": RiskLevel.MODERATE,
            "score": 620,
            "prob": 0.35,
            "dti": 0.4,
            "util": 0.5,
            "stability": 0.6,
            "repayment": 0.7,
            "days_ago": 5
        },
        {
            "email": "stable.driver@example.com",
            "role": UserRole.APPLICANT,
            "gig": "Ride Hailing",
            "years": 4.0,
            "days": 26,
            "amount": 50000,
            "status": ApplicationStatus.ASSESSED,
            "risk_level": RiskLevel.LOWER,
            "score": 750,
            "prob": 0.12,
            "dti": 0.25,
            "util": 0.3,
            "stability": 0.85,
            "repayment": 0.9,
            "days_ago": 2
        },
        {
            "email": "volatile.freelancer@example.com",
            "role": UserRole.APPLICANT,
            "gig": "Freelance Designer",
            "years": 3.0,
            "days": 15,
            "amount": 35000,
            "status": ApplicationStatus.MANUAL_REVIEW,
            "risk_level": RiskLevel.MODERATE,
            "score": 580,
            "prob": 0.42,
            "dti": 0.35,
            "util": 0.6,
            "stability": 0.4,
            "repayment": 0.8,
            "days_ago": 1
        },
        {
            "email": "high.risk@example.com",
            "role": UserRole.APPLICANT,
            "gig": "Construction Labour",
            "years": 1.0,
            "days": 20,
            "amount": 40000,
            "status": ApplicationStatus.COMPLETED,
            "risk_level": RiskLevel.HIGHER,
            "score": 410,
            "prob": 0.78,
            "dti": 0.65,
            "util": 0.85,
            "stability": 0.3,
            "repayment": 0.4,
            "days_ago": 15
        },
        {
            "email": "insufficient.new@example.com",
            "role": UserRole.APPLICANT,
            "gig": "Tutoring",
            "years": 0.2,
            "days": 10,
            "amount": 10000,
            "status": ApplicationStatus.MANUAL_REVIEW,
            "risk_level": RiskLevel.INSUFFICIENT,
            "score": None,
            "prob": None,
            "dti": None,
            "util": None,
            "stability": None,
            "repayment": None,
            "days_ago": 0
        },
        {
            "email": "recovery.shock@example.com",
            "role": UserRole.APPLICANT,
            "gig": "Delivery Partner",
            "years": 3.5,
            "days": 22,
            "amount": 30000,
            "status": ApplicationStatus.ASSESSED,
            "risk_level": RiskLevel.MODERATE,
            "score": 650,
            "prob": 0.30,
            "dti": 0.45,
            "util": 0.55,
            "stability": 0.5,
            "repayment": 0.75,
            "days_ago": 10
        },
        {
            "email": "strong.repayment@example.com",
            "role": UserRole.APPLICANT,
            "gig": "E-commerce Seller",
            "years": 5.0,
            "days": 28,
            "amount": 100000,
            "status": ApplicationStatus.COMPLETED,
            "risk_level": RiskLevel.LOWER,
            "score": 810,
            "prob": 0.05,
            "dti": 0.15,
            "util": 0.2,
            "stability": 0.9,
            "repayment": 0.95,
            "days_ago": 30
        }
    ]
    
    # First, let's delete existing applications for demo users to avoid duplicates if re-run
    demo_emails = [a["email"] for a in applicants]
    for e in demo_emails:
        u = db.query(User).filter(User.email == e).first()
        if u:
            p = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == u.id).first()
            if p:
                apps = db.query(Application).filter(Application.applicant_profile_id == p.id).all()
                for app in apps:
                    db.delete(app)
                db.commit()
    
    for a in applicants:
        user = get_or_create_user(db, a["email"], a["role"])
        profile = get_or_create_profile(db, user.id, a["gig"], a["years"], a["days"])
        create_application_and_assessment(
            db, profile.id, model.id, a["status"], a["amount"],
            a["risk_level"], a["score"], a["prob"], a["dti"],
            a["util"], a["stability"], a["repayment"],
            created_days_ago=a["days_ago"]
        )
        
    logger.info("Demo data seeded successfully.")
    
if __name__ == "__main__":
    seed()
