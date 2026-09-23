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
    ApplicationFeatures,
    ForwardOutcome,
    AssembledApplicationRecord,
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
from src.data.synthetic.feature_derivation import (
    derive_application_features,
    validate_derived_features,
)
from src.data.synthetic.target_generator import (
    get_target_rng,
    compute_prediction_horizon,
    simulate_single_forward_path,
    simulate_forward_outcome,
    generate_forward_outcomes,
    validate_forward_outcome,
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
    IdentityValidationError,
    CohortValidationError,
    TargetValidationError,
    FeatureRangeError,
)
from src.data.synthetic.assembly import (
    assemble_application_record,
    assemble_dataset,
    validate_assembled_record,
    validate_assembled_dataset,
)
from src.data.synthetic.validators import (
    ValidationErrorDetail,
    DatasetValidationReport,
    validate_record_schema,
    validate_identities_and_relations,
    validate_cohort_distribution,
    validate_feature_semantics,
    validate_target_semantics,
    validate_temporal_distribution,
    validate_impossible_combinations,
    validate_missingness,
    validate_leakage_suite,
    validate_determinism,
    validate_dataset,
    validate_dataset_strict,
)
from src.data.synthetic.dataset_generator import (
    GenerationResult,
    create_canonical_pyarrow_schema,
    serialize_applications_parquet,
    serialize_raw_artifacts,
    serialize_validation_artifacts,
    generate_full_synthetic_dataset,
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
    "ApplicationFeatures",
    "ForwardOutcome",
    "AssembledApplicationRecord",
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
    "IdentityValidationError",
    "CohortValidationError",
    "TargetValidationError",
    "FeatureRangeError",
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
    "derive_application_features",
    "validate_derived_features",
    # Target Generator
    "get_target_rng",
    "compute_prediction_horizon",
    "simulate_single_forward_path",
    "simulate_forward_outcome",
    "generate_forward_outcomes",
    "validate_forward_outcome",
    # Assembly
    "assemble_application_record",
    "assemble_dataset",
    "validate_assembled_record",
    "validate_assembled_dataset",
    # Validation & Leakage
    "ValidationErrorDetail",
    "DatasetValidationReport",
    "validate_record_schema",
    "validate_identities_and_relations",
    "validate_cohort_distribution",
    "validate_feature_semantics",
    "validate_target_semantics",
    "validate_temporal_distribution",
    "validate_impossible_combinations",
    "validate_missingness",
    "validate_leakage_suite",
    "validate_determinism",
    "validate_dataset",
    "validate_dataset_strict",
    # Final Dataset Generator (P2-T10)
    "GenerationResult",
    "create_canonical_pyarrow_schema",
    "serialize_applications_parquet",
    "serialize_raw_artifacts",
    "serialize_validation_artifacts",
    "generate_full_synthetic_dataset",
]

