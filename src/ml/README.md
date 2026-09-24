# PARAKH ML Package (`src/ml`)

## 1. Overview and Responsibility

This package implements the Machine Learning infrastructure for **PARAKH: Credit Score for the Invisible** (CX0506). The system performs privacy-preserving, volatility-aware alternative credit risk assessment for gig-economy workers who lack traditional formal credit bureau files.

### Person 3 ML Responsibility
Person 3 is responsible for:
- Model experimentation and evaluation infrastructure.
- Base risk model abstractions and prediction contracts.
- Probability-based, threshold-based, and calibration evaluation utilities.
- Cohort-specific performance auditing (Healthy Volatile, Stable, Declining, etc.).
- Experiment tracking and comparative benchmarking (Baseline vs. Volatility-Aware).
- Model-input data validation and leakage prevention boundaries.
- Explainability interfaces (SHAP integration in Phase 7).
- Subgroup fairness auditing across approved operational dimensions.
- Future model training and selection: Phase 5 (Baseline), Phase 6 (Volatility-Aware Model), Phase 8 (Model Selection), and Phase 9 (Inference Packaging).

---

## 2. Prepared ML Architecture and Module Organization

The experimentation infrastructure is organized into modular, independently testable components:

```
src/ml/
├── __init__.py                  # Central package exports
├── constants.py                 # Core enums, risk tiers, thresholds, and seeds
├── config.py                    # Workspace paths and deterministic seed configuration
│
├── models/                      # Model abstractions and output contracts
│   ├── __init__.py
│   ├── base.py                  # BaseRiskModel abstract base class & NotFittedError
│   └── prediction.py            # PredictionResult typed contract
│
├── evaluation/                  # Comprehensive evaluation framework
│   ├── __init__.py
│   ├── metrics.py               # ClassificationMetrics & evaluate_predictions
│   ├── calibration.py           # CalibrationResult, ECE, MCE & reliability curves
│   ├── cohorts.py               # evaluate_by_cohort for synthetic population segments
│   ├── comparison.py            # ModelComparisonResult & baseline benchmarking
│   ├── fairness.py              # FairnessAuditReport & subgroup parity auditing
│   └── tracking.py              # ExperimentMetadata serialization & persistence
│
├── data/                        # Model ingestion boundaries
│   ├── __init__.py
│   └── validation.py            # ModelDataValidator & identity leakage auditing
│
└── explainability/              # Explainability and attribution contracts
    ├── __init__.py
    └── base.py                  # BaseExplainer ABC & PlainLanguageTranslator
```

---

## 3. Core Frameworks and Workflows

### 3.1 Model Abstraction (`src/ml/models/base.py`)
All estimators inherit from [`BaseRiskModel`](file:///home/gnx/Projects/PARAKH/src/ml/models/base.py), enforcing a uniform contract:
- `fit(X, y)`: Fits the estimator on training features and binary labels.
- `predict_proba(X)`: Returns a 1D array of calibrated repayment default probabilities $P(\text{Default} \mid \mathbf{x}) \in [0.0, 1.0]$.
- `predict(X, threshold=0.5)`: Returns binary predictions $\{0, 1\}$. Raises `NotFittedError` if invoked before fitting.
- `get_metadata()`: Extracts standardized model provenance (name, version, hyperparameters, feature names).

### 3.2 Prediction Result Contract (`src/ml/models/prediction.py`)
Outputs are encapsulated in the typed [`PredictionResult`](file:///home/gnx/Projects/PARAKH/src/ml/models/prediction.py) dataclass, fully decoupled from backend ORM schemas:
- **Scored Outcomes:** Generates continuous calibrated default probabilities, monotonic presentation scores ($300\text{--}850$), risk tiers (`LOWER`, `MODERATE`, `HIGHER`), confidence metrics, and top driving factors.
- **Insufficient Evidence Outcomes:** When historical observation or signal diversity is truncated ($< 30\text{ days}$, $< 4\text{ payouts}$, or $< 2\text{ core signal groups}$), the contract short-circuits to `risk_level = INSUFFICIENT`, returning `score = None`, `risk_probability = None`, and actionable `missing_signal_guidance`.

### 3.3 Evaluation Workflow (`src/ml/evaluation/metrics.py`)
- Distinguishes probability-based metrics (ROC-AUC, PR-AUC, Brier score) from decision-threshold metrics (Precision, Recall, F1, Confusion Matrix).
- Handles edge cases robustly: single-class evaluation slices safely record a note and set ROC-AUC / PR-AUC to `None` without raising uncaught exceptions; zero-division scenarios in precision/recall are guarded with `zero_division=0`.

### 3.4 Calibration Workflow (`src/ml/evaluation/calibration.py`)
- Evaluates whether predicted probabilities represent true empirical frequencies via Brier score loss, Expected Calibration Error (ECE), and Maximum Calibration Error (MCE).
- Supports uniform (equal-width) and quantile (equal-frequency) probability binning.

### 3.5 Cohort Evaluation Workflow (`src/ml/evaluation/cohorts.py`)
- Evaluates the synthetic population cohorts defined in Phase 1: `Stable`, `Healthy Volatile`, `Declining`, `Irregular`, `High Obligation`, and `Insufficient Data`.
- Handles small cohorts and single-class distributions gracefully, returning sample counts alongside metrics. Cohort labels remain metadata and are never used as model training features.

### 3.6 Volatility-Aware Experiment Design (`src/ml/evaluation/comparison.py`)
Compares two specific experimental variants:
- **Experiment A (Baseline):** Standard risk modeling using linear volatility deductions.
- **Experiment B (Volatility-Aware):** Model conditioned on the joint interaction of volatility, recovery velocity, trend slope, and liquidity buffers.
- **Hypothesis Focus:** Directly tracks the `Healthy Volatile` and `Declining` cohorts to test whether healthy income variability is falsely penalized as default risk in the baseline, and whether the volatility-aware model successfully recovers viable gig borrowers while maintaining high recall on structural insolvency.

### 3.7 Experiment Tracking (`src/ml/evaluation/tracking.py`)
A lightweight, JSON-serializable [`ExperimentMetadata`](file:///home/gnx/Projects/PARAKH/src/ml/evaluation/tracking.py) schema records hyperparameters, dataset/feature versions, random seeds, training timestamps, global metrics, and cohort breakdowns without heavy external platforms.

### 3.8 Model-Input Validation (`src/ml/data/validation.py`)
Acts as an ingestion firewall for datasets delivered by Person 2:
- Verifies target presence and binary $\{0, 1\}$ or probability $[0, 1]$ constraints.
- Verifies that all expected feature columns are present and strictly numeric.
- Detects worker identity leakage across train, validation, and test splits using `applicant_profile_id`.

### 3.9 Explainability Boundary (`src/ml/explainability/base.py`)
Prepares interfaces for future SHAP-based local and global explanations:
- [`BaseExplainer`](file:///home/gnx/Projects/PARAKH/src/ml/explainability/base.py) defines the contract for local instance attribution and global feature ranking.
- Separates quantitative attributions (`FeatureContribution`) from plain-language translations ([`PlainLanguageTranslator`](file:///home/gnx/Projects/PARAKH/src/ml/explainability/base.py)), ensuring non-cryptic explanations for loan reviewers.

### 3.10 Subgroup Fairness Auditing (`src/ml/evaluation/fairness.py`)
Evaluates Demographic Parity Ratio (DPR) and Equal Opportunity Difference (EOD) across approved operational subgroups (e.g., `gig_work_type`, `tenure_group`). Prohibits collecting or inferring personal protected characteristics. Explicitly documents that synthetic fairness findings do not prove real-world human fairness.

---

## 4. How Future Phase 5 Consumes Person 2's Output

When Person 2 completes Phase 2 (Synthetic Data Generation), Phase 3 (Data Validation), and Phase 4 (Feature Engineering), Person 3 will consume the processed datasets through the following standardized workflow:

```
Person 2 Processed Dataset (CSV / Parquet in data/processed/)
                           │
                           ▼
  1. Ingestion Validation (ModelDataValidator.validate_training_dataframe)
                           │
                           ▼
  2. Identity Leakage Audit (ModelDataValidator.audit_split_leakage)
                           │
                           ▼
  3. Model Training (Phase 5 Baseline Logistic Regression; Phase 6 Volatility-Aware GBM)
                           │
                           ▼
  4. Probability & Threshold Evaluation (evaluate_predictions)
                           │
                           ▼
  5. Calibration Verification (evaluate_calibration -> ECE, MCE)
                           │
                           ▼
  6. Cohort Auditing (evaluate_by_cohort -> Healthy Volatile vs. Declining)
                           │
                           ▼
  7. Hypothesis Benchmark (compare_models -> Experiment A vs. Experiment B)
                           │
                           ▼
  8. Experiment Metadata Persistence (ExperimentMetadata.save_to_file in experiments/reports/)
```

---

## 5. What Is Intentionally Not Implemented in this Preparation Phase

In strict adherence to project phase boundaries:
- **No Data Generation:** No synthetic datasets were generated (belongs to Person 2 in Phase 2).
- **No Feature Engineering Implementation:** No feature calculation scripts were implemented (belongs to Person 2 in Phase 4).
- **No Model Training:** No estimators (Logistic Regression, LightGBM, XGBoost) were fitted or trained.
- **No Hyperparameter Optimization:** No grid search, random search, or tuning was executed.
- **No Arbitrary Thresholds:** Operational underwriting cutoffs are not hard-coded; prototype thresholds are documented as provisional and will be calibrated on validation ROC/PR curves in Phase 8.
- **No Backend/Frontend Modifications:** Backend and frontend source code remains completely untouched.

---

## 6. Running Tests

The ML preparation test suite uses pytest with in-memory fixtures:

```bash
.venv-ml/bin/pytest tests/ml -v
```
