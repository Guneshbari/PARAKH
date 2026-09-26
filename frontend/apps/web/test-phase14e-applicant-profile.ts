/**
 * Phase 14E: Frontend Applicant Profile Editing Verification Test Suite (P2-05)
 *
 * Verifies end-to-end frontend API client contract, endpoint routing,
 * request payload serialization, partial updates, and error handling.
 */

import assert from 'assert';
import {
  ParakhApiClient,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplicantProfileUpdate,
} from '@parakh/api';

async function runPhase14EFrontendTests() {
  console.log('=============================================================');
  console.log('Phase 14E: Applicant Profile Editing Frontend Contract Test');
  console.log('=============================================================\n');

  const client = new ParakhApiClient({ baseUrl: 'http://localhost:8000' });

  // -------------------------------------------------------------------------
  // Test 1: Method Exposure on ApiClient
  // -------------------------------------------------------------------------
  console.log('Test 1: Verifying profile methods exposed on ApiClient...');
  assert.strictEqual(typeof client.updateApplicantProfile, 'function');
  assert.strictEqual(typeof client.getApplicantProfile, 'function');
  assert.strictEqual(typeof client.getApplicantByUserId, 'function');
  console.log('✓ updateApplicantProfile, getApplicantProfile, and getApplicantByUserId exposed.\n');

  // Intercept fetch for isolated deterministic contract verification
  const originalFetch = globalThis.fetch;
  const interceptedCalls: Array<{ url: string; method: string; body: string | null; headers: Record<string, string> }> = [];

  function setupMockFetch(responder: (req: { url: string; method: string; body: string | null }) => Response) {
    interceptedCalls.length = 0;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      const method = init?.method || 'GET';
      const body = (init?.body as string) || null;
      const headers = (init?.headers as Record<string, string>) || {};
      interceptedCalls.push({ url, method, body, headers });
      return responder({ url, method, body });
    };
  }

  const mockProfileId = '11111111-1111-1111-1111-111111111111';
  const mockUserId = '00000000-0000-0000-0000-000000000001';

  const initialProfile: BackendApplicantProfile = {
    id: mockProfileId,
    user_id: mockUserId,
    gig_work_type: 'Food Delivery',
    work_type: 'Food Delivery',
    years_working: 2.0,
    average_working_days: 24,
    business_or_loan_purpose: 'Electric Scooter Battery Swap',
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-09-01T10:00:00Z',
  };

  const updatedProfile: BackendApplicantProfile = {
    id: mockProfileId,
    user_id: mockUserId,
    gig_work_type: 'Ride Hailing',
    work_type: 'Ride Hailing',
    years_working: 3.5,
    average_working_days: 26,
    business_or_loan_purpose: 'Commercial Vehicle Maintenance',
    created_at: '2026-09-01T10:00:00Z',
    updated_at: '2026-09-27T01:00:00Z',
  };

  try {
    // -----------------------------------------------------------------------
    // Test 2: PATCH updateApplicantProfile Payload Serialization
    // -----------------------------------------------------------------------
    console.log('Test 2: Verifying updateApplicantProfile request serialization...');
    setupMockFetch(() => new Response(JSON.stringify(updatedProfile), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));

    const updatePayload: BackendApplicantProfileUpdate = {
      gig_work_type: 'Ride Hailing',
      years_working: 3.5,
      average_working_days: 26,
      business_or_loan_purpose: 'Commercial Vehicle Maintenance',
    };

    const res = await client.updateApplicantProfile(mockProfileId, updatePayload);

    assert.strictEqual(interceptedCalls.length, 1);
    assert.strictEqual(interceptedCalls[0].method, 'PATCH');
    assert.strictEqual(
      interceptedCalls[0].url,
      `http://localhost:8000/api/v1/applicants/${mockProfileId}`
    );
    const parsedBody = JSON.parse(interceptedCalls[0].body || '{}');
    assert.strictEqual(parsedBody.gig_work_type, 'Ride Hailing');
    assert.strictEqual(parsedBody.years_working, 3.5);
    assert.strictEqual(parsedBody.average_working_days, 26);
    assert.strictEqual(parsedBody.business_or_loan_purpose, 'Commercial Vehicle Maintenance');
    assert.strictEqual(res.gig_work_type, 'Ride Hailing');
    assert.strictEqual(res.years_working, 3.5);
    console.log('✓ updateApplicantProfile correctly sends PATCH with serialized JSON.\n');

    // -----------------------------------------------------------------------
    // Test 3: Partial PATCH update
    // -----------------------------------------------------------------------
    console.log('Test 3: Verifying partial update payload serialization...');
    const partialUpdated: BackendApplicantProfile = {
      ...initialProfile,
      years_working: 4.0,
      updated_at: '2026-09-27T01:05:00Z',
    };
    setupMockFetch(() => new Response(JSON.stringify(partialUpdated), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));

    const partialRes = await client.updateApplicantProfile(mockProfileId, { years_working: 4.0 });
    assert.strictEqual(interceptedCalls.length, 1);
    const partialBody = JSON.parse(interceptedCalls[0].body || '{}');
    assert.strictEqual(partialBody.years_working, 4.0);
    assert.strictEqual(partialBody.gig_work_type, undefined);
    assert.strictEqual(partialRes.years_working, 4.0);
    console.log('✓ Partial PATCH serializes only provided fields without injecting defaults.\n');

    // -----------------------------------------------------------------------
    // Test 4: GET getApplicantProfile by Profile ID
    // -----------------------------------------------------------------------
    console.log('Test 4: Verifying getApplicantProfile routing...');
    setupMockFetch(() => new Response(JSON.stringify(initialProfile), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));

    const getRes = await client.getApplicantProfile(mockProfileId);
    assert.strictEqual(interceptedCalls.length, 1);
    assert.strictEqual(interceptedCalls[0].method, 'GET');
    assert.strictEqual(
      interceptedCalls[0].url,
      `http://localhost:8000/api/v1/applicants/${mockProfileId}`
    );
    assert.strictEqual(getRes.id, mockProfileId);
    console.log('✓ getApplicantProfile correctly calls GET /api/v1/applicants/{id}.\n');

    // -----------------------------------------------------------------------
    // Test 5: GET getApplicantByUserId
    // -----------------------------------------------------------------------
    console.log('Test 5: Verifying getApplicantByUserId routing...');
    setupMockFetch(() => new Response(JSON.stringify(initialProfile), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));

    const getByUserRes = await client.getApplicantByUserId(mockUserId);
    assert.strictEqual(interceptedCalls.length, 1);
    assert.strictEqual(interceptedCalls[0].method, 'GET');
    assert.strictEqual(
      interceptedCalls[0].url,
      `http://localhost:8000/api/v1/applicants/user/${mockUserId}`
    );
    assert.strictEqual(getByUserRes.user_id, mockUserId);
    console.log('✓ getApplicantByUserId correctly calls GET /api/v1/applicants/user/{userId}.\n');

    // -----------------------------------------------------------------------
    // Test 6: HTTP 403 Forbidden Error Propagation (Cross-applicant isolation)
    // -----------------------------------------------------------------------
    console.log('Test 6: Verifying HTTP 403 Forbidden error propagation...');
    setupMockFetch(() => new Response(JSON.stringify({
      detail: "Access denied: cannot modify another applicant's profile."
    }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    }));

    try {
      await client.updateApplicantProfile('other-profile-id', { gig_work_type: 'Tampered' });
      assert.fail('Should have thrown ApiError on HTTP 403');
    } catch (err: unknown) {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 403);
      assert(err.userMessage.includes('Access denied') || err.message.includes('403'));
      console.log('✓ HTTP 403 ownership error cleanly propagated to client.\n');
    }

    // -----------------------------------------------------------------------
    // Test 7: HTTP 401 Unauthorized Error Propagation
    // -----------------------------------------------------------------------
    console.log('Test 7: Verifying HTTP 401 Unauthorized error propagation...');
    setupMockFetch(() => new Response(JSON.stringify({
      detail: 'Not authenticated'
    }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    }));

    try {
      await client.updateApplicantProfile(mockProfileId, { gig_work_type: 'Ride Hailing' });
      assert.fail('Should have thrown ApiError on HTTP 401');
    } catch (err: unknown) {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 401);
      console.log('✓ HTTP 401 unauthenticated error correctly propagated.\n');
    }

    // -----------------------------------------------------------------------
    // Test 8: HTTP 404 Not Found Error Propagation
    // -----------------------------------------------------------------------
    console.log('Test 8: Verifying HTTP 404 Not Found error propagation...');
    setupMockFetch(() => new Response(JSON.stringify({
      detail: "ApplicantProfile with id 'nonexistent' not found."
    }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    }));

    try {
      await client.updateApplicantProfile('nonexistent', { years_working: 3.0 });
      assert.fail('Should have thrown ApiError on HTTP 404');
    } catch (err: unknown) {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 404);
      console.log('✓ HTTP 404 not found error correctly propagated.\n');
    }

    // -----------------------------------------------------------------------
    // Test 9: HTTP 422 Validation Error Propagation
    // -----------------------------------------------------------------------
    console.log('Test 9: Verifying HTTP 422 Validation error propagation...');
    setupMockFetch(() => new Response(JSON.stringify({
      detail: [{ loc: ['body', 'years_working'], msg: 'Input should be less than or equal to 50' }]
    }), {
      status: 422,
      headers: { 'Content-Type': 'application/json' },
    }));

    try {
      await client.updateApplicantProfile(mockProfileId, { years_working: 99.0 });
      assert.fail('Should have thrown ApiError on HTTP 422');
    } catch (err: unknown) {
      assert(err instanceof ApiError);
      assert.strictEqual(err.status, 422);
      console.log('✓ HTTP 422 validation error correctly propagated.\n');
    }

    console.log('=============================================================');
    console.log('ALL PHASE 14E FRONTEND TESTS PASSED! ✓');
    console.log('=============================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase14EFrontendTests().catch((err) => {
  console.error('Phase 14E frontend verification test failed:', err);
  process.exit(1);
});
