# PARAKH — Phase 5 Baseline Model Report

## Executive Summary

Phase 5 establishes the first reproducible, interpretable credit-risk benchmark for the PARAKH Alternative Credit Assessment Platform. Operating on the frozen Phase 3 preprocessing pipeline and Phase 4 `BASELINE` feature subset (26 raw/derived underwriting features transformed into 35 model-ready numeric and categorical dummy columns), Phase 5 trains and evaluates a **Regularized L2 Logistic Regression** classifier.

This baseline model establishes the empirical performance floor, verifies directional signal validity, and provides an audited point of comparison for the upcoming Phase 6 Volatility-Aware non-linear models.

**Phase Status:** **`COMPLETED`** (183 repository tests passing, zero leakage detected, bitwise deterministic execution).

### Key Performance Summary (Validation Split, N = 1,697)

| Metric Category | Metric | Baseline Value | Standard Target | Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Discrimination** | **ROC-AUC** | **0.9725** | $\ge 0.8500$ | Excellent global pairwise separation |
| **Discrimination** | **PR-AUC (Avg Precision)** | **0.8778** | $\ge 0.7000$ | Robust minority default detection |
| **Probability Calibration** | **Brier Score** | **0.0375** | $\le 0.0800$ | High mean squared probability accuracy |
| **Probability Calibration** | **Expected Calibration Error (ECE)** | **0.0149 (1.49%)** | $\le 0.0500$ | Predicted probabilities closely match observed default rates |
| **Classification (@ 0.50)** | **Precision** | **0.8659** | $\ge 0.7500$ | 86.6% of flagged defaulters actually default |
| **Classification (@ 0.50)** | **Recall** | **0.7243** | $\ge 0.7000$ | Captures 72.4% of all default occurrences |
| **Classification (@ 0.50)** | **F1-Score** | **0.7888** | $\ge 0.7000$ | Strong harmonic balance at standard cutoff |

---

## 1. Baseline Model Specification & Architecture

```
                                  PARAKH ML PIPELINE (PHASE 5)
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                                  │
│   Phase 2 Canonical Synthetic Applications (12,000 records / 10,000 unique applicants)           │
│                                           │                                                      │
│                                           ▼                                                      │
│   Applicant-Grouped Splitter (seed=42) ──► Train (70%) | Val (15%) | Test (15% strictly held out)│
│                                           │                                                      │
│                                           ▼                                                      │
│   CreditRiskPreprocessor (fit on Train) ──► Scaler (Robust), Imputer (Median), One-Hot Encoder   │
│                                           │                                                      │
│                                           ▼                                                      │
│   Phase 4 BASELINE Feature Subset Selection (26 features -> 35 model-ready columns)              │
│                                           │                                                      │
│                                           ▼                                                      │
│   LogisticRegressionBaseline Wrapper (L2 penalty, lbfgs solver, max_iter=1000, random_state=42) │
│                                           │                                                      │
│                                           ▼                                                      │
│   Validation Set Evaluation ─────────────► Discrimination, Calibration, Cohort Audit, Reporting  │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Mathematical Formulation
The baseline model is parameterized as a regularized binary logistic regression model with the standard logit link:

$$P(\text{Default} = 1 \mid \mathbf{x}) = \sigma(\mathbf{w}^T \mathbf{x} + b) = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{x} + b)}}$$

Optimization minimizes the L2-penalized negative log-likelihood (cross-entropy loss) on the scored training set:

$$\min_{\mathbf{w}, b} \left\{ \frac{1}{2} \|\mathbf{w}\|_2^2 + C \sum_{i=1}^{N_{\text{train}}} \left[ - y_i \log(\hat{p}_i) - (1 - y_i) \log(1 - \hat{p}_i) \right] \right\}$$

where:
- $\mathbf{x} \in \mathbb{R}^{35}$ represents the model-ready feature vector.
- $y_i \in \{0, 1\}$ is the ground-truth default indicator (`target_default_flag`).
- $C = 1.0$ is the inverse regularization strength selected through validation tuning.
- Solver: deterministic Limited-memory BFGS (`lbfgs`) with convergence tolerance $10^{-4}$ and maximum 1,000 iterations.
- Prior calibration: `class_weight=None` is maintained to keep predicted probabilities anchored to the empirical default prior (~12.8%) without artificial skewing.

### 1.2 Feature Dimension & Composition
The baseline model consumes strictly the Phase 4 `BASELINE` feature set:
- **Total Input Features Before Encoding:** 26 features.
- **Model-Ready Matrix Columns:** 35 columns:
  - **24 Continuous & Ratio Features:** Core income baselines (`feat_inc_median_90d`, `feat_inc_mean_90d`, `feat_inc_p25_90d`), raw unconditioned coefficient of variation (`feat_inc_cv_90d`), activity indicators (`feat_act_active_days_ratio`, `feat_act_zero_earn_weeks`, `feat_act_max_idle_streak`), platform tenure & metrics (`feat_ten_years_working`, `feat_ten_platform_rating`, `feat_ten_trips_completed`), payment metrics (`feat_pay_utility_on_time`, `feat_pay_repay_reliability`), debt service ratios (`feat_bur_dti_ratio`, `feat_bur_installment_dti`, `feat_bur_total_dti`), sufficiency markers (`feat_suf_observed_days`, `feat_suf_payout_count`), loan profile inputs (`requested_loan_amount`, `loan_tenure_months`, `years_working`, `average_working_days`), liquidity indicators (`feat_liq_buffer_to_loan`, `feat_liq_burn_months`), and installment floor coverage (`feat_eng_installment_floor_coverage`).
  - **11 One-Hot Categorical Indicators:** 6 sectors (`gig_work_type_DELIVERY`, `FREELANCE_MICRO`, `HOME_SERVICES`, `LOGISTICS`, `OTHER`, `RIDE_HAILING`) and 5 loan purposes (`loan_purpose_EQUIPMENT_PURCHASE`, `OTHER`, `PERSONAL_EMERGENCY`, `VEHICLE_MAINTENANCE`, `WORKING_CAPITAL`).
- **Explicitly Excluded:** All 4 contract interaction features (`feat_int_*`) and all 8 non-linear engineered volatility features (`feat_eng_vol_*`, `feat_eng_downside_*`, `feat_eng_buffer_*`).

---

## 2. Training Protocol & Hyperparameter Selection

### 2.1 Dataset Partitioning & Anti-Leakage Protocol
Data partitioning adheres strictly to the grouped strategy established in Phase 3:
- Applications belonging to the same applicant are grouped strictly by `applicant_profile_id` (PRNG seed 42) to eliminate intra-applicant information leakage.
- **Unscored Records Quarantine:** All 593 records belonging to the Insufficient Data cohort (`target_default_flag` is null) are quarantined and excluded from training and validation folds.
- **Test Set Quarantine:** The test partition (1,698 scored records) is strictly held out and completely unobserved during model training, tuning, and threshold selection.

| Split Name | Total Records | Scored Records | Quarantined Unscored | Defaults ($y=1$) | Default Rate | Role in Phase 5 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 8,412 | **8,012** | 400 | 1,024 | 12.78% | Model coefficient estimation |
| **Validation** | 1,803 | **1,697** | 106 | 214 | 12.61% | Hyperparameter tuning & benchmark evaluation |
| **Test** | 1,785 | **1,698** | 87 | 248 | 14.61% | **STRICTLY HELD OUT (Unobserved)** |
| **Total** | **12,000** | **11,407** | **593** | **1,486** | **13.03%** | Canonical dataset |

### 2.2 Hyperparameter Tuning Sweep (Validation Set Only)
A grid sweep of the inverse regularization strength $C$ was performed exclusively on the validation split:

| $C$ Value | Validation ROC-AUC | Validation PR-AUC | Validation Brier Score | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `0.001` | 0.9396 | 0.6454 | 0.0716 | Heavy underfitting, over-regularized |
| `0.010` | 0.9679 | 0.8516 | 0.0465 | Strong regularizer |
| `0.050` | 0.9719 | 0.8744 | 0.0394 | Approaching optimum |
| `0.100` | 0.9723 | 0.8770 | 0.0382 | Balanced regularization |
| `0.500` | 0.9725 | 0.8776 | 0.0375 | Optimal zone |
| **`1.000`** | **0.9725** | **0.8778** | **0.0375** | **Optimal validation PR-AUC & Brier score (Selected)** |
| `2.000` | 0.9724 | 0.8772 | 0.0377 | Stable performance |
| `5.000` | 0.9722 | 0.8765 | 0.0378 | Slight variance increase |
| `10.000` | 0.9722 | 0.8767 | 0.0379 | Minimal regularization |
| `50.000` | 0.9721 | 0.8761 | 0.0380 | Near-unconstrained MLE |
| `100.000` | 0.9721 | 0.8761 | 0.0380 | Unconstrained MLE |

**Selected Configuration:** $C = 1.0$ achieves the highest PR-AUC (0.8778), tied for highest ROC-AUC (0.9725), and lowest Brier score (0.0375).

---

## 3. Comprehensive Validation Performance Analysis

### 3.1 Primary Diagnostic Evaluation (Threshold = 0.50)
At the standard diagnostic cutoff $\tau = 0.50$:

```
                             PREDICTED CLASS
                       Non-Default (0)   Default (1)
ACTUAL   Non-Default        1,459             24        (TN = 1459, FP = 24)
CLASS    Default               59            155        (FN = 59,   TP = 155)
```

- **Accuracy:** 95.11% (1,614 / 1,697)
- **Precision:** 86.59% (155 / 179)
- **Recall:** 72.43% (155 / 214)
- **Specificity:** 98.38% (1,459 / 1,483)
- **False Positive Rate:** 1.62% (24 / 1,483)
- **F1-Score:** 0.7888

### 3.2 Decision Threshold Sensitivity Sweep
To evaluate operational trade-offs across various lending risk appetites, performance was audited across a decision threshold grid:

| Threshold ($\tau$) | Precision | Recall | F1-Score | True Positives | False Positives | False Negatives | Operational Implication |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0.10` | 0.5515 | 0.9252 | 0.6911 | 198 | 161 | 16 | Conservative / High Protection (Catches 92.5% of defaults) |
| `0.13` (Prior) | 0.5957 | 0.9159 | 0.7219 | 196 | 133 | 18 | Base Rate Aligned (Near-optimal default sensitivity) |
| `0.20` | 0.6989 | 0.8785 | 0.7785 | 188 | 81 | 26 | Balanced Underwriting Cutoff |
| `0.30` | 0.7532 | 0.8131 | 0.7820 | 174 | 57 | 40 | Low False-Positive Operational Window |
| `0.40` | 0.7970 | 0.7523 | 0.7740 | 161 | 41 | 53 | Moderate Risk Cutoff |
| **`0.50`** | **0.8659** | **0.7243** | **0.7888** | **155** | **24** | **59** | **Standard Diagnostic Benchmark** |
| `0.60` | 0.8957 | 0.6822 | 0.7745 | 146 | 17 | 68 | High-Conviction Default Identification |
| `0.70` | 0.9220 | 0.6075 | 0.7324 | 130 | 11 | 84 | Extremely Strict Flagging |
| `0.80` | 0.9554 | 0.5000 | 0.6564 | 107 | 5 | 107 | Near-Zero False Positive Tolerance |

> [!NOTE]
> The thresholds reported above are diagnostic evaluations. Final production lending thresholds are policy decisions owned by credit risk committees and are out of scope for Phase 5.

---

## 4. Probability Calibration Analysis

Accurate credit assessment requires predicted probabilities to mirror true empirical default frequencies. Calibration was evaluated using 10 equal-width uniform decile bins on the validation split.

### 4.1 Calibration Reliability Table

| Bin Index | Probability Range | Sample Count | Mean Predicted $\hat{p}$ | Observed Default Rate | Absolute Gap | Reliability Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0** | `[0.00, 0.10]` | 1,338 | 0.0093 (0.93%) | 0.0120 (1.20%) | 0.0027 | Perfectly Calibrated |
| **1** | `[0.10, 0.20]` | 90 | 0.1435 (14.35%) | 0.1111 (11.11%) | 0.0324 | Well Calibrated |
| **2** | `[0.20, 0.30]` | 38 | 0.2486 (24.86%) | 0.3684 (36.84%) | 0.1198 | Slight Underestimation |
| **3** | `[0.30, 0.40]` | 29 | 0.3455 (34.55%) | 0.4483 (44.83%) | 0.1028 | Slight Underestimation |
| **4** | `[0.40, 0.50]` | 23 | 0.4578 (45.78%) | 0.2609 (26.09%) | 0.1969 | Small Sample Dispersion |
| **5** | `[0.50, 0.60]` | 16 | 0.5540 (55.40%) | 0.5625 (56.25%) | 0.0085 | Perfectly Calibrated |
| **6** | `[0.60, 0.70]` | 22 | 0.6479 (64.79%) | 0.7273 (72.73%) | 0.0794 | Well Calibrated |
| **7** | `[0.70, 0.80]` | 29 | 0.7530 (75.30%) | 0.7931 (79.31%) | 0.0401 | Well Calibrated |
| **8** | `[0.80, 0.90]` | 39 | 0.8621 (86.21%) | 0.9487 (94.87%) | 0.0866 | Well Calibrated |
| **9** | `[0.90, 1.00]` | 73 | 0.9630 (96.30%) | 0.9589 (95.89%) | 0.0041 | Perfectly Calibrated |

### 4.2 Calibration Error Summary
- **Expected Calibration Error (ECE - Uniform):** **0.0149 (1.49%)**
- **Expected Calibration Error (ECE - Quantile):** **0.0210 (2.10%)**
- **Maximum Calibration Error (MCE):** **0.1969 (Bin 4)**
- **Brier Score:** **0.0375**

**Interpretation:** The baseline model exhibits strong natural probability calibration across the majority of the population. Over 78% of the validation population falls into Bin 0 ($[0.00, 0.10]$), where predicted default risk (0.93%) closely matches observed default frequency (1.20%). The highest risk bin ($[0.90, 1.00]$) has a mean predicted probability of 96.30% against an empirical default rate of 95.89%.

---

## 5. Borrower Cohort Segmented Performance Audit

Performance was audited independently across each of the 5 scored behavioral cohorts on the validation set:

| Cohort Name | Sample Count ($N$) | Defaults ($y=1$) | Empirical Default Rate | Cohort ROC-AUC | Cohort PR-AUC | Cohort Brier Score | Behavioral Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Declining** | 382 | 118 | 30.89% | **0.9554** | **0.9127** | 0.0769 | Structural income deterioration, degrading rating |
| **Healthy Volatile** | 465 | 3 | 0.65% | **0.9589** | **0.2804** | 0.0073 | High CV, rapid bounceback, adequate buffer |
| **High Obligation** | 170 | 11 | 6.47% | **0.8954** | **0.6309** | 0.0363 | Healthy earnings, elevated DTI $> 0.50$ |
| **Irregular** | 249 | 78 | 31.33% | **0.9375** | **0.8981** | 0.0916 | Erratic payouts, prolonged idle streaks, low buffer |
| **Stable** | 431 | 4 | 0.93% | **0.9977** | **0.8167** | 0.0045 | Stationary earnings, high activity, low CV |
| **Total Scored** | **1,697** | **214** | **12.61%** | **0.9725** | **0.8778** | **0.0375** | Full validation partition |

### 5.1 Critical Behavioral Insights & Phase 6 Motivation
1. **Separation of Macro Distress (Declining & Irregular):** The baseline linear model successfully isolates macro distress indicators (ROC-AUC $> 0.93$ for both Declining and Irregular cohorts). Earning trends, total working days, and liquidity burn months serve as strong linear signals.
2. **The Healthy Volatile Challenge:** While overall ROC-AUC within the Healthy Volatile cohort appears high (0.9589), the low base default rate (0.65%, 3 defaults out of 465 workers) yields a PR-AUC of 0.2804. Because the linear model only has access to raw `feat_inc_cv_90d` without joint conditioning on recovery bounceback or liquidity cushions, it cannot differentiate an upward growth surge from an unbuffered dip.
3. **Motivation for Phase 6:** This precise limitation validates the core PARAKH hypothesis: non-linear tree models equipped with the 9 volatility interaction features are needed to prevent penalizing healthy variable earners while maintaining high sensitivity to genuine structural insolvency.

---

## 6. Interpretability & Feature Importance (Coefficients & Odds Ratios)

The model intercept is **$-5.7380$**, reflecting the low prior default log-odds of a healthy gig worker at baseline feature means.

### 6.1 Feature Weights and Odds Ratios (Top 15 Predictors)

| Rank | Feature Name | Coefficient ($\beta$) | Absolute Weight ($|\beta|$) | Odds Ratio ($e^\beta$) | Risk Impact & Economic Rationale |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `feat_liq_burn_months` | **-4.4631** | 4.4631 | **0.0115** | **Strongly Protective:** Each unit increase in living cost reserves reduces odds of default by ~98.8%. |
| **2** | `feat_inc_mean_90d` | **-4.0226** | 4.0226 | **0.0179** | **Strongly Protective:** Absolute earning capacity provides substantial protection against default. |
| **3** | `requested_loan_amount` | **-2.7839** | 2.7839 | **0.0618** | **Protective Direction:** Standardized loan amount scaled against high-tenure workers with verified earning baselines. |
| **4** | `average_working_days` | **-2.2381** | 2.2381 | **0.1067** | **Protective:** Consistent platform engagement strongly reduces credit risk. |
| **5** | `feat_ten_trips_completed` | **+1.5580** | 1.5580 | **4.7492** | **Risk Correlation:** Correlated with high-activity but over-extended full-time gig workers with high operating costs. |
| **6** | `feat_eng_installment_floor_coverage` | **-1.1050** | 1.1050 | **0.3312** | **Protective:** Having ample coverage of monthly EMI during 25th percentile lean weeks cuts default odds by 66.9%. |
| **7** | `feat_act_active_days_ratio` | **+0.9797** | 0.9797 | **2.6637** | **Marginal Stress Marker:** Active days ratio in interaction with hours worked captures gig worker strain. |
| **8** | `feat_liq_buffer_to_loan` | **+0.7677** | 0.7677 | **2.1548** | **Linear Artifact:** Linear model proxy for debt exposure relative to liquid balance without non-linear interaction. |
| **9** | `feat_inc_median_90d` | **+0.6731** | 0.6731 | **1.9603** | **Linear Collinearity:** Collinear compensation against `feat_inc_mean_90d` ($\beta = -4.02$). |
| **10** | `feat_bur_total_dti` | **+0.4923** | 0.4923 | **1.6360** | **Risk Driver:** Total debt service obligations increase default odds by 63.6% per unit increase. |
| **11** | `loan_purpose_OTHER` | **-0.4349** | 0.4349 | **0.6473** | **Protective:** Lower relative risk compared to emergency or vehicle maintenance purposes. |
| **12** | `feat_bur_installment_dti` | **+0.3937** | 0.3937 | **1.4824** | **Risk Driver:** Existing monthly installment obligations increase repayment default probability. |
| **13** | `feat_bur_dti_ratio` | **+0.3767** | 0.3767 | **1.4575** | **Risk Driver:** Debt-to-income ratio elevation increases risk. |
| **14** | `gig_work_type_OTHER` | **+0.3177** | 0.3177 | **1.3740** | **Sector Difference:** Slight risk increase relative to primary delivery / logistics platforms. |
| **15** | `loan_purpose_WORKING_CAPITAL` | **+0.2808** | 0.2808 | **1.3241** | **Risk Driver:** Borrowers requiring working capital loans display higher default incidence than equipment purchase. |

---

## 7. Anti-Leakage & Governance Invariants Verification

All five anti-leakage invariants specified in `docs/ml-specification.md` Section 16 have been rigorously verified:

| Invariant ID | Invariant Name | Implementation Mechanism | Verification Result |
| :--- | :--- | :--- | :--- |
| **INV-1** | **Temporal Horizon** | Feature inputs strictly derive from historical telemetry $t < t_0$. | **PASSED** (Enforced by Phase 2 generator and Phase 4 pipeline) |
| **INV-2** | **Target Window** | Target `target_default_flag` evaluated strictly in $(t_0, t_0 + T_{\text{pred}}]$ and isolated from $\mathbf{X}$. | **PASSED** (0 target or label columns present in model feature matrix) |
| **INV-3** | **Simulation Independence** | Causal sequential timeline; features constructed independently of forward target outcomes. | **PASSED** (Frozen canonical dataset preserved unchanged) |
| **INV-4** | **Pre-Processing Fit** | `CreditRiskPreprocessor` fit strictly on `X_train`. Validation and test only call `.transform()`. | **PASSED** (Preprocessor fit on 8,012 training rows only) |
| **INV-5** | **Cross-Entity Identity** | Grouped splitting ensures all applications per applicant remain in the same split partition. | **PASSED** (Zero applicant profile ID overlap across train, val, and test splits) |
| **INV-6** | **Test Set Quarantine** | Test partition (1,698 scored records) strictly held out and unobserved. | **PASSED** (Zero test set records used in tuning or thresholding) |

---

## 8. Artifact Registry & Deliverables

All generated Phase 5 baseline model artifacts have been validated and saved to their canonical project locations:

| Artifact Path | Artifact Type | Format | Content & Purpose |
| :--- | :--- | :--- | :--- |
| `models/artifacts/logistic_regression_baseline.joblib` | Model Binary | Joblib | Serialized `LogisticRegressionBaseline` fitted model artifact |
| `models/artifacts/logistic_regression_baseline_metadata.json` | Provenance Metadata | JSON | Model hyperparameters, training metadata, feature list (35), intercept, coefficients |
| `experiments/reports/phase5_baseline_metrics.json` | Core Validation Metrics | JSON | Primary validation metrics (ROC-AUC, PR-AUC, Brier score, ECE, precision, recall, F1, confusion matrix) |
| `experiments/reports/phase5_baseline_evaluation.json` | Comprehensive Evaluation | JSON | Full evaluation report (tuning sweep, multi-threshold sweep, calibration bins, cohort breakdown) |
| `experiments/reports/phase5_validation_predictions.parquet` | Scored Validation Records | Parquet | 1,697 scored validation rows with application IDs, predicted default probabilities, risk tiers, and 300-850 scores |

---

## 9. Benchmark Reference for Phase 6 (Volatility-Aware Models)

Phase 5 establishes the formal benchmark floor for Phase 6:

1. **Selection Rule:** A non-linear tree model (Random Forest, HistGradientBoosting, LightGBM) will only be promoted over the baseline if it achieves:
   - Statistically significant improvement in ROC-AUC ($\Delta \ge +0.02$).
   - Noticeable improvement in PR-AUC ($\Delta \ge +0.03$), specifically within the Healthy Volatile cohort.
   - Preserved or improved probability calibration ($\text{ECE} \le 0.02$).
2. **Feature Set Comparison:** Phase 6 will benchmark models trained on the 35 `BASELINE` features versus the 64 `VOLATILITY_AWARE` features to quantify the explicit value added by the 9 newly engineered volatility interaction features.
