// Comprehensive Unit Test Suite for @parakh/api
// Tests ApiError, enum adapters, entity adapters, and ParakhApiClient
import assert from 'node:assert';
import {
  ApiError,
  adaptRiskLevel,
  reverseAdaptRiskLevel,
  adaptApplicationStatus,
  reverseAdaptApplicationStatus,
  adaptUserRole,
  adaptReviewOutcomeStatus,
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  adaptBorrowerProfile,
  ParakhApiClient,
  createApiClient,
} from './index';
import type {
  BackendApplication,
  BackendCreditAssessmentResponse,
  BackendReviewOutcomeResponse,
  BackendApplicantProfile,
  BackendUser,
} from './types';

async function runTests() {
  console.log('--- Running @parakh/api Tests ---');

  // =========================================================================
  // 1. ApiError Tests
  // =========================================================================
  console.log('1. Testing ApiError status code mapping and classification...');

  const err401 = ApiError.fromResponse(401, { detail: 'Could not validate credentials' });
  assert.strictEqual(err401.status, 401);
  assert.strictEqual(err401.code, 'UNAUTHORIZED');
  assert.strictEqual(err401.userMessage, 'Could not validate credentials');
  assert.strictEqual(err401.isUnauthorized(), true);
  assert.strictEqual(err401.isForbidden(), false);

  const err403 = ApiError.fromResponse(403, { detail: 'Insufficient permissions' });
  assert.strictEqual(err403.code, 'FORBIDDEN');
  assert.strictEqual(err403.isForbidden(), true);

  const err404 = ApiError.fromResponse(404, { detail: 'Application not found' });
  assert.strictEqual(err404.code, 'NOT_FOUND');
  assert.strictEqual(err404.isNotFound(), true);

  const err409 = ApiError.fromResponse(409, { detail: 'Active application already exists' });
  assert.strictEqual(err409.code, 'CONFLICT');
  assert.strictEqual(err409.isConflict(), true);

  const err422 = ApiError.fromResponse(422, {
    detail: [{ loc: ['body', 'requested_loan_amount'], msg: 'Field required', type: 'value_error.missing' }],
  });
  assert.strictEqual(err422.code, 'SCHEMA_ERROR');
  assert.strictEqual(err422.isValidationError(), true);
  assert.strictEqual(err422.userMessage, 'requested_loan_amount: Field required');

  const err500 = ApiError.fromResponse(500, { detail: 'Database connection failed' });
  assert.strictEqual(err500.code, 'SERVER_ERROR');
  assert.strictEqual(err500.isServerError(), true);

  const errTimeout = new ApiError('Timeout', 408);
  assert.strictEqual(errTimeout.isTimeout(), true);

  const errNetwork = new ApiError('Failed to fetch', 0);
  assert.strictEqual(errNetwork.isNetworkError(), true);

  console.log('   ✓ ApiError classification passed');

  // =========================================================================
  // 2. Enum Adapter Tests
  // =========================================================================
  console.log('2. Testing Enum Adapters...');

  // Risk Level
  assert.strictEqual(adaptRiskLevel('LOWER'), 'LOWER_ESTIMATED RISK');
  assert.strictEqual(adaptRiskLevel('MODERATE'), 'MODERATE_ESTIMATED RISK');
  assert.strictEqual(adaptRiskLevel('HIGHER'), 'HIGHER_ESTIMATED RISK');
  assert.strictEqual(adaptRiskLevel('INSUFFICIENT'), 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW');
  assert.strictEqual(adaptRiskLevel('UNKNOWN_LEVEL'), 'MODERATE_ESTIMATED RISK'); // fallback

  assert.strictEqual(reverseAdaptRiskLevel('LOWER_ESTIMATED RISK'), 'LOWER');
  assert.strictEqual(reverseAdaptRiskLevel('MODERATE_ESTIMATED RISK'), 'MODERATE');
  assert.strictEqual(reverseAdaptRiskLevel('HIGHER_ESTIMATED RISK'), 'HIGHER');
  assert.strictEqual(reverseAdaptRiskLevel('INSUFFICIENT_EVIDENCE_MANUAL_REVIEW'), 'INSUFFICIENT');

  // Application Status
  assert.strictEqual(adaptApplicationStatus('DRAFT'), 'SUBMITTED');
  assert.strictEqual(adaptApplicationStatus('SUBMITTED'), 'SUBMITTED');
  assert.strictEqual(adaptApplicationStatus('UNDER_REVIEW'), 'DATA_VALIDATION');
  assert.strictEqual(adaptApplicationStatus('ASSESSED'), 'ASSESSMENT_COMPLETED');
  assert.strictEqual(adaptApplicationStatus('MANUAL_REVIEW'), 'MANUAL_REVIEW_REQUIRED');
  assert.strictEqual(adaptApplicationStatus('COMPLETED'), 'REVIEW_COMPLETED');
  assert.strictEqual(adaptApplicationStatus('UNKNOWN'), 'SUBMITTED');

  assert.strictEqual(reverseAdaptApplicationStatus('SUBMITTED'), 'SUBMITTED');
  assert.strictEqual(reverseAdaptApplicationStatus('DATA_VALIDATION'), 'UNDER_REVIEW');
  assert.strictEqual(reverseAdaptApplicationStatus('FINANCIAL_ANALYSIS'), 'UNDER_REVIEW');
  assert.strictEqual(reverseAdaptApplicationStatus('ASSESSMENT_COMPLETED'), 'ASSESSED');
  assert.strictEqual(reverseAdaptApplicationStatus('MANUAL_REVIEW_REQUIRED'), 'MANUAL_REVIEW');
  assert.strictEqual(reverseAdaptApplicationStatus('REVIEW_COMPLETED'), 'COMPLETED');

  // User Role
  assert.strictEqual(adaptUserRole('APPLICANT'), 'applicant');
  assert.strictEqual(adaptUserRole('REVIEWER'), 'reviewer');
  assert.strictEqual(adaptUserRole('ADMIN'), 'admin');

  // Review Outcome Status
  assert.strictEqual(adaptReviewOutcomeStatus('REVIEWED'), 'OUTCOME_RECORDED');
  assert.strictEqual(adaptReviewOutcomeStatus('ESCALATED'), 'MANUAL_REVIEW_IN_PROGRESS');
  assert.strictEqual(adaptReviewOutcomeStatus('ADDITIONAL_INFORMATION_REQUIRED'), 'VERIFICATION_REQUESTED');
  assert.strictEqual(adaptReviewOutcomeStatus(null), 'PENDING');

  console.log('   ✓ Enum Adapters passed');

  // =========================================================================
  // 3. Entity Adapter Tests
  // =========================================================================
  console.log('3. Testing Entity Adapters...');

  // Application Adapter
  const rawApp: BackendApplication = {
    id: 'app-12345',
    applicant_profile_id: 'prof-987',
    requested_loan_amount: '500000',
    loan_purpose: 'Working Capital Expansion',
    preferred_repayment_period: 24,
    status: 'UNDER_REVIEW',
    created_at: '2026-01-10T10:00:00Z',
    updated_at: '2026-01-11T12:00:00Z',
  };

  const rawProfile: BackendApplicantProfile = {
    id: 'prof-987',
    user_id: 'user-001',
    full_name: 'Rajesh Sharma',
    phone_number: '+91 98765 43210',
    city: 'Mumbai',
    work_type: 'INFORMAL_VENDOR',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  const adaptedApp = adaptApplication(rawApp, rawProfile);
  assert.strictEqual(adaptedApp.id, 'app-12345');
  assert.strictEqual(adaptedApp.applicantId, 'prof-987');
  assert.strictEqual(adaptedApp.applicantName, 'Rajesh Sharma');
  assert.strictEqual(adaptedApp.phone, '+91 98765 43210');
  assert.strictEqual(adaptedApp.requestedAmount, 500000);
  assert.strictEqual(adaptedApp.purpose, 'Working Capital Expansion');
  assert.strictEqual(adaptedApp.employmentType, 'INFORMAL_VENDOR');
  assert.strictEqual(adaptedApp.status, 'DATA_VALIDATION');
  console.log('   ✓ adaptApplication passed');

  // Assessment Adapter
  const rawAssessment: BackendCreditAssessmentResponse = {
    id: 'asmt-456',
    application_id: 'app-12345',
    model_version_id: 'model-v1',
    credit_score: 750,
    score: 750,
    risk_level: 'LOWER',
    risk_probability: 0.12,
    confidence: 0.91,
    income_stability: 0.88,
    repayment_reliability: 0.96,
    debt_to_income: 0.18,
    key_factors: [
      'High daily order completion rate',
      'Consistent weekly income inflow',
      'Low debt obligations',
    ],
    explanation: {
      shap_values: [
        { feature: 'weekly_inflow', displayName: 'Weekly Cash Inflow', value: 0.35, explanation: 'Strong recurring inflows' },
        { feature: 'debt_ratio', displayName: 'Debt Ratio', value: 0.15, explanation: 'Manageable obligation load' },
      ],
      recommendations: ['Maintain current active order volume', 'Link recurring UPI collections'],
    },
    model_name: 'volatility-aware-risk-model',
    model_version: '1.0.0',
    assessed_at: '2026-01-12T09:00:00Z',
    created_at: '2026-01-12T09:00:00Z',
  };

  const adaptedAssessment = adaptAssessment(rawAssessment, 'Rajesh Sharma');
  assert.strictEqual(adaptedAssessment.id, 'asmt-456');
  assert.strictEqual(adaptedAssessment.applicantId, 'app-12345');
  assert.strictEqual(adaptedAssessment.applicantName, 'Rajesh Sharma');
  assert.strictEqual(adaptedAssessment.score, 750);
  assert.strictEqual(adaptedAssessment.riskLevel, 'LOWER_ESTIMATED RISK');
  assert.strictEqual(adaptedAssessment.estimatedRepaymentDifficulty, 12);
  assert.strictEqual(adaptedAssessment.modelConfidence, 91);
  assert.strictEqual(adaptedAssessment.modelName, 'volatility-aware-risk-model');
  assert.strictEqual(adaptedAssessment.modelVersion, '1.0.0');
  assert.strictEqual(adaptedAssessment.keyPositiveFactors.length, 2);
  assert.strictEqual(adaptedAssessment.keyAttentionFactors.length, 1);
  assert.strictEqual(adaptedAssessment.featureContributions.length, 2);
  assert.strictEqual(adaptedAssessment.featureContributions[0].featureName, 'weekly_inflow');
  assert.strictEqual(adaptedAssessment.featureContributions[0].direction, 'POSITIVE');
  assert.strictEqual(adaptedAssessment.actionableRecommendations.length, 2);
  assert.strictEqual(adaptedAssessment.isInsufficientEvidence, false);
  console.log('   ✓ adaptAssessment (LOWER scored) passed');

  // MODERATE assessment test
  const rawModerate: BackendCreditAssessmentResponse = {
    id: 'asmt-mod',
    application_id: 'app-mod',
    model_version_id: 'mv-1',
    credit_score: 685,
    score: 685,
    risk_level: 'MODERATE',
    risk_probability: 0.28,
    confidence: 0.82,
    assessed_at: '2026-01-12T10:00:00Z',
    created_at: '2026-01-12T10:00:00Z',
  };
  const adaptedModerate = adaptAssessment(rawModerate);
  assert.strictEqual(adaptedModerate.score, 685);
  assert.strictEqual(adaptedModerate.riskLevel, 'MODERATE_ESTIMATED RISK');
  assert.strictEqual(adaptedModerate.estimatedRepaymentDifficulty, 28);
  assert.strictEqual(adaptedModerate.modelConfidence, 82);
  console.log('   ✓ adaptAssessment (MODERATE scored) passed');

  // HIGHER assessment test
  const rawHigher: BackendCreditAssessmentResponse = {
    id: 'asmt-high',
    application_id: 'app-high',
    model_version_id: 'mv-1',
    credit_score: 590,
    score: 590,
    risk_level: 'HIGHER',
    risk_probability: 0.55,
    confidence: 0.78,
    assessed_at: '2026-01-12T11:00:00Z',
    created_at: '2026-01-12T11:00:00Z',
  };
  const adaptedHigher = adaptAssessment(rawHigher);
  assert.strictEqual(adaptedHigher.score, 590);
  assert.strictEqual(adaptedHigher.riskLevel, 'HIGHER_ESTIMATED RISK');
  assert.strictEqual(adaptedHigher.estimatedRepaymentDifficulty, 55);
  assert.strictEqual(adaptedHigher.modelConfidence, 78);
  console.log('   ✓ adaptAssessment (HIGHER scored) passed');

  // INSUFFICIENT evidence assessment test (Refusal contract)
  const rawInsufficient: BackendCreditAssessmentResponse = {
    id: 'asmt-insufficient',
    application_id: 'app-insufficient',
    model_version_id: 'mv-1',
    credit_score: null,
    score: null,
    risk_level: 'INSUFFICIENT',
    risk_probability: null,
    confidence: 0.0,
    assessment_status: 'INSUFFICIENT_EVIDENCE',
    model_name: 'volatility-aware-risk-model',
    model_version: '1.0.0',
    key_factors: [
      'Insufficient evidence: minimum 30 days of continuous platform telemetry required',
      'Missing primary income signal from connected digital accounts',
    ],
    explanation: {
      is_insufficient_evidence: true,
      missing_signals: [
        'Observed history below minimum requirement.',
        'Payout cycle count below minimum requirement.',
        'Core signal groups below minimum requirement.',
      ],
      shap_values: [],
      disclaimer: 'Alternative credit assessment prototype for underbanked gig workers under DPDP Act 2023. Not a formal credit bureau score.',
    },
    assessed_at: '2026-01-12T12:00:00Z',
    created_at: '2026-01-12T12:00:00Z',
  };

  const adaptedInsufficient = adaptAssessment(rawInsufficient);
  // Verify nulls are preserved and never fabricated
  assert.strictEqual(adaptedInsufficient.score, null, 'score must be null for INSUFFICIENT');
  assert.strictEqual(adaptedInsufficient.riskLevel, 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW');
  assert.strictEqual(adaptedInsufficient.estimatedRepaymentDifficulty, null, 'difficulty must be null for INSUFFICIENT');
  assert.strictEqual(adaptedInsufficient.modelConfidence, 0, 'confidence 0.0 must remain 0 and not become 85');
  assert.strictEqual(adaptedInsufficient.isInsufficientEvidence, true);
  assert.strictEqual(adaptedInsufficient.modelName, 'volatility-aware-risk-model');
  assert.strictEqual(adaptedInsufficient.modelVersion, '1.0.0');
  assert.strictEqual(adaptedInsufficient.assessmentStatus, 'INSUFFICIENT_EVIDENCE');
  assert.strictEqual(
    adaptedInsufficient.disclaimer,
    'Alternative credit assessment prototype for underbanked gig workers under DPDP Act 2023. Not a formal credit bureau score.'
  );
  assert.strictEqual(adaptedInsufficient.featureContributions.length, 0, 'empty shap_values must yield empty array');
  assert.strictEqual(adaptedInsufficient.missingSignals?.length, 3);
  assert.strictEqual(adaptedInsufficient.missingSignals?.[0], 'Observed history below minimum requirement.');
  // Confidence interval must not be inverted
  assert.ok(adaptedInsufficient.volatilityProfile.confidenceInterval[0] <= adaptedInsufficient.volatilityProfile.confidenceInterval[1]);
  console.log('   ✓ adaptAssessment (INSUFFICIENT evidence & null score preservation) passed');

  // Underwriter Review Adapter
  const rawReview: BackendReviewOutcomeResponse = {
    id: 'rev-789',
    application_id: 'app-12345',
    reviewer_id: 'usr-uw-1',
    outcome: 'REVIEWED',
    notes: 'Borrower exhibits robust cash reserves and positive supplier feedback.',
    created_at: '2026-01-13T14:30:00Z',
    updated_at: '2026-01-13T14:30:00Z',
  };

  const adaptedReview = adaptReviewOutcome(rawReview, 'Senior Underwriter Priya');
  assert.strictEqual(adaptedReview.status, 'OUTCOME_RECORDED');
  assert.strictEqual(adaptedReview.action, 'RECORD_OUTCOME');
  assert.strictEqual(adaptedReview.decisionNotes, 'Borrower exhibits robust cash reserves and positive supplier feedback.');
  assert.strictEqual(adaptedReview.underwriterId, 'usr-uw-1');
  assert.strictEqual(adaptedReview.underwriterName, 'Senior Underwriter Priya');
  console.log('   ✓ adaptReviewOutcome passed');

  // Borrower Profile Adapter
  const rawUser: BackendUser = {
    id: 'user-001',
    email: 'rajesh@sharmatextiles.in',
    role: 'APPLICANT',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  const adaptedProfile = adaptBorrowerProfile(rawProfile, rawUser.email);
  assert.strictEqual(adaptedProfile.id, 'prof-987');
  assert.strictEqual(adaptedProfile.fullName, 'Rajesh Sharma');
  assert.strictEqual(adaptedProfile.email, 'rajesh@sharmatextiles.in');
  assert.strictEqual(adaptedProfile.phone, '+91 98765 43210');
  assert.strictEqual(adaptedProfile.city, 'Mumbai');
  console.log('   ✓ adaptBorrowerProfile passed');

  // =========================================================================
  // 4. ParakhApiClient Unit Tests
  // =========================================================================
  console.log('4. Testing ParakhApiClient token management and HTTP contracts...');

  let unauthorizedTriggered = false;
  const client = createApiClient({
    baseUrl: 'http://localhost:8000',
    timeoutMs: 5000,
    onUnauthorized: () => {
      unauthorizedTriggered = true;
    },
  });

  assert.strictEqual(client.getToken(), null);
  client.setToken('test-jwt-bearer-token');
  assert.strictEqual(client.getToken(), 'test-jwt-bearer-token');
  client.clearToken();
  assert.strictEqual(client.getToken(), null);

  // Mock global fetch for testing request() plumbing
  const originalFetch = globalThis.fetch;
  try {
    // Test 1: Successful GET request with Bearer token
    client.setToken('auth-token-xyz');
    let capturedUrl = '';
    let capturedHeaders: Record<string, string> = {};

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      capturedHeaders = (init?.headers as Record<string, string>) || {};
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'usr-123', email: 'test@parakh.ai', role: 'APPLICANT' }),
      } as Response;
    };

    const me = await client.getMe();
    assert.strictEqual(me.email, 'test@parakh.ai');
    assert.strictEqual(capturedUrl, 'http://localhost:8000/api/v1/auth/me');
    assert.strictEqual(capturedHeaders['Authorization'], 'Bearer auth-token-xyz');
    assert.strictEqual(capturedHeaders['Content-Type'], 'application/json');

    // Test 2: 401 Unauthorized invokes onUnauthorized callback and throws ApiError
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token has expired' }),
      } as Response;
    };

    let errorThrown: ApiError | null = null;
    try {
      await client.getMe();
    } catch (e) {
      errorThrown = e as ApiError;
    }

    assert.notStrictEqual(errorThrown, null);
    assert.strictEqual(errorThrown?.status, 401);
    assert.strictEqual(errorThrown?.code, 'UNAUTHORIZED');
    assert.strictEqual(errorThrown?.userMessage, 'Token has expired');
    assert.strictEqual(unauthorizedTriggered, true);

    // Test 3: 404 Not Found error
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Application record not found' }),
      } as Response;
    };

    try {
      await client.getApplicationById('non-existent-id');
      assert.fail('Expected getApplicationById to throw 404');
    } catch (e) {
      const err = e as ApiError;
      assert.strictEqual(err.status, 404);
      assert.strictEqual(err.isNotFound(), true);
      assert.strictEqual(err.userMessage, 'Application record not found');
    }

    // Test 4: 204 No Content
    globalThis.fetch = async () => {
      return {
        ok: true,
        status: 204,
      } as Response;
    };

    const res204 = await client.request('/api/v1/dummy-204');
    assert.strictEqual(res204, undefined);

    // Test 5: triggerAssessmentAdapted delegates to POST /api/v1/applications/{id}/assess and returns adapted domain model
    let triggerUrl = '';
    let triggerMethod = '';
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      triggerUrl = String(input);
      triggerMethod = init?.method || 'GET';
      return {
        ok: true,
        status: 200,
        json: async () => ({
          id: 'asmt-e2e',
          application_id: 'app-999',
          model_version_id: 'mv-frozen',
          credit_score: 850,
          score: 850,
          risk_probability: 0.0264,
          risk_level: 'LOWER',
          confidence: 0.9967,
          model_name: 'volatility-aware-risk-model',
          model_version: '1.0.0',
          key_factors: ['Steady weekly income cadence'],
          explanation: {
            shap_values: [{ feature: 'tenure', displayName: 'Platform Tenure', value: 0.45 }],
            disclaimer: 'Prototype disclaimer',
          },
          assessed_at: '2026-09-24T05:00:00Z',
          created_at: '2026-09-24T05:00:00Z',
        }),
      } as Response;
    };

    const assessedResult = await client.triggerAssessmentAdapted('app-999');
    assert.strictEqual(triggerUrl, 'http://localhost:8000/api/v1/applications/app-999/assess');
    assert.strictEqual(triggerMethod, 'POST');
    assert.strictEqual(assessedResult.score, 850);
    assert.strictEqual(assessedResult.riskLevel, 'LOWER_ESTIMATED RISK');
    assert.strictEqual(assessedResult.estimatedRepaymentDifficulty, 3);
    assert.strictEqual(assessedResult.modelConfidence, 100);
    assert.strictEqual(assessedResult.modelName, 'volatility-aware-risk-model');
    assert.strictEqual(assessedResult.modelVersion, '1.0.0');
    assert.strictEqual(assessedResult.featureContributions.length, 1);

  } finally {
    globalThis.fetch = originalFetch;
  }

  console.log('   ✓ ParakhApiClient HTTP requests and error handling passed');

  console.log('\n=========================================');
  console.log('ALL @parakh/api TESTS PASSED SUCCESSFULLY!');
  console.log('=========================================');
}

runTests().catch((err) => {
  console.error('Test run failed:', err);
  process.exit(1);
});
