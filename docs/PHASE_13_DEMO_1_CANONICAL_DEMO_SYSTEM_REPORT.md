# PHASE 13-DEMO-1: Dynamic Canonical Demo Data System Report

## 1. Discovery Summary
A systematic discovery of the frontend revealed that the application relies on backend APIs for almost all its state:
- **Portfolio Analytics**: Driven by the `api.getPortfolioAnalyticsAdapted()` which connects to the real `GET /api/v1/analytics/portfolio` backend endpoint. This aggregates real `Application`, `ApplicantProfile`, and `CreditAssessment` database tables.
- **Model Insights & Explanations**: `api.getModelVersions()` retrieves real model versions. However, fairness and global feature importance were hardcoded UI constants with "Not Persisted" states.
- **Operational Alerts**: Found in `app/admin/profile/page.tsx` as hardcoded UI constants.

## 2. Architecture Decisions
Instead of creating a massive fake API layer in the frontend, the strategy utilizes the actual database structure. By populating the DB with comprehensive "Canonical Demo Data", the existing aggregations and pages naturally render perfectly synced data.

A centralized `DemoProvider` (`canonicalDemoData.ts`) was only created for UI states that do not have an equivalent backend endpoint:
- `mlInsights`: Global features and Fairness evaluation data (Demographic Parity).
- `alerts`: Operational alerts for reviewers.

## 3. Implementation Steps
1. **Seed Script**: Built `scripts/seed_demo_data.py` that connects to the database via SQLAlchemy and deterministically seeds canonical test users, including:
   - Stable lower-risk gig worker
   - Volatile but resilient freelancer
   - Genuine higher-risk applicant
   - Insufficient-evidence applicant
   - Recovery-after-income-shock applicant
   - Strong repayment applicant
   - Arjun Verma (fixed and updated)
2. **Frontend Demo Provider**: Created `frontend/apps/web/lib/demo/canonicalDemoData.ts`.
3. **Wiring**: Updated `AdminModelInsightsPage` and `AdminProfilePage` to utilize the `canonicalDemoData` instead of empty hardcoded placeholders.
4. **Consistency Testing**: Automated test `scripts/test_demo_consistency.py` validates that database constraints, counts, and states remain globally coherent for both the Reviewer and Applicant roles.

## 4. Resetting Demo Data
To reset the canonical demo data, run the seed script against the backend container:
```bash
cat scripts/seed_demo_data.py | docker compose exec -T backend python
```
The script is idempotent and will clean up old application data for demo users before reseeding.

## 5. Replacing Demo Provider
When actual ML insights and alert pipelines are added to the backend, `canonicalDemoData.ts` can be phased out by swapping its imports in `model-insights/page.tsx` and `profile/page.tsx` with standard `apiClient` fetches.
