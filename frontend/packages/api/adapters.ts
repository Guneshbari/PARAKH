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
  BackendPortfolioAnalytics,
  BackendSectorRiskItem,
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
  const rawScore = backendAssessment.score ?? backendAssessment.credit_score;
  const score = rawScore !== null && rawScore !== undefined ? Number(rawScore) : null;

  const rawRiskProb = backendAssessment.risk_probability;
  const riskProbability = rawRiskProb !== null && rawRiskProb !== undefined ? Number(rawRiskProb) : null;
  const estimatedRepaymentDifficulty =
    riskProbability !== null
      ? Math.round(riskProbability > 1 ? riskProbability : riskProbability * 100)
      : null;

  const rawConfidence = backendAssessment.confidence;
  const confidence = rawConfidence !== null && rawConfidence !== undefined ? Number(rawConfidence) : null;
  const modelConfidence =
    confidence !== null
      ? Math.round(confidence > 1 ? confidence : confidence * 100)
      : null;

  // Parse explanation metadata
  const explanation = backendAssessment.explanation || {};
  const isInsufficientEvidence = Boolean(
    explanation.is_insufficient_evidence ??
    (backendAssessment.risk_level?.toUpperCase() === 'INSUFFICIENT')
  );
  const missingSignals: string[] = Array.isArray(explanation.missing_signals)
    ? explanation.missing_signals
    : [];
  const disclaimer: string | undefined =
    typeof explanation.disclaimer === 'string' ? explanation.disclaimer : undefined;

  const modelName = backendAssessment.model_name ?? null;
  const modelVersion = backendAssessment.model_version ?? null;
  const assessmentStatus = backendAssessment.assessment_status ?? undefined;
  const debtToIncome =
    backendAssessment.debt_to_income != null ? Number(backendAssessment.debt_to_income) : null;
  const utilization =
    backendAssessment.utilization != null ? Number(backendAssessment.utilization) : null;

  // Parse SHAP contributions
  const featureContributions: SHAPContribution[] = [];
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
      factorStr.toLowerCase().includes('dip') ||
      factorStr.toLowerCase().includes('insufficient');

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
  const stability =
    backendAssessment.income_stability != null ? Number(backendAssessment.income_stability) : 0.85;
  const volatilityIndex = Math.max(0, Math.min(1, 1 - stability));
  const repaymentHistoryRate =
    backendAssessment.repayment_reliability != null
      ? Math.round(Number(backendAssessment.repayment_reliability) * 100)
      : 95;

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
    existingObligationsMonthly:
      debtToIncome != null ? Math.round(debtToIncome * 10000) : 2000,
    dataQualityScore:
      confidence !== null
        ? Number((confidence > 1 ? confidence / 100 : confidence).toFixed(2))
        : 0.0,
    confidenceInterval:
      score !== null
        ? [Math.max(300, score - 35), Math.min(850, score + 35)]
        : [300, 850],
  };

  // Safe recommendations derived from factors or backend
  const recommendations: string[] = Array.isArray(explanation.recommendations)
    ? explanation.recommendations
    : isInsufficientEvidence
    ? [
        'Connect verified digital payment accounts with at least 30 days of continuous inflow history.',
        'Ensure primary gig platform payout accounts are actively linked.',
      ]
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
    estimatedRepaymentDifficulty,
    modelConfidence,
    isInsufficientEvidence,
    missingSignals,
    disclaimer,
    modelName,
    modelVersion,
    debtToIncome,
    utilization,
    assessmentStatus,
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

// ==========================================
// 3. ANALYTICS & GOVERNANCE ADAPTERS
// ==========================================

export interface AdaptedScoreBucket {
  range: string;
  label: string;
  count: number;
  percentage: number;
  riskTier: RiskLevel;
}

export interface AdaptedPipelineStage {
  id: string;
  name: string;
  count: number;
  subtext: string;
}

export interface AdaptedSectorRisk {
  sector: string;
  lowerRisk: number;
  moderateRisk: number;
  higherRisk: number;
  manualReview: number;
  total: number;
}

export interface AdaptedPortfolioAnalytics {
  totalEvaluated: number;
  totalApplicants: number;
  averageScore: number | null;
  averageRiskDifficulty: number | null;
  assessmentCompletionRate: number;
  totalAssessments: number;
  assessedApplications: number;
  manualReviewApplications: number;
  completedApplications: number;
  riskDistribution: {
    lowerRiskCount: number;
    moderateRiskCount: number;
    higherRiskCount: number;
    manualReviewCount: number;
  };
  pipelineStages: AdaptedPipelineStage[];
  scoreDistribution: AdaptedScoreBucket[];
  monthlyVolume: {
    month: string;
    count: number;
    avgScore: number | null;
  }[];
  sectorRisk: AdaptedSectorRisk[];
}

export interface AdaptedSectorRisk {
  sector: string;
  displayName: string;
  lowerRisk: number;
  moderateRisk: number;
  higherRisk: number;
  manualReview: number;
  total: number;
}

const SECTOR_DISPLAY_NAMES: Record<string, string> = {
  DELIVERY: 'Delivery & Quick Commerce',
  MOBILITY: 'Mobility & Cab Drivers',
  HOME_SERVICES: 'Home Services & Maintenance',
  RETAIL_COMMERCE: 'Retail & Commerce',
  FREELANCE_CREATIVE: 'Freelance & Creative',
  GIG_WORKER: 'General Gig Worker',
  OTHER: 'Other Sectors',
};

/**
 * Adapts FastAPI sector risk items into frontend display models.
 */
export function adaptSectorRisk(items: BackendSectorRiskItem[] = []): AdaptedSectorRisk[] {
  return items.map((s) => ({
    sector: s.sector,
    displayName: SECTOR_DISPLAY_NAMES[s.sector] || s.sector.replace(/_/g, ' '),
    lowerRisk: s.lower_risk || 0,
    moderateRisk: s.moderate_risk || 0,
    higherRisk: s.higher_risk || 0,
    manualReview: s.manual_review || 0,
    total: s.total || 0,
  }));
}

/**
 * Adapts FastAPI BackendPortfolioAnalytics into frontend domain display models.
 */
export function adaptPortfolioAnalytics(backend: BackendPortfolioAnalytics): AdaptedPortfolioAnalytics {
  const statusDist = backend.status_distribution || {};
  const riskDist = backend.risk_distribution || {};

  // Pipeline stages derived from canonical backend ApplicationStatus
  const pipelineStages: AdaptedPipelineStage[] = [
    {
      id: 'p1',
      name: 'Intake Registered',
      count: (statusDist['SUBMITTED'] || 0) + (statusDist['DRAFT'] || 0),
      subtext: 'Intake applications registered',
    },
    {
      id: 'p2',
      name: 'Data Validation',
      count: statusDist['UNDER_REVIEW'] || 0,
      subtext: 'Inflows & validation in progress',
    },
    {
      id: 'p3',
      name: 'Assessment Completed',
      count: statusDist['ASSESSED'] || 0,
      subtext: 'Synthesized credit evaluation ready',
    },
    {
      id: 'p4',
      name: 'Manual Review Required',
      count: statusDist['MANUAL_REVIEW'] || 0,
      subtext: 'Non-standard volatility / reviewer queue',
    },
    {
      id: 'p5',
      name: 'Review Completed',
      count: statusDist['COMPLETED'] || 0,
      subtext: 'Human underwriter decision finalized',
    },
  ];

  // Score distribution buckets
  const scoreDistribution: AdaptedScoreBucket[] = (backend.score_distribution || []).map((b) => ({
    range: b.range,
    label: b.label,
    count: b.count,
    percentage: b.percentage,
    riskTier: adaptRiskLevel(b.risk_tier),
  }));

  // Monthly volume
  const monthlyVolume = (backend.monthly_volume || []).map((m) => ({
    month: m.month,
    count: m.count,
    avgScore: m.avg_score,
  }));

  return {
    totalEvaluated: backend.total_applications || 0,
    totalApplicants: backend.total_applicants || 0,
    averageScore:
      backend.average_credit_score !== null && backend.average_credit_score !== undefined
        ? Math.round(backend.average_credit_score)
        : null,
    averageRiskDifficulty:
      backend.average_risk_probability !== null && backend.average_risk_probability !== undefined
        ? Number((backend.average_risk_probability * 100).toFixed(1))
        : null,
    assessmentCompletionRate: Number((backend.assessment_completion_rate || 0).toFixed(1)),
    totalAssessments: backend.total_assessments || 0,
    assessedApplications: backend.assessed_applications || 0,
    manualReviewApplications: backend.manual_review_applications || 0,
    completedApplications: backend.completed_applications || 0,
    riskDistribution: {
      lowerRiskCount: riskDist['LOWER'] || 0,
      moderateRiskCount: riskDist['MODERATE'] || 0,
      higherRiskCount: riskDist['HIGHER'] || 0,
      manualReviewCount: riskDist['INSUFFICIENT'] || 0,
    },
    pipelineStages,
    scoreDistribution,
    monthlyVolume,
    sectorRisk: adaptSectorRisk(backend.sector_risk || []),
  };
}


