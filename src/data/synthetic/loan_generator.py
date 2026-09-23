"""
PARAKH Synthetic Data Generator - Loan Application Generator
Samples application-level loan financing terms:
- requested_loan_amount: Log-normal (mu=ln(20000), sigma=0.55, High Obligation mu=ln(35000))
- loan_tenure_months: Discrete (1, 2, 3, 4, 6, 12)
- loan_purpose: Categorical (VEHICLE_MAINTENANCE, WORKING_CAPITAL, etc.)
- contractual_emi: Standard reducing-balance formula at 18% p.a.
- daily_debt_obligation: (existing_debt + EMI) / 30
"""

import math
import random

from typing import Optional, Union

from src.data.synthetic.applicant_generator import generate_deterministic_uuid
from src.data.synthetic.config import (
    COHORT_HIGH_OBLIGATION,
    LOAN_AMOUNT_MIN,
    LOAN_AMOUNT_MAX,
    LOAN_AMOUNT_LOGNORMAL_MU,
    LOAN_AMOUNT_LOGNORMAL_SIGMA,
    LOAN_AMOUNT_ROUND_BASE,
    LOAN_MULTIPLE_MIN,
    LOAN_MULTIPLE_MAX,
    LOAN_TENURES,
    LOAN_TENURE_PROPORTIONS,
    LOAN_PURPOSES,
    LOAN_PURPOSE_PROPORTIONS,
    calculate_contractual_emi,
)
from src.data.synthetic.schemas import ApplicantProfile, Application


def sample_loan_amount(
    profile_or_cohort: Union[ApplicantProfile, str, float],
    rng: random.Random,
    monthly_income_baseline: Optional[float] = None,
) -> float:
    """
    Sample principal loan financing amount requested in INR (Approved P2-T10 Affordability Revision):
    loan_amount = monthly_income_baseline * loan_multiple
    loan_multiple ~ Uniform(1.5, 2.5)
    Rounded to nearest ₹500, clipped to [500, 500000].
    """
    if isinstance(profile_or_cohort, ApplicantProfile):
        monthly_base = profile_or_cohort.baseline_weekly_income * 4.33
    elif monthly_income_baseline is not None:
        monthly_base = monthly_income_baseline
    elif isinstance(profile_or_cohort, (int, float)):
        monthly_base = float(profile_or_cohort)
    else:
        monthly_base = 20000.0

    loan_multiple = rng.uniform(LOAN_MULTIPLE_MIN, LOAN_MULTIPLE_MAX)
    raw_loan = monthly_base * loan_multiple
    rounded = round(raw_loan / LOAN_AMOUNT_ROUND_BASE) * LOAN_AMOUNT_ROUND_BASE
    return float(min(max(rounded, LOAN_AMOUNT_MIN), LOAN_AMOUNT_MAX))


def sample_loan_tenure(rng: random.Random) -> int:
    """
    Sample discrete contractual loan repayment tenure in months.
    Values: [6, 9, 12] with approved probabilities [0.20, 0.30, 0.50].
    """
    tenures = list(LOAN_TENURE_PROPORTIONS.keys())
    weights = list(LOAN_TENURE_PROPORTIONS.values())
    return int(rng.choices(tenures, weights=weights, k=1)[0])


def sample_loan_purpose(rng: random.Random) -> str:
    """
    Sample declared financing purpose enum string.
    """
    purposes = list(LOAN_PURPOSE_PROPORTIONS.keys())
    weights = list(LOAN_PURPOSE_PROPORTIONS.values())
    return str(rng.choices(purposes, weights=weights, k=1)[0])


def generate_single_application(
    applicant_profile: ApplicantProfile,
    application_index: int,
    cutoff_timestamp: str,
    rng: random.Random,
) -> Application:
    """
    Generates a single Application record for an applicant profile at cutoff timestamp t0.
    """
    application_id = generate_deterministic_uuid(rng)
    loan_amount = sample_loan_amount(applicant_profile, rng)
    tenure_months = sample_loan_tenure(rng)
    loan_purpose = sample_loan_purpose(rng)

    contractual_emi = round(calculate_contractual_emi(loan_amount, tenure_months), 2)
    daily_debt_obligation = round(
        (applicant_profile.existing_monthly_debt + contractual_emi) / 30.0, 2
    )

    return Application(
        application_id=application_id,
        applicant_profile_id=applicant_profile.applicant_profile_id,
        application_index=application_index,
        cutoff_timestamp=cutoff_timestamp,
        requested_loan_amount=loan_amount,
        loan_tenure_months=tenure_months,
        loan_purpose=loan_purpose,
        contractual_emi=contractual_emi,
        daily_debt_obligation=daily_debt_obligation,
    )
