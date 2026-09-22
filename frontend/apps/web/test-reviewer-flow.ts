// Integration test suite for Phase 7: Complete Reviewer Portal Flow
import assert from 'node:assert';
import {
  api,
  ApiError,
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  reverseAdaptReviewAction,
  type BackendApplication,
  type BackendApplicantProfile,
  type BackendCreditAssessmentResponse,
  type BackendFinancialSignal,
  type BackendUnderwriterReview,
  type BackendModelVersion,
} from '@parakh/api';

async function runReviewerIntegrationTests() {
  console.log('\n==================================================');
  console.log('RUNNING PARAKH REVIEWER PORTAL INTEGRATION TESTS');
  console.log('==================================================\n');

  const originalFetch = globalThis.fetch;

  // In-memory persistent database simulator for reviewer test suite
  const db = {
    users: [
      {
        id: 'usr-reviewer-202',
        email: 'priya.sharma@parakh.local',
        role: 'REVIEWER',
        is_active: true,
      },
      {
        id: 'usr-applicant-101',
        email: 'arjun.verma@example.com',
        role: 'APPLICANT',
        is_active: true,
      },
    ],
    profiles: [
      {
        id: 'prof-applicant-101',
        user_id: 'usr-applicant-101',
        full_name: 'Arjun Verma',
        phone_number: '+91 98765 43210',
        work_type: 'GIG_WORKER',
        created_at: new Date(Date.now() - 86400000).toISOString(),
        updated_at: new Date(Date.now() - 86400000).toISOString(),
      },
    ] as BackendApplicantProfile[],
    applications: [
      {
        id: 'app-review-001',
        applicant_profile_id: 'prof-applicant-101',
        requested_loan_amount: 50000,
        loan_purpose: 'Delivery Vehicle Fleet Expansion',
        preferred_repayment_period: 6,
        status: 'MANUAL_REVIEW',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        updated_at: new Date(Date.now() - 3600000).toISOString(),
      },
    ] as BackendApplication[],
    assessments: [
      {
        id: 'asmt-eval-001',
        application_id: 'app-review-001',
        score: 720,
        risk_level: 'MODERATE',
        approval_recommendation: true,
        recommended_limit: 45000,
        created_at: new Date(Date.now() - 1800000).toISOString(),
      },
    ] as unknown as BackendCreditAssessmentResponse[],
    signals: [
      {
        id: 'sig-001',
        application_id: 'app-review-001',
        source: 'GIG_PLATFORM',
        average_income: 1850,
        payment_regularity: 0.94,
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
    ] as BackendFinancialSignal[],
    reviews: [] as BackendUnderwriterReview[],
    modelVersions: [
      {
        id: 'mv-001',
        model_name: 'PARAKH-MockEngine-v1.0',
        version: '1.0.0',
        algorithm: 'Rule-Based + Stochastic Volatility Calibration',
        description: 'Baseline production scoring engine',
        is_active: true,
        created_at: new Date(Date.now() - 604800000).toISOString(),
      },
      {
        id: 'mv-002',
        model_name: 'PARAKH-LightGBM-Experimental',
        version: '2.0.0-rc1',
        algorithm: 'Gradient Boosted Volatility Trees',
        description: 'Candidate retrain under Person 2/3 calibration',
        is_active: false,
        created_at: new Date(Date.now() - 86400000).toISOString(),
      },
    ] as BackendModelVersion[],
  };

  try {
    // Mock fetch implementing the exact FastAPI routing contract
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = String(input);
      const method = init?.method || 'GET';
      const headers = (init?.headers as Record<string, string>) || {};
      const token = headers['Authorization']?.replace('Bearer ', '');

      const currentUser = token === 'token-reviewer-priya'
        ? db.users[0]
        : token === 'token-applicant-arjun'
        ? db.users[1]
        : null;

      // 1. POST /api/v1/auth/login
      if (url.endsWith('/api/v1/auth/login') && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        if (body.email === 'priya.sharma@parakh.local' && body.password === 'PriyaReviewer#2026') {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              access_token: 'token-reviewer-priya',
              token_type: 'bearer',
              role: 'REVIEWER',
              user_id: 'usr-reviewer-202',
            }),
          } as Response;
        } else if (body.email === 'arjun.verma@example.com') {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              access_token: 'token-applicant-arjun',
              token_type: 'bearer',
              role: 'APPLICANT',
              user_id: 'usr-applicant-101',
            }),
          } as Response;
        }
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Invalid credentials' }),
        } as Response;
      }

      // Check authentication for protected routes
      if (!currentUser) {
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Not authenticated or invalid token' }),
        } as Response;
      }

      // 2. GET /api/v1/applications (List all applications - REVIEWER/ADMIN ONLY)
      if (url.includes('/api/v1/applications') && !url.includes('/status') && !url.includes('/applicant/') && method === 'GET') {
        const parsedUrl = new URL(url, 'http://localhost');
        const pathname = parsedUrl.pathname;

        // Exact /api/v1/applications
        if (pathname === '/api/v1/applications') {
          if (currentUser.role !== 'REVIEWER' && currentUser.role !== 'ADMIN') {
            return {
              ok: false,
              status: 403,
              json: async () => ({ detail: 'Access denied: only reviewers and administrators can list all applications.' }),
            } as Response;
          }
          return {
            ok: true,
            status: 200,
            json: async () => db.applications,
          } as Response;
        }

        // /api/v1/applications/{application_id}/reviews
        if (pathname.endsWith('/reviews')) {
          const appId = pathname.split('/')[4];
          const matched = db.reviews.filter(r => r.application_id === appId);
          return {
            ok: true,
            status: 200,
            json: async () => matched,
          } as Response;
        }

        // /api/v1/applications/{application_id}/assessments/latest
        if (pathname.includes('/assessments/latest')) {
          const appId = pathname.split('/')[4];
          const asmt = db.assessments.find((a) => a.application_id === appId);
          if (asmt) {
            return {
              ok: true,
              status: 200,
              json: async () => asmt,
            } as Response;
          }
          return {
            ok: false,
            status: 404,
            json: async () => ({ detail: 'Assessment not found' }),
          } as Response;
        }

        // /api/v1/applications/{application_id}
        const appId = pathname.split('/').pop();
        const found = db.applications.find(a => a.id === appId);
        if (found) {
          return {
            ok: true,
            status: 200,
            json: async () => found,
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Application not found' }),
        } as Response;
      }

      // 3. POST /api/v1/applications/{application_id}/reviews
      if (url.includes('/api/v1/applications/') && url.endsWith('/reviews') && method === 'POST') {
        if (currentUser.role !== 'REVIEWER' && currentUser.role !== 'ADMIN') {
          return {
            ok: false,
            status: 403,
            json: async () => ({ detail: 'Access denied: only reviewers can record review outcomes.' }),
          } as Response;
        }
        const body = JSON.parse(init?.body as string);
        const appId = url.split('/applications/')[1].split('/reviews')[0];

        const newReview: BackendUnderwriterReview = {
          id: `rev-${Date.now()}`,
          application_id: appId,
          reviewer_id: body.reviewer_id,
          outcome: body.outcome,
          notes: body.notes || null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        db.reviews.push(newReview);

        return {
          ok: true,
          status: 201,
          json: async () => newReview,
        } as Response;
      }

      // 4. GET /api/v1/reviewers/{reviewer_id}/reviews
      if (url.includes('/api/v1/reviewers/') && url.endsWith('/reviews') && method === 'GET') {
        if (currentUser.role === 'APPLICANT') {
          return {
            ok: false,
            status: 403,
            json: async () => ({ detail: 'Access denied: applicants cannot inspect reviewer activity.' }),
          } as Response;
        }
        const reviewerId = url.split('/reviewers/')[1].split('/reviews')[0];
        const reviews = db.reviews.filter(r => r.reviewer_id === reviewerId);
        return {
          ok: true,
          status: 200,
          json: async () => reviews,
        } as Response;
      }

      // 5. PATCH /api/v1/applications/{application_id}/status
      if (url.includes('/api/v1/applications/') && url.includes('/status') && method === 'PATCH') {
        const appId = url.split('/applications/')[1].split('/status')[0];
        const parsedUrl = new URL(url, 'http://localhost');
        const nextStatus = parsedUrl.searchParams.get('status') as any;

        const app = db.applications.find(a => a.id === appId);
        if (!app) {
          return {
            ok: false,
            status: 404,
            json: async () => ({ detail: 'Application not found' }),
          } as Response;
        }

        app.status = nextStatus;
        app.updated_at = new Date().toISOString();
        return {
          ok: true,
          status: 200,
          json: async () => app,
        } as Response;
      }

      // 6. GET /api/v1/applicants/{id}
      if (url.includes('/api/v1/applicants/') && method === 'GET') {
        const profId = url.split('/applicants/')[1];
        const profile = db.profiles.find(p => p.id === profId);
        if (profile) {
          return {
            ok: true,
            status: 200,
            json: async () => profile,
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Profile not found' }),
        } as Response;
      }

      // 7. GET /api/v1/assessments/application/{id}/latest
      if (url.includes('/api/v1/assessments/application/') && url.endsWith('/latest') && method === 'GET') {
        const appId = url.split('/application/')[1].split('/latest')[0];
        const asmt = db.assessments.find(a => a.application_id === appId);
        if (asmt) {
          return {
            ok: true,
            status: 200,
            json: async () => asmt,
          } as Response;
        }
        return {
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Assessment not found' }),
        } as Response;
      }

      // 8. GET /api/v1/model-versions
      if (url.endsWith('/api/v1/model-versions') && method === 'GET') {
        return {
          ok: true,
          status: 200,
          json: async () => db.modelVersions,
        } as Response;
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: `Unhandled route: ${method} ${url}` }),
      } as Response;
    };

    // ==========================================
    // TEST 1: REVIEWER LOGIN & JWT SESSION
    // ==========================================
    console.log('Test 1: Reviewer login via POST /api/v1/auth/login...');
    const loginRes = await api.login({
      email: 'priya.sharma@parakh.local',
      password: 'PriyaReviewer#2026',
    });
    assert.strictEqual(loginRes.role, 'REVIEWER');
    assert.strictEqual(loginRes.access_token, 'token-reviewer-priya');
    assert.strictEqual(api.getToken(), 'token-reviewer-priya');
    console.log('✓ Reviewer logged in with valid JWT token');

    // ==========================================
    // TEST 2: REVIEW QUEUE RETRIEVAL
    // ==========================================
    console.log('\nTest 2: Fetch priority review queue via GET /api/v1/applications...');
    const queueApps = await api.getApplications();
    assert.strictEqual(queueApps.length, 1);
    assert.strictEqual(queueApps[0].id, 'app-review-001');
    assert.strictEqual(queueApps[0].status, 'MANUAL_REVIEW');

    const adaptedQueueApp = adaptApplication(queueApps[0]);
    assert.strictEqual(adaptedQueueApp.status, 'MANUAL_REVIEW_REQUIRED');
    assert.strictEqual(adaptedQueueApp.requestedAmount, 50000);
    console.log('✓ Priority review queue fetched and adapted successfully');

    // ==========================================
    // TEST 3: APPLICATION DOSSIER & PROFILE RETRIEVAL
    // ==========================================
    console.log('\nTest 3: Fetch application dossier details...');
    const dossierApp = await api.getApplicationById('app-review-001');
    assert.strictEqual(dossierApp.id, 'app-review-001');

    const profile = await api.getApplicantProfile(dossierApp.applicant_profile_id);
    assert.strictEqual(profile.full_name, 'Arjun Verma');
    assert.strictEqual(profile.work_type, 'GIG_WORKER');

    const asmt = await api.getLatestAssessmentByApplication('app-review-001');
    assert.strictEqual(asmt.score, 720);
    assert.strictEqual(asmt.risk_level, 'MODERATE');

    const adaptedDossier = adaptApplication(dossierApp, profile, adaptAssessment(asmt));
    assert.strictEqual(adaptedDossier.applicantName, 'Arjun Verma');
    assert.strictEqual(adaptedDossier.assessment?.score, 720);
    console.log('✓ Full application dossier synthesized');

    // ==========================================
    // TEST 4: SUBMIT HUMAN REVIEW DECISION
    // ==========================================
    console.log('\nTest 4: Submit human review outcome via POST /api/v1/applications/{id}/reviews...');
    const reviewPayload = {
      reviewer_id: loginRes.user_id,
      outcome: reverseAdaptReviewAction('RECORD_OUTCOME'),
      notes: 'Reviewed cashflow regularity. Inflow rebound confirmed after monsoon lull.',
    };
    assert.strictEqual(reviewPayload.outcome, 'REVIEWED');

    const createdReview = await api.createReview('app-review-001', reviewPayload);
    assert.strictEqual(createdReview.application_id, 'app-review-001');
    assert.strictEqual(createdReview.reviewer_id, 'usr-reviewer-202');
    assert.strictEqual(createdReview.outcome, 'REVIEWED');
    assert.ok(createdReview.id);
    console.log('✓ Review outcome created and persisted to database');

    // ==========================================
    // TEST 5: PERSISTENCE & REVIEW AUDIT LOG RETRIEVAL
    // ==========================================
    console.log('\nTest 5: Verify review persistence on application and reviewer profile...');
    const appReviews = await api.getReviewsByApplication('app-review-001');
    assert.strictEqual(appReviews.length, 1);
    assert.strictEqual(appReviews[0].id, createdReview.id);

    const adaptedReview = adaptReviewOutcome(appReviews[0]);
    assert.strictEqual(adaptedReview.status, 'OUTCOME_RECORDED');

    const reviewerReviews = await api.getReviewsByReviewer('usr-reviewer-202');
    assert.strictEqual(reviewerReviews.length, 1);
    assert.strictEqual(reviewerReviews[0].id, createdReview.id);
    console.log('✓ Review outcome persisted in database and verifiable across application & reviewer endpoints');

    // ==========================================
    // TEST 6: APPLICATION STATUS LIFECYCLE ADVANCEMENT
    // ==========================================
    console.log('\nTest 6: Advance application status to COMPLETED...');
    const updatedApp = await api.updateApplicationStatus('app-review-001', 'COMPLETED');
    assert.strictEqual(updatedApp.status, 'COMPLETED');
    console.log('✓ Application transitioned to COMPLETED status');

    // ==========================================
    // TEST 7: MODEL GOVERNANCE & LINEAGE RETRIEVAL
    // ==========================================
    console.log('\nTest 7: Fetch model versions via GET /api/v1/model-versions...');
    const modelVersions = await api.getModelVersions();
    assert.strictEqual(modelVersions.length, 2);
    const activeModel = modelVersions.find(m => m.is_active);
    assert.ok(activeModel);
    assert.strictEqual(activeModel.model_name, 'PARAKH-MockEngine-v1.0');
    console.log('✓ Model versions and active production engine retrieved');

    // ==========================================
    // TEST 8: RBAC GUARDS (APPLICANT FORBIDDEN FROM REVIEWER ACTIONS)
    // ==========================================
    console.log('\nTest 8: Verify RBAC security guards (APPLICANT role 403 Forbidden)...');
    // Login as applicant
    await api.login({
      email: 'arjun.verma@example.com',
      password: 'Password123!',
    });
    assert.strictEqual(api.getToken(), 'token-applicant-arjun');

    // Attempt to list all applications
    try {
      await api.getApplications();
      assert.fail('Should have been rejected with 403');
    } catch (err: any) {
      assert.strictEqual(err.status, 403);
      console.log('  ✓ APPLICANT forbidden from listing all applications (403)');
    }

    // Attempt to submit a review
    try {
      await api.createReview('app-review-001', {
        reviewer_id: 'usr-applicant-101',
        outcome: 'REVIEWED',
        notes: 'Illegal review attempt',
      });
      assert.fail('Should have been rejected with 403');
    } catch (err: any) {
      assert.strictEqual(err.status, 403);
      console.log('  ✓ APPLICANT forbidden from submitting reviews (403)');
    }

    // Attempt to inspect reviewer activity
    try {
      await api.getReviewsByReviewer('usr-reviewer-202');
      assert.fail('Should have been rejected with 403');
    } catch (err: any) {
      assert.strictEqual(err.status, 403);
      console.log('  ✓ APPLICANT forbidden from inspecting reviewer audit log (403)');
    }

    console.log('\n==================================================');
    console.log('ALL 8 REVIEWER PORTAL INTEGRATION TESTS PASSED!');
    console.log('==================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runReviewerIntegrationTests().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
