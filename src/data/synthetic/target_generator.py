"""
PARAKH Synthetic Credit Application Generator - Forward Target & Outcome Generator
Implements Stage I (Forward Cash-flow Accounting Simulator) and Stage J (Target Generation).

Strictly adheres to:
- docs/final-ml-data-requirements.md (v1.1.0 Frozen Specification, Section 10, 11, 15, 21)
- Person 3 Authoritative Parameter Clarification Addendum
- P2-T02 Approved Architecture and Schema Freeze

Causal Forward Timeline:
    Simulation runs strictly across t in (t0, t0 + T_pred] where T_pred in [30, 90] days.
    Buffer update: B_t = B_{t-1} + I_t - E_t - O_t - S_t
    Default trigger: min_t B_t < 0 and consecutive days(B_t < 0) >= 7 (Insolvency Grace Period).

Anti-Leakage Guarantees:
- Temporal barrier: All forward simulation variables (I_t, E_t, O_t, S_t, B_t) exist strictly after t0.
- Zero feature leakage: Predictor features do not consume forward outcomes.
- Independent PRNG: Target generation utilizes dedicated application-level RNG streams.
- Insufficient Data cohort records remain unscored (target_default_flag = None, repayment_risk_probability = None).
"""

from datetime import datetime, timezone, timedelta
import hashlib
import math
import random
from typing import Dict, List, Optional, Tuple, Any

from src.data.synthetic.config import (
    MASTER_SEED,
    COHORT_HEALTHY_VOLATILE,
    COHORT_STABLE,
    COHORT_DECLINING,
    COHORT_IRREGULAR,
    COHORT_HIGH_OBLIGATION,
    COHORT_INSUFFICIENT_DATA,
    FORWARD_EARNINGS_AR_ALPHA,
    FORWARD_EARNINGS_BASE_SIGMA_RATIO,
    FORWARD_EARNINGS_JUMP_PROBABILITY,
    FORWARD_EARNINGS_JUMP_MAGNITUDE_MIN,
    FORWARD_EARNINGS_JUMP_MAGNITUDE_MAX,
    DECLINING_COHORT_TRAJECTORY_DRIFT,
    SHOCK_DAILY_LAMBDA,
    SHOCK_PARETO_SCALE,
    SHOCK_PARETO_SHAPE,
    SHOCK_HARD_CAP,
    SHOCK_COHORT_MODIFIERS,
    INSOLVENCY_GRACE_PERIOD_DAYS,
    PREDICTION_HORIZON_DAYS_MIN,
    PREDICTION_HORIZON_DAYS_MAX,
)
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ForwardOutcome,
)


def get_target_rng(master_seed: int, application_id: str) -> random.Random:
    """
    Derives an isolated, deterministic PRNG instance for the forward target simulation
    of a specific loan application.
    Eliminates cross-application RNG coupling and guarantees bit-for-bit reproducibility.
    """
    payload = f"{master_seed}:target:{application_id}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    app_seed = (int(digest[:8], 16) % 2147483647) + 1
    return random.Random(app_seed)


def compute_prediction_horizon(loan_tenure_months: int) -> int:
    """
    Computes the forward prediction horizon T_pred matching the loan tenure.
    Bounded strictly in [30, 90] days per Section 10.3:
    - 1 month: 30 days
    - 2 months: 60 days
    - 3, 4, 6, 12 months: 90 days
    """
    raw_days = loan_tenure_months * 30
    return min(PREDICTION_HORIZON_DAYS_MAX, max(PREDICTION_HORIZON_DAYS_MIN, raw_days))


def simulate_single_forward_path(
    application: Application,
    applicant_profile: ApplicantProfile,
    rng: random.Random,
    horizon_days: int,
) -> Tuple[int, bool, float]:
    """
    Simulates a single forward cash-flow realization day-by-day across t in [1, horizon_days].

    At each daily simulation step t in {1, 2, ..., horizon_days}:
        B_t = B_{t-1} + I_t - E_t - O_t - S_t

    Where:
        B_0: Verified starting cashflow buffer at cutoff timestamp t0.
        I_t: Daily realized earnings ~ AR(1) process with Poisson jumps.
        E_t: Daily non-discretionary living expenses = monthly_living_expense / 30.0.
        O_t: Contractual debt obligations = application.daily_debt_obligation.
        S_t: Exogenous negative shock ~ Poisson-Pareto shock process.

    Returns:
        (max_consecutive_neg, is_default, min_buffer)
    """
    cohort = applicant_profile.cohort_archetype
    mu_0 = applicant_profile.baseline_weekly_income / 6.0
    sigma_base = FORWARD_EARNINGS_BASE_SIGMA_RATIO * mu_0
    alpha = FORWARD_EARNINGS_AR_ALPHA
    jump_p = FORWARD_EARNINGS_JUMP_PROBABILITY
    drift = DECLINING_COHORT_TRAJECTORY_DRIFT if cohort == COHORT_DECLINING else 0.0

    E_t = applicant_profile.monthly_living_expense / 30.0
    O_t = application.daily_debt_obligation

    cohort_shock_mod = SHOCK_COHORT_MODIFIERS.get(cohort, 1.0)
    lambda_shock = SHOCK_DAILY_LAMBDA * cohort_shock_mod
    p_shock = 1.0 - math.exp(-lambda_shock)

    B_t = applicant_profile.starting_cashflow_buffer
    I_prev = mu_0
    consec_neg = 0
    max_consec_neg = 0
    min_buffer = B_t

    for t in range(1, horizon_days + 1):
        # 1. Forward AR(1) Realized Daily Earnings
        eps = rng.gauss(0.0, sigma_base)
        jump = 0.0
        if rng.random() < jump_p:
            mag = rng.uniform(FORWARD_EARNINGS_JUMP_MAGNITUDE_MIN, FORWARD_EARNINGS_JUMP_MAGNITUDE_MAX) * mu_0
            jump = mag if rng.random() < 0.5 else -mag

        mu_t = mu_0 * (1.0 + drift * t)
        I_t = max(0.0, mu_t + alpha * (I_prev - mu_t) + eps + jump)
        I_prev = I_t

        # 2. Exogenous Poisson-Pareto Financial Shock
        S_t = 0.0
        if rng.random() < p_shock:
            raw_shock = SHOCK_PARETO_SCALE * rng.paretovariate(SHOCK_PARETO_SHAPE)
            S_t = min(SHOCK_HARD_CAP, raw_shock)

        # 3. Liquidity Buffer Update
        B_t = B_t + I_t - E_t - O_t - S_t
        if B_t < min_buffer:
            min_buffer = B_t

        # 4. Cash-Flow Insolvency Condition Tracking
        if B_t < 0.0:
            consec_neg += 1
            if consec_neg > max_consec_neg:
                max_consec_neg = consec_neg
        else:
            consec_neg = 0

    is_default = (max_consec_neg >= INSOLVENCY_GRACE_PERIOD_DAYS)
    return max_consec_neg, is_default, min_buffer


def simulate_forward_outcome(
    application: Application,
    applicant_profile: ApplicantProfile,
    master_seed: int = MASTER_SEED,
    n_mc_paths: int = 20,
) -> ForwardOutcome:
    """
    Generates the future outcome and target labels for a single loan application strictly after t0.

    Adheres strictly to docs/final-ml-data-requirements.md Section 10:
    - Prediction horizon T_pred in [30, 90] days matching loan tenure.
    - Cash-flow insolvency condition: >= 7 consecutive days of negative liquidity buffer.
    - Insufficient Data cohort records are unscored (target_default_flag = None, repayment_risk_probability = None).
    - Continuous risk probability calibrated via Monte Carlo ensemble and liquidity cushion.

    Parameters:
        application: Application record anchored at cutoff timestamp t0.
        applicant_profile: Baseline profile and financial parameters.
        master_seed: Deterministic master seed (42).
        n_mc_paths: Number of Monte Carlo simulation paths (default: 20). Path 0 defines realized outcome.

    Returns:
        ForwardOutcome dataclass instance.
    """
    if application.applicant_profile_id != applicant_profile.applicant_profile_id:
        raise ValidationError(
            f"Mismatched applicant profile ID: application {application.application_id} "
            f"references profile {application.applicant_profile_id}, but received {applicant_profile.applicant_profile_id}"
        )

    horizon_days = compute_prediction_horizon(application.loan_tenure_months)
    cohort = applicant_profile.cohort_archetype

    # Thin-file / Insufficient Data cohort is unscored by ML contract (Section 10, Decision D5)
    if cohort == COHORT_INSUFFICIENT_DATA:
        outcome = ForwardOutcome(
            application_id=application.application_id,
            prediction_horizon_days=horizon_days,
            consecutive_negative_days=0,
            target_default_flag=None,
            repayment_risk_probability=None,
            cutoff_timestamp=application.cutoff_timestamp,
        )
        validate_forward_outcome(outcome, cohort)
        return outcome

    # Isolated application-level deterministic PRNG
    rng = get_target_rng(master_seed, application.application_id)

    # Path 0: Primary realized outcome trajectory
    path0_max_neg, path0_default, path0_min_b = simulate_single_forward_path(
        application=application,
        applicant_profile=applicant_profile,
        rng=rng,
        horizon_days=horizon_days,
    )

    target_default_flag = 1 if path0_default else 0
    consecutive_negative_days = path0_max_neg

    # Multi-path Monte Carlo ensemble for continuous calibrated risk probability
    if n_mc_paths > 1:
        path_defaults = 1 if path0_default else 0
        min_buffers = [path0_min_b]

        for _ in range(n_mc_paths - 1):
            _, is_def, min_b = simulate_single_forward_path(
                application=application,
                applicant_profile=applicant_profile,
                rng=rng,
                horizon_days=horizon_days,
            )
            if is_def:
                path_defaults += 1
            min_buffers.append(min_b)

        p_mc = path_defaults / float(n_mc_paths)
        avg_min_b = sum(min_buffers) / float(len(min_buffers))
        cushion = avg_min_b / (application.contractual_emi + 1.0)
        p_sig = 1.0 / (1.0 + math.exp(min(50.0, max(-50.0, 1.2 * cushion))))

        p_raw = 0.80 * p_mc + 0.20 * p_sig
        if target_default_flag == 1:
            risk_prob = round(min(max(p_raw, 0.0500), 0.9999), 4)
        else:
            risk_prob = round(min(max(p_raw, 0.0001), 0.9500), 4)
    else:
        # Single path mode
        cushion = path0_min_b / (application.contractual_emi + 1.0)
        p_sig = 1.0 / (1.0 + math.exp(min(50.0, max(-50.0, 1.2 * cushion))))
        if target_default_flag == 1:
            risk_prob = round(min(max(p_sig, 0.5000), 0.9999), 4)
        else:
            risk_prob = round(min(max(p_sig, 0.0001), 0.4999), 4)

    outcome = ForwardOutcome(
        application_id=application.application_id,
        prediction_horizon_days=horizon_days,
        consecutive_negative_days=consecutive_negative_days,
        target_default_flag=target_default_flag,
        repayment_risk_probability=risk_prob,
        cutoff_timestamp=application.cutoff_timestamp,
    )
    validate_forward_outcome(outcome, cohort)
    return outcome


def generate_forward_outcomes(
    applications: List[Application],
    profiles: Dict[str, ApplicantProfile],
    master_seed: int = MASTER_SEED,
    n_mc_paths: int = 20,
) -> List[ForwardOutcome]:
    """
    Generates forward simulation outcomes and target labels for a batch of applications.
    """
    outcomes: List[ForwardOutcome] = []
    for app in applications:
        profile = profiles[app.applicant_profile_id]
        outcome = simulate_forward_outcome(
            application=app,
            applicant_profile=profile,
            master_seed=master_seed,
            n_mc_paths=n_mc_paths,
        )
        outcomes.append(outcome)
    return outcomes


def validate_forward_outcome(outcome: ForwardOutcome, cohort_archetype: str) -> None:
    """
    Validates a forward outcome record against the frozen ML data contract.
    Raises ImpossibleCombinationError or ValidationError on contract violations.
    """
    # 1. Prediction horizon bounds
    if not (PREDICTION_HORIZON_DAYS_MIN <= outcome.prediction_horizon_days <= PREDICTION_HORIZON_DAYS_MAX):
        raise ImpossibleCombinationError(
            f"Prediction horizon {outcome.prediction_horizon_days} out of bounds "
            f"[{PREDICTION_HORIZON_DAYS_MIN}, {PREDICTION_HORIZON_DAYS_MAX}]"
        )

    # 2. Consecutive negative days bounds
    if outcome.consecutive_negative_days < 0 or outcome.consecutive_negative_days > outcome.prediction_horizon_days:
        raise ImpossibleCombinationError(
            f"consecutive_negative_days {outcome.consecutive_negative_days} must be within "
            f"[0, {outcome.prediction_horizon_days}]"
        )

    # 3. Insufficient Data cohort routing (thin-file un-scored)
    if cohort_archetype == COHORT_INSUFFICIENT_DATA:
        if outcome.target_default_flag is not None:
            raise ImpossibleCombinationError(
                f"Insufficient Data cohort must have null target_default_flag, found {outcome.target_default_flag}"
            )
        if outcome.repayment_risk_probability is not None:
            raise ImpossibleCombinationError(
                f"Insufficient Data cohort must have null repayment_risk_probability, found {outcome.repayment_risk_probability}"
            )
        return

    # 4. Scored cohorts contract
    if outcome.target_default_flag is None:
        raise ImpossibleCombinationError(
            f"Scored cohort '{cohort_archetype}' cannot have null target_default_flag"
        )

    if outcome.target_default_flag not in (0, 1):
        raise ImpossibleCombinationError(
            f"target_default_flag must be 0 or 1, found {outcome.target_default_flag}"
        )

    if outcome.repayment_risk_probability is None:
        raise ImpossibleCombinationError(
            f"Scored cohort '{cohort_archetype}' cannot have null repayment_risk_probability"
        )

    if not (0.0 <= outcome.repayment_risk_probability <= 1.0):
        raise ImpossibleCombinationError(
            f"repayment_risk_probability {outcome.repayment_risk_probability} must be bounded in [0.0, 1.0]"
        )

    # 5. Default trigger logic consistency
    if outcome.target_default_flag == 1:
        if outcome.consecutive_negative_days < INSOLVENCY_GRACE_PERIOD_DAYS:
            raise ImpossibleCombinationError(
                f"Default flag Y=1 requires consecutive_negative_days >= {INSOLVENCY_GRACE_PERIOD_DAYS}, "
                f"found {outcome.consecutive_negative_days}"
            )
    else:  # target_default_flag == 0
        if outcome.consecutive_negative_days >= INSOLVENCY_GRACE_PERIOD_DAYS:
            raise ImpossibleCombinationError(
                f"Non-default flag Y=0 cannot have consecutive_negative_days >= {INSOLVENCY_GRACE_PERIOD_DAYS}, "
                f"found {outcome.consecutive_negative_days}"
            )
