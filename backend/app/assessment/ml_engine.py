"""ML Assessment Engine and Model boundary contracts for PARAKH.

Provides the decoupled integration interface for Person 3's trained ML models
(e.g., LightGBM, XGBoost, Logistic Regression) to plug into the canonical
AssessmentEngine architecture and map into standard AssessmentResult instances.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import (
    AssessmentNotImplementedError,
    AssessmentOutputError,
)
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.models.assessment import RiskLevel


class MLModelOutput(BaseModel):
    """Standardized prediction output contract for Person 3's ML models."""

    model_config = ConfigDict(extra="forbid")

    risk_probability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Model estimated probability of default bounded [0, 1] (nullable for insufficient evidence)",
    )
    confidence: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Model evaluation confidence bounded [0, 1]",
    )
    risk_level: Optional[RiskLevel] = Field(
        None,
        description="Categorical risk tier. If omitted, derived from credit score or probability.",
    )
    credit_score: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Model-computed alternative credit score (0-1000). If omitted, mapped from risk_probability.",
    )
    key_factors: List[str] = Field(
        default_factory=list,
        description="Top influential features or driving signals identified by the model",
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured explainability payload (e.g., SHAP values, feature importance weights)",
    )
    debt_to_income: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Derived debt-to-income ratio",
    )
    utilization: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Derived credit utilization index",
    )
    income_stability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Derived income stability score",
    )
    repayment_reliability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Derived repayment reliability score",
    )


class MLModel(ABC):
    """Abstract interface contract for Person 3's ML credit scoring models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the trained model (e.g., 'lightgbm-credit-v1')."""
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the semantic version of the trained model (e.g., '1.0.0')."""
        pass

    @abstractmethod
    def predict(self, input_data: AssessmentInput) -> MLModelOutput:
        """Execute model inference on normalized assessment input and engineered features.

        Args:
            input_data: Validated AssessmentInput containing loan, work, and derived features.

        Returns:
            MLModelOutput: Standardized prediction outputs.

        Raises:
            AssessmentEngineError: If model inference or calculation fails.
        """
        pass


class MLAssessmentEngine(AssessmentEngine):
    """AssessmentEngine implementation wrapping Person 3's ML model.

    Decouples model execution and inference from application workflow, mapping
    raw model predictions into PARAKH's canonical AssessmentResult domain schema.
    """

    def __init__(
        self,
        model: Optional[MLModel] = None,
        engine_name: str = "parakh-ml-engine",
        engine_version: str = "1.0.0",
    ) -> None:
        """Initialize MLAssessmentEngine with an optional model instance."""
        self._model = model
        self._engine_name = engine_name
        self._engine_version = engine_version

    @property
    def engine_name(self) -> str:
        """Return the name/identifier of this engine or its underlying model."""
        if self._model:
            return self._model.model_name
        return self._engine_name

    @property
    def engine_version(self) -> str:
        """Return the version string of this engine or its underlying model."""
        if self._model:
            return self._model.model_version
        return self._engine_version

    def set_model(self, model: MLModel) -> None:
        """Register or swap the underlying MLModel implementation."""
        self._model = model

    def assess(self, input_data: AssessmentInput) -> AssessmentResult:
        """Execute credit assessment evaluation via the registered MLModel.

        Args:
            input_data: Privacy-compliant AssessmentInput with derived features.

        Returns:
            AssessmentResult: Canonical assessment output matching persistence model.

        Raises:
            AssessmentNotImplementedError: If no ML model has been registered.
            AssessmentOutputError: If model produces invalid or malformed output.
        """
        if self._model is None:
            raise AssessmentNotImplementedError(
                "ML credit assessment model is not implemented or registered. "
                "AssessmentEngine is configured for ML mode, but requires Person 3's trained model."
            )

        output = self._model.predict(input_data)
        if not isinstance(output, MLModelOutput):
            raise AssessmentOutputError(
                f"ML model returned {type(output).__name__}, expected MLModelOutput."
            )

        # Map or compute score [300, 850] from risk_probability if not explicitly provided and not insufficient evidence
        score = output.credit_score
        if score is None and output.risk_level != RiskLevel.INSUFFICIENT and output.risk_probability is not None:
            risk_prob_float = float(output.risk_probability)
            score = int(round(300 + (1.0 - risk_prob_float) * 550))
            score = max(0, min(1000, score))

        # Map risk level if not explicitly provided by the model
        risk_level = output.risk_level
        if risk_level is None:
            if score is not None:
                if score >= 700:
                    risk_level = RiskLevel.LOWER
                elif score >= 550:
                    risk_level = RiskLevel.MODERATE
                else:
                    risk_level = RiskLevel.HIGHER
            else:
                risk_level = RiskLevel.INSUFFICIENT

        # Construct standard AssessmentResult
        return AssessmentResult(
            score=score,
            risk_probability=output.risk_probability,
            confidence=output.confidence,
            risk_level=risk_level,
            model_name=self.engine_name,
            model_version=self.engine_version,
            debt_to_income=output.debt_to_income,
            utilization=output.utilization,
            income_stability=output.income_stability,
            repayment_reliability=output.repayment_reliability,
            key_factors=output.key_factors,
            explanation=output.explanation,
            assessment_status="COMPLETED",
        )
