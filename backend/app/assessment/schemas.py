"""Input and output contracts for the credit assessment engine."""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.assessment.exceptions import AssessmentInputError
from app.models.assessment import RiskLevel
from app.schemas.assessment import CreditAssessmentCreate

# Prohibited fields for strict data-minimization compliance
PROHIBITED_FIELDS: Set[str] = {
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


def _check_for_prohibited_keys(data: Any, path: str = "") -> None:
    """Recursively scan dictionaries and objects for prohibited privacy-invasive fields."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PROHIBITED_FIELDS:
                raise AssessmentInputError(
                    f"Prohibited privacy-invasive field '{key}' rejected by data-minimization policy."
                )
            if isinstance(value, (dict, list)):
                _check_for_prohibited_keys(value, f"{path}.{key}" if path else key)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                _check_for_prohibited_keys(item, path)


class AssessmentInput(BaseModel):
    """Normalized, data-minimization-compliant input required for credit assessment.

    Contains exclusively aggregate signals, derived attributes, and loan terms.
    Rejects any raw transactions, banking credentials, merchant descriptions,
    or location data.
    """

    model_config = ConfigDict(extra="forbid")

    # Identifiers
    application_id: Optional[UUID] = Field(
        None,
        description="Application identifier for traceability",
    )
    applicant_profile_id: Optional[UUID] = Field(
        None,
        description="Applicant profile identifier",
    )

    # Loan terms
    requested_loan_amount: Decimal = Field(
        ...,
        gt=0,
        description="Requested financing principal (must be > 0)",
    )
    loan_tenure_months: Optional[int] = Field(
        None,
        gt=0,
        le=120,
        description="Loan tenure duration in months",
    )
    loan_purpose: Optional[str] = Field(
        None,
        max_length=255,
        description="Declared commercial/operational loan purpose",
    )

    # Work profile indicators
    gig_work_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Gig sector or platform work classification",
    )
    years_working: Optional[Decimal] = Field(
        None,
        ge=0,
        le=50,
        description="Tenure in gig economy in years",
    )
    average_working_days: Optional[int] = Field(
        None,
        ge=0,
        le=31,
        description="Average active working days per month",
    )

    # Derived financial signals (aggregated only)
    average_income: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Aggregated monthly/periodic average earnings",
    )
    median_income: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Aggregated median earnings",
    )
    income_volatility: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Income variance or volatility index",
    )
    income_trend: Optional[str] = Field(
        None,
        max_length=50,
        description="Directional earnings trend (e.g., STABLE, GROWING)",
    )
    active_days: Optional[int] = Field(
        None,
        ge=0,
        description="Total active delivery/work days recorded",
    )
    payment_regularity: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Platform payout regularity bounded [0, 1]",
    )
    cashflow_buffer: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Estimated cash buffer or reserve capacity",
    )
    existing_obligation: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Known ongoing monthly debt obligations",
    )
    platform_rating: Optional[Decimal] = Field(
        None,
        ge=0,
        le=5,
        description="Composite platform performance rating [0, 5]",
    )
    repayment_reliability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Historical or platform repayment consistency [0, 1]",
    )

    # Pre-calculated derived features dictionary (strictly sanitized)
    derived_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional derived numeric/categorical features",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_privacy_and_prohibited_fields(cls, values: Any) -> Any:
        """Ensure no raw or privacy-invasive fields are included in the payload."""
        if isinstance(values, dict):
            _check_for_prohibited_keys(values)
        return values

    @classmethod
    def from_domain_objects(
        cls,
        application: Any,
        applicant_profile: Optional[Any] = None,
        financial_signal: Optional[Any] = None,
        derived_features: Optional[Dict[str, Any]] = None,
    ) -> "AssessmentInput":
        """Adapter factory creating an AssessmentInput from domain entities/schemas.

        Extracts loan parameters from Application, work metrics from ApplicantProfile,
        and aggregated indicators from FinancialSignal.
        """
        def _get(obj: Any, attr: str, default: Any = None) -> Any:
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(attr, default)
            val = getattr(obj, attr, default)
            # Guard against auto-created unittest.mock.MagicMock attributes
            if type(val).__name__ in ("MagicMock", "Mock"):
                return default
            return val

        app_id = _get(application, "id") or _get(application, "application_id")
        prof_id = _get(application, "applicant_profile_id") or (
            _get(applicant_profile, "id") if applicant_profile else None
        )
        loan_amount = _get(application, "requested_loan_amount")
        tenure = _get(application, "preferred_repayment_period") or _get(
            application, "loan_tenure_months"
        )
        purpose = _get(application, "loan_purpose")

        return cls(
            application_id=app_id,
            applicant_profile_id=prof_id,
            requested_loan_amount=loan_amount,
            loan_tenure_months=tenure,
            loan_purpose=purpose,
            gig_work_type=_get(applicant_profile, "gig_work_type"),
            years_working=_get(applicant_profile, "years_working"),
            average_working_days=_get(applicant_profile, "average_working_days"),
            average_income=_get(financial_signal, "average_income"),
            median_income=_get(financial_signal, "median_income"),
            income_volatility=_get(financial_signal, "income_volatility"),
            income_trend=_get(financial_signal, "income_trend"),
            active_days=_get(financial_signal, "active_days"),
            payment_regularity=_get(financial_signal, "payment_regularity"),
            cashflow_buffer=_get(financial_signal, "cashflow_buffer"),
            existing_obligation=_get(financial_signal, "existing_obligation"),
            platform_rating=_get(financial_signal, "platform_rating"),
            repayment_reliability=_get(financial_signal, "repayment_reliability"),
            derived_features=derived_features or {},
        )


class AssessmentResult(BaseModel):
    """Standardized output evaluation returned by an AssessmentEngine.

    Maps cleanly to the CreditAssessment domain model and response schemas while
    supporting explainability metadata and model provenance.
    """

    model_config = ConfigDict(extra="forbid")

    # Core scores
    score: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Assigned alternative credit score (0-1000, nullable if insufficient evidence)",
    )
    risk_probability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Estimated probability of default bounded [0, 1]",
    )
    confidence: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Assessment confidence level bounded [0, 1]",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Categorical risk tier (reusing domain RiskLevel enum)",
    )

    # Model provenance
    model_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name/identifier of the scoring algorithm or engine",
    )
    model_version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Semantic version string of the model used",
    )

    # Financial health ratios & intermediate indicators
    debt_to_income: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Estimated debt-to-income ratio",
    )
    utilization: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Credit utilization proxy indicator",
    )
    income_stability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Income stability index [0, 1]",
    )
    repayment_reliability: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Historical or platform repayment consistency [0, 1]",
    )

    # Explainability & decision metadata
    key_factors: List[str] = Field(
        default_factory=list,
        description="Primary driving factors influencing the score",
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed feature contributions (e.g., SHAP, feature importances)",
    )
    assessment_status: str = Field(
        default="COMPLETED",
        description="Assessment completion state",
    )

    def to_credit_assessment_create(
        self,
        application_id: Union[UUID, str],
        model_version_id: Union[UUID, str],
    ) -> CreditAssessmentCreate:
        """Convert AssessmentResult into a CreditAssessmentCreate schema.

        Bridges the framework-independent assessment output with the persistence layer.
        """
        app_id = UUID(str(application_id))
        mv_id = UUID(str(model_version_id))

        return CreditAssessmentCreate(
            application_id=app_id,
            model_version_id=mv_id,
            credit_score=self.score,
            risk_probability=self.risk_probability,
            risk_level=self.risk_level,
            confidence=self.confidence,
            debt_to_income=self.debt_to_income,
            utilization=self.utilization,
            income_stability=self.income_stability,
            repayment_reliability=self.repayment_reliability,
            assessment_status=self.assessment_status,
            explanation=self.explanation or None,
        )
