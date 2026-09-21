// Mock data for User / Borrower Portal (Isolated for offline development)
// Strict domain conformance with @parakh/types

import type {
  BorrowerProfile,
  CreditAssessmentResult,
  CreditApplication,
} from '@parakh/types';

export const mockBorrowerProfile: BorrowerProfile = {
  id: 'USR-8910',
  fullName: 'Arjun Verma',
  phone: '+91 98451 28910',
  email: 'arjun.verma.gig@gmail.com',
  city: 'Bengaluru, Karnataka',
  verifiedAadhaar: true,
  verifiedPAN: true,
  connectedAccountsCount: 3,
  memberSince: 'Aug 2024',
};

export const mockUserAssessment: CreditAssessmentResult = {
  id: 'EVA-89412',
  applicantId: 'USR-8910',
  applicantName: 'Arjun Verma',
  score: 742,
  maxScore: 850,
  riskLevel: 'LOWER_ESTIMATED RISK',
  estimatedRepaymentDifficulty: 21,
  modelConfidence: 87,
  volatilityProfile: {
    incomeFrequency: 'weekly',
    incomeVolatilityIndex: 0.28,
    incomeTrend: 'volatile_stable',
    recoveryRateAfterLowIncome: 0.94,
    lowIncomePeriodsEncountered: 3,
    successfulRecoveryCycles: 3,
    averageWeeklyInflow: 12800,
    repaymentHistoryRate: 98,
    existingObligationsMonthly: 4500,
    dataQualityScore: 0.89,
    confidenceInterval: [728, 756],
    gigPlatformEarnings: [
      {
        platformName: 'Swiggy',
        durationMonths: 18,
        averageWeeklyEarnings: 9200,
        ratingScore: 4.85,
        activeTripsOrOrdersPerMonth: 210,
      },
      {
        platformName: 'Urban Company',
        durationMonths: 8,
        averageWeeklyEarnings: 3600,
        ratingScore: 4.9,
        activeTripsOrOrdersPerMonth: 42,
      },
    ],
  },
  keyPositiveFactors: [
    {
      id: 'F1',
      title: 'Healthy Shock Rebound',
      category: 'INCOME_VOLATILITY',
      impact: 'HIGH',
      description: 'Income shocks recover to baseline within 10-14 days across all observed historical dips.',
    },
    {
      id: 'F2',
      title: 'Punctual Utility & UPI Cadence',
      category: 'REPAYMENT',
      impact: 'HIGH',
      description: '98% on-time settlement rate on mobile recharge, LPG cylinders, and electricity bills.',
    },
    {
      id: 'F3',
      title: 'Diversified Platform Earnings',
      category: 'TENURE',
      impact: 'MEDIUM',
      description: 'Active earning history across two separate gig platforms enhances income stability.',
    },
  ],
  keyAttentionFactors: [
    {
      id: 'A1',
      title: 'Rainy Season Variance',
      category: 'INCOME_VOLATILITY',
      impact: 'MEDIUM',
      description: 'Temporary 35% weekly dip during heavy rain spells; historically recovered fully in following week.',
    },
  ],
  featureContributions: [
    {
      featureName: 'shock_recovery_rate',
      displayName: 'Income Rebound Velocity',
      contributionValue: 0.42,
      direction: 'POSITIVE',
      explanationText: 'Rebounds to baseline within 10 days after low-earning weeks.',
    },
    {
      featureName: 'utility_punctuality',
      displayName: 'Utility Settlement Track Record',
      contributionValue: 0.35,
      direction: 'POSITIVE',
      explanationText: 'Consistent payment history across electricity, gas, and telecom.',
    },
    {
      featureName: 'platform_tenure',
      displayName: 'Gig Platform Tenure (18 mos)',
      contributionValue: 0.28,
      direction: 'POSITIVE',
      explanationText: 'Continuous active delivery profile on Swiggy and Urban Company.',
    },
    {
      featureName: 'single_week_volatility',
      displayName: 'Seasonal Monsoon Volatility',
      contributionValue: -0.15,
      direction: 'NEGATIVE',
      explanationText: 'Seasonal weather fluctuations reduce weekly shifts temporarily.',
    },
  ],
  actionableRecommendations: [
    'Continue linking active platform earnings to maintain verified data confidence above 85%.',
    'Maintaining utility bill payments before the due date contributes positively to repayment reliability.',
    'No additional debt burden detected; maintain current obligation ratio below 35% of inflow.',
  ],
  assessedAt: '2026-09-18T10:30:00Z',
};

export const mockUserApplications: CreditApplication[] = [
  {
    id: 'APP-8012',
    applicantId: 'USR-8910',
    applicantName: 'Arjun Verma',
    phone: '+91 98451 28910',
    requestedAmount: 35000,
    purpose: 'Two-Wheeler EV Battery Upgrade',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-09-18T09:15:00Z',
    status: 'ASSESSMENT_COMPLETED',
    assessment: mockUserAssessment,
  },
  {
    id: 'APP-8320',
    applicantId: 'USR-8910',
    applicantName: 'Arjun Verma',
    phone: '+91 98451 28910',
    requestedAmount: 45000,
    purpose: 'Commercial Drone Delivery Gear Pilot',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-09-16T14:30:00Z',
    status: 'MANUAL_REVIEW_REQUIRED',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-8320',
      score: 698,
      riskLevel: 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW',
      estimatedRepaymentDifficulty: 38,
      modelConfidence: 74,
    },
    review: {
      status: 'MANUAL_REVIEW_IN_PROGRESS',
      action: 'MANUAL_REVIEW',
      decisionNotes:
        'Evaluating seasonal monsoon variance dip against secondary platform earnings. Requesting verification of recent UPI merchant settlements before recording outcome.',
      verificationItemsRequested: ['Latest 30-day UPI QR settlement report', 'Urban Company partner rating certificate'],
      underwriterId: 'UW-402',
      underwriterName: 'Priya Sharma (Risk Assessment Underwriter)',
      recordedAt: '2026-09-17T11:20:00Z',
    },
  },
  {
    id: 'APP-8401',
    applicantId: 'USR-8910',
    applicantName: 'Arjun Verma',
    phone: '+91 98451 28910',
    requestedAmount: 25000,
    purpose: 'Cold Storage Delivery Insulated Box',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-09-20T10:45:00Z',
    status: 'DATA_VALIDATION',
  },
  {
    id: 'APP-7649',
    applicantId: 'USR-8910',
    applicantName: 'Arjun Verma',
    phone: '+91 98451 28910',
    requestedAmount: 15000,
    purpose: 'Smartphone & Delivery Gear',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-08-10T14:20:00Z',
    status: 'REVIEW_COMPLETED',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-7649',
      score: 728,
      estimatedRepaymentDifficulty: 24,
    },
    review: {
      status: 'OUTCOME_RECORDED',
      action: 'RECORD_OUTCOME',
      decisionNotes:
        'Human underwriter verified 18-month Swiggy activity telemetry and 12-month BBPS utility clearance cadence. Risk classified as LOWER ESTIMATED RISK with sound shock rebound velocity.',
      underwriterId: 'UW-108',
      underwriterName: 'Rajesh Nair (Credit Underwriter)',
      recordedAt: '2026-08-11T16:30:00Z',
    },
  },
  {
    id: 'APP-6921',
    applicantId: 'USR-8910',
    applicantName: 'Arjun Verma',
    phone: '+91 98451 28910',
    requestedAmount: 20000,
    purpose: 'Emergency Vehicle Maintenance',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-07-04T11:00:00Z',
    status: 'ASSESSMENT_COMPLETED',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-6921',
      score: 710,
      riskLevel: 'MODERATE_ESTIMATED RISK',
      estimatedRepaymentDifficulty: 31,
    },
  },
];

export interface ConnectedDataSource {
  id: string;
  name: string;
  category: 'GIG_PLATFORM' | 'ACCOUNT_AGGREGATOR' | 'UTILITY_BBPS' | 'IDENTITY';
  provider: string;
  status: 'ACTIVE' | 'SYNCING' | 'ACTION_REQUIRED' | 'DISCONNECTED';
  lastSyncedAt: string;
  details: {
    tenureMonths?: number;
    monthlyAverage?: number;
    rating?: number;
    completedTrips?: number;
    accountMask?: string;
    onTimeRate?: number;
  };
}

export const mockConnectedDataSources: ConnectedDataSource[] = [
  {
    id: 'DS-SWIGGY',
    name: 'Swiggy Partner Telemetry',
    category: 'GIG_PLATFORM',
    provider: 'Swiggy Delivery Partner API',
    status: 'ACTIVE',
    lastSyncedAt: '12 minutes ago',
    details: {
      tenureMonths: 18,
      monthlyAverage: 36800,
      rating: 4.85,
      completedTrips: 3420,
    },
  },
  {
    id: 'DS-URBAN',
    name: 'Urban Company Pro Stream',
    category: 'GIG_PLATFORM',
    provider: 'Urban Company Partner Connect',
    status: 'ACTIVE',
    lastSyncedAt: '1 hour ago',
    details: {
      tenureMonths: 8,
      monthlyAverage: 14400,
      rating: 4.9,
      completedTrips: 312,
    },
  },
  {
    id: 'DS-BBPS',
    name: 'Bharat BillPay (BBPS)',
    category: 'UTILITY_BBPS',
    provider: 'NPCI BBPS Utility Central',
    status: 'ACTIVE',
    lastSyncedAt: 'Yesterday at 20:15',
    details: {
      onTimeRate: 98,
      accountMask: '3 Billers Active (BESCOM, Indane, Airtel)',
    },
  },
  {
    id: 'DS-AA-HDFC',
    name: 'Sahamati Account Aggregator',
    category: 'ACCOUNT_AGGREGATOR',
    provider: 'Anumati AA / HDFC Bank Savings',
    status: 'ACTIVE',
    lastSyncedAt: 'Today at 04:00 AM',
    details: {
      accountMask: '•••4912',
      monthlyAverage: 51200,
    },
  },
];

export function getUserApplicationById(id: string): CreditApplication {
  const cleanId = id.toUpperCase();
  const found = mockUserApplications.find((app) => app.id.toUpperCase() === cleanId);
  if (found) return found;

  // Graceful fallback keeping exact types for any test ID
  return {
    ...mockUserApplications[0],
    id: cleanId,
  };
}

