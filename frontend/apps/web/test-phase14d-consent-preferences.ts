/**
 * Phase 14D: Frontend DPDP Consent Preferences Verification Test Suite (P2-04)
 *
 * Verifies end-to-end frontend API client contract, endpoint routing,
 * request payload serialization, response types, and error propagation.
 */

import assert from 'assert';
import { ParakhApiClient, ApiError, type BackendConsentPreferences } from '@parakh/api';

async function runPhase14DFrontendTests() {
  console.log('=============================================================');
  console.log('Phase 14D: DPDP Consent Preferences Frontend Contract Test');
  console.log('=============================================================\n');

  const client = new ParakhApiClient({ baseUrl: 'http://localhost:8000' });

  // -------------------------------------------------------------------------
  // Test 1: Method Exposure on ApiClient
  // -------------------------------------------------------------------------
  console.log('Test 1: Verifying consent preference methods exposed on ApiClient...');
  assert.strictEqual(typeof client.getConsentPreferences, 'function');
  assert.strictEqual(typeof client.updateConsentPreferences, 'function');
  assert.strictEqual(typeof client.revokeConsentPreference, 'function');
  console.log('✓ getConsentPreferences, updateConsentPreferences, and revokeConsentPreference exposed.\n');

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

  const mockDefaultPreferences: BackendConsentPreferences = {
    user_id: '00000000-0000-0000-0000-000000000001',
    consent_benchmark: false,
    consent_realtime: false,
    consent_alerts: false,
    preferences: [
      { key: 'consent_benchmark', granted: false, consented_at: null, revoked_at: null, updated_at: null },
      { key: 'consent_realtime', granted: false, consented_at: null, revoked_at: null, updated_at: null },
      { key: 'consent_alerts', granted: false, consented_at: null, revoked_at: null, updated_at: null },
    ],
    updated_at: null,
  };

  const mockUpdatedPreferences: BackendConsentPreferences = {
    user_id: '00000000-0000-0000-0000-000000000001',
    consent_benchmark: true,
    consent_realtime: true,
    consent_alerts: false,
    preferences: [
      { key: 'consent_benchmark', granted: true, consented_at: '2026-09-27T00:00:00Z', revoked_at: null, updated_at: '2026-09-27T00:00:00Z' },
      { key: 'consent_realtime', granted: true, consented_at: '2026-09-27T00:00:00Z', revoked_at: null, updated_at: '2026-09-27T00:00:00Z' },
      { key: 'consent_alerts', granted: false, consented_at: null, revoked_at: null, updated_at: null },
    ],
    updated_at: '2026-09-27T00:00:00Z',
  };

  const mockRevokedPreferences: BackendConsentPreferences = {
    user_id: '00000000-0000-0000-0000-000000000001',
    consent_benchmark: false,
    consent_realtime: true,
    consent_alerts: false,
    preferences: [
      { key: 'consent_benchmark', granted: false, consented_at: '2026-09-27T00:00:00Z', revoked_at: '2026-09-27T00:05:00Z', updated_at: '2026-09-27T00:05:00Z' },
      { key: 'consent_realtime', granted: true, consented_at: '2026-09-27T00:00:00Z', revoked_at: null, updated_at: '2026-09-27T00:00:00Z' },
      { key: 'consent_alerts', granted: false, consented_at: null, revoked_at: null, updated_at: null },
    ],
    updated_at: '2026-09-27T00:05:00Z',
  };

  try {
    // -------------------------------------------------------------------------
    // Test 2: GET /api/v1/consents/preferences Request Serialization
    // -------------------------------------------------------------------------
    console.log('Test 2: Verifying getConsentPreferences request serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockDefaultPreferences), { status: 200 }));
    const fetched = await client.getConsentPreferences();

    assert.strictEqual(interceptedCalls.length, 1);
    assert.ok(interceptedCalls[0].url.endsWith('/api/v1/consents/preferences'));
    assert.strictEqual(interceptedCalls[0].method, 'GET');
    assert.strictEqual(fetched.consent_benchmark, false);
    assert.strictEqual(fetched.consent_realtime, false);
    assert.strictEqual(fetched.consent_alerts, false);
    console.log('✓ getConsentPreferences correctly calls GET /api/v1/consents/preferences.\n');

    // -------------------------------------------------------------------------
    // Test 3: GET with userId Query Parameter
    // -------------------------------------------------------------------------
    console.log('Test 3: Verifying getConsentPreferences with target userId override...');
    setupMockFetch(() => new Response(JSON.stringify(mockDefaultPreferences), { status: 200 }));
    await client.getConsentPreferences('target-user-uuid');

    assert.strictEqual(interceptedCalls.length, 1);
    assert.ok(interceptedCalls[0].url.includes('/api/v1/consents/preferences?user_id=target-user-uuid'));
    console.log('✓ getConsentPreferences appends ?user_id= when provided.\n');

    // -------------------------------------------------------------------------
    // Test 4: PATCH /api/v1/consents/preferences Request Serialization
    // -------------------------------------------------------------------------
    console.log('Test 4: Verifying updateConsentPreferences payload serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockUpdatedPreferences), { status: 200 }));
    const updateResult = await client.updateConsentPreferences({
      consent_benchmark: true,
      consent_realtime: true,
    });

    assert.strictEqual(interceptedCalls.length, 1);
    assert.ok(interceptedCalls[0].url.endsWith('/api/v1/consents/preferences'));
    assert.strictEqual(interceptedCalls[0].method, 'PATCH');
    const parsedBody = JSON.parse(interceptedCalls[0].body!);
    assert.strictEqual(parsedBody.consent_benchmark, true);
    assert.strictEqual(parsedBody.consent_realtime, true);
    assert.strictEqual(updateResult.consent_benchmark, true);
    assert.strictEqual(updateResult.consent_realtime, true);
    console.log('✓ updateConsentPreferences correctly sends PATCH with serialized JSON.\n');

    // -------------------------------------------------------------------------
    // Test 5: POST /api/v1/consents/preferences/{key}/revoke Serialization
    // -------------------------------------------------------------------------
    console.log('Test 5: Verifying revokeConsentPreference serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockRevokedPreferences), { status: 200 }));
    const revokeResult = await client.revokeConsentPreference('consent_benchmark');

    assert.strictEqual(interceptedCalls.length, 1);
    assert.ok(interceptedCalls[0].url.endsWith('/api/v1/consents/preferences/consent_benchmark/revoke'));
    assert.strictEqual(interceptedCalls[0].method, 'POST');
    assert.strictEqual(revokeResult.consent_benchmark, false);
    assert.strictEqual(revokeResult.consent_realtime, true);
    console.log('✓ revokeConsentPreference correctly calls POST /api/v1/consents/preferences/{key}/revoke.\n');

    // -------------------------------------------------------------------------
    // Test 6: API Error Propagation (HTTP 403 Forbidden)
    // -------------------------------------------------------------------------
    console.log('Test 6: Verifying HTTP 403 error handling on ownership violation...');
    setupMockFetch(() => new Response(JSON.stringify({ detail: 'Access denied: cannot modify another applicant preferences.' }), { status: 403 }));

    try {
      await client.updateConsentPreferences({ consent_benchmark: true }, 'other-user');
      assert.fail('Expected ApiError to be thrown for 403');
    } catch (err: any) {
      assert.ok(err instanceof ApiError, 'Must be instance of ApiError');
      assert.strictEqual(err.status, 403);
      assert.ok(err.userMessage.includes('Access denied') || err.message.includes('Access denied'));
    }
    console.log('✓ HTTP 403 ownership error cleanly propagated to consumer.\n');

    // -------------------------------------------------------------------------
    // Test 7: HTTP 401 Unauthenticated Error Handling
    // -------------------------------------------------------------------------
    console.log('Test 7: Verifying HTTP 401 error handling for unauthenticated requests...');
    setupMockFetch(() => new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 }));

    try {
      await client.getConsentPreferences();
      assert.fail('Expected ApiError to be thrown for 401');
    } catch (err: any) {
      assert.ok(err instanceof ApiError);
      assert.strictEqual(err.status, 401);
    }
    console.log('✓ HTTP 401 unauthenticated error correctly propagated.\n');

    console.log('=============================================================');
    console.log('ALL PHASE 14D FRONTEND TESTS PASSED! ✓');
    console.log('=============================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase14DFrontendTests().catch((err) => {
  console.error('Test suite failed:', err);
  process.exit(1);
});
