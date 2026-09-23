"""Deterministic grouped dataset splitting utility for PARAKH credit risk datasets.

Implements the frozen 70/15/15 grouped split protocol (docs/final-ml-data-requirements.md).
Groups strictly by applicant_profile_id to prevent data leakage from repeated assessments.
Uses deterministic random seed 42.
"""
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from src.ml.constants import DEFAULT_RANDOM_SEED
from src.ml.data.validation import LeakageAuditReport, ModelDataValidator


@dataclass
class PartitionSummary:
    """Statistical summary for a single dataset partition."""

    name: str
    total_rows: int
    unique_applicants: int
    scored_rows: int
    insufficient_data_rows: int
    default_count: int
    default_rate: float
    cohort_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class GroupedSplitResult:
    """Container holding partitions and audit reports for a grouped dataset split."""

    train_df: pd.DataFrame
    val_df: pd.DataFrame
    test_df: pd.DataFrame
    train_applicants: Set[str]
    val_applicants: Set[str]
    test_applicants: Set[str]
    train_summary: PartitionSummary
    val_summary: PartitionSummary
    test_summary: PartitionSummary
    leakage_audit: LeakageAuditReport

    def to_dict(self) -> Dict[str, Any]:
        """Convert split results into dictionary summary."""
        return {
            "leakage_detected": self.leakage_audit.leakage_detected,
            "train": {
                "rows": self.train_summary.total_rows,
                "applicants": self.train_summary.unique_applicants,
                "scored_rows": self.train_summary.scored_rows,
                "insufficient_data_rows": self.train_summary.insufficient_data_rows,
                "defaults": self.train_summary.default_count,
                "default_rate": round(self.train_summary.default_rate, 4),
                "cohorts": self.train_summary.cohort_distribution,
            },
            "val": {
                "rows": self.val_summary.total_rows,
                "applicants": self.val_summary.unique_applicants,
                "scored_rows": self.val_summary.scored_rows,
                "insufficient_data_rows": self.val_summary.insufficient_data_rows,
                "defaults": self.val_summary.default_count,
                "default_rate": round(self.val_summary.default_rate, 4),
                "cohorts": self.val_summary.cohort_distribution,
            },
            "test": {
                "rows": self.test_summary.total_rows,
                "applicants": self.test_summary.unique_applicants,
                "scored_rows": self.test_summary.scored_rows,
                "insufficient_data_rows": self.test_summary.insufficient_data_rows,
                "defaults": self.test_summary.default_count,
                "default_rate": round(self.test_summary.default_rate, 4),
                "cohorts": self.test_summary.cohort_distribution,
            },
        }


class GroupedDatasetSplitter:
    """Splits credit risk datasets into train, validation, and test partitions grouped by applicant."""

    @classmethod
    def split(
        cls,
        df: pd.DataFrame,
        applicant_id_column: str = "applicant_profile_id",
        target_column: str = "target_default_flag",
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = DEFAULT_RANDOM_SEED,
        scored_only: bool = False,
    ) -> GroupedSplitResult:
        """Partition DataFrame into train/validation/test splits grouped by applicant ID.

        Args:
            df: Input application DataFrame.
            applicant_id_column: Column tracking applicant identity.
            target_column: Binary repayment target column name.
            train_ratio: Fraction of applicants for training (default 0.70).
            val_ratio: Fraction of applicants for validation (default 0.15).
            test_ratio: Fraction of applicants for testing (default 0.15).
            seed: Deterministic random seed (default 42).
            scored_only: If True, filters out insufficient-data records before splitting.

        Returns:
            GroupedSplitResult: Resulting partitions and leakage audit report.
        """
        if not math.isclose(train_ratio + val_ratio + test_ratio, 1.0, rel_tol=1e-5):
            raise ValueError(
                f"Split ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
            )

        working_df = df.copy()
        if scored_only and target_column in working_df.columns:
            working_df = working_df[working_df[target_column].notnull()].copy()

        if applicant_id_column not in working_df.columns:
            raise KeyError(f"Applicant column '{applicant_id_column}' not found in DataFrame.")

        # Deterministically permute unique applicants
        unique_applicants = working_df[applicant_id_column].drop_duplicates().values
        rng = np.random.RandomState(seed)
        shuffled_applicants = rng.permutation(unique_applicants)

        n_total = len(shuffled_applicants)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)
        # Allocate remaining applicants to test to guarantee complete coverage
        n_test = n_total - n_train - n_val

        train_apps = set(shuffled_applicants[:n_train])
        val_apps = set(shuffled_applicants[n_train : n_train + n_val])
        test_apps = set(shuffled_applicants[n_train + n_val :])

        train_df = working_df[working_df[applicant_id_column].isin(train_apps)].copy()
        val_df = working_df[working_df[applicant_id_column].isin(val_apps)].copy()
        test_df = working_df[working_df[applicant_id_column].isin(test_apps)].copy()

        # Audit for applicant leakage across partitions
        leakage_audit = ModelDataValidator.audit_split_leakage(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            applicant_id_column=applicant_id_column,
        )

        if leakage_audit.leakage_detected:
            raise RuntimeError(
                f"CRITICAL: Applicant identity leakage detected across splits! "
                f"Train/Val: {leakage_audit.overlapping_train_val}, "
                f"Train/Test: {leakage_audit.overlapping_train_test}, "
                f"Val/Test: {leakage_audit.overlapping_val_test}"
            )

        train_summary = cls._summarize_partition("Train", train_df, target_column, applicant_id_column)
        val_summary = cls._summarize_partition("Validation", val_df, target_column, applicant_id_column)
        test_summary = cls._summarize_partition("Test", test_df, target_column, applicant_id_column)

        return GroupedSplitResult(
            train_df=train_df,
            val_df=val_df,
            test_df=test_df,
            train_applicants=train_apps,
            val_applicants=val_apps,
            test_applicants=test_apps,
            train_summary=train_summary,
            val_summary=val_summary,
            test_summary=test_summary,
            leakage_audit=leakage_audit,
        )

    @staticmethod
    def _summarize_partition(
        name: str, df: pd.DataFrame, target_column: str, applicant_col: str
    ) -> PartitionSummary:
        """Compute statistical summary for a partition."""
        total_rows = len(df)
        unique_apps = df[applicant_col].nunique() if applicant_col in df.columns else 0

        scored_mask = df[target_column].notnull() if target_column in df.columns else pd.Series(False, index=df.index)
        scored_rows = int(scored_mask.sum())
        insuf_rows = total_rows - scored_rows

        defaults = int(df.loc[scored_mask, target_column].sum()) if scored_rows > 0 else 0
        default_rate = defaults / scored_rows if scored_rows > 0 else 0.0

        cohorts = (
            df["cohort_archetype"].value_counts().to_dict()
            if "cohort_archetype" in df.columns
            else {}
        )

        return PartitionSummary(
            name=name,
            total_rows=total_rows,
            unique_applicants=unique_apps,
            scored_rows=scored_rows,
            insufficient_data_rows=insuf_rows,
            default_count=defaults,
            default_rate=default_rate,
            cohort_distribution=cohorts,
        )
