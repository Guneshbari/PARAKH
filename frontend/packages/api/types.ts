// @parakh/api
// Backend Transport Types (Exact FastAPI Pydantic Schemas - snake_case)

export type BackendUserRole = 'APPLICANT' | 'REVIEWER' | 'ADMIN';

export type BackendApplicationStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'ASSESSED'
  | 'MANUAL_REVIEW'
  | 'COMPLETED';

export type BackendRiskLevel = 'LOWER' | 'MODERATE' | 'HIGHER' | 'INSUFFICIENT';

export type BackendReviewOutcomeType =
  | 'REVIEWED'
  | 'ESCALATED'
  | 'ADDITIONAL_INFORMATION_REQUIRED';

export type BackendConsentDataSource =
  | 'PLATFORM'
  | 'FINANCIAL_ACTIVITY'
  | 'UTILITY';

export type BackendSignalSource =
  | 'PLATFORM'
  | 'FINANCIAL_ACTIVITY'
  | 'UTILITY'
  | 'DERIVED'
  | 'BANKING_AGGREGATOR'
  | 'GIG_PLATFORM'
  | 'TELECOM_UTILITY'
  | 'SELF_REPORTED';

// --- Auth & User Transport Models ---

export interface BackendLoginRequest {
  email: string;
  password: string;
}

export interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
  role: BackendUserRole;
}

export interface BackendUserCreate {
  email: string;
  password: string;
  role?: BackendUserRole;
}

export interface BackendUserResponse {
  id: string;
  email: string;
  role: BackendUserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Applicant Profile Transport Models ---

export interface BackendApplicantProfileCreate {
  user_id?: string;
  full_name?: string;
  phone_number?: string;
  city?: string;
  work_type?: string;
  experience_months?: number;
  average_working_days_per_week?: number;
  primary_income_source?: string;
  declared_monthly_income?: number;
  preferred_loan_purpose?: string;
}

export interface BackendApplicantProfileUpdate {
  full_name?: string;
  phone_number?: string;
  city?: string;
  work_type?: string;
  experience_months?: number;
  average_working_days_per_week?: number;
  primary_income_source?: string;
  declared_monthly_income?: number;
  preferred_loan_purpose?: string;
}

export interface BackendApplicantProfileResponse {
  id: string;
  user_id: string;
  full_name?: string | null;
  phone_number?: string | null;
  city?: string | null;
  work_type?: string | null;
  experience_months?: number | null;
  average_working_days_per_week?: number | null;
  primary_income_source?: string | null;
  declared_monthly_income?: number | string | null;
  preferred_loan_purpose?: string | null;
  created_at: string;
  updated_at: string;
}

// --- Application Transport Models ---

export interface BackendApplicationCreate {
  applicant_profile_id: string;
  requested_loan_amount: number | string;
  loan_purpose?: string;
  preferred_repayment_period?: number;
}

export interface BackendApplicationUpdate {
  requested_loan_amount?: number | string;
  loan_purpose?: string;
  preferred_repayment_period?: number;
  status?: BackendApplicationStatus;
}

export interface BackendApplicationStatusUpdate {
  status: BackendApplicationStatus;
}

export interface BackendApplicationResponse {
  id: string;
  applicant_profile_id: string;
  requested_loan_amount: number | string;
  loan_purpose?: string | null;
  preferred_repayment_period?: number | null;
  status: BackendApplicationStatus;
  created_at: string;
  updated_at: string;
}

// --- Assessment Transport Models ---

export interface BackendCreditAssessmentResponse {
  id: string;
  application_id: string;
  model_version_id: string;
  credit_score?: number | null;
  score?: number | null;
  risk_probability?: number | string | null;
  risk_level: BackendRiskLevel;
  confidence?: number | string | null;
  debt_to_income?: number | string | null;
  utilization?: number | string | null;
  income_stability?: number | string | null;
  repayment_reliability?: number | string | null;
  assessment_status?: string;
  model_name?: string | null;
  model_version?: string | null;
  key_factors?: string[];
  explanation?: Record<string, any>;
  assessed_at: string;
  created_at: string;
}

// --- Financial Signal Transport Models ---

export interface BackendFinancialSignalCreate {
  source: BackendSignalSource;
  average_income?: number | string;
  median_income?: number | string;
  income_volatility?: number | string;
  income_trend?: string;
  active_days?: number;
  payment_regularity?: number | string;
  cashflow_buffer?: number | string;
  existing_obligation?: number | string;
  platform_rating?: number | string;
  repayment_reliability?: number | string;
  signal_metadata?: Record<string, any>;
  application_id?: string;
  applicant_profile_id?: string;

  // Legacy/alias fields for compatibility
  average_daily_income?: number | string;
  income_volatility_score?: number | string;
  days_active_per_month?: number;
  total_monthly_turnover?: number | string;
  operating_expenses_ratio?: number | string;
  digital_payment_acceptance_ratio?: number | string;
  raw_signal_metadata?: Record<string, any>;
}

export interface BackendFinancialSignalResponse {
  id: string;
  application_id: string;
  applicant_profile_id?: string | null;
  source: BackendSignalSource;
  average_income?: number | string | null;
  median_income?: number | string | null;
  income_volatility?: number | string | null;
  income_trend?: string | null;
  active_days?: number | null;
  payment_regularity?: number | string | null;
  cashflow_buffer?: number | string | null;
  existing_obligation?: number | string | null;
  platform_rating?: number | string | null;
  repayment_reliability?: number | string | null;
  signal_metadata?: Record<string, any>;
  created_at: string;

  // Legacy/alias fields for compatibility
  average_daily_income?: number | string | null;
  income_volatility_score?: number | string | null;
  days_active_per_month?: number | null;
  total_monthly_turnover?: number | string | null;
  operating_expenses_ratio?: number | string | null;
  digital_payment_acceptance_ratio?: number | string | null;
  raw_signal_metadata?: Record<string, any>;
  recorded_at?: string;
}

// --- Consent Transport Models ---

export interface BackendConsentCreate {
  data_source: BackendConsentDataSource;
  purpose: string;
  application_id?: string;
  applicant_profile_id?: string;
  granted?: boolean;
}

export interface BackendConsentResponse {
  id: string;
  application_id?: string | null;
  applicant_profile_id?: string | null;
  data_source: BackendConsentDataSource;
  purpose: string;
  granted: boolean;
  granted_at: string;
  revoked_at?: string | null;
  created_at: string;
  updated_at: string;
}

// --- Review Transport Models ---

export interface BackendReviewOutcomeCreate {
  application_id?: string;
  reviewer_id: string;
  outcome: BackendReviewOutcomeType;
  notes?: string;
}

export interface BackendReviewOutcomeResponse {
  id: string;
  application_id: string;
  reviewer_id: string;
  outcome: BackendReviewOutcomeType;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

// --- Model Version Transport Models ---

export interface BackendModelVersionCreate {
  model_name: string;
  version: string;
  algorithm?: string;
  description?: string;
  is_active?: boolean;
}

export interface BackendModelVersionResponse {
  id: string;
  model_name: string;
  version: string;
  algorithm?: string | null;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Audit Log Transport Models ---

export interface BackendAuditLogResponse {
  id: string;
  timestamp: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  user_id?: string | null;
  application_id?: string | null;
  actor_role?: string | null;
  outcome: string;
  metadata?: Record<string, any>;
}

// Convenience Type Aliases
export type BackendUser = BackendUserResponse;
export type BackendApplicantProfile = BackendApplicantProfileResponse;
export type BackendApplication = BackendApplicationResponse;
export type BackendAssessment = BackendCreditAssessmentResponse;
export type BackendFinancialSignal = BackendFinancialSignalResponse;
export type BackendConsent = BackendConsentResponse;
export type BackendUnderwriterReview = BackendReviewOutcomeResponse;
export type BackendUnderwriterReviewCreate = BackendReviewOutcomeCreate;
export type BackendModelVersion = BackendModelVersionResponse;
export type BackendAuditLog = BackendAuditLogResponse;

