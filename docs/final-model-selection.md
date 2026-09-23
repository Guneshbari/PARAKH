# PARAKH — Final Model Selection & Inference Contract Specification

## 1. Selected Model Identity & Governance

This document establishes the official Machine Learning Model Selection and Inference Contract for the PARAKH Alternative Credit Risk Assessment Platform, finalized during **Phase 8 (Final Model Validation & Selection)**.

| Specification Attribute | Contract Value | Reference / Lineage |
| :--- | :--- | :--- |
| **Model Identity** | `volatility-aware-risk-model` | Phase 6 LightGBM GBDT Risk Model |
| **Model Class** | `src.ml.models.volatility_aware.VolatilityAwareRiskModel` | Subclass of [`BaseRiskModel`](file:///home/gnx/Projects/PARAKH/src/ml/models/base.py#L17-L112) |
| **Model Version** | `1.0.0` | Semantic Version 1.0.0 |
| **Primary Estimator** | `lightgbm.LGBMClassifier` | 150 estimators, learning rate 0.05, num leaves 31 |
| **Feature Variant** | `VOLATILITY_AWARE` | Phase 4 Volatility-Aware Feature Set |
| **Total Model-Ready Features** | **64 columns** | 53 numeric/ratio continuous features + 11 one-hot categories |
| **Training Commit** | [`2d47a35`](https://github.com/Guneshbari/PARAKH/commit/2d47a35) | Phase 6 Volatility-Aware Model Implementation |
| **Selection Phase & Commit** | **Phase 8** | Out-of-sample held-out validation on test partition ($N=1,698$) |
| **Artifact Path** | [`models/artifacts/volatility_aware_risk_model.joblib`](file:///home/gnx/Projects/PARAKH/models/artifacts/volatility_aware_risk_model.joblib) | Serialized Joblib Binary Artifact |
| **Manifest Path** | [`models/artifacts/FINAL_MODEL.json`](file:///home/gnx/Projects/PARAKH/models/artifacts/FINAL_MODEL.json) | Production Model Registry Manifest |

> [!IMPORTANT]
> **Zero Retraining Declaration:** The selected model artifact was trained exclusively on the Phase 3 training partition ($N=8,012$, applicant-grouped split, seed=42) during Phase 6. No retraining, weight adjustments, or test-driven parameter tuning occurred during Phase 8.

---

## 2. Rationale & Factual Evidence for Selection

The Volatility-Aware LightGBM model was selected over the Phase 5 L2 Logistic Regression baseline based on factual, multi-dimensional validation evidence across both the validation split ($N=1,697$) and the held-out test split ($N=1,698$):

### 2.1 Out-of-Sample Performance Superiority (Held-Out Test Set, N = 1,698)

| Metric | Phase 5 Linear Baseline | Phase 6 Volatility-Aware | Absolute Delta ($\Delta$) | Operational Advantage |
| :--- | :---: | :---: | :---: | :--- |
| **ROC-AUC** | 0.9696 | **0.9718** | **+0.0022** | Superior pairwise discrimination across diverse borrower profiles |
| **PR-AUC (Avg Precision)** | 0.8680 | **0.8773** | **+0.0093** | Significantly higher precision across minority default candidates |
| **Brier Score** | 0.0472 | **0.0457** | **-0.0015** | Lower mean squared probability error |
| **Recall (@ 0.50 cutoff)** | 0.6734 (167 / 248) | **0.7056 (175 / 248)** | **+0.0322** | **8 additional true defaults detected** (+4.8% relative gain) |
| **False Negatives (@ 0.50)** | 81 | **73** | **-8** | **9.9% reduction in undetected default risk** |
| **Precision (@ 0.50 cutoff)** | 0.8350 | **0.8373** | **+0.0023** | Precision preserved while detecting more defaults |
| **F1-Score (@ 0.50 cutoff)** | 0.7455 | **0.7659** | **+0.0204** | Higher harmonic balance across all operational thresholds |

### 2.2 Empirical Hypothesis Verification Across Cohorts
1. **Healthy Volatile Cohort ($N = 415$, 3 actual defaults):**
   - Baseline PR-AUC: 0.7556
   - Volatility-Aware PR-AUC: **0.8667** (**+0.1111**, or **+14.7% gain**)
   - The tree model isolates genuine distress from seasonal earning spikes by conditioning income variance on recovery velocity and cashflow cushions.
2. **High Obligation Cohort ($N = 173$, 13 actual defaults):**
   - Baseline Recall: 0.2308 (caught only 3 defaults)
   - Volatility-Aware Recall: **0.6154** (caught 8 defaults, **+166.7% improvement**), with PR-AUC improving from 0.5535 to **0.7933** (+0.2398) and Brier error dropping from 0.0492 to **0.0309** (-37.2%).
3. **Irregular Cohort ($N = 299$, 96 actual defaults):**
   - Baseline Recall: 0.6354 (61 defaults detected)
   - Volatility-Aware Recall: **0.6979** (67 defaults detected, +6 defaults caught).

### 2.3 Why the Alternative (Logistic Regression Baseline) Was Not Selected
While the Phase 5 L2 Logistic Regression baseline demonstrated solid performance and excellent linear interpretability, it has structural limitations:
- **Monotonic Volatility Penalty:** Penalizes variance without conditioning on bounceback speed or liquidity buffers.
- **Lower Recall:** Misses 81 defaults on the test set compared to 73 for LightGBM.
- **Inability to Capture Synergistic Interactions:** Fails to detect compounding stress between debt-to-income and negative momentum without exhaustive manual polynomial terms.

---

## 3. Required Preprocessing & Feature Engineering Pipeline

Downstream inference services must execute the exact two-stage transformation pipeline prior to invoking model scoring:

```
                            INFERENCE EXECUTION PIPELINE
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                 │
│   Raw Credit Application Payload (JSON / Dict)                                                  │
│   ├── Raw Loan/Profile Inputs (6 fields): requested_loan_amount, loan_tenure_months, ...       │
│   └── 90-Day Telemetry Summaries (40 fields): feat_inc_median_90d, feat_liq_net_margin, ...    │
│                                           │                                                     │
│                                           ▼                                                     │
│   Stage 1: Feature Engineering Layer (FeatureEngineer)                                          │
│   ├── Calculates 9 Volatility Interaction Terms (feat_eng_*)                                    │
│   ├── Preserves deterministic pre-t0 mathematical formulations                                  │
│   └── Outputs 55 pre-encoded columns                                                            │
│                                           │                                                     │
│                                           ▼                                                     │
│   Stage 2: Preprocessing Pipeline (CreditRiskPreprocessor)                                      │
│   ├── Median Imputation: Fills missing telemetry values using frozen training medians          │
│   ├── Log Transformation: Applied to heavily skewed monetary inputs                             │
│   ├── Robust Scaling: Scales continuous numeric features using training median/IQR             │
│   ├── Missingness Indicators: Appends binary missingness flags for sparse indicators            │
│   └── One-Hot Encoding: Expands gig_work_type (6 dummies) & loan_purpose (5 dummies)           │
│                                           │                                                     │
│                                           ▼                                                     │
│   Model Ingestion Vector: 64 model-ready columns in strict contract order                       │
│                                           │                                                     │
│                                           ▼                                                     │
│   VolatilityAwareRiskModel.predict_proba() -> Repayment Default Probability p in [0.0, 1.0]     │
│                                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Stage 1: Feature Engineering (`FeatureEngineer`)
Implemented in [`src/ml/features/feature_engineering.py`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py#L756-L895). Adds the 9 non-linear interaction features:
1. `feat_eng_vol_to_baseline`: $\frac{\text{CV}}{\text{median\_inc} / 10000 + 0.1}$
2. `feat_eng_downside_to_median`: $\frac{\sqrt{\max(\text{downside\_var}, 0)}}{\text{median\_inc} + 1.0}$
3. `feat_eng_vol_x_trend`: $\text{CV} \times (\text{momentum} - 1.0)$
4. `feat_eng_vol_to_bounceback`: $\frac{\text{CV}}{\text{bounceback\_ratio} + 0.1}$
5. `feat_eng_recovery_velocity`: $\frac{\text{bounceback\_ratio}}{\text{days\_to\_recover} / 7.0 + 1.0}$
6. `feat_eng_buffer_burn_coverage`: $\text{burn\_months} \times (\text{buffer\_to\_loan} + 0.1)$
7. `feat_eng_vol_cushion_ratio`: $\frac{\text{buffer\_to\_loan} + 0.1}{\text{CV} + 0.05}$
8. `feat_eng_dti_risk_multiplier`: $\text{total\_dti} \times (1.0 + \text{CV})$
9. `feat_eng_installment_floor_coverage`: $\frac{\text{p25\_inc}}{(\text{loan\_amount} / \max(\text{tenure}, 1.0)) + 1.0}$

### 3.2 Stage 2: Preprocessing (`CreditRiskPreprocessor`)
Implemented in [`src/ml/data/preprocessing.py`](file:///home/gnx/Projects/PARAKH/src/ml/data/preprocessing.py#L42-L345):
- Fitted strictly on the training partition ($N=8,012$).
- Imputes missing continuous features with training medians.
- Applies `RobustScaler` (median centering and interquartile range scaling).
- Encodes `gig_work_type` into 6 one-hot binary indicators.
- Encodes `loan_purpose` into 5 one-hot binary indicators.
- Enforces strict feature ordering matching `volatility_model.feature_names_in_`.

---

## 4. Input & Output Schemas

### 4.1 Required Input Schema (Pre-Transformation)

The model expects 46 raw and pre-derived fields per credit application:

#### A. Raw Application Inputs (6 fields)
- `requested_loan_amount`: float, loan principal in INR (₹5,000 to ₹50,000).
- `loan_tenure_months`: int, repayment tenure (3 to 24 months).
- `years_working`: float, years of active gig work experience.
- `average_working_days`: float, average monthly days actively working (5 to 30).
- `gig_work_type`: string, enum: `["DELIVERY", "FREELANCE_MICRO", "HOME_SERVICES", "LOGISTICS", "OTHER", "RIDE_HAILING"]`.
- `loan_purpose`: string, enum: `["EQUIPMENT_PURCHASE", "OTHER", "PERSONAL_EMERGENCY", "VEHICLE_MAINTENANCE", "WORKING_CAPITAL"]`.

#### B. Derived 90-Day Telemetry Features (40 fields)
- **Income Level & Distribution (8):** `feat_inc_median_90d`, `feat_inc_mean_90d`, `feat_inc_p25_90d`, `feat_inc_trimmed_mean`, `feat_inc_cv_90d`, `feat_inc_downside_var`, `feat_inc_iqr_ratio`, `feat_inc_min_max_ratio`.
- **Trend & Momentum (3):** `feat_trend_slope_90d`, `feat_trend_momentum_30_90`, `feat_trend_consec_drops`.
- **Activity & Working Patterns (4):** `feat_act_active_days_ratio`, `feat_act_zero_earn_weeks`, `feat_act_max_idle_streak`, `feat_act_weekend_intensity`.
- **Recovery & Resilience (3):** `feat_rec_bounceback_ratio`, `feat_rec_days_to_recover`, `feat_rec_max_drawdown`.
- **Liquidity & Cash Buffers (3):** `feat_liq_buffer_to_loan`, `feat_liq_burn_months`, `feat_liq_net_margin`.
- **Debt Service & Burden (4):** `feat_bur_dti_ratio`, `feat_bur_installment_dti`, `feat_bur_total_dti`, `feat_bur_loan_to_income`.
- **Platform Tenure & Reputation (4):** `feat_ten_years_working`, `feat_ten_platform_rating`, `feat_ten_trips_completed`, `feat_ten_cancellation_rate`.
- **Payment Discipline (3):** `feat_pay_utility_on_time`, `feat_pay_max_bill_delay`, `feat_pay_repay_reliability`.
- **Data Sufficiency (4):** `feat_suf_observed_days`, `feat_suf_payout_count`, `feat_suf_group_count`, `feat_suf_missing_ratio`.
- **Interaction Contracts (4):** `feat_int_vol_x_recovery`, `feat_int_vol_x_buffer`, `feat_int_trend_x_dti`, `feat_int_resilience_idx`.

---

### 4.2 Standardized Output Contract

The model produces a standardized assessment complying with [`PredictionResult`](file:///home/gnx/Projects/PARAKH/src/ml/models/prediction.py#L20-L188):

```json
{
  "model_name": "volatility-aware-risk-model",
  "model_version": "1.0.0",
  "application_id": "00447c00-e6a6-41f1-8403-7a92ca66e0c4",
  "applicant_profile_id": "56197905-d246-47fa-a97b-09d2a9d63f0e",
  "risk_probability": 0.0015,
  "score": 849,
  "risk_level": "LOWER",
  "is_insufficient_evidence": false,
  "confidence": 0.95,
  "key_factors": [
    "Living expense reserve runway presents an favorable pattern for credit assessment.",
    "Net cash retained after operating expenses presents an favorable pattern for credit assessment.",
    "Requested loan principal presents an elevated pattern for credit assessment."
  ],
  "explanation": {
    "base_value_log_odds": -4.861827,
    "top_risk_reducing_factors": [...],
    "top_risk_increasing_factors": [...]
  },
  "assessed_at": "2026-09-23T18:34:19.741367+00:00"
}
```

---

## 5. Decision Thresholds & Risk Tier Mapping

### 5.1 Diagnostic vs. Production Thresholds
- **Diagnostic Benchmark Threshold:** `0.50`
  - Used for standardized model comparisons, confusion matrices, and validation audits across Phases 5, 6, 7, and 8.
- **Production Lending Cutoff Status:** **PROVISIONAL / PROTOTYPE ONLY**.
  - 0.50 must **not** be automatically treated as a production lending cutoff. Commercial underwriting cutoffs depend on institution-specific risk appetite, loan product profitability, cost of capital, and loss reserve constraints.

### 5.2 Provisional Risk Tier Architecture

| Risk Tier | Probability Range | Presentation Score Range | Provisional Operational Guidance |
| :--- | :---: | :---: | :--- |
| **`LOWER`** | $p < 0.20$ | 740 – 850 | High confidence in repayment capacity; standard automated underwriting eligibility. |
| **`MODERATE`** | $0.20 \le p < 0.45$ | 603 – 739 | Moderate volatility or higher debt-to-income; eligible for smaller facility or secondary review. |
| **`HIGHER`** | $p \ge 0.45$ | 300 – 602 | Substantial risk of default; loan restructuring or conditional decline required. |
| **`INSUFFICIENT`** | N/A ($p = \text{null}$) | N/A ($\text{score} = \text{null}$) | Refused evaluation due to insufficient observation window ($<60$ days) or excessive missing data. |

> [!WARNING]
> **Provisional Tier Notice:** The risk tiers and threshold bounds above are provisional prototype guidelines defined in the Phase 0 specification. They do not constitute legally binding underwriting decisions or statutory credit decisions.

---

## 6. Insufficient-Data & Refusal Routing Protocol

In accordance with Phase 1 data contract rules:
1. **Quarantine from Scoring:** Applications that fail data sufficiency requirements ($N = 593$ in canonical dataset) are **never passed to the machine learning model**.
2. **Deterministic Routing:** When `feat_suf_observed_days < 60` or `feat_suf_missing_ratio > 0.40`:
   - `is_insufficient_evidence` is set to `True`.
   - `risk_probability` and `score` remain `None`.
   - `risk_level` is set strictly to `RiskTier.INSUFFICIENT`.
   - `missing_signal_guidance` is populated with specific instructions (e.g. *"Provide 60+ consecutive days of verified platform earnings telemetry"*).

---

## 7. Known Prototype Limitations & Safety Disclaimers

1. **Synthetic Data Domain:** The model was trained and evaluated on synthetic gig worker profiles. While behavioral distributions mimic real gig economy dynamics, empirical validation against bank transaction feeds and partner platform data is mandatory prior to live underwriting.
2. **Absence of Real Protected Attributes:** The synthetic population lacks verified protected demographic features (e.g., race, gender, age). The fairness audits performed in Phase 7 and Phase 8 evaluated behavioral cohort equity, not statutory compliance under the Equal Credit Opportunity Act (ECOA) or Fair Housing Act (FHA).
3. **Statistical Attribution, Not Causality:** Feature attributions (TreeSHAP) quantify mathematical relationships within the gradient-boosted trees. They do not represent physical causality.
4. **Frozen Model Integrity:** The model binary [`volatility_aware_risk_model.joblib`](file:///home/gnx/Projects/PARAKH/models/artifacts/volatility_aware_risk_model.joblib) is frozen and must not be retrained or altered during downstream backend integration.
