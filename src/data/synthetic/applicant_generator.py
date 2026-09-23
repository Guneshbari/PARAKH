"""
PARAKH Synthetic Data Generator - Applicant and Profile Generator
Implements:
- Synthetic, non-PII, deterministic RFC 4122 UUIDv4 applicant identities
- Exact cohort assignment according to frozen proportions (25/25/20/15/10/5%)
- Worker baseline profile generation matching Table 6.2 and Section 7.1
"""

import math
import random
from typing import List, Tuple
import uuid

from src.data.synthetic.config import (
    UNIQUE_APPLICANTS,
    COHORT_ARCHETYPES,
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    COHORT_PROPORTIONS,
    GIG_WORK_TYPES,
    GIG_WORK_TYPE_PROPORTIONS,
    LIVING_EXPENSE_MONTHLY_MU,
    LIVING_EXPENSE_MONTHLY_SIGMA,
    LIVING_EXPENSE_MONTHLY_MIN,
    LIVING_EXPENSE_MONTHLY_MAX,
    EXISTING_DEBT_MULTIPLIER,
)
from src.data.synthetic.exceptions import ConfigurationError
from src.data.synthetic.random_state import RandomStateManager, Substream
from src.data.synthetic.schemas import Applicant, ApplicantProfile


def generate_cohort_assignments(
    n_applicants: int = UNIQUE_APPLICANTS,
    rng: random.Random = None,
) -> List[str]:
    """
    Generate deterministic cohort assignments matching frozen contract proportions.
    For 10,000 applicants, generates exactly:
    - 2,500 Healthy Volatile
    - 2,500 Stable
    - 2,000 Declining
    - 1,500 Irregular
    - 1,000 High Obligation
    - 500 Insufficient Data
    """
    if rng is None:
        raise ValueError("rng instance must be provided")

    cohort_counts = {
        COHORT_HEALTHY_VOLATILE: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_HEALTHY_VOLATILE])),
        COHORT_STABLE: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_STABLE])),
        COHORT_DECLINING: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_DECLINING])),
        COHORT_IRREGULAR: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_IRREGULAR])),
        COHORT_HIGH_OBLIGATION: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_HIGH_OBLIGATION])),
        COHORT_INSUFFICIENT_DATA: int(round(n_applicants * COHORT_PROPORTIONS[COHORT_INSUFFICIENT_DATA])),
    }

    # Verify counts sum exactly to n_applicants
    total_assigned = sum(cohort_counts.values())
    if total_assigned != n_applicants:
        # Adjust rounding difference on majority cohort
        diff = n_applicants - total_assigned
        cohort_counts[COHORT_STABLE] += diff

    cohort_list: List[str] = []
    for cohort_name, count in cohort_counts.items():
        cohort_list.extend([cohort_name] * count)

    # Deterministic shuffle
    rng.shuffle(cohort_list)
    return cohort_list


def generate_deterministic_uuid(rng: random.Random) -> str:
    """
    Generates a deterministic, synthetic RFC 4122 UUIDv4 string using the provided PRNG.
    Contains no PII, hardware MAC address, or system clock state.
    """
    raw_int = rng.getrandbits(128)
    # Set version to 4 (bits 12-15 of time_hi_and_version to 0100)
    raw_int = (raw_int & ~(0xF << 76)) | (0x4 << 76)
    # Set variant to RFC 4122 (bits 6-7 of clock_seq_hi_and_reserved to 10)
    raw_int = (raw_int & ~(0x3 << 62)) | (0x2 << 62)
    return str(uuid.UUID(int=raw_int))


def generate_single_profile(
    applicant_profile_id: str,
    cohort_archetype: str,
    rng: random.Random,
) -> ApplicantProfile:
    """
    Generate baseline profile and financial attributes for an individual applicant.
    Respects Table 6.2 and Section 7.1 distributions and cohort modifications.
    """
    # 1. Primary Gig Work Type (Section 7.1)
    work_types = list(GIG_WORK_TYPE_PROPORTIONS.keys())
    work_weights = list(GIG_WORK_TYPE_PROPORTIONS.values())
    gig_work_type = rng.choices(work_types, weights=work_weights, k=1)[0]

    # 2. Cumulative Years Working (Table 6.2: Gamma(k=2.0, theta=1.25))
    if cohort_archetype == COHORT_INSUFFICIENT_DATA:
        years_working = round(rng.uniform(0.01, 0.10), 2)
    else:
        raw_years = rng.gammavariate(2.0, 1.25)
        if cohort_archetype == COHORT_STABLE:
            raw_years += 1.0
        years_working = round(min(max(raw_years, 0.0), 50.0), 2)

    # 3. Average Working Days (Table 6.2: Truncated Normal(24, 4), Irregular Normal(14, 5))
    if cohort_archetype == COHORT_IRREGULAR:
        raw_days = rng.gauss(14.0, 5.0)
    else:
        raw_days = rng.gauss(24.0, 4.0)
    average_working_days = int(min(max(round(raw_days), 0), 31))

    # 4. Monthly Living Expense (Table 6.2: LogNormal(mu=ln(14000), sigma=0.10))
    raw_expense = rng.lognormvariate(LIVING_EXPENSE_MONTHLY_MU, LIVING_EXPENSE_MONTHLY_SIGMA)
    monthly_living_expense = round(
        min(max(raw_expense, LIVING_EXPENSE_MONTHLY_MIN), LIVING_EXPENSE_MONTHLY_MAX), 2
    )

    # 5. Baseline Weekly Income (Table 6.2: LogNormal with sigma=0.40)
    if cohort_archetype == COHORT_HEALTHY_VOLATILE:
        mu_income = math.log(8000.0)
    elif cohort_archetype == COHORT_STABLE:
        mu_income = math.log(7000.0)
    elif cohort_archetype == COHORT_DECLINING:
        mu_income = math.log(4500.0)
    elif cohort_archetype == COHORT_IRREGULAR:
        mu_income = math.log(3800.0)
    elif cohort_archetype == COHORT_HIGH_OBLIGATION:
        mu_income = math.log(9200.0)
    else:  # Insufficient Data
        mu_income = math.log(3200.0)
    baseline_weekly_income = round(
        min(max(rng.lognormvariate(mu_income, 0.40), 1000.0), 50000.0), 2
    )

    # 6. Existing Monthly Debt (Table 6.2: Gamma DTI)
    monthly_income = baseline_weekly_income * 4.33
    if cohort_archetype != COHORT_HIGH_OBLIGATION and rng.random() < 0.15:
        existing_monthly_debt = 0.0
    else:
        if cohort_archetype == COHORT_HIGH_OBLIGATION:
            dti = rng.gammavariate(5.0, 0.12)  # Mean ~0.60
        else:
            dti = rng.gammavariate(2.2, 0.10)  # Mean ~0.22
        raw_debt = round(min(max(dti * monthly_income, 0.0), 100000.0), 2)
        existing_monthly_debt = round(raw_debt * EXISTING_DEBT_MULTIPLIER, 2)

    # 7. Starting Cashflow Buffer (Table 6.2: LogNormal buffer-to-loan proxy)
    if cohort_archetype == COHORT_HEALTHY_VOLATILE:
        buffer_ratio = rng.lognormvariate(math.log(0.90), 0.50)
    elif cohort_archetype == COHORT_HIGH_OBLIGATION:
        buffer_ratio = rng.lognormvariate(math.log(0.25), 0.50)
    elif cohort_archetype in (COHORT_DECLINING, COHORT_IRREGULAR):
        buffer_ratio = rng.lognormvariate(math.log(0.35), 0.50)
    else:
        buffer_ratio = rng.lognormvariate(math.log(0.65), 0.50)

    starting_cashflow_buffer = buffer_ratio * 20000.0
    if cohort_archetype in (COHORT_IRREGULAR, COHORT_DECLINING) and rng.random() < 0.10:
        starting_cashflow_buffer = 0.0
    starting_cashflow_buffer = round(min(max(starting_cashflow_buffer, 0.0), 200000.0), 2)

    # 8. Platform Rating (Table 6.2: Shifted Beta)
    if cohort_archetype == COHORT_DECLINING:
        rating = 1.0 + 4.0 * rng.betavariate(4.0, 2.0)
    else:
        rating = 1.0 + 4.0 * rng.betavariate(8.0, 1.5)
    platform_rating = round(min(max(rating, 1.0), 5.0), 2)

    # 9. Cancellation Rate (Table 6.2: Beta(1.5, 20.0))
    if gig_work_type == "FREELANCE_MICRO":
        cancellation_rate = 0.0
    else:
        cancellation_rate = round(min(max(rng.betavariate(1.5, 20.0), 0.0), 1.0), 4)

    # 10. Alternative Repayment Reliability (Table 6.2: Beta(9.0, 1.5))
    payment_reliability = round(min(max(rng.betavariate(9.0, 1.5), 0.0), 1.0), 4)

    return ApplicantProfile(
        applicant_profile_id=applicant_profile_id,
        cohort_archetype=cohort_archetype,
        gig_work_type=gig_work_type,
        years_working=years_working,
        average_working_days=average_working_days,
        monthly_living_expense=monthly_living_expense,
        existing_monthly_debt=existing_monthly_debt,
        starting_cashflow_buffer=starting_cashflow_buffer,
        baseline_weekly_income=baseline_weekly_income,
        platform_rating=platform_rating,
        cancellation_rate=cancellation_rate,
        payment_reliability=payment_reliability,
    )


def generate_applicants_and_profiles(
    random_state_manager: RandomStateManager,
    n_applicants: int = UNIQUE_APPLICANTS,
) -> Tuple[List[Applicant], List[ApplicantProfile]]:
    """
    Coordinates applicant identity generation, cohort assignment, and profile sampling.
    Returns:
    - List of 10,000 Applicant objects
    - List of 10,000 ApplicantProfile objects
    """
    rng_cohorts = random_state_manager.get_stream(Substream.COHORTS)
    rng_applicants = random_state_manager.get_stream(Substream.APPLICANTS)
    rng_profiles = random_state_manager.get_stream(Substream.PROFILES)

    # Step 1: Assign cohorts
    cohorts = generate_cohort_assignments(n_applicants, rng=rng_cohorts)

    # Step 2: Generate applicant identities and profiles
    applicants: List[Applicant] = []
    profiles: List[ApplicantProfile] = []

    seen_ids = set()
    for i in range(n_applicants):
        applicant_id = generate_deterministic_uuid(rng_applicants)
        if applicant_id in seen_ids:
            raise ConfigurationError(f"Duplicate UUID generated: {applicant_id}")
        seen_ids.add(applicant_id)

        cohort = cohorts[i]
        applicant = Applicant(
            applicant_profile_id=applicant_id,
            cohort_archetype=cohort,
        )
        applicants.append(applicant)

        profile = generate_single_profile(
            applicant_profile_id=applicant_id,
            cohort_archetype=cohort,
            rng=rng_profiles,
        )
        profiles.append(profile)

    return applicants, profiles
