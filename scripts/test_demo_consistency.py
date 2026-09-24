import sys
import os
import logging
from sqlalchemy import func

sys.path.insert(0, os.path.abspath("backend"))

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.models.applicant import ApplicantProfile
from app.models.application import Application, ApplicationStatus
from app.models.assessment import CreditAssessment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_consistency():
    db = SessionLocal()
    
    users = db.query(User).all()
    assert len(users) >= 8, "Expected at least 8 users including demo users"
    
    applicants = db.query(ApplicantProfile).all()
    assert len(applicants) >= 7, "Expected at least 7 applicant profiles"
    
    apps = db.query(Application).all()
    assert len(apps) >= 7, "Expected at least 7 applications"
    
    assessments = db.query(CreditAssessment).all()
    assert len(assessments) >= 6, "Expected at least 6 assessments"
    
    # Check Arjun's data coherence
    arjun = db.query(User).filter(User.email == "arjun.verma@example.com").first()
    assert arjun is not None
    arjun_profile = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == arjun.id).first()
    assert arjun_profile is not None
    arjun_app = db.query(Application).filter(Application.applicant_profile_id == arjun_profile.id).first()
    assert arjun_app is not None
    assert arjun_app.status == ApplicationStatus.COMPLETED
    
    # Check portfolio aggregation numbers
    total_apps = db.query(func.count(Application.id)).scalar()
    completed = db.query(func.count(Application.id)).filter(Application.status == ApplicationStatus.COMPLETED).scalar()
    assert total_apps >= 7
    assert completed >= 3
    
    logger.info("Consistency tests passed successfully.")

if __name__ == "__main__":
    test_consistency()
