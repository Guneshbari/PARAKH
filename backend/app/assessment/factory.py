from typing import Optional
from app.assessment.base import AssessmentEngine
from app.assessment.exceptions import AssessmentEngineError
from app.assessment.ml_engine import MLAssessmentEngine, MLModel
from app.assessment.mock import MockAssessmentEngine
from app.core.config import settings


def create_assessment_engine(
    engine_name: Optional[str] = None,
    model: Optional[MLModel] = None,
    attach_model: Optional[bool] = None,
) -> AssessmentEngine:
    """Create an AssessmentEngine instance based on configuration or explicit parameter.

    Args:
        engine_name: Optional engine identifier ('mock' or 'ml').
            Defaults to settings.ASSESSMENT_ENGINE if omitted.
        model: Optional explicit MLModel instance to attach to MLAssessmentEngine.
        attach_model: Optional boolean flag to explicitly control whether the default
            production MLModelAdapter is attached when engine is 'ml'. If None, attaches
            automatically when engine_name is omitted (production settings-driven mode).

    Returns:
        AssessmentEngine: Configured assessment engine instance.

    Raises:
        AssessmentEngineError: If engine name is unrecognized or invalid.
    """
    resolved_name = (engine_name or settings.ASSESSMENT_ENGINE).lower().strip()

    if resolved_name == "mock":
        return MockAssessmentEngine()
    elif resolved_name == "ml":
        if model is not None:
            return MLAssessmentEngine(model=model)

        should_attach = attach_model if attach_model is not None else (engine_name is None)
        if should_attach:
            from app.assessment.ml_model_adapter import MLModelAdapter
            return MLAssessmentEngine(model=MLModelAdapter())
        return MLAssessmentEngine()
    else:
        raise AssessmentEngineError(
            f"Unsupported assessment engine: '{resolved_name}'. Supported engines are 'mock' and 'ml'."
        )

