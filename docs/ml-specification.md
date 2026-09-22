# PARAKH ML Specification and Architecture: Credit Score for the Invisible
**Document Version:** 1.0.0  
**Phase:** Phase 0 — ML Scope, Specification and Architecture  
**Branch:** `ml/credit-risk`  
**Problem Statement:** CX0506 — Credit Score for the Invisible  
**Domain:** FinTech / Digital Payments / Alternative Credit Scoring  
**Status:** Approved Specification  

---

## Table of Contents

1. [ML Objective](#1-ml-objective)
2. [Problem Definition](#2-problem-definition)
3. [Prediction Target](#3-prediction-target)
4. [Unit of Prediction](#4-unit-of-prediction)
5. [Observation and Prediction Windows](#5-observation-and-prediction-windows)
6. [Input Signal Framework](#6-input-signal-framework)
7. [Income Behaviour Framework](#7-income-behaviour-framework)
8. [Volatility-Aware Risk Concept](#8-volatility-aware-risk-concept)
9. [Feature Framework](#9-feature-framework)
10. [Risk Output](#10-risk-output)
11. [Insufficient Evidence](#11-insufficient-evidence)
12. [Proposed Model Architecture](#12-proposed-model-architecture)
13. [Evaluation Strategy](#13-evaluation-strategy)
14. [Explainability](#14-explainability)
15. [Fairness](#15-fairness)
16. [Data Leakage Prevention](#16-data-leakage-prevention)
17. [Synthetic Data Requirements](#17-synthetic-data-requirements)
18. [Future Inference Contract](#18-future-inference-contract)
19. [Backend Integration Boundary](#19-backend-integration-boundary)
20. [Assumptions and Limitations](#20-assumptions-and-limitations)
21. [Phase-by-Phase ML Roadmap](#21-phase-by-phase-ml-roadmap)

---

## 1. ML Objective

The primary objective of the PARAKH Machine Learning system is to estimate loan repayment risk for gig workers, freelancers, and informal micro-entrepreneurs who lack traditional credit histories (credit "invisibles" or "thin-file" applicants) by evaluating consented alternative financial, platform, and behavioural signals.

### 1.1 The Core Distinction: Volatility-Aware Credit Assessment
Conventional credit underwriting systems are calibrated on formal salaried employees whose income is expected to arrive on fixed monthly dates with negligible variance. When applied to gig-economy workers (such as ride-hailing drivers, delivery agents, or freelance service providers), conventional models treat income variance as default risk, penalizing healthy workers simply because their earnings vary week to week.

PARAKH ML implements a **volatility-aware credit assessment** paradigm based on the following principles:
- **Healthy volatility is normal in gig work:** Gig workers frequently experience cyclical variation driven by platform demand surges, seasonal peaks, festivals, weather events, or deliberate rest days. High variance alone does not signify insolvency.
- **Deterioration vs. Natural Fluctuation:** The ML system must distinguish between healthy, resilient earnings volatility (where drops are followed by prompt recovery) and genuine financial deterioration (persistent negative trend, structural collapse of active days, or severe debt overhang).
- **Joint Signal Conditioning:** Income level, trajectory (trend), variance (volatility), regularity (consistency), post-shock bounceback (recovery), platform tenure, and existing debt commitments must be evaluated jointly rather than in isolated linear penalties.

### 1.2 Explicit Non-Claims and Regulatory Boundaries
To maintain scientific rigor and regulatory compliance, the following boundaries are established:
- **No Bureau Replacement:** The PARAKH prototype does not replace regulated credit bureaus (e.g., CIBIL, Equifax, Experian, CRIF High Mark) or statutory bureau files.
- **No Legally Binding Decisioning:** The ML system is an algorithmic risk assessment and decision-support prototype. It does not issue legally binding credit approvals or rejections under RBI (Reserve Bank of India) lending frameworks.
- **No Claims of Empirical Production Performance:** Because this phase and subsequent early phases develop and evaluate models on controlled synthetic distributions, no claims are made regarding real-world commercial default rates until validated on real, legally consented institutional data.
- **Strict Adherence to Grounded Evidence:** All proposed interfaces and attributes are verified against existing repository artifacts and explicitly marked where newly proposed.

---

## 2. Problem Definition

### 2.1 Context and Financial Exclusion
Credit invisibles represent a large portion of the working population in developing digital economies. While gig workers generate consistent digital cash flow via on-demand platforms, their cash flows do not fit the documentation requirements of formal commercial lending:
1. **Absence of Formal Collateral and Pay Slips:** Gig workers are independent contractors without standard employer salary slips or Form 16 documentation.
2. **Thin-File / No-File Status:** Workers without prior formal bank loans or credit cards receive low or zero credit scores from bureaus simply due to lack of bureau history ("No-Hit").
3. **Misclassification of Non-Linear Lifestyles:** Irregular payout intervals and fluctuating hours lead heuristic bank filters to flag gig workers as "unstable" or "high risk."

### 2.2 Machine Learning Framing
PARAKH formulates alternative credit assessment as a **supervised probabilistic risk estimation and decision-support problem**:
$$\hat{p} = P(Y = 1 \mid \mathbf{x}_{\text{obs}})$$
Where:
- $\mathbf{x}_{\text{obs}}$ is a vector of features extracted strictly over a defined historical observation period from consented alternative signals.
- $Y \in \{0, 1\}$ denotes the binary repayment outcome ($1$ = default / severe delinquency, $0$ = successful repayment) over a specified forward prediction horizon.
- $\hat{p} \in [0.0, 1.0]$ represents the calibrated default probability.

### 2.3 Prototype Scope
The system designed across Phase 0 through Phase 9 is an isolated, reproducible Machine Learning prototype. It prioritizes:
1. High explainability (local and global attributions).
2. Rigorous prevention of temporal and target data leakage.
3. Explicit detection of cold-start / sparse data profiles (yielding `INSUFFICIENT_EVIDENCE` rather than inaccurate forced predictions).
4. Fair treatment across distinct gig sectors and operational tenure groups.

---

## 3. Prediction Target

### 3.1 Target Definition
The primary ML prediction target is:
$$\mathbf{Y} \in \{0, 1\} \quad \text{where } Y = 1 \text{ denotes loan repayment default / severe delinquency}$$

In the synthetic prototype environment:
- **Positive Outcome ($Y = 1$):** A default event, defined as the failure to fulfill contractual repayment obligations (e.g., 30+ or 60+ days past due [DPD] on a synthetic financing product) within the designated prediction window.
- **Negative Outcome ($Y = 0$):** Successful, full repayment of scheduled obligations within the prediction window without entering severe delinquency.

### 3.2 Probability vs. Score Representation
- **Primary ML Output:** Calibrated repayment risk probability ($\hat{p} \in [0.0, 1.0]$). Operating natively in probability space preserves calibration, allows mathematically sound threshold tuning, enables loss-function optimization, and facilitates risk aggregation.
- **Presentation Layer Score:** For user experience and reviewer familiarization, the continuous probability $\hat{p}$ can be transformed via a monotonic scaling function into a presentation score (e.g., $S \in [300, 850]$ or $[0, 1000]$):
  $$S = \text{round}\left(S_{\min} + (1.0 - \hat{p}) \times (S_{\max} - S_{\min})\right)$$
  The presentation score is strictly a secondary transformation and is never used as the training objective.

### 3.3 Synthetic Target Simulation Assumptions
Because production credit default data is unavailable in the prototype workspace, the target will be simulated in Phase 2 using a clear behavioural insolvency model rather than arbitrary labels:
1. **Cash Flow Solvency Condition:** A worker defaults ($Y = 1$) if their cumulative net earnings plus available cash buffers over the prediction horizon fall below their non-negotiable living costs plus committed debt obligations.
2. **Shock Vulnerability:** Default probability increases non-linearly if a negative economic shock (e.g., illness, equipment breakdown, demand collapse) occurs in an environment where cash reserves are depleted and debt-to-income is high.
3. **No Target Leakage into Features:** The simulation logic generating $Y$ must strictly consume forward-looking outcome-window data, while feature extractors must strictly consume historical observation-window data.

---

## 4. Unit of Prediction

### 4.1 Prediction Entity: Application-Level Assessment
The unit of prediction is a **Credit Assessment for a specific Loan Application at a discrete point in time $t_0$**.

```
Applicant Profile (Worker Identity)
       │
       ├── Application 1 (t = t_0) ──> Assessment 1 (ML Prediction at t_0)
       │
       └── Application 2 (t = t_1) ──> Assessment 2 (ML Prediction at t_1)
```

### 4.2 Rationale
- **Time-Varying Worker Status:** A worker's earning behaviour, platform ratings, and debt commitments change over time. Scoring an applicant without anchoring to a timestamp would cause temporal ambiguity.
- **Loan-Specific Terms:** Repayment risk is conditional not only on earning capacity, but on the requested loan terms:
  - Principal amount requested ($L$)
  - Preferred repayment tenure in months ($M$)
  - Intended purpose of financing
  A worker with ₹25,000 monthly income may represent low risk for a ₹5,000 micro-advance, but high risk for a ₹150,000 equipment purchase loan.
- **Alignment with Domain Model:** Existing backend entities (`applications` and `credit_assessments` in `backend/app/models/application.py` and `backend/app/models/assessment.py`) explicitly associate each assessment with an `application_id`.

---

## 5. Observation and Prediction Windows

A strict temporal partition prevents data leakage and aligns with real-world credit assessment workflows.

```
       [   Observation Window (T_obs)   ]  Cutoff (t_0)  [  Prediction Window (T_pred)  ]
───────|────────────────────────────────|───────────────|──────────────────────────────|───────> Time
       t_0 - T_obs                                      t_0                            t_0 + T_pred
       <------- Consented Signals ------->               <----- Repayment Outcome ----->
       <------- Features Extracted ------>               <----- Target Label (Y) ------>
```

### 5.1 Observation Window ($T_{\text{obs}}$)
- **Duration:** Standard **90 days** (with secondary support for 180 days where extended history exists).
- **Function:** Captures historical platform payouts, work frequency, earnings volatility, and spending indicators prior to application submission.
- **Granularity:** Payout-level, daily work logs, and periodic transaction summaries occurring within $[t_0 - T_{\text{obs}}, t_0)$.
- **Minimum History Requirement:** A worker must possess a minimum of **30 days** of active platform history and at least **4 completed payout cycles** within the observation window to qualify for statistical scoring; otherwise, the system routes the profile to `INSUFFICIENT_EVIDENCE`.

### 5.2 Cutoff Point ($t_0$)
- **Timestamp:** The exact UTC timestamp at which the application is submitted.
- **Hard Rule:** Any signal, transaction, payout, or event recorded with timestamp $t \ge t_0$ is strictly prohibited from feature computation.

### 5.3 Prediction Horizon ($T_{\text{pred}}$)
- **Duration:** Standard **30 to 90 days** (aligned with micro-financing tenures common in alternative gig lending: 1 to 3 months).
- **Function:** The future window over which borrower repayment behaviour and potential delinquency are observed and labeled.

---

## 6. Input Signal Framework

PARAKH operates under strict **data-minimization and user-consent principles** (as established in `backend/app/models/financial_signal.py` and `backend/app/assessment/schemas.py`). Invasive surveillance data—including raw bank transaction texts, GPS location histories, contact address books, and banking passwords—is rejected at the boundary.

### 6.1 Signal Taxonomy

| Signal Group | Signal Name | Data Type | Status in Codebase | Source / Channel | Consent Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Worker / Profile** | `applicant_profile_id` | UUID | Existing in Backend | System Profile | Yes |
| | `gig_work_type` | Categorical | Existing in Backend | Platform / Profile | Yes |
| | `years_working` | Decimal (Years) | Existing in Backend | Platform / Profile | Yes |
| | `average_working_days` | Integer (Days/Mo) | Existing in Backend | Platform / Profile | Yes |
| **Loan Terms** | `requested_loan_amount` | Decimal (INR) | Existing in Backend | Application Form | N/A |
| | `loan_tenure_months` | Integer (Months) | Existing in Backend | Application Form | N/A |
| | `loan_purpose` | String | Existing in Backend | Application Form | N/A |
| **Gig Income** | `periodic_earnings_series` | Array of Floats | Proposed for ML | Consented Gig API | Yes |
| | `average_income` | Decimal (INR) | Existing in Backend | FinancialSignal | Yes |
| | `median_income` | Decimal (INR) | Existing in Backend | FinancialSignal | Yes |
| | `active_days` | Integer (Count) | Existing in Backend | FinancialSignal | Yes |
| | `payout_frequency` | Categorical (Daily/Wk)| Proposed for ML | Consented Gig API | Yes |
| **Income Behaviour** | `income_volatility` | Decimal (Index) | Existing in Backend | FinancialSignal | Yes |
| | `income_trend` | String (Categorical)| Existing in Backend | FinancialSignal | Yes |
| | `shock_recovery_series` | Array of Tuples | Proposed for ML | Derived from Series | Yes |
| **Cashflow & Buffer**| `cashflow_buffer` | Decimal (INR) | Existing in Backend | FinancialSignal | Yes |
| | `reserve_to_expense_ratio`| Float | Proposed for ML | Derived from Signals| Yes |
| **Payment Behaviour**| `payment_regularity` | Decimal ([0, 1]) | Existing in Backend | FinancialSignal | Yes |
| | `repayment_reliability`| Decimal ([0, 1]) | Existing in Backend | FinancialSignal | Yes |
| | `utility_payment_ratio`| Float ([0, 1]) | Proposed for ML | Consented Utility BBPS| Yes |
| **Obligations** | `existing_obligation` | Decimal (INR/Mo) | Existing in Backend | FinancialSignal | Yes |
| | `debt_to_income` | Decimal (Ratio) | Existing in Backend | Assessment/Derived | Yes |
| **Platform Activity** | `platform_rating` | Decimal ([0, 5]) | Existing in Backend | FinancialSignal | Yes |
| | `completed_orders_count`| Integer | Proposed for ML | Consented Gig API | Yes |
| | `cancellation_rate` | Float ([0, 1]) | Proposed for ML | Consented Gig API | Yes |

### 6.2 Data Minimization Policy
Any payload containing the following prohibited keys is rejected immediately by the ingestion boundary (matching `PROHIBITED_FIELDS` in `backend/app/assessment/schemas.py`):
`bank_account_number`, `bank_credentials`, `banking_login_credentials`, `password`, `raw_transactions`, `raw_bank_statements`, `raw_upi_transactions`, `raw_upi_logs`, `upi_vpa`, `merchant_name`, `gps_coordinates`, `location_history`, `contact_list`.

---

## 7. Income Behaviour Framework

Because gig workers earn on piece-rate, shift-rate, or surge-rate schedules, treating periodic income as a stationary Gaussian distribution produces severe credit mischaracterizations. PARAKH establishes six core behavioural pillars to model gig income dynamics:

```
                          ┌─────────────────────────────┐
                          │   Income Behaviour Matrix   │
                          └──────────────┬──────────────┘
            ┌───────────────────┬────────┴───────────┬───────────────────┐
            ▼                   ▼                    ▼                   ▼
    ┌───────────────┐   ┌───────────────┐    ┌───────────────┐   ┌───────────────┐
    │ Income Level  │   │  Volatility   │    │     Trend     │   │   Recovery    │
    │ Baseline &    │   │ Fluctuation   │    │ Trajectory &  │   │ Elasticity &  │
    │ Earning Power │   │ & Dispersion  │    │ Direction     │   │ Post-Shock    │
    └───────────────┘   └───────────────┘    └───────────────┘   └───────────────┘
            │                                                            │
            └───────────────────┬────────────────────┬───────────────────┘
                                ▼                    ▼
                        ┌───────────────┐    ┌───────────────┐
                        │  Consistency  │    │   Frequency   │
                        │ Regularity of │    │ Cadence &     │
                        │ Active Cycles │    │ Payout Speed  │
                        └───────────────┘    └───────────────┘
```

### 7.1 The Six Behavioural Pillars
1. **Income Level:** Baseline earning capacity over the observation window. Modeled using robust statistics (median and 25th percentile) rather than simple arithmetic mean to prevent positive surge spikes from skewing baseline expectations.
2. **Income Volatility:** Magnitude of periodic earning fluctuations relative to baseline. Quantified using robust dispersion metrics (Coefficient of Variation, Downside Semi-Variance, Interquartile Range).
3. **Income Trend:** The directional momentum of earnings over time (positive slope, neutral plateau, or structural contraction), separated from short-term noise.
4. **Income Consistency:** Temporal regularity of earning generation (active days per week, continuity of payout cycles, absence of unexpected multi-week lapses).
5. **Income Recovery:** The resilience and speed with which a worker's earnings rebound to baseline after experiencing an income trough or external economic shock.
6. **Earning Frequency:** The structural cadence of earnings (e.g., daily cash-outs vs. weekly automated settlements), reflecting working capital liquidity.

### 7.2 Core Behavioural Profiles
The framework formally recognizes four distinct earning archetypes:

```
  Income (₹)
     ▲
     │       /\    /\        /\    /\        Healthy Volatile (Surges & dips, but rapid recovery)
     │  /\  /  \  /  \  /\  /  \  /  \
     │ /  \/    \/    \/  \/    \/    \      Stable (Low variance, predictable baseline)
     │---------------------------------
     │ \
     │  \     \                              Declining (Persistent loss of earning capacity)
     │   \_____\_____\_________
     │         __        __                  Irregular (Sparse activity, high fragility)
     │________/  \______/  \___________
     └─────────────────────────────────► Time
```

1. **Healthy Volatile:**
   - *Characteristics:* High earnings variance; periodic surge weeks (e.g., festive seasons or monsoon demand) interspersed with lighter weeks; rapid rebound following troughs; strong overall median income.
   - *Credit Risk Interpretation:* **Low to Moderate Risk**. Natural flexibility of gig work must not be penalized. High resilience and strong recovery indicate healthy debt service capacity.
2. **Declining:**
   - *Characteristics:* Low or moderate volatility, but persistent negative trend over consecutive periods (e.g., dropping 15% month-over-month); declining active days.
   - *Credit Risk Interpretation:* **High Risk**. Indicates platform burnout, vehicle de-registration, de-prioritization by platform dispatch algorithms, or broader loss of earning viability.
3. **Stable:**
   - *Characteristics:* Consistent weekly or monthly earnings with minimal variance; regular active working days (e.g., 24–26 days per month); predictable cash flow.
   - *Credit Risk Interpretation:* **Lower Risk**. High predictability provides consistent debt service capacity.
4. **Irregular / Fragile:**
   - *Characteristics:* Sparse, ad-hoc earning days with multi-week zero-earning gaps; weak rebound after drops; near-zero cash reserve buffer.
   - *Credit Risk Interpretation:* **Higher Risk**. Highly vulnerable to default upon the slightest expenditure shock.

---

## 8. Volatility-Aware Risk Concept

### 8.1 Why Naive Scoring Fails
In traditional scoring formulations (including the baseline rule-based `MockAssessmentEngine` currently in `backend/app/assessment/mock.py`), volatility enters the score as a simple linear penalty:
```python
# Naive penalty in existing mock backend engine:
if input_data.income_volatility is not None:
    base -= min(0.25, vol * 0.5)
```
This naive deduction produces two catastrophic errors:
1. **False Positives (Unfair Denial):** It penalizes highly productive gig workers who earn ₹50,000 one month and ₹35,000 the next (variance = ₹15,000), even though their *lowest* earning period comfortably covers a ₹3,000 monthly loan installment.
2. **False Negatives (Blindness to Decay):** It rewards an applicant whose earnings are declining steadily from ₹20,000 to ₹15,000 to ₹10,000 simply because the variance between consecutive months is small and predictable.

### 8.2 The PARAKH Formulation: Joint Conditioning
In the PARAKH ML architecture, default risk is conditioned on the **joint interaction** of volatility with recovery, trend, baseline level, and debt commitments:
$$P(\text{Default} \mid \mathbf{x}) = f(\text{Volatility} \times \text{Recovery}, \text{Trend}, \frac{\text{Baseline Income}}{\text{Obligations}}, \text{Cashflow Buffer})$$

### 8.3 Behavioural Interaction Matrix

| Volatility Level | Income Trend | Recovery Speed | Cashflow Buffer | Obligation Burden (DTI) | Expected ML Risk Tier | Algorithmic Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **High** | Stable / Upward | Fast (< 14 days) | Healthy (> 1.5x loan) | Low (< 20%) | **LOWER_RISK** | Healthy volatile archetype: high earnings capacity with verified elasticity. |
| **High** | Downward | Slow / No recovery| Exhausted (< 0.5x)| High (> 50%) | **HIGHER_RISK** | Structural crisis: compounding volatility with insolvency and debt burden. |
| **Low** | Downward | Not applicable | Low (< 0.5x) | High (> 40%) | **HIGHER_RISK** | Declining archetype: stability in the direction of insolvency. |
| **Low** | Stable | Not applicable | Moderate (> 1.0x)| Low (< 25%) | **LOWER_RISK** | Classical stable profile: steady predictable cash flows. |
| **Moderate** | Flat | Moderate | Marginal | Moderate (30%) | **MODERATE_RISK** | Baseline risk: requires monitoring and conservative loan sizing. |

---

## 9. Feature Framework

Features are organized into ten modular functional categories. All features are computed strictly over the observation window $[t_0 - T_{\text{obs}}, t_0)$.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Feature Category Taxonomy                       │
├────────────────────────────┬────────────────────────────┬──────────────┤
│ 1. Income Level            │ 2. Volatility Metrics      │ 3. Trend     │
│ 4. Consistency & Activity  │ 5. Shock Recovery          │ 6. Work Tenure│
│ 7. Cashflow & Liquidity    │ 8. Payment Discipline      │ 9. Burden    │
│ 10. Data Sufficiency       │                            │              │
└────────────────────────────┴────────────────────────────┴──────────────┘
```

### 9.1 Feature Category Specifications

#### 1. Income Level Features
- **Purpose:** Quantify baseline earning capacity and ability to absorb basic living costs.
- **Features:**
  - `income_median_90d`: Median income across periodic payout cycles (robust against surge outliers). Derived.
  - `income_p25_90d`: 25th percentile of periodic earnings (represents conservative earning floor). Derived.
  - `income_mean_90d`: Arithmetic mean of periodic earnings. Derived.
- **Expected Direction:** Higher values $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Low, provided all cycles fall strictly before $t_0$.

#### 2. Volatility Features
- **Purpose:** Measure dispersion and earnings instability over time.
- **Features:**
  - `income_cv_90d`: Coefficient of variation ($\sigma / \mu$) of periodic payouts. Derived.
  - `downside_semi_variance_90d`: Variance calculated exclusively on periods where earnings fall below the worker's median. Derived.
  - `income_iqr_ratio`: Interquartile range normalized by median ($(\text{P75} - \text{P25}) / \text{Median}$). Derived.
- **Expected Direction:** Non-linear; high downside variance with low buffer $\rightarrow$ Higher risk ($\uparrow$).
- **Leakage Risk:** Low.

#### 3. Trend Features
- **Purpose:** Detect whether earning capacity is expanding, stable, or contracting.
- **Features:**
  - `income_slope_90d`: Normalized linear regression slope of earnings across sequential cycles. Derived.
  - `momentum_30d_vs_90d`: Ratio of average income in the recent 30 days to average income over the full 90-day window. Derived.
  - `consecutive_decline_periods`: Maximum count of consecutive cycles with decreasing earnings. Derived.
- **Expected Direction:** Negative slope / low momentum $\rightarrow$ Higher risk ($\uparrow$).
- **Leakage Risk:** Low.

#### 4. Consistency and Activity Features
- **Purpose:** Capture dedication and regularity of platform engagement.
- **Features:**
  - `active_days_ratio`: Total active working days divided by total calendar days in window. Derived.
  - `zero_earning_weeks_count`: Number of calendar weeks with zero recorded earnings. Derived.
  - `payout_regularity_index`: Normalized index ($[0, 1]$) of payout arrival timeliness against expected platform schedules. Derived.
- **Expected Direction:** High active days / high regularity $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Low.

#### 5. Recovery and Resilience Features
- **Purpose:** Quantify elasticity and speed of rebound following earnings shocks.
- **Features:**
  - `trough_bounceback_ratio`: Ratio of post-shock peak income to pre-shock baseline. Derived.
  - `recovery_duration_days`: Number of days required to return to $\ge 80\%$ of median income following a trough ($> 30\%$ drop). Derived.
  - `max_drawdown_depth`: Maximum percentage drop from a rolling peak to subsequent trough. Derived.
- **Expected Direction:** Fast recovery / high bounceback $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Must verify that the trough and recovery both concluded prior to $t_0$.

#### 6. Work Profile and Platform Tenure
- **Purpose:** Evaluate platform experience, stability, and customer reputation.
- **Features:**
  - `years_working`: Total tenure operating in the gig sector. Raw / Profile.
  - `platform_rating`: Composite customer rating normalized to $[0.0, 1.0]$. Raw.
  - `gig_work_type_code`: One-hot or target-encoded category (e.g., delivery, ride-hailing, domestic service). Raw.
- **Expected Direction:** Longer tenure / high rating $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Low.

#### 7. Cashflow and Liquidity Buffer Features
- **Purpose:** Evaluate liquidity cushion available to service debt during dry spells.
- **Features:**
  - `cashflow_buffer_to_loan_ratio`: Cash reserves divided by requested loan principal. Derived.
  - `burn_rate_buffer_months`: Cash buffer divided by estimated monthly non-discretionary commitments. Derived.
- **Expected Direction:** Higher buffer ratio $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Low.

#### 8. Payment Discipline Features
- **Purpose:** Assess demonstrated creditworthiness across alternative payment channels.
- **Features:**
  - `utility_on_time_ratio`: Percentage of utility/telecom bills paid on or before due date. Derived.
  - `historical_repayment_reliability`: Platform loan or peer micro-advance repayment consistency index ($[0.0, 1.0]$). Derived.
- **Expected Direction:** High on-time ratio $\rightarrow$ Lower risk ($\downarrow$).
- **Leakage Risk:** Low.

#### 9. Obligation and Leverage Features
- **Purpose:** Quantify total ongoing debt burden relative to earning capacity.
- **Features:**
  - `debt_to_income_ratio` (DTI): Total monthly debt obligations divided by monthly median income. Derived.
  - `projected_installment_burden`: Requested loan installment divided by median periodic income. Derived.
- **Expected Direction:** High DTI $\rightarrow$ Substantially higher risk ($\uparrow$).
- **Leakage Risk:** Low.

#### 10. Data Sufficiency Features
- **Purpose:** Quantify information completeness to govern confidence and routing.
- **Features:**
  - `observation_days_count`: Total days of recorded history available. Derived.
  - `signal_source_count`: Number of distinct verified signal sources present (Platform, Utility, Bank, Profile). Derived.
  - `missing_feature_ratio`: Fraction of required feature inputs missing or unpopulated. Derived.
- **Expected Direction:** High sufficiency $\rightarrow$ Higher confidence ($\uparrow$).
- **Leakage Risk:** None.

---

## 10. Risk Output

The model produces a structured risk assessment object comprising calibrated probabilities, categorical tiers, and decision-support metrics.

### 10.1 Output Definitions
1. **Risk Score (Probability):**
   $$\hat{p} = P(\text{Default} \mid \mathbf{x}) \in [0.0000, 1.0000]$$
   A strictly calibrated continuous probability output by the ML model.
2. **Risk Category (Risk Tier):**
   A discrete tier derived from calibrated thresholds on $\hat{p}$.
   - Proposed ML Tiers: `LOWER_RISK`, `HIGHER_RISK`, and `INSUFFICIENT_EVIDENCE`.
   - Compatibility with Backend: The existing backend `RiskLevel` enum (`backend/app/models/assessment.py`) defines:
     `LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`.
     To ensure zero conflict while preserving model fidelity:
     - `LOWER_RISK` maps directly to backend `RiskLevel.LOWER`.
     - `MODERATE_RISK` (intermediate tier) maps to backend `RiskLevel.MODERATE`.
     - `HIGHER_RISK` maps to backend `RiskLevel.HIGHER`.
     - `INSUFFICIENT_EVIDENCE` maps to backend `RiskLevel.INSUFFICIENT`.
3. **Assessment Confidence:**
   A continuous index $C \in [0.0, 1.0]$ representing **data completeness and signal sufficiency**, NOT a claim of statistical certainty:
   $$C = w_1 \cdot \left(\frac{\text{Observed Days}}{\text{Target Window Days}}\right) + w_2 \cdot \left(\frac{\text{Active Signal Sources}}{\text{Total Signal Sources}}\right) + w_3 \cdot (1 - \text{Missing Ratio})$$

### 10.2 Prototype Decision Thresholds
Initial operational thresholds are established for synthetic prototyping and will be calibrated against validation ROC and PR curves in Phase 8:

| Risk Category | Default Probability Threshold ($\hat{p}$) | Synthetic Score Equivalent ($S \in [300, 850]$) | Presumed Policy Recommendation |
| :--- | :--- | :--- | :--- |
| **LOWER_RISK** | $\hat{p} < 0.20$ | $S \ge 700$ | Standard automated processing |
| **MODERATE_RISK** | $0.20 \le \hat{p} < 0.45$ | $550 \le S < 700$ | Manual review / conservative loan terms |
| **HIGHER_RISK** | $\hat{p} \ge 0.45$ | $S < 550$ | Elevated risk mitigation required |
| **INSUFFICIENT_EVIDENCE** | Undefined / Null | Null / None | Cold-start refusal; request additional signals |

> [!IMPORTANT]
> The thresholds above are explicit prototype defaults. In Phase 8, optimal cutoffs will be determined by maximizing the F1-score or matching specific operational risk tolerance curves (e.g., target false-positive rate $\le 5\%$).

---

## 11. Insufficient Evidence

A foundational ethical requirement of the PARAKH ML system is the **refusal to guess**. When input data lacks the necessary observation depth or signal diversity to support an informed estimate, the model must return `INSUFFICIENT_EVIDENCE` rather than fabricating an arbitrary score or assuming high risk.

```
Incoming Assessment Input
           │
           ▼
┌──────────────────────────────────────┐
│ Evidence Sufficiency Evaluator       │
│  - Observation duration >= 30 days?  │
│  - Completed payouts >= 4?           │
│  - Distinct signal categories >= 2?  │
│  - Critical signals populated?       │
└──────────────────┬───────────────────┘
                   │
         Pass ─────┴───── Fail
          │                │
          ▼                ▼
┌──────────────────┐  ┌──────────────────────────────────────────────┐
│ Proceed to       │  │ Short-Circuit: Return INSUFFICIENT_EVIDENCE  │
│ Feature Pipeline │  │  - credit_score = null                       │
│ & ML Scoring     │  │  - risk_probability = 0.50 (uninformed prior)│
└──────────────────┘  │  - confidence = data completeness index      │
                      │  - explanation = explicit missing factors    │
                      └──────────────────────────────────────────────┘
```

### 11.1 Insufficient Evidence Triggers
An assessment is immediately classified as `INSUFFICIENT_EVIDENCE` if any of the following deterministic conditions are met:
1. **Observation Duration Truncation:** Total historical timeline in the observation window is less than **30 days**.
2. **Payout Cycle Sparsity:** Fewer than **4 distinct payout cycles** recorded.
3. **Absence of Core Signal Groups:** Fewer than **2 independent signal categories** are present (e.g., profile present, but zero platform income or utility signals).
4. **Extreme Missingness in Critical Pillars:** Both `average_income` and `median_income` are null or zero, or all payment discipline indicators are missing.
5. **Direct Data Conflict:** Incoherent timestamps (e.g., start date occurs after end date) or mutually contradictory signals (e.g., active days $> 0$ with zero recorded earnings over 180 days).

### 11.2 Output Behaviour Under Insufficient Evidence
When triggered:
- `credit_score` is returned as `None` / `null`.
- `risk_probability` is set to an uninformed neutral prior (e.g., `0.5000` or `null`).
- `risk_level` is set strictly to `INSUFFICIENT` (`INSUFFICIENT_EVIDENCE`).
- `confidence` is calculated purely from the completeness formula ($C \le 0.35$).
- `key_factors` lists the exact missing signals required to enable scoring (e.g., *"Requires at least 30 days of verified gig platform earning history"*).

---

## 12. Proposed Model Architecture

The ML system is architected as an end-to-end, reproducible, modular scikit-learn compatible pipeline.

```
Consented Raw Signals
         │
         ▼
┌────────────────────────────────────────┐
│ 1. Data Validation & Minimization Gate │  <-- Rejects prohibited fields & invalid ranges
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 2. Temporal Windowing & Feature Engine │  <-- Aggregates [t_0 - T_obs, t_0) features
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 3. Income Behaviour Component          │  <-- Extracts volatility, recovery, & trend
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 4. Calibrated Risk Classifier          │  <-- Baseline / Tree-based model -> P(Default)
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│ 5. Explainability & Packaging Engine   │  <-- Computes SHAP attributions & factors
└──────────────────┬─────────────────────┘
                   │
                   ▼
Standardized Assessment Output Object
```

### 12.1 Pipeline Components
1. **Data Validation & Minimization Gate:** Validates schema integrity, types, and ranges; enforces data-minimization rules; strips or rejects prohibited attributes.
2. **Temporal Windowing & Feature Engine:** Enforces the observation window boundary ($t < t_0$) and computes normalized feature vectors.
3. **Income Behaviour Component:** Dedicated sub-module computing the six behavioural pillars, joint interaction terms, and recovery metrics.
4. **Calibrated Risk Classifier:** Supervised classification model yielding default probability $\hat{p}$, calibrated via Isotonic Regression or Platt Scaling.
5. **Explainability & Packaging Engine:** Extracts local instance feature contributions and generates plain-language explanations.

### 12.2 Model Selection and Benchmark Strategy
To prevent premature complexity, model selection follows a strict evidence-driven progression:
1. **Stage 1 — Baseline Model (Phase 5):**
   - **Logistic Regression** with L2 regularization and standard scaling.
   - Purpose: Establish the baseline performance floor, verify linear feature directions, and ensure pipeline operational stability.
2. **Stage 2 — Volatility-Aware Non-Linear Models (Phase 6):**
   - **Random Forest Classifier** and **Histogram-based Gradient Boosting (HistGradientBoostingClassifier / LightGBM)**.
   - Purpose: Capture non-linear feature interactions (such as the joint volatility $\times$ recovery interaction) that linear models fail to resolve.
3. **Model Selection Rule:** A complex model (e.g., Gradient Boosting) will only be selected over the baseline if it demonstrates a statistically significant improvement in ROC-AUC ($\ge 0.03$) and PR-AUC on cross-validation while maintaining acceptable explainability.

---

## 13. Evaluation Strategy

### 13.1 Metric Selection
Alternative credit datasets exhibit class imbalance (typical default rates range from 5% to 15%). Consequently, accuracy is rejected as a primary metric.

| Evaluation Metric | Target Domain | Why It Is Critical for PARAKH |
| :--- | :--- | :--- |
| **PR-AUC (Average Precision)** | Ranking / Imbalance | Primary metric for imbalanced positive default detection. Focuses on the minority class without inflation by high true negatives. |
| **ROC-AUC** | Discrimination | Measures overall pairwise separation between defaulters and non-defaulters across all possible thresholds. |
| **Brier Score / ECE** | Calibration | Measures how closely predicted probabilities reflect empirical default frequencies ($\hat{p} = 0.20$ must correspond to a 20% empirical default rate). |
| **Precision @ Calibrated Threshold** | Operational Cost | Minimizes false positives (denying viable gig workers access to credit). |
| **Recall @ Calibrated Threshold** | Risk Protection | Minimizes false negatives (underwriting loans that default). |
| **F1-Score** | Balance | Harmonic balance between precision and recall at operational cutoffs. |

### 13.2 Validation Splits and Leakage Control
- **K-Fold Stratified Cross-Validation:** 5-fold cross-validation stratified by the target label $Y$.
- **Temporal Out-of-Time (OOT) Testing:** Where longitudinal data exists, a holdout test split consisting of the latest chronological time slice ($T_{\text{test}}$) will be evaluated to verify temporal generalization.
- **Group Separation:** If individual workers submit multiple applications over time, splits must be grouped by `applicant_profile_id` (`GroupKFold`) to prevent the same worker from appearing in both train and test folds.

### 13.3 Stress and Stability Checks
- **Subgroup Breakdown:** Metrics evaluated independently across gig work sectors and tenure buckets.
- **Perturbation Testing:** Verifying that small perturbations in input earnings ($\pm 5\%$) do not cause erratic swings in predicted risk categories.

---

## 14. Explainability

A black-box prediction is unacceptable in credit assessment. Lenders require risk rationale for auditability, and workers require transparent explanations.

### 14.1 Explanation Deliverables
Every completed assessment must produce:
1. **Top Contributing Factors (`key_factors`):** 3 to 5 human-readable bullet points identifying the primary variables driving the assessment.
2. **Directional Impact:** Whether each factor increased or decreased estimated risk.
3. **Structured Explanation Payload (`explanation`):** Quantitative attributions (e.g., SHAP values or feature impact scores) mapped to each feature group.

### 14.2 Future Technology: SHAP (Phase 7)
In Phase 7, **TreeSHAP** (for tree models) or **LinearSHAP** (for baseline models) will be integrated to generate local additive attributions:
$$\hat{f}(\mathbf{x}) = \phi_0 + \sum_{j=1}^{M} \phi_j(\mathbf{x})$$
Where:
- $\phi_0$ is the base expected value.
- $\phi_j$ is the marginal contribution of feature $j$.

### 14.3 Plain-Language Mapping Rules
Raw mathematical features must be translated into clear, respectful language:

| Technical Feature Direction | Plain-Language reviewer Explanation |
| :--- | :--- |
| High `income_cv_90d` + High `recovery_duration_days` | *"Earning fluctuations accompanied by extended recovery periods indicate cashflow vulnerability."* |
| High `income_cv_90d` + Fast `trough_bounceback_ratio` | *"Earnings vary periodically, but demonstrated rapid recovery following dips indicates strong earning resilience."* |
| High `cashflow_buffer_to_loan_ratio` | *"Sufficient cash reserves provide strong insulation against temporary earning disruptions."* |
| High `debt_to_income_ratio` | *"Existing monthly debt commitments consume a high proportion of baseline earnings."* |
| High `utility_on_time_ratio` | *"Consistent on-time utility payment history demonstrates strong payment discipline."* |

---

## 15. Fairness

Algorithmic fairness is a core design requirement for alternative credit assessment to avoid reinforcing historical systemic disparities.

### 15.1 Synthetic Subgroup Auditing
In the synthetic prototype, fairness will be audited across three dimensions:
1. **Gig Work Sector:** Ride-hailing vs. Food Delivery vs. Logistics vs. Freelance Micro-Services.
2. **Platform Tenure:** New entrants (< 6 months) vs. Mid-tenure (6–24 months) vs. Long-tenure (> 2 years).
3. **Income Tier Cohorts:** Lower tercile vs. Middle tercile vs. Upper tercile.

### 15.2 Evaluated Fairness Metrics (Phase 7)
- **Demographic Parity Ratio (DPR):**
  $$\frac{P(\hat{Y} = 0 \mid A = a)}{P(\hat{Y} = 0 \mid A = b)} \ge 0.80$$
  Evaluating whether loan qualification rates differ disproportionately across gig sectors.
- **Equal Opportunity Difference (EOD):**
  $$\left| \text{TPR}_{A=a} - \text{TPR}_{A=b} \right| \le 0.10$$
  Ensuring that true non-defaulters in different sectors have an equal probability of being identified as creditworthy.

### 15.3 Critical Limitation on Synthetic Fairness
> [!WARNING]
> Synthetic fairness testing verifies that the *algorithmic pipeline itself* does not introduce mechanical bias across simulated groups. It **does not prove real-world fairness** in human populations, which requires validation on representative empirical datasets under real socioeconomic conditions.

---

## 16. Data Leakage Prevention

Zero-tolerance rules are enforced across all development and training workflows to ensure validity.

```
       HISTORICAL OBSERVATION             CUTOFF            FUTURE OUTCOME
       t in [t_0 - T_obs, t_0)             t_0             t in (t_0, t_0 + T_pred]
  ┌───────────────────────────────┐         │       ┌────────────────────────────────┐
  │ ONLY data here can form       │         │       │ ONLY data here can form        │
  │ predictive features (x)       │         │       │ target labels (Y)              │
  └───────────────────────────────┘         │       └────────────────────────────────┘
                                  ◄─────────┴────────►
                                     STRICT BARRIER
                                  NO INFORMATION CROSS
```

### 16.1 The Five Anti-Leakage Invariants
1. **Temporal Horizon Invariant:** Predictive features $\mathbf{x}$ may strictly use records with timestamp $t < t_0$. No post-cutoff signals may enter the feature matrix.
2. **Target Window Invariant:** Ground-truth default label $Y$ is determined strictly within $(t_0, t_0 + T_{\text{pred}}]$. Outcome-window variables (such as actual loan repayment dates or post-application defaults) are strictly excluded from $\mathbf{x}$.
3. **Simulation Independence Invariant:** In Phase 2 synthetic data generation, features and target outcomes must be simulated sequentially through a causal timeline rather than using target values to construct features.
4. **Pre-Processing Fit Invariant:** All transformations—including imputation, scaling, one-hot encoding, and feature selection—must be `fit` exclusively on the training folds and `transform`ed on validation/test folds within scikit-learn `Pipeline` objects.
5. **Cross-Entity Identity Invariant:** Grouped splits must ensure that all assessments belonging to the same applicant remain within the same split partition.

---

## 17. Synthetic Data Requirements

Phase 2 will implement synthetic data generation. To ensure the ML system can test the volatility-aware hypothesis, the synthetic generator must satisfy specific behavioural criteria.

### 17.1 Required Behavioural Cohorts
The generator must produce a multi-profile dataset with balanced representation across:
1. **Cohort 1 (Stable Low-Volatility):** Regular daily active hours, stationary earnings, steady buffer ($25\%$ of dataset).
2. **Cohort 2 (Healthy Volatile):** Weekly earnings variance $> 35\%$, high peak surges, rapid recovery from dips ($< 10$ days), adequate cashflow buffer ($25\%$ of dataset).
3. **Cohort 3 (Declining / Deteriorating):** Negative monthly earnings trend ($-10\%$ to $-20\%$ per month), degrading platform ratings, eroding buffer ($20\%$ of dataset).
4. **Cohort 4 (Irregular / Fragile):** Erratic payout gaps, prolonged zero-earning streaks, high debt obligations ($15\%$ of dataset).
5. **Cohort 5 (High Obligation / Over-leveraged):** Healthy earnings, but debt-to-income $> 50\%$ ($10\%$ of dataset).
6. **Cohort 6 (Insufficient / Sparse):** Fewer than 30 observation days or fewer than 4 payout records ($5\%$ of dataset; reserved for testing insufficient evidence routing).

### 17.2 Realism Constraints
- **Time-Series Autocorrelation:** Payouts within individual profiles must exhibit realistic temporal dependency (Markovian or ARIMA-like process with demand shocks).
- **Realistic Noise and Outliers:** Platform commission variations, customer tip variance, and occasional zero-earning sick days.
- **Reproducibility:** Generator must support explicit random seeding (`seed=42`) for deterministic reproducibility across runs.

---

## 18. Future Inference Contract

Phase 9 will package the trained ML models into an inference engine. The conceptual contract defined here governs that future interface.

### 18.1 Conceptual Input Schema (`MLInferenceInput`)
```json
{
  "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "applicant_profile_id": "7ca12a88-8821-4d1a-8c90-1c390a88b101",
  "requested_loan_amount": 15000.00,
  "loan_tenure_months": 3,
  "loan_purpose": "Vehicle Maintenance and Battery Replacement",
  "gig_work_type": "DELIVERY",
  "years_working": 2.5,
  "average_working_days": 24,
  "financial_signals": {
    "average_income": 32000.00,
    "median_income": 30500.00,
    "income_volatility": 0.2800,
    "income_trend": "GROWING",
    "active_days": 72,
    "payment_regularity": 0.9200,
    "cashflow_buffer": 8500.00,
    "existing_obligation": 4000.00,
    "platform_rating": 4.85,
    "repayment_reliability": 0.9500
  },
  "historical_payout_series": [
    {"payout_date": "2026-06-07", "amount": 7500.00, "active_days": 6},
    {"payout_date": "2026-06-14", "amount": 8200.00, "active_days": 6},
    {"payout_date": "2026-06-21", "amount": 6900.00, "active_days": 5},
    {"payout_date": "2026-06-28", "amount": 9100.00, "active_days": 7}
  ]
}
```

### 18.2 Conceptual Output Schema (`MLInferenceOutput`)
```json
{
  "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "model_name": "parakh-volatility-risk-engine",
  "model_version": "1.0.0",
  "risk_probability": 0.1250,
  "score": 781,
  "risk_level": "LOWER",
  "confidence": 0.8800,
  "debt_to_income": 0.1311,
  "utilization": 0.1500,
  "income_stability": 0.8200,
  "repayment_reliability": 0.9500,
  "key_factors": [
    "Demonstrated rapid income recovery following short-term earning dips",
    "Low debt-to-income ratio (13.1%) provides strong repayment capacity",
    "High platform customer rating (4.85) and consistent active working days",
    "Positive earnings growth trend observed across the 90-day window"
  ],
  "explanation": {
    "engine_type": "VOLATILITY_AWARE_ML",
    "feature_importances": {
      "trough_bounceback_ratio": -0.142,
      "debt_to_income": -0.098,
      "cashflow_buffer_to_loan": -0.065,
      "income_cv_90d": 0.021
    },
    "income_archetype": "HEALTHY_VOLATILE",
    "insufficient_evidence": false
  },
  "assessment_status": "COMPLETED",
  "assessed_at": "2026-09-22T23:55:00Z"
}
```

---

## 19. Backend Integration Boundary

The ML package (`src/ml/`) and backend service (`backend/app/`) maintain strict separation until Phase 10.

```
┌──────────────────────────────────────────────┐
│ ML Workspace Responsibility (Phases 0-9)     │
│  - Signal schemas and data definitions       │
│  - Synthetic data generators                 │
│  - Feature engineering & pipeline code       │
│  - Model training, tuning, and artifacts     │
│  - SHAP explainability and fairness audits   │
│  - Standalone inference engine               │
└──────────────────────┬───────────────────────┘
                       │
       PHASE 10 BOUNDARY ADAPTER (Engine Contract)
                       │
┌──────────────────────▼───────────────────────┐
│ Backend Application Responsibility (Host)    │
│  - User authentication and RBAC              │
│  - Consent capture, revocation, & audit      │
│  - PostgreSQL persistence (SQLAlchemy)       │
│  - FastAPI routing & response serialization  │
│  - Reviewer workflows and UI integration     │
└──────────────────────────────────────────────┘
```

### 19.1 Clear Division of Responsibilities
- **ML Scope:** Model training, artifact serialization (`models/artifacts/`), validation metrics, feature calculators, and local SHAP computation.
- **Backend Scope:** PostgreSQL tables, database migrations (`alembic/`), HTTP transport, authorization checks, applicant profile persistence, and loan disbursement workflows.

### 19.2 Documentation of Discrepancies and Bridge Plan
During codebase inspection in Phase 0, specific architectural differences were identified between the existing backend prototype and this ML specification:

1. **Risk Tiers Taxonomy:**
   - *Backend Concept:* `RiskLevel` enum in `backend/app/models/assessment.py` defines `LOWER`, `MODERATE`, `HIGHER`, `INSUFFICIENT`.
   - *ML Design:* Risk probability space with tiers `LOWER_RISK`, `MODERATE_RISK`, `HIGHER_RISK`, and `INSUFFICIENT_EVIDENCE`.
   - *Bridge:* The ML inference adapter in Phase 10 will directly map `LOWER_RISK -> RiskLevel.LOWER`, `MODERATE_RISK -> RiskLevel.MODERATE`, `HIGHER_RISK -> RiskLevel.HIGHER`, and `INSUFFICIENT_EVIDENCE -> RiskLevel.INSUFFICIENT`.
2. **Volatility Handling:**
   - *Backend Concept:* The existing `MockAssessmentEngine` (`backend/app/assessment/mock.py`) subtracts a penalty directly for any positive volatility value (`base -= min(0.25, vol * 0.5)`).
   - *ML Design:* Volatility is conditioned on recovery and trend.
   - *Bridge:* The trained ML engine will replace the mock engine without modifying backend schemas, supplying volatility-aware evaluations through the existing `AssessmentEngine` abstract interface (`backend/app/assessment/base.py`).
3. **Engine Interface Compliance:**
   - The abstract base class `AssessmentEngine` (`backend/app/assessment/base.py`) defines `assess(input_data: AssessmentInput) -> AssessmentResult`.
   - In Phase 10, the ML model will be wrapped in a class implementing this exact interface:
     ```python
     class PARAKHMLAssessmentEngine(AssessmentEngine):
         def assess(self, input_data: AssessmentInput) -> AssessmentResult:
             # Adapt AssessmentInput -> ML pipeline -> AssessmentResult
             ...
     ```

---

## 20. Assumptions and Limitations

### 20.1 Assumptions
1. **Consented Data Availability:** Applicants are assumed to grant explicit digital consent to retrieve alternative signals via Account Aggregator, BBPS, or gig platform partner APIs.
2. **Digital Platform Identity:** The worker operates on digital gig platforms where earnings and active days are logged electronically.
3. **Data Integrity at Ingestion:** Aggregated input signals received from platform APIs are assumed to have passed digital signature verification at the gateway.

### 20.2 Limitations
1. **Synthetic Data Realism Boundary:** Models trained on synthetic data capture the statistical relationships intentionally encoded in the simulator. They cannot discover unmodeled real-world economic interactions.
2. **Non-Stationary Economic Shocks:** Sudden macroeconomic shifts (e.g., fuel price shocks, platform commission hikes, algorithmic dispatch changes) can alter repayment dynamics faster than historical models anticipate.
3. **Thin-File Cold Start:** Applicants with fewer than 30 days of platform work cannot be scored and must be routed to `INSUFFICIENT_EVIDENCE`.
4. **Regulatory Status:** The system is an algorithmic research and evaluation prototype. It does not possess accreditation as a Credit Information Company (CIC) under RBI regulations.
5. **Human-in-the-Loop Requirement:** ML outputs are designed to assist human credit reviewers rather than execute unmonitored autonomous lending decisions.

---

## 21. Phase-by-Phase ML Roadmap

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4
Spec &      Data        Synthetic   Data Valid. Feature
Arch.       Definition  Generation  & Clean     Engineering
                                                     │
                                                     ▼
Phase 9 ◄── Phase 8 ◄── Phase 7 ◄── Phase 6 ◄── Phase 5
Inference   Model       Fairness &  Volatility  Baseline
Pipeline    Validation  SHAP        Model       Models
   │
   ▼
Phase 10
Backend
Integration
```

### Roadmap Overview

- **Phase 0 — ML Scope, Specification and Architecture (Current Phase):**
  Define complete ML objective, prediction target, signal taxonomy, income behaviour framework, volatility-aware concept, anti-leakage invariants, future inference schemas, and integration boundaries. Zero code implementation or training.
- **Phase 1 — Data Definition:**
  Define structured dataset schemas, column definitions, data types, value constraints, and data dictionaries for both raw signal feeds and processed feature tables.
- **Phase 2 — Synthetic Data Generation:**
  Develop synthetic behavioural generator simulating diverse gig worker profiles (Healthy Volatile, Stable, Declining, Irregular, High Obligation, Insufficient Data) with causal shock and recovery dynamics.
- **Phase 3 — Data Validation and Preprocessing:**
  Implement automated schema validation, missing-value handlers, range validators, and data quality checks ensuring data minimization compliance.
- **Phase 4 — Feature Engineering:**
  Implement feature extractors for the 10 feature categories: robust income baselines, volatility indices, trend regressors, consistency metrics, and shock recovery counters.
- **Phase 5 — Baseline Models:**
  Implement, train, and calibrate a simple baseline classifier (Regularized Logistic Regression) to establish the minimum benchmark performance floor.
- **Phase 6 — Volatility-Aware Risk Model:**
  Train non-linear models (Random Forest, HistGradientBoosting / LightGBM) that capture the joint interaction between volatility, trend, recovery, and cashflow buffers.
- **Phase 7 — Explainability and Fairness:**
  Implement SHAP explanation generation (local and global attributions, key factors translation) and audit demographic parity and equal opportunity across simulated gig worker cohorts.
- **Phase 8 — Model Validation and Selection:**
  Perform rigorous out-of-time validation, grouped cross-validation, threshold calibration, and statistical comparison against the baseline to formally select the production model artifact.
- **Phase 9 — Prediction / Inference Pipeline:**
  Package the selected model, preprocessors, calibrators, and explainers into a clean, standalone inference module satisfying the `MLInferenceInput` / `MLInferenceOutput` contract.
- **Phase 10 — Backend Integration:**
  Implement the backend adapter bridging the ML package with the FastAPI backend application via `PARAKHMLAssessmentEngine`, connecting ML outputs to database persistence and reviewer API routes.

---
*End of ML Specification Document.*
