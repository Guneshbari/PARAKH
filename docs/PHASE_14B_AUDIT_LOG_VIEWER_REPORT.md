# Phase 14B — Audit Log Viewer UI
**Gap Closed:** P2-02 from the frozen Phase 12B Frontend ↔ Backend ↔ ML Gap Analysis Report  
**Branch:** `ml/credit-risk`  
**Commit:** `feat: add audit log viewer`  
**Previous Phase:** 14A (`49df170` — Implement Operational Alerts)

---

## 1. Objective

Connect the existing `GET /api/v1/audit-logs` backend capability to a reviewer/admin-facing audit trail viewer with:

- **RBAC enforcement** — `REVIEWER` and `ADMIN` allowed; `APPLICANT` rejected with 403
- **Action and entity-type filtering** with dropdown selectors
- **Pagination** (20 events per page, Previous/Next controls, skip/limit)
- **Application UUID and User UUID** text filters
- **Event detail modal** with safe, sanitized metadata rendering
- **Privacy/PII guarantees** — zero credentials, passwords, tokens, raw transactions exposed
- **Clear loading, empty, and error states**
- **JSON export** for current page audit events

---

## 2. Gap Reference — P2-02

> **P2-02** — Build Audit Log Viewer UI  
> *"Create an Admin audit log viewer consuming `GET /api/v1/audit-logs`."*  
> — Phase 12B Gap Analysis Report, line 537

---

## 3. Backend Changes

### 3.1 `backend/app/api/v1/audit.py`

**Changed:** RBAC on both audit endpoints from `UserRole.ADMIN` → `UserRole.REVIEWER, UserRole.ADMIN`

```
Before: current_user: User = Depends(require_role(UserRole.ADMIN))
After:  current_user: User = Depends(require_role(UserRole.REVIEWER, UserRole.ADMIN))
```

This allows Priya Sharma (REVIEWER) and all ADMIN users to access audit trail records.  
`APPLICANT` callers still receive **HTTP 403 Forbidden**.  
Unauthenticated callers still receive **HTTP 401 Unauthorized**.

### 3.2 Backend Test Updates

| File | Change |
|------|--------|
| `backend/tests/test_audit_logging.py` | Added `reviewer` user in `TestAuditApiAndSecurity.setUp`; expanded `test_32` to assert reviewer → 200 and admin → 200 |
| `backend/tests/test_auth_integration.py` | Updated `test_11_reviewer_rbac_permissions` to assert reviewer → 200 (was incorrectly asserting 403 before Phase 14B); updated `test_10` comment |
| `backend/tests/test_phase14b_audit_viewer.py` | **New file** — 10 dedicated tests |

---

## 4. New Backend Test Suite — `test_phase14b_audit_viewer.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_01_unauthenticated_request_rejected` | No bearer token | 401 |
| `test_02_applicant_role_rejected` | APPLICANT caller | 403 |
| `test_03_reviewer_role_allowed` | REVIEWER caller | 200, list of ≥3 records |
| `test_04_admin_role_allowed` | ADMIN caller | 200, list of ≥3 records |
| `test_05_filter_by_action` | `?action=AUTH_LOGIN_SUCCESS` | 200, 1 record |
| `test_06_filter_by_entity_type` | `?entity_type=Application` | 200, 1 record |
| `test_07_filter_by_application_id` | `?application_id={uuid}` | 200, 2 linked records |
| `test_08_pagination_skip_and_limit` | `?limit=1&skip=0` vs `skip=1` | 200, distinct IDs |
| `test_09_get_single_audit_log_by_id` | `GET /audit-logs/{id}` | 200 for reviewer, 403 for applicant |
| `test_10_privacy_and_zero_pii_assurance` | Inspect all metadata keys | No password, password_hash, raw_transactions, bank_account, secret_key |

---

## 5. Frontend Changes

### 5.1 `frontend/packages/types/index.ts`

Added `AuditLogEntry` domain interface:

```typescript
export interface AuditLogEntry {
  id: string;
  userId?: string | null;
  applicationId?: string | null;
  action: string;
  entityType: string;
  entityId?: string | null;
  actorRole?: string | null;
  outcome?: string | null;
  metadata?: Record<string, any> | null;
  createdAt: string;
}
```

### 5.2 `frontend/packages/api/types.ts`

Updated `BackendAuditLogResponse`:
- Added `created_at?: string` (actual backend field)
- Made `timestamp?: string` optional (legacy alias)
- Made `outcome` nullable (`outcome?: string | null`)
- Made `metadata` nullable (`metadata?: Record<string, any> | null`)

### 5.3 `frontend/packages/api/adapters.ts`

Added `adaptAuditLog(backend: BackendAuditLogResponse): AuditLogEntry` — maps snake_case backend fields to camelCase domain fields, extracts `actor_role` and `outcome` from top-level or `metadata` as fallback, resolves `createdAt` from `created_at` or `timestamp`.

### 5.4 `frontend/packages/api/index.ts`

- Added `application_id?: string` to `getAuditLogs` params
- Added `getAuditLogsAdapted(params)` method that calls `getAuditLogs` and maps through `adaptAuditLog`

### 5.5 `frontend/apps/web/components/layout/Sidebar.tsx`

Added `{ href: '/admin/audit-logs', label: 'Audit Logs', icon: History }` to `adminLinks` between Model Insights and Profile.

### 5.6 `frontend/apps/web/app/admin/audit-logs/page.tsx` _(new file)_

Full audit trail viewer page (protected by existing `AdminLayout` with `<RouteGuard requiredRole="reviewer">`):

**UI Sections:**

| Section | Description |
|---------|-------------|
| Page Header | "Audit Trail & System Governance" with SOC2 / DPDP compliance badges, Refresh, Export JSON buttons |
| Stats Row | 4 cards: Viewed Events, Auth & Security, Assessments & ML, Entity Operations |
| Filter Controls | Action dropdown (15 options), Entity Type dropdown (11 options), Application UUID input, User UUID input |
| Events Table | Timestamp (local + ISO), Action badge (colour-coded), Entity + EntityId, Actor/User (with role), Application UUID (linkable), Outcome badge, Inspect button |
| Pagination | Previous / Page number / Next; `PAGE_SIZE = 20`; detects hasMore by requesting `limit + 1` |
| Empty State | Context-aware: empty ledger vs. no filter matches with reset action |
| Error State | Error banner with Retry button |
| Event Inspect Modal | Full event detail with copy-to-clipboard, sanitized metadata JSON viewer, DPDP assurance notice |

**Privacy / PII Guarantees:**

- No passwords, tokens, API keys, raw transaction blobs, GPS coordinates, demographic attributes, or contact books are rendered
- Metadata displayed exactly as returned from the backend's `AuditService.sanitize_audit_metadata()` which strips prohibited fields at write time

---

## 6. Regression Test Results

| Suite | Tests | Passed | Skipped | Failed |
|-------|-------|--------|---------|--------|
| `test_audit_logging.py` | 35 | 33 | 2 | 0 |
| `test_phase14b_audit_viewer.py` | 10 | 10 | 0 | 0 |
| `test_operational_alerts.py` | 17 | 17 | 0 | 0 |
| `test_auth_integration.py` | included in full suite | — | — | 0 |
| **Full suite** (`backend/tests/ + tests/ml/`) | **521** | **481** | **40** | **0** |

---

## 7. TypeScript Compilation

```
docker compose exec frontend /app/node_modules/.bin/tsc --noEmit --project apps/web/tsconfig.json
# Exit code: 0
```

---

## 8. Frozen Model Artifact Integrity

| Artifact | SHA-256 |
|----------|---------|
| `volatility_aware_risk_model.joblib` | `88e8c4d6f75470a600b51e8f76fa442df7e43bb1766a7e759751a786e71c4060` ✅ |
| `FINAL_MODEL.json` | `e8f593bd1714bd93054fa897f343b900bf5c8c39b49d4c839a061b7cd1fb626f` ✅ |
| `credit_risk_preprocessor.joblib` | `bba8d91afebb8e88fe1e9e30567b60817c77a28afa055befe1cbf77ed4039eb2` ✅ |

No ML model, preprocessing artifact, telemetry feature derivation, scoring formulas, or training data were touched.

---

## 9. Files Changed

| File | Change |
|------|--------|
| `backend/app/api/v1/audit.py` | Opened audit endpoints to REVIEWER role |
| `backend/tests/test_audit_logging.py` | Added reviewer fixture + expanded test_32 |
| `backend/tests/test_auth_integration.py` | Fixed test_11 to match new REVIEWER access |
| `backend/tests/test_phase14b_audit_viewer.py` | **New** — 10-test Phase 14B regression suite |
| `frontend/packages/types/index.ts` | Added `AuditLogEntry` interface |
| `frontend/packages/api/types.ts` | Updated `BackendAuditLogResponse` fields |
| `frontend/packages/api/adapters.ts` | Added `adaptAuditLog` function |
| `frontend/packages/api/index.ts` | Added `application_id` param + `getAuditLogsAdapted` |
| `frontend/apps/web/components/layout/Sidebar.tsx` | Added Audit Logs nav link (History icon) |
| `frontend/apps/web/app/admin/audit-logs/page.tsx` | **New** — Full audit trail viewer page |
| `docs/PHASE_14B_AUDIT_LOG_VIEWER_REPORT.md` | This report |

---

## 10. Gap Status

| Gap | Status |
|-----|--------|
| **P2-02** Build Audit Log Viewer UI | ✅ **CLOSED** |
