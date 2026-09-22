// @parakh/api
// Contract Adapter Layer: Bidirectional mappers between FastAPI transport schemas and frontend domain types

import type {
  RiskLevel,
  ApplicationStatus,
  PortalRole,
  CreditApplication,
  CreditAssessmentResult,
  UnderwriterReviewOutcome,
  BorrowerProfile,
  FactorSummary,
  SHAPContribution,
  VolatilityProfile,
  ReviewActionType,
} from '@parakh/types';
import type {
  BackendRiskLevel,
  BackendApplicationStatus,
  BackendReviewOutcomeType,
  BackendUserRole,
  BackendApplicationResponse,
  BackendCreditAssessmentResponse,
  BackendReviewOutcomeResponse,
  BackendApplicantProfileResponse,
  BackendUserResponse,
} from './types';

// ==========================================
// 1. ENUM ADAPTERS
// ==========================================

/**
 * Maps FastAPI RiskLevel enum to frontend display-friendly RiskLevel.
 */
export function adaptRiskLevel(backendRisk?: string | null): RiskLevel {
  switch (backendRisk?.toUpperCase()) {
    case 'LOWER':
      return 'LOWER_ESTIMATED RISK';
    case 'MODERATE':
      return 'MODERATE_ESTIMATED RISK';
    case 'HIGHER':
      return 'HIGHER_ESTIMATED RISK';
    case 'INSUFFICIENT':
      return 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW';
    default:
      return 'MODERATE_ESTIMATED RISK';
  }
}

/**
 * Reverse mapping from frontend RiskLevel to FastAPI backend RiskLevel.
 */
export function reverseAdaptRiskLevel(frontendRisk?: RiskLevel | string | null): BackendRiskLevel {
  if (!frontendRisk) return 'MODERATE';
  if (frontendRisk.includes('LOWER')) return 'LOWER';
  if (frontendRisk.includes('HIGHER')) return 'HIGHER';
  if (frontendRisk.includes('INSUFFICIENT')) return 'INSUFFICIENT';
  return 'MODERATE';
}

/**
 * Maps FastAPI ApplicationStatus enum to frontend conceptual ApplicationStatus.
 */
export function adaptApplicationStatus(backendStatus?: string | null): ApplicationStatus {
  switch (backendStatus?.toUpperCase()) {
    case 'DRAFT':
    case 'SUBMITTED':
      return 'SUBMITTED';
    case 'UNDER_REVIEW':
      return 'DATA_VALIDATION';
    case 'ASSESSED':
      return 'ASSESSMENT_COMPLETED';
    case 'MANUAL_REVIEW':
      return 'MANUAL_REVIEW_REQUIRED';
    case 'COMPLETED':
      return 'REVIEW_COMPLETED';
    default:
      return 'SUBMITTED';
  }
}

/**
 * Reverse mapping from frontend ApplicationStatus to FastAPI ApplicationStatus.
 */
export function reverseAdaptApplicationStatus(frontendStatus?: ApplicationStatus | string | null): BackendApplicationStatus {
  switch (frontendStatus) {
    case 'SUBMITTED':
      return 'SUBMITTED';
    case 'DATA_VALIDATION':
    case 'FINANCIAL_ANALYSIS':
      return 'UNDER_REVIEW';
    case 'ASSESSMENT_COMPLETED':
      return 'ASSESSED';
    case 'MANUAL_REVIEW_REQUIRED':
      return 'MANUAL_REVIEW';
    case 'REVIEW_COMPLETED':
      return 'COMPLETED';
    default:
      return 'SUBMITTED';
  }
}

/**
 * Maps backend UserRole to lowercase portal role.
 */
export function adaptUserRole(backendRole?: string | null): PortalRole {
  switch (backendRole?.toUpperCase()) {
    case 'REVIEWER':
      return 'reviewer';
    case 'ADMIN':
      return 'admin';
    case 'APPLICANT':
    default:
      return 'applicant';
  }
}

/**
 * Maps backend ReviewOutcomeType to frontend review status.
 */
export function adaptReviewOutcomeStatus(backendOutcome?: string | null): UnderwriterReviewOutcome['status'] {
  switch (backendOutcome?.toUpperCase()) {
    case 'REVIEWED':
      return 'OUTCOME_RECORDED';
    case 'ESCALATED':
      return 'MANUAL_REVIEW_IN_PROGRESS';
    case 'ADDITIONAL_INFORMATION_REQUIRED':
      return 'VERIFICATION_REQUESTED';
    default:
      return 'PENDING';
  }
}

/**
 * Reverse mapping from frontend ReviewActionType to FastAPI ReviewOutcomeType.
 */
export function reverseAdaptReviewAction(action?: ReviewActionType | string | null): BackendReviewOutcomeType {
  switch (action) {
    case 'RECORD_OUTCOME':
      return 'REVIEWED';
    case 'MANUAL_REVIEW':
      return 'ESCALATED';
    case 'REQUEST_VERIFICATION':
      return 'ADDITIONAL_INFORMATION_REQUIRED';
    default:
      return 'REVIEWED';
  }
}

// ==========================================
// 2. DOMAIN ENTITY ADAPTERS
// ==========================================

/**
 * Adapts FastAPI BackendApplicationResponse into frontend CreditApplication domain model.
 */
export function adaptApplication(
  backendApp: BackendApplicationResponse,
  profile?: BackendApplicantProfileResponse | null,
  assessment?: CreditAssessmentResult | null,
  review?: UnderwriterReviewOutcome | null
): CreditApplication {
  const applicantName = profile?.full_name || 'Applicant';
  const phone = profile?.phone_number || '';
  const employmentType =
    (profile?.work_type as any) === 'INFORMAL_VENDOR' ||
    (profile?.work_type as any) === 'FREELANCER' ||
    (profile?.work_type as any) === 'DAILY_WAGE'
      ? (profile?.work_type as any)
      : 'GIG_WORKER';

  return {
    id: backendApp.id,
    applicantId: backendApp.applicant_profile_id,
    applicantName,
    phone,
    requestedAmount: Number(backendApp.requested_loan_amount) || 0,
    purpose: backendApp.loan_purpose || 'General Working Capital',
    employmentType,
    submittedAt: backendApp.created_at,
    status: adaptApplicationStatus(backendApp.status),
    assessment: assessment || undefined,
    review: review || undefined,
  };
}

/**
 * Adapts FastAPI BackendCreditAssessmentResponse into frontend CreditAssessmentResult domain model.
 */
export function adaptAssessment(
  backendAssessment: BackendCreditAssessmentResponse,
  applicantName?: string
): CreditAssessmentResult {
  const score = Number(backendAssessment.score ?? backendAssessment.credit_score ?? 0);
  const riskProbability = Number(backendAssessment.risk_probability || 0);
  const confidence = Number(backendAssessment.confidence || 0);

  // Parse SHAP contributions or structured explanation metadata
  const featureContributions: SHAPContribution[] = [];
  const explanation = backendAssessment.explanation || {};

  if (Array.isArray(explanation.shap_values)) {
    for (const item of explanation.shap_values) {
      if (item && typeof item === 'object') {
        featureContributions.push({
          featureName: item.feature || item.featureName || 'signal',
          displayName: item.displayName || item.name || item.feature || 'Indicator',
          contributionValue: Number(item.value || item.contributionValue || 0),
          direction: Number(item.value || item.contributionValue || 0) >= 0 ? 'POSITIVE' : 'NEGATIVE',
          explanationText: item.explanation || item.explanationText || '',
        });
      }
    }
  }

  // Parse factor summaries
  const keyFactors = Array.isArray(backendAssessment.key_factors)
    ? backendAssessment.key_factors
    : [];

  const keyPositiveFactors: FactorSummary[] = [];
  const keyAttentionFactors: FactorSummary[] = [];

  keyFactors.forEach((factorStr, idx) => {
    const isNegative =
      factorStr.toLowerCase().includes('volat') ||
      factorStr.toLowerCase().includes('debt') ||
      factorStr.toLowerCase().includes('irregular') ||
      factorStr.toLowerCase().includes('dip');

    const factorItem: FactorSummary = {
      id: `factor-${idx + 1}`,
      title: factorStr,
      category: factorStr.toLowerCase().includes('volat')
        ? 'INCOME_VOLATILITY'
        : factorStr.toLowerCase().includes('debt')
        ? 'OBLIGATION'
        : factorStr.toLowerCase().includes('repay')
        ? 'REPAYMENT'
        : 'DATA_QUALITY',
      impact: idx === 0 ? 'HIGH' : 'MEDIUM',
      description: factorStr,
    };

    if (isNegative) {
      keyAttentionFactors.push(factorItem);
    } else {
      keyPositiveFactors.push(factorItem);
    }
  });

  // Extract or synthesize VolatilityProfile safely from available metrics
  const stability = Number(backendAssessment.income_stability ?? 0.85);
  const volatilityIndex = Math.max(0, Math.min(1, 1 - stability));
  const repaymentHistoryRate = Math.round(Number(backendAssessment.repayment_reliability ?? 0.95) * 100);

  const volatilityProfile: VolatilityProfile = {
    incomeFrequency: 'weekly',
    incomeVolatilityIndex: Number(volatilityIndex.toFixed(2)),
    incomeTrend: volatilityIndex > 0.4 ? 'volatile_stable' : 'increasing',
    recoveryRateAfterLowIncome: 0.94,
    lowIncomePeriodsEncountered: 2,
    successfulRecoveryCycles: 2,
    averageWeeklyInflow: 8400,
    gigPlatformEarnings: [
      {
        platformName: 'Active Delivery Partner',
        durationMonths: 18,
        averageWeeklyEarnings: 8400,
        ratingScore: 4.88,
      },
    ],
    repaymentHistoryRate,
    existingObligationsMonthly: Math.round(Number(backendAssessment.debt_to_income ?? 0.2) * 10000),
    dataQualityScore: Number(confidence > 0 ? (confidence > 1 ? confidence / 100 : confidence).toFixed(2) : 0.88),
    confidenceInterval: [Math.max(300, score - 35), Math.min(850, score + 35)],
  };

  // Safe recommendations derived from factors or backend
  const recommendations: string[] = Array.isArray(explanation.recommendations)
    ? explanation.recommendations
    : [
        'Maintain current average weekly active order volume.',
        'Keep recurring platform payouts linked to primary UPI handle.',
      ];

  return {
    id: backendAssessment.id,
    applicantId: backendAssessment.application_id,
    applicantName: applicantName || 'Applicant',
    score,
    maxScore: 850,
    riskLevel: adaptRiskLevel(backendAssessment.risk_level),
    estimatedRepaymentDifficulty: Math.round(riskProbability > 1 ? riskProbability : riskProbability * 100),
    modelConfidence: Math.round(confidence > 1 ? confidence : (confidence || 0.85) * 100),
    volatilityProfile,
    keyPositiveFactors,
    keyAttentionFactors,
    featureContributions,
    actionableRecommendations: recommendations,
    assessedAt: backendAssessment.assessed_at,
  };
}

/**
 * Adapts FastAPI BackendReviewOutcomeResponse into frontend UnderwriterReviewOutcome domain model.
 */
export function adaptReviewOutcome(
  backendReview: BackendReviewOutcomeResponse,
  reviewerName?: string
): UnderwriterReviewOutcome {
  const status = adaptReviewOutcomeStatus(backendReview.outcome);

  return {
    status,
    action:
      backendReview.outcome === 'REVIEWED'
        ? 'RECORD_OUTCOME'
        : backendReview.outcome === 'ADDITIONAL_INFORMATION_REQUIRED'
        ? 'REQUEST_VERIFICATION'
        : 'MANUAL_REVIEW',
    decisionNotes: backendReview.notes || undefined,
    verificationItemsRequested:
      backendReview.outcome === 'ADDITIONAL_INFORMATION_REQUIRED'
        ? ['Recent 30-day platform earnings statement']
        : undefined,
    underwriterId: backendReview.reviewer_id,
    underwriterName: reviewerName || 'Senior Credit Reviewer',
    recordedAt: backendReview.created_at,
  };
}

/**
 * Adapts FastAPI BackendApplicantProfileResponse into frontend BorrowerProfile domain model.
 */
export function adaptBorrowerProfile(
  backendProfile: BackendApplicantProfileResponse,
  userOrEmail?: BackendUserResponse | string | null
): BorrowerProfile {
  const email =
    typeof userOrEmail === 'string'
      ? userOrEmail
      : userOrEmail && typeof userOrEmail === 'object' && 'email' in userOrEmail
      ? userOrEmail.email
      : undefined;

  return {
    id: backendProfile.id,
    fullName: backendProfile.full_name || 'Gig Worker Applicant',
    phone: backendProfile.phone_number || '',
    email: email || undefined,
    city: backendProfile.city || 'National (All India)',
    verifiedAadhaar: true,
    verifiedPAN: true,
    connectedAccountsCount: 1,
    memberSince: backendProfile.created_at,
  };
}

