"""Deterministic, leakage-safe credit risk data preprocessor (Phase 3).

Follows Section 14 of the frozen ML data contract (docs/final-ml-data-requirements.md).
Features:
1. Strict train-only fitting: All scalers, imputers, and encoders fit exclusively on training data.
2. Skewed monetary compression: log(1 + x) applied to right-skewed currency features.
3. Nominal categorical encoding: One-hot encoding with handle_unknown='ignore' for zero-leakage inference.
4. Ratio scaling: RobustScaler (median / IQR) or StandardScaler fitted on training fold.
5. Missing-value handling: Median imputation with optional missingness indicators, preserving distinction
   between valid zeros and unobserved values.
6. Extreme leverage clipping: Winsorization of leverage ratios to [0.0, 5.0] to prevent division instability.
7. Insufficient evidence segregation: Identifies unscored records without altering target labels.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder, RobustScaler, StandardScaler

from src.ml.data.dataset_validator import (
    ALLOWED_GIG_WORK_TYPES,
    ALLOWED_LOAN_PURPOSES,
    DERIVED_FEATURES,
    MANDATORY_FEATURES,
    OPTIONAL_FEATURES,
)


# Monetary feature columns to log1p transform (currency INR / right-skewed)
MONETARY_LOG_COLUMNS: List[str] = [
    "feat_inc_median_90d",
    "feat_inc_p25_90d",
    "feat_inc_mean_90d",
    "feat_inc_trimmed_mean",
    "feat_inc_downside_var",
    "requested_loan_amount",
]

# Leverage ratio columns to winsorize / clip to [0.0, 5.0]
LEVERAGE_CLIP_COLUMNS: List[str] = [
    "feat_bur_total_dti",
    "feat_bur_dti_ratio",
    "feat_bur_installment_dti",
    "feat_liq_buffer_to_loan",
]

# Raw categorical columns eligible for model encoding
CATEGORICAL_INPUT_COLUMNS: List[str] = [
    "gig_work_type",
    "loan_purpose",
]

# Raw numeric columns from loan / profile context
RAW_NUMERIC_COLUMNS: List[str] = [
    "requested_loan_amount",
    "loan_tenure_months",
    "years_working",
    "average_working_days",
]

# Protected / Non-predictor columns (strictly excluded from feature matrix)
EXCLUDED_NON_PREDICTORS: Set[str] = {
    "applicant_profile_id",
    "application_id",
    "cutoff_timestamp",
    "cohort_archetype",
    "target_default_flag",
    "repayment_risk_probability",
}


class CreditRiskPreprocessor(BaseEstimator, TransformerMixin):
    """Deterministic, leakage-safe preprocessor for PARAKH credit risk assessment."""

    def __init__(
        self,
        scaler_type: str = "robust",
        apply_log_transform: bool = True,
        clip_leverage_ratios: bool = True,
        leverage_clip_bounds: Tuple[float, float] = (0.0, 5.0),
        add_missing_indicators: bool = True,
        include_raw_loan_features: bool = True,
    ) -> None:
        """Initialize preprocessing hyperparameters.

        Args:
            scaler_type: Scaling method for continuous features ('robust', 'standard', or None).
            apply_log_transform: Whether to apply log(1 + x) to skewed monetary features.
            clip_leverage_ratios: Whether to winsorize leverage ratios to bounds.
            leverage_clip_bounds: Lower and upper clipping bounds for leverage ratios (default [0.0, 5.0]).
            add_missing_indicators: Whether to generate binary missingness flags for imputed columns.
            include_raw_loan_features: Whether to include raw loan and profile features (amount, tenure, etc.).
        """
        self.scaler_type = scaler_type
        self.apply_log_transform = apply_log_transform
        self.clip_leverage_ratios = clip_leverage_ratios
        self.leverage_clip_bounds = leverage_clip_bounds
        self.add_missing_indicators = add_missing_indicators
        self.include_raw_loan_features = include_raw_loan_features

        # Fitted state
        self.is_fitted_: bool = False
        self.fitted_medians_: Dict[str, float] = {}
        self.fitted_scaler_: Optional[Union[RobustScaler, StandardScaler]] = None
        self.fitted_encoder_: Optional[OneHotEncoder] = None
        self.numeric_feature_names_in_: List[str] = []
        self.categorical_feature_names_in_: List[str] = []
        self.feature_names_in_: List[str] = []
        self.feature_names_out_: List[str] = []
        self.imputed_features_with_indicator_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Optional[Any] = None) -> "CreditRiskPreprocessor":
        """Fit preprocessor parameters strictly on training observations.

        Args:
            X: Training DataFrame containing features and metadata.
            y: Ignored (retained for scikit-learn API compatibility).

        Returns:
            self: Fitted preprocessor instance.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"X must be a pandas DataFrame, got {type(X).__name__}")

        if len(X) == 0:
            raise ValueError("Cannot fit CreditRiskPreprocessor on an empty DataFrame.")

        # 1. Identify input feature columns
        all_numeric_candidates = list(DERIVED_FEATURES)
        if self.include_raw_loan_features:
            for col in RAW_NUMERIC_COLUMNS:
                if col not in all_numeric_candidates and col in X.columns:
                    all_numeric_candidates.append(col)

        self.numeric_feature_names_in_ = [
            c for c in all_numeric_candidates if c in X.columns and c not in EXCLUDED_NON_PREDICTORS
        ]

        if self.include_raw_loan_features:
            self.categorical_feature_names_in_ = [
                c for c in CATEGORICAL_INPUT_COLUMNS if c in X.columns and c not in EXCLUDED_NON_PREDICTORS
            ]
        else:
            self.categorical_feature_names_in_ = []

        self.feature_names_in_ = self.numeric_feature_names_in_ + self.categorical_feature_names_in_

        # 2. Compute training medians for imputation
        self.fitted_medians_ = {}
        self.imputed_features_with_indicator_ = []
        for col in self.numeric_feature_names_in_:
            series = X[col]
            median_val = float(series.median())
            # Fallback to 0.0 if entire column is NaN
            if np.isnan(median_val):
                median_val = 0.0
            self.fitted_medians_[col] = median_val

            if self.add_missing_indicators and series.isna().sum() > 0:
                self.imputed_features_with_indicator_.append(col)

        # 3. Fit One-Hot Encoder for categorical inputs
        if self.categorical_feature_names_in_:
            cat_df = X[self.categorical_feature_names_in_].fillna("OTHER").astype(str)
            self.fitted_encoder_ = OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            )
            self.fitted_encoder_.fit(cat_df)
        else:
            self.fitted_encoder_ = None

        # 4. Prepare numeric matrix for scaler fitting
        numeric_df = self._process_numeric_df(X, is_fitting=True)

        # 5. Fit continuous scaler
        if self.scaler_type == "robust":
            self.fitted_scaler_ = RobustScaler()
            self.fitted_scaler_.fit(numeric_df)
        elif self.scaler_type == "standard":
            self.fitted_scaler_ = StandardScaler()
            self.fitted_scaler_.fit(numeric_df)
        elif self.scaler_type is None or self.scaler_type == "none":
            self.fitted_scaler_ = None
        else:
            raise ValueError(
                f"Unsupported scaler_type '{self.scaler_type}'. Choose 'robust', 'standard', or None."
            )

        # 6. Build output feature names
        out_names: List[str] = list(numeric_df.columns)
        if self.fitted_encoder_ is not None and self.categorical_feature_names_in_:
            encoder_cols = list(
                self.fitted_encoder_.get_feature_names_out(self.categorical_feature_names_in_)
            )
            out_names.extend(encoder_cols)

        self.feature_names_out_ = out_names
        self.is_fitted_ = True
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform observations using parameters fitted strictly on training data.

        Args:
            X: Input DataFrame (training, validation, or test split, or inference payload).

        Returns:
            pd.DataFrame: Transformed, leakage-safe numerical feature matrix.
        """
        if not self.is_fitted_:
            raise RuntimeError("CreditRiskPreprocessor must be fitted before calling transform.")

        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"X must be a pandas DataFrame, got {type(X).__name__}")

        # 1. Transform numeric features
        numeric_df = self._process_numeric_df(X, is_fitting=False)
        numeric_cols = list(numeric_df.columns)

        if self.fitted_scaler_ is not None:
            scaled_matrix = self.fitted_scaler_.transform(numeric_df)
            transformed_numeric = pd.DataFrame(
                scaled_matrix, columns=numeric_cols, index=X.index
            )
        else:
            transformed_numeric = numeric_df.copy()

        # 2. Transform categorical features
        if self.fitted_encoder_ is not None and self.categorical_feature_names_in_:
            cat_df = X[self.categorical_feature_names_in_].fillna("OTHER").astype(str)
            encoded_matrix = self.fitted_encoder_.transform(cat_df)
            encoder_cols = list(
                self.fitted_encoder_.get_feature_names_out(self.categorical_feature_names_in_)
            )
            transformed_cat = pd.DataFrame(
                encoded_matrix, columns=encoder_cols, index=X.index
            )
            result_df = pd.concat([transformed_numeric, transformed_cat], axis=1)
        else:
            result_df = transformed_numeric

        # Ensure exact feature column alignment
        return result_df[self.feature_names_out_]

    def fit_transform(self, X: pd.DataFrame, y: Optional[Any] = None) -> pd.DataFrame:
        """Fit preprocessor to data and return transformed feature matrix."""
        return self.fit(X, y).transform(X)

    def _process_numeric_df(self, X: pd.DataFrame, is_fitting: bool) -> pd.DataFrame:
        """Internal helper to apply imputation, missing indicators, log1p, and clipping."""
        processed: Dict[str, np.ndarray] = {}

        for col in self.numeric_feature_names_in_:
            if col in X.columns:
                series = X[col]
            else:
                # Column absent in inference payload; impute with fitted median
                series = pd.Series(self.fitted_medians_[col], index=X.index)

            # Detect missingness
            is_na = series.isna().values
            values = series.values.copy()

            # Impute missing values with fitted median
            median_val = self.fitted_medians_[col]
            values[is_na] = median_val
            values = values.astype(float)

            # Skewed monetary log1p compression
            if self.apply_log_transform and col in MONETARY_LOG_COLUMNS:
                # clip at 0 before log1p
                values = np.log1p(np.maximum(values, 0.0))

            # Leverage ratio clipping
            if self.clip_leverage_ratios and col in LEVERAGE_CLIP_COLUMNS:
                low, high = self.leverage_clip_bounds
                values = np.clip(values, low, high)

            processed[col] = values

            # Missingness indicator if column had missing values
            if self.add_missing_indicators and col in self.imputed_features_with_indicator_:
                indicator_col = f"{col}_was_missing"
                processed[indicator_col] = is_na.astype(float)

        return pd.DataFrame(processed, index=X.index)

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> List[str]:
        """Return the list of output feature column names produced by transform."""
        if not self.is_fitted_:
            raise RuntimeError("CreditRiskPreprocessor must be fitted before requesting feature names.")
        return list(self.feature_names_out_)

    @staticmethod
    def filter_scored_applications(df: pd.DataFrame, target_column: str = "target_default_flag") -> pd.DataFrame:
        """Filter dataset to records eligible for supervised model training (non-null targets).

        Does not alter or drop records in-place; returns a copy of scored rows.
        """
        if target_column not in df.columns:
            return df.copy()
        return df[df[target_column].notnull()].copy()

    @staticmethod
    def filter_insufficient_data_applications(
        df: pd.DataFrame, target_column: str = "target_default_flag"
    ) -> pd.DataFrame:
        """Filter dataset to insufficient-data records (null targets / insufficient history)."""
        if target_column not in df.columns:
            return pd.DataFrame(columns=df.columns)
        return df[df[target_column].isnull()].copy()

    @staticmethod
    def check_insufficient_evidence(
        record: Union[pd.Series, Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """Evaluate if an application satisfies insufficient evidence rules.

        Rules from Phase 0/1 contract:
        - Less than 30 days active history (feat_suf_observed_days < 30)
        - Fewer than 4 completed payout cycles (feat_suf_payout_count < 4)
        """
        reasons: List[str] = []
        observed_days = record.get("feat_suf_observed_days") if isinstance(record, dict) else record["feat_suf_observed_days"]
        payout_count = record.get("feat_suf_payout_count") if isinstance(record, dict) else record["feat_suf_payout_count"]

        if observed_days is not None and observed_days < 30:
            reasons.append(f"Observed days {observed_days} < 30 days minimum.")
        if payout_count is not None and payout_count < 4:
            reasons.append(f"Payout cycle count {payout_count} < 4 cycles minimum.")

        is_insufficient = len(reasons) > 0
        return is_insufficient, reasons
