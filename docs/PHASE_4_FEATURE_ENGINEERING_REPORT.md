# PARAKH — Phase 4 Feature Engineering Report

## Executive Summary

Phase 4 establishes the deterministic model-ready feature engineering layer for the PARAKH Alternative Credit Risk assessment platform. Operating directly on the Phase 3 validated canonical dataset (`data/synthetic/synthetic_credit_applications.parquet`), this layer operationalizes the **volatility-aware credit assessment paradigm**: distinguishing between healthy gig-income variability and structural financial deterioration through joint conditioning.

**Phase Status:** **`COMPLETED`** (170 tests passing, 0 leakage detected, bitwise deterministic execution).

---

## 1. Feature Architecture Overview

```
Raw Application DataFrame (52 cols)
  │
  ├── 1. Feature Lineage Registry (MASTER_LINEAGE: 55 tracked features)
  │
  ├── 2. Feature Engineering Layer (FeatureEngineer in src/ml/features/feature_engineering.py)
  │      ├── Input: 40 derived telemetry + 4 raw numeric + 2 raw categorical
  │      └── Output: 9 Newly Engineered Volatility-Aware Interaction Features (feat_eng_*)
  │
  ├── 3. Feature Subset Selection
  │      ├── BASELINE Feature Set: 26 features (classical underwriting signals)
  │      └── VOLATILITY_AWARE Feature Set: 55 features (full joint conditioning set)
  │
  └── 4. Model-Ready Matrix Generation (CreditRiskPreprocessor)
         ├── Train Split (70%): X_train (8,012 rows × 64 cols), y_train (8,012 labels)
         ├── Val Split (15%):   X_val   (1,697 rows × 64 cols), y_val   (1,697 labels)
         └── Test Split (15%):  X_test  (1,698 rows × 64 cols), y_test  (1,698 labels)
```

---

## 2. Feature Inventory Breakdown

| Feature Category | Count | Origin / Role |
| :--- | :--- | :--- |
| **Mandatory Core Derived Features** | 19 | Phase 2 telemetry extraction (income baseline, CV, trend, bounceback, DTI) |
| **Optional Derived Features** | 17 | Phase 2 telemetry extraction (activity streaks, ratings, margins, utility) |
| **Canonical Contract Interactions** | 4 | Contract-defined interactions (`feat_int_vol_x_recovery`, `feat_int_vol_x_buffer`, `feat_int_trend_x_dti`, `feat_int_resilience_idx`) |
| **Raw Numeric Context Inputs** | 4 | `requested_loan_amount`, `loan_tenure_months`, `years_working`, `average_working_days` |
| **Raw Categorical Inputs** | 2 | `gig_work_type` (6 categories), `loan_purpose` (5 categories) |
| **Newly Engineered Volatility Features** | **9** | **Phase 4 joint conditioning features (`feat_eng_*`)** |
| **Total Tracked Features** | **55** | Documented in `MASTER_LINEAGE` registry |
| **One-Hot Encoded Categories** | 11 | 6 (`gig_work_type`) + 5 (`loan_purpose`) dummy indicators |
| **Final Model Matrix ($\mathbf{X}$) Columns** | **64** | **53 continuous/ratio features + 11 categorical indicator features** |

---

## 3. The 9 Newly Engineered Volatility-Aware Features

Each engineered feature directly solves a specific failure mode of naive volatility scoring:

| Feature Name | Mathematical Formulation | Source Variables | Economic & Risk Rationale |
| :--- | :--- | :--- | :--- |
| `feat_eng_vol_to_baseline` | $\frac{\text{CV}}{\text{Median Income} / 10000.0 + 0.1}$ | `feat_inc_cv_90d`, `feat_inc_median_90d` | **Scale-Normalized Volatility:** Normalizes relative dispersion by absolute earning capacity. A CV of 0.35 on ₹40,000/mo income maintains massive insolvency buffer; the same CV on ₹6,000/mo threatens basic living costs. |
| `feat_eng_downside_to_median` | $\frac{\sqrt{\text{Downside Variance}}}{\text{Median Income} + 1.0}$ | `feat_inc_downside_var`, `feat_inc_median_90d` | **Downside Exposure Ratio:** Measures pure adverse shortfall risk (earnings below median) normalized against baseline income, ignoring benign upward surge variance. |
| `feat_eng_vol_x_trend` | $\text{CV} \times (\text{Momentum}_{30/90} - 1.0)$ | `feat_inc_cv_90d`, `feat_trend_momentum_30_90` | **Directional Volatility:** Disentangles expansion volatility from decay volatility. Positive momentum with high CV indicates growth surges (healthy); negative momentum indicates structural decline (distress). |
| `feat_eng_vol_to_bounceback` | $\frac{\text{CV}}{\text{Bounceback Ratio} + 0.1}$ | `feat_inc_cv_90d`, `feat_rec_bounceback_ratio` | **Unbuffered Volatility:** Volatility unmitigated by recovery elasticity. When post-shock bounceback is high ($\ge 1.2$), variance is safely absorbed; when bounceback is weak ($< 0.8$), variance signals vulnerability. |
| `feat_eng_recovery_velocity` | $\frac{\text{Bounceback Ratio}}{\text{Days to Recover} / 7.0 + 1.0}$ | `feat_rec_bounceback_ratio`, `feat_rec_days_to_recover` | **Recovery Velocity:** Magnitude of earnings rebound normalized per week elapsed from shock trough. Higher values denote rapid, elastic post-trough recovery. |
| `feat_eng_buffer_burn_coverage` | $\text{Burn Months} \times (\text{Buffer to Loan} + 0.1)$ | `feat_liq_burn_months`, `feat_liq_buffer_to_loan` | **Combined Liquidity Strength:** Multiplicative reserve metric combining runway duration (months of living cost reserves) with capital loan coverage. |
| `feat_eng_vol_cushion_ratio` | $\frac{\text{Buffer to Loan} + 0.1}{\text{CV} + 0.05}$ | `feat_liq_buffer_to_loan`, `feat_inc_cv_90d` | **Liquidity Cushion per Volatility Unit:** Quantifies capital buffer relative to degree of earnings variability. High cushion confirms ample liquidity insulation against earnings dips. |
| `feat_eng_dti_risk_multiplier` | $\text{Total DTI} \times (1.0 + \text{CV})$ | `feat_bur_total_dti`, `feat_inc_cv_90d` | **Compounding Debt Stress:** High debt service is manageable when earnings are stable (CV = 0.10), but causes immediate cashflow insolvency when earnings are highly erratic (CV = 0.60). |
| `feat_eng_installment_floor_coverage`| $\frac{\text{P25 Income}}{\text{Loan Amount} / \text{Tenure} + 1.0}$ | `feat_inc_p25_90d`, `requested_loan_amount`, `loan_tenure_months` | **Floor Installment Coverage:** Coverage of monthly loan installment during lean earning weeks (25th percentile). If coverage exceeds $2.0\times$ even at the floor, default risk is low regardless of top-line volatility. |

---

## 4. Experiment Variant Feature Subsets

To facilitate rigorous benchmarking in Phase 5 and Phase 6:

### A. Baseline Model Feature Set (26 Input Features $\to$ 35 Model Columns)
- **Features Included:** Linear earning indicators (`feat_inc_median_90d`, `feat_inc_mean_90d`, `feat_inc_p25_90d`), raw activity metrics (`feat_act_active_days_ratio`, `feat_act_zero_earn_weeks`, `feat_act_max_idle_streak`), platform tenure & ratings (`feat_ten_years_working`, `feat_ten_platform_rating`, `feat_ten_trips_completed`), debt ratios (`feat_bur_dti_ratio`, `feat_bur_installment_dti`, `feat_bur_total_dti`), liquid buffer, raw loan terms, and raw unconditioned CV (`feat_inc_cv_90d`).
- **Features Excluded:** All 4 contract interaction features (`feat_int_*`) and all 8 non-linear engineered volatility features (`feat_eng_vol_*`, `feat_eng_downside_*`, `feat_eng_buffer_*`).
- **Objective:** Establishes the traditional underwriting benchmark to quantify the value of volatility-aware conditioning.

### B. Volatility-Aware Feature Set (55 Input Features $\to$ 64 Model Columns)
- **Features Included:** All 40 canonical derived features + 4 raw numeric loan/profile features + 2 raw categorical features + all 9 newly engineered volatility interaction features.
- **Objective:** Supplies non-linear tree models (Random Forest, HistGradientBoosting, LightGBM) with the joint representations needed to resolve the behavioural interaction matrix.

---

## 5. Model-Ready Matrix Specifications

Generated deterministically via `build_model_ready_matrices()` on the 70/15/15 grouped split:

| Partition | Total Applications | Scored Applications | Unscored (Insufficient) | Matrix Shape ($\mathbf{X}$) | Defaults Count ($y=1$) | Default Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 8,412 | 8,012 | 400 | `(8012, 64)` | 1,024 | 12.78% |
| **Validation** | 1,803 | 1,697 | 106 | `(1697, 64)` | 214 | 12.61% |
| **Test** | 1,785 | 1,698 | 87 | `(1698, 64)` | 248 | 14.61% |
| **Total** | **12,000** | **11,407** | **593** | — | **1,486** | **13.03%** |

### Data Invariants & Anti-Leakage Verification
1. **Identifier Quarantine:** `applicant_profile_id`, `application_id`, `cutoff_timestamp`, and `cohort_archetype` are strictly excluded from $\mathbf{X}$.
2. **Target Isolation:** `target_default_flag` is isolated in ground-truth vector $\mathbf{y}$ and never used during feature construction.
3. **Temporal Invariance:** All 55 input features derive exclusively from historical events occurring strictly before application timestamp $t_0$.
4. **Fitting Isolation:** All scalers, imputers, and category dictionaries are fitted strictly on `train_df`. Validation and test splits only call `.transform()`.
5. **Zero Numerical Anomalies:** 0 NaNs, 0 Infs, 0 unhandled categories across all generated matrices.

---

## 6. Implementation Deliverables

1. [`src/ml/features/feature_engineering.py`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py):
   - [`FeatureLineageRecord`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py#L32): Dataclass encapsulating complete metadata and lineage for every feature.
   - [`FeatureEngineer`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py#L380): Scikit-learn compatible transformer computing the 9 volatility-aware features.
   - [`build_model_ready_matrices`](file:///home/gnx/Projects/PARAKH/src/ml/features/feature_engineering.py#L510): End-to-end matrix builder for baseline and volatility-aware experiments.
2. [`src/ml/features/__init__.py`](file:///home/gnx/Projects/PARAKH/src/ml/features/__init__.py): Public package exports.
3. [`tests/ml/test_phase4_feature_engineering.py`](file:///home/gnx/Projects/PARAKH/tests/ml/test_phase4_feature_engineering.py): Automated unit test suite covering determinism, zero denominators, trend conditioning, lineage completeness, and matrix integrity.
4. [`docs/PHASE_4_FEATURE_ENGINEERING_REPORT.md`](file:///home/gnx/Projects/PARAKH/docs/PHASE_4_FEATURE_ENGINEERING_REPORT.md): Complete Phase 4 technical documentation.
