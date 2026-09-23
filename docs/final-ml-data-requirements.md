# PARAKH: Final and Complete ML Data Requirements Document
**Document Version:** 1.1.0 (Frozen Final Specification — Synthetic Parameters Resolved)  
**Author:** Person 3 — ML/Model Developer  
**Target Consumers:** Person 2 (Data Engineering / Synthetic Data Generator) & Person 4 (Backend Integration)  
**Branch:** `ml/credit-risk`  
**Problem Statement:** CX0506 — Credit Score for the Invisible  
**Status:** FROZEN ML DATA CONTRACT (PHASE 2 READY)  

---

## Table of Contents

1. [Model Purpose and Target Definition](#1-model-purpose-and-target-definition)
2. [Complete Input Feature Contract](#2-complete-input-feature-contract)
3. [Raw vs. Derived Features](#3-raw-vs-derived-features)
4. [Backend-to-ML Mapping](#4-backend-to-ml-mapping)
5. [Feature Dependencies, Correlations, and Constraints](#5-feature-dependencies-correlations-and-constraints)
6. [Numerical Feature Distributions (Synthetic Generation Guidance)](#6-numerical-feature-distributions-synthetic-generation-guidance)
7. [Categorical Feature Distributions](#7-categorical-feature-distributions)
8. [Missing Values and Sentinel Policies](#8-missing-values-and-sentinel-policies)
9. [Outliers and Edge Cases](#9-outliers-and-edge-cases)
10. [Target Generation Logic (Cash-Flow Insolvency)](#10-target-generation-logic-cash-flow-insolvency)
11. [Target Class Balance and Imbalance Handling](#11-target-class-balance-and-imbalance-handling)
12. [Train / Validation / Test Splitting Strategy](#12-train--validation--test-splitting-strategy)
13. [Data Leakage Prevention Boundary](#13-data-leakage-prevention-boundary)
14. [Preprocessing and Transformation Pipeline](#14-preprocessing-and-transformation-pipeline)
15. [Model Input Format (Schema Specifications)](#15-model-input-format-schema-specifications)
16. [Model Output Contract](#16-model-output-contract)
17. [Explainability and Factor Attribution Requirements](#17-explainability-and-factor-attribution-requirements)
18. [Model and Artifact Versioning](#18-model-and-artifact-versioning)
19. [Sample Data Records (Minimum 5 Diverse Archetypes)](#19-sample-data-records-minimum-5-diverse-archetypes)
20. [Person 2 Validation Checklist](#20-person-2-validation-checklist)
21. [Final Frozen ML Data Contract](#21-final-frozen-ml-data-contract)

---

## 1. Model Purpose and Target Definition

### 1.1 Predictive Objective
The PARAKH Machine Learning model predicts the **calibrated probability of loan repayment default** over a forward prediction horizon ($T_{\text{pred}} \in [30, 90]\text{ days}$) for gig-economy workers, freelancers, and thin-file micro-borrowers who lack formal credit bureau files.

The central modeling objective is **volatility-aware risk assessment**: the model must distinguish natural, resilient gig-income volatility (cyclical platform demand, seasonal surges, and temporary rests followed by prompt recovery) from structural financial deterioration (chronic downward earning trends, declining active days, and severe debt overhang).

### 1.2 ML Task Formulation
- **Task Type:** Supervised Binary Classification with monotonic probability calibration.
- **Decision Unit:** A single credit evaluation request for an applicant loan application anchored at cutoff timestamp $t_0$.

### 1.3 Exact Target Variable Specification

| Target Property | Value / Definition |
| :--- | :--- |
| **Binary Target Column Name** | `target_default_flag` ($Y$) |
| **Continuous Target Column Name** | `repayment_risk_probability` ($\hat{p} = P(Y = 1 \mid \mathbf{x}_{\text{obs}})$) |
| **Data Type (Binary)** | Integer (`int64` / `int8`) |
| **Data Type (Continuous)** | Float (`float64`) bounded in $[0.0000, 1.0000]$ |
| **Target Generation Mechanism** | **Derived via forward cash-flow insolvency simulation** (see Section 10). It is strictly NOT an arbitrary coin-toss label, nor is it directly copied from any historical observation feature. |
| **Positive Outcome ($Y = 1$)** | **Default / Insolvent / Severely Delinquent:** The borrower fails to service contractual loan installments during the forward prediction horizon $(t_0, t_0 + T_{\text{pred}}]$ due to cash-flow exhaustion, reaching 30+ days past due (DPD) or failing the cash-flow solvency condition. |
| **Negative Outcome ($Y = 0$)** | **Successful Repayment / Non-Default:** The borrower successfully services all contractual debt obligations due within the prediction horizon on or before scheduled dates. |

---

## 2. Complete Input Feature Contract

This table establishes the comprehensive specification for every feature consumed by the model or supplied as applicant context. All features are measured strictly over the historical observation window $[t_0 - 90\text{d}, t_0)$.

### 2.1 Complete Feature Contract Table

| Feature Name | Data Type | Required | Unit | Allowed Range | Allowed Categories | Description | Missing Allowed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `applicant_profile_id` | String | Yes | UUIDv4 | N/A | Valid RFC 4122 UUID | Unique worker identity token | No |
| `application_id` | String | Yes | UUIDv4 | N/A | Valid RFC 4122 UUID | Unique loan application identifier | No |
| `cutoff_timestamp` | String | Yes | ISO-8601 | $t \le \text{Current UTC}$ | Valid UTC timestamp string | Application cutoff point ($t_0$) | No |
| `cohort_archetype` | String | No (Meta) | Categorical | N/A | `Healthy Volatile`, `Stable`, `Declining`, `Irregular`, `High Obligation`, `Insufficient Data` | Ground truth simulation cohort (metadata only; excluded from model training) | No |
| `gig_work_type` | String | Yes | Categorical | N/A | `DELIVERY`, `RIDE_HAILING`, `LOGISTICS`, `HOME_SERVICES`, `FREELANCE_MICRO`, `OTHER` | Primary gig economy operating sector | No (Default `OTHER`) |
| `years_working` | Float | No | Years | $[0.0, 50.0]$ | N/A | Cumulative tenure working in gig economy | Yes |
| `average_working_days` | Integer | No | Days/Mo | $[0, 31]$ | N/A | Self-reported typical active days per month | Yes |
| `requested_loan_amount`| Float | Yes | INR (₹) | $[500.0, 500000.0]$ | N/A | Principal loan financing amount requested | No |
| `loan_tenure_months` | Integer | Yes | Months | $[1, 60]$ | N/A | Contractual loan repayment tenure requested | No |
| `loan_purpose` | String | No | Categorical | N/A | `VEHICLE_MAINTENANCE`, `WORKING_CAPITAL`, `EQUIPMENT_PURCHASE`, `PERSONAL_EMERGENCY`, `OTHER` | Declared purpose of requested financing | Yes |
| `feat_inc_median_90d` | Float | Yes | INR (₹) | $[0.0, 500000.0]$ | N/A | Median weekly net income across trailing 90 days | No |
| `feat_inc_p25_90d` | Float | Yes | INR (₹) | $[0.0, 500000.0]$ | N/A | 25th percentile of weekly net earnings (conservative earning floor) | No |
| `feat_inc_mean_90d` | Float | No | INR (₹) | $[0.0, 500000.0]$ | N/A | Arithmetic mean of weekly net earnings | Yes |
| `feat_inc_trimmed_mean` | Float | No | INR (₹) | $[0.0, 500000.0]$ | N/A | 10% trimmed mean of periodic earnings | Yes |
| `feat_inc_cv_90d` | Float | Yes | Ratio | $[0.0, 5.0]$ | N/A | Coefficient of variation ($\sigma / \mu$) of earnings | No |
| `feat_inc_downside_var` | Float | Yes | $\text{INR}^2$ | $[0.0, 1.0 \times 10^{10}]$| N/A | Semi-variance calculated strictly on weeks below median | No |
| `feat_inc_iqr_ratio` | Float | No | Ratio | $[0.0, 10.0]$ | N/A | Interquartile range normalized by median | Yes |
| `feat_inc_min_max_ratio`| Float | No | Ratio | $[0.0, 1.0]$ | N/A | Minimum weekly payout divided by maximum weekly payout | Yes |
| `feat_trend_slope_90d` | Float | Yes | INR/week | $[-50000.0, 50000.0]$ | N/A | Ordinary Least Squares regression slope across weekly payouts | No |
| `feat_trend_momentum_30_90`| Float| Yes | Ratio | $[0.0, 5.0]$ | N/A | Ratio of mean earnings in last 30d to full 90d mean | No |
| `feat_trend_consec_drops`| Integer| No | Count | $[0, 13]$ | N/A | Maximum streak of consecutive declining weekly payout cycles | Yes |
| `feat_act_active_days_ratio`| Float| Yes | Ratio | $[0.0, 1.0]$ | N/A | Total active working days divided by 90 | No |
| `feat_act_zero_earn_weeks`| Integer| Yes | Count | $[0, 13]$ | N/A | Total calendar weeks with zero recorded earnings | No |
| `feat_act_max_idle_streak`| Integer| No | Days | $[0, 90]$ | N/A | Longest consecutive streak of inactive calendar days | Yes |
| `feat_act_weekend_intensity`| Float| No | Ratio | $[0.0, 1.0]$ | N/A | Weekend active hours divided by total active hours | Yes |
| `feat_rec_bounceback_ratio`| Float| Yes | Ratio | $[0.0, 10.0]$ | N/A | Post-trough peak earnings divided by pre-trough baseline | No |
| `feat_rec_days_to_recover`| Float | Yes | Days | $[0.0, 90.0]$ | N/A | Elapsed calendar days from income trough back to $\ge 80\%$ median | No |
| `feat_rec_max_drawdown` | Float | No | Ratio | $[0.0, 1.0]$ | N/A | Maximum percentage drawdown from rolling peak to subsequent trough | Yes |
| `feat_ten_years_working` | Float | No | Years | $[0.0, 50.0]$ | N/A | Verified tenure in gig economy | Yes |
| `feat_ten_platform_rating`| Float | No | Rating | $[1.0, 5.0]$ | N/A | Composite platform customer rating snapshot at $t_0$ | Yes |
| `feat_ten_trips_completed`| Integer| No | Count | $[0, 100000]$ | N/A | Cumulative trips or deliveries completed in trailing 90d | Yes |
| `feat_ten_cancellation_rate`| Float| No | Ratio | $[0.0, 1.0]$ | N/A | Driver cancellation ratio over trailing 90d | Yes |
| `feat_liq_buffer_to_loan` | Float | Yes | Ratio | $[0.0, 50.0]$ | N/A | Starting liquid buffer divided by requested loan amount | No |
| `feat_liq_burn_months` | Float | Yes | Months | $[0.0, 60.0]$ | N/A | Liquid buffer divided by monthly non-discretionary commitments | No |
| `feat_liq_net_margin` | Float | No | Ratio | $[-2.0, 1.0]$ | N/A | (Gross earnings - expenses) / Gross earnings over 90d | Yes |
| `feat_pay_utility_on_time`| Float | No | Ratio | $[0.0, 1.0]$ | N/A | Fraction of utility bills paid on or before due date | Yes |
| `feat_pay_max_bill_delay` | Integer| No | Days | $[0, 180]$ | N/A | Maximum days past due on trailing utility bills | Yes |
| `feat_pay_repay_reliability`| Float| No | Index | $[0.0, 1.0]$ | N/A | Prior micro-loan or peer advance repayment consistency index | Yes |
| `feat_bur_dti_ratio` | Float | Yes | Ratio | $[0.0, 20.0]$ | N/A | Existing monthly debt divided by median monthly income | No |
| `feat_bur_installment_dti`| Float | Yes | Ratio | $[0.0, 20.0]$ | N/A | Projected loan monthly installment divided by median income | No |
| `feat_bur_total_dti` | Float | Yes | Ratio | $[0.0, 20.0]$ | N/A | (Existing debt + projected installment) / Median monthly income | No |
| `feat_bur_loan_to_income` | Float | No | Ratio | $[0.0, 10.0]$ | N/A | Requested loan principal divided by annualized median earnings | Yes |
| `feat_suf_observed_days` | Integer| Yes | Days | $[0, 90]$ | N/A | Total days elapsed between first recorded activity and $t_0$ | No |
| `feat_suf_payout_count` | Integer| Yes | Count | $[0, 90]$ | N/A | Total verified payout settlement events in window | No |
| `feat_suf_group_count` | Integer| Yes | Count | $[0, 5]$ | N/A | Number of distinct core signal groups populated | No |
| `feat_suf_missing_ratio` | Float | Yes | Ratio | $[0.0, 1.0]$ | N/A | Fraction of optional feature fields missing or null | No |
| `feat_int_vol_x_recovery` | Float | Yes | Index | $[0.0, 450.0]$ | N/A | `feat_inc_cv_90d * feat_rec_days_to_recover` | No |
| `feat_int_vol_x_buffer` | Float | Yes | Index | $[0.0, 50.0]$ | N/A | `feat_inc_cv_90d / (feat_liq_buffer_to_loan + 0.1)` | No |
| `feat_int_trend_x_dti` | Float | Yes | Index | $[-50000.0, 50000.0]$ | N/A | `feat_trend_slope_90d * (1.0 + feat_bur_total_dti)` | No |
| `feat_int_resilience_idx` | Float | Yes | Index | $[0.0, 100.0]$ | N/A | `feat_rec_bounceback_ratio / (feat_inc_cv_90d + 0.05)` | No |

---

## 3. Raw vs. Derived Features

To maintain clear lineage, features are strictly bifurcated into raw application/signal inputs and derived model features.

### 3.1 Raw Ingestion Features
These attributes represent unprocessed signals ingested from the application submission, platform APIs, or user profiles:
- `applicant_profile_id`, `application_id`, `cutoff_timestamp`
- `requested_loan_amount`, `loan_tenure_months`, `loan_purpose`
- `gig_work_type`, `years_working`, `average_working_days`
- Raw time-series payout array: $\mathcal{S}_{\text{payout}} = \{(t_k, \text{gross}_k, \text{net}_k, \text{days}_k)\}_{k=1}^K$
- Raw daily activity flags: $\mathcal{S}_{\text{activity}} = \{(d_j, \text{active}_j, \text{hours}_j)\}_{j=1}^{90}$
- Raw cashflow balance snapshot: $\text{cashflow\_buffer}$ at $t_0$
- Raw monthly obligation: $\text{existing\_obligation}$ at $t_0$
- Raw customer rating: $\text{platform\_rating}$ at $t_0$

### 3.2 Derived Feature Lineage and Formulas

| Derived Feature Name | Mathematical Formula | Input Fields | Data Type | Unit | Valid Range | Example Calculation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `feat_inc_median_90d` | $\text{Median}(\{I_k\}_{k=1}^K)$ | Weekly net payouts $I_k$ | Float | INR | $[0, 500000]$ | Median of $[6500, 7200, 8100, 7000] = 7100.0$ |
| `feat_inc_p25_90d` | $\text{Percentile}_{25}(\{I_k\}_{k=1}^K)$ | Weekly net payouts $I_k$ | Float | INR | $[0, 500000]$ | 25th percentile of payouts $= 6625.0$ |
| `feat_inc_cv_90d` | $\frac{\sigma_{\{I_k\}}}{\mu_{\{I_k\}}}$ | Weekly net payouts $I_k$ | Float | Ratio | $[0, 5]$ | Mean $= 7200$, $\sigma = 1800 \implies \text{CV} = 0.25$ |
| `feat_inc_downside_var` | $\frac{1}{K}\sum_{k=1}^K (I_k - \text{Med})^2 \cdot \mathbb{I}(I_k < \text{Med})$ | $I_k$, $\text{Med}$ | Float | $\text{INR}^2$ | $[0, 10^{10}]$ | Deviations below 7100 squared and averaged $= 360000.0$ |
| `feat_trend_slope_90d` | $\frac{\sum (k - \bar{k})(I_k - \bar{I})}{\sum (k - \bar{k})^2}$ | Sequence $k$, payouts $I_k$ | Float | INR/wk | $[-50000, 50000]$| OLS slope over 12 weeks $= +145.20\text{ INR/week}$ |
| `feat_trend_momentum_30_90`| $\frac{\mu(I_{\text{last 4 wks}})}{\mu(I_{\text{all 12 wks}})}$ | $I_k$ | Float | Ratio | $[0, 5]$ | Recent mean 8000 / Overall mean $7200 = 1.1111$ |
| `feat_act_active_days_ratio`| $\frac{1}{90}\sum_{j=1}^{90} \mathbb{I}(\text{active}_j = \text{True})$ | Daily activity array | Float | Ratio | $[0, 1]$ | 68 active days / 90 total days $= 0.7556$ |
| `feat_act_zero_earn_weeks`| $\sum_{k=1}^K \mathbb{I}(I_k == 0)$ | Weekly net payouts $I_k$ | Integer| Count | $[0, 13]$ | 1 week with zero earnings $= 1$ |
| `feat_rec_days_to_recover`| $t_{\text{recovered}} - t_{\text{trough}}$ where $I(t_{\text{recovered}}) \ge 0.85 \cdot \text{Med}$ | Timestamped payouts | Float | Days | $[0, 90]$ | Drop on day 30, recovered on day 38 $\implies 8.0\text{ days}$ |
| `feat_rec_bounceback_ratio`| $\frac{\max(I_{\text{post-trough}})}{\text{Baseline}}$ | Trough depth, post peak | Float | Ratio | $[0, 10]$ | Post-trough peak 8500 / baseline $7100 = 1.1972$ |
| `feat_liq_buffer_to_loan` | $\frac{\text{cashflow\_buffer}}{\text{requested\_loan\_amount}}$ | Cash buffer, loan amount | Float | Ratio | $[0, 50]$ | Buffer ₹15,000 / Loan ₹20,000 $= 0.75$ |
| `feat_liq_burn_months` | $\frac{\text{cashflow\_buffer}}{\text{existing\_monthly\_debt} + \text{living\_cost}}$ | Cash buffer, debt, living| Float | Months| $[0, 60]$ | Buffer ₹15,000 / Commitments ₹15,000 $= 1.0\text{ month}$ |
| `feat_bur_dti_ratio` | $\frac{\text{existing\_monthly\_debt}}{\text{feat\_inc\_median\_90d} \times 4.33}$ | Existing debt, median | Float | Ratio | $[0, 20]$ | Debt ₹4,000 / Monthly income ₹30,743 $= 0.1301$ |
| `feat_bur_installment_dti`| $\frac{\text{loan\_installment}}{\text{feat\_inc\_median\_90d} \times 4.33}$ | Projected EMI, median | Float | Ratio | $[0, 20]$ | EMI ₹3,600 / Monthly income ₹30,743 $= 0.1171$ |
| `feat_bur_total_dti` | `feat_bur_dti_ratio` + `feat_bur_installment_dti`| DTI ratios | Float | Ratio | $[0, 20]$ | $0.1301 + 0.1171 = 0.2472$ |
| `feat_suf_observed_days` | $t_0 - \min(t_{\text{payout\_start}})$ | Payout start dates | Integer| Days | $[0, 90]$ | First payout 84 days before $t_0 \implies 84$ |
| `feat_suf_payout_count` | $\text{Count}(\mathcal{S}_{\text{payout}})$ | Payout array | Integer| Count | $[0, 90]$ | 12 weekly payouts $= 12$ |
| `feat_suf_missing_ratio` | $\frac{\sum \mathbb{I}(\text{feat}_m \text{ is null})}{\text{Total optional features}}$ | Optional feature fields | Float | Ratio | $[0, 1]$ | 3 nulls out of 18 optional fields $= 0.1667$ |
| `feat_int_vol_x_recovery` | $\text{feat\_inc\_cv\_90d} \times \text{feat\_rec\_days\_to\_recover}$ | CV, recovery days | Float | Index | $[0, 450]$ | $0.35 \times 8.0 = 2.80$ |
| `feat_int_vol_x_buffer` | $\frac{\text{feat\_inc\_cv\_90d}}{\text{feat\_liq\_buffer\_to\_loan} + 0.1}$ | CV, buffer-to-loan | Float | Index | $[0, 50]$ | $0.35 / (0.75 + 0.1) = 0.4118$ |

---

## 4. Backend-to-ML Mapping

Every feature is rigorously verified against actual backend entities in `backend/app/models/` and `backend/app/schemas/`.

| ML Feature Name | Backend Field / Source Entity | Classification | Transformation | Required | Verification Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `applicant_profile_id` | `ApplicantProfile.id` (`applicant_profiles.id`) | DIRECT | Direct string mapping | Yes | Foreign key on `applications.applicant_profile_id` |
| `application_id` | `Application.id` (`applications.id`) | DIRECT | Direct string mapping | Yes | Primary key on `applications` table |
| `cutoff_timestamp` | `Application.created_at` | DIRECT | UTC ISO-8601 string | Yes | Application creation timestamp serves as $t_0$ |
| `requested_loan_amount`| `Application.requested_loan_amount` | DIRECT | Decimal to float | Yes | Mandatory field on `Application` model |
| `loan_tenure_months` | `Application.preferred_repayment_period` | DIRECT | Integer cast | Yes | Mapped to `loan_tenure_months` in `AssessmentInput` |
| `loan_purpose` | `Application.loan_purpose` | DIRECT | String | No | Nullable string on `Application` model |
| `gig_work_type` | `ApplicantProfile.gig_work_type` | DIRECT | String enum | Yes | Mandatory field on `ApplicantProfile` model |
| `years_working` | `ApplicantProfile.years_working` | DIRECT | Numeric to float | No | Nullable field on `ApplicantProfile` model |
| `average_working_days` | `ApplicantProfile.average_working_days` | DIRECT | Integer | No | Nullable field on `ApplicantProfile` model |
| `feat_inc_mean_90d` | `FinancialSignal.average_income` | DIRECT | Numeric to float | No | Pre-aggregated scalar in `financial_signals` table |
| `feat_inc_median_90d` | `FinancialSignal.median_income` | DIRECT | Numeric to float | Yes | Mandatory baseline in `financial_signals` table |
| `feat_inc_cv_90d` | `FinancialSignal.income_volatility` | DIRECT | Numeric to float | Yes | Mapped directly from `FinancialSignal.income_volatility` |
| `feat_trend_slope_90d` | `FinancialSignal.income_trend` | DERIVED | Categorical to slope proxy | Yes | Backend stores string (`GROWING`, `STABLE`, `DECLINING`) |
| `feat_act_active_days_ratio`| `FinancialSignal.active_days` | DERIVED | `active_days / 90.0` | Yes | Backend stores integer count `active_days` |
| `feat_liq_buffer_to_loan` | `FinancialSignal.cashflow_buffer` & `Application.requested_loan_amount` | DERIVED | `cashflow_buffer / requested_loan_amount` | Yes | Both fields exist in backend database |
| `feat_bur_dti_ratio` | `FinancialSignal.existing_obligation` & `FinancialSignal.median_income` | DERIVED | `existing_obligation / (median_income * 4.33)` | Yes | Both fields exist in `financial_signals` table |
| `feat_ten_platform_rating`| `FinancialSignal.platform_rating` | DIRECT | Numeric to float | No | Nullable field on `FinancialSignal` model |
| `feat_pay_repay_reliability`| `FinancialSignal.repayment_reliability` | DIRECT | Numeric to float | No | Nullable field on `FinancialSignal` model |
| `payout_records` series | `FinancialSignal.signal_metadata["payout_records"]` | DERIVED | Extract time series from JSONB | Yes | Stored in JSONB `signal_metadata` in backend |
| `feat_rec_days_to_recover`| None (requires raw time series) | NOT CURRENTLY AVAILABLE | Computed from `signal_metadata["payout_records"]` | Yes | First-class column does not exist in backend DB |
| `feat_rec_bounceback_ratio`| None (requires raw time series) | NOT CURRENTLY AVAILABLE | Computed from `signal_metadata["payout_records"]` | Yes | First-class column does not exist in backend DB |
| `feat_pay_utility_on_time`| `FinancialSignal.payment_regularity` | DIRECT | Numeric to float | No | Backend uses `payment_regularity` as utility/payout proxy |
| `feat_pay_max_bill_delay` | None | NOT CURRENTLY AVAILABLE | Requires external BBPS aggregator | No | Not present in existing backend database |
| `feat_act_weekend_intensity`| None | NOT CURRENTLY AVAILABLE | Requires raw shift telemetry in JSONB | No | Not present in existing backend database |

---

## 5. Feature Dependencies, Correlations, and Constraints

### 5.1 Established Structural Relationships

| Related Features | Expected Direction | Strength | Hard Boundary Constraints |
| :--- | :--- | :--- | :--- |
| **Gross Income ↔ Net Payout** | Positive | Strong ($r > 0.95$) | $\text{net\_payout} \le \text{gross\_earnings}$ (Platform commission must be $\ge 0$). |
| **Active Days ↔ Income** | Positive | Moderate ($r \approx 0.65$) | $\text{active\_days} == 0 \implies \text{income} == 0$. Non-zero income requires $\ge 1$ active day. |
| **Tenure ↔ Rating** | Positive | Weak ($r \approx 0.25$) | New workers ($\le 1\text{ mo}$) may have unpopulated rating (`null`). |
| **Income ↔ Buffer** | Positive | Moderate ($r \approx 0.50$) | High income does not guarantee high buffer if consumption is high. |
| **Obligations ↔ DTI** | Positive | Strong ($r > 0.85$) | $\text{DTI} = \text{Obligations} / \text{Income}$. If income $= 0$, DTI is undefined. |
| **Volatility ↔ Recovery** | Orthogonal / Joint | Variable | High volatility with low recovery days $\rightarrow$ Healthy. High volatility with high recovery days $\rightarrow$ Fragile. |

### 5.2 Impossible Combinations (Validation Rejection Gate)
The synthetic generator and validation gate must guarantee that the following combinations **never appear in valid data**:
1. `gross_earnings < net_payout_amount` (Mathematically impossible platform fee).
2. `feat_act_active_days_ratio == 0.0` but `feat_inc_median_90d > 0.0` (Earning money without working).
3. `feat_inc_cv_90d == 0.0` but `feat_inc_downside_var > 0.0` (Variance without deviation).
4. `feat_rec_bounceback_ratio < 0.0` (Negative monetary bounceback).
5. `feat_suf_payout_count > feat_suf_observed_days` (More than one payout per day on weekly settlement platforms).
6. `payout_period_start > payout_period_end` (Inverted calendar interval).
7. `payout_timestamp >= cutoff_timestamp` (Temporal leakage across $t_0$).

### 5.3 Plausible Edge Cases (To Be Actively Simulated)
- **Acute Shock Episode:** A worker with 2 years of tenure and high average income experiences a 14-day zero-earning trough due to acute illness, followed by complete rebound to baseline within 8 days.
- **Over-leveraged Earner:** High weekly earnings (₹15,000/week), but existing debt obligations exceed ₹50,000/month ($\text{DTI} > 0.80$), resulting in cashflow default despite high gross income.

---

## 6. Numerical Feature Distributions (Synthetic Generation Guidance)

To enable Person 2 to implement the synthetic data generator without making unguided assumptions, this section resolves the stochastic distribution families, baseline parameters, physical bounds, and cohort-specific modifiers for **all numerical model features** (Decision **D1** resolved).

### 6.1 Generation Methodology
Person 2's synthetic generator implements a **causal bottom-up generator**:
1. First, a daily time-series sequence of gross earnings, platform commission deductions, and active working hours is simulated over the 90-day observation window $[t_0 - 90\text{d}, t_0)$.
2. Secondary derived features (`feat_inc_mean_90d`, `feat_inc_trimmed_mean`, `feat_inc_iqr_ratio`, `feat_inc_min_max_ratio`, `feat_trend_consec_drops`, `feat_act_max_idle_streak`, `feat_act_weekend_intensity`, `feat_rec_max_drawdown`, `feat_liq_net_margin`, `feat_bur_loan_to_income`, and all interaction terms) are calculated deterministically from the generated time series and balance sheets using their exact formulas from Section 3.2.
3. For standalone profile, tenure, platform, and payment discipline features that do not originate from daily platform payouts, the parametric distributions specified below must be sampled directly.

### 6.2 Complete Numerical Feature Distribution Specifications (D1 Resolved)

| Feature Name | Distribution | Baseline Parameters | Hard Min / Max | Typical Range | Zero Allowed? | Negative Allowed? | Cohort Adjustments & Generation Notes | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `requested_loan_amount` | Log-normal | $\mu = \ln(20000)$, $\sigma = 0.55$ | $[500, 500000]$ | ₹5,000 to ₹50,000 | No | No | High Obligation cohort requests higher amounts ($\mu = \ln(35000)$). Round to nearest ₹500. | Reflects urban micro-lending financing demand for vehicle repairs and working capital. |
| `loan_tenure_months` | Discrete Categorical | Values: $[1, 2, 3, 4, 6, 12]$ with probabilities $[0.10, 0.20, 0.35, 0.15, 0.15, 0.05]$ | $[1, 60]$ | $2\text{ to }6\text{ months}$ | No | No | Fixed discrete product tenures common in alternative digital credit. | Micro-credit tenures in gig financing are typically short (1 to 6 months). |
| `years_working` | Gamma | Shape $k = 2.0$, Scale $\theta = 1.25$ | $[0.0, 50.0]$ | $0.5\text{ to }6.0\text{ years}$ | Yes | No | Stable cohort shifted by $+1.0\text{ yr}$; Insufficient Data cohort sampled $\le 0.1\text{ yr}$. | Heavy right tail with mode around 1.5 to 2.5 years of gig platform tenure. |
| `average_working_days` | Truncated Normal | $\mu = 24.0$, $\sigma = 4.0$, clipped $[0, 31]$ | $[0, 31]$ | $20\text{ to }28\text{ days/mo}$ | Yes | No | Irregular cohort sampled from $\mu = 14.0, \sigma = 5.0$. Discrete integer days. | Self-reported monthly active work commitment. |
| `feat_inc_median_90d` | Log-normal | $\mu = \ln(7000)$, $\sigma = 0.40$ | $[0, 500000]$ | ₹3,500 to ₹18,000/wk | Yes | No | Healthy Volatile: $\mu = \ln(8000)$; Declining: $\mu = \ln(4500)$; Irregular: $\mu = \ln(3800)$. | Positively skewed earnings distribution typical of piece-rate gig labor. |
| `feat_inc_p25_90d` | Deterministic Derived | $P_{25}(\{I_k\})$ from weekly payouts | $[0, 500000]$ | ₹2,500 to ₹15,000/wk | Yes | No | Must satisfy $\text{feat\_inc\_p25\_90d} \le \text{feat\_inc\_median\_90d}$. | 25th percentile conservative earning baseline floor. |
| `feat_inc_mean_90d` | Deterministic Derived | $\text{Mean}(\{I_k\})$ from weekly payouts | $[0, 500000]$ | ₹3,500 to ₹20,000/wk | Yes | No | In Healthy Volatile, mean exceeds median due to positive surge spikes. | Standard arithmetic earning benchmark. |
| `feat_inc_trimmed_mean` | Deterministic Derived | 10% Trimmed Mean from payouts | $[0, 500000]$ | ₹3,500 to ₹19,000/wk | Yes | No | Filters single-week holiday surge outliers. | Robust alternative mean estimator. |
| `feat_inc_cv_90d` | Gamma | Shape $k = 3.0$, Scale $\theta = 0.08$ | $[0.0, 5.0]$ | $0.10\text{ to }0.75$ | Yes | No | Healthy Volatile: $k = 4.5, \theta = 0.08$ (CV $\approx 0.35$); Stable: $k = 2.0, \theta = 0.05$ (CV $\approx 0.10$). | Captures relative earning dispersion around baseline. |
| `feat_inc_downside_var` | Deterministic Derived | Semi-variance below median | $[0.0, 1.0 \times 10^{10}]$ | $5 \times 10^4\text{ to }2 \times 10^6$ | Yes | No | Low in Stable cohort; moderate in Healthy Volatile; high in Irregular. | Focuses exclusively on downside cash-flow shortfall risks. |
| `feat_inc_iqr_ratio` | Deterministic Derived | $(P_{75} - P_{25}) / \text{Median}$ | $[0.0, 10.0]$ | $0.15\text{ to }0.80$ | Yes | No | Set to 0 if median is 0. Bounded dispersion metric. | Robust interquartile dispersion indicator. |
| `feat_inc_min_max_ratio`| Deterministic Derived | $\min(I_k) / \max(I_k)$ | $[0.0, 1.0]$ | $0.20\text{ to }0.85$ | Yes | No | Near 1.0 for Stable; $< 0.30$ for Healthy Volatile and Irregular. | Extreme earnings spread ratio. |
| `feat_trend_slope_90d` | Normal | $\mu = 0.0$, $\sigma = 150.0$, clipped $[-1000, 1000]$ | $[-50000, 50000]$ | $-300\text{ to }+300\text{ INR/wk}$ | Yes | Yes | Declining cohort: $\mu = -220.0, \sigma = 60.0$; Healthy Volatile: $\mu = +75.0, \sigma = 80.0$. | Linear trajectory slope across weekly payout cycles. |
| `feat_trend_momentum_30_90`| Deterministic Derived | $\text{Mean}(I_{\text{last 4 wks}}) / \text{Mean}(I_{\text{all 12 wks}})$| $[0.0, 5.0]$ | $0.65\text{ to }1.40$ | Yes | No | $< 0.80$ indicates recent decay; $> 1.10$ indicates recent expansion. | Rolling momentum ratio. |
| `feat_trend_consec_drops`| Deterministic Derived | Max consecutive weekly earnings drops | $[0, 13]$ | $1\text{ to }5\text{ cycles}$ | Yes | No | High in Declining cohort ($3\text{--}6$); low in Stable cohort ($0\text{--}2$). | Stress indicator for chronic earnings decline. |
| `feat_act_active_days_ratio`| Beta | $\alpha = 5.0$, $\beta = 2.0$ | $[0.0, 1.0]$ | $0.50\text{ to }0.95$ | Yes | No | Irregular: $\alpha = 2.0, \beta = 3.5$ (ratio $\approx 0.35$); Stable: $\alpha = 8.0, \beta = 1.5$ (ratio $\approx 0.85$). | Engagement continuity across 90 calendar days. |
| `feat_act_zero_earn_weeks`| Deterministic Derived | Count of weeks with ₹0 income | $[0, 13]$ | $0\text{ to }3\text{ weeks}$ | Yes | No | 0 for Stable; $\ge 2$ for Irregular; 0 for Healthy Volatile (active workers). | Structural idle weeks indicator. |
| `feat_act_max_idle_streak`| Deterministic Derived | Max consecutive inactive calendar days | $[0, 90]$ | $1\text{ to }14\text{ days}$ | Yes | No | Stable $\le 3\text{ days}$; Irregular $10\text{--}25\text{ days}$. | Prolonged absence or illness marker. |
| `feat_act_weekend_intensity`| Beta | $\alpha = 3.0$, $\beta = 3.0$ | $[0.0, 1.0]$ | $0.25\text{ to }0.65$ | Yes | No | High in Delivery/Ride-hailing workers surging on Friday-Sunday shifts. | Weekend work concentration. |
| `feat_rec_bounceback_ratio`| Truncated Normal | $\mu = 1.15$, $\sigma = 0.25$, clipped $[0.2, 3.0]$ | $[0.0, 10.0]$ | $0.80\text{ to }1.50$ | Yes | No | Healthy Volatile: $\mu = 1.30, \sigma = 0.20$; Declining: $\mu = 0.65, \sigma = 0.15$. | Quantifies earnings elasticity post-trough. |
| `feat_rec_days_to_recover`| Exponential | Scale $\lambda = 7.0\text{ days}$, clipped $[0, 90]$ | $[0.0, 90.0]$ | $3\text{ to }15\text{ days}$ | Yes | No | Healthy Volatile: $\lambda = 5.0\text{ days}$; Declining: $\lambda = 25.0\text{ days}$ (or capped at 90). | Speed of earnings rebound following income dips. |
| `feat_rec_max_drawdown` | Beta | $\alpha = 2.5$, $\beta = 4.0$ | $[0.0, 1.0]$ | $0.15\text{ to }0.65$ | Yes | No | Higher in Healthy Volatile and Irregular; minimal in Stable ($< 0.25$). | Maximum percentage earnings trough from peak. |
| `feat_ten_years_working` | Identical to profile | Sampled from `years_working` | $[0.0, 50.0]$ | $0.5\text{ to }6.0\text{ years}$ | Yes | No | 10% randomly injected missing values (`null`). | Tenure in gig economy. |
| `feat_ten_platform_rating`| Beta (shifted) | Shifted to $[1.0, 5.0]$: $\alpha = 8.0, \beta = 1.5$ | $[1.0, 5.0]$ | $4.20\text{ to }4.95$ | No | No | Declining cohort has lower ratings ($\alpha = 4.0, \beta = 2.0$, mean $\approx 4.10$). 15% nulls. | Composite platform customer feedback rating. |
| `feat_ten_trips_completed`| Poisson / NegBin | Poisson with $\lambda = \text{active\_days} \times 12$ | $[0, 100000]$ | $300\text{ to }1,500\text{ trips}$ | Yes | No | Correlated with active days and work type (Delivery > Logistics). | Cumulative order fulfillments. |
| `feat_ten_cancellation_rate`| Beta | $\alpha = 1.5$, $\beta = 20.0$ | $[0.0, 1.0]$ | $0.02\text{ to }0.15$ | Yes | No | Low across professional drivers; elevated in Irregular/Declining ($> 0.15$). 20% nulls. | Driver cancellation discipline. |
| `feat_liq_buffer_to_loan` | Log-normal | $\mu = \ln(0.65)$, $\sigma = 0.50$ | $[0.0, 50.0]$ | $0.20\text{ to }2.50$ | Yes | No | Healthy Volatile: $\mu = \ln(0.90)$; High Obligation: $\mu = \ln(0.25)$. | Liquid cash reserves relative to requested principal. |
| `feat_liq_burn_months` | Deterministic Derived | `cashflow_buffer / monthly_commitments` | $[0.0, 60.0]$ | $0.3\text{ to }2.5\text{ months}$ | Yes | No | Monthly commitments = existing monthly debt + living cost floor. | Reserve buffer coverage duration. |
| `feat_liq_net_margin` | Normal | $\mu = 0.25$, $\sigma = 0.15$, clipped $[-1.0, 0.70]$| $[-2.0, 1.0]$ | $0.05\text{ to }0.45$ | Yes | Yes | Can be negative during shock months. 25% nulls. | Estimated net cash flow margin. |
| `feat_pay_utility_on_time`| Beta | $\alpha = 8.0$, $\beta = 2.0$ | $[0.0, 1.0]$ | $0.60\text{ to }1.00$ | Yes | No | Low in Irregular cohort ($\alpha = 3.0, \beta = 3.0$); 35% nulls (unconsented). | On-time utility bill payment discipline. |
| `feat_pay_max_bill_delay` | Poisson | $\lambda = 3.0\text{ days}$ | $[0, 180]$ | $0\text{ to }15\text{ days}$ | Yes | No | Zero for prime utility payers; $> 30$ for stressed borrowers. 35% nulls. | Severity of utility payment delinquency. |
| `feat_pay_repay_reliability`| Beta | $\alpha = 9.0$, $\beta = 1.5$ | $[0.0, 1.0]$ | $0.70\text{ to }1.00$ | Yes | No | Micro-loan / peer advance repayment index. 40% nulls. | Historical alternative credit repayment track record. |
| `feat_bur_dti_ratio` | Gamma | Shape $k = 2.2$, Scale $\theta = 0.10$ | $[0.0, 20.0]$ | $0.05\text{ to }0.50$ | Yes | No | High Obligation cohort sampled from $k = 5.0, \theta = 0.12$ (DTI $\approx 0.60$). | Existing debt to median monthly income. |
| `feat_bur_installment_dti`| Deterministic Derived | Projected loan EMI / Monthly income | $[0.0, 20.0]$ | $0.04\text{ to }0.25$ | Yes | No | EMI calculated from loan amount and tenure at standard interest. | Additional debt service burden from requested loan. |
| `feat_bur_total_dti` | Deterministic Derived | `feat_bur_dti_ratio + feat_bur_installment_dti`| $[0.0, 20.0]$ | $0.10\text{ to }0.75$ | Yes | No | High Obligation cohort exceeds 0.60. Critical solvency factor. | Combined borrower debt service burden. |
| `feat_bur_loan_to_income` | Deterministic Derived | Principal / (Weekly median * 52) | $[0.0, 10.0]$ | $0.03\text{ to }0.30$ | Yes | No | Principal leverage relative to annualized income. | Overall leverage ratio. |
| `feat_suf_observed_days` | Uniform / Discrete | 90 days for complete history | $[0, 90]$ | $80\text{ to }90\text{ days}$ | No | No | Insufficient Data cohort sampled uniformly from $[5, 25]$ days. | Historical telemetry span available. |
| `feat_suf_payout_count` | Discrete Count | Payout count in observation window | $[0, 90]$ | $11\text{ to }13\text{ payouts}$ | No | No | Insufficient Data cohort sampled from $[1, 3]$ payouts. | Completed settlement cycles available. |
| `feat_suf_group_count` | Discrete Count | Number of active core signal groups | $[0, 5]$ | $3\text{ to }5\text{ groups}$ | No | No | Insufficient Data cohort has $\le 1$ group. | Core signal diversity indicator. |
| `feat_suf_missing_ratio` | Deterministic Derived | Null optional features / 21 | $[0.0, 1.0]$ | $0.05\text{ to }0.30$ | Yes | No | Elevated when utility or platform ratings are unconsented. | Data completeness index. |
| `feat_int_vol_x_recovery` | Deterministic Derived | `feat_inc_cv_90d * feat_rec_days_to_recover` | $[0.0, 450.0]$ | $0.5\text{ to }8.0$ | Yes | No | Low in Healthy Volatile (moderate CV $\times$ small recovery days); high in Fragile. | Core volatility-aware interaction term. |
| `feat_int_vol_x_buffer` | Deterministic Derived | `feat_inc_cv_90d / (feat_liq_buffer_to_loan + 0.1)`| $[0.0, 50.0]$ | $0.10\text{ to }2.50$ | Yes | No | High volatility insulated by high buffer results in low risk index. | Buffer-adjusted earnings volatility. |
| `feat_int_trend_x_dti` | Deterministic Derived | `feat_trend_slope_90d * (1.0 + feat_bur_total_dti)`| $[-50000, 50000]$ | $-350\text{ to }+350$ | Yes | Yes | Compound stress: negative slope amplified by high leverage. | Compound trajectory and leverage interaction. |
| `feat_int_resilience_idx` | Deterministic Derived | `feat_rec_bounceback_ratio / (feat_inc_cv_90d + 0.05)`| $[0.0, 100.0]$ | $1.5\text{ to }8.0$ | Yes | No | High bounceback with moderate variance indicates superior earning resilience. | Composite earning resilience index. |

---

## 7. Categorical Feature Distributions

Synthetic population sampling must adhere to the proportions defined below. These proportions reflect **prototype experimental cohorts**, not census demographics.

### 7.1 Categorical Specifications

| Categorical Feature | Allowed Categories | Synthetic Generator Proportion | Category Meaning |
| :--- | :--- | :--- | :--- |
| `cohort_archetype` | `Healthy Volatile` | 25.0% | High earnings variance, rapid recovery from dips, adequate cash buffer. |
| | `Stable` | 25.0% | Consistent weekly income, low variance, steady active days. |
| | `Declining` | 20.0% | Negative earnings trend, deteriorating ratings, eroding buffer. |
| | `Irregular` | 15.0% | Sparse active days, erratic payout intervals, low buffer. |
| | `High Obligation` | 10.0% | Healthy earnings, but debt-to-income exceeds 50%. |
| | `Insufficient Data` | 5.0% | Observation history $< 30\text{ days}$ or completed payouts $< 4$. |
| `gig_work_type` | `DELIVERY` | 40.0% | Food, grocery, and e-commerce parcel courier. |
| | `RIDE_HAILING` | 35.0% | Two-wheeler taxi, auto-rickshaw, or four-wheeler cab driver. |
| | `LOGISTICS` | 12.0% | Intra-city light commercial goods freight. |
| | `HOME_SERVICES` | 8.0% | Domestic cleaning, repairs, electrical, salon services. |
| | `FREELANCE_MICRO` | 3.0% | Digital data entry, micro-tasks, transcription. |
| | `OTHER` | 2.0% | Unclassified informal gig work. |
| `income_trend` | `GROWING` | 25.0% | Positive earnings momentum ($> +5\%$ per month). |
| | `STABLE` | 50.0% | Fluctuation within $[-5\%, +5\%]$ per month. |
| | `DECLINING` | 25.0% | Structural downward drift ($< -5\%$ per month). |
| `loan_purpose` | `VEHICLE_MAINTENANCE` | 45.0% | Tyres, battery, brake overhaul, insurance renewal. |
| | `WORKING_CAPITAL` | 30.0% | Fuel, platform onboarding deposit, inventory. |
| | `EQUIPMENT_PURCHASE` | 15.0% | Smartphone upgrade, delivery bag, helmet. |
| | `PERSONAL_EMERGENCY` | 7.0% | Family healthcare, school fees. |
| | `OTHER` | 3.0% | Miscellaneous declared commercial purpose. |

---

## 8. Missing Values and Sentinel Policies

### 8.1 Distinct Semantic Missing States
1. **True Observed Zero (`0.00`):** Valid numerical quantity (e.g. ₹0 debt). **Never impute or convert to null.**
2. **Missing Value (`null` / `None`):** Unpopulated field in an optional signal. Imputed during pipeline preprocessing with an explicit indicator `_was_missing`.
3. **Missing Period (`MISSING_PERIOD`):** Telemetry outage. Interpolated if gap $\le 1$ week; otherwise tagged as unverified gap.
4. **Unconsented Signal Group:** Entire optional group absent (e.g., utility). Treated as neutral weight; does NOT invalidate assessment if $\ge 2$ core groups exist.
5. **Not Applicable (`N/A`):** Domain-inapplicable attribute (e.g., cancellation rate for freelancers).
6. **Invalid Value:** Domain violation (e.g., negative earnings). Rejected immediately at validation gate.

### 8.2 Missingness Policy Table

| Feature Name | Missing Allowed | Recommended Missing % in Synthetic Data | Null Representation | Pipeline Imputation Handling |
| :--- | :--- | :--- | :--- | :--- |
| `feat_inc_median_90d` | No | 0.0% | None | Mandatory; missing triggers `INSUFFICIENT` |
| `feat_inc_p25_90d` | No | 0.0% | None | Mandatory; missing triggers `INSUFFICIENT` |
| `feat_inc_cv_90d` | No | 0.0% | None | Mandatory; missing triggers `INSUFFICIENT` |
| `feat_trend_slope_90d` | No | 0.0% | None | Mandatory; missing triggers `INSUFFICIENT` |
| `feat_act_active_days_ratio`| No | 0.0% | None | Mandatory; missing triggers `INSUFFICIENT` |
| `feat_ten_years_working` | Yes | 10.0% | `NaN` / `null` | Median imputation with `feat_ten_years_working_was_missing = 1` |
| `feat_ten_platform_rating`| Yes | 15.0% | `NaN` / `null` | Impute neutral 4.50 with `rating_was_missing = 1` |
| `feat_ten_cancellation_rate`| Yes | 20.0% | `NaN` / `null` | Median imputation with indicator |
| `feat_pay_utility_on_time`| Yes | 35.0% | `NaN` / `null` | Impute neutral 0.50 with `utility_was_missing = 1` |
| `feat_pay_max_bill_delay` | Yes | 35.0% | `NaN` / `null` | Impute 0 with indicator |
| `feat_pay_repay_reliability`| Yes | 40.0% | `NaN` / `null` | Impute neutral 0.50 with indicator |
| `feat_liq_net_margin` | Yes | 25.0% | `NaN` / `null` | Median imputation with indicator |

---

## 9. Outliers and Edge Cases

### 9.1 Boundary Definitions

| Outlier / Edge Case Type | Operational Boundary | Expected Synthetic Frequency | Simulation and Preprocessing Policy |
| :--- | :--- | :--- | :--- |
| **Very Low Income** | Median $< ₹3,000/\text{week}$ ($< ₹12,000/\text{mo}$) | $\approx 8.0\%$ of dataset | Valid informal earner; evaluate solvency against micro-loan size. |
| **Very High Income** | Median $> ₹25,000/\text{week}$ ($> ₹100,000/\text{mo}$) | $\approx 2.0\%$ of dataset | Top-tier multi-platform worker; log-transform to prevent gradient explosion. |
| **Very Low Activity** | $< 10$ active working days in 90 days | $\approx 5.0\%$ of dataset | Flags severe under-employment; triggers high default risk unless buffer is huge. |
| **Very High Activity** | $> 84$ active working days in 90 days ($> 93\%$) | $\approx 3.0\%$ of dataset | High engagement; check for sustainability. |
| **New Entrant Worker** | Tenure $< 30$ days | $\approx 5.0\%$ of dataset | **Triggers `INSUFFICIENT_EVIDENCE` short-circuit.** Unscored. |
| **Established Veteran** | Tenure $> 5$ years ($> 60\text{ months}$) | $\approx 5.0\%$ of dataset | Strong tenure signal; cap at 10 years to prevent leverage. |
| **Extreme Leverage** | $\text{Total DTI} > 1.0$ (Debt exceeds 100% income) | $\approx 4.0\%$ of dataset | Severe over-indebtedness; deterministic default trigger in forward simulation. |
| **Zero Cash Reserve** | $\text{cashflow\_buffer} == 0.00\text{ INR}$ | $\approx 15.0\%$ of dataset | Valid numerical zero; extreme vulnerability to temporary shock. |

---

## 10. Target Generation Logic (Cash-Flow Insolvency)

This section establishes the frozen forward-looking accounting simulator that Person 2 must implement to produce `target_default_flag`. All target-generation decisions (**D2**, **D3**, and **D4**) are fully resolved.

### 10.1 Causal Forward Timeline
The target is generated **strictly from events in the forward prediction window** $(t_0, t_0 + T_{\text{pred}}]$:

```
t_0 (Application Cutoff)                      t_0 + T_pred (Close of Outcome Window)
 |                                                  |
 ▼                                                  ▼
[ Day 1 ──► Day 2 ──► Day 3 ───────────────► Day T_pred ]
  • Starting Cashflow Buffer: B_0 = cashflow_buffer(t_0)
  • Realized Daily Income: I_t ~ Forward Earnings Simulator
  • Realized Living Cost: E_t ~ Non-discretionary Living Expense Simulator
  • Contractual Debt Due: O_t ~ Existing Debt EMI + Requested Loan EMI
  • Stochastic Shock Event: S_t ~ Poisson Shock Generator (e.g. Illness / Repair)
```

### 10.2 Mathematical Cash-Flow Insolvency Condition
At each daily simulation step $t \in \{1, 2, \dots, T_{\text{pred}}\}$, the borrower's liquid liquidity buffer $B_t$ updates via:
$$B_t = B_{t-1} + I_t - E_t - O_t - S_t$$

Where:
- $B_0$: Verified starting cashflow buffer at cutoff timestamp $t_0$.
- $I_t$: Daily earnings realized on day $t$.
- $E_t$: Daily non-discretionary living expenses on day $t$.
- $O_t$: Contractual debt obligations due on day $t$ (existing monthly obligations amortized daily + requested loan installment).
- $S_t$: Exogenous negative shock expenditure on day $t$ (drawn from Poisson-Pareto shock process).

**Insolvency Rule:**
A default event ($Y = 1$) is triggered if the cumulative liquidity buffer remains negative for consecutive days exceeding the grace period:
$$Y = 1 \iff \min_{t} B_t < 0 \quad \text{and} \quad \text{Days}(B_t < 0) \ge \text{Grace Period}$$

### 10.3 Simulator Parameter Status (D2, D3, D4 Resolved)

| Simulation Parameter | Final Value / Specification | Parameter Status | Decision ID | Technical Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Prediction Horizon ($T_{\text{pred}}$)** | $30\text{ to }90\text{ days}$ (matching loan tenure) | **FROZEN** | Core Contract | Aligned with micro-financing tenures common in alternative gig lending. |
| **Insolvency Grace Period** | **7 consecutive days** of negative liquidity | **FROZEN** | Core Contract | A single-day dip below ₹0 is absorbed via informal overdraft; 7 consecutive days indicates insolvency. |
| **Exogenous Shock Frequency ($\lambda$)** | **Monthly $\lambda = 0.05$ shocks/mo** ($\lambda_{\text{daily}} = 0.05 / 30 = 0.001667\text{ shocks/day}$) | **FROZEN** | **D2** | On average, 5% to 15% of borrowers experience an acute shock during the prediction window, preventing artificial default inflation. |
| **Daily Shock Probability** | Bernoulli: $P(\text{Shock on day } t) = 1 - e^{-\lambda_{\text{daily}}} \approx 0.001667$ | **FROZEN** | **D2** | At most one shock can occur on any given simulation day. Events are conditionally independent. |
| **Cohort Shock Modifiers** | Irregular $\lambda \times 1.25$; Declining $\lambda \times 1.10$; Stable $\lambda \times 0.80$; Others $\lambda \times 1.00$ | **FROZEN** | **D2** | Reflects differential equipment maintenance and health risks across operational profiles. |
| **Pareto Shock Scale ($s_m$)** | **₹3,000 INR** (Minimum shock expenditure threshold) | **FROZEN** | **D3** | Represents minimum realistic financial shock: minor two-wheeler repair or acute clinic consultation. |
| **Pareto Shock Shape ($\alpha$)** | **$\alpha = 2.20$** (Mean shock magnitude $\approx ₹5,500$ INR) | **FROZEN** | **D3** | Shape $\alpha > 2.0$ guarantees finite mean and variance ($\mu = \frac{\alpha s_m}{\alpha - 1} = \frac{2.2 \times 3000}{1.2} = ₹5,500$). |
| **Hard Shock Maximum** | **₹25,000 INR** (Clipped upper bound) | **FROZEN** | **D3** | Capped to prevent absurd multi-lakh outliers from distorting micro-lending loss distributions. |
| **Base Living Cost Floor** | **₹14,000 INR / month** ($E_t = ₹466.67\text{ INR/day}$) | **FROZEN** | **D4** | Center of provisional ₹12,000–₹18,000 range; represents basic urban subsistence in Indian metros. |
| **Applicant Living Cost Variance**| Log-normal around ₹14,000 with $\sigma = 0.10$ | **FROZEN** | **D4** | Ensures realistic variance in living expenses across households while preserving the subsistence floor. |
| **Living Cost Hard Bounds** | Hard Floor: ₹12,000/mo ($₹400/\text{day}$); Hard Cap: ₹22,000/mo ($₹733.33/\text{day}$) | **FROZEN** | **D4** | Bounds prevent unlivable zero living costs or excessive luxury expenditure in the simulator. |

### 10.4 Absolute Anti-Leakage Isolation Rule
> [!CAUTION]
> The daily simulation variables ($I_t$, $E_t$, $O_t$, $S_t$, $B_t$ for $t > 0$) exist strictly inside the target generator. They must **NEVER appear in the model feature matrix $\mathbf{x}_{\text{obs}}$**. Model features may only consume data occurring strictly before $t_0$.

---

## 11. Target Class Balance and Imbalance Handling

### 11.1 Expected Target Class Proportions
- **Target Positive Rate ($Y = 1$ Default):** **$10.0\%\text{ to }15.0\%$ overall default rate** across the aggregate synthetic dataset.
- **Target Negative Rate ($Y = 0$ Repaid):** **$85.0\%\text{ to }90.0\%$ overall successful repayment rate**.

### 11.2 Cohort vs. Target Distribution Distinction
Cohort proportions must not be confused with target class distribution:
- `Healthy Volatile` (25% of dataset): Expected default rate $\approx 4\%\text{--}8\%$.
- `Stable` (25% of dataset): Expected default rate $\approx 2\%\text{--}5\%$.
- `Declining` (20% of dataset): Expected default rate $\approx 25\%\text{--}40\%$.
- `Irregular` (15% of dataset): Expected default rate $\approx 35\%\text{--}50\%$.
- `High Obligation` (10% of dataset): Expected default rate $\approx 20\%\text{--}30\%$.
- `Insufficient Data` (5% of dataset): Excluded from training ($Y = \text{null}$).

Combining these cohort default rates yields the aggregate $\approx 12.5\%$ positive class prevalence.

### 11.3 Imbalance Handling Protocol
- **No Raw Resampling:** Person 2 must generate natural imbalanced datasets. Do NOT apply SMOTE or random oversampling to the generated dataset files.
- **Algorithm-Level Handling:** Class imbalance is handled during Phase 5/6 model training via sample weighting (`scale_pos_weight` in LightGBM, `class_weight='balanced'` in Logistic Regression).
- **Evaluation Independence:** Primary metrics are PR-AUC and ROC-AUC, which are robust to class imbalance.

---

## 12. Train / Validation / Test Splitting Strategy

### 12.1 Dataset Partitioning Ratios
- **Training Set:** **70%** (Model parameter fitting and baseline calibration).
- **Validation Set:** **15%** (Hyperparameter optimization and threshold calibration).
- **Test Set:** **15%** (Final out-of-sample evaluation and fairness auditing).

### 12.2 Frozen Dataset Size Specification (D5 Resolved)

| Dataset Size Dimension | Frozen Specification | Parameter Status | Decision ID | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Default Total Applications** | **12,000 applications** | **FROZEN** | **D5** | Center of documented 10,000–20,000 range; provides high statistical power without excessive training latency. |
| **Default Unique Applicants** | **10,000 unique workers** | **FROZEN** | **D5** | Generates $\approx 2,000$ repeated applications over time to rigorously test grouped cross-validation. |
| **Scored Applications** | **11,400 applications** (95% of total) | **FROZEN** | **D5** | 600 applications (5%) belong to Insufficient Data cohort and remain unscored ($Y = \text{null}$). |
| **Expected Default Count** | **$\approx 1,425$ defaults** ($Y = 1$, range $1,140\text{--}1,710$) | **FROZEN** | **D5** | Yields $\approx 12.5\%$ default rate, sufficient to evaluate PR-AUC and minority class recall reliably. |
| **Training Partition (70%)** | **8,400 applications** ($\approx 7,000$ unique applicants) | **FROZEN** | **D5** | Robust training sample for baseline linear models and gradient boosting trees. |
| **Validation Partition (15%)**| **1,800 applications** ($\approx 1,500$ unique applicants) | **FROZEN** | **D5** | Uncontaminated validation split for threshold tuning and calibration. |
| **Test Partition (15%)** | **1,800 applications** ($\approx 1,500$ unique applicants) | **FROZEN** | **D5** | Final out-of-sample benchmarking and subgroup fairness auditing. |
| **Configurable Override** | Supported via generator CLI/config (`--n_samples`) | **FROZEN** | **D5** | Person 2's generator must accept an optional override flag while defaulting to 12,000 rows. |

### 12.3 Grouped Splitting Protocol
- **Hard Rule:** All rows sharing the same `applicant_profile_id` must reside entirely within the same partition (`GroupKFold` or `GroupShuffleSplit`).
- **Splitting Ownership:** Person 2 delivers **one single unified dataset file** (`synthetic_credit_applications.parquet`). Person 3 executes the grouped splitting inside the ML training pipeline.

---

## 13. Data Leakage Prevention Boundary

The five anti-leakage invariants are frozen:

```
HISTORICAL OBSERVATION WINDOW [t_0 - 90d, t_0)          CUTOFF (t_0)        OUTCOME WINDOW (t_0, t_0 + T_pred]
┌──────────────────────────────────────────────┐              │              ┌────────────────────────────────┐
│ PREDICTIVE FEATURES (x_obs)                  │              │              │ TARGET OUTCOME (Y)             │
│ - Historical payouts                         │              │              │ - Forward realized earnings    │
│ - Historical active days                     │              │              │ - Forward actual expenses      │
│ - Trailing buffer snapshot at t_0            │              │              │ - Forward debt settlements     │
│ - Stated loan request terms                  │              │              │ - Realized default event       │
└──────────────────────────────────────────────┘              │              └────────────────────────────────┘
                                                ◄─────────────┴─────────────►
                                                STRICT TEMPORAL ISOLATION GATE
```

1. **Temporal Cutoff:** Any event with timestamp $t \ge t_0$ is pruned from feature engineering.
2. **Outcome Isolation:** Actual loan repayment performance, post-$t_0$ platform earnings, and forward defaults are strictly prohibited from predictor construction.
3. **No Target Proxies:** Features such as "future repayment count" or "post-cutoff active days" are disallowed.
4. **Fitting Isolation:** Scalers, imputers, and encoders are fitted strictly on training fold partitions.

---

## 14. Preprocessing and Transformation Pipeline

### 14.1 Transformation Specifications

| Feature Group | Features | Transformation | Pipeline Component | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Skewed Monetary Values** | `feat_inc_median_90d`, `requested_loan_amount`, `cashflow_buffer` | $\log(1 + x)$ | `FunctionTransformer` | Compresses extreme right-skewed currency tails. |
| **Nominal Categoricals** | `gig_work_type`, `loan_purpose` | One-Hot Encoding (`handle_unknown='ignore'`) | `OneHotEncoder` | Converts unranked categories into binary indicator columns. |
| **Ordinal Categoricals** | `income_trend` | Ordinal: `DECLINING` $\rightarrow 0$, `STABLE` $\rightarrow 1$, `GROWING` $\rightarrow 2$ | `OrdinalEncoder` | Preserves natural directional hierarchy. |
| **Continuous Ratios** | `feat_inc_cv_90d`, `feat_bur_total_dti`, `feat_act_active_days_ratio` | Robust Scaling (median/IQR) | `RobustScaler` | Center and scale without distortion from extreme outliers. |
| **Optional Nulls** | `feat_ten_years_working`, `feat_pay_utility_on_time`, etc. | Median Imputation + Binary Indicator | `SimpleImputer(add_indicator=True)` | Preserves missingness signal while providing complete numerical matrix. |
| **Extreme Leverage Ratios** | `feat_bur_total_dti`, `feat_liq_buffer_to_loan` | Winsorization / Clipping to $[0.0, 5.0]$ | `FunctionTransformer` | Prevents infinite division values when income or loan is small. |

---

## 15. Model Input Format (Schema Specifications)

### 15.1 Tabular Schema (Parquet / Pandas)
The dataset file delivered by Person 2 must be a Parquet table named `synthetic_credit_applications.parquet` containing:
- 3 Identity metadata columns: `applicant_profile_id` (str), `application_id` (str), `cutoff_timestamp` (str ISO-8601).
- 1 Simulation metadata column: `cohort_archetype` (str).
- 3 Raw loan application columns: `requested_loan_amount` (float64), `loan_tenure_months` (int64), `loan_purpose` (str).
- 3 Raw profile columns: `gig_work_type` (str), `years_working` (float64), `average_working_days` (int64).
- 40 Model feature columns: `feat_inc_median_90d` through `feat_int_resilience_idx` (float64 / int64).
- 2 Target columns: `target_default_flag` (int64: 0, 1, or null for insufficient), `repayment_risk_probability` (float64).

### 15.2 Real-Time REST Inference JSON Payload (`MLInferenceInput`)
```json
{
  "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "applicant_profile_id": "7ca12a88-8821-4d1a-8c90-1c390a88b101",
  "cutoff_timestamp": "2026-09-23T10:00:00Z",
  "requested_loan_amount": 15000.00,
  "loan_tenure_months": 3,
  "loan_purpose": "VEHICLE_MAINTENANCE",
  "gig_work_type": "DELIVERY",
  "years_working": 2.5,
  "average_working_days": 24,
  "features": {
    "feat_inc_median_90d": 7800.00,
    "feat_inc_p25_90d": 6900.00,
    "feat_inc_cv_90d": 0.2850,
    "feat_inc_downside_var": 420000.00,
    "feat_trend_slope_90d": 115.50,
    "feat_trend_momentum_30_90": 1.0850,
    "feat_act_active_days_ratio": 0.8000,
    "feat_act_zero_earn_weeks": 0,
    "feat_rec_bounceback_ratio": 1.2500,
    "feat_rec_days_to_recover": 6.0,
    "feat_liq_buffer_to_loan": 0.8000,
    "feat_liq_burn_months": 1.2000,
    "feat_bur_dti_ratio": 0.1184,
    "feat_bur_installment_dti": 0.1581,
    "feat_bur_total_dti": 0.2765,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 12,
    "feat_suf_group_count": 4,
    "feat_suf_missing_ratio": 0.0556,
    "feat_int_vol_x_recovery": 1.7100,
    "feat_int_vol_x_buffer": 0.3167,
    "feat_int_trend_x_dti": 147.44,
    "feat_int_resilience_idx": 3.7313
  }
}
```

---

## 16. Model Output Contract

### 16.1 Prediction Output Structure
The output contract aligns directly with [`PredictionResult`](file:///home/gnx/Projects/PARAKH/src/ml/models/prediction.py#L22-L177) and bridges cleanly to the backend [`CreditAssessmentResponse`](file:///home/gnx/Projects/PARAKH/backend/app/schemas/assessment.py#L64-L122):

| Field Name | Data Type | Allowed Range / Values | Description |
| :--- | :--- | :--- | :--- |
| `model_name` | String | `parakh-risk-engine` | Algorithm identifier |
| `model_version` | String | `1.0.0` | Semantic version string |
| `risk_probability` | Float | $[0.0000, 1.0000]$ (or null) | Calibrated default probability |
| `score` | Integer | $[300, 850]$ (or null) | Monotonic presentation credit score |
| `risk_level` | String | `LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT` | Standardized categorical risk tier |
| `confidence` | Float | $[0.0000, 1.0000]$ | Evidence completeness index |
| `is_insufficient_evidence`| Boolean | `True`, `False` | Refusal to score indicator |
| `debt_to_income` | Float | $\ge 0.0000$ (or null) | Verified DTI ratio |
| `income_stability` | Float | $[0.0000, 1.0000]$ (or null) | Normalized income stability index |
| `repayment_reliability` | Float | $[0.0000, 1.0000]$ (or null) | Platform repayment track record |
| `income_archetype` | String | E.g. `Healthy Volatile` | Classified behavioural archetype |
| `volatility_interpretation`| String | Text description | Volatility vs deterioration narrative |
| `key_factors` | List[String] | 3 to 5 bullet strings | Primary drivers influencing score |
| `missing_signal_guidance` | List[String] | Strings (or null) | Actionable missing requirements if insufficient |

### 16.2 Provisional Decision Thresholds (Decision D6 Status)
- **LOWER Risk:** $\hat{p} < 0.20 \implies \text{Score } \ge 700$.
- **MODERATE Risk:** $0.20 \le \hat{p} < 0.45 \implies 550 \le \text{Score} < 700$.
- **HIGHER Risk:** $\hat{p} \ge 0.45 \implies \text{Score } < 550$.
- *Final Status (D6):* **UNDECIDED — Person 3 must finalize this before production underwriting use.**  
  *Rationale:* Decision thresholds cannot be frozen a priori without empirical calibration against validation ROC and PR curves in Phase 8 to balance default loss vs. financial inclusion.

---

## 17. Explainability and Factor Attribution Requirements

### 17.1 Explanation Architecture
Explainability is decoupled into quantitative attribution (SHAP in Phase 7) and a human-readable translation layer ([`PlainLanguageTranslator`](file:///home/gnx/Projects/PARAKH/src/ml/explainability/base.py#L111-L151)):

```
Trained Model + Instance Features
              │
              ▼
    SHAP Value Attributions (phi_j)
              │
              ├───────────────────────────────────────────────┐
              ▼                                               ▼
Quantitative Feature Impact (Log-Odds)           PlainLanguageTranslator
- recovery_duration_days: -0.14                  "Demonstrated rapid earning recovery following
- debt_to_income: +0.18                           income dips indicates strong earning resilience."
```

### 17.2 Feature-to-Human-Readable Translation Mapping

| Feature Name | Favorable Contribution (`DECREASES_RISK`) | Adverse Contribution (`INCREASES_RISK`) |
| :--- | :--- | :--- |
| `feat_inc_median_90d` | "Strong baseline earning capacity provides reliable debt coverage." | "Lower baseline earnings restrict capacity to service additional loan installments." |
| `feat_inc_cv_90d` | "Consistent periodic income with low variance supports predictable repayment." | "Elevated earnings volatility across payout cycles indicates income unpredictability." |
| `feat_rec_days_to_recover` | "Demonstrated rapid earning recovery following income dips indicates strong earning resilience." | "Prolonged recovery periods following income drops suggest cashflow vulnerability." |
| `feat_liq_buffer_to_loan` | "Healthy liquid cash reserve provides strong insulation against unexpected shocks." | "Limited cash reserve provides minimal buffer to absorb temporary disruptions." |
| `feat_bur_total_dti` | "Favorable debt-to-income ratio leaves sufficient disposable income for debt service." | "Existing monthly debt commitments consume a high proportion of baseline earnings." |

---

## 18. Model and Artifact Versioning

Every trained model artifact must register the following metadata matching [`ModelVersion`](file:///home/gnx/Projects/PARAKH/backend/app/models/model_version.py#L11-L42):
- `model_name`: String (e.g. `parakh-volatility-risk-gbm`).
- `model_version`: Semantic version string (e.g. `1.0.0`).
- `dataset_version`: Synthetic dataset identifier (e.g. `synthetic-v1.0`).
- `feature_schema_version`: Feature lineage version (e.g. `feat-v1.0`).
- `preprocessing_version`: Preprocessor pipeline hash.
- `artifact_hash`: SHA-256 hash of serialized joblib model file.
- `training_timestamp`: UTC ISO-8601 string.
- `metrics`: Dictionary of evaluation results (ROC-AUC, PR-AUC, Brier score, ECE).

---

## 19. Sample Data Records (Minimum 5 Diverse Archetypes)

The following 6 records represent the core synthetic archetypes. Note: Expected model predictions (Decision **D7**) remain **UNDECIDED — Person 3 must finalize this after model training.** because estimators have not been trained yet.

```json
[
  {
    "record_id": "SAMPLE_001_HEALTHY_VOLATILE",
    "applicant_profile_id": "7ca12a88-8821-4d1a-8c90-1c390a88b101",
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "Healthy Volatile",
    "gig_work_type": "DELIVERY",
    "requested_loan_amount": 15000.00,
    "loan_tenure_months": 3,
    "loan_purpose": "VEHICLE_MAINTENANCE",
    "feat_inc_median_90d": 7800.00,
    "feat_inc_p25_90d": 6500.00,
    "feat_inc_cv_90d": 0.3200,
    "feat_inc_downside_var": 380000.00,
    "feat_trend_slope_90d": 85.00,
    "feat_trend_momentum_30_90": 1.0500,
    "feat_act_active_days_ratio": 0.7800,
    "feat_act_zero_earn_weeks": 0,
    "feat_rec_bounceback_ratio": 1.2500,
    "feat_rec_days_to_recover": 6.0,
    "feat_liq_buffer_to_loan": 0.8500,
    "feat_liq_burn_months": 1.3000,
    "feat_bur_total_dti": 0.2200,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 12,
    "feat_suf_group_count": 4,
    "feat_suf_missing_ratio": 0.0556,
    "feat_int_vol_x_recovery": 1.9200,
    "feat_int_vol_x_buffer": 0.3368,
    "feat_int_trend_x_dti": 103.70,
    "feat_int_resilience_idx": 3.3784,
    "target_default_flag": 0,
    "repayment_risk_probability": 0.0650,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  },
  {
    "record_id": "SAMPLE_002_STABLE",
    "applicant_profile_id": "1ea22b99-9922-4e2b-9d91-2d491b99c202",
    "application_id": "4ab96f75-6828-4673-c4fd-3d074f77bfb7",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "Stable",
    "gig_work_type": "RIDE_HAILING",
    "requested_loan_amount": 25000.00,
    "loan_tenure_months": 6,
    "loan_purpose": "WORKING_CAPITAL",
    "feat_inc_median_90d": 8200.00,
    "feat_inc_p25_90d": 7800.00,
    "feat_inc_cv_90d": 0.1200,
    "feat_inc_downside_var": 95000.00,
    "feat_trend_slope_90d": 15.00,
    "feat_trend_momentum_30_90": 1.0100,
    "feat_act_active_days_ratio": 0.8500,
    "feat_act_zero_earn_weeks": 0,
    "feat_rec_bounceback_ratio": 1.0500,
    "feat_rec_days_to_recover": 3.0,
    "feat_liq_buffer_to_loan": 0.6000,
    "feat_liq_burn_months": 1.1000,
    "feat_bur_total_dti": 0.1900,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 12,
    "feat_suf_group_count": 4,
    "feat_suf_missing_ratio": 0.0000,
    "feat_int_vol_x_recovery": 0.3600,
    "feat_int_vol_x_buffer": 0.1714,
    "feat_int_trend_x_dti": 17.85,
    "feat_int_resilience_idx": 6.1765,
    "target_default_flag": 0,
    "repayment_risk_probability": 0.0320,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  },
  {
    "record_id": "SAMPLE_003_DECLINING",
    "applicant_profile_id": "2fb33c00-0033-5f3c-0e02-3e502c00d303",
    "application_id": "5bc07a86-7939-5784-d5ae-4e185a88cgc8",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "Declining",
    "gig_work_type": "DELIVERY",
    "requested_loan_amount": 20000.00,
    "loan_tenure_months": 4,
    "loan_purpose": "PERSONAL_EMERGENCY",
    "feat_inc_median_90d": 4500.00,
    "feat_inc_p25_90d": 3200.00,
    "feat_inc_cv_90d": 0.2200,
    "feat_inc_downside_var": 510000.00,
    "feat_trend_slope_90d": -240.00,
    "feat_trend_momentum_30_90": 0.7200,
    "feat_act_active_days_ratio": 0.5500,
    "feat_act_zero_earn_weeks": 1,
    "feat_rec_bounceback_ratio": 0.6500,
    "feat_rec_days_to_recover": 25.0,
    "feat_liq_buffer_to_loan": 0.1500,
    "feat_liq_burn_months": 0.3000,
    "feat_bur_total_dti": 0.4800,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 12,
    "feat_suf_group_count": 3,
    "feat_suf_missing_ratio": 0.1111,
    "feat_int_vol_x_recovery": 5.5000,
    "feat_int_vol_x_buffer": 0.8800,
    "feat_int_trend_x_dti": -355.20,
    "feat_int_resilience_idx": 2.4074,
    "target_default_flag": 1,
    "repayment_risk_probability": 0.5800,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  },
  {
    "record_id": "SAMPLE_004_IRREGULAR",
    "applicant_profile_id": "3ac44d11-1144-6a4d-1f13-4f613d11e404",
    "application_id": "6cd18b97-8040-6895-e6bf-5f296b99dhd9",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "Irregular",
    "gig_work_type": "LOGISTICS",
    "requested_loan_amount": 30000.00,
    "loan_tenure_months": 3,
    "loan_purpose": "VEHICLE_MAINTENANCE",
    "feat_inc_median_90d": 3800.00,
    "feat_inc_p25_90d": 1200.00,
    "feat_inc_cv_90d": 0.6500,
    "feat_inc_downside_var": 920000.00,
    "feat_trend_slope_90d": -45.00,
    "feat_trend_momentum_30_90": 0.8800,
    "feat_act_active_days_ratio": 0.3800,
    "feat_act_zero_earn_weeks": 3,
    "feat_rec_bounceback_ratio": 0.8000,
    "feat_rec_days_to_recover": 22.0,
    "feat_liq_buffer_to_loan": 0.1000,
    "feat_liq_burn_months": 0.2000,
    "feat_bur_total_dti": 0.6200,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 8,
    "feat_suf_group_count": 2,
    "feat_suf_missing_ratio": 0.2222,
    "feat_int_vol_x_recovery": 14.3000,
    "feat_int_vol_x_buffer": 3.2500,
    "feat_int_trend_x_dti": -72.90,
    "feat_int_resilience_idx": 1.1429,
    "target_default_flag": 1,
    "repayment_risk_probability": 0.6400,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  },
  {
    "record_id": "SAMPLE_005_HIGH_OBLIGATION",
    "applicant_profile_id": "4bd55e22-2255-7b5e-2a24-5a724e22f505",
    "application_id": "7de29c08-9151-7906-f7ca-6a307c00eie0",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "High Obligation",
    "gig_work_type": "RIDE_HAILING",
    "requested_loan_amount": 50000.00,
    "loan_tenure_months": 6,
    "loan_purpose": "EQUIPMENT_PURCHASE",
    "feat_inc_median_90d": 9200.00,
    "feat_inc_p25_90d": 8500.00,
    "feat_inc_cv_90d": 0.1800,
    "feat_inc_downside_var": 180000.00,
    "feat_trend_slope_90d": 35.00,
    "feat_trend_momentum_30_90": 1.0200,
    "feat_act_active_days_ratio": 0.8800,
    "feat_act_zero_earn_weeks": 0,
    "feat_rec_bounceback_ratio": 1.1000,
    "feat_rec_days_to_recover": 4.0,
    "feat_liq_buffer_to_loan": 0.1200,
    "feat_liq_burn_months": 0.3500,
    "feat_bur_total_dti": 0.7400,
    "feat_suf_observed_days": 90,
    "feat_suf_payout_count": 12,
    "feat_suf_group_count": 4,
    "feat_suf_missing_ratio": 0.0556,
    "feat_int_vol_x_recovery": 0.7200,
    "feat_int_vol_x_buffer": 0.8182,
    "feat_int_trend_x_dti": 60.90,
    "feat_int_resilience_idx": 4.7826,
    "target_default_flag": 1,
    "repayment_risk_probability": 0.5200,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  },
  {
    "record_id": "SAMPLE_006_INSUFFICIENT_DATA",
    "applicant_profile_id": "5ce66f33-3366-8c6f-3b35-6b835f33a606",
    "application_id": "8ef30d19-0262-8017-08db-7b418d11fjf1",
    "cutoff_timestamp": "2026-09-23T10:00:00Z",
    "cohort_archetype": "Insufficient Data",
    "gig_work_type": "DELIVERY",
    "requested_loan_amount": 10000.00,
    "loan_tenure_months": 2,
    "loan_purpose": "WORKING_CAPITAL",
    "feat_inc_median_90d": 3200.00,
    "feat_inc_p25_90d": 2800.00,
    "feat_inc_cv_90d": 0.1500,
    "feat_inc_downside_var": 50000.00,
    "feat_trend_slope_90d": 0.00,
    "feat_trend_momentum_30_90": 1.0000,
    "feat_act_active_days_ratio": 0.1500,
    "feat_act_zero_earn_weeks": 0,
    "feat_rec_bounceback_ratio": 1.0000,
    "feat_rec_days_to_recover": 0.0,
    "feat_liq_buffer_to_loan": 0.2000,
    "feat_liq_burn_months": 0.5000,
    "feat_bur_total_dti": 0.2500,
    "feat_suf_observed_days": 18,
    "feat_suf_payout_count": 2,
    "feat_suf_group_count": 1,
    "feat_suf_missing_ratio": 0.4444,
    "feat_int_vol_x_recovery": 0.0000,
    "feat_int_vol_x_buffer": 0.5000,
    "feat_int_trend_x_dti": 0.00,
    "feat_int_resilience_idx": 5.0000,
    "target_default_flag": null,
    "repayment_risk_probability": null,
    "expected_model_prediction": "UNDECIDED — Person 3 must finalize this after model training."
  }
]
```

---

## 20. Person 2 Validation Checklist

Before handing off the generated synthetic dataset to Person 3, Person 2 must verify every item:

- [ ] **1. Schema Conformance:** The Parquet file contains all 40 required feature columns with exact name matching.
- [ ] **2. Data Types:** Numeric columns are strictly `float64` or `int64`. Identifiers are valid UUIDv4 strings.
- [ ] **3. Range Bounds:** Features satisfy physical bounds: income $\ge 0$, ratios $\ge 0$, active days ratio $\in [0, 1]$, ratings $\in [1, 5]$.
- [ ] **4. Zero vs Null Integrity:** Debt-free applicants have `existing_obligation = 0.00` (NOT `null`).
- [ ] **5. Cohort Proportions:** Dataset contains the 6 cohorts matching the specified proportions within $\pm 2\%$.
- [ ] **6. Volatility-Aware Realism:** Healthy Volatile cohort exhibits high CV ($> 0.25$) but fast recovery ($\le 10\text{ days}$) and low default rate ($< 10\%$).
- [ ] **7. Declining Cohort Realism:** Declining cohort exhibits negative slope and elevated default rate ($> 25\%$).
- [ ] **8. Target Distribution:** Overall positive default rate is between $10.0\%$ and $15.0\%$.
- [ ] **9. Zero Temporal Leakage:** All feature values are computed strictly from historical events before cutoff $t_0$.
- [ ] **10. Zero Target Leakage:** No forward outcome variable ($I_t$, $E_t$, $S_t$ for $t > 0$) appears in the feature columns.
- [ ] **11. Impossible Combinations Excluded:** Zero active days with positive income, or negative recovery ratios, do not exist.
- [ ] **12. Insufficient Evidence Labels:** Insufficient Data cohort records ($< 30\text{d}$ history) have `target_default_flag = null`.
- [ ] **13. Grouped Split Readiness:** Dataset contains multiple applications for a subset of workers to test grouped cross-validation.
- [ ] **14. Deterministic Reproducibility:** Dataset generated with fixed seed `seed = 42`.

---

## 21. Final Frozen ML Data Contract

This section constitutes the **FROZEN SPECIFICATION** governing Person 2 dataset generation and Person 4 backend integration.

### 21.1 Contract Summary

```
================================================================================
                       PARAKH FROZEN ML DATA CONTRACT
================================================================================
Primary Target:          target_default_flag (int64: 0 = Repaid, 1 = Default)
Continuous Target:       repayment_risk_probability (float64: [0.0000, 1.0000])
Unit of Prediction:      Application-level assessment at cutoff timestamp t_0
Observation Window:      [t_0 - 90 days, t_0) (Strict temporal cutoff)
Prediction Horizon:      (t_0, t_0 + 30-90 days] (Forward outcome window)
Total Feature Count:     40 derived/model features + 6 profile/loan raw features
Mandatory Features:      19 core features (must be populated for scoring)
Optional Features:       21 features (median imputation with _was_missing flag)
Dataset Rows:            12,000 applications (10,000 unique applicants; configurable override)
Target Distribution:     10.0% to 15.0% default rate across aggregate dataset
Splitting Protocol:      Grouped by applicant_profile_id (70% Train, 15% Val, 15% Test)
================================================================================
```

### 21.2 SYNTHETIC GENERATION PARAMETERS — FROZEN FOR PHASE 2

This reference table provides Person 2 with the frozen, deterministic generation parameters resolved by Person 3:

| Decision ID | Target Dimension | Frozen Parameter / Distribution | Operational Details & Generator Rules |
| :--- | :--- | :--- | :--- |
| **D1** | **Secondary Numerical Distributions** | All 40 features fully mapped in Section 6.2 | Time-series payouts and active days generated bottom-up; secondary derived features computed deterministically via Section 3.2 formulas. |
| **D2** | **Exogenous Shock Frequency ($\lambda$)** | Monthly $\lambda = 0.05$ ($\lambda_{\text{daily}} = 0.001667\text{ shocks/day}$) | Poisson process; daily probability $P(\text{shock}) = 1 - e^{-\lambda_{\text{daily}}}$. Cohort modifiers: Irregular $\times 1.25$, Declining $\times 1.10$, Stable $\times 0.80$. |
| **D3** | **Pareto Shock Magnitude** | Scale $s_m = ₹3,000\text{ INR}$, Shape $\alpha = 2.20$, Hard Cap $= ₹25,000\text{ INR}$ | Mean shock magnitude $\approx ₹5,500\text{ INR}$. Drawn independently on days when a shock occurs; added to daily living costs. |
| **D4** | **Living-Cost Floor** | Base Floor $= ₹14,000\text{ INR/month}$ ($₹466.67/\text{day}$) | Sampled log-normally per applicant ($\mu = \ln(14000), \sigma = 0.10$); bounded strictly in $[₹12,000, ₹22,000]/\text{month}$. |
| **D5** | **Dataset Size** | **12,000 applications** ($\approx 10,000$ unique workers) | 70% Train (8,400), 15% Val (1,800), 15% Test (1,800). Grouped by `applicant_profile_id`. Configurable override supported via `--n_samples`. |
| **D6** | **Production Underwriting Cutoffs** | **UNDECIDED — Person 3 must finalize this before production underwriting use.** | Retained as unresolved. Decision cutoffs must be empirically calibrated on validation ROC/PR curves in Phase 8. |
| **D7** | **Expected Model Predictions** | **UNDECIDED — Person 3 must finalize this after model training.** | Retained as unresolved. Expected predictions cannot be truthfully established before Phase 5 model training. |

### 21.3 Frozen Features Reference

#### Mandatory Scoring Features (19 Features)
1. `feat_inc_median_90d`: Float, INR $[0, 500000]$
2. `feat_inc_p25_90d`: Float, INR $[0, 500000]$
3. `feat_inc_cv_90d`: Float, Ratio $[0.0, 5.0]$
4. `feat_inc_downside_var`: Float, $\text{INR}^2$ $[0.0, 1.0 \times 10^{10}]$
5. `feat_trend_slope_90d`: Float, INR/wk $[-50000, +50000]$
6. `feat_trend_momentum_30_90`: Float, Ratio $[0.0, 5.0]$
7. `feat_act_active_days_ratio`: Float, Ratio $[0.0, 1.0]$
8. `feat_act_zero_earn_weeks`: Integer, Count $[0, 13]$
9. `feat_rec_bounceback_ratio`: Float, Ratio $[0.0, 10.0]$
10. `feat_rec_days_to_recover`: Float, Days $[0.0, 90.0]$
11. `feat_liq_buffer_to_loan`: Float, Ratio $[0.0, 50.0]$
12. `feat_liq_burn_months`: Float, Months $[0.0, 60.0]$
13. `feat_bur_dti_ratio`: Float, Ratio $[0.0, 20.0]$
14. `feat_bur_installment_dti`: Float, Ratio $[0.0, 20.0]$
15. `feat_bur_total_dti`: Float, Ratio $[0.0, 20.0]$
16. `feat_suf_observed_days`: Integer, Days $[0, 90]$
17. `feat_suf_payout_count`: Integer, Count $[0, 90]$
18. `feat_suf_group_count`: Integer, Count $[0, 5]$
19. `feat_suf_missing_ratio`: Float, Ratio $[0.0, 1.0]$

#### Optional Scored Features (Imputed if Absent) (21 Features)
20. `feat_inc_mean_90d`: Float, INR $[0, 500000]$
21. `feat_inc_trimmed_mean`: Float, INR $[0, 500000]$
22. `feat_inc_iqr_ratio`: Float, Ratio $[0.0, 10.0]$
23. `feat_inc_min_max_ratio`: Float, Ratio $[0.0, 1.0]$
24. `feat_trend_consec_drops`: Integer, Count $[0, 13]$
25. `feat_act_max_idle_streak`: Integer, Days $[0, 90]$
26. `feat_act_weekend_intensity`: Float, Ratio $[0.0, 1.0]$
27. `feat_rec_max_drawdown`: Float, Ratio $[0.0, 1.0]$
28. `feat_ten_years_working`: Float, Years $[0.0, 50.0]$
29. `feat_ten_platform_rating`: Float, Rating $[1.0, 5.0]$
30. `feat_ten_trips_completed`: Integer, Count $[0, 100000]$
31. `feat_ten_cancellation_rate`: Float, Ratio $[0.0, 1.0]$
32. `feat_liq_net_margin`: Float, Ratio $[-2.0, 1.0]$
33. `feat_pay_utility_on_time`: Float, Ratio $[0.0, 1.0]$
34. `feat_pay_max_bill_delay`: Integer, Days $[0, 180]$
35. `feat_pay_repay_reliability`: Float, Index $[0.0, 1.0]$
36. `feat_bur_loan_to_income`: Float, Ratio $[0.0, 10.0]$
37. `feat_int_vol_x_recovery`: Float, Index $[0.0, 450.0]$
38. `feat_int_vol_x_buffer`: Float, Index $[0.0, 50.0]$
39. `feat_int_trend_x_dti`: Float, Index $[-50000, 50000]$
40. `feat_int_resilience_idx`: Float, Index $[0.0, 100.0]$

### 21.4 Frozen Target and Class Balance
- `target_default_flag`: $0$ = Non-default, $1$ = Default, `null` = Insufficient evidence.
- Target derived strictly from forward cash-flow insolvency condition ($B_t < 0$).
- Target positive class rate: $10.0\%\text{ to }15.0\%$.

### 21.5 Frozen Leakage and Partition Rules
- Preprocessing transformations fitted strictly on training partition.
- Splits grouped strictly by `applicant_profile_id` (70% Train / 15% Val / 15% Test).
- Predictors strictly available before cutoff $t_0$.

---
*End of Final ML Data Requirements Document.*
