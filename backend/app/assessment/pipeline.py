"""Feature engineering pipeline contract and passthrough implementation for PARAKH.

Defines the boundary between raw/persisted FinancialSignal records and the
AssessmentEngine, providing a clean plug-in point for Person 2's feature pipeline.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Sequence
from app.assessment.schemas import _check_for_prohibited_keys


class FeaturePipeline(ABC):
    """Abstract interface for Person 2's feature engineering pipeline.

    Framework-independent contract transforming raw/persisted FinancialSignal records
    and application context into an engine-consumable feature set.
    """

    @abstractmethod
    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extract and compute sanitized features for credit assessment.

        Args:
            signals: Sequence of FinancialSignal domain records or dictionaries.
            application: Optional Application domain model or dictionary.
            applicant_profile: Optional ApplicantProfile domain model or dictionary.

        Returns:
            Dict[str, Any]: Key-value feature set passed into AssessmentInput.derived_features.

        Raises:
            AssessmentInputError: If derived features violate strict data minimization.
        """
        pass


class PassthroughFeaturePipeline(FeaturePipeline):
    """Default fallback feature pipeline used prior to ML feature engineering integration.

    Preserves any existing signal_metadata without fabricating synthetic numbers or
    violating data-minimization policies.
    """

    def extract_features(
        self,
        signals: Sequence[Any],
        application: Optional[Any] = None,
        applicant_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extract features by propagating existing non-sensitive signal_metadata."""
        features: Dict[str, Any] = {}
        if signals:
            latest = signals[-1] if isinstance(signals, (list, tuple)) else signals
            if isinstance(latest, dict):
                meta = latest.get("signal_metadata")
            else:
                meta = getattr(latest, "signal_metadata", None)

            if isinstance(meta, dict):
                # Ensure no prohibited privacy-invasive keys are passed
                _check_for_prohibited_keys(meta)
                features.update(meta)

        return features
