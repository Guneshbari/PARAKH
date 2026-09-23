# PARAKH ML Data Contract and Dataset Specification
**Document Version:** 1.0.0  
**Phase:** Phase 1 — Data Definition  
**Branch:** `ml/credit-risk`  
**Problem Statement:** CX0506 — Credit Score for the Invisible  
**Domain:** FinTech / Digital Payments / Alternative Credit Risk Modeling  
**Status:** Approved Data Contract  

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Relationship to Phase 0](#2-relationship-to-phase-0)
3. [Dataset Unit and Entity Model](#3-dataset-unit-and-entity-model)
4. [Temporal Boundary and Timeline](#4-temporal-boundary-and-timeline)
5. [Raw Input Signal Contract](#5-raw-input-signal-contract)
6. [Income Time-Series Contract](#6-income-time-series-contract)
7. [Work Activity Contract](#7-work-activity-contract)
8. [Platform Behaviour Contract](#8-platform-behaviour-contract)
9. [Aggregated Financial Signal Contract](#9-aggregated-financial-signal-contract)
10. [Payment Behaviour Contract](#10-payment-behaviour-contract)
11. [Financial Obligation Contract](#11-financial-obligation-contract)
12. [Data Sufficiency Contract](#12-data-sufficiency-contract)
13. [Missing Data Semantics](#13-missing-data-semantics)
14. [Validation Constraints](#14-validation-constraints)
15. [Income Behaviour Data Requirements](#15-income-behaviour-data-requirements)
16. [Feature Lineage](#16-feature-lineage)
17. [Target/Label Contract](#17-targetlabel-contract)
18. [Synthetic Data Requirements for Phase 2](#18-synthetic-data-requirements-for-phase-2)
19. [Train/Validation/Test Data Contract](#19-trainvalidationtest-data-contract)
20. [Privacy and Data Minimization](#20-privacy-and-data-minimization)
21. [Leakage Prevention](#21-leakage-prevention)
22. [Open Decisions](#22-open-decisions)
23. [Phase 2 Handoff](#23-phase-2-handoff)

---

## 1. Purpose

This document establishes the formal, implementation-ready **Data Contract and Dataset Specification** for the PARAKH Machine Learning system. It translates the high-level architecture established in Phase 0 ([`docs/ml-specification.md`](file:///home/gnx/Projects/PARAKH/docs/ml-specification.md)) into exact tabular and time-series schemas, rigorous temporal boundary constraints, data sufficiency triggers, feature lineages, and target labeling rules.

### Scope Boundaries for Phase 1
- **Specification Only:** This document defines schemas, types, nullability, time windows, and validation contracts.
- **No Data Generation:** No synthetic datasets, CSVs, Parquet files, or SQLite databases are created in this phase (deferred to Phase 2).
- **No Code Implementation:** No Python feature extractors, preprocessors, or model scripts are implemented (deferred to Phases 3–6).
- **No Backend Modification:** Backend schemas and services remain untouched. Contextual alignment is maintained via explicit mapping.

---

## 2. Relationship to Phase 0

Phase 1 directly operationalizes the architectural decisions finalized in [`docs/ml-specification.md`](file:///home/gnx/Projects/PARAKH/docs/ml-specification.md). All fixed decisions are preserved without modification:

| Phase 0 Architectural Decision | Phase 1 Data Contract Realization |
| :--- | :--- |
| **Prediction Target** | Calibrated default probability $P(\text{Default} \mid \mathbf{x}_{\text{obs}})$, with synthetic default defined by cash-flow insolvency over the prediction window. |
| **Unit of Prediction** | Loan application-level assessment anchored to applicant profile at cutoff timestamp $t_0$. |
| **Observation Window ($T_{\text{obs}}$)** | 90 days trailing strictly before $t_0$ ($[t_0 - 90\text{d}, t_0)$). |
| **Minimum History Floor** | Minimum 30 days active history and $\ge 4$ completed payout cycles. |
| **Prediction Window ($T_{\text{pred}}$)** | 30 to 90 days forward strictly after $t_0$ ($(t_0, t_0 + T_{\text{pred}}]$). |
| **Output Risk Tiers** | `LOWER`, `MODERATE`, `HIGHER`, and `INSUFFICIENT` (matching backend [`RiskLevel`](file:///home/gnx/Projects/PARAKH/backend/app/models/assessment.py#L26-L32)). |
| **Income Behaviour Pillars** | 6 pillars: Level, Volatility, Trend, Consistency, Recovery, Frequency. |
| **Earning Archetypes** | 4 primary (Healthy Volatile, Stable, Declining, Irregular) + 2 edge cohorts (High Obligation, Insufficient Data). |
| **Feature Taxonomy** | 10 modular categories spanning 40+ derived indicators. |
| **Insufficient Evidence** | Deterministic short-circuiting on truncated history, sparse payouts, or missing core signal pillars. |
| **Data Minimization** | Total rejection of raw transaction texts, credentials, raw UPI logs, GPS coordinates, and contact lists. |

### Contextual Backend Discrepancies Acknowledged
1. **Mock Backend Deductions vs. ML Interaction:** The existing backend mock engine ([`MockAssessmentEngine`](file:///home/gnx/Projects/PARAKH/backend/app/assessment/mock.py#L17-L26)) deducts points linearly for volatility (`base -= min(0.25, vol * 0.5)`). The ML data contract preserves fine-grained time-series signals so Phase 4/6 can compute joint recovery-conditioned features, proving that healthy volatility does not equal default risk.
2. **Persistence vs. Time-Series Storage:** Existing backend table `financial_signals` ([`FinancialSignal`](file:///home/gnx/Projects/PARAKH/backend/app/models/financial_signal.py#L37-L43)) stores pre-aggregated scalar indicators (`average_income`, `income_volatility`). The ML training contract requires time-series sequences (`payout_amount`, `payout_date`, `active_days`) to extract bounceback velocities and drawdowns.

---

## 3. Dataset Unit and Entity Model

### 3.1 Entity Definitions
To ensure unambiguous data engineering across future phases, the four core entities are defined:

1. **Applicant (`applicant_profile_id`):** The individual human gig worker. A persistent entity identified across multiple applications and temporal observations.
2. **Loan Application (`application_id`):** A discrete financing request submitted at timestamp $t_0$. Contains requested loan principal, tenure, and purpose.
3. **Credit Assessment (`assessment_id`):** The evaluation event produced by the ML model at or immediately following $t_0$.
4. **Primary ML Dataset Row (Training Example):** A single application-level assessment anchored at cutoff timestamp $t_0$, where all predictive features are extracted strictly from $[t_0 - T_{\text{obs}}, t_0)$ and the ground truth outcome is observed strictly within $(t_0, t_0 + T_{\text{pred}}]$.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Applicant Profile (applicant_profile_id)                               │
│ Unique worker identity, gig work sector, aggregate tenure              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ 1
                                    │
                                    ▼ N
┌────────────────────────────────────────────────────────────────────────┐
│ Loan Application (application_id)                                      │
│ Submitted at Cutoff Timestamp t_0; requested loan terms (amount, tenure)│
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ 1                              │ 1
                    ▼ 1                              ▼ 1
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│ Historical Observation Slice         │  │ Future Outcome Window        │
│ Range: [t_0 - 90 days, t_0)          │  │ Range: (t_0, t_0 + 30-90 days]│
│ - Income time-series payouts         │  │ - Actual repayment status    │
│ - Work activity & active days logs   │  │ - Delinquency (DPD count)     │
│ - Aggregated financial signals       │  │ - Cashflow solvency state    │
│ - Payment discipline & obligations   │  │                              │
│                                      │  │                              │
│ =======> Predictor Matrix (x) ======>│  │ ===> Target Label (Y) ======>│
└──────────────────────────────────────┘  └──────────────────────────────┘
```

### 3.2 Repeated Assessments Representation
A worker may apply for multiple loans over time ($t_0^{(1)} < t_0^{(2)}$). In the ML dataset:
- Each application constitutes an independent row anchored to its respective cutoff $t_0^{(k)}$.
- Observation windows slide with $t_0^{(k)}$. Signals occurring between $t_0^{(1)}$ and $t_0^{(2)}$ are future outcomes for Application 1, but historical observation features for Application 2.
- **Independence Assumption:** Repeated applications for the same worker are non-independent. To prevent catastrophic data leakage, all splits (train/val/test) must group by `applicant_profile_id`.

---

## 4. Temporal Boundary and Timeline

A strict mathematical temporal boundary is enforced to prevent lookahead bias and target leakage.

```
PAST (Observation Window T_obs)              CUTOFF (t_0)        FUTURE (Prediction Window T_pred)
[==========================================)      |      (========================================]
t_0 - 90 days                                     t_0    t_0 + 1s                     t_0 + 90 days
<------------ Historical Telemetry -------->      |      <----------- Target Outcome ------------>
  • Trailing payouts & earnings                   |        • Actual scheduled installment due dates
  • Daily active work days                        |        • Realized cash flows & living expenses
  • Platform customer ratings                     |        • Default / Insolvency event (Y in {0,1})
  • Bill payment timeliness                       |
  • Existing monthly obligations                  |
──────────────────────────────────────────────────┴────────────────────────────────────────────────► Time
                                            Application Cutoff
                                           (All features frozen)
```

### 4.1 Chronological Partitions
1. **Observation Start ($t_{\text{obs\_start}} = t_0 - 90\text{ days}$):** The earliest timestamp from which raw historical signals are extracted.
2. **Cutoff Timestamp ($t_0$):** The exact UTC timestamp at which the application is submitted.
   - **Hard Rule:** Any signal, log, or transaction with timestamp $t \ge t_0$ is strictly prohibited from entering feature calculations.
3. **Prediction Start ($t_{\text{pred\_start}} = t_0$):** The start of the forward outcome horizon.
4. **Prediction End ($t_{\text{pred\_end}} = t_0 + T_{\text{pred}}$):** The close of the outcome window ($T_{\text{pred}} \in [30, 90]\text{ days}$, matching loan tenure).

---

## 5. Raw Input Signal Contract

Raw signals represent the unengineered inputs ingested from platform APIs, Account Aggregators (BBPS), and application forms.

### 5.1 Signal Field Taxonomy and Ingestion Contract

| Field Name | Description | Data Type | Unit | Frequency | Category | Status | Avail. at $t_0$ | Privacy Class | Missing Policy | Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `applicant_profile_id` | Unique worker identity | UUIDv4 | String | Static | Identity | Required | Yes | Pseudonymous | Error / Reject | Valid UUID |
| `application_id` | Loan application ID | UUIDv4 | String | Static | Identity | Required | Yes | Pseudonymous | Error / Reject | Valid UUID |
| `cutoff_timestamp` | Application timestamp ($t_0$)| ISO-8601 UTC | DateTime | Static | Identity | Required | Yes | Non-sensitive | Error / Reject | $\le \text{Current UTC}$ |
| `gig_work_type` | Primary gig economy sector | String | Categorical| Static | Profile | Required | Yes | Non-sensitive | Default `OTHER`| Enum (see Sec 7) |
| `years_working` | Cumulative gig tenure | Float | Years | Static | Profile | Optional | Yes | Non-sensitive | Retain Null | $\ge 0.0, \le 50.0$ |
| `average_working_days` | Self-reported active days/mo | Integer | Days/Month| Static | Profile | Optional | Yes | Non-sensitive | Retain Null | $\ge 0, \le 31$ |
| `payout_records` | Time-series payout events | Array[Object]| INR | Event/Weekly| Gig Income | Required | Yes | Aggregated Fin.| $\ge 4$ cycles | See Section 6 |
| `active_days_records` | Daily activity logs | Array[Object]| Days | Daily | Work Activity| Required | Yes | Operational | Impute 0 active| See Section 7 |
| `platform_rating` | Composite customer rating | Float | Rating [1-5]| Periodic | Platform | Optional | Yes | Non-sensitive | Retain Null | $\ge 1.0, \le 5.0$ |
| `completed_orders_count`| Total delivered tasks | Integer | Tasks | Periodic | Platform | Optional | Yes | Non-sensitive | Retain Null | $\ge 0$ |
| `cancellation_rate` | Worker trip cancel ratio | Float | Ratio [0-1] | Periodic | Platform | Optional | Yes | Non-sensitive | Retain Null | $\ge 0.0, \le 1.0$ |
| `cashflow_buffer` | Average liquid bank reserve | Decimal(12,2)| INR | Trailing 90d| Cashflow | Optional | Yes | Aggregated Fin.| Retain Null | $\ge 0.00$ |
| `utility_on_time_ratio` | Ratio of timely bill pays | Float | Ratio [0-1] | Monthly | Payment | Optional | Yes | Alternative Fin.| Retain Null | $\ge 0.0, \le 1.0$ |
| `repayment_reliability` | Prior loan repayment rate | Float | Ratio [0-1] | Event | Payment | Optional | Yes | Alternative Fin.| Retain Null | $\ge 0.0, \le 1.0$ |
| `existing_obligation` | Monthly debt commitments | Decimal(12,2)| INR/Month | Trailing 30d| Obligation | Required | Yes | Financial | Default 0.00 | $\ge 0.00$ |
| `requested_loan_amount` | Principal requested | Decimal(12,2)| INR | Application | Obligation | Required | Yes | Financial | Error / Reject | $> 0.00$ |
| `loan_tenure_months` | Requested tenure | Integer | Months | Application | Obligation | Required | Yes | Financial | Error / Reject | $\ge 1, \le 60$ |

---

## 6. Income Time-Series Contract

The income time-series is the central data structure required to evaluate volatility, recovery, trend, and earning consistency. Raw income history must **never be collapsed into a single summary mean** before feature engineering.

### 6.1 Payout Event Schema (`payout_records`)
Each entry in the `payout_records` array represents a verified electronic settlement from an on-demand platform:

```json
{
  "payout_id": "pay_982f1b4c-2b5d-4f1e-8e6d-92a8e411b021",
  "payout_timestamp": "2026-08-15T18:30:00Z",
  "gross_earnings": 8450.00,
  "net_payout_amount": 7920.00,
  "deductions_amount": 530.00,
  "payout_period_start": "2026-08-08T00:00:00Z",
  "payout_period_end": "2026-08-14T23:59:59Z",
  "active_days_in_period": 6,
  "payout_channel": "PLATFORM_DIRECT_DEPOSIT"
}
```

### 6.2 Income Time-Series Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `payout_id` | String | Identifier | Unique settlement transaction reference | No | Unique per record | Generated before $t_0$ |
| `payout_timestamp` | DateTime | UTC ISO-8601 | Exact settlement timestamp | No | Valid UTC string | $t_0 - 90\text{d} \le t < t_0$ |
| `gross_earnings` | Decimal(10,2)| INR | Total earnings before platform commission | No | $\ge 0.00$ | Occurred before $t_0$ |
| `net_payout_amount` | Decimal(10,2)| INR | Net amount credited to worker | No | $\ge 0.00$, $\le \text{gross}$ | Occurred before $t_0$ |
| `deductions_amount` | Decimal(10,2)| INR | Fuel/platform fee deductions | Yes | $\ge 0.00$, default 0.00 | Occurred before $t_0$ |
| `payout_period_start`| DateTime | UTC ISO-8601 | Start of earnings cycle | No | $< \text{period\_end}$ | $\ge t_0 - 90\text{d}$ |
| `payout_period_end` | DateTime | UTC ISO-8601 | End of earnings cycle | No | $\le \text{payout\_timestamp}$ | $< t_0$ |
| `active_days_in_period`| Integer | Days | Active days worked during cycle | No | $0 \le d \le 7$ (for weekly) | Verified before $t_0$ |
| `payout_channel` | String | Categorical | Channel (DIRECT_DEPOSIT, UPI_CASHOUT)| Yes | Enum | Recorded before $t_0$ |

### 6.3 Time-Series Structuring Rules
1. **Observation Granularity:** Payout records are binned into standard weekly calendar buckets $[W_k, W_{k+1})$ across the 90-day window ($12\text{ to }13\text{ weeks}$).
2. **Zero-Earning Weeks:** If an applicant is active (logged in) but earns ₹0, the week is recorded with `net_payout_amount = 0.00` and `active_days_in_period > 0`.
3. **Inactive Weeks:** If the applicant did not log into the platform, the week is recorded with `net_payout_amount = 0.00` and `active_days_in_period = 0`.
4. **Disconnection / Missing Telemetry:** If platform data sync failed, the period is marked `MISSING_PERIOD` (distinct from zero-earning).
5. **Deduplication:** Payout records with identical `payout_id` or identical `(payout_timestamp, net_payout_amount)` are deduplicated prior to aggregation.
6. **Minimum Observation Count:** A minimum of **4 completed payout cycles** is required. Datasets with fewer than 4 cycles trigger `INSUFFICIENT_EVIDENCE`.

---

## 7. Work Activity Contract

Work activity signals measure the physical labor input and engagement continuity of the gig worker.

### 7.1 Work Activity Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `activity_date` | Date | YYYY-MM-DD | Daily activity date | No | Valid calendar date | $t_0 - 90\text{d} \le t < t_0$ |
| `is_active_day` | Boolean | Flag | Worker logged in and accepted tasks | No | True / False | Before $t_0$ |
| `hours_online` | Float | Hours | Hours logged into platform dispatch | Yes | $0.0 \le h \le 24.0$ | Before $t_0$ |
| `trips_completed` | Integer | Count | Rides or delivery orders fulfilled | Yes | $\ge 0$ | Before $t_0$ |
| `trip_acceptance_rate`| Float | Ratio [0-1] | Fraction of dispatched tasks accepted | Yes | $0.0 \le r \le 1.0$ | Trailing 90d before $t_0$ |
| `driver_cancellation_rate`| Float | Ratio [0-1] | Fraction of accepted tasks cancelled | Yes | $0.0 \le r \le 1.0$ | Trailing 90d before $t_0$ |

### 7.2 Permitted Gig Work Types (`gig_work_type`)
- `DELIVERY` (Food, grocery, parcel courier)
- `RIDE_HAILING` (Auto-rickshaw, two-wheeler taxi, cab driver)
- `LOGISTICS` (Commercial mini-truck, intercity freight)
- `HOME_SERVICES` (Repairs, cleaning, salon, domestic service)
- `FREELANCE_MICRO` (Digital tasks, transcription, creative gig work)
- `OTHER` (Unclassified gig sector)

---

## 8. Platform Behaviour Contract

Reputational and platform standing metrics derived from partner platform feeds.

### 8.1 Platform Behaviour Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `platform_rating` | Float | Rating [1.0-5.0]| Trailing customer satisfaction rating | Yes | $1.0 \le r \le 5.0$ | Snapshot at $t_0$ |
| `lifetime_trips` | Integer | Count | All-time trips fulfilled on platform | Yes | $\ge 0$ | Cumulative to $t_0$ |
| `platform_tier` | String | Categorical | Platform status (BRONZE, SILVER, GOLD)| Yes | Enum | Current at $t_0$ |
| `account_standing` | String | Categorical | Operational status (ACTIVE, SUSPENDED)| No | ACTIVE / SUSPENDED | Current at $t_0$ |
| `deactivation_warnings`| Integer | Count | Formal safety/compliance strikes | Yes | $\ge 0$ | Trailing 90d before $t_0$ |

---

## 9. Aggregated Financial Signal Contract

Aligns with the existing backend [`FinancialSignal`](file:///home/gnx/Projects/PARAKH/backend/app/models/financial_signal.py#L37-L43) entity, defining the summary indicators computed over the trailing 90 days.

### 9.1 Aggregated Financial Signal Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `source` | String | Enum | Signal source category | No | PLATFORM, FINANCIAL_ACTIVITY, UTILITY, DERIVED | Up to $t_0$ |
| `measurement_period_start`| DateTime | UTC ISO-8601 | Start of aggregation window | Yes | Exactly $t_0 - 90\text{ days}$ | $< t_0$ |
| `measurement_period_end` | DateTime | UTC ISO-8601 | End of aggregation window | Yes | $\le t_0$ | $\le t_0$ |
| `average_income` | Decimal(12,2)| INR | Mean monthly/periodic income | Yes | $\ge 0.00$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `median_income` | Decimal(12,2)| INR | Median periodic income (robust floor) | Yes | $\ge 0.00$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `income_volatility` | Decimal(8,4) | Ratio | Coefficient of variation ($\sigma / \mu$) | Yes | $\ge 0.0000$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `income_trend` | String | Categorical | Trajectory (GROWING, STABLE, DECLINING)| Yes | Max length 50 | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `active_days` | Integer | Days | Total active working days in window | Yes | $0 \le d \le 90$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `payment_regularity` | Decimal(5,4) | Index [0-1] | Regularity of platform payout receipts | Yes | $0.0000 \le p \le 1.0000$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `cashflow_buffer` | Decimal(12,2)| INR | Average liquid reserve balance | Yes | $\ge 0.00$ | Evaluated over $[t_0-90\text{d}, t_0)$ |
| `existing_obligation`| Decimal(12,2)| INR/Month | Verified monthly debt commitments | Yes | $\ge 0.00$ | Evaluated over $[t_0-30\text{d}, t_0)$ |
| `repayment_reliability`| Decimal(5,4)| Index [0-1] | Historical alternative debt repayment rate| Yes | $0.0000 \le r \le 1.0000$ | Cumulative to $t_0$ |
| `signal_metadata` | JSONB / Dict | Key-Value | Sanitized non-sensitive attributes | Yes | Valid JSON object | Generated before $t_0$ |

---

## 10. Payment Behaviour Contract

Alternative credit discipline indicators captured from consented Bharat Bill Payment System (BBPS) or telecom recharge feeds.

### 10.1 Payment Behaviour Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `utility_bills_observed_count`| Integer | Count | Count of utility/telecom bills tracked | Yes | $\ge 0$ | In $[t_0-90\text{d}, t_0)$ |
| `utility_on_time_ratio` | Float | Ratio [0-1] | Fraction of bills paid on or before due date| Yes | $0.0 \le r \le 1.0$ | In $[t_0-90\text{d}, t_0)$ |
| `utility_max_delay_days` | Integer | Days | Maximum days past due on utility bill | Yes | $\ge 0$ | In $[t_0-90\text{d}, t_0)$ |
| `telecom_recharge_regularity`| Float | Index [0-1] | Regularity of prepaid mobile data recharges| Yes | $0.0 \le r \le 1.0$ | In $[t_0-90\text{d}, t_0)$ |
| `peer_microloan_default_count`| Integer | Count | Defaults on digital peer micro-advances | Yes | $\ge 0$ | In $[t_0-90\text{d}, t_0)$ |

---

## 11. Financial Obligation Contract

Captures existing borrower commitments and the specific terms of the requested credit facility.

### 11.1 Financial Obligation Specification Table

| Field Name | Type | Unit | Description | Nullable | Validation Constraints | Temporal Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `requested_loan_amount` | Decimal(12,2)| INR | Financing principal requested | No | $> 0.00$ | Stated at $t_0$ |
| `loan_tenure_months` | Integer | Months | Requested repayment period | No | $\ge 1, \le 60$ | Stated at $t_0$ |
| `loan_purpose` | String | Text | Purpose (e.g., VEHICLE_MAINTENANCE) | Yes | Max 255 chars | Stated at $t_0$ |
| `existing_monthly_debt` | Decimal(12,2)| INR/Month | Verified monthly debt commitments | Yes | $\ge 0.00$, default 0.00 | Known at $t_0$ |
| `estimated_monthly_installment`| Decimal(10,2)| INR/Month | Projected monthly installment for requested loan| No | $> 0.00$ | Derived at $t_0$ |
| `debt_to_income_ratio` | Float | Ratio | `existing_monthly_debt / median_income` | Yes | $\ge 0.0$ | Derived at $t_0$ |
| `projected_total_dti` | Float | Ratio | `(existing_monthly_debt + installment) / median`| Yes | $\ge 0.0$ | Derived at $t_0$ |

---

## 12. Data Sufficiency Contract

The PARAKH system enforces an ethical **refusal to guess** when data evidence is insufficient to produce a responsible statistical estimate.

### 12.1 Deterministic Sufficiency Thresholds

```
                      INCOMING ASSESSMENT DATA AT t_0
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │              SUFFICIENCY EVALUATION GATE               │
        │                                                        │
        │ 1. Observation History >= 30 days?                     │
        │ 2. Completed Payout Cycles >= 4?                       │
        │ 3. Core Signal Groups >= 2 present?                    │
        │ 4. Income Baseline non-null and > 0?                   │
        │ 5. Contradictory signals absent?                       │
        └────────────────────────────┬───────────────────────────┘
                                     │
                        All Pass     │    Any Fail
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │   PROCEED TO SCORING      │   │  TRIGGER SHORT-CIRCUIT    │
       │ Route to Feature Engine & │   │ Return INSUFFICIENT       │
       │ Calibrated Risk Model     │   │ Null score & probabilities│
       └───────────────────────────┘   └───────────────────────────┘
```

An assessment is short-circuited to `INSUFFICIENT` if **any** of the following conditions trigger:
1. **Truncated History:** Observation span is $< 30\text{ days}$ between the earliest recorded payout and $t_0$.
2. **Cycle Sparsity:** Total completed platform payout cycles $< 4$.
3. **Pillar Missingness:** Fewer than **2 core signal groups** are present from the set:
   $$\{\text{Gig Income Series}, \text{Daily Work Activity}, \text{Cashflow Buffer}, \text{Payment Discipline}, \text{Financial Obligations}\}$$
4. **Zero/Null Income Baseline:** Both `average_income` and `median_income` are null or ₹0.00.
5. **Direct Data Contradiction:** E.g., `active_days > 20` but total gross earnings = ₹0.00 over 90 days, or measurement start date $> t_0$.

### 12.2 Output Contract When Insufficient
```json
{
  "credit_score": null,
  "risk_probability": null,
  "risk_level": "INSUFFICIENT",
  "confidence": 0.2250,
  "assessment_status": "COMPLETED",
  "key_factors": [
    "Insufficient platform observation history (minimum 30 days required)",
    "Fewer than 4 completed payout cycles available to assess earning stability"
  ],
  "missing_signal_guidance": [
    "Connect an active gig platform account with at least 30 days of payout history",
    "Provide verified utility bill payment history via BBPS"
  ]
}
```

---

## 13. Missing Data Semantics

To prevent erroneous imputation, missingness is categorized into distinct semantic states:

| State | Definition | Example | ML Pipeline Handling Policy |
| :--- | :--- | :--- | :--- |
| **Missing Value (`null`)** | Field is unpopulated for an individual record. | `platform_rating = null` | Retain `null`; impute via median in Phase 3/4 pipeline with explicit `_was_missing` binary indicator. |
| **Missing Period (`NaN`)** | Time interval has no reported data due to telemetry gap. | Week 5 has no sync log. | Interpolate linearly only if gap $\le 1$ week; otherwise mark as unverified gap. |
| **Missing Signal Group** | Entire source channel is unconsented or unavailable. | Applicant has no utility account. | Permitted if $\ge 2$ other core groups exist; default group features to neutral weight; do not reject. |
| **Zero Value (`0.00`)** | True observed zero. | `existing_monthly_debt = 0.00` | **Never treat as missing.** Genuine numerical zero representing debt-free status. |
| **Not Applicable (`N/A`)**| Concept does not apply to this borrower profile. | `cancellation_rate` for domestic cleaners.| Assign neutral domain sentinel or separate categorical level `NOT_APPLICABLE`. |
| **Invalid Value** | Value violates physical or logical domain bounds. | `active_days = -5`, `rating = 7.2` | Reject record during validation (Phase 3); do not impute. |

---

## 14. Validation Constraints

The future data validation pipeline (implemented in Phase 3) must enforce the following assertions:

### 14.1 Integrity and Range Constraints

```
┌────────────────────────────────────────────────────────────────────────┐
│                        VALIDATION RULE ENGINE                          │
├──────────────────────────┬──────────────────────┬──────────────────────┤
│ Constraint Check         │ Target Field         │ Enforcement Boundary │
├──────────────────────────┼──────────────────────┼──────────────────────┤
│ Non-Negative Income      │ gross/net earnings   │ >= 0.00 INR          │
│ Bounded Active Days      │ active_days_in_period│ 0 <= days <= 7/week  │
│ Bounded Rating           │ platform_rating      │ 1.00 <= r <= 5.00    │
│ Bounded Probabilities    │ on-time/cancel ratios│ 0.0000 <= p <= 1.0000│
│ Positive Financing Terms │ loan amount / tenure │ amount > 0, 1 <= m <= 60│
│ Temporal Ordering        │ observation / cutoff │ start < end <= t_0   │
│ Identity Format          │ UUID identifiers     │ RFC 4122 compliance  │
│ Anti-Prohibited Scan     │ Entire Payload       │ 0 prohibited keys    │
└──────────────────────────┴──────────────────────┴──────────────────────┘
```

1. **Monetary Non-Negativity:** `gross_earnings >= 0`, `net_payout_amount >= 0`, `cashflow_buffer >= 0`, `existing_obligation >= 0`.
2. **Activity Bounds:** Daily active hours $\in [0.0, 24.0]$; weekly active days $\in [0, 7]$; monthly active days $\in [0, 31]$.
3. **Platform Rating Range:** `platform_rating` $\in [1.0, 5.0]$.
4. **Ratio Normalization:** `utility_on_time_ratio`, `cancellation_rate`, `repayment_reliability` $\in [0.0, 1.0]$.
5. **Loan Term Bounds:** `requested_loan_amount > 0`; `loan_tenure_months` $\in [1, 60]$.
6. **Temporal Consistency:** `payout_period_start < payout_period_end <= payout_timestamp < cutoff_timestamp (t_0)`.
7. **Prohibited Key Interception:** Automatic rejection of any record containing keys from `PROHIBITED_FIELDS` ([`backend/app/assessment/schemas.py`](file:///home/gnx/Projects/PARAKH/backend/app/assessment/schemas.py#L10-L29)).

---

## 15. Income Behaviour Data Requirements

To test the central volatility-aware hypothesis in subsequent phases, the raw data schema must supply the exact inputs needed to compute the six behavioral pillars:

```
Raw Payout Series: {(t_1, I_1), (t_2, I_2), ..., (t_N, I_N)}  where t_N < t_0
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│    LEVEL     │        │  VOLATILITY  │        │    TREND     │
│ Median(I)    │        │ CV = sigma/mu│        │ OLS Slope    │
│ P25 floor    │        │ Downside Var │        │ Momentum     │
└──────────────┘        └──────────────┘        └──────────────┘
       │                       │                       │
       ├───────────────────────┼───────────────────────┤
       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ RECOVERY     │        │ CONSISTENCY  │        │  FREQUENCY   │
│ Bounceback % │        │ Active ratio │        │ Delta t gaps │
│ Days to base │        │ Zero-earn wks│        │ Payout type  │
└──────────────┘        └──────────────┘        └──────────────┘
```

1. **Pillar 1: Income Level:**
   - *Inputs Required:* Net payout series $\{I_1, I_2, \dots, I_N\}$ over trailing 90 days.
   - *Future Calculation:* $\text{Median}(I)$, 25th percentile ($P_{25}$), Trimmed Mean.
2. **Pillar 2: Income Volatility:**
   - *Inputs Required:* Payout series $\{I_k\}$, period lengths.
   - *Future Calculation:* Coefficient of Variation ($\text{CV} = \sigma / \mu$), Downside Semi-Variance ($\frac{1}{M}\sum (I_k - \mu)^2 \cdot \mathbb{I}(I_k < \mu)$), IQR ratio.
3. **Pillar 3: Income Trend:**
   - *Inputs Required:* Timestamped series $\{(t_k, I_k)\}$.
   - *Future Calculation:* Ordinary Least Squares linear regression slope ($\beta$), 30-day vs. 90-day momentum ratio ($\frac{\mu_{30\text{d}}}{\mu_{90\text{d}}}$).
4. **Pillar 4: Income Consistency:**
   - *Inputs Required:* Daily active days array $\{A_d\}_{d=1}^{90}$, payout regularity indicator.
   - *Future Calculation:* Active day ratio ($\sum A_d / 90$), zero-earning week count, maximum consecutive non-earning streak length.
5. **Pillar 5: Income Recovery:**
   - *Inputs Required:* High-resolution sequence of weekly earnings.
   - *Future Calculation:* Identification of trough events ($I_k \le 0.70 \times \text{Median}$); post-trough bounceback ratio ($\frac{I_{k+1}}{\text{Median}}$); duration in days to recover to $\ge 85\%$ baseline.
6. **Pillar 6: Earning Frequency:**
   - *Inputs Required:* Intervals between consecutive payout timestamps ($\Delta t_k = t_k - t_{k-1}$).
   - *Future Calculation:* Median payout gap in days, payout cadence regularity index.

---

## 16. Feature Lineage

This planning table establishes the exact source signal, observation window, derivation method, and leakage risk for all 40 future features across the 10 groups.

### 16.1 Master Feature Lineage Planning Table

| Future Feature Name | Source Signal Group | Source Observation Window | Derived From / Calculation Method | Avail. at $t_0$ | Leakage Risk | Status | Target Future Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `feat_inc_median_90d` | Gig Income | $[t_0-90\text{d}, t_0)$ | Median of net weekly payouts | Yes | Low | Required | Phase 4 |
| `feat_inc_p25_90d` | Gig Income | $[t_0-90\text{d}, t_0)$ | 25th percentile of payouts | Yes | Low | Required | Phase 4 |
| `feat_inc_mean_90d` | Gig Income | $[t_0-90\text{d}, t_0)$ | Arithmetic mean of payouts | Yes | Low | Optional | Phase 4 |
| `feat_inc_trimmed_mean` | Gig Income | $[t_0-90\text{d}, t_0)$ | 10% trimmed mean of payouts | Yes | Low | Optional | Phase 4 |
| `feat_inc_cv_90d` | Gig Income | $[t_0-90\text{d}, t_0)$ | Std dev / mean of payouts | Yes | Low | Required | Phase 4 |
| `feat_inc_downside_var` | Gig Income | $[t_0-90\text{d}, t_0)$ | Semi-variance below median | Yes | Low | Required | Phase 4 |
| `feat_inc_iqr_ratio` | Gig Income | $[t_0-90\text{d}, t_0)$ | $(P_{75} - P_{25}) / \text{Median}$ | Yes | Low | Optional | Phase 4 |
| `feat_inc_min_max_ratio`| Gig Income | $[t_0-90\text{d}, t_0)$ | Min payout / Max payout | Yes | Low | Optional | Phase 4 |
| `feat_trend_slope_90d` | Gig Income | $[t_0-90\text{d}, t_0)$ | Linear slope over payout cycles | Yes | Low | Required | Phase 4 |
| `feat_trend_momentum_30_90`| Gig Income | $[t_0-90\text{d}, t_0)$ | Mean(last 30d) / Mean(90d) | Yes | Low | Required | Phase 4 |
| `feat_trend_consec_drops`| Gig Income | $[t_0-90\text{d}, t_0)$ | Max consecutive declining cycles| Yes | Low | Optional | Phase 4 |
| `feat_act_active_days_ratio`| Work Activity | $[t_0-90\text{d}, t_0)$ | Active days / 90 | Yes | Low | Required | Phase 4 |
| `feat_act_zero_earn_weeks`| Work Activity | $[t_0-90\text{d}, t_0)$ | Count of weeks with ₹0 income | Yes | Low | Required | Phase 4 |
| `feat_act_max_idle_streak`| Work Activity | $[t_0-90\text{d}, t_0)$ | Max consecutive inactive days | Yes | Low | Optional | Phase 4 |
| `feat_act_weekend_intensity`| Work Activity | $[t_0-90\text{d}, t_0)$ | Weekend hours / Total hours | Yes | Low | Optional | Phase 4 |
| `feat_rec_bounceback_ratio`| Gig Income | $[t_0-90\text{d}, t_0)$ | Post-trough peak / pre-trough | Yes | Low | Required | Phase 4 |
| `feat_rec_days_to_recover`| Gig Income | $[t_0-90\text{d}, t_0)$ | Days elapsed from trough to baseline| Yes | Low | Required | Phase 4 |
| `feat_rec_max_drawdown` | Gig Income | $[t_0-90\text{d}, t_0)$ | $(Peak - Trough) / Peak$ | Yes | Low | Optional | Phase 4 |
| `feat_ten_years_working` | Profile | Static at $t_0$ | Tenure in years | Yes | Low | Optional | Phase 4 |
| `feat_ten_platform_rating`| Platform | Snapshot at $t_0$ | Customer rating $[1-5]$ | Yes | Low | Optional | Phase 4 |
| `feat_ten_trips_completed`| Platform | Trailing 90d | Total rides/orders | Yes | Low | Optional | Phase 4 |
| `feat_ten_cancellation_rate`| Platform | Trailing 90d | Driver cancellation ratio | Yes | Low | Optional | Phase 4 |
| `feat_liq_buffer_to_loan`| Cashflow | Snapshot at $t_0$ | Liquid buffer / Loan principal | Yes | Low | Required | Phase 4 |
| `feat_liq_burn_months` | Cashflow | Snapshot at $t_0$ | Buffer / Monthly obligations | Yes | Low | Required | Phase 4 |
| `feat_liq_net_margin` | Cashflow | Trailing 90d | (Earnings - Expenses) / Earnings| Yes | Low | Optional | Phase 4 |
| `feat_pay_utility_on_time`| Payment | Trailing 90d | On-time bills / Total bills | Yes | Low | Optional | Phase 4 |
| `feat_pay_max_bill_delay`| Payment | Trailing 90d | Maximum days past due | Yes | Low | Optional | Phase 4 |
| `feat_pay_repay_reliability`| Payment | Historical to $t_0$ | Alternative loan repayment index| Yes | Low | Optional | Phase 4 |
| `feat_bur_dti_ratio` | Obligation | Trailing 30d at $t_0$ | Existing debt / Median monthly inc| Yes | Low | Required | Phase 4 |
| `feat_bur_installment_dti`| Obligation | Derived at $t_0$ | Projected loan payment / Median inc| Yes | Low | Required | Phase 4 |
| `feat_bur_total_dti` | Obligation | Derived at $t_0$ | (Debt + Installment) / Median inc| Yes | Low | Required | Phase 4 |
| `feat_bur_loan_to_income`| Obligation | Derived at $t_0$ | Loan principal / Annualized inc | Yes | Low | Optional | Phase 4 |
| `feat_suf_observed_days` | Data Sufficiency| Window span | Days between first log and $t_0$| Yes | Zero | Required | Phase 4 |
| `feat_suf_payout_count` | Data Sufficiency| Window count | Total payout records in window | Yes | Zero | Required | Phase 4 |
| `feat_suf_group_count` | Data Sufficiency| Window presence | Number of active signal groups | Yes | Zero | Required | Phase 4 |
| `feat_suf_missing_ratio` | Data Sufficiency| Completeness | Null fields / Total expected | Yes | Zero | Required | Phase 4 |
| `feat_int_vol_x_recovery`| Interaction | $[t_0-90\text{d}, t_0)$ | `income_cv * days_to_recover` | Yes | Low | Required | Phase 4 |
| `feat_int_vol_x_buffer` | Interaction | $[t_0-90\text{d}, t_0)$ | `income_cv / (buffer_to_loan + 0.1)`| Yes | Low | Required | Phase 4 |
| `feat_int_trend_x_dti` | Interaction | $[t_0-90\text{d}, t_0)$ | `trend_slope * (1.0 + total_dti)`| Yes | Low | Required | Phase 4 |
| `feat_int_resilience_idx`| Interaction | $[t_0-90\text{d}, t_0)$ | Composite bounceback / CV | Yes | Low | Required | Phase 4 |

---

## 17. Target/Label Contract

The target variable defines loan default in the synthetic prototype environment.

### 17.1 Target Definition Specification

| Property | Value / Definition |
| :--- | :--- |
| **Variable Name** | `target_default_flag` ($Y$) |
| **Continuous Target** | `repayment_risk_probability` ($\hat{p} \in [0.0000, 1.0000]$) |
| **Data Type** | Binary Integer ($Y \in \{0, 1\}$) |
| **Positive Class ($Y = 1$)** | Default event: Failure to meet scheduled loan repayment obligations within the prediction window. |
| **Negative Class ($Y = 0$)** | Successful repayment: All scheduled installments settled on or before contractual due dates. |
| **Prediction Horizon ($T_{\text{pred}}$)**| 30 to 90 calendar days forward ($(t_0, t_0 + T_{\text{pred}}]$). |
| **Insolvency Event Condition** | Realized cumulative net cash flows plus liquid buffer over $T_{\text{pred}}$ falls below non-discretionary living costs plus scheduled loan installments: $\sum_{t=t_0}^{t_0+T_{\text{pred}}} \text{NetCashflow}_t + \text{Buffer}_{t_0} < \text{Obligations}_{T_{\text{pred}}} + \text{LivingExpenses}_{T_{\text{pred}}}$ |
| **Right-Censoring Handling** | If borrower withdraws application, deactivates account, or data sync terminates before $t_0 + T_{\text{pred}}$, label is `CENSORED` and excluded from supervised training. |

### 17.2 Isolation of Target from Predictive Features
- **Strict Forward Bounding:** $Y$ is determined exclusively by events in $(t_0, t_0 + T_{\text{pred}}]$.
- **Zero Reverse-Leakage:** No forward outcome variable (e.g., actual installments paid, future earnings in month $+1$, post-cutoff defaults) may be used to construct features.

---

## 18. Synthetic Data Requirements for Phase 2

Phase 2 will implement the synthetic data generator. The generator must construct a multi-profile dataset exhibiting realistic temporal dynamics and behavioral heterogeneity.

### 18.1 Cohort Sampling Proportions

```
┌────────────────────────────────────────────────────────────────────────┐
│                      SYNTHETIC POPULATION COHORTS                      │
├───────────────────────────────┬────────────┬───────────────────────────┤
│ Cohort Archetype              │ Proportion │ Expected Default Rate     │
├───────────────────────────────┼────────────┼───────────────────────────┤
│ 1. Healthy Volatile           │ 25%        │ Low (4% - 8%)             │
│ 2. Stable Low-Volatility      │ 25%        │ Very Low (2% - 5%)        │
│ 3. Declining / Deteriorating  │ 20%        │ High (25% - 40%)          │
│ 4. Irregular / Fragile        │ 15%        │ Very High (35% - 50%)     │
│ 5. High Obligation Burden     │ 10%        │ Moderate-High (20% - 30%) │
│ 6. Insufficient Data          │ 5%         │ Excluded / Unscored       │
└───────────────────────────────┴────────────┴───────────────────────────┘
```

### 18.2 Time-Series Stochastic Process Specifications
- **Daily Earning Process:** Modeled as an Autoregressive process with Poisson shock jumps:
  $$I_t = \alpha \cdot I_{t-1} + (1 - \alpha) \cdot \mu_{\text{cohort}} + \epsilon_t + J_t$$
  Where $J_t$ represents festive/surge spikes ($J_t > 0$) or acute illness/breakdown shocks ($J_t < 0$).
- **Shock and Recovery Realism:**
  - *Healthy Volatile:* Experiences deep troughs ($I_t < 0.6 \mu$) with rapid recovery ($\le 10\text{ days}$).
  - *Declining:* Structural downward drift ($\mu_t = \mu_0 \cdot (1 - \delta \cdot t)$).
  - *Irregular:* High zero-earning day probability ($P(\text{active}) < 0.40$).
- **Reproducibility:** Generator must accept an explicit integer random seed (`seed = 42`).

---

## 19. Train/Validation/Test Data Contract

To prevent data contamination and overly optimistic validation scores, dataset partitioning must enforce strict identity and temporal constraints.

### 19.1 Partitioning Schema
- **Training Set (70%):** Model training and baseline calibration.
- **Validation Set (15%):** Hyperparameter tuning, feature selection, and threshold calibration.
- **Test Set (15%):** Final out-of-sample evaluation and fairness auditing.

### 19.2 Splitting Strategies
1. **Grouped Cross-Validation (`GroupKFold` / `GroupShuffleSplit`):** All rows associated with a specific `applicant_profile_id` must reside entirely within the train fold or entirely within the test fold. Never split a worker's applications across train and test.
2. **Temporal Out-of-Time (OOT) Holdout:** For longitudinal testing, the final 15% chronological window $[T_{\text{split}}, T_{\text{end}}]$ forms the OOT evaluation set, ensuring models are tested strictly on future time slices.

---

## 20. Privacy and Data Minimization

The dataset strictly complies with the Digital Personal Data Protection (DPDP) Act 2023 and RBI Digital Lending Guidelines.

### 20.1 Ingestion Gate: Prohibited vs. Collected Data

| Data Classification | Fields Ingested | Fields Explicitly Rejected | Regulatory Justification |
| :--- | :--- | :--- | :--- |
| **Financial Signals** | Aggregated periodic earnings, cashflow buffer, existing debt commitments. | Raw bank statements, line-item merchant texts, raw UPI logs, bank credentials. | Minimization: Risk estimation requires cashflow volume and volatility, not itemized lifestyle consumption. |
| **Location & Mobility**| Aggregated active days, hours online, trip counts. | Real-time GPS tracks, location breadcrumbs, home/office coordinates. | Privacy: GPS logs represent invasive surveillance with zero predictive necessity for credit risk. |
| **Device & Contacts** | None. | Contact address book, call logs, SMS text archives, photos. | RBI Compliance: Statutory prohibition against reading applicant contact books or private media. |
| **Identity** | Anonymous UUID tokens (`applicant_profile_id`). | Full names, government ID numbers (Aadhaar/PAN), phone numbers, email addresses. | Pseudonymization: Machine learning pipeline operates strictly on tokenized surrogate keys. |

---

## 21. Leakage Prevention

The five anti-leakage invariants established in Phase 0 are operationalized into concrete data engineering rules:

1. **Temporal Cutoff Enforcement:** $t_{\text{signal}} < t_0$. Any raw event occurring at or after $t_0$ is pruned before feature aggregation.
2. **Forward Target Isolation:** Target $Y$ is evaluated strictly within $(t_0, t_0 + T_{\text{pred}}]$. No target calculation logic may consume signals prior to $t_0$.
3. **Pipeline Encapsulation:** Scaling (e.g. `StandardScaler`), imputing (`SimpleImputer`), and encoding (`OneHotEncoder`) must be fitted strictly on training folds inside scikit-learn `Pipeline` objects.
4. **Group Separation:** Grouped splitting by `applicant_profile_id` prevents worker identity overlap.
5. **No Target Proxies:** Features such as "future repayment count" or "post-cutoff platform earnings" are strictly disallowed.

---

## 22. Open Decisions

The following items are documented as open decisions requiring empirical calibration in future phases:

| Open Decision | Impacted Future Phase | Planned Resolution Mechanism |
| :--- | :--- | :--- |
| **Exact Synthetic Stochastic Parameters** | Phase 2 (Synthetic Data) | Set baseline parameters ($\alpha = 0.7$, jump intensity $\lambda = 0.05$) based on published gig economy labor research. |
| **Living Expense Cost Floors (INR)** | Phase 2 (Synthetic Target) | Model basic non-discretionary costs at ₹12,000 to ₹18,000/month for urban Tier-1 gig workers. |
| **Real Account Aggregator Schema** | Phase 10 (Backend Integration) | Map real Sahamati / Setu Account Aggregator JSON formats to the Aggregated Financial Signal schema. |
| **Optimal Default Decision Threshold** | Phase 8 (Model Validation) | Select decision threshold $\tau$ on validation PR curve to balance default loss vs. financial inclusion. |

---

## 23. Phase 2 Handoff

This data specification is implementation-ready and serves as the direct blueprint for **Phase 2 — Synthetic Data Generation**.

### Phase 2 Handoff Checklist
- [x] Primary ML dataset unit defined (Application assessment at cutoff $t_0$).
- [x] Temporal boundaries ($T_{\text{obs}} = 90\text{d}$, $T_{\text{pred}} = 30-90\text{d}$) explicitly bounded.
- [x] Raw signal schemas and data types defined for all 8 categories.
- [x] Payout time-series schema structured to support volatility and recovery calculation.
- [x] Insufficient evidence deterministic triggers established.
- [x] Missingness semantics codified (zero $\ne$ null $\ne$ unknown).
- [x] Target label ($Y \in \{0, 1\}$) defined under cashflow insolvency principles.
- [x] Synthetic cohort proportions and stochastic requirements detailed.
- [x] Feature lineage table connecting 40 derived features to raw signals complete.

---
*End of ML Data Contract and Dataset Specification.*
