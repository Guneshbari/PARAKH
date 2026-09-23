"""
PARAKH Synthetic Data Generator Package.
Provides modules for generating realistic, volatility-aware synthetic credit applications
and cashflow insolvency simulation.
"""

from src.data.synthetic.config import (
    MASTER_SEED,
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
    REPEAT_APPLICANTS,
    CANONICAL_OUTPUT_PATH,
    validate_config,
)
from src.data.synthetic.random_state import (
    RandomStateManager,
    Substream,
)
from src.data.synthetic.schemas import (
    Applicant,
    ApplicantProfile,
    Application,
    HistoricalTelemetry,
    DerivedFeatures,
    ForwardOutcome,
    FinalRecord,
    ColumnDefinition,
    ColumnCategory,
    DataType,
    FINAL_DATASET_SCHEMA,
    get_column_names,
    get_metadata_columns,
    get_raw_profile_columns,
    get_raw_loan_columns,
    get_derived_feature_columns,
    get_target_columns,
    get_feature_matrix_columns,
    get_excluded_columns,
    validate_schema_counts,
)
from src.data.synthetic.exceptions import (
    GeneratorError,
    ConfigurationError,
    SchemaError,
    ValidationError,
    TemporalLeakageError,
    ImpossibleCombinationError,
    MissingnessViolationError,
    ReproducibilityError,
)

__all__ = [
    # Config
    "MASTER_SEED",
    "TOTAL_APPLICATIONS",
    "UNIQUE_APPLICANTS",
    "REPEAT_APPLICANTS",
    "CANONICAL_OUTPUT_PATH",
    "validate_config",
    # Random State
    "RandomStateManager",
    "Substream",
    # Schemas
    "Applicant",
    "ApplicantProfile",
    "Application",
    "HistoricalTelemetry",
    "DerivedFeatures",
    "ForwardOutcome",
    "FinalRecord",
    "ColumnDefinition",
    "ColumnCategory",
    "DataType",
    "FINAL_DATASET_SCHEMA",
    "get_column_names",
    "get_metadata_columns",
    "get_raw_profile_columns",
    "get_raw_loan_columns",
    "get_derived_feature_columns",
    "get_target_columns",
    "get_feature_matrix_columns",
    "get_excluded_columns",
    "validate_schema_counts",
    # Exceptions
    "GeneratorError",
    "ConfigurationError",
    "SchemaError",
    "ValidationError",
    "TemporalLeakageError",
    "ImpossibleCombinationError",
    "MissingnessViolationError",
    "ReproducibilityError",
]
