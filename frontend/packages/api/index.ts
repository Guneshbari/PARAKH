// @parakh/api
// Authoritative API Client and Contract Adapters for PARAKH Platform
// Single communication layer between Next.js frontend and FastAPI backend

import type {
  CreditApplication,
  CreditAssessmentResult,
  BorrowerProfile,
  UnderwriterReviewOutcome,
  LoginRequest,
  TokenResponse,
  UserResponse,
  UserCreateRequest,
} from '@parakh/types';

import { ApiError, type ApiErrorCode } from './errors';
import type {
  BackendUser,
  BackendUserCreate,
  BackendApplicantProfile,
  BackendApplicantProfileCreate,
  BackendApplication,
  BackendApplicationCreate,
  BackendAssessment,
  BackendFinancialSignal,
  BackendFinancialSignalCreate,
  BackendConsent,
  BackendConsentCreate,
  BackendUnderwriterReview,
  BackendUnderwriterReviewCreate,
  BackendModelVersion,
  BackendModelVersionCreate,
  BackendAuditLog,
  BackendPortfolioAnalytics,
  BackendSectorRiskItem,
} from './types';
import {
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  adaptBorrowerProfile,
  adaptPortfolioAnalytics,
  adaptSectorRisk,
  type AdaptedPortfolioAnalytics,
  type AdaptedSectorRisk,
} from './adapters';

export * from './errors';
export * from './types';
export * from './adapters';

export interface ApiClientConfig {
  baseUrl?: string;
  timeoutMs?: number;
  headers?: Record<string, string>;
  token?: string | null;
  onUnauthorized?: () => void;
}

export class ParakhApiClient {
  private baseUrl: string;
  private timeoutMs: number;
  private defaultHeaders: Record<string, string>;
  private token: string | null = null;
  private onUnauthorized?: () => void;

  constructor(config?: ApiClientConfig) {
    const envUrl =
      typeof process !== 'undefined' && process.env
        ? process.env.NEXT_PUBLIC_API_URL
        : undefined;
    this.baseUrl = config?.baseUrl || envUrl || 'http://localhost:8000';
    this.timeoutMs = config?.timeoutMs || 15000;
    this.token = config?.token || null;
    this.onUnauthorized = config?.onUnauthorized;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(config?.headers || {}),
    };
  }

  setToken(token: string | null): void {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  clearToken(): void {
    this.token = null;
  }

  public async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const headers: Record<string, string> = {
      ...this.defaultHeaders,
      ...((options?.headers as Record<string, string>) || {}),
    };

    if (this.token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers,
      });

      if (!response.ok) {
        if (response.status === 401 && this.onUnauthorized) {
          this.onUnauthorized();
        }

        let errorData: unknown;
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }
        throw ApiError.fromResponse(response.status, errorData);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return undefined as unknown as T;
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      if (err instanceof Error && err.name === 'AbortError') {
        throw new ApiError(
          'Request timed out',
          408,
          null,
          'TIMEOUT',
          'The request timed out waiting for the server to respond.'
        );
      }
      throw new ApiError(
        err instanceof Error ? err.message : 'Network connection error occurred',
        0,
        err,
        'NETWORK_ERROR',
        'Unable to reach the server. Please check your network connection.'
      );
    } finally {
      clearTimeout(timer);
    }
  }

  // =========================================================================
  // 1. AUTHENTICATION & IDENTITY ENDPOINTS
  // =========================================================================

  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: credentials.email.trim().toLowerCase(),
        password: credentials.password,
      }),
    });
    if (response.access_token) {
      this.setToken(response.access_token);
    }
    return response;
  }

  async getMe(): Promise<UserResponse> {
    return this.request<UserResponse>('/api/v1/auth/me', {
      method: 'GET',
    });
  }

  async register(data: UserCreateRequest): Promise<UserResponse> {
    return this.request<UserResponse>('/api/v1/users', {
      method: 'POST',
      body: JSON.stringify({
        email: data.email.trim().toLowerCase(),
        password: data.password,
        role: data.role || 'APPLICANT',
      }),
    });
  }

  async getUserById(id: string): Promise<BackendUser> {
    return this.request<BackendUser>(`/api/v1/users/${encodeURIComponent(id)}`, {
      method: 'GET',
    });
  }

  async getUserByEmail(email: string): Promise<BackendUser> {
    return this.request<BackendUser>(`/api/v1/users/by-email/${encodeURIComponent(email)}`, {
      method: 'GET',
    });
  }

  async updateUser(id: string, data: Partial<BackendUserCreate>): Promise<BackendUser> {
    return this.request<BackendUser>(`/api/v1/users/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // =========================================================================
  // 2. APPLICANT PROFILES
  // =========================================================================

  async createApplicant(data: BackendApplicantProfileCreate): Promise<BackendApplicantProfile> {
    return this.request<BackendApplicantProfile>('/api/v1/applicants', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApplicantProfile(profileId: string): Promise<BackendApplicantProfile> {
    return this.request<BackendApplicantProfile>(`/api/v1/applicants/${encodeURIComponent(profileId)}`, {
      method: 'GET',
    });
  }

  async getApplicantByUserId(userId: string): Promise<BackendApplicantProfile> {
    return this.request<BackendApplicantProfile>(`/api/v1/applicants/user/${encodeURIComponent(userId)}`, {
      method: 'GET',
    });
  }

  async updateApplicantProfile(
    profileId: string,
    data: Partial<BackendApplicantProfileCreate>
  ): Promise<BackendApplicantProfile> {
    return this.request<BackendApplicantProfile>(`/api/v1/applicants/${encodeURIComponent(profileId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // =========================================================================
  // 3. CREDIT APPLICATIONS
  // =========================================================================

  async getApplications(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    applicant_profile_id?: string;
  }): Promise<BackendApplication[]> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.status) query.append('status', params.status);
    if (params?.applicant_profile_id) query.append('applicant_profile_id', params.applicant_profile_id);
    const qs = query.toString();
    return this.request<BackendApplication[]>(`/api/v1/applications${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  async createApplication(data: BackendApplicationCreate): Promise<BackendApplication> {
    return this.request<BackendApplication>('/api/v1/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApplicationById(applicationId: string): Promise<BackendApplication> {
    return this.request<BackendApplication>(`/api/v1/applications/${encodeURIComponent(applicationId)}`, {
      method: 'GET',
    });
  }

  async getApplicationsByApplicant(applicantProfileId: string): Promise<BackendApplication[]> {
    return this.request<BackendApplication[]>(
      `/api/v1/applications/applicant/${encodeURIComponent(applicantProfileId)}`,
      { method: 'GET' }
    );
  }

  async updateApplication(
    applicationId: string,
    data: Partial<BackendApplicationCreate>
  ): Promise<BackendApplication> {
    return this.request<BackendApplication>(`/api/v1/applications/${encodeURIComponent(applicationId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async updateApplicationStatus(
    applicationId: string,
    status: string,
    note?: string
  ): Promise<BackendApplication> {
    const query = new URLSearchParams({ status });
    if (note) query.append('note', note);
    return this.request<BackendApplication>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/status?${query.toString()}`,
      { method: 'PATCH' }
    );
  }

  // =========================================================================
  // 4. CREDIT ASSESSMENTS
  // =========================================================================

  async triggerAssessment(applicationId: string, modelVersionId?: string): Promise<BackendAssessment> {
    const qs = modelVersionId ? `?model_version_id=${encodeURIComponent(modelVersionId)}` : '';
    return this.request<BackendAssessment>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/assess${qs}`,
      {
        method: 'POST',
      }
    );
  }

  async getAssessmentById(assessmentId: string): Promise<BackendAssessment> {
    return this.request<BackendAssessment>(`/api/v1/assessments/${encodeURIComponent(assessmentId)}`, {
      method: 'GET',
    });
  }

  async getAssessmentsByApplication(applicationId: string): Promise<BackendAssessment[]> {
    return this.request<BackendAssessment[]>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/assessments`,
      { method: 'GET' }
    );
  }

  async getLatestAssessmentByApplication(applicationId: string): Promise<BackendAssessment> {
    return this.request<BackendAssessment>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/assessments/latest`,
      { method: 'GET' }
    );
  }

  // =========================================================================
  // 5. FINANCIAL SIGNALS
  // =========================================================================

  async recordFinancialSignals(
    applicationId: string,
    signals: BackendFinancialSignalCreate
  ): Promise<BackendFinancialSignal> {
    return this.request<BackendFinancialSignal>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/financial-signals`,
      {
        method: 'POST',
        body: JSON.stringify(signals),
      }
    );
  }

  async getFinancialSignals(applicationId: string): Promise<BackendFinancialSignal[]> {
    return this.request<BackendFinancialSignal[]>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/financial-signals`,
      { method: 'GET' }
    );
  }

  async getLatestFinancialSignals(applicationId: string): Promise<BackendFinancialSignal> {
    return this.request<BackendFinancialSignal>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/financial-signals/latest`,
      { method: 'GET' }
    );
  }

  // =========================================================================
  // 6. CONSENTS
  // =========================================================================

  async createConsent(data: BackendConsentCreate): Promise<BackendConsent> {
    return this.request<BackendConsent>('/api/v1/consents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getConsentsByApplication(applicationId: string): Promise<BackendConsent[]> {
    return this.request<BackendConsent[]>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/consents`,
      { method: 'GET' }
    );
  }

  async getActiveConsentsByApplication(applicationId: string): Promise<BackendConsent[]> {
    return this.request<BackendConsent[]>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/consents/active`,
      { method: 'GET' }
    );
  }

  async revokeConsent(consentId: string): Promise<BackendConsent> {
    return this.request<BackendConsent>(`/api/v1/consents/${encodeURIComponent(consentId)}/revoke`, {
      method: 'POST',
    });
  }

  // =========================================================================
  // 7. UNDERWRITER REVIEWS
  // =========================================================================

  async createReview(
    applicationId: string,
    review: BackendUnderwriterReviewCreate
  ): Promise<BackendUnderwriterReview> {
    const payload = {
      application_id: applicationId,
      ...review,
    };
    return this.request<BackendUnderwriterReview>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/reviews`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  async getReviewsByApplication(applicationId: string): Promise<BackendUnderwriterReview[]> {
    return this.request<BackendUnderwriterReview[]>(
      `/api/v1/applications/${encodeURIComponent(applicationId)}/reviews`,
      { method: 'GET' }
    );
  }

  async getReviewsByReviewer(reviewerId: string): Promise<BackendUnderwriterReview[]> {
    return this.request<BackendUnderwriterReview[]>(
      `/api/v1/reviewers/${encodeURIComponent(reviewerId)}/reviews`,
      { method: 'GET' }
    );
  }

  // =========================================================================
  // 8. MODEL VERSIONS
  // =========================================================================

  async createModelVersion(data: BackendModelVersionCreate): Promise<BackendModelVersion> {
    return this.request<BackendModelVersion>('/api/v1/model-versions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getModelVersions(params?: {
    skip?: number;
    limit?: number;
    is_active?: boolean;
  }): Promise<BackendModelVersion[]> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    const qs = query.toString();
    return this.request<BackendModelVersion[]>(`/api/v1/model-versions${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  async getActiveModelVersion(modelName: string): Promise<BackendModelVersion> {
    return this.request<BackendModelVersion>(
      `/api/v1/model-versions/active/${encodeURIComponent(modelName)}`,
      { method: 'GET' }
    );
  }

  async getModelVersionById(id: string): Promise<BackendModelVersion> {
    return this.request<BackendModelVersion>(`/api/v1/model-versions/${encodeURIComponent(id)}`, {
      method: 'GET',
    });
  }

  // =========================================================================
  // 9. AUDIT LOGS
  // =========================================================================

  async getAuditLogs(params?: {
    skip?: number;
    limit?: number;
    action?: string;
    entity_type?: string;
    entity_id?: string;
    user_id?: string;
  }): Promise<BackendAuditLog[]> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.append('skip', String(params.skip));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.action) query.append('action', params.action);
    if (params?.entity_type) query.append('entity_type', params.entity_type);
    if (params?.entity_id) query.append('entity_id', params.entity_id);
    if (params?.user_id) query.append('user_id', params.user_id);
    const qs = query.toString();
    return this.request<BackendAuditLog[]>(`/api/v1/audit-logs${qs ? `?${qs}` : ''}`, {
      method: 'GET',
    });
  }

  async getAuditLogById(auditId: string): Promise<BackendAuditLog> {
    return this.request<BackendAuditLog>(`/api/v1/audit-logs/${encodeURIComponent(auditId)}`, {
      method: 'GET',
    });
  }

  // =========================================================================
  // 10. PORTFOLIO ANALYTICS
  // =========================================================================

  async getPortfolioAnalytics(): Promise<BackendPortfolioAnalytics> {
    return this.request<BackendPortfolioAnalytics>('/api/v1/analytics/portfolio', {
      method: 'GET',
    });
  }

  async getSectorRisk(): Promise<BackendSectorRiskItem[]> {
    return this.request<BackendSectorRiskItem[]>('/api/v1/analytics/sector-risk', {
      method: 'GET',
    });
  }

  async getPortfolioAnalyticsAdapted(): Promise<AdaptedPortfolioAnalytics> {
    const raw = await this.getPortfolioAnalytics();
    return adaptPortfolioAnalytics(raw);
  }

  async getSectorRiskAdapted(): Promise<AdaptedSectorRisk[]> {
    const raw = await this.getSectorRisk();
    return adaptSectorRisk(raw);
  }

  // =========================================================================
  // 11. ADAPTER-BACKED CONVENIENCE METHODS (Frontend Domain Models)
  // =========================================================================

  async getApplicationAdapted(
    applicationId: string,
    applicantProfile?: BackendApplicantProfile | null
  ): Promise<CreditApplication> {
    const rawApp = await this.getApplicationById(applicationId);
    let profile = applicantProfile;
    if (!profile && rawApp.applicant_profile_id) {
      try {
        profile = await this.getApplicantProfile(rawApp.applicant_profile_id);
      } catch {
        profile = null;
      }
    }
    return adaptApplication(rawApp, profile);
  }

  async getApplicationsAdapted(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    applicant_profile_id?: string;
  }): Promise<CreditApplication[]> {
    const rawApps = await this.getApplications(params);
    return rawApps.map((raw) => adaptApplication(raw));
  }

  async getLatestAssessmentAdapted(applicationId: string): Promise<CreditAssessmentResult> {
    const raw = await this.getLatestAssessmentByApplication(applicationId);
    return adaptAssessment(raw);
  }

  async getAssessmentAdapted(assessmentId: string): Promise<CreditAssessmentResult> {
    const raw = await this.getAssessmentById(assessmentId);
    return adaptAssessment(raw);
  }

  async recordReviewOutcomeAdapted(
    applicationId: string,
    review: BackendUnderwriterReviewCreate
  ): Promise<UnderwriterReviewOutcome> {
    const raw = await this.createReview(applicationId, review);
    return adaptReviewOutcome(raw);
  }

  async getBorrowerProfileAdapted(
    applicantProfileId: string,
    user?: BackendUser | null
  ): Promise<BorrowerProfile> {
    const rawProfile = await this.getApplicantProfile(applicantProfileId);
    let rawUser = user;
    if (!rawUser && rawProfile.user_id) {
      try {
        rawUser = await this.getUserById(rawProfile.user_id);
      } catch {
        rawUser = null;
      }
    }
    return adaptBorrowerProfile(rawProfile, rawUser);
  }
}

// Singleton instance & factory
export const api: ParakhApiClient = new ParakhApiClient();

export function createApiClient(config?: ApiClientConfig): ParakhApiClient {
  return new ParakhApiClient(config);
}
