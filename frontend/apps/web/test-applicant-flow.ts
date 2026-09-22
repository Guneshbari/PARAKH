// Integration test suite for Phase 6: Complete Applicant Portal Flow
import assert from 'node:assert';
import {
  api,
  ApiError,
  adaptApplication,
  adaptAssessment,
  adaptBorrowerProfile,
  type BackendApplicantProfile,
  type BackendApplication,
  type BackendConsent,
  type BackendFinancialSignal,
  type BackendCreditAssessmentResponse,
} from '@parakh/api';

async function runApplicantIntegrationTests() {
  console.log('\n==================================================');
  console.log('RUNNING PARAKH APPLICANT PORTAL INTEGRATION TESTS');
  console.log('==================================================\n');

  const originalFetch = globalThis.fetch;

  // In-memory persistent database simulator for integration test
  const db = {
    users: [
      {
        id: 'usr-applicant-101',
        email: 'arjun.verma@example.com',
        role: 'APPLICANT',
        is_active: true,
      },
    ],
    profiles: [] as BackendApplicantProfile[],
    applications: [] as BackendApplication[],
    consents: [] as BackendConsent[],
    signals: [] as BackendFinancialSignal[],
    assessments: [] as BackendCreditAssessmentResponse[],
  };

  try {
    // Mock fetch implementing the exact FastAPI routing contract
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      const method = init?.method || 'GET';
      const headers = (init?.headers as Record<string, string>) || {};
      const token = headers['Authorization']?.replace('Bearer ', '');

      // Check token for protected routes
      if (!url.includes('/auth/login') && (!token || token !== 'mock-jwt-token-arjun')) {
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Not authenticated or token expired' }),
        } as Response;
      }

      // 1. POST /api/v1/auth/login
      if (url.endsWith('/api/v1/auth/login') && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        if (body.email === 'arjun.verma@example.com' && body.password === 'Password123!') {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              access_token: 'mock-jwt-token-arjun',
              token_type: 'bearer',
              expires_in: 86400,
              user_id: 'usr-applicant-101',
              email: 'arjun.verma@example.com',
              role: 'APPLICANT',
            }),
          } as Response;
        }
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid credentials' }),
        } as Response;
      }

      // 2. GET /api/v1/auth/me
      if (url.endsWith('/api/v1/auth/me') && method === 'GET') {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 'usr-applicant-101',
            email: 'arjun.verma@example.com',
            role: 'APPLICANT',
            is_active: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        } as Response;
      }

      // 3. GET /api/v1/applicants/user/{user_id}
      if (url.includes('/api/v1/applicants/user/') && method === 'GET') {
        const userId = url.split('/').pop()?.split('?')[0];
        const profile = db.profiles.find((p) => p.user_id === userId);
        if (!profile) {
          return {
            ok: false,
            status: 404,
            json: async () => ({ detail: `ApplicantProfile for user '${userId}' not found.` }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          json: async () => profile,
        } as Response;
      }

      // 4. POST /api/v1/applicants
      if (url.endsWith('/api/v1/applicants') && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        const newProfile: BackendApplicantProfile = {
          id: `prof-${Date.now()}`,
          user_id: 'usr-applicant-101',
          full_name: body.full_name,
          phone_number: body.phone_number,
          city: body.city,
          work_type: body.work_type,
          experience_months: body.experience_months,
          declared_monthly_income: body.declared_monthly_income,
          preferred_loan_purpose: body.preferred_loan_purpose,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        db.profiles.push(newProfile);
        return {
          ok: true,
          status: 201,
          json: async () => newProfile,
        } as Response;
      }

      // 5. POST /api/v1/applications
      if (url.endsWith('/api/v1/applications') && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        const newApp: BackendApplication = {
          id: `app-${Date.now()}`,
          applicant_profile_id: body.applicant_profile_id,
          requested_loan_amount: body.requested_loan_amount,
          loan_purpose: body.loan_purpose,
          preferred_repayment_period: body.preferred_repayment_period || 12,
          status: 'SUBMITTED',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        db.applications.push(newApp);
        return {
          ok: true,
          status: 201,
          json: async () => newApp,
        } as Response;
      }

      // 6. GET /api/v1/applications/applicant/{profile_id}
      if (url.includes('/api/v1/applications/applicant/') && method === 'GET') {
        const profileId = url.split('/').pop()?.split('?')[0];
        const apps = db.applications.filter((a) => a.applicant_profile_id === profileId);
        return {
          ok: true,
          status: 200,
          json: async () => apps,
        } as Response;
      }

      // 7. GET /api/v1/applications/{application_id}
      const appMatch = url.match(/\/api\/v1\/applications\/([^/?]+)$/);
      if (appMatch && method === 'GET') {
        const appId = appMatch[1];
        const app = db.applications.find((a) => a.id === appId);
        if (!app) {
          return {
            ok: false,
            status: 404,
            json: async () => ({ detail: 'Application not found' }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          json: async () => app,
        } as Response;
      }

      // 8. POST /api/v1/consents
      if (url.endsWith('/api/v1/consents') && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        const consent: BackendConsent = {
          id: `cns-${Date.now()}`,
          application_id: body.application_id,
          applicant_profile_id: body.applicant_profile_id,
          data_source: body.data_source,
          purpose: body.purpose,
          granted: true,
          granted_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        db.consents.push(consent);
        return {
          ok: true,
          status: 201,
          json: async () => consent,
        } as Response;
      }

      // 9. GET /api/v1/applications/{id}/consents/active
      const activeConsentsMatch = url.match(/\/api\/v1\/applications\/([^/]+)\/consents\/active/);
      if (activeConsentsMatch && method === 'GET') {
        const appId = activeConsentsMatch[1];
        const active = db.consents.filter((c) => c.application_id === appId && !c.revoked_at);
        return {
          ok: true,
          status: 200,
          json: async () => active,
        } as Response;
      }

      // 10. POST /api/v1/consents/{id}/revoke
      const revokeMatch = url.match(/\/api\/v1\/consents\/([^/]+)\/revoke/);
      if (revokeMatch && method === 'POST') {
        const consentId = revokeMatch[1];
        const consent = db.consents.find((c) => c.id === consentId);
        if (consent) {
          consent.revoked_at = new Date().toISOString();
        }
        return {
          ok: true,
          status: 200,
          json: async () => consent,
        } as Response;
      }

      // 11. POST /api/v1/applications/{id}/financial-signals
      const signalMatch = url.match(/\/api\/v1\/applications\/([^/]+)\/financial-signals/);
      if (signalMatch && method === 'POST') {
        const appId = signalMatch[1];
        const body = JSON.parse(init?.body as string);
        const sig: BackendFinancialSignal = {
          id: `sig-${Date.now()}`,
          application_id: appId,
          source: body.source,
          average_income: body.average_income,
          income_volatility: body.income_volatility,
          active_days: body.active_days,
          created_at: new Date().toISOString(),
        };
        db.signals.push(sig);
        return {
          ok: true,
          status: 201,
          json: async () => sig,
        } as Response;
      }

      // 12. GET /api/v1/applications/{id}/financial-signals
      if (signalMatch && method === 'GET') {
        const appId = signalMatch[1];
        const sigs = db.signals.filter((s) => s.application_id === appId);
        return {
          ok: true,
          status: 200,
          json: async () => sigs,
        } as Response;
      }

      // 13. POST /api/v1/applications/{id}/assess
      const assessMatch = url.match(/\/api\/v1\/applications\/([^/?]+)\/assess/);
      if (assessMatch && method === 'POST') {
        const appId = assessMatch[1];
        const app = db.applications.find((a) => a.id === appId);
        if (app) {
          app.status = 'ASSESSED';
        }
        const asmt: BackendCreditAssessmentResponse = {
          id: `asmt-${Date.now()}`,
          application_id: appId,
          model_version_id: 'mv-v1-mock',
          credit_score: 742,
          score: 742,
          risk_level: 'LOWER',
          confidence: 0.88,
          risk_probability: 0.14,
          income_stability: 0.86,
          repayment_reliability: 0.98,
          debt_to_income: 0.22,
          key_factors: [
            'Consistent weekly cashflow rhythm',
            'Strong 10-day recovery velocity',
            'Low existing obligation load',
          ],
          explanation: {
            shap_values: [
              { feature: 'cashflow_recovery', displayName: 'Recovery Velocity', value: 0.32, explanation: 'High rebound velocity' },
            ],
            recommendations: ['Maintain current active gig schedule'],
          },
          assessed_at: new Date().toISOString(),
          created_at: new Date().toISOString(),
        };
        db.assessments.push(asmt);
        return {
          ok: true,
          status: 201,
          json: async () => asmt,
        } as Response;
      }

      // 14. GET /api/v1/applications/{id}/assessments/latest
      const latestAssessMatch = url.match(/\/api\/v1\/applications\/([^/]+)\/assessments\/latest/);
      if (latestAssessMatch && method === 'GET') {
        const appId = latestAssessMatch[1];
        const asmt = db.assessments.filter((a) => a.application_id === appId).pop();
        if (!asmt) {
          return {
            ok: false,
            status: 404,
            json: async () => ({ detail: 'Assessment not found' }),
          } as Response;
        }
        return {
          ok: true,
          status: 200,
          json: async () => asmt,
        } as Response;
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Route not found' }),
      } as Response;
    };

    // =========================================================================
    // EXECUTE END-TO-END APPLICANT JOURNEY
    // =========================================================================

    // Test 1: Applicant Login
    console.log('Test 1: POST /api/v1/auth/login');
    const tokenResp = await api.login({
      email: 'arjun.verma@example.com',
      password: 'Password123!',
    });
    assert.strictEqual(tokenResp.access_token, 'mock-jwt-token-arjun');
    assert.strictEqual(api.getToken(), 'mock-jwt-token-arjun');
    console.log('  ✓ Login successful, JWT stored in client');

    // Test 2: Verify authenticated identity
    console.log('Test 2: GET /api/v1/auth/me');
    const me = await api.getMe();
    assert.strictEqual(me.id, 'usr-applicant-101');
    assert.strictEqual(me.role, 'APPLICANT');
    console.log('  ✓ Authenticated user identity confirmed');

    // Test 3: Load / Create Applicant Profile
    console.log('Test 3: Profile lifecycle (GET -> 404 -> POST /api/v1/applicants)');
    let profile: BackendApplicantProfile | null = null;
    try {
      profile = await api.getApplicantByUserId(me.id);
    } catch (e) {
      assert.strictEqual((e as ApiError).status, 404);
    }
    assert.strictEqual(profile, null);

    const createdProf = await api.createApplicant({
      full_name: 'Arjun Verma',
      phone_number: '9845128910',
      city: 'Bengaluru',
      work_type: 'GIG_WORKER',
      experience_months: 18,
      declared_monthly_income: 52000,
      preferred_loan_purpose: 'Two-Wheeler EV Battery Upgrade & Gear',
    });
    assert.strictEqual(createdProf.full_name, 'Arjun Verma');
    assert.strictEqual(createdProf.city, 'Bengaluru');

    const fetchedProf = await api.getApplicantByUserId(me.id);
    assert.strictEqual(fetchedProf.id, createdProf.id);
    console.log('  ✓ Applicant Profile created and retrievable by user ID');

    // Test 4: Submit New Credit Application
    console.log('Test 4: POST /api/v1/applications');
    const createdApp = await api.createApplication({
      applicant_profile_id: fetchedProf.id,
      requested_loan_amount: 35000,
      loan_purpose: 'Two-Wheeler EV Battery Upgrade & Gear',
      preferred_repayment_period: 12,
    });
    assert.strictEqual(createdApp.requested_loan_amount, 35000);
    assert.strictEqual(createdApp.status, 'SUBMITTED');
    console.log('  ✓ Credit Application created with UUID:', createdApp.id);

    // Test 5: Register Consent
    console.log('Test 5: POST /api/v1/consents');
    const consent = await api.createConsent({
      application_id: createdApp.id,
      applicant_profile_id: fetchedProf.id,
      data_source: 'PLATFORM',
      purpose: 'Alternative credit assessment and risk evaluation under DPDP Act 2023',
      granted: true,
    });
    assert.strictEqual(consent.data_source, 'PLATFORM');
    assert.strictEqual(consent.granted, true);
    console.log('  ✓ Statutory DPDP consent registered');

    // Test 6: Ingest Financial Telemetry Signals
    console.log('Test 6: POST /api/v1/applications/{id}/financial-signals');
    const sig = await api.recordFinancialSignals(createdApp.id, {
      source: 'PLATFORM',
      average_income: 52000,
      income_volatility: 0.18,
      active_days: 24,
    });
    assert.strictEqual(sig.source, 'PLATFORM');
    assert.strictEqual(sig.average_income, 52000);
    console.log('  ✓ Financial telemetry ingested under data minimization');

    // Test 7: Trigger Assessment Evaluation
    console.log('Test 7: POST /api/v1/applications/{id}/assess');
    const rawAsmt = await api.triggerAssessment(createdApp.id);
    assert.strictEqual(rawAsmt.score, 742);
    assert.strictEqual(rawAsmt.risk_level, 'LOWER');
    console.log('  ✓ Assessment triggered and persisted');

    // Test 8: Retrieve Latest Assessment & Adapter Mapping
    console.log('Test 8: GET /api/v1/applications/{id}/assessments/latest & adaptAssessment');
    const latestRaw = await api.getLatestAssessmentByApplication(createdApp.id);
    const adaptedAsmt = adaptAssessment(latestRaw, fetchedProf.full_name || undefined);
    assert.strictEqual(adaptedAsmt.score, 742);
    assert.strictEqual(adaptedAsmt.riskLevel, 'LOWER_ESTIMATED RISK');
    assert.strictEqual(adaptedAsmt.keyPositiveFactors.length, 3);
    assert.strictEqual(adaptedAsmt.featureContributions.length, 1);
    console.log('  ✓ Assessment dossier accurately mapped to frontend domain model');

    // Test 9: Browser Refresh Simulation (Fetch assessment directly from URL params)
    console.log('Test 9: Browser Refresh Simulation (/user/results/[id])');
    const refreshAsmt = await api.getLatestAssessmentByApplication(createdApp.id);
    assert.strictEqual(refreshAsmt.id, rawAsmt.id);
    assert.strictEqual(refreshAsmt.score, rawAsmt.score);
    console.log('  ✓ Refresh persistence verified: identical dossier returned independently of React state');

    // Test 10: Query Applications List
    console.log('Test 10: GET /api/v1/applications/applicant/{profile_id} & adaptApplication');
    const appList = await api.getApplicationsByApplicant(fetchedProf.id);
    assert.strictEqual(appList.length, 1);
    const adaptedApp = adaptApplication(appList[0], fetchedProf, adaptedAsmt);
    assert.strictEqual(adaptedApp.id, createdApp.id);
    assert.strictEqual(adaptedApp.applicantName, 'Arjun Verma');
    assert.strictEqual(adaptedApp.requestedAmount, 35000);
    assert.strictEqual(adaptedApp.status, 'ASSESSMENT_COMPLETED');
    console.log('  ✓ Applications list retrieved and adapted');

    // Test 11: Query Application Detail
    console.log('Test 11: GET /api/v1/applications/{application_id}');
    const appDetail = await api.getApplicationById(createdApp.id);
    assert.strictEqual(appDetail.id, createdApp.id);
    console.log('  ✓ Application detail query verified');

    // Test 12: Revoke Consent
    console.log('Test 12: POST /api/v1/consents/{id}/revoke');
    await api.revokeConsent(consent.id);
    const activeConsents = await api.getActiveConsentsByApplication(createdApp.id);
    assert.strictEqual(activeConsents.length, 0);
    console.log('  ✓ Consent revocation verified');

    // Test 13: Unauthorized Request Blocking
    console.log('Test 13: Unauthorized request without valid JWT');
    api.clearToken();
    try {
      await api.getMe();
      assert.fail('Expected request to throw 401');
    } catch (e) {
      assert.strictEqual((e as ApiError).status, 401);
      assert.strictEqual((e as ApiError).isUnauthorized(), true);
    }
    console.log('  ✓ Unauthorized access blocked with HTTP 401');

    console.log('\n==================================================');
    console.log('ALL 13 APPLICANT INTEGRATION TESTS PASSED!');
    console.log('==================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runApplicantIntegrationTests().catch((err) => {
  console.error('Integration tests failed:', err);
  process.exit(1);
});
