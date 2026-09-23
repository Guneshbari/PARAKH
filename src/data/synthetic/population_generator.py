"""
PARAKH Synthetic Data Generator - Population Generator Orchestrator
Coordinates:
- 10,000 unique applicant identities and profiles
- Exact cohort distribution
- Deterministic repeat applicant selection (exactly 2,000 repeat borrowers)
- Application timestamp sequencing (t0_second > t0_first in [120, 270] days)
- 12,000 total application requests
- Validation of structural invariants
"""

from typing import List, Optional, Set

from src.data.synthetic.applicant_generator import generate_applicants_and_profiles
from src.data.synthetic.config import (
    MASTER_SEED,
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
    REPEAT_APPLICANTS,
    SINGLE_APPLICANTS,
)
from src.data.synthetic.exceptions import ValidationError
from src.data.synthetic.loan_generator import generate_single_application
from src.data.synthetic.random_state import RandomStateManager, Substream
from src.data.synthetic.schemas import (
    Applicant,
    ApplicantProfile,
    Application,
    PopulationData,
)
from src.data.synthetic.temporal_manager import (
    select_repeat_applicants,
    generate_single_applicant_timestamp,
    generate_repeat_applicant_timestamps,
)


def generate_population(
    random_state_manager: Optional[RandomStateManager] = None,
    n_applicants: int = UNIQUE_APPLICANTS,
    n_repeats: int = REPEAT_APPLICANTS,
) -> PopulationData:
    """
    Generates the complete applicant and application population.
    Default configuration yields:
    - 10,000 unique applicants
    - 10,000 applicant profiles
    - 2,000 repeat applicants (each with exactly 2 applications)
    - 8,000 single applicants (each with exactly 1 application)
    - 12,000 total applications
    """
    if random_state_manager is None:
        random_state_manager = RandomStateManager(MASTER_SEED)

    # Step 1: Generate applicants and baseline profiles
    applicants, profiles = generate_applicants_and_profiles(
        random_state_manager=random_state_manager,
        n_applicants=n_applicants,
    )

    # Step 2: Select repeat applicants deterministically
    rng_temporal = random_state_manager.get_stream(Substream.APPLICATIONS)
    repeat_indices = select_repeat_applicants(
        n_applicants=n_applicants,
        n_repeats=n_repeats,
        rng=rng_temporal,
    )

    repeat_applicant_ids: List[str] = [
        applicants[idx].applicant_profile_id for idx in sorted(repeat_indices)
    ]
    repeat_id_set: Set[str] = set(repeat_applicant_ids)

    # Step 3: Generate applications and timestamps
    applications: List[Application] = []
    rng_loan = random_state_manager.get_stream(Substream.APPLICATIONS)

    for idx, applicant in enumerate(applicants):
        profile = profiles[idx]
        is_repeat = idx in repeat_indices

        if is_repeat:
            # Repeat borrower: generate 2 applications
            t0_1, t0_2, _ = generate_repeat_applicant_timestamps(rng_temporal)

            app_1 = generate_single_application(
                applicant_profile=profile,
                application_index=1,
                cutoff_timestamp=t0_1,
                rng=rng_loan,
            )
            app_2 = generate_single_application(
                applicant_profile=profile,
                application_index=2,
                cutoff_timestamp=t0_2,
                rng=rng_loan,
            )
            applications.append(app_1)
            applications.append(app_2)
        else:
            # Single borrower: generate 1 application
            t0 = generate_single_applicant_timestamp(rng_temporal)
            app = generate_single_application(
                applicant_profile=profile,
                application_index=1,
                cutoff_timestamp=t0,
                rng=rng_loan,
            )
            applications.append(app)

    # Step 4: Validate structural invariants
    expected_total_applications = (n_applicants - n_repeats) + (n_repeats * 2)
    if len(applicants) != n_applicants:
        raise ValidationError(f"Expected {n_applicants} applicants, got {len(applicants)}")
    if len(profiles) != n_applicants:
        raise ValidationError(f"Expected {n_applicants} profiles, got {len(profiles)}")
    if len(applications) != expected_total_applications:
        raise ValidationError(
            f"Expected {expected_total_applications} applications, got {len(applications)}"
        )
    if len(repeat_applicant_ids) != n_repeats:
        raise ValidationError(f"Expected {n_repeats} repeat applicants, got {len(repeat_applicant_ids)}")

    return PopulationData(
        applicants=applicants,
        profiles=profiles,
        applications=applications,
        repeat_applicant_ids=repeat_applicant_ids,
    )
