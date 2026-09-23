"""
PARAKH Synthetic Data Generator - Temporal Manager
Manages:
- Application cutoff timestamp (t0) generation within [2025-01-01, 2026-09-22]
- Deterministic selection of exactly 2,000 repeat applicants
- Repeat application timestamp sequencing (t0_second > t0_first, interval in [120, 270] days)
- Timezone-aware UTC ISO-8601 formatting
"""

from datetime import datetime, timezone, timedelta
import random
from typing import Dict, List, Set, Tuple

from src.data.synthetic.config import (
    APPLICATION_TIMESTAMP_START,
    APPLICATION_TIMESTAMP_END,
    REPEAT_INTERVAL_DAYS_MIN,
    REPEAT_INTERVAL_DAYS_MAX,
    REPEAT_APPLICANTS,
    UNIQUE_APPLICANTS,
)


START_DATETIME: datetime = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATETIME: datetime = datetime(2026, 9, 22, 23, 59, 59, tzinfo=timezone.utc)
TOTAL_SPAN_SECONDS: int = int((END_DATETIME - START_DATETIME).total_seconds())


def format_iso8601(dt: datetime) -> str:
    """Format timezone-aware UTC datetime as ISO-8601 string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def select_repeat_applicants(
    n_applicants: int = UNIQUE_APPLICANTS,
    n_repeats: int = REPEAT_APPLICANTS,
    rng: random.Random = None,
) -> Set[int]:
    """
    Deterministically select exactly n_repeats applicant indices to have 2 applications.
    """
    if rng is None:
        raise ValueError("rng instance must be provided")
    indices = rng.sample(range(n_applicants), n_repeats)
    return set(indices)


def generate_single_applicant_timestamp(rng: random.Random) -> str:
    """
    Generate a single application cutoff timestamp t0 uniformly distributed
    within [START_DATETIME, END_DATETIME].
    """
    offset_seconds = rng.randint(0, TOTAL_SPAN_SECONDS)
    t0 = START_DATETIME + timedelta(seconds=offset_seconds)
    return format_iso8601(t0)


def generate_repeat_applicant_timestamps(rng: random.Random) -> Tuple[str, str, int]:
    """
    Generate two application timestamps (t0_first, t0_second) for a repeat applicant.
    Enforces:
    - interval_days in [120, 270] days
    - t0_second > t0_first strictly
    - t0_second <= END_DATETIME
    Returns (t0_first_iso, t0_second_iso, interval_days).
    """
    interval_days = rng.randint(REPEAT_INTERVAL_DAYS_MIN, REPEAT_INTERVAL_DAYS_MAX)
    total_span_days = (END_DATETIME.date() - START_DATETIME.date()).days
    max_first_days = total_span_days - interval_days
    if max_first_days < 0:
        raise ValueError("Interval exceeds total available time span in days")

    first_day_offset = rng.randint(0, max_first_days)
    first_date = START_DATETIME.date() + timedelta(days=first_day_offset)
    second_date = first_date + timedelta(days=interval_days)

    # Independent time of day for realistic shift submission timestamps
    sec_1 = rng.randint(0, 86399)
    sec_2 = rng.randint(0, 86399)

    t0_first = datetime(
        first_date.year, first_date.month, first_date.day, tzinfo=timezone.utc
    ) + timedelta(seconds=sec_1)

    t0_second = datetime(
        second_date.year, second_date.month, second_date.day, tzinfo=timezone.utc
    ) + timedelta(seconds=sec_2)

    if t0_second > END_DATETIME:
        t0_second = END_DATETIME

    assert t0_second <= END_DATETIME, "Second timestamp exceeds end boundary"
    assert t0_second > t0_first, "Second timestamp must be strictly later than first"

    return format_iso8601(t0_first), format_iso8601(t0_second), interval_days

