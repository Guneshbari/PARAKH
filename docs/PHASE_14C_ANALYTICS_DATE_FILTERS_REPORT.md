# Phase 14C — Analytics Date-Range Filters (P2-03)

**Gap Closed:** P2-03 from the frozen Phase 12B Frontend ↔ Backend ↔ ML Gap Analysis Report  
**Branch:** `ml/credit-risk`  
**Commit:** `feat: add analytics date range filters`  
**Previous Phase:** 14B (`4cdef2f` — Implement Audit Log Viewer)

---

## 1. P2-03 Gap Definition

> **P2-03** — Implement Date Range Query Parameters on Analytics  
> *"Add `start_date` and `end_date` parameters to `GET /api/v1/analytics/portfolio`."*  
> *"On `/admin/analytics`, filter buttons for `30D`, `90D`, `6M`, and `ALL` cannot pass time-range queries because `GET /api/v1/analytics/portfolio` does not accept date parameters."*  
> — *Phase 12B Gap Analysis Report (lines 298, 486, 538, 574)*

In Phase 12B, the audit revealed that the `/admin/analytics` UI contained preset filter buttons (`30D`, `90D`, `6M`, `All Time`), but the backend `GET /api/v1/analytics/portfolio` endpoint did not accept date parameters, forcing the frontend to execute completely unfiltered queries regardless of user selection.

---

## 2. Existing Analytics Architecture

The portfolio analytics architecture computes aggregated KPIs directly in PostgreSQL (or SQLite in memory for test suites) across three core tables:
- `applications` (`Application` model)
- `applicant_profiles` (`ApplicantProfile` model)
- `credit_assessments` (`CreditAssessment` model)

Aggregations are executed using SQL `GROUP BY`, `func.count`, and `func.avg` without Python-level N+1 record iteration:
1. `total_applications`: total submitted loan applications.
2. `total_applicants`: count of unique applicant profiles.
3. `status_distribution`: application counts grouped by `ApplicationStatus` enum.
4. `risk_distribution`: assessment counts grouped by `RiskLevel` enum.
5. `average_credit_score`: mean credit score of completed assessments.
6. `average_risk_probability`: mean risk probability of completed assessments.
7. `assessment_completion_rate`: percentage of applications in `ASSESSED`, `MANUAL_REVIEW`, or `COMPLETED`.
8. `score_distribution`: 5-tier histogram buckets based on credit score.
9. `monthly_volume`: 6-month historical trend of application counts and average scores.
10. `sector_risk`: risk tier breakdown grouped by applicant gig work type/sector.

---

## 3. Authoritative Analytics Timestamp and Date Fields

To prevent temporal mismatch and guarantee that all metrics reflect the exact same population:
- **Application-Level Metrics:** `Application.created_at` (UTC timestamp) is the authoritative timestamp for application volume, status distribution, pipeline completion rate, and monthly application volume counts.
- **Assessment-Level Metrics:** `CreditAssessment.created_at` (UTC timestamp) is the authoritative timestamp for risk level distributions, average credit score, average risk probability, score distribution histogram, monthly volume average score, and sector risk breakdown.
- **Applicant Profile Count:** When filtered by date, `total_applicants` counts distinct `Application.applicant_profile_id` associated with applications created within the filtered window, ensuring profile counts align with the active portfolio population. When unfiltered, the total registered profile count is preserved.

---

## 4. API Contract & Date Semantics

### 4.1 Query Parameters

Endpoint: `GET /api/v1/analytics/portfolio`

| Parameter | Type | Format | Required | Description |
|-----------|------|--------|----------|-------------|
| `start_date` | `date` | `YYYY-MM-DD` | No | Inclusive start of date range (UTC calendar day). Records created on or after `start_date 00:00:00 UTC` are included. |
| `end_date` | `date` | `YYYY-MM-DD` | No | Inclusive end of date range (UTC calendar day). Records created on or before `end_date 23:59:59.999999 UTC` are included. |

### 4.2 Inclusive/Exclusive Boundary Semantics

Date parameters are interpreted as UTC calendar days:
- **`start_date` clause:** `col >= datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc)` (inclusive lower bound).
- **`end_date` clause:** `col < datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)` (exclusive upper bound of the next day, ensuring full inclusion of the entire calendar day down to sub-second timestamps).
- **Single-Day Filter (`start_date == end_date`):** Filters records between `00:00:00 UTC` and `< next_day 00:00:00 UTC`, covering the complete single calendar day.
- **Only `start_date` supplied:** Includes records on or after `start_date 00:00:00 UTC` with no upper bound.
- **Only `end_date` supplied:** Includes records on or before `end_date 23:59:59.999999 UTC` with no lower bound.

### 4.3 Validation Behavior

- **Reversed Range (`start_date > end_date`):** Returns **HTTP 422 Unprocessable Entity** with JSON body `{"detail": "start_date must not be after end_date."}`.
- **Invalid Date Format:** FastAPI / Pydantic validation rejects unparseable strings (e.g. `invalid-date` or `2026-13-45`) with standard **HTTP 422 Unprocessable Entity**.
- **Empty Result Window:** A valid date range matching 0 records returns **HTTP 200 OK** with zeroed counts, null averages, and empty bucket lists.

### 4.4 Backward Compatibility

- Calling `GET /api/v1/analytics/portfolio` without parameters produces identical results to prior phases without any filtering or regression.
- Both parameters remain strictly optional (`Optional[date] = Query(None, ...)`).

---

## 5. Database Query Implementation

### 5.1 Filter Clause Helpers (`backend/app/api/v1/analytics.py`)

```python
def _app_date_filters(start_date: Optional[date], end_date: Optional[date]) -> list:
    filters = []
    if start_date is not None:
        filters.append(Application.created_at >= datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc))
    if end_date is not None:
        next_day = datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)
        filters.append(Application.created_at < next_day)
    return filters

def _assess_date_filters(start_date: Optional[date], end_date: Optional[date]) -> list:
    filters = []
    if start_date is not None:
        filters.append(CreditAssessment.created_at >= datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc))
    if end_date is not None:
        next_day = datetime(end_date.year, end_date.month, end_date.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)
        filters.append(CreditAssessment.created_at < next_day)
    return filters
```

### 5.2 Metric-Level Query Application

Every query in `get_portfolio_analytics` and `_build_sector_risk` applies the respective filter list directly in SQL:
- `total_applications`: `.filter(*app_filters)`
- `total_applicants`: `.filter(*app_filters)` over distinct profile IDs when filtered; all-time profile count when unfiltered
- `status_distribution`: `.filter(*app_filters).group_by(Application.status)`
- `risk_distribution`: `.filter(*assess_filters).group_by(CreditAssessment.risk_level)`
- `average_credit_score`, `average_risk_probability`: `.filter(*assess_filters)`
- `score_distribution`: `.filter(*assess_filters)` per bucket
- `monthly_volume`: `.filter(*app_filters)` for counts, `.filter(*assess_filters)` for scores
- `sector_risk`: `.filter(*assess_filters)` in `_build_sector_risk(db, start_date, end_date)`

---

## 6. Frontend & API Client Changes

### 6.1 API Client (`frontend/packages/api/index.ts` & `types.ts`)

Added `PortfolioAnalyticsQueryParams`:
```typescript
export interface PortfolioAnalyticsQueryParams {
  start_date?: string;
  end_date?: string;
}
```

Extended `getPortfolioAnalytics` and `getPortfolioAnalyticsAdapted`:
```typescript
async getPortfolioAnalytics(params?: PortfolioAnalyticsQueryParams): Promise<BackendPortfolioAnalytics> {
  const query = new URLSearchParams();
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);
  const qs = query.toString();
  return this.request<BackendPortfolioAnalytics>(`/api/v1/analytics/portfolio${qs ? `?${qs}` : ''}`, {
    method: 'GET',
  });
}

async getPortfolioAnalyticsAdapted(params?: PortfolioAnalyticsQueryParams): Promise<AdaptedPortfolioAnalytics> {
  const raw = await this.getPortfolioAnalytics(params);
  return adaptPortfolioAnalytics(raw);
}
```

Also corrected operational alerts API client methods to use `this.request(...)` with respective HTTP methods (`GET`, `PATCH`).

### 6.2 Analytics Page UI (`frontend/apps/web/app/admin/analytics/page.tsx`)

The dashboard has been updated without altering the layout:
1. **Time Range Presets:** `All Time`, `30D`, `90D`, `6M`. Selecting a preset automatically populates the date inputs and triggers an immediate filtered request.
2. **Explicit Date Controls:** Separate `Start` and `End` HTML5 date inputs (`YYYY-MM-DD`). Entering custom dates switches active preset to `CUSTOM`.
3. **Apply Action:** Dedicated "Apply" button with loading spinner (`Loader2`) when request is in flight. Client-side validates `start_date <= end_date` before sending.
4. **Reset/Clear Action:** "Reset" button clears both date inputs, resets preset to `ALL`, and fetches all-time portfolio analytics.
5. **Active Filter Badge:** Displays active date range badge (`From YYYY-MM-DD to YYYY-MM-DD`) in the page header.
6. **Loading State:** Apply button displays `<Loader2 className="animate-spin" /> Updating...` while requests are in progress.
7. **Empty/No-Data State:** Shows context-aware card when zero records match the selected date range, with a "Reset Date Filter" CTA.
8. **Error Banner:** Displays validation and API errors clearly with a "Retry" button.

---

## 7. Numerical Boundary Tests & Test Results

A deterministic fixture spanning 3 dates was established in `backend/tests/test_phase14c_analytics_date_filters.py`:
- **Date 1 (2026-05-10):** 1 application, 1 assessment (COMPLETED, score=750, risk=0.1500, LOWER, Food Delivery)
- **Date 2 (2026-05-15 00:00:00 UTC):** 1 application, 1 assessment (ASSESSED, score=680, risk=0.3500, MODERATE, Food Delivery)
- **Date 2 (2026-05-15 23:59:59 UTC):** 1 application, 1 assessment (MANUAL_REVIEW, score=620, risk=0.4500, HIGHER, Ride Logistics)
- **Date 3 (2026-05-20 12:00:00 UTC):** 1 application (SUBMITTED, unassessed, Home Services)

### Numerical Assertions Summary

| Filter Case | Parameters | Total Apps | Total Applicants | Total Assessed | Avg Score | Avg Risk Prob | Completion Rate |
|-------------|------------|------------|------------------|----------------|-----------|---------------|-----------------|
| Unfiltered | None | 4 | 3 | 3 | 683.3 | 0.3167 | 75.0% |
| Start-Date Only | `start_date=2026-05-15` | 3 | 3 | 2 | 650.0 | 0.4000 | 66.7% |
| End-Date Only | `end_date=2026-05-15` | 3 | 2 | 3 | 683.3 | 0.3167 | 100.0% |
| Both Dates | `2026-05-10` to `2026-05-15` | 3 | 2 | 3 | 683.3 | 0.3167 | 100.0% |
| Equal Dates (Single Day) | `2026-05-15` to `2026-05-15` | 2 | 2 | 2 | 650.0 | 0.4000 | 100.0% |
| Out of Range | `2025-01-01` to `2025-01-31` | 0 | 0 | 0 | null | null | 0.0% |
| Reversed Range | `2026-05-20` to `2026-05-10` | HTTP 422 | — | — | — | — | — |
| Invalid String | `start_date=invalid-date` | HTTP 422 | — | — | — | — | — |

---

## 8. Role-Based Access Control (RBAC)

RBAC rules on `GET /api/v1/analytics/portfolio` are strictly preserved:
- **`REVIEWER`:** Allowed (HTTP 200 OK)
- **`ADMIN`:** Allowed (HTTP 200 OK)
- **`APPLICANT`:** Forbidden (HTTP 403 Forbidden with `"Access denied: only reviewers and administrators can access portfolio analytics."`)
- **Unauthenticated:** Unauthorized (HTTP 401 Unauthorized)

---

## 9. Test Execution Summary

### 9.1 Dedicated Phase 14C Backend Suite (`test_phase14c_analytics_date_filters.py`)
- **10 passed in 17.22s**

### 9.2 Existing Portfolio Analytics Suite (`test_analytics.py`)
- **4 passed in 6.27s**

### 9.3 Frontend Test Suite (`test-phase14c-analytics-filters.ts`)
- **8 tests passed successfully** (Serialization, start_date only, end_date only, combined, adapted model, empty data, 422 error propagation, reset/clear).

### 9.4 TypeScript Compilation
- **0 errors**: `docker compose exec frontend /app/node_modules/.bin/tsc --noEmit --project apps/web/tsconfig.json`

### 9.5 Full Backend & ML Regression Suite
- **491 passed, 40 skipped, 0 failures across 531 tests (94.66s)**
  - `test_phase14b_audit_viewer.py`: 10 passed
  - `test_audit_logging.py`: 33 passed, 2 skipped
  - `test_operational_alerts.py`: 17 passed
  - `test_phase13a1_explanation_persistence.py`: 7 passed, 1 skipped
  - `test_phase13a2_sufficiency_gate.py`: 13 passed
  - `test_phase13a3_telemetry_pipeline.py`: 27 passed
  - `test_phase13a4_preprocessor_persistence.py`: 14 passed
  - `test_phase9_inference.py`: 54 passed

---

## 10. ML Artifact Integrity Verification

Model artifacts and feature calculation code were untouched:

| Artifact | Expected SHA-256 | Actual SHA-256 | Status |
|----------|------------------|----------------|--------|
| `volatility_aware_risk_model.joblib` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` | Intact |
| `FINAL_MODEL.json` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` | Intact |
| `credit_risk_preprocessor.joblib` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` | Intact |

---

## 11. Remaining P2 / P3 Gap Inventory

With P2-03 resolved, the remaining Phase 12B gaps are:
- **P2-04:** Wire DPDP Consent Preferences to PostgreSQL
- **P2-05:** Wire Applicant Profile Editing (`PATCH /api/v1/applicants/{id}`)
- **P2-06:** Model Promotion / Activation API (`POST /api/v1/model-versions/{id}/activate`)
- **P2-07:** Wire Offline Fairness Evaluation Execution (`GroupedFairnessAuditor`)
- **P2-08:** Clean Up Unused & Redundant API Client Methods in `@parakh/api`
- **P2-09:** Clean Up Unconsumed Application Backend Routes
- **P2-10:** Global SHAP Aggregation Worker
- **P2-11:** Historical Assessment Auditing UI (`GET /api/v1/applications/{id}/assessments`)
- **P3-01 to P3-06:** Polish items (fallback counts, FIDO2 copy, empty score formatting, term editing)
