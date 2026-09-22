// @parakh/api
// Typed client contracts for communicating with FastAPI backend
// Strictly throws typed errors on HTTP failure; NO silent fallback to mock data

import type {
  CreditApplication,
  CreditAssessmentResult,
  BorrowerProfile,
  PortfolioAnalytics,
  ModelInsights,
  UnderwriterReviewOutcome,
  LoginRequest,
  TokenResponse,
  UserResponse,
  UserCreateRequest,
} from '@parakh/types';
import type { ApplicationFormData, UnderwriterReviewInput } from '@parakh/validation';

export interface ApiClientConfig {
  baseUrl?: string;
  timeoutMs?: number;
  headers?: Record<string, string>;
  token?: string | null;
  onUnauthorized?: () => void;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public responseData?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
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


  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
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
        throw new ApiError(
          `API request failed with HTTP status ${response.status}`,
          response.status,
          errorData
        );
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      if (err instanceof Error && err.name === 'AbortError') {
        throw new ApiError('Request timed out', 408);
      }
      throw new ApiError(
        err instanceof Error ? err.message : 'Network error occurred',
        0,
        err
      );
    } finally {
      clearTimeout(timer);
    }
  }

  // --- AUTHENTICATION & IDENTITY ENDPOINTS ---

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


  // --- USER / BORROWER ENDPOINTS ---

  async getBorrowerProfile(id: string): Promise<BorrowerProfile> {
    return this.request<BorrowerProfile>(`/api/v1/user/profile/${id}`);
  }

  async getBorrowerDashboard(applicantId: string): Promise<{
    assessment: CreditAssessmentResult;
    recentApplications: CreditApplication[];
  }> {
    return this.request(`/api/v1/user/dashboard/${applicantId}`);
  }

  async getUserApplications(applicantId: string): Promise<CreditApplication[]> {
    return this.request<CreditApplication[]>(`/api/v1/user/applications?applicantId=${encodeURIComponent(applicantId)}`);
  }

  async getApplicationById(id: string): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/api/v1/user/applications/${id}`);
  }

  async submitApplication(data: ApplicationFormData): Promise<CreditApplication> {
    return this.request<CreditApplication>('/api/v1/user/applications', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAssessmentResult(id: string): Promise<CreditAssessmentResult> {
    return this.request<CreditAssessmentResult>(`/api/v1/user/results/${id}`);
  }

  // --- ADMIN / UNDERWRITER ENDPOINTS ---

  async getAdminDashboard(): Promise<{
    portfolio: PortfolioAnalytics;
    priorityReviewQueue: CreditApplication[];
  }> {
    return this.request('/api/v1/admin/dashboard');
  }

  async getAdminApplications(filter?: { status?: string; riskLevel?: string }): Promise<CreditApplication[]> {
    const query = new URLSearchParams();
    if (filter?.status) query.append('status', filter.status);
    if (filter?.riskLevel) query.append('riskLevel', filter.riskLevel);
    const qs = query.toString();
    return this.request<CreditApplication[]>(`/api/v1/admin/applications${qs ? `?${qs}` : ''}`);
  }

  async getAdminApplicationDetail(id: string): Promise<CreditApplication> {
    return this.request<CreditApplication>(`/api/v1/admin/applications/${id}`);
  }

  async recordReviewAction(
    applicationId: string,
    review: UnderwriterReviewInput
  ): Promise<UnderwriterReviewOutcome> {
    return this.request<UnderwriterReviewOutcome>(`/api/v1/admin/applications/${applicationId}/review`, {
      method: 'POST',
      body: JSON.stringify(review),
    });
  }

  async getPortfolioAnalytics(): Promise<PortfolioAnalytics> {
    return this.request<PortfolioAnalytics>('/api/v1/admin/analytics');
  }

  async getModelInsights(): Promise<ModelInsights> {
    return this.request<ModelInsights>('/api/v1/admin/model-insights');
  }
}

// Singleton instance & factory
export const api: ParakhApiClient = new ParakhApiClient();

export function createApiClient(config?: ApiClientConfig): ParakhApiClient {
  return new ParakhApiClient(config);
}

