// @parakh/api
// Standardized API Error Model for PARAKH Platform

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'SCHEMA_ERROR'
  | 'SERVER_ERROR'
  | 'TIMEOUT'
  | 'NETWORK_ERROR'
  | 'UNKNOWN';

export class ApiError extends Error {
  public readonly status: number;
  public readonly code: ApiErrorCode;
  public readonly userMessage: string;
  public readonly details?: unknown;
  public readonly responseData?: unknown;

  constructor(
    message: string,
    status: number,
    responseData?: unknown,
    code?: ApiErrorCode,
    userMessage?: string
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.responseData = responseData;
    this.details = responseData;
    this.code = code || ApiError.deriveCode(status);
    this.userMessage = userMessage || ApiError.deriveUserMessage(this.code, responseData, message);

    // Maintains proper stack trace for where error was thrown (V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }

  static deriveCode(status: number): ApiErrorCode {
    switch (status) {
      case 400:
        return 'VALIDATION_ERROR';
      case 401:
        return 'UNAUTHORIZED';
      case 403:
        return 'FORBIDDEN';
      case 404:
        return 'NOT_FOUND';
      case 409:
        return 'CONFLICT';
      case 422:
        return 'SCHEMA_ERROR';
      case 408:
        return 'TIMEOUT';
      case 0:
        return 'NETWORK_ERROR';
      default:
        if (status >= 500) return 'SERVER_ERROR';
        return 'UNKNOWN';
    }
  }

  static deriveUserMessage(code: ApiErrorCode, responseData: unknown, fallback: string): string {
    // Check if FastAPI returned a specific { detail: string }
    if (typeof responseData === 'object' && responseData !== null && 'detail' in responseData) {
      const detail = (responseData as { detail: unknown }).detail;
      if (typeof detail === 'string') {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        // Pydantic validation error array: extract first field message
        const first = detail[0];
        if (typeof first === 'object' && first !== null && 'msg' in first) {
          const field = Array.isArray(first.loc) ? first.loc.slice(-1)[0] : '';
          return field ? `${field}: ${first.msg}` : String(first.msg);
        }
      }
    }

    switch (code) {
      case 'UNAUTHORIZED':
        return 'Your session has expired or credentials were invalid. Please sign in again.';
      case 'FORBIDDEN':
        return 'You do not have required clearance or authorization to perform this action.';
      case 'NOT_FOUND':
        return 'The requested record or resource could not be found.';
      case 'CONFLICT':
        return 'A record with this identifier or unique data already exists.';
      case 'SCHEMA_ERROR':
      case 'VALIDATION_ERROR':
        return 'The submitted data was incomplete or failed validation rules.';
      case 'TIMEOUT':
        return 'The request timed out waiting for the server to respond.';
      case 'NETWORK_ERROR':
        return 'Unable to reach the server. Please check your network connection.';
      case 'SERVER_ERROR':
        return 'A server processing error occurred. Please try again later.';
      default:
        return fallback || 'An unexpected error occurred.';
    }
  }

  static fromResponse(status: number, responseData: unknown, customMessage?: string): ApiError {
    const code = ApiError.deriveCode(status);
    const userMessage = ApiError.deriveUserMessage(code, responseData, customMessage || '');
    return new ApiError(
      customMessage || `API request failed with HTTP ${status}`,
      status,
      responseData,
      code,
      userMessage
    );
  }

  isUnauthorized(): boolean {
    return this.status === 401 || this.code === 'UNAUTHORIZED';
  }

  isForbidden(): boolean {
    return this.status === 403 || this.code === 'FORBIDDEN';
  }

  isNotFound(): boolean {
    return this.status === 404 || this.code === 'NOT_FOUND';
  }

  isConflict(): boolean {
    return this.status === 409 || this.code === 'CONFLICT';
  }

  isValidationError(): boolean {
    return this.status === 400 || this.status === 422 || this.code === 'VALIDATION_ERROR' || this.code === 'SCHEMA_ERROR';
  }

  isServerError(): boolean {
    return this.status >= 500 || this.code === 'SERVER_ERROR';
  }

  isTimeout(): boolean {
    return this.status === 408 || this.code === 'TIMEOUT';
  }

  isNetworkError(): boolean {
    return this.status === 0 || this.code === 'NETWORK_ERROR';
  }
}
