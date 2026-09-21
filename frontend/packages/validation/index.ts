// @parakh/validation
// Shared Zod schemas for application intake, validation, and underwriter reviews

import { z } from 'zod';

export const EmploymentTypeSchema = z.enum([
  'GIG_WORKER',
  'INFORMAL_VENDOR',
  'FREELANCER',
  'DAILY_WAGE',
]);

export const IncomeFrequencySchema = z.enum([
  'daily',
  'weekly',
  'irregular',
  'monthly',
]);

// Step-by-step New Application Schema
export const ApplicationFormSchema = z.object({
  // 1. Personal Profile
  fullName: z
    .string()
    .min(3, 'Full name must be at least 3 characters')
    .max(80, 'Full name cannot exceed 80 characters'),
  phone: z
    .string()
    .regex(/^[6-9]\d{9}$/, 'Please enter a valid 10-digit Indian mobile number'),
  city: z
    .string()
    .min(2, 'City is required'),

  // 2. Work & Platform Details
  employmentType: EmploymentTypeSchema,
  primaryPlatform: z
    .string()
    .min(2, 'Platform or trade name is required (e.g. Zomato, Swiggy, Urban Company, Local Shop)'),
  tenureMonths: z
    .number()
    .min(1, 'Tenure must be at least 1 month')
    .max(360, 'Invalid tenure duration'),

  // 3. Volatility-Aware Inflow Signals
  incomeFrequency: IncomeFrequencySchema,
  averageMonthlyIncome: z
    .number()
    .min(5000, 'Average monthly inflow must be at least ₹5,000')
    .max(500000, 'Amount exceeds prototype intake limits'),
  lowestMonthIncome: z
    .number()
    .min(0, 'Lowest month income cannot be negative'),
  typicalRecoveryDays: z
    .number()
    .min(1, 'Recovery period must be at least 1 day')
    .max(60, 'Maximum recovery window is 60 days'),

  // 4. Obligations
  monthlyRent: z.number().min(0, 'Rent cannot be negative'),
  utilityExpenses: z.number().min(0, 'Utility expenses cannot be negative'),
  existingEmiObligations: z.number().min(0, 'Existing EMIs cannot be negative'),

  // 5. Purpose & Consent
  requestedAmount: z
    .number()
    .min(5000, 'Minimum requested amount is ₹5,000')
    .max(200000, 'Maximum evaluation cap is ₹2,00,000'),
  purpose: z
    .string()
    .min(3, 'Please describe the intended purpose (e.g., Vehicle repair, inventory purchase)'),
  consentGiven: z
    .boolean()
    .refine((val) => val === true, 'You must provide consent for alternative data assessment'),
});

export type ApplicationFormData = z.infer<typeof ApplicationFormSchema>;

// Underwriter Human Review Schema
export const UnderwriterReviewSchema = z.object({
  action: z.enum(['REQUEST_VERIFICATION', 'MANUAL_REVIEW', 'RECORD_OUTCOME']),
  decisionNotes: z
    .string()
    .min(10, 'Review rationale must be at least 10 characters'),
  verificationItems: z
    .array(z.string())
    .optional(),
  overrideRiskLevel: z
    .enum([
      'LOWER_ESTIMATED RISK',
      'MODERATE_ESTIMATED RISK',
      'HIGHER_ESTIMATED RISK',
      'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW',
    ])
    .optional(),
});

export type UnderwriterReviewInput = z.infer<typeof UnderwriterReviewSchema>;
