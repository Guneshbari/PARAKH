// Phase 8: Review + Audit Workflow Integration Test Suite
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
  type BackendUnderwriterReview,
} from '@parakh/api';

async function runPhase8WorkflowTests() {
  console.log('\n=============================================================');
  console.log('PARAKH PHASE 8: REVIEW + AUDIT WORKFLOW VERIFICATION SUITE');
  console.log('=============================================================\n');

  const originalFetch = globalThis.fetch;

  // Persistent mock database representing FastAPI + PostgreSQL state
  const db = {
    users: [
      {
        id: 'usr-reviewer-801',
        email: 'priya.reviewer@parakh.local',
        role: 'REVIEWER',
        is_active: true,
      },
      {
        id: 'usr-applicant-802',
        email: 'applicant.ravi@example.com',
        role: 'APPLICANT',
        is_active: true,
      },
    ],
    profiles: [
      {
        id: 'prof-applicant-802',
        user_id: 'usr-applicant-802',
        full_name: 'Ravi Kumar',
        phone_number: '+91 99887 76655',
        work_type: 'GIG_WORKER',
        created_at: '2026-09-22T08:00:00Z',
        updated_at: '2026-09-22T08:00:00Z',
      },
    ] as BackendApplicantProfile[],
    applications: [
      {
        id: 'app-flow-801',
        applicant_profile_id: 'prof-applicant-802',
        requested_loan_amount: 40000,
        loan_purpose: 'Bike maintenance and insurance',
        preferred_repayment_period: 6,
        status: 'ASSESSED',
        created_at: '2026-09-22T09:00:00Z',
        updated_at: '2026-09-22T09:00:00Z',
      },
    ] as BackendApplication[],
    assessments: [
      {
        id: 'asmt-flow-801',
        application_id: 'app-flow-801',
        model_version_id: 'mv-mock-v1',
        credit_score: 715,
        risk_level: 'LOWER',
        confidence: 0.89,
        created_at: '2026-09-22T09:30:00Z',
      },
    ] as BackendCreditAssessmentResponse[],
    reviews: [] as BackendUnderwriterReview[],
    auditLogs: [] as Array<{
      id: string;
      action: string;
      entity_type: string;
      entity_id: string;
      user_id: string;
      application_id: string;
      metadata: Record<string, any>;
      created_at: string;
    }>,
  };

  let currentUserRole: 'REVIEWER' | 'APPLICANT' | null = null;
  let currentUserId: string | null = null;

  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    const urlStr = url.toString();
    const method = init?.method || 'GET';
    const body = init?.body ? JSON.parse(init.body as string) : {};

    // 1. Auth routes
    if (urlStr.includes('/api/v1/auth/login')) {
      const user = db.users.find((u) => u.email === body.email);
      if (!user) {
        return new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 });
      }
      currentUserRole = user.role as any;
      currentUserId = user.id;
      return new Response(
        JSON.stringify({
          access_token: `token-for-${user.id}`,
          token_type: 'bearer',
          user_id: user.id,
          email: user.email,
          role: user.role,
        }),
        { status: 200 }
      );
    }

    if (urlStr.includes('/api/v1/auth/me')) {
      const user = db.users.find((u) => u.id === currentUserId);
      if (!user) return new Response(JSON.stringify({ detail: 'Unauthorized' }), { status: 401 });
      return new Response(JSON.stringify(user), { status: 200 });
    }

    // 2. Application routes
    if (urlStr.match(/\/api\/v1\/applications\/([^/]+)$/)) {
      const appId = urlStr.split('/api/v1/applications/')[1];
      const app = db.applications.find((a) => a.id === appId);
      if (!app) {
        return new Response(JSON.stringify({ detail: 'Application not found' }), { status: 404 });
      }
      return new Response(JSON.stringify(app), { status: 200 });
    }

    // 3. Latest Assessment
    if (urlStr.match(/\/api\/v1\/applications\/([^/]+)\/assessments\/latest/)) {
      const appId = urlStr.split('/api/v1/applications/')[1].split('/')[0];
      const asmt = db.assessments.find((a) => a.application_id === appId);
      if (!asmt) {
        return new Response(JSON.stringify({ detail: 'Assessment not found' }), { status: 404 });
      }
      return new Response(JSON.stringify(asmt), { status: 200 });
    }

    // 4. Reviews POST & GET
    if (urlStr.match(/\/api\/v1\/applications\/([^/]+)\/reviews/)) {
      const appId = urlStr.split('/api/v1/applications/')[1].split('/')[0];
      if (method === 'POST') {
        // RBAC check: only REVIEWER or ADMIN can submit reviews
        if (currentUserRole !== 'REVIEWER') {
          return new Response(
            JSON.stringify({ detail: 'Forbidden: Insufficient privileges for reviewer action' }),
            { status: 403 }
          );
        }

        const app = db.applications.find((a) => a.id === appId);
        if (!app) {
          return new Response(JSON.stringify({ detail: 'Application not found' }), { status: 404 });
        }

        // Validation: notes length >= 10
        if (body.notes && body.notes.trim().length < 10) {
          return new Response(
            JSON.stringify({ detail: 'Review decision notes must contain at least 10 characters.' }),
            { status: 400 }
          );
        }

        // Atomic Transaction: ReviewOutcome + Application Status Update + AuditLog
        const newReview: BackendUnderwriterReview = {
          id: `rev-${Date.now()}`,
          application_id: appId,
          reviewer_id: currentUserId || 'usr-reviewer-801',
          outcome: body.outcome,
          notes: body.notes,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        db.reviews.push(newReview);

        // Update application status
        let targetStatus: BackendApplication['status'] = app.status;
        if (body.outcome === 'REVIEWED') {
          targetStatus = 'COMPLETED';
        } else if (body.outcome === 'ESCALATED') {
          targetStatus = 'MANUAL_REVIEW';
        } else if (body.outcome === 'ADDITIONAL_INFORMATION_REQUIRED') {
          targetStatus = 'UNDER_REVIEW';
        }
        app.status = targetStatus;
        app.updated_at = new Date().toISOString();

        // Write AuditLog records
        db.auditLogs.push({
          id: `aud-${Date.now()}-1`,
          action: 'APPLICATION_STATUS_CHANGED',
          entity_type: 'Application',
          entity_id: appId,
          user_id: currentUserId!,
          application_id: appId,
          metadata: { new_status: targetStatus, trigger: 'REVIEW_OUTCOME_RECORDED' },
          created_at: new Date().toISOString(),
        });
        db.auditLogs.push({
          id: `aud-${Date.now()}-2`,
          action: 'REVIEW_CREATED',
          entity_type: 'ReviewOutcome',
          entity_id: newReview.id,
          user_id: currentUserId!,
          application_id: appId,
          metadata: { review_outcome: body.outcome },
          created_at: new Date().toISOString(),
        });

        return new Response(JSON.stringify(newReview), { status: 201 });
      }

      if (method === 'GET') {
        const appReviews = db.reviews.filter((r) => r.application_id === appId);
        return new Response(JSON.stringify(appReviews), { status: 200 });
      }
    }

    // 5. Profiles
    if (urlStr.match(/\/api\/v1\/applicant-profiles\/([^/]+)/)) {
      const profId = urlStr.split('/api/v1/applicant-profiles/')[1];
      const prof = db.profiles.find((p) => p.id === profId);
      return new Response(JSON.stringify(prof || {}), { status: 200 });
    }

    return new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 });
  }) as any;

  try {
    // -------------------------------------------------------------
    // STEP 1: REVIEWER LOGIN & APPLICATION INSPECTION
    // -------------------------------------------------------------
    console.log('[Step 1] Reviewer authenticates via POST /api/v1/auth/login');
    const authResult = await api.login({ email: 'priya.reviewer@parakh.local', password: 'ReviewerPass123!' });
    assert.strictEqual(authResult.role, 'REVIEWER');
    assert.ok(authResult.access_token);
    console.log('✓ Reviewer authenticated with JWT role: REVIEWER');

    console.log('\n[Step 2] Reviewer opens application app-flow-801 & views assessment');
    const rawApp = await api.getApplicationById('app-flow-801');
    assert.strictEqual(rawApp.status, 'ASSESSED');
    const rawAssessment = await api.getLatestAssessmentByApplication('app-flow-801');
    assert.strictEqual(rawAssessment.credit_score, 715);
    assert.strictEqual(rawAssessment.risk_level, 'LOWER');
    console.log('✓ Retrieved application dossier in ASSESSED status with credit_score 715');

    // -------------------------------------------------------------
    // STEP 2: REVIEW ACTION SUBMISSION (RECORD_OUTCOME -> REVIEWED)
    // -------------------------------------------------------------
    console.log('\n[Step 3] Reviewer chooses RECORD_OUTCOME and submits review notes');
    const actionOutcome = reverseAdaptReviewAction('RECORD_OUTCOME');
    assert.strictEqual(actionOutcome, 'REVIEWED');

    const createdReview = await api.createReview('app-flow-801', {
      reviewer_id: authResult.user_id,
      outcome: actionOutcome,
      notes: 'Verified continuous gig work history on Swiggy and Zomato. Approved loan facility.',
    });
    assert.strictEqual(createdReview.outcome, 'REVIEWED');
    assert.strictEqual(createdReview.application_id, 'app-flow-801');
    console.log('✓ Review outcome REVIEWED persisted');

    // -------------------------------------------------------------
    // STEP 3: PERSISTENCE & ATOMIC AUDIT VERIFICATION
    // -------------------------------------------------------------
    console.log('\n[Step 4] Verifying atomic persistence in database: ReviewOutcome + ApplicationStatus + AuditLog');
    assert.strictEqual(db.reviews.length, 1);
    assert.strictEqual(db.applications[0].status, 'COMPLETED');
    assert.strictEqual(db.auditLogs.length, 2);

    const statusAudit = db.auditLogs.find((l) => l.action === 'APPLICATION_STATUS_CHANGED');
    assert.ok(statusAudit, 'Audit record for status change must be created');
    assert.strictEqual(statusAudit?.metadata.new_status, 'COMPLETED');
    assert.strictEqual(statusAudit?.user_id, authResult.user_id);

    const reviewAudit = db.auditLogs.find((l) => l.action === 'REVIEW_CREATED');
    assert.ok(reviewAudit, 'Audit record for review creation must be created');
    assert.strictEqual(reviewAudit?.metadata.review_outcome, 'REVIEWED');
    console.log('✓ Application status atomically updated to COMPLETED');
    console.log('✓ APPLICATION_STATUS_CHANGED and REVIEW_CREATED audit logs recorded');

    // -------------------------------------------------------------
    // STEP 4: APPLICANT VISIBILITY & PERSISTED STATUS RETRIEVAL
    // -------------------------------------------------------------
    console.log('\n[Step 5] Applicant logs in and retrieves application via GET /api/v1/applications/app-flow-801');
    const applicantAuth = await api.login({ email: 'applicant.ravi@example.com', password: 'ApplicantPass123!' });
    assert.strictEqual(applicantAuth.role, 'APPLICANT');

    const applicantApp = await api.getApplicationById('app-flow-801');
    assert.strictEqual(applicantApp.status, 'COMPLETED');

    const adaptedForApplicant = adaptApplication(applicantApp);
    assert.strictEqual(adaptedForApplicant.status, 'REVIEW_COMPLETED');
    console.log('✓ Applicant retrieves application with persisted status: COMPLETED (adapted: REVIEW_COMPLETED)');

    // -------------------------------------------------------------
    // STEP 5: SIMULATE BROWSER REFRESH
    // -------------------------------------------------------------
    console.log('\n[Step 6] Simulating browser refresh: reload application from backend API');
    const refreshedApp = await api.getApplicationById('app-flow-801');
    assert.strictEqual(refreshedApp.status, 'COMPLETED', 'Status must not revert to draft or mock');
    console.log('✓ Application retains persisted COMPLETED status across reloads');

    // -------------------------------------------------------------
    // STEP 6: RBAC ENFORCEMENT ON REVIEW ACTIONS
    // -------------------------------------------------------------
    console.log('\n[Step 7] Testing RBAC: Applicant attempt to submit review action');
    let rbacBlocked = false;
    try {
      await api.createReview('app-flow-801', {
        reviewer_id: applicantAuth.user_id,
        outcome: 'REVIEWED',
        notes: 'Unauthorized approval attempt from applicant session.',
      });
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 403) {
        rbacBlocked = true;
      }
    }
    assert.ok(rbacBlocked, 'Applicant role must receive HTTP 403 Forbidden on review creation');
    console.log('✓ Applicant unauthorized review attempt rejected with HTTP 403 Forbidden');

    // -------------------------------------------------------------
    // STEP 7: NOTES LENGTH VALIDATION
    // -------------------------------------------------------------
    console.log('\n[Step 8] Testing Notes validation: rejecting notes < 10 characters');
    // Switch back to reviewer
    await api.login({ email: 'priya.reviewer@parakh.local', password: 'ReviewerPass123!' });
    let validationRejected = false;
    try {
      await api.createReview('app-flow-801', {
        reviewer_id: authResult.user_id,
        outcome: 'REVIEWED',
        notes: 'too short',
      });
    } catch (err: any) {
      if (err instanceof ApiError && (err.status === 400 || err.status === 422)) {
        validationRejected = true;
      }
    }
    assert.ok(validationRejected, 'Short notes (< 10 chars) must be rejected');
    console.log('✓ Review notes < 10 characters successfully rejected by validation');

    // -------------------------------------------------------------
    // STEP 8: ADDITIONAL REVIEW ACTIONS (MANUAL_REVIEW & REQUEST_VERIFICATION)
    // -------------------------------------------------------------
    console.log('\n[Step 9] Testing review actions: MANUAL_REVIEW and REQUEST_VERIFICATION');
    const manualAction = reverseAdaptReviewAction('MANUAL_REVIEW');
    assert.strictEqual(manualAction, 'ESCALATED');

    await api.createReview('app-flow-801', {
      reviewer_id: authResult.user_id,
      outcome: manualAction,
      notes: 'Escalating to committee for unusual gig income variance check.',
    });
    assert.strictEqual(db.applications[0].status, 'MANUAL_REVIEW');
    console.log('✓ Action MANUAL_REVIEW (ESCALATED) successfully set application status to MANUAL_REVIEW');

    const verifyAction = reverseAdaptReviewAction('REQUEST_VERIFICATION');
    assert.strictEqual(verifyAction, 'ADDITIONAL_INFORMATION_REQUIRED');

    await api.createReview('app-flow-801', {
      reviewer_id: authResult.user_id,
      outcome: verifyAction,
      notes: 'Requesting updated platform delivery statements for the past 60 days.',
    });
    assert.strictEqual(db.applications[0].status, 'UNDER_REVIEW');
    console.log('✓ Action REQUEST_VERIFICATION (ADDITIONAL_INFORMATION_REQUIRED) successfully set application status to UNDER_REVIEW');

    console.log('\n=============================================================');
    console.log('ALL PHASE 8 WORKFLOW INTEGRATION TESTS PASSED SUCCESSFULLY! ✓');
    console.log('=============================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase8WorkflowTests().catch((err) => {
  console.error('\n❌ Phase 8 Workflow Test Failure:', err);
  process.exit(1);
});
