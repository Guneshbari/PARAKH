"""Central constants, enums, and configuration for PARAKH ML infrastructure.

Follows the authoritative specifications in docs/ml-specification.md and docs/ml-data-specification.md.
"""
from enum import Enum
from typing import Final, List, Set

# Standard random seed for reproducibility across all ML experiments
DEFAULT_RANDOM_SEED: Final[int] = 42

# Temporal window defaults
DEFAULT_OBSERVATION_DAYS: Final[int] = 90
DEFAULT_MIN_ACTIVE_HISTORY_DAYS: Final[int] = 30
DEFAULT_MIN_PAYOUT_CYCLES: Final[int] = 4
DEFAULT_PREDICTION_HORIZON_MIN_DAYS: Final[int] = 30
DEFAULT_PREDICTION_HORIZON_MAX_DAYS: Final[int] = 90


class RiskTier(str, Enum):
    """Categorical risk tiers for PARAKH credit assessment.

    Directly compatible with backend RiskLevel enum (backend/app/models/assessment.py):
    - LOWER: Favorable creditworthiness profile.
    - MODERATE: Intermediate risk tier requiring conservative sizing or monitoring.
    - HIGHER: Elevated repayment risk profile.
    - INSUFFICIENT: Insufficient data or history to support a responsible statistical score.
    """

    LOWER = "LOWER"
    MODERATE = "MODERATE"
    HIGHER = "HIGHER"
    INSUFFICIENT = "INSUFFICIENT"


class CohortArchetype(str, Enum):
    """Synthetic population cohorts defined in Phase 1 Data Contract (docs/ml-data-specification.md)."""

    HEALTHY_VOLATILE = "Healthy Volatile"
    STABLE = "Stable"
    DECLINING = "Declining"
    IRREGULAR = "Irregular"
    HIGH_OBLIGATION = "High Obligation"
    INSUFFICIENT_DATA = "Insufficient Data"


class GigWorkSector(str, Enum):
    """Approved gig economy sectors for subgroup evaluation and feature representation."""

    DELIVERY = "DELIVERY"
    RIDE_HAILING = "RIDE_HAILING"
    LOGISTICS = "LOGISTICS"
    HOME_SERVICES = "HOME_SERVICES"
    FREELANCE_MICRO = "FREELANCE_MICRO"
    OTHER = "OTHER"


class ExperimentVariant(str, Enum):
    """Experiment design variants for volatility-aware model benchmarking."""

    BASELINE = "BASELINE"
    VOLATILITY_AWARE = "VOLATILITY_AWARE"


# Provisional default probability thresholds documented in docs/ml-specification.md (Section 10.2).
# NOTE: These are provisional prototype cutoffs only. Operational thresholds will be calibrated
# empirically against validation ROC/PR curves in Phase 8.
PROVISIONAL_THRESHOLD_LOWER: Final[float] = 0.20
PROVISIONAL_THRESHOLD_HIGHER: Final[float] = 0.45

# Presentation score scale (e.g., 300 to 850)
PRESENTATION_SCORE_MIN: Final[int] = 300
PRESENTATION_SCORE_MAX: Final[int] = 850

# Core signal groups required for sufficiency check
CORE_SIGNAL_GROUPS: Final[Set[str]] = {
    "gig_income",
    "work_activity",
    "cashflow_buffer",
    "payment_discipline",
    "financial_obligations",
}

MIN_REQUIRED_CORE_SIGNAL_GROUPS: Final[int] = 2

# Prohibited fields to ensure strict data minimization compliance
PROHIBITED_FIELDS: Final[Set[str]] = {
    "bank_account_number",
    "bank_credentials",
    "banking_login_credentials",
    "password",
    "password_hash",
    "raw_transactions",
    "raw_bank_statements",
    "raw_upi_transactions",
    "raw_upi_logs",
    "upi_vpa",
    "merchant_name",
    "merchant_description",
    "merchant_details",
    "gps_coordinates",
    "location_history",
    "contact_list",
    "contacts",
}
