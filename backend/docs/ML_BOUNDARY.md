# PARAKH ML-Ready Boundary Integration Guide

This document defines the technical integration contracts for **Person 2 (Feature Engineering)** and **Person 3 (ML Models)** to plug their implementations into PARAKH without altering frontend code, REST API endpoints, or PostgreSQL database tables.

---

## Architecture Overview

```
Raw Financial Signals (persisted in DB)
        ↓
Person 2: FeaturePipeline (app.assessment.pipeline.FeaturePipeline)
        ↓
AssessmentInput (app.assessment.schemas.AssessmentInput)
        ↓
Person 3: MLModel (app.assessment.ml_engine.MLModel)
        ↓
MLAssessmentEngine (app.assessment.ml_engine.MLAssessmentEngine)
        ↓
AssessmentResult (app.assessment.schemas.AssessmentResult)
        ↓
AssessmentService.create_assessment()
        ↓
CreditAssessment (SQLAlchemy model -> PostgreSQL table: credit_assessments)
        ↓
POST /api/v1/applications/{application_id}/assess (unchanged)
        ↓
@parakh/api + Adapters + Next.js UI (unchanged)
```

---

## 1. Engine Configuration & Selection

Assessment engine selection is driven by environment configuration (`Settings.ASSESSMENT_ENGINE`):

```bash
# In .env or production environment:
ASSESSMENT_ENGINE=mock   # Active default (MockAssessmentEngine)
# or
ASSESSMENT_ENGINE=ml     # Production ML mode (MLAssessmentEngine)
```

- **Default**: `"mock"` points to `MockAssessmentEngine`.
- **Factory**: `app.assessment.factory.create_assessment_engine()` resolves the engine based on configuration.
- **Dependency**: FastAPI `get_assessment_engine()` dependency automatically injects the configured engine.

---

## 2. Person 2: Feature Pipeline Boundary

Person 2 implements feature extraction by subclassing `app.assessment.pipeline.FeaturePipeline`:

```python
from typing import Any, Dict, Optional, Sequence
from app.assessment.pipeline import FeaturePipeline
from app.assessment.schemas import _check_for_prohibited_keys

class CustomFeaturePipeline(FeaturePipeline):
    """Person 2's engineered feature calculation pipeline."""

    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        features: Dict[str, Any] = {}

        # 1. Compute statistical aggregations over signals sequence
        # Example: rolling cashflow ratios, earnings trends, volatility indicators

        # 2. Extract application / profile metadata if applicable

        # 3. Data minimization: Ensure no prohibited keys are introduced
        _check_for_prohibited_keys(features)

        return features
```

### Data Minimization Compliance
The feature pipeline **must never** emit fields in `PROHIBITED_FIELDS`:
- Bank account credentials, passwords, raw bank statements, raw UPI logs, UPI VPA
- Raw transactions, merchant names, location history, GPS coordinates, contacts

Features returned by `extract_features` are injected into `AssessmentInput.derived_features`.

---

## 3. Person 3: ML Model Boundary

Person 3 implements the trained scoring model (LightGBM, XGBoost, Logistic Regression) by subclassing `app.assessment.ml_engine.MLModel`:

```python
from decimal import Decimal
from app.assessment.ml_engine import MLModel, MLModelOutput
from app.assessment.schemas import AssessmentInput
from app.models.assessment import RiskLevel

class ProductionCreditModel(MLModel):
    """Person 3's trained LightGBM / XGBoost / Logistic Regression model."""

    @property
    def model_name(self) -> str:
        return "lightgbm-credit-v1"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    def predict(self, input_data: AssessmentInput) -> MLModelOutput:
        # Access engineered features from input_data.derived_features
        # and standard domain inputs:
        # input_data.requested_loan_amount, input_data.average_income, etc.

        # Run inference:
        risk_probability = Decimal("0.1450")  # Model estimated PD [0, 1]
        confidence = Decimal("0.8900")        # Model confidence [0, 1]
        credit_score = 735                    # Alternative credit score [0, 1000]

        return MLModelOutput(
            risk_probability=risk_probability,
            confidence=confidence,
            credit_score=credit_score,
            risk_level=RiskLevel.LOWER,
            key_factors=[
                "Stable platform tenure",
                "High payment regularity",
            ],
            explanation={
                "shap_values": {"income_volatility": -0.12, "payment_regularity": 0.25},
            },
            debt_to_income=Decimal("0.22"),
            utilization=Decimal("0.18"),
            income_stability=Decimal("0.88"),
            repayment_reliability=Decimal("0.94"),
        )
```

### Registration with MLAssessmentEngine
Plug the model into `MLAssessmentEngine`:
```python
from app.assessment.ml_engine import MLAssessmentEngine

model = ProductionCreditModel()
engine = MLAssessmentEngine(model=model)
```

If `MLAssessmentEngine` is invoked without a registered model, it raises `AssessmentNotImplementedError`, which FastAPI maps to `HTTP 501 Not Implemented`.

---

## 4. Contract Output & Database Mapping

`MLAssessmentEngine` maps `MLModelOutput` into the canonical `AssessmentResult`.
`AssessmentResult` maps directly to `CreditAssessmentCreate` and the PostgreSQL `credit_assessments` table:

| Model Output Field | Domain AssessmentResult | DB Column (`credit_assessments`) | API Response (`CreditAssessmentResponse`) |
|:---|:---|:---|:---|
| `credit_score` | `score` | `credit_score` (Integer) | `score` / `credit_score` |
| `risk_probability` | `risk_probability` | `risk_probability` (Numeric 5,4) | `risk_probability` |
| `risk_level` | `risk_level` | `risk_level` (Enum String) | `risk_level` |
| `confidence` | `confidence` | `confidence` (Numeric 5,4) | `confidence` |
| `debt_to_income` | `debt_to_income` | `debt_to_income` (Numeric 6,4) | `debt_to_income` |
| `utilization` | `utilization` | `utilization` (Numeric 6,4) | `utilization` |
| `income_stability` | `income_stability` | `income_stability` (Numeric 5,4) | `income_stability` |
| `repayment_reliability` | `repayment_reliability` | `repayment_reliability` (Numeric 5,4) | `repayment_reliability` |
| `key_factors` | `key_factors` | Transient / Model Version metadata | `key_factors` (List[str]) |
| `explanation` | `explanation` | Transient / Model Version metadata | `explanation` (Dict[str, Any]) |
| `model_name` | `model_name` | Linked via `model_versions` FK | `model_name` (String) |
| `model_version` | `model_version` | Linked via `model_versions` FK | `model_version` (String) |

---

## 5. Stable API & Frontend Guarantees

The following contracts remain 100% frozen:
- **API Endpoint**: `POST /api/v1/applications/{application_id}/assess`
- **Frontend SDK**: `api.triggerAssessment(applicationId)`
- **Adapter**: `adaptAssessment(rawAssessment)` in `@parakh/api`
- **UI Surfaces**: Applicant Results (`/user/results/[id]`), Reviewer Dossier (`/admin/applications/[id]`), Admin Governance (`/admin/model-insights`)
