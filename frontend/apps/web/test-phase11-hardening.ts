/**
 * Phase 11 Frontend & API Hardening Verification Suite
 *
 * Verifies:
 * 1. Safe retry policy: GET requests retry on transient 502/503/network errors; POST requests NEVER retry.
 * 2. Corrupted JSON response parsing gracefully wraps into ApiError (status 502, code SCHEMA_ERROR).
 * 3. Status error normalization (401 UNAUTHORIZED, 403 FORBIDDEN, 404 NOT_FOUND, 500 SERVER_ERROR).
 * 4. Token lifecycle: Bearer header attached consistently; onUnauthorized callback fired on 401.
 * 5. Adapter resilience: null/empty response data handled gracefully without runtime crashes.
 */

import { ParakhApiClient, ApiError, adaptApplication, adaptAssessment, adaptPortfolioAnalytics } from '@parakh/api';

async function runPhase11HardeningTests() {
  console.log('🧪 Starting Phase 11 Frontend & API Hardening Verification...\n');

  let passed = 0;
  let total = 0;

  function assert(condition: boolean, msg: string) {
    total++;
    if (!condition) {
      console.error(`❌ FAILED: ${msg}`);
      throw new Error(`Assertion failed: ${msg}`);
    }
    console.log(`✅ PASSED: ${msg}`);
    passed++;
  }

  const originalFetch = globalThis.fetch;

  try {
    // -----------------------------------------------------------------------
    // TEST 1: Idempotent GET Request Retries on Transient 503 Server Error
    // -----------------------------------------------------------------------
    console.log('\n--- 1. Idempotent GET Retry Test ---');
    let getAttempts = 0;
    globalThis.fetch = async (url: any, init: any) => {
      getAttempts++;
      if (getAttempts === 1) {
        // First attempt fails with transient 503
        return new Response(JSON.stringify({ detail: 'Service Temporarily Unavailable' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      // Second attempt succeeds
      return new Response(JSON.stringify({ status: 'ok', data: [1, 2, 3] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    const client = new ParakhApiClient({ baseUrl: 'http://test-server' });
    const getResult = await client.request<{ status: string; data: number[] }>('/test-get', { method: 'GET' });
    assert(getResult.status === 'ok', 'GET request succeeded on retry');
    assert(getAttempts === 2, `GET request retried exactly once on transient failure (attempts: ${getAttempts})`);

    // -----------------------------------------------------------------------
    // TEST 2: Non-Idempotent POST Mutation is NEVER Retried
    // -----------------------------------------------------------------------
    console.log('\n--- 2. Non-Idempotent Mutation Non-Retry Test ---');
    let postAttempts = 0;
    globalThis.fetch = async (url: any, init: any) => {
      postAttempts++;
      return new Response(JSON.stringify({ detail: 'Internal Server Error' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    let postFailedWithApiError = false;
    try {
      await client.request('/test-post', { method: 'POST', body: JSON.stringify({ action: 'SUBMIT_REVIEW' }) });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 503) {
        postFailedWithApiError = true;
      }
    }
    assert(postFailedWithApiError, 'POST request failed with ApiError');
    assert(postAttempts === 1, `POST mutation was NOT retried automatically (attempts: ${postAttempts})`);

    // -----------------------------------------------------------------------
    // TEST 3: Corrupted / Malformed JSON on 200 Handled as SCHEMA_ERROR
    // -----------------------------------------------------------------------
    console.log('\n--- 3. Corrupted Response Body Parsing Test ---');
    globalThis.fetch = async () => {
      // Simulate proxy or server returning HTML or invalid JSON on 200
      return new Response('<html><head><title>502 Bad Gateway</title></head><body>Proxy Error</body></html>', {
        status: 200,
        headers: { 'Content-Type': 'text/html' },
      });
    };

    let corruptHandled = false;
    try {
      await client.request('/test-corrupt', { method: 'GET', maxRetries: 0 });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 502 && err.code === 'SCHEMA_ERROR') {
        corruptHandled = true;
      }
    }
    assert(corruptHandled, 'Corrupted JSON response converted to ApiError 502 SCHEMA_ERROR');

    // -----------------------------------------------------------------------
    // TEST 4: HTTP Status Error Normalization (401, 403, 404, 500)
    // -----------------------------------------------------------------------
    console.log('\n--- 4. HTTP Error Normalization Test ---');
    const testCases = [
      { status: 401, expectedCode: 'UNAUTHORIZED' },
      { status: 403, expectedCode: 'FORBIDDEN' },
      { status: 404, expectedCode: 'NOT_FOUND' },
      { status: 422, expectedCode: 'SCHEMA_ERROR' },
      { status: 500, expectedCode: 'SERVER_ERROR' },
    ];

    for (const tc of testCases) {
      globalThis.fetch = async () => {
        return new Response(JSON.stringify({ detail: `Error for status ${tc.status}` }), {
          status: tc.status,
          headers: { 'Content-Type': 'application/json' },
        });
      };

      try {
        await client.request('/test-status', { method: 'GET', maxRetries: 0 });
        assert(false, `Expected request to throw for HTTP ${tc.status}`);
      } catch (err: any) {
        assert(
          err instanceof ApiError && err.status === tc.status && err.code === tc.expectedCode,
          `HTTP ${tc.status} normalized correctly to code ${tc.expectedCode}`
        );
      }
    }

    // -----------------------------------------------------------------------
    // TEST 5: JWT Token Attachment & onUnauthorized Callback
    // -----------------------------------------------------------------------
    console.log('\n--- 5. Auth Token Lifecycle & onUnauthorized Test ---');
    let capturedAuthHeader: string | null = null;
    let unauthorizedFired = false;

    const authClient = new ParakhApiClient({
      baseUrl: 'http://test-server',
      onUnauthorized: () => {
        unauthorizedFired = true;
      },
    });

    authClient.setToken('test_jwt_token_sample_abc123');

    globalThis.fetch = async (url: any, init: any) => {
      capturedAuthHeader = init?.headers?.['Authorization'] || null;
      return new Response(JSON.stringify({ detail: 'Session expired' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    };

    try {
      await authClient.request('/test-auth', { method: 'GET', maxRetries: 0 });
    } catch {}

    assert(capturedAuthHeader === 'Bearer test_jwt_token_sample_abc123', 'Bearer JWT token attached to request header');
    assert(unauthorizedFired, 'onUnauthorized callback triggered when receiving 401');

    authClient.clearToken();
    assert(authClient.getToken() === null, 'Token cleared properly');

    // -----------------------------------------------------------------------
    // TEST 6: Adapters Handle Empty and Null Data Robustly
    // -----------------------------------------------------------------------
    console.log('\n--- 6. Adapters Resilience Test ---');
    const mockRawApp: any = {
      id: '11111111-1111-1111-1111-111111111111',
      applicant_profile_id: null,
      requested_loan_amount: '50000.00',
      loan_purpose: 'Equipment purchase',
      preferred_repayment_period: 12,
      status: 'SUBMITTED',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Adapt with null profile, null assessment, null review
    const adaptedApp = adaptApplication(mockRawApp, null, null, null);
    assert(adaptedApp.id === mockRawApp.id, 'adaptApplication handles null profile and assessments');
    assert(adaptedApp.applicantName === 'Applicant', 'adaptApplication defaults applicant name safely');
    assert(adaptedApp.assessment === undefined, 'adaptApplication safely leaves assessment undefined when absent');

    // Portfolio analytics with empty arrays
    const mockEmptyAnalytics: any = {
      total_applications_evaluated: 0,
      average_credit_score: null,
      average_risk_difficulty: null,
      assessment_completion_rate: 0,
      sector_risk_breakdown: [],
    };
    const adaptedAnalytics = adaptPortfolioAnalytics(mockEmptyAnalytics);
    assert(adaptedAnalytics.totalEvaluated === 0, 'adaptPortfolioAnalytics handles 0 evaluated count');
    assert(adaptedAnalytics.averageScore === null, 'adaptPortfolioAnalytics safely preserves null score when absent');
    assert(Array.isArray(adaptedAnalytics.sectorRisk) && adaptedAnalytics.sectorRisk.length === 0, 'adaptPortfolioAnalytics handles empty sector breakdown');

    console.log(`\n🎉 All ${passed}/${total} Phase 11 Hardening Tests Passed!`);
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase11HardeningTests().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
