// Mock data for Admin / Underwriter Cockpit
// Domain types conform strictly with @parakh/types

import type {
  PortfolioAnalytics,
  CreditApplication,
  RiskLevel,
  ModelInsights,
} from '@parakh/types';
import { mockUserAssessment } from './user';

export const mockPortfolioAnalytics: PortfolioAnalytics = {
  totalEvaluated: 14280,
  averageScore: 718,
  averageRiskDifficulty: 24.5,
  assessmentCompletionRate: 94.2,
  verificationRate: 91.8,
  riskDistribution: {
    lowerRiskCount: 8420, // 59.0%
    moderateRiskCount: 3910, // 27.4%
    higherRiskCount: 1240, // 8.7%
    manualReviewCount: 710, // 5.0%
  },
  volatilityTrendsBySector: [
    {
      sector: 'Food & Quick Commerce Delivery',
      avgRecoveryRate: 0.93,
      volatilityIndex: 0.29,
      applicantCount: 6840,
    },
    {
      sector: 'On-Demand Home Services',
      avgRecoveryRate: 0.91,
      volatilityIndex: 0.26,
      applicantCount: 3210,
    },
    {
      sector: 'Ride Hailing & Logistics',
      avgRecoveryRate: 0.88,
      volatilityIndex: 0.34,
      applicantCount: 2890,
    },
    {
      sector: 'Informal Vendors & Micro-Shops',
      avgRecoveryRate: 0.85,
      volatilityIndex: 0.38,
      applicantCount: 1340,
    },
  ],
  monthlyVolume: [
    { month: 'Apr 2026', count: 1820, avgScore: 712 },
    { month: 'May 2026', count: 2150, avgScore: 715 },
    { month: 'Jun 2026', count: 2480, avgScore: 716 },
    { month: 'Jul 2026', count: 2340, avgScore: 714 },
    { month: 'Aug 2026', count: 2690, avgScore: 720 },
    { month: 'Sep 2026', count: 2800, avgScore: 722 },
  ],
};

export interface ScoreDistributionBucket {
  range: string;
  label: string;
  count: number;
  percentage: number;
  riskTier: RiskLevel;
}

export const mockScoreDistributionBuckets: ScoreDistributionBucket[] = [
  {
    range: '800–850',
    label: 'Exceptional Resilience',
    count: 1840,
    percentage: 12.9,
    riskTier: 'LOWER_ESTIMATED RISK',
  },
  {
    range: '740–799',
    label: 'Strong Shock Recovery',
    count: 5680,
    percentage: 39.8,
    riskTier: 'LOWER_ESTIMATED RISK',
  },
  {
    range: '680–739',
    label: 'Moderate Cyclical Variance',
    count: 4410,
    percentage: 30.9,
    riskTier: 'MODERATE_ESTIMATED RISK',
  },
  {
    range: '600–679',
    label: 'Elevated Income Volatility',
    count: 1620,
    percentage: 11.3,
    riskTier: 'HIGHER_ESTIMATED RISK',
  },
  {
    range: '< 600',
    label: 'Insufficient Evidence / High Volatility',
    count: 730,
    percentage: 5.1,
    riskTier: 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW',
  },
];

export interface PipelineStage {
  id: string;
  name: string;
  count: number;
  subtext: string;
}

export const mockPipelineStages: PipelineStage[] = [
  { id: 'p1', name: 'Intake Registered', count: 14280, subtext: 'Digital intake sessions' },
  { id: 'p2', name: 'Data Validation', count: 13810, subtext: 'KYC & AA attested' },
  { id: 'p3', name: 'Volatility Engine', count: 13420, subtext: '12-wk cashflow computed' },
  { id: 'p4', name: 'Assessment Dossier', count: 12710, subtext: 'Explainable score ready' },
  { id: 'p5', name: 'Review Queue', count: 710, subtext: 'Manual review required' },
];

export interface OperationalAlert {
  id: string;
  title: string;
  category: 'VOLATILITY_ALERT' | 'TELEMETRY_STATUS' | 'FAIRNESS_AUDIT';
  severity: 'INFO' | 'WARNING' | 'SUCCESS';
  message: string;
  timestamp: string;
}

export const mockOperationalAlerts: OperationalAlert[] = [
  {
    id: 'ALT-901',
    title: 'Monsoon Seasonal Volatility Pattern Detected',
    category: 'VOLATILITY_ALERT',
    severity: 'INFO',
    message:
      'Swiggy and Zomato delivery inflows experienced a 32% temporary dip during Week 36 in Bengaluru East. Historical rebound velocity confirms 10–14 day recovery. Do not treat as financial distress.',
    timestamp: '28m ago',
  },
  {
    id: 'ALT-902',
    title: 'Urban Company Partner Connect Telemetry Live',
    category: 'TELEMETRY_STATUS',
    severity: 'SUCCESS',
    message:
      'Real-time partner stream operational. 3,210 worker profiles synchronized with zero API ingestion backlog.',
    timestamp: '1h ago',
  },
  {
    id: 'ALT-903',
    title: 'Fairness Parity Audit Confirmed (v2.4)',
    category: 'FAIRNESS_AUDIT',
    severity: 'INFO',
    message:
      'Equalized odds difference across gig sectors is 0.02 (Parity ratio: 0.97). Meets statutory transparency standards.',
    timestamp: '3h ago',
  },
];

export const mockPriorityReviewQueue: (CreditApplication & {
  triggerReason: string;
  sectorTag: string;
})[] = [
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
    triggerReason: 'Monsoon dip in week 36; secondary platform tenure cross-check',
    sectorTag: 'Swiggy / Urban Company',
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
        'Evaluating seasonal monsoon variance dip against secondary platform earnings. Requesting verification of recent UPI merchant settlements.',
      underwriterName: 'Priya Sharma (Senior Credit Reviewer)',
      recordedAt: '2026-09-17T11:20:00Z',
    },
  },
  {
    id: 'APP-8344',
    applicantId: 'USR-9021',
    applicantName: 'Sunita Devi',
    phone: '+91 97120 44102',
    requestedAmount: 30000,
    purpose: 'Home Salon Sterilization Equipment',
    employmentType: 'GIG_WORKER',
    submittedAt: '2026-09-17T10:15:00Z',
    status: 'MANUAL_REVIEW_REQUIRED',
    triggerReason: 'High platform rating (4.92) but single-platform concentration',
    sectorTag: 'Urban Company',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-8344',
      applicantName: 'Sunita Devi',
      score: 712,
      riskLevel: 'MODERATE_ESTIMATED RISK',
      estimatedRepaymentDifficulty: 29,
      modelConfidence: 82,
    },
  },
  {
    id: 'APP-8356',
    applicantId: 'USR-9104',
    applicantName: 'Mohammed Rafiq',
    phone: '+91 99014 55901',
    requestedAmount: 40000,
    purpose: 'Three-Wheeler CNG Engine Overhaul',
    employmentType: 'DAILY_WAGE',
    submittedAt: '2026-09-18T16:00:00Z',
    status: 'DATA_VALIDATION',
    triggerReason: 'UPI settlement frequency variance; statement cross-check required',
    sectorTag: 'Auto & Logistics',
  },
  {
    id: 'APP-8371',
    applicantId: 'USR-9289',
    applicantName: 'Ramesh Kumar',
    phone: '+91 94481 33290',
    requestedAmount: 20000,
    purpose: 'Daily Vegetable Cart Working Capital',
    employmentType: 'INFORMAL_VENDOR',
    submittedAt: '2026-09-19T08:30:00Z',
    status: 'MANUAL_REVIEW_REQUIRED',
    triggerReason: 'Zero formal bureau presence; exceptional 98% QR settlement cadence',
    sectorTag: 'Street Vendor / QR',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-8371',
      applicantName: 'Ramesh Kumar',
      score: 730,
      riskLevel: 'LOWER_ESTIMATED RISK',
      estimatedRepaymentDifficulty: 23,
      modelConfidence: 86,
    },
  },
  {
    id: 'APP-8389',
    applicantId: 'USR-9340',
    applicantName: 'Deepa Sundaram',
    phone: '+91 98862 11029',
    requestedAmount: 35000,
    purpose: 'Boutique Tailoring Commercial Sewing Unit',
    employmentType: 'FREELANCER',
    submittedAt: '2026-09-19T13:45:00Z',
    status: 'MANUAL_REVIEW_REQUIRED',
    triggerReason: 'Recent surge in micro-merchant UPI inflows; tenure verification',
    sectorTag: 'Freelance & Crafts',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-8389',
      applicantName: 'Deepa Sundaram',
      score: 704,
      riskLevel: 'MODERATE_ESTIMATED RISK',
      estimatedRepaymentDifficulty: 30,
      modelConfidence: 80,
    },
  },
];

export const mockAllAdminApplications: (CreditApplication & {
  triggerReason?: string;
  sectorTag?: string;
})[] = [
  ...mockPriorityReviewQueue,
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
    sectorTag: 'Swiggy Delivery Partner',
    assessment: mockUserAssessment,
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
    sectorTag: 'Swiggy Delivery Partner',
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
      underwriterName: 'Rajesh Nair (Credit Reviewer)',
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
    sectorTag: 'Swiggy Delivery Partner',
    assessment: {
      ...mockUserAssessment,
      id: 'EVA-6921',
      score: 710,
      riskLevel: 'MODERATE_ESTIMATED RISK',
      estimatedRepaymentDifficulty: 31,
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
    sectorTag: 'Swiggy Delivery Partner',
  },
];

export function getAdminApplicationById(
  id: string
): CreditApplication & { triggerReason?: string; sectorTag?: string } {
  const cleanId = id.toUpperCase();
  const found = mockAllAdminApplications.find(
    (app) => app.id.toUpperCase() === cleanId
  );
  if (found) return found;

  // Fallback for any dynamic test ID
  return {
    ...mockAllAdminApplications[0],
    id: cleanId,
  };
}

export const mockModelInsights: ModelInsights = {
  modelVersion: 'v2.4-volatility-prod',
  lastTrainedAt: '2026-09-10T04:00:00Z',
  datasetRecordsCount: 482000,
  totalAssessmentsGenerated: 14280,
  topFeatures: [
    {
      feature: 'shock_recovery_rate',
      displayName: 'Income Shock Rebound Velocity',
      importance: 0.26,
      description: 'Days required to return to 90%+ baseline cashflow following cyclical earning dips.',
    },
    {
      feature: 'utility_micro_punctuality',
      displayName: 'Micro-Obligation & Utility Cadence',
      importance: 0.22,
      description: '24-cycle on-time payment track record across electricity, gas cylinder, and telecom.',
    },
    {
      feature: 'gig_platform_tenure',
      displayName: 'Verified Platform Tenure (Months)',
      importance: 0.18,
      description: 'Cumulative active months with authenticated delivery or service partner ratings.',
    },
    {
      feature: 'rolling_volatility_index',
      displayName: '12-Week Volatility Index',
      importance: 0.14,
      description: 'Standardized coefficient of variation across rolling weekly inflow distributions.',
    },
    {
      feature: 'aa_inflow_volume',
      displayName: 'Account Aggregator Inflow Depth',
      importance: 0.09,
      description: 'Total monthly settlement volume verified via RBI-licensed Account Aggregator network.',
    },
    {
      feature: 'fixed_debt_cushion',
      displayName: 'Commitment Inflow Cushion',
      importance: 0.05,
      description: 'Residual disposable cashflow margin remaining after mandatory micro-commitments.',
    },
    {
      feature: 'platform_rating_consistency',
      displayName: 'Platform Service Quality Rating',
      importance: 0.04,
      description: 'Sustained customer feedback score (>4.8★) indicating high gig partner retention.',
    },
    {
      feature: 'seasonal_weather_multiplier',
      displayName: 'Monsoon Variance Calibration',
      importance: 0.02,
      description: 'Localized precipitation adjustment preventing false default attribution during extreme rain.',
    },
  ],
  fairnessMetrics: [
    {
      attribute: 'Geographic Density',
      demographicGroup: 'Metro (BLR/HYD) vs. Tier-2 Hubs (MYS/HUB)',
      parityRatio: 0.98,
      equalizedOddsDifference: 0.01,
      auditStatus: 'FAIR',
    },
    {
      attribute: 'Platform Concentration',
      demographicGroup: 'Swiggy/Zomato vs. Urban Company vs. Auto Fleets',
      parityRatio: 0.96,
      equalizedOddsDifference: 0.02,
      auditStatus: 'FAIR',
    },
    {
      attribute: 'Gender Representation',
      demographicGroup: 'Women Partners (Salon/Craft) vs. General Fleet',
      parityRatio: 0.97,
      equalizedOddsDifference: 0.02,
      auditStatus: 'FAIR',
    },
    {
      attribute: 'Worker Age Brackets',
      demographicGroup: 'Youth (18–24) vs. Senior Partners (45+)',
      parityRatio: 0.95,
      equalizedOddsDifference: 0.03,
      auditStatus: 'FAIR',
    },
  ],
};

export interface SectorRiskDistributionData {
  sector: string;
  lowerRisk: number;
  moderateRisk: number;
  higherRisk: number;
  manualReview: number;
  total: number;
}

export const mockSectorRiskStackedData: SectorRiskDistributionData[] = [
  {
    sector: 'Food Delivery',
    lowerRisk: 4240,
    moderateRisk: 1780,
    higherRisk: 480,
    manualReview: 340,
    total: 6840,
  },
  {
    sector: 'Home Services',
    lowerRisk: 2050,
    moderateRisk: 820,
    higherRisk: 210,
    manualReview: 130,
    total: 3210,
  },
  {
    sector: 'Ride Logistics',
    lowerRisk: 1420,
    moderateRisk: 930,
    higherRisk: 380,
    manualReview: 160,
    total: 2890,
  },
  {
    sector: 'Micro-Vendors',
    lowerRisk: 710,
    moderateRisk: 380,
    higherRisk: 170,
    manualReview: 80,
    total: 1340,
  },
];

export interface ShockRecoveryCurvePoint {
  day: string;
  foodDelivery: number;
  homeServices: number;
  rideLogistics: number;
  formalBenchmark: number;
}

export const mockShockRecoveryCurveData: ShockRecoveryCurvePoint[] = [
  { day: 'Day 0', foodDelivery: 45, homeServices: 50, rideLogistics: 40, formalBenchmark: 95 },
  { day: 'Day 3', foodDelivery: 58, homeServices: 64, rideLogistics: 52, formalBenchmark: 96 },
  { day: 'Day 6', foodDelivery: 74, homeServices: 78, rideLogistics: 68, formalBenchmark: 97 },
  { day: 'Day 9', foodDelivery: 88, homeServices: 89, rideLogistics: 82, formalBenchmark: 98 },
  { day: 'Day 12', foodDelivery: 96, homeServices: 95, rideLogistics: 91, formalBenchmark: 99 },
  { day: 'Day 15', foodDelivery: 100, homeServices: 98, rideLogistics: 97, formalBenchmark: 100 },
  { day: 'Day 18', foodDelivery: 102, homeServices: 101, rideLogistics: 100, formalBenchmark: 100 },
  { day: 'Day 21', foodDelivery: 101, homeServices: 100, rideLogistics: 101, formalBenchmark: 100 },
];


