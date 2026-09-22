"""Engine factory for selecting and instantiating assessment engines."""
from typing import Optional
from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import AssessmentEngineError
from app.assessment.ml_engine import MLAssessmentEngine
from app.assessment.mock import MockAssessmentEngine
from app.core.config import settings


def create_assessment_engine(engine_name: Optional[str] = None) -> AssessmentEngine:
    """Create an AssessmentEngine instance based on configuration or explicit parameter.

    Args:
        engine_name: Optional engine identifier ('mock' or 'ml').
            Defaults to settings.ASSESSMENT_ENGINE if omitted.

    Returns:
        AssessmentEngine: Configured assessment engine instance.

    Raises:
        AssessmentEngineError: If engine name is unrecognized or invalid.
    """
    resolved_name = (engine_name or settings.ASSESSMENT_ENGINE).lower().strip()

    if resolved_name == "mock":
        return MockAssessmentEngine()
    elif resolved_name == "ml":
        return MLAssessmentEngine()
    else:
        raise AssessmentEngineError(
            f"Unsupported assessment engine: '{resolved_name}'. Supported engines are 'mock' and 'ml'."
        )
