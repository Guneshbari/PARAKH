"""
PARAKH Synthetic Credit Application Generator - Custom Exceptions
Defines hierarchical exceptions for configuration, schema, validation,
temporal leakage, and impossible combinations.
"""


class GeneratorError(Exception):
    """Base exception for all synthetic data generator errors."""
    pass


class ConfigurationError(GeneratorError):
    """Raised when configuration parameters are invalid or inconsistent."""
    pass


class SchemaError(GeneratorError):
    """Raised when dataset schema, column names, or data types violate specifications."""
    pass


class ValidationError(GeneratorError):
    """Base exception for validation gate failures."""
    pass


class TemporalLeakageError(ValidationError):
    """
    Raised when temporal isolation is violated:
    - Historical telemetry timestamp >= cutoff timestamp t0
    - Forward simulation outcomes appear in observation features
    """
    pass


class ImpossibleCombinationError(ValidationError):
    """
    Raised when physically impossible or contradictory data combinations are detected:
    - feat_act_active_days_ratio == 0 but feat_inc_median_90d > 0
    - feat_inc_cv_90d == 0 but feat_inc_downside_var > 0
    - feat_rec_bounceback_ratio < 0
    - feat_suf_payout_count > feat_suf_observed_days
    - gross_earnings < net_payout_amount
    """
    pass


class MissingnessViolationError(ValidationError):
    """Raised when mandatory features contain nulls or optional features violate missingness bounds."""
    pass


class ReproducibilityError(ValidationError):
    """Raised when identical seeds fail to reproduce identical outputs."""
    pass
