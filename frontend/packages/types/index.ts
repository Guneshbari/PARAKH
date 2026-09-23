// @parakh/types
// Domain types for PARAKH alternative credit assessment platform

export type RiskLevel =
  | 'LOWER_ESTIMATED RISK'
  | 'MODERATE_ESTIMATED RISK'
  | 'HIGHER_ESTIMATED RISK'
  | 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW';

export type IncomeFrequency = 'daily' | 'weekly' | 'irregular' | 'monthly';
export type IncomeTrend = 'increasing' | 'stable' | 'volatile_stable' | 'declining';

export interface GigPlatformEarning {
  platformName: string;
  durationMonths: number;
  averageWeeklyEarnings: number;
  ratingScore?: number;
  activeTripsOrOrdersPerMonth?: number;
}

export interface VolatilityProfile {
  incomeFrequency: IncomeFrequency;
  incomeVolatilityIndex: number; // 0.0 - 1.0 (standardized coefficient of variation)
  incomeTrend: IncomeTrend;
  recoveryRateAfterLowIncome: number; // e.g. 0.94 (94% of low cycles rebound in 10-14 days)
  lowIncomePeriodsEncountered: number; // Dip count over the observation window
  successfulRecoveryCycles: number; // Dips followed by positive rebound
  averageWeeklyInflow: number;
  gigPlatformEarnings: GigPlatformEarning[];
  repaymentHistoryRate: number; // percentage of micro-obligations paid on time
  existingObligationsMonthly: number;
  dataQualityScore: number; // 0.0 - 1.0 confidence in underlying data feeds
  confidenceInterval: [number, number]; // [lowerScore, upperScore]
}

export interface FactorSummary {
  id: string;
  title: string;
  category: 'INCOME_VOLATILITY' | 'REPAYMENT' | 'OBLIGATION' | 'TENURE' | 'DATA_QUALITY';
  impact: 'HIGH' | 'MEDIUM' | 'LOW';
  description: string;
}

export interface SHAPContribution {
  featureName: string;
  displayName: string;
  contributionValue: number; // Relative impact (-1.0 to +1.0)
  direction: 'POSITIVE' | 'NEGATIVE';
  explanationText: string;
}

export interface CreditAssessmentResult {
  id: string;
  applicantId: string;
  applicantName: string;
  score: number | null; // e.g. 742, or null if insufficient evidence
  maxScore: number; // 850
  riskLevel: RiskLevel;
  estimatedRepaymentDifficulty: number | null; // e.g. 21 (21%), or null if insufficient evidence
  modelConfidence: number | null; // e.g. 87 (87%), or null / 0
  isInsufficientEvidence?: boolean;
  missingSignals?: string[];
  disclaimer?: string;
  modelName?: string | null;
  modelVersion?: string | null;
  debtToIncome?: number | null;
  utilization?: number | null;
  assessmentStatus?: string;
  volatilityProfile: VolatilityProfile;
  keyPositiveFactors: FactorSummary[];
  keyAttentionFactors: FactorSummary[];
  featureContributions: SHAPContribution[];
  actionableRecommendations: string[];
  assessedAt: string;
}

export type ApplicationStatus =
  | 'SUBMITTED'
  | 'DATA_VALIDATION'
  | 'FINANCIAL_ANALYSIS'
  | 'ASSESSMENT_COMPLETED'
  | 'MANUAL_REVIEW_REQUIRED'
  | 'REVIEW_COMPLETED';

export type ReviewActionType =
  | 'REQUEST_VERIFICATION'
  | 'MANUAL_REVIEW'
  | 'RECORD_OUTCOME';

export interface UnderwriterReviewOutcome {
  status: 'PENDING' | 'VERIFICATION_REQUESTED' | 'MANUAL_REVIEW_IN_PROGRESS' | 'OUTCOME_RECORDED';
  action?: ReviewActionType;
  decisionNotes?: string;
  verificationItemsRequested?: string[];
  underwriterId?: string;
  underwriterName?: string;
  recordedAt?: string;
}

export interface CreditApplication {
  id: string;
  applicantId: string;
  applicantName: string;
  phone: string;
  requestedAmount: number;
  purpose: string;
  employmentType: 'GIG_WORKER' | 'INFORMAL_VENDOR' | 'FREELANCER' | 'DAILY_WAGE';
  submittedAt: string;
  status: ApplicationStatus;
  assessment?: CreditAssessmentResult;
  review?: UnderwriterReviewOutcome;
}

export interface BorrowerProfile {
  id: string;
  fullName: string;
  phone: string;
  email?: string;
  city: string;
  verifiedAadhaar: boolean;
  verifiedPAN: boolean;
  connectedAccountsCount: number;
  memberSince: string;
  volatilityProfile?: VolatilityProfile;
}

export interface PortfolioAnalytics {
  totalEvaluated: number;
  averageScore: number;
  averageRiskDifficulty: number;
  assessmentCompletionRate: number;
  verificationRate: number;
  riskDistribution: {
    lowerRiskCount: number;
    moderateRiskCount: number;
    higherRiskCount: number;
    manualReviewCount: number;
  };
  volatilityTrendsBySector: {
    sector: string;
    avgRecoveryRate: number;
    volatilityIndex: number;
    applicantCount: number;
  }[];
  monthlyVolume: {
    month: string;
    count: number;
    avgScore: number;
  }[];
}

export interface ModelInsights {
  modelVersion: string;
  lastTrainedAt: string;
  datasetRecordsCount: number;
  totalAssessmentsGenerated: number;
  topFeatures: {
    feature: string;
    displayName: string;
    importance: number;
    description: string;
  }[];
  fairnessMetrics: {
    attribute: string;
    demographicGroup: string;
    parityRatio: number;
    equalizedOddsDifference: number;
    auditStatus: 'FAIR' | 'NEEDS_MONITORING';
  }[];
}

// --- AUTH & IDENTITY TYPES (Canonical Backend Contract) ---

export type UserRole = 'APPLICANT' | 'REVIEWER' | 'ADMIN';
export type PortalRole = 'applicant' | 'reviewer' | 'admin';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
  role: UserRole;
}

export interface UserResponse {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreateRequest {
  email: string;
  password: string;
  role?: UserRole;
}

export function normalizeUserRole(role?: string | null): UserRole | null {
  if (!role) return null;
  const upper = role.toUpperCase();
  if (upper === 'APPLICANT') return 'APPLICANT';
  if (upper === 'REVIEWER') return 'REVIEWER';
  if (upper === 'ADMIN') return 'ADMIN';
  return null;
}

export function toPortalRole(role?: string | null): PortalRole | null {
  const normalized = normalizeUserRole(role);
  if (normalized === 'APPLICANT') return 'applicant';
  if (normalized === 'REVIEWER') return 'reviewer';
  if (normalized === 'ADMIN') return 'admin';
  return null;
}

