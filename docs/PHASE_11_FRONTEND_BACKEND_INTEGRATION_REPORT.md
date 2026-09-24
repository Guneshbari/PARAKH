# Phase 11B — Frontend ↔ Backend Integration Implementation Report

**Project:** PARAKH — Alternative Credit Assessment Prototype (CX0506)  
**Branch:** `ml/credit-risk`  
**Role:** Frontend Integration Engineer  
**Status:** Implementation Complete & Fully Verified  
**Date:** September 2026  

---

## 1. Executive Summary

Phase 11B completes the implementation of the frontend-to-backend integration between the PARAKH Next.js frontend, the FastAPI backend services (`POST /api/v1/applications/{application_id}/assess`), and the frozen Phase 9 LightGBM Volatility-Aware Credit Risk Model (`models/artifacts/volatility_aware_risk_model.joblib`).

All integration defects identified in Phase 11A—including numerical score coercion from `null`, the falsy zero-confidence evaluation bug, unhandled unrated states in the user and reviewer dossiers, and missing explainability metadata—have been resolved. The frontend now faithfully adheres to the core ML governance rule: **zero score fabrication on insufficient telemetry**.

---

## 2. Files Changed

| File Path | Nature of Changes |
|---|---|
| [`frontend/packages/types/index.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/types/index.ts) | Made `score`, `estimatedRepaymentDifficulty`, and `modelConfidence` nullable (`number \| null`). Added `isInsufficientEvidence`, `missingSignals`, `disclaimer`, `modelName`, `modelVersion`, `debtToIncome`, `utilization`, and `assessmentStatus` to `CreditAssessmentResult`. |
| [`frontend/packages/api/adapters.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/adapters.ts) | Updated `adaptAssessment()` to preserve `null` scores, eliminate the `(confidence \|\| 0.85)` falsy evaluation bug, guard the confidence interval from bound inversion on `null` scores, and extract all explainability metadata. |
| [`frontend/packages/api/index.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/index.ts) | Added convenience method `triggerAssessmentAdapted()` to `ParakhApiClient` for triggering assessments and returning adapted domain models directly. |
| [`frontend/packages/api/test-api-adapters.ts`](file:///home/gnx/Projects/PARAKH/frontend/packages/api/test-api-adapters.ts) | Added test cases covering all 4 risk tiers (`LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`), verifying `score: null` preservation, `confidence: 0.0` preservation, `missingSignals` mapping, `isInsufficientEvidence: true`, empty SHAP array handling, and `triggerAssessmentAdapted()`. |
| [`frontend/apps/web/components/shared/CreditScoreCard.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/components/shared/CreditScoreCard.tsx) | Added conditional branch for unrated / insufficient evidence assessments: displays **`UNRATED / No Score Generated`**, shows `N/A` for difficulty, `0% (Insufficient telemetry)` for confidence, and displays model version badges when present. Suppresses `0 / 850` score counters. |
| [`frontend/apps/web/components/shared/FeatureContributionCard.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/components/shared/FeatureContributionCard.tsx) | Added clean empty-state fallback when `contributions.length === 0`: informs users that feature attributions are unavailable when no score is generated. |
| [`frontend/apps/web/app/user/results/[id]/page.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/user/results/%5Bid%5D/page.tsx) | Added prominent missing signals warning alert banner, contextualized AI risk insight text for unrated states, always renders `FeatureContributionCard`, and displays the statutory model disclaimer from `assessment.disclaimer`. |
| [`frontend/apps/web/app/admin/applications/[id]/page.tsx`](file:///home/gnx/Projects/PARAKH/frontend/apps/web/app/admin/applications/%5Bid%5D/page.tsx) | Updated underwriter header to render `UNRATED (Insufficient Telemetry)` and `Uncalculated` difficulty when score is null. Added reviewer missing signals warning card and contextualized reviewer AI synthesis text. |

---

## 3. API Integration Completed

- **Assessment Triggering:** Both applicant intake (`/user/applications/new`) and programmatic callers can invoke `api.triggerAssessment(applicationId)` or `api.triggerAssessmentAdapted(applicationId)`.
- **Assessment Fetching:** Application and dossier pages fetch latest assessment records via `api.getLatestAssessmentByApplication(applicationId)` and direct lookups via `api.getAssessmentById(assessmentId)`.
- **Security & Headers:** All outbound requests continue to use `ParakhApiClient` with Bearer JWT injection, 15-second timeouts, and no-retry on non-idempotent POST operations.

---

## 4. Type Changes (`@parakh/types`)

The domain interface `CreditAssessmentResult` was updated as follows:

```typescript
export interface CreditAssessmentResult {
  id: string;
  applicantId: string;
  applicantName: string;
  score: number | null; // Nullable when insufficient evidence
  maxScore: number; // 850
  riskLevel: RiskLevel;
  estimatedRepaymentDifficulty: number | null; // Nullable when insufficient evidence
  modelConfidence: number | null; // Nullable / 0 when insufficient evidence
  isInsufficientEvidence?: boolean;
  missingSignals?: string[];
  disclaimer?: string;
  modelName?: string | null;
  modelVersion?: string | null;
  debtToIncome?: number | null;
  utilization?: number | null;
  assessmentStatus?: string;
  volatilityProfile: VolatilityProfile;
  keyPositiveFactors: FactorSummary[];
  keyAttentionFactors: FactorSummary[];
  featureContributions: SHAPContribution[];
  actionableRecommendations: string[];
  assessedAt: string;
}
```

---

## 5. Adapter Changes (`@parakh/api`)

In `frontend/packages/api/adapters.ts`:

1. **Preserving Null Score:**
   ```typescript
   const rawScore = backendAssessment.score ?? backendAssessment.credit_score;
   const score = rawScore !== null && rawScore !== undefined ? Number(rawScore) : null;
   ```
2. **Preserving Zero / Null Confidence:**
   ```typescript
   const rawConfidence = backendAssessment.confidence;
   const confidence = rawConfidence !== null && rawConfidence !== undefined ? Number(rawConfidence) : null;
   const modelConfidence = confidence !== null ? Math.round(confidence > 1 ? confidence : confidence * 100) : null;
   ```
   *Fixes bug where `0.0` was falsy and fell back to `0.85` (85%).*
3. **Preserving Null Probability:**
   ```typescript
   const rawRiskProb = backendAssessment.risk_probability;
   const riskProbability = rawRiskProb !== null && rawRiskProb !== undefined ? Number(rawRiskProb) : null;
   const estimatedRepaymentDifficulty = riskProbability !== null ? Math.round(riskProbability > 1 ? riskProbability : riskProbability * 100) : null;
   ```
4. **Metadata Extraction:**
   - Extracts `explanation.is_insufficient_evidence`
   - Extracts `explanation.missing_signals`
   - Extracts `explanation.disclaimer`
   - Extracts `model_name`, `model_version`, `assessment_status`, `debt_to_income`, and `utilization`.
5. **Confidence Interval Bound Protection:**
   ```typescript
   confidenceInterval: score !== null ? [Math.max(300, score - 35), Math.min(850, score + 35)] : [300, 850]
   ```
   *Guards against `[300, 35]` bound inversion when score is null.*

---

## 6. UI Changes

### 6.1 `CreditScoreCard.tsx`
- **When Scored (`score !== null`):** Displays `<AnimatedNumber value={assessment.score} /> / 850`, risk tier badge, repayment difficulty percentage, and model confidence percentage.
- **When Unrated (`score === null` or `isInsufficientEvidence === true`):**
  - Renders **`UNRATED`** in bold mono type with sub-header **`No Score Generated`**.
  - Displays `<RiskBadge riskLevel="INSUFFICIENT_EVIDENCE_MANUAL_REVIEW" />` (`MANUAL REVIEW REQUIRED`).
  - Displays governance explanation: *"Alternative telemetry is insufficient to safely synthesize a reliable credit score. Under PARAKH model governance, scores are not fabricated without sufficient verified cashflow history."*
  - Shows `Uncalculated (N/A)` for Repayment Risk and `0% (Insufficient telemetry)` for Confidence.
  - Replaces shock recovery with `Pending Data`.

### 6.2 `FeatureContributionCard.tsx`
- **When SHAP values exist:** Renders divergence bars (+/- %) with feature names and explanations.
- **When empty (`contributions.length === 0`):** Displays an explanation card: *"Feature attributions are unavailable because no predictive score was generated. When alternative telemetry is insufficient, SHAP feature impact cannot be computed."*

### 6.3 User Assessment Results (`/user/results/[id]`)
- Displays prominent **Missing Signals Banner** listing specific missing telemetry items (e.g. *"Observed history below minimum requirement"*).
- Provides actionable buttons: *"Manage Connected Accounts"* and *"Submit Updated Application"*.
- Adapts the AI Insight Card to explicitly explain evaluation refusal under RBI regulatory fair practice standards.
- Renders dynamic statutory disclaimer from `assessment.disclaimer`.

### 6.4 Reviewer Application Dossier (`/admin/applications/[id]`)
- Underwriter header renders `UNRATED (Insufficient Telemetry)` and `Uncalculated` difficulty instead of `0 / 850`.
- Renders **Manual Review Triggered: Evidence Threshold Not Met** card with missing signals list.
- Adapts reviewer AI insight text to guide underwriters on evidence refusal and options (request verification vs. record outcome).

---

## 7. Verification Results

### 7.1 Automated API Adapter Suite
```
--- Running @parakh/api Tests ---
1. Testing ApiError status code mapping and classification...
   ✓ ApiError classification passed
2. Testing Enum Adapters...
   ✓ Enum Adapters passed
3. Testing Entity Adapters...
   ✓ adaptApplication passed
   ✓ adaptAssessment (LOWER scored) passed
   ✓ adaptAssessment (MODERATE scored) passed
   ✓ adaptAssessment (HIGHER scored) passed
   ✓ adaptAssessment (INSUFFICIENT evidence & null score preservation) passed
   ✓ adaptReviewOutcome passed
   ✓ adaptBorrowerProfile passed
4. Testing ParakhApiClient token management and HTTP contracts...
   ✓ ParakhApiClient HTTP requests and error handling passed

=========================================
ALL @parakh/api TESTS PASSED SUCCESSFULLY!
=========================================
```

### 7.2 Applicant Portal Lifecycle Integration Suite
```
==================================================
RUNNING PARAKH APPLICANT PORTAL INTEGRATION TESTS
==================================================
Test 1: POST /api/v1/auth/login                       ✓ Passed
Test 2: GET /api/v1/auth/me                           ✓ Passed
Test 3: Profile lifecycle                             ✓ Passed
Test 4: POST /api/v1/applications                     ✓ Passed
Test 5: POST /api/v1/consents                         ✓ Passed
Test 6: POST /api/v1/financial-signals                ✓ Passed
Test 7: POST /api/v1/assess                           ✓ Passed
Test 8: GET /assessments/latest & adaptAssessment     ✓ Passed
Test 9: Browser Refresh Simulation                    ✓ Passed
Test 10: GET /applications/applicant                  ✓ Passed
Test 11: GET /applications/{id}                       ✓ Passed
Test 12: POST /consents/{id}/revoke                   ✓ Passed
Test 13: Unauthorized request (401)                   ✓ Passed
==================================================
ALL 13 APPLICANT INTEGRATION TESTS PASSED!
==================================================
```

### 7.3 Backend & ML Test Suites
- **ML / Data Suite:** **273 passed, 0 failed** in 7.97s.
- **Backend Suite:** **237 passed, 0 failed, 39 skipped** (live PostgreSQL fixtures) in 41.44s.

---

## 8. Mock Data Status

- **`frontend/apps/web/data/mock/user.ts`:** Remains untouched as an offline testing fixture; verified that zero production pages import it.
- **`frontend/apps/web/data/mock/admin.ts`:** `mockOperationalAlerts` is retained exclusively for dashboard operational announcements; all application, analytics, and assessment data is fetched from live backend endpoints.
- **`CashflowVolatilityChart.tsx`:** Synthetic 12-week reference curve is preserved and dynamically annotated with the backend-computed rebound rate.

---

## 9. Authentication & Security Audit

- JWT Bearer authentication verified across all routes.
- HTTP 401 triggers `onUnauthorized()` $\to$ purges `parakh_auth_token` and redirects to `/login`.
- HTTP 403 triggers authorization rejection / consent error without exposing internal backend tracebacks.
- Sensitive access tokens are never logged or exposed in UI views.

---

## 10. Final Integration Status

- **Status:** **INTEGRATION COMPLETE & VERIFIED**
- **Contract Adherence:** 100% compliant with FastAPI backend and Phase 9 inference specifications.
- **ML Boundaries:** Zero modifications made to ML models, model artifacts, datasets, or backend schemas.
- **Score Fabrication:** Eliminated. Unrated assessments are explicitly presented as unrated across all views.
