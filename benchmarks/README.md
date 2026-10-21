# PARAKH — Alternative Credit Assessment Benchmark Suite

This directory contains the authoritative, reproducible benchmarking pipeline for the **PARAKH Alternative Credit Assessment Platform**. It provides an independent, end-to-end evaluation auditing all performance, fairness, and portfolio impact claims comparing the **Phase 5 Linear Baseline** (`LogisticRegressionBaseline`) against the **Phase 6 Volatility-Aware Gradient-Boosted Model** (`VolatilityAwareRiskModel`).

---

## 1. Quick Start (Single Command Reproduction)

To execute the entire benchmark, verify frozen artifact digests, score the held-out test partition ($N = 1,698$), and regenerate all machine-readable reports, CSVs, and plots:

```bash
# Execute benchmark suite using the project environment
python benchmarks/run_benchmark.py
```

Optional flags:
```bash
# Run with custom config or custom output directory
python benchmarks/run_benchmark.py --config benchmarks/config.yaml --output-dir benchmarks/results
```

---

## 2. Benchmark Architecture & Integrity Controls

The benchmark executes strictly out-of-sample on the quarantined Phase 3 test split with the following invariants:
1. **Zero Retraining**: Frozen models (`logistic_regression_baseline.joblib` and `volatility_aware_risk_model.joblib`) and preprocessor (`credit_risk_preprocessor.joblib`) are loaded read-only; hashes are verified prior to execution.
2. **Zero Applicant Leakage**: Split is deterministically grouped by `applicant_profile_id` (Seed 42, 70/15/15 ratio) ensuring zero borrower overlap across train, validation, and test sets.
3. **Quarantine of Identifiers & Future Telemetry**: Feature matrices strictly exclude `application_id`, `applicant_profile_id`, `cutoff_timestamp`, and `target_default_flag`.
4. **Data Sufficiency Governance**: Unscored applications ($N = 87$ in test partition with $< 30$ active days or $< 4$ payouts) are responsibly quarantined without synthetic score imputation.
5. **Privacy & DPDP Compliance**: Zero statutory prohibited fields (bank credentials, raw UPI logs, contact books, GPS coordinates) are accepted or processed.

---

## 3. Resume Claims Audit & Empirical Reconciliation

| Resume Claim | Baseline Value | Candidate Value | Measured Absolute Delta | Measured Relative Change | Audit Status | Reconciliation Summary |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Evaluation Set Size: 1,698** | N/A | 1,698 | N/A | N/A | **VERIFIED** | Exact scored application rows in held-out test split (248 defaults, 14.61% default rate). |
| **Random Seed: 42** | N/A | 42 | N/A | N/A | **VERIFIED** | Frozen seed for deterministic grouped dataset partitioning and bootstrap sampling. |
| **Linear Baseline** | Logistic Regression | N/A | N/A | N/A | **VERIFIED** | `LogisticRegressionBaseline` with L2 penalty, StandardScaling, and 35 pre-$t_0$ features. |
| **PR-AUC Improvement: +0.93%** | 0.8680 | 0.8773 | **+0.0093 (+0.93 pp)** | **+1.07%** | **VERIFIED (Reporting Note)** | The resume reported the absolute gain (+0.0093 / +0.93 pp) formatted as a percentage. The relative gain is +1.07%. |
| **Distressed-Volatility Recall Gain: +3.81 pp** | 73.91% | 77.72% | **+3.81 pp** | **+5.15%** | **VERIFIED** | Evaluated on the distressed-volatile cohort ($N = 696$, defaults = 184) at 0.50 cutoff. |
| **Additional Loans Approved: 38** | 1,317 good | 1,355 good | **+38 good borrowers** | **+2.89%** | **VERIFIED (Denominator Note)** | 38 represents net additional *good borrowers* approved. Total approved loans expanded by +50 (1,393 vs 1,343). |
| **Good-Borrower Capture Improvement: +2.62%** | 90.83% | 93.45% | **+2.62 pp** | **+2.89%** | **VERIFIED (Reporting Note)** | Absolute percentage-point gain in good-borrower capture ($1355/1450 - 1317/1450$). Relative gain is +2.89%. |
| **Simulated Expected Loss Reduction: 16.17%** | ₹524.55 | ₹439.75 | **-₹84.80** | **-16.17%** | **VERIFIED** | Under policy cutoffs ($p < 0.20$ Approve) at 50% LGD per ₹1 Lakh exposure. (Invariant to LGD assumption). |

---

## 4. Methodology & Exact Mathematical Formulations

### 4.1 Precision-Recall Area Under Curve (PR-AUC)
Evaluated using scikit-learn's `average_precision_score`:
$$\text{AP} = \sum_{n} (R_n - R_{n-1}) P_n$$
Calculated directly on continuous predicted default probabilities and binary target default indicators.

### 4.2 Distressed-Volatility Cohort Recall
Identifies applicants exhibiting high earnings volatility combined with structural distress:
$$\text{Cohort}_{\text{Distressed}} = \{ i \mid \text{CV}_i > 0.22 \land (\text{Bounceback}_i < 0.90 \lor \text{DTI}_i > 0.35 \lor \text{BufferRatio}_i < 0.25) \}$$
Within this cohort ($N = 696$, 184 actual defaults):
$$\text{Recall}_{\tau=0.50} = \frac{\sum_{i \in \text{Defaults}} \mathbb{I}(\hat{p}_i \ge 0.50)}{184}$$
- Baseline: $136 / 184 = 73.91\%$
- Volatility-Aware: $143 / 184 = 77.72\%$
- Absolute Gain: $77.72\% - 73.91\% = \mathbf{+3.81 \text{ percentage points}}$ (+7 additional defaults caught).

### 4.3 Lending Decision Policy & Good-Borrower Capture
Operationalized under the three-tier policy:
- **Streamlined Approve**: $\hat{p} < 0.20$ (Presentation Score $> 740$)
- **Credit Adjudicator Review**: $0.20 \le \hat{p} < 0.45$ (Score $603 - 740$)
- **Statutory Adverse Action**: $\hat{p} \ge 0.45$ (Score $\le 602$)

Good-borrower capture is defined strictly against ground-truth non-defaulters ($y = 0$, $N = 1,450$):
$$\text{Capture Rate} = \frac{\sum_{i \in \text{Non-Defaults}} \mathbb{I}(\hat{p}_i < 0.20)}{1,450}$$
- Baseline Good Borrowers Approved: $1,317 / 1,450 = 90.8276\%$
- Volatility-Aware Good Borrowers Approved: $1,355 / 1,450 = 93.4483\%$
- Net Expansion: $1,355 - 1,317 = \mathbf{+38 \text{ good borrowers}}$
- Percentage-Point Gain: $93.4483\% - 90.8276\% = \mathbf{+2.6207 \text{ pp}}$

### 4.4 Expected Loss (EL) Simulation
Simulated portfolio risk for approved applicants across Loss Given Default scenarios ($LGD \in \{0.25, 0.50, 0.75\}$):
$$\text{Total Expected Loss} = \sum_{i \in \text{Approved}} \hat{p}_i \times \text{Exposure}_i \times LGD$$
$$\text{EL per ₹1 Lakh Approved Exposure} = \frac{\text{Total Expected Loss}}{\sum_{i \in \text{Approved}} \text{Exposure}_i} \times 100,000$$
At 50% LGD:
- Baseline: ₹524.55 per ₹1 Lakh
- Volatility-Aware: ₹439.75 per ₹1 Lakh
- Relative Reduction: $\frac{439.75 - 524.55}{524.55} \times 100\% = \mathbf{-16.166\% \approx -16.17\%}$

---

## 5. Artifact Directory Structure

```
benchmarks/
├── README.md               # Complete benchmark methodology and reproduction guide
├── config.yaml             # Reproducible execution configuration and artifact digests
├── metrics.py              # Pure metric calculation functions, loss formulas, and CI bootstrapping
├── run_benchmark.py        # Dedicated CLI entry point
└── results/
    ├── environment.txt     # Commit hash, hardware/OS, Python and library versions
    ├── summary.json        # Machine-readable audit results with claim verifications
    ├── summary.csv         # Formatted comparative metric summary table
    ├── raw/
    │   └── test_predictions.parquet  # Quarantined anonymized test predictions
    └── plots/
        ├── pr_curve.png              # Precision-Recall comparison curve
        ├── confusion_matrices.png    # Matched baseline and candidate confusion matrices
        └── expected_loss_simulation.png # Expected loss reduction across LGDs
```

---

## 6. Running Unit & Validation Tests

To execute the automated benchmark verification test suite:

```bash
# Run benchmark unit tests
pytest tests/benchmarks/ -v
```
