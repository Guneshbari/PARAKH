"""Aggregation router for all v1 domain endpoints."""
from fastapi import APIRouter
from app.api.v1.applicants import router as applicants_router
from app.api.v1.applications import router as applications_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.consents import router as consents_router
from app.api.v1.financial_signals import router as signals_router
from app.api.v1.model_versions import router as model_versions_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.users import router as users_router

v1_router = APIRouter()

# Auth routes: /api/v1/auth
v1_router.include_router(auth_router, prefix="/auth")

# Domain routes
v1_router.include_router(users_router)
v1_router.include_router(applicants_router)
v1_router.include_router(applications_router)
v1_router.include_router(consents_router)
v1_router.include_router(signals_router)
v1_router.include_router(assessments_router)
v1_router.include_router(model_versions_router)
v1_router.include_router(reviews_router)
v1_router.include_router(audit_router)
