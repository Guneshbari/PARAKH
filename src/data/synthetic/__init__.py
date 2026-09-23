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
    DailyActivityEvent,
    WeeklyPayoutEvent,
    HistoricalTelemetry,
    ApplicationHistoricalData,
    DerivedFeatures,
    ForwardOutcome,
    FinalRecord,
    PopulationData,
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
from src.data.synthetic.applicant_generator import (
    generate_cohort_assignments,
    generate_deterministic_uuid,
    generate_single_profile,
    generate_applicants_and_profiles,
)
from src.data.synthetic.temporal_manager import (
    select_repeat_applicants,
    generate_single_applicant_timestamp,
    generate_repeat_applicant_timestamps,
)
from src.data.synthetic.loan_generator import (
    sample_loan_amount,
    sample_loan_tenure,
    sample_loan_purpose,
    generate_single_application,
)
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.telemetry_generator import (
    get_application_rng,
    format_utc_iso,
    generate_application_history,
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
    "DailyActivityEvent",
    "WeeklyPayoutEvent",
    "HistoricalTelemetry",
    "ApplicationHistoricalData",
    "DerivedFeatures",
    "ForwardOutcome",
    "FinalRecord",
    "PopulationData",
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
    # Generators
    "generate_cohort_assignments",
    "generate_deterministic_uuid",
    "generate_single_profile",
    "generate_applicants_and_profiles",
    "select_repeat_applicants",
    "generate_single_applicant_timestamp",
    "generate_repeat_applicant_timestamps",
    "sample_loan_amount",
    "sample_loan_tenure",
    "sample_loan_purpose",
    "generate_single_application",
    "generate_population",
    "get_application_rng",
    "format_utc_iso",
    "generate_application_history",
]

