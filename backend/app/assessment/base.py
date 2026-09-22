"""Abstract base interface for credit assessment engines."""
from abc import ABC, abstractmethod
from typing import Optional
from app.assessment.schemas import AssessmentInput, AssessmentResult


class AssessmentEngine(ABC):
    """Abstract interface contract for PARAKH credit assessment engines.

    Framework-independent contract decoupling scoring implementations
    (e.g., rule-based mock engines, ML models, ensembles) from the
    persistence and service layers.
    """

    @property
    def engine_name(self) -> str:
        """Return the name/identifier of this assessment engine."""
        return getattr(self, "_engine_name", self.__class__.__name__)

    @property
    def engine_version(self) -> str:
        """Return the version string of this assessment engine."""
        return getattr(self, "_engine_version", "1.0.0")

    @abstractmethod
    def assess(self, input_data: AssessmentInput) -> AssessmentResult:
        """Execute credit assessment evaluation on normalized input features.

        Args:
            input_data: Data-minimization-compliant assessment input.

        Returns:
            AssessmentResult: Standardized score, risk tier, probability, and confidence.

        Raises:
            AssessmentEngineError: If calculation or model inference fails.
            AssessmentInputError: If input data is insufficient or invalid.
        """
        pass
