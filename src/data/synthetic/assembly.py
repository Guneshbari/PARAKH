"""
PARAKH Synthetic Credit Application Generator - Application-Level Dataset Assembly (P2-T08).
Combines the outputs of:
- P2-T04: Applicant profile & loan application identity and metadata
- P2-T05: Trailing 90-day telemetry and cutoff timestamp t0
- P2-T06: Deterministic 40-feature vector
- P2-T07: Forward cash-flow simulation outcome and target_default_flag

Guarantees:
1. One application produces exactly one assembled record.
2. Exact 52-column schema adhering strictly to docs/final-ml-data-requirements.md (v1.1.0).
3. Repeat applications remain distinct separate records with verified temporal spacing.
4. Feature values and target values are preserved unchanged from upstream stages.
5. Incomplete observation / Insufficient Data cohort records preserve null target semantics.
6. Zero data leakage: predictors < t0, targets strictly post-t0.
7. Comprehensive 14-point validation gate.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any

from src.data.synthetic.config import (
    APPLICATION_TIMESTAMP_START,
    APPLICATION_TIMESTAMP_END,
    COHORT_INSUFFICIENT_DATA,
    COHORT_ARCHETYPES,
    GIG_WORK_TYPES,
    LOAN_PURPOSES,
    LOAN_TENURES,
    LOAN_AMOUNT_MIN,
    LOAN_AMOUNT_MAX,
    INSOLVENCY_GRACE_PERIOD_DAYS,
    PREDICTION_HORIZON_DAYS_MIN,
    PREDICTION_HORIZON_DAYS_MAX,
    REPEAT_INTERVAL_DAYS_MIN,
)
from src.data.synthetic.exceptions import (
    ImpossibleCombinationError,
    SchemaError,
    TemporalLeakageError,
    ValidationError,
)
from src.data.synthetic.schemas import (
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    DerivedFeatures,
    ForwardOutcome,
    FinalRecord,
    AssembledApplicationRecord,
    FINAL_DATASET_SCHEMA,
    DataType,
    get_column_names,
)
from src.data.synthetic.feature_derivation import validate_derived_features


def assemble_application_record(
    application: Application,
    applicant_profile: ApplicantProfile,
    features: ApplicationFeatures,
    outcome: ForwardOutcome,
) -> AssembledApplicationRecord:
    """
    Assembles a single application-level record by unifying Stage B-J outputs.

    Parameters:
        application: Stage F Application financing event.
        applicant_profile: Stage D ApplicantProfile demographic and baseline context.
        features: Stage G/H ApplicationFeatures containing 40 derived ML features.
        outcome: Stage I/J ForwardOutcome containing future simulation targets.

    Returns:
        Validated AssembledApplicationRecord dataclass instance.
    """
    # 1. Relational Integrity Checks
    if application.applicant_profile_id != applicant_profile.applicant_profile_id:
        raise ValidationError(
            f"Applicant profile ID mismatch: application references '{application.applicant_profile_id}', "
            f"but received profile '{applicant_profile.applicant_profile_id}'"
        )
    if features.application_id != application.application_id:
        raise ValidationError(
            f"Feature application ID mismatch: expected '{application.application_id}', "
            f"got '{features.application_id}'"
        )
    if features.applicant_profile_id != application.applicant_profile_id:
        raise ValidationError(
            f"Feature applicant profile ID mismatch: expected '{application.applicant_profile_id}', "
            f"got '{features.applicant_profile_id}'"
        )
    if outcome.application_id != application.application_id:
        raise ValidationError(
            f"Outcome application ID mismatch: expected '{application.application_id}', "
            f"got '{outcome.application_id}'"
        )

    # 2. Temporal Cutoff Integrity Checks
    if features.cutoff_timestamp != application.cutoff_timestamp:
        raise TemporalLeakageError(
            f"Feature cutoff timestamp mismatch: application has '{application.cutoff_timestamp}', "
            f"features have '{features.cutoff_timestamp}'"
        )
    if outcome.cutoff_timestamp is not None and outcome.cutoff_timestamp != application.cutoff_timestamp:
        raise TemporalLeakageError(
            f"Outcome cutoff timestamp mismatch: application has '{application.cutoff_timestamp}', "
            f"outcome has '{outcome.cutoff_timestamp}'"
        )

    # 3. Assemble unified record
    record = AssembledApplicationRecord(
        application_id=application.application_id,
        applicant_profile_id=application.applicant_profile_id,
        cutoff_timestamp=application.cutoff_timestamp,
        cohort_archetype=applicant_profile.cohort_archetype,
        gig_work_type=applicant_profile.gig_work_type,
        years_working=applicant_profile.years_working,
        average_working_days=applicant_profile.average_working_days,
        requested_loan_amount=application.requested_loan_amount,
        loan_tenure_months=application.loan_tenure_months,
        loan_purpose=application.loan_purpose,
        features=features.features,
        target_default_flag=outcome.target_default_flag,
        repayment_risk_probability=outcome.repayment_risk_probability,
        prediction_horizon_days=outcome.prediction_horizon_days,
        consecutive_negative_days=outcome.consecutive_negative_days,
    )

    # 4. Validate assembled record against frozen schema
    validate_assembled_record(record)
    return record


def assemble_dataset(
    applications: List[Application],
    profiles: Dict[str, ApplicantProfile],
    features: Dict[str, ApplicationFeatures],
    outcomes: Dict[str, ForwardOutcome],
    deterministic_sort: bool = False,
) -> List[AssembledApplicationRecord]:
    """
    Combines application, profile, feature, and outcome entities into a validated dataset.

    Parameters:
        applications: List of Application financing events.
        profiles: Mapping from applicant_profile_id to ApplicantProfile.
        features: Mapping from application_id to ApplicationFeatures.
        outcomes: Mapping from application_id to ForwardOutcome.
        deterministic_sort: If True, stably sorts output records by application_id.

    Returns:
        List of validated AssembledApplicationRecord instances.
    """
    records: List[AssembledApplicationRecord] = []

    for app in applications:
        if app.applicant_profile_id not in profiles:
            raise ValidationError(
                f"Missing ApplicantProfile for applicant_profile_id '{app.applicant_profile_id}'"
            )
        if app.application_id not in features:
            raise ValidationError(
                f"Missing ApplicationFeatures for application_id '{app.application_id}'"
            )
        if app.application_id not in outcomes:
            raise ValidationError(
                f"Missing ForwardOutcome for application_id '{app.application_id}'"
            )

        prof = profiles[app.applicant_profile_id]
        feat = features[app.application_id]
        out = outcomes[app.application_id]

        record = assemble_application_record(
            application=app,
            applicant_profile=prof,
            features=feat,
            outcome=out,
        )
        records.append(record)

    if deterministic_sort:
        records.sort(key=lambda r: r.application_id)

    validate_assembled_dataset(records)
    return records


def validate_assembled_record(record: AssembledApplicationRecord) -> None:
    """
    Validates a single assembled record against physical, relational, and schema bounds.
    Raises SchemaError, ValidationError, or ImpossibleCombinationError on contract violation.
    """
    # 1. Identity & Cutoff validation
    if not record.application_id or not isinstance(record.application_id, str):
        raise ValidationError("application_id must be a non-empty string")
    if not record.applicant_profile_id or not isinstance(record.applicant_profile_id, str):
        raise ValidationError("applicant_profile_id must be a non-empty string")

    try:
        t0_dt = datetime.fromisoformat(record.cutoff_timestamp.replace("Z", "+00:00"))
    except Exception as e:
        raise ValidationError(f"Invalid ISO-8601 cutoff_timestamp '{record.cutoff_timestamp}': {e}")

    start_dt = datetime.fromisoformat(APPLICATION_TIMESTAMP_START.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(APPLICATION_TIMESTAMP_END.replace("Z", "+00:00"))
    if not (start_dt <= t0_dt <= end_dt):
        raise TemporalLeakageError(
            f"cutoff_timestamp '{record.cutoff_timestamp}' is out of frozen bounds "
            f"[{APPLICATION_TIMESTAMP_START}, {APPLICATION_TIMESTAMP_END}]"
        )

    # 2. Metadata & Profile Categoricals & Ranges
    if record.cohort_archetype not in COHORT_ARCHETYPES:
        raise ValidationError(f"Invalid cohort_archetype: '{record.cohort_archetype}'")
    if record.gig_work_type not in GIG_WORK_TYPES:
        raise ValidationError(f"Invalid gig_work_type: '{record.gig_work_type}'")
    if record.loan_purpose is not None and record.loan_purpose not in LOAN_PURPOSES:
        raise ValidationError(f"Invalid loan_purpose: '{record.loan_purpose}'")
    if record.loan_tenure_months not in LOAN_TENURES:
        raise ValidationError(f"Invalid loan_tenure_months: {record.loan_tenure_months}")
    if not (LOAN_AMOUNT_MIN <= record.requested_loan_amount <= LOAN_AMOUNT_MAX):
        raise ValidationError(
            f"requested_loan_amount {record.requested_loan_amount} out of bounds [{LOAN_AMOUNT_MIN}, {LOAN_AMOUNT_MAX}]"
        )
    if record.years_working is not None and not (0.0 <= record.years_working <= 50.0):
        raise ValidationError(f"years_working {record.years_working} out of bounds [0.0, 50.0]")
    if record.average_working_days is not None and not (0 <= record.average_working_days <= 31):
        raise ValidationError(f"average_working_days {record.average_working_days} out of bounds [0, 31]")

    # 3. Deterministic 40 Derived Features Validation
    try:
        validate_derived_features(record.features)
    except AssertionError as e:
        raise ImpossibleCombinationError(f"Invalid derived features: {e}") from e

    # 4. Target & Outcome Consistency
    if not (PREDICTION_HORIZON_DAYS_MIN <= record.prediction_horizon_days <= PREDICTION_HORIZON_DAYS_MAX):
        raise ImpossibleCombinationError(
            f"prediction_horizon_days {record.prediction_horizon_days} out of bounds "
            f"[{PREDICTION_HORIZON_DAYS_MIN}, {PREDICTION_HORIZON_DAYS_MAX}]"
        )
    if not (0 <= record.consecutive_negative_days <= record.prediction_horizon_days):
        raise ImpossibleCombinationError(
            f"consecutive_negative_days {record.consecutive_negative_days} must be in [0, {record.prediction_horizon_days}]"
        )

    if record.cohort_archetype == COHORT_INSUFFICIENT_DATA:
        if record.target_default_flag is not None:
            raise ImpossibleCombinationError(
                f"Insufficient Data cohort record must have null target_default_flag, got {record.target_default_flag}"
            )
        if record.repayment_risk_probability is not None:
            raise ImpossibleCombinationError(
                f"Insufficient Data cohort record must have null repayment_risk_probability, got {record.repayment_risk_probability}"
            )
    else:
        if record.target_default_flag is None:
            raise ImpossibleCombinationError(
                f"Scored cohort '{record.cohort_archetype}' cannot have null target_default_flag"
            )
        if record.target_default_flag not in (0, 1):
            raise ImpossibleCombinationError(
                f"target_default_flag must be 0 or 1, got {record.target_default_flag}"
            )
        if record.repayment_risk_probability is None:
            raise ImpossibleCombinationError(
                f"Scored cohort '{record.cohort_archetype}' cannot have null repayment_risk_probability"
            )
        if not (0.0 <= record.repayment_risk_probability <= 1.0):
            raise ImpossibleCombinationError(
                f"repayment_risk_probability {record.repayment_risk_probability} out of [0.0, 1.0]"
            )
        if record.consecutive_negative_days >= INSOLVENCY_GRACE_PERIOD_DAYS and record.target_default_flag != 1:
            raise ImpossibleCombinationError(
                f"consecutive_negative_days >= {INSOLVENCY_GRACE_PERIOD_DAYS} requires target_default_flag = 1"
            )
        if record.consecutive_negative_days < INSOLVENCY_GRACE_PERIOD_DAYS and record.target_default_flag != 0:
            raise ImpossibleCombinationError(
                f"consecutive_negative_days < {INSOLVENCY_GRACE_PERIOD_DAYS} requires target_default_flag = 0"
            )

    # 5. Schema Alignment & 52-Column Structure Check
    record_dict = record.to_dict()
    schema_cols = get_column_names()

    if len(record_dict) != 52:
        raise SchemaError(f"Assembled record must contain exactly 52 columns, found {len(record_dict)}")

    missing_cols = set(schema_cols) - set(record_dict.keys())
    if missing_cols:
        raise SchemaError(f"Assembled record missing frozen columns: {missing_cols}")

    extra_cols = set(record_dict.keys()) - set(schema_cols)
    if extra_cols:
        raise SchemaError(f"Assembled record contains unexpected columns: {extra_cols}")

    # Check physical data types against FINAL_DATASET_SCHEMA
    for col_def in FINAL_DATASET_SCHEMA:
        val = record_dict[col_def.name]
        if val is None:
            if not col_def.nullable:
                raise SchemaError(f"Non-nullable column '{col_def.name}' contains None")
            continue

        if col_def.dtype == DataType.STRING:
            if not isinstance(val, str):
                raise SchemaError(f"Column '{col_def.name}' expected string, got {type(val).__name__}")
        elif col_def.dtype == DataType.INT64:
            if not isinstance(val, int) or isinstance(val, bool):
                raise SchemaError(f"Column '{col_def.name}' expected int, got {type(val).__name__}")
        elif col_def.dtype == DataType.FLOAT64:
            if not isinstance(val, (float, int)) or isinstance(val, bool):
                raise SchemaError(f"Column '{col_def.name}' expected float, got {type(val).__name__}")


def validate_assembled_dataset(records: List[AssembledApplicationRecord]) -> None:
    """
    Validates dataset-level properties across a collection of assembled records.
    Ensures application uniqueness, repeat applicant temporal ordering, and individual compliance.
    """
    if not records:
        raise ValidationError("Dataset must contain at least 1 record")

    # 1. Application ID Uniqueness
    seen_app_ids: Set[str] = set()
    applicant_apps: Dict[str, List[AssembledApplicationRecord]] = {}

    for record in records:
        if record.application_id in seen_app_ids:
            raise ImpossibleCombinationError(
                f"Duplicate application_id detected: '{record.application_id}'"
            )
        seen_app_ids.add(record.application_id)

        if record.applicant_profile_id not in applicant_apps:
            applicant_apps[record.applicant_profile_id] = []
        applicant_apps[record.applicant_profile_id].append(record)

        # Validate record individually
        validate_assembled_record(record)

    # 2. Repeat Applicant Temporal Integrity
    for prof_id, apps in applicant_apps.items():
        if len(apps) > 1:
            # Sort by cutoff timestamp
            apps_sorted = sorted(
                apps,
                key=lambda r: datetime.fromisoformat(r.cutoff_timestamp.replace("Z", "+00:00")),
            )
            for i in range(len(apps_sorted) - 1):
                t1 = datetime.fromisoformat(apps_sorted[i].cutoff_timestamp.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(apps_sorted[i + 1].cutoff_timestamp.replace("Z", "+00:00"))
                delta_days = (t2 - t1).total_seconds() / 86400.0

                if delta_days < REPEAT_INTERVAL_DAYS_MIN:
                    raise TemporalLeakageError(
                        f"Repeat applicant '{prof_id}' has application interval {delta_days:.1f} days, "
                        f"violating minimum spacing of {REPEAT_INTERVAL_DAYS_MIN} days"
                    )
