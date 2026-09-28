import assert from 'node:assert';
import { ParakhApiClient, api } from './index';

console.log('=============================================================');
console.log('BATCH C: P2-08 API CLIENT CLEANUP VERIFICATION TEST SUITE');
console.log('=============================================================');

const client = new ParakhApiClient();

// 1. Verify removed/redundant methods remain NO LONGER EXPOSED
// Note: getAssessmentsByApplication was deliberately restored in Batch D (P2-11)
// for historical assessment auditing in the reviewer/admin application dossier.
// Note: updateApplication was deliberately restored in Final P3 (P3-06)
// for application term editing on PATCH /api/v1/applications/{application_id}.
const removedMethods = [
  'getUserById',
  'getUserByEmail',
  'updateUser',
  'getLatestFinancialSignals',
  'getConsentsByApplication',
  'createModelVersion',
  'getActiveModelVersion',
  'getModelVersionById',
  'getAuditLogById',
  'getApplicationAdapted',
  'getApplicationsAdapted',
  'getLatestAssessmentAdapted',
  'getAssessmentAdapted',
  'recordReviewOutcomeAdapted',
  'getBorrowerProfileAdapted',
] as const;

console.log('\nTest 1: Verifying removed/redundant methods are not exposed on prototype or instance...');
for (const method of removedMethods) {
  assert.strictEqual(
    (client as unknown as Record<string, unknown>)[method],
    undefined,
    `Method ${method} should not exist on ParakhApiClient instance`
  );
  assert.strictEqual(
    (ParakhApiClient.prototype as unknown as Record<string, unknown>)[method],
    undefined,
    `Method ${method} should not exist on ParakhApiClient.prototype`
  );
  assert.strictEqual(
    (api as unknown as Record<string, unknown>)[method],
    undefined,
    `Method ${method} should not exist on api singleton`
  );
}
console.log(`✓ All ${removedMethods.length} candidate methods are confirmed removed.`);

// 2. Verify all actively consumed and supported methods remain EXPOSED as functions
const retainedMethods = [
  // Auth
  'login',
  'register',
  'getMe',
  // Applicant Profiles (including Phase 14E updateApplicantProfile)
  'createApplicant',
  'getApplicantProfile',
  'getApplicantByUserId',
  'updateApplicantProfile',
  // Applications (including restored P3-06 updateApplication)
  'getApplications',
  'createApplication',
  'getApplicationById',
  'getApplicationsByApplicant',
  'updateApplicationStatus',
  'updateApplication',
  // Assessments (including restored P2-11 getAssessmentsByApplication)
  'triggerAssessment',
  'getAssessmentById',
  'getLatestAssessmentByApplication',
  'getAssessmentsByApplication',
  // Financial Signals
  'recordFinancialSignals',
  'getFinancialSignals',
  // Consents & Preferences (including Phase 14D)
  'createConsent',
  'getActiveConsentsByApplication',
  'revokeConsent',
  'getConsentPreferences',
  'updateConsentPreferences',
  'revokeConsentPreference',
  // Reviews
  'createReview',
  'getReviewsByApplication',
  'getReviewsByReviewer',
  // Model Governance (including Phase 14F and P2-10 getGlobalSHAP)
  'getModelVersions',
  'activateModelVersion',
  'runFairnessAudit',
  'getGlobalSHAP',
  // Audit Logs (including Phase 14B)
  'getAuditLogs',
  'getAuditLogsAdapted',
  // Portfolio Analytics (including Phase 14C date filters)
  'getPortfolioAnalytics',
  'getPortfolioAnalyticsAdapted',
  'getSectorRisk',
  'getSectorRiskAdapted',
  // Supported test contract adapter
  'triggerAssessmentAdapted',
  // Operational Alerts (Phase 14A)
  'getOperationalAlerts',
  'getOperationalAlert',
  'acknowledgeOperationalAlert',
  'resolveOperationalAlert',
] as const;

console.log('\nTest 2: Verifying retained methods remain callable functions...');
for (const method of retainedMethods) {
  assert.strictEqual(
    typeof (client as unknown as Record<string, unknown>)[method],
    'function',
    `Retained method ${method} must be a function on ParakhApiClient instance`
  );
  assert.strictEqual(
    typeof (api as unknown as Record<string, unknown>)[method],
    'function',
    `Retained method ${method} must be a function on api singleton`
  );
}
console.log(`✓ All ${retainedMethods.length} retained methods are confirmed intact and callable.`);

console.log('\n=============================================================');
console.log('ALL BATCH C P2-08 FRONTEND API CLIENT TESTS PASSED! ✓');
console.log('=============================================================');
