# PARAKH — Phase 2 ML Synthetic Data Handoff

## Status

Phase 2 synthetic credit-risk data pipeline is complete through P2-T11.

Branch:
`ml/synthetic-data`

Final dataset commit:
`cc7e87c` — `ml: generate synthetic credit risk dataset`

## Task Completion

- P2-T01 — Contract & repository analysis — COMPLETE
- P2-T02 — Generator architecture + schemas — COMPLETE
- P2-T03 — Applicant & cohort generator — COMPLETE
- P2-T04 — 90-day historical time-series generator — COMPLETE
- P2-T05 — Profile/loan/obligation signals — COMPLETE
- P2-T06 — Deterministic feature derivation — COMPLETE
- P2-T07 — Forward target/outcome generator — COMPLETE
- P2-T08 — Application-level dataset assembly — COMPLETE
- P2-T09 — Validation & leakage checks — COMPLETE
- P2-T10 — Final 12,000-row dataset — COMPLETE
- P2-T11 — Final QA/report — COMPLETE
- P2-T12 — Final Phase 2 handoff — IN PROGRESS

## Final Dataset

Canonical artifact:

`data/synthetic/synthetic_credit_applications.parquet`

Dataset size:

- 12,000 applications
- 10,000 unique applicants
- 11,407 scored applications
- 593 Insufficient Data applications
- 52 canonical columns
- 40 derived ML features

## Final Frozen Parameters

- Master seed: 42
- Loan multiple: Uniform(1.0, 1.75)
- Annual interest rate: 18%
- Loan amortization: reducing balance
- Tenure:
  - 6 months: 20%
  - 9 months: 30%
  - 12 months: 50%
- Living cost:
  - Base: ₹14,000/month
  - Log-normal sigma: 0.10
  - Bounds: ₹12,000–₹22,000
- Existing monthly debt:
  - 0.50 × current generated existing monthly debt
- Observation window: 90 days
- Prediction horizon: 30–90 days

No target relabeling, class rebalancing, clipping, or post-processing was used.

## Final Target Result

- Defaults: 1,486
- Scored default rate: 13.03%
- Deterministic-deficit rate: 17.42%

The observed scored default rate is within the authoritative 10–15% requirement.

## Validation

P2-T09 validation passed, including:

- Schema validation
- Identity and relational integrity
- Cohort validation
- Feature bounds and categorical domains
- Target validation
- Temporal validation
- Missingness validation
- Impossible-combination checks
- Leakage checks
- Deterministic reproducibility

Leakage checks cover post-t0 events, future-target influence, target-in-feature contamination, cutoff boundaries, and application isolation.

## Final QA

Full test suite:

`118 passed, 0 failed, 0 errors`

Dataset-specific validation confirms:

- Exact 12,000-row dataset
- Exact 10,000 unique applicants
- Required cohort distribution
- Repeat-applicant structure and spacing
- Deterministic generation
- Exact 52-column schema
- Full validation pass
- No future leakage
- Faithful default-rate calculation

## Integration Scope

Phase 2 work is limited to the ML synthetic-data/data-generation scope.

Backend and frontend application code were not intentionally modified as part of the Phase 2 synthetic dataset work.

## Handoff

The branch is ready for Pull Request review and integration into `main`.

No further parameter tuning or dataset regeneration should be performed unless explicitly authorized.
