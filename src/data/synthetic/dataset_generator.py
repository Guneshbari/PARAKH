"""
PARAKH Synthetic Credit Application Generator - Dataset Generator & Serializer (P2-T10)
Coordinates the end-to-end execution of the synthetic credit-risk generation pipeline:
1. Population Generation (10,000 unique workers, 2,000 repeat borrowers, 12,000 applications)
2. Trailing 90-day Telemetry Simulation (daily events, weekly payouts)
3. Deterministic Feature Derivation (40 frozen ML features)
4. Forward Target/Outcome Simulation (prediction horizon, insolvency grace period)
5. Application-Level Dataset Assembly (canonical 52-column schema)
6. Parquet Serialization & Artifact Management
7. Comprehensive Validation Gate Verification

Strictly adheres to docs/final-ml-data-requirements.md (v1.1.0 Frozen Specification).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from src.data.synthetic.config import (
    APPLICATION_TIMESTAMP_END,
    APPLICATION_TIMESTAMP_START,
    CANONICAL_OUTPUT_PATH,
    COHORT_ARCHETYPES,
    COHORT_PROPORTIONS,
    MASTER_SEED,
    REPEAT_APPLICANTS,
    REPEAT_INTERVAL_DAYS_MAX,
    REPEAT_INTERVAL_DAYS_MIN,
    TOTAL_APPLICATIONS,
    UNIQUE_APPLICANTS,
)
from src.data.synthetic.exceptions import ValidationError
from src.data.synthetic.population_generator import generate_population
from src.data.synthetic.random_state import RandomStateManager
from src.data.synthetic.telemetry_generator import (
    DailyActivityEvent,
    WeeklyPayoutEvent,
    generate_application_history,
)
from src.data.synthetic.feature_derivation import derive_application_features
from src.data.synthetic.target_generator import simulate_forward_outcome
from src.data.synthetic.assembly import (
    assemble_application_record,
    assemble_dataset,
)
from src.data.synthetic.schemas import (
    FINAL_DATASET_SCHEMA,
    Applicant,
    ApplicantProfile,
    Application,
    ApplicationFeatures,
    ApplicationHistoricalData,
    AssembledApplicationRecord,
    DataType,
    ForwardOutcome,
    PopulationData,
    get_column_names,
)
from src.data.synthetic.validators import (
    DatasetValidationReport,
    validate_dataset,
    validate_dataset_strict,
)


@dataclass
class GenerationResult:
    """Contains paths, entities, and validation report from a full dataset generation run."""
    parquet_path: str
    row_count: int
    unique_applicants: int
    unique_applications: int
    repeat_applicants: int
    validation_report: DatasetValidationReport
    artifact_paths: Dict[str, str] = field(default_factory=dict)
    generation_seconds: float = 0.0


def create_canonical_pyarrow_schema() -> pa.Schema:
    """Constructs the exact 52-column PyArrow Schema from FINAL_DATASET_SCHEMA."""
    fields = []
    for c in FINAL_DATASET_SCHEMA:
        if c.dtype == DataType.STRING:
            t = pa.string()
        elif c.dtype == DataType.FLOAT64:
            t = pa.float64()
        elif c.dtype == DataType.INT64:
            t = pa.int64()
        else:
            raise ValueError(f"Unsupported DataType enum: {c.dtype}")
        fields.append(pa.field(c.name, t, nullable=c.nullable))
    return pa.schema(fields)


def serialize_applications_parquet(
    records: List[AssembledApplicationRecord],
    output_path: str,
    compression: str = "snappy",
) -> None:
    """Serializes 52-column application records to canonical Parquet format."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    schema = create_canonical_pyarrow_schema()
    col_names = [f.name for f in schema]

    # Transpose list-of-dicts to dict-of-lists for zero-copy Arrow table construction
    pydict: Dict[str, List[Any]] = {col: [] for col in col_names}
    for rec in records:
        d = rec.to_dict()
        for col in col_names:
            pydict[col].append(d[col])

    table = pa.Table.from_pydict(pydict, schema=schema)
    pq.write_table(table, output_path, compression=compression)


def serialize_raw_artifacts(
    population: PopulationData,
    histories: Dict[str, ApplicationHistoricalData],
    output_base_dir: str,
    compression: str = "snappy",
) -> Dict[str, str]:
    """
    Serializes raw profiles, applications, daily activity events, and weekly payouts
    into structured Parquet audit tables.
    """
    raw_dir = os.path.join(output_base_dir, "raw")
    events_dir = os.path.join(output_base_dir, "events")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(events_dir, exist_ok=True)

    artifact_paths: Dict[str, str] = {}

    # 1. Raw Applicant Profiles
    profiles_dict = {
        "applicant_profile_id": [p.applicant_profile_id for p in population.profiles],
        "cohort_archetype": [p.cohort_archetype for p in population.profiles],
        "gig_work_type": [p.gig_work_type for p in population.profiles],
        "years_working": [p.years_working for p in population.profiles],
        "average_working_days": [p.average_working_days for p in population.profiles],
        "monthly_living_expense": [p.monthly_living_expense for p in population.profiles],
        "existing_monthly_debt": [p.existing_monthly_debt for p in population.profiles],
        "starting_cashflow_buffer": [p.starting_cashflow_buffer for p in population.profiles],
        "baseline_weekly_income": [p.baseline_weekly_income for p in population.profiles],
        "platform_rating": [p.platform_rating for p in population.profiles],
        "cancellation_rate": [p.cancellation_rate for p in population.profiles],
        "payment_reliability": [p.payment_reliability for p in population.profiles],
    }
    profiles_path = os.path.join(raw_dir, "applicant_profiles.parquet")
    pq.write_table(pa.Table.from_pydict(profiles_dict), profiles_path, compression=compression)
    artifact_paths["raw_profiles"] = profiles_path

    # 2. Raw Application Financing Events
    apps_dict = {
        "application_id": [a.application_id for a in population.applications],
        "applicant_profile_id": [a.applicant_profile_id for a in population.applications],
        "application_index": [a.application_index for a in population.applications],
        "cutoff_timestamp": [a.cutoff_timestamp for a in population.applications],
        "requested_loan_amount": [a.requested_loan_amount for a in population.applications],
        "loan_tenure_months": [a.loan_tenure_months for a in population.applications],
        "loan_purpose": [a.loan_purpose for a in population.applications],
        "contractual_emi": [a.contractual_emi for a in population.applications],
        "daily_debt_obligation": [a.daily_debt_obligation for a in population.applications],
    }
    apps_path = os.path.join(raw_dir, "applications.parquet")
    pq.write_table(pa.Table.from_pydict(apps_dict), apps_path, compression=compression)
    artifact_paths["raw_applications"] = apps_path

    # 3. Raw Daily Activity Events
    daily_app_ids: List[str] = []
    daily_dates: List[str] = []
    daily_offsets: List[int] = []
    daily_actives: List[bool] = []
    daily_hours: List[float] = []
    daily_weekends: List[bool] = []
    daily_gross: List[float] = []
    daily_fee: List[float] = []
    daily_net: List[float] = []
    daily_unobserved: List[bool] = []

    for a_id, h in histories.items():
        for ev in h.daily_events:
            daily_app_ids.append(ev.application_id)
            daily_dates.append(ev.date)
            daily_offsets.append(ev.day_offset)
            daily_actives.append(ev.is_active)
            daily_hours.append(ev.hours_worked)
            daily_weekends.append(ev.is_weekend)
            daily_gross.append(ev.gross_earnings)
            daily_fee.append(ev.platform_fee)
            daily_net.append(ev.net_earnings)
            daily_unobserved.append(ev.is_unobserved)

    daily_dict = {
        "application_id": daily_app_ids,
        "date": daily_dates,
        "day_offset": daily_offsets,
        "is_active": daily_actives,
        "hours_worked": daily_hours,
        "is_weekend": daily_weekends,
        "gross_earnings": daily_gross,
        "platform_fee": daily_fee,
        "net_earnings": daily_net,
        "is_unobserved": daily_unobserved,
    }
    daily_path = os.path.join(events_dir, "daily_activity_events.parquet")
    pq.write_table(pa.Table.from_pydict(daily_dict), daily_path, compression=compression)
    artifact_paths["daily_events"] = daily_path

    # 4. Raw Weekly Settlement Payout Events
    payout_app_ids: List[str] = []
    payout_ids: List[str] = []
    payout_cycles: List[int] = []
    payout_starts: List[str] = []
    payout_ends: List[str] = []
    payout_timestamps: List[str] = []
    payout_gross: List[float] = []
    payout_net: List[float] = []
    payout_active_days: List[int] = []
    payout_settled: List[bool] = []

    for a_id, h in histories.items():
        for p in h.weekly_payouts:
            payout_app_ids.append(p.application_id)
            payout_ids.append(p.payout_id)
            payout_cycles.append(p.cycle_index)
            payout_starts.append(p.period_start)
            payout_ends.append(p.period_end)
            payout_timestamps.append(p.payout_timestamp)
            payout_gross.append(p.gross_amount)
            payout_net.append(p.net_amount)
            payout_active_days.append(p.active_days)
            payout_settled.append(p.is_settled)

    payout_dict = {
        "application_id": payout_app_ids,
        "payout_id": payout_ids,
        "cycle_index": payout_cycles,
        "period_start": payout_starts,
        "period_end": payout_ends,
        "payout_timestamp": payout_timestamps,
        "gross_amount": payout_gross,
        "net_amount": payout_net,
        "active_days": payout_active_days,
        "is_settled": payout_settled,
    }
    payout_path = os.path.join(events_dir, "weekly_payout_events.parquet")
    pq.write_table(pa.Table.from_pydict(payout_dict), payout_path, compression=compression)
    artifact_paths["weekly_payouts"] = payout_path

    return artifact_paths


def serialize_validation_artifacts(
    report: DatasetValidationReport,
    output_base_dir: str,
) -> Dict[str, str]:
    """Saves structured machine-readable and human-readable validation reports."""
    val_dir = os.path.join(output_base_dir, "validation")
    os.makedirs(val_dir, exist_ok=True)

    json_path = os.path.join(val_dir, "validation_report.json")
    with open(json_path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    txt_path = os.path.join(val_dir, "validation_report.txt")
    with open(txt_path, "w") as f:
        f.write(report.summary())

    return {
        "validation_json": json_path,
        "validation_txt": txt_path,
    }


def generate_full_synthetic_dataset(
    master_seed: int = MASTER_SEED,
    n_applicants: int = UNIQUE_APPLICANTS,
    n_repeats: int = REPEAT_APPLICANTS,
    output_parquet_path: str = CANONICAL_OUTPUT_PATH,
    serialize_raw: bool = True,
    run_strict_validation: bool = True,
    deterministic_sort: bool = True,
) -> GenerationResult:
    """
    Executes the complete synthetic data generation pipeline to produce the final dataset:
    - 10,000 unique applicants, 2,000 repeat applicants, 12,000 applications
    - Trailing 90d telemetry, 40 derived features, forward targets
    - Serializes canonical Parquet and raw/event/validation artifacts
    - Executes complete P2-T09 validation suite
    """
    start_time = time.time()
    rsm = RandomStateManager(master_seed)

    # 1. Generate Population Layer
    population = generate_population(
        random_state_manager=rsm,
        n_applicants=n_applicants,
        n_repeats=n_repeats,
    )
    profiles_by_id: Dict[str, ApplicantProfile] = {
        p.applicant_profile_id: p for p in population.profiles
    }

    # 2. Simulate Telemetry, Derive Features, Simulate Targets
    histories: Dict[str, ApplicationHistoricalData] = {}
    features: Dict[str, ApplicationFeatures] = {}
    outcomes: Dict[str, ForwardOutcome] = {}

    for app in population.applications:
        prof = profiles_by_id[app.applicant_profile_id]

        # 90-day historical time-series
        hist = generate_application_history(app, prof, master_seed=master_seed)
        histories[app.application_id] = hist

        # Deterministic 40 derived features
        feat = derive_application_features(app, prof, hist)
        features[app.application_id] = feat

        # Forward target / outcome simulation (Monte Carlo forward insolvency)
        out = simulate_forward_outcome(app, prof, master_seed=master_seed, n_mc_paths=5)
        outcomes[app.application_id] = out

    # 3. Assemble Intermediate Application Records
    assembled_records = assemble_dataset(
        applications=population.applications,
        profiles=profiles_by_id,
        features=features,
        outcomes=outcomes,
        deterministic_sort=deterministic_sort,
    )

    # 4. Serialize Primary 52-Column Parquet Table
    serialize_applications_parquet(assembled_records, output_parquet_path)
    artifact_paths: Dict[str, str] = {"primary_dataset": output_parquet_path}

    # 5. Serialize Raw Audit & Event Data
    base_dir = os.path.dirname(os.path.abspath(output_parquet_path))
    if serialize_raw:
        raw_paths = serialize_raw_artifacts(population, histories, base_dir)
        artifact_paths.update(raw_paths)

    # 6. Execute Full Validation Suite
    # Check cohort distribution against frozen contract with tolerance
    validation_report = validate_dataset(
        records=assembled_records,
        applications=population.applications,
        profiles=profiles_by_id,
        histories=histories,
        outcomes=outcomes,
        run_leakage_tests=True,
        run_determinism_test=True,
        tolerance=0.03,
        enforce_proportions=True,
    )

    # Save validation reports
    val_paths = serialize_validation_artifacts(validation_report, base_dir)
    artifact_paths.update(val_paths)

    # Save generation metadata
    metadata = {
        "master_seed": master_seed,
        "total_applications": len(assembled_records),
        "unique_applicants": len(population.applicants),
        "repeat_applicants": len(population.repeat_applicant_ids),
        "canonical_schema_columns": len(FINAL_DATASET_SCHEMA),
        "parquet_path": output_parquet_path,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - start_time, 2),
        "overall_validation_status": validation_report.overall_status,
        "default_rate": validation_report.default_rate,
        "scored_count": validation_report.scored_count,
        "unscored_count": validation_report.unscored_count,
        "default_count": validation_report.default_count,
    }
    meta_path = os.path.join(base_dir, "generation_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    artifact_paths["generation_metadata"] = meta_path

    if run_strict_validation and validation_report.overall_status == "FAIL":
        first_err = validation_report.validation_errors[0]
        raise ValidationError(f"Final dataset generation failed validation: {first_err.message}")

    elapsed = round(time.time() - start_time, 2)
    return GenerationResult(
        parquet_path=output_parquet_path,
        row_count=len(assembled_records),
        unique_applicants=len(population.applicants),
        unique_applications=len(assembled_records),
        repeat_applicants=len(population.repeat_applicant_ids),
        validation_report=validation_report,
        artifact_paths=artifact_paths,
        generation_seconds=elapsed,
    )
