"""Deterministic rule-based mock assessment engine for PARAKH."""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from app.assessment.base import AssessmentEngine
from app.assessment.schemas import AssessmentInput, AssessmentResult
from app.models.assessment import RiskLevel

# Explicit transparent component weights (sum to 1.00)
WEIGHT_INCOME_STABILITY = 0.25
WEIGHT_PAYMENT_RELIABILITY = 0.25
WEIGHT_WORK_STABILITY = 0.15
WEIGHT_CASHFLOW_STRENGTH = 0.15
WEIGHT_OBLIGATION_BURDEN = 0.10
WEIGHT_PLATFORM_RELIABILITY = 0.10


class MockAssessmentEngine(AssessmentEngine):
    """Deterministic rule-based mock assessment engine.

    Implements the AssessmentEngine contract for testing, validation, and demo flows
    prior to integration of trained machine learning models.

    DISCLAIMER:
    This engine evaluates creditworthiness using transparent heuristic scoring rules.
    It does NOT represent a statistical or production credit scoring model.
    """

    @property
    def engine_name(self) -> str:
        """Identifier for the mock assessment engine."""
        return "parakh-mock-engine"

    @property
    def engine_version(self) -> str:
        """Semantic version of the mock assessment engine."""
        return "1.0.0"

    def assess(self, input_data: AssessmentInput) -> AssessmentResult:
        """Execute deterministic rule-based evaluation on validated input features.

        Args:
            input_data: Validated, privacy-compliant input features.

        Returns:
            AssessmentResult: Standardized score, probability, risk tier, confidence,
                and explainability metadata.
        """
        # 1. Evidence sufficiency check
        if not self._has_sufficient_evidence(input_data):
            return self._build_insufficient_evidence_result(input_data)

        # 2. Compute individual normalized component indices [0.0, 1.0]
        inc_stability = self._calc_income_stability(input_data)
        pay_reliability = self._calc_payment_reliability(input_data)
        work_stability = self._calc_work_stability(input_data)
        cashflow_str = self._calc_cashflow_strength(input_data)
        ob_burden, debt_to_income = self._calc_obligation_burden(input_data)
        plat_reliability = self._calc_platform_reliability(input_data)

        # 3. Weighted composite index [0.0, 1.0]
        composite_index = (
            inc_stability * WEIGHT_INCOME_STABILITY
            + pay_reliability * WEIGHT_PAYMENT_RELIABILITY
            + work_stability * WEIGHT_WORK_STABILITY
            + cashflow_str * WEIGHT_CASHFLOW_STRENGTH
            + ob_burden * WEIGHT_OBLIGATION_BURDEN
            + plat_reliability * WEIGHT_PLATFORM_RELIABILITY
        )
        composite_index = max(0.0, min(1.0, composite_index))

        # 4. Alternative credit score mapped to [300, 850]
        score = int(round(300 + composite_index * 550))
        score = max(0, min(1000, score))

        # 5. Risk probability bounded in [0.05, 0.95]
        # Inversely correlated: higher composite index yields lower risk probability
        risk_prob_float = 1.0 - (composite_index * 0.90 + 0.05)
        risk_probability = Decimal(str(round(max(0.01, min(0.99, risk_prob_float)), 4)))

        # 6. Confidence based on data completeness [0.35, 0.95]
        confidence = self._calc_confidence(input_data)

        # 7. Risk level categorization reusing existing domain enum
        if score >= 700:
            risk_level = RiskLevel.LOWER
        elif score >= 550:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.HIGHER

        # 8. Deterministic key driving factors
        key_factors = self._generate_key_factors(
            inc_stability=inc_stability,
            pay_reliability=pay_reliability,
            work_stability=work_stability,
            cashflow_str=cashflow_str,
            ob_burden=ob_burden,
            plat_reliability=plat_reliability,
        )

        # 9. Structured explanation payload
        explanation: Dict[str, Any] = {
            "components": {
                "income_stability": round(inc_stability, 4),
                "payment_reliability": round(pay_reliability, 4),
                "work_stability": round(work_stability, 4),
                "cashflow_strength": round(cashflow_str, 4),
                "obligation_burden": round(ob_burden, 4),
                "platform_reliability": round(plat_reliability, 4),
            },
            "weights": {
                "income_stability": WEIGHT_INCOME_STABILITY,
                "payment_reliability": WEIGHT_PAYMENT_RELIABILITY,
                "work_stability": WEIGHT_WORK_STABILITY,
                "cashflow_strength": WEIGHT_CASHFLOW_STRENGTH,
                "obligation_burden": WEIGHT_OBLIGATION_BURDEN,
                "platform_reliability": WEIGHT_PLATFORM_RELIABILITY,
            },
            "composite_index": round(composite_index, 4),
            "debt_to_income_ratio": float(debt_to_income) if debt_to_income is not None else None,
            "engine_note": (
                "Deterministic rule-based mock evaluation for testing and demo flows. "
                "Not a live ML credit scoring model."
            ),
        }

        return AssessmentResult(
            score=score,
            risk_probability=risk_probability,
            confidence=confidence,
            risk_level=risk_level,
            model_name=self.engine_name,
            model_version=self.engine_version,
            debt_to_income=debt_to_income,
            utilization=Decimal(str(round(1.0 - ob_burden, 4))),
            income_stability=Decimal(str(round(inc_stability, 4))),
            repayment_reliability=Decimal(str(round(pay_reliability, 4))),
            key_factors=key_factors,
            explanation=explanation,
            assessment_status="COMPLETED",
        )

    # -------------------------------------------------------------------------
    # Helper Component Calculators
    # -------------------------------------------------------------------------

    def _has_sufficient_evidence(self, input_data: AssessmentInput) -> bool:
        """Determine whether input contains sufficient aggregated data to score."""
        signals_present = 0
        if input_data.average_income is not None or input_data.median_income is not None:
            signals_present += 1
        if input_data.payment_regularity is not None or input_data.repayment_reliability is not None:
            signals_present += 1
        if input_data.years_working is not None or input_data.average_working_days is not None:
            signals_present += 1
        if input_data.cashflow_buffer is not None or input_data.existing_obligation is not None:
            signals_present += 1
        if input_data.platform_rating is not None or input_data.gig_work_type is not None:
            signals_present += 1

        # Must have at least 2 distinct signal categories
        return signals_present >= 2

    def _build_insufficient_evidence_result(self, input_data: AssessmentInput) -> AssessmentResult:
        """Construct standard response for insufficient evidence scenarios."""
        confidence = self._calc_confidence(input_data)
        return AssessmentResult(
            score=None,
            risk_probability=Decimal("0.5000"),
            confidence=confidence,
            risk_level=RiskLevel.INSUFFICIENT,
            model_name=self.engine_name,
            model_version=self.engine_version,
            debt_to_income=None,
            utilization=None,
            income_stability=None,
            repayment_reliability=None,
            key_factors=[
                "Insufficient platform and financial history available to generate alternative score",
                "Additional gig platform connection or income history required",
            ],
            explanation={
                "insufficient_evidence": True,
                "reason": "At least two independent financial/platform signal categories are required.",
                "engine_note": "Cold-start or sparse profile evaluation.",
            },
            assessment_status="COMPLETED",
        )

    def _calc_income_stability(self, input_data: AssessmentInput) -> float:
        """Evaluate income level and stability [0.0, 1.0]."""
        income = float(input_data.average_income or input_data.median_income or 0)
        # 40,000 monthly income represents standard benchmark in mock scale
        base = min(1.0, income / 40000.0) if income > 0 else 0.4

        # Volatility deduction
        if input_data.income_volatility is not None:
            vol = float(input_data.income_volatility)
            base -= min(0.25, vol * 0.5)

        # Trend bonus/penalty
        if input_data.income_trend:
            trend = input_data.income_trend.upper()
            if "GROW" in trend or "UP" in trend:
                base += 0.08
            elif "STABLE" in trend:
                base += 0.04
            elif "DECLIN" in trend or "DOWN" in trend:
                base -= 0.10

        return max(0.05, min(1.0, base))

    def _calc_payment_reliability(self, input_data: AssessmentInput) -> float:
        """Evaluate payment regularity and historical repayment consistency [0.0, 1.0]."""
        regularity = (
            float(input_data.payment_regularity)
            if input_data.payment_regularity is not None
            else None
        )
        repayment = (
            float(input_data.repayment_reliability)
            if input_data.repayment_reliability is not None
            else None
        )

        if regularity is not None and repayment is not None:
            return max(0.0, min(1.0, (regularity * 0.6) + (repayment * 0.4)))
        if regularity is not None:
            return max(0.0, min(1.0, regularity))
        if repayment is not None:
            return max(0.0, min(1.0, repayment))
        return 0.50

    def _calc_work_stability(self, input_data: AssessmentInput) -> float:
        """Evaluate gig tenure and working activity [0.0, 1.0]."""
        scores: List[float] = []

        if input_data.years_working is not None:
            # 4 years benchmark gives 1.0
            scores.append(min(1.0, float(input_data.years_working) / 4.0))

        if input_data.average_working_days is not None:
            # 26 days/month active benchmark gives 1.0
            scores.append(min(1.0, float(input_data.average_working_days) / 26.0))

        if input_data.active_days is not None:
            # 300 annual active days benchmark gives 1.0
            scores.append(min(1.0, float(input_data.active_days) / 300.0))

        if scores:
            return max(0.0, min(1.0, sum(scores) / len(scores)))
        return 0.45

    def _calc_cashflow_strength(self, input_data: AssessmentInput) -> float:
        """Evaluate cash reserve buffer relative to requested financing [0.0, 1.0]."""
        buffer_val = float(input_data.cashflow_buffer or 0)
        loan_amt = float(input_data.requested_loan_amount)

        if buffer_val <= 0:
            return 0.35

        # Buffer covering 25% or more of loan amount gives top score
        coverage = buffer_val / max(1.0, loan_amt)
        return max(0.0, min(1.0, 0.40 + min(0.60, coverage * 2.4)))

    def _calc_obligation_burden(self, input_data: AssessmentInput) -> Tuple[float, Optional[Decimal]]:
        """Evaluate debt-to-income and ongoing obligation burden [0.0, 1.0]."""
        income = float(input_data.average_income or input_data.median_income or 0)
        obligation = float(input_data.existing_obligation or 0)

        if income <= 0:
            return 0.50, None

        dti = obligation / income
        dti_decimal = Decimal(str(round(dti, 4)))

        # Lower DTI is better for creditworthiness
        if dti <= 0.10:
            score = 0.95
        elif dti <= 0.25:
            score = 0.80
        elif dti <= 0.40:
            score = 0.60
        elif dti <= 0.60:
            score = 0.35
        else:
            score = 0.15

        return score, dti_decimal

    def _calc_platform_reliability(self, input_data: AssessmentInput) -> float:
        """Evaluate composite platform customer rating [0.0, 1.0]."""
        if input_data.platform_rating is not None:
            rating = float(input_data.platform_rating)
            # Ratings range [0, 5], standard gig threshold is [3.0, 5.0]
            if rating <= 3.0:
                return 0.10
            return max(0.0, min(1.0, (rating - 3.0) / 2.0))
        return 0.55

    def _calc_confidence(self, input_data: AssessmentInput) -> Decimal:
        """Calculate confidence based on evidence completeness."""
        trackable_signals = [
            input_data.average_income,
            input_data.median_income,
            input_data.payment_regularity,
            input_data.repayment_reliability,
            input_data.years_working,
            input_data.average_working_days,
            input_data.active_days,
            input_data.cashflow_buffer,
            input_data.existing_obligation,
            input_data.platform_rating,
            input_data.income_trend,
            input_data.gig_work_type,
        ]
        present = sum(1 for s in trackable_signals if s is not None)
        total = len(trackable_signals)

        # Completeness ratio maps to [0.20, 0.95]
        ratio = present / float(total)
        conf_float = 0.20 + (ratio * 0.75)
        return Decimal(str(round(conf_float, 4)))

    def _generate_key_factors(
        self,
        inc_stability: float,
        pay_reliability: float,
        work_stability: float,
        cashflow_str: float,
        ob_burden: float,
        plat_reliability: float,
    ) -> List[str]:
        """Generate top deterministic human-readable driving factors."""
        factors: List[str] = []

        # Payment reliability factors
        if pay_reliability >= 0.75:
            factors.append("Strong platform payout regularity and timing consistency")
        elif pay_reliability < 0.45:
            factors.append("Irregular platform payout consistency")

        # Income factors
        if inc_stability >= 0.70:
            factors.append("Stable recurring platform income pattern")
        elif inc_stability < 0.40:
            factors.append("Elevated earnings volatility or lower baseline income")

        # Obligation factors
        if ob_burden >= 0.75:
            factors.append("Favorable existing debt-to-income ratio")
        elif ob_burden < 0.45:
            factors.append("Elevated existing monthly debt commitment burden")

        # Cashflow buffer factors
        if cashflow_str >= 0.70:
            factors.append("Healthy cashflow buffer relative to requested financing")
        elif cashflow_str < 0.40:
            factors.append("Limited cashflow buffer to absorb unexpected shocks")

        # Work tenure factors
        if work_stability >= 0.70:
            factors.append("Established track record and high active days in gig work")
        elif work_stability < 0.40:
            factors.append("Shorter operational tenure in gig platform work")

        # Platform rating
        if plat_reliability >= 0.80:
            factors.append("High platform customer service rating")

        # Ensure at least two factors are always present
        if not factors:
            factors = [
                "Moderate platform activity recorded",
                "Baseline repayment indicators within expected range",
            ]

        return factors[:4]
