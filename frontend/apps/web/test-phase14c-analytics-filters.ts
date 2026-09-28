// Phase 14C: Analytics Date-Range Filtering Verification Suite (P2-03)
import assert from 'node:assert';
import {
  api,
  adaptPortfolioAnalytics,
  type BackendPortfolioAnalytics,
  ApiError,
} from '@parakh/api';

async function runPhase14CAnalyticsFilterTests() {
  console.log('\n=============================================================');
  console.log('PARAKH PHASE 14C: ANALYTICS DATE-RANGE FILTERS TEST SUITE');
  console.log('=============================================================\n');

  const originalFetch = globalThis.fetch;
  let interceptedUrls: string[] = [];

  const mockPortfolioResponse: BackendPortfolioAnalytics = {
    total_applications: 3,
    total_applicants: 2,
    assessed_applications: 2,
    manual_review_applications: 1,
    completed_applications: 0,
    average_credit_score: 650.0,
    average_risk_probability: 0.4000,
    assessment_completion_rate: 100.0,
    total_assessments: 2,
    status_distribution: {
      DRAFT: 0,
      SUBMITTED: 0,
      UNDER_REVIEW: 0,
      ASSESSED: 1,
      MANUAL_REVIEW: 1,
      COMPLETED: 0,
    },
    risk_distribution: {
      LOWER: 0,
      MODERATE: 1,
      HIGHER: 1,
      INSUFFICIENT: 0,
    },
    score_distribution: [
      { range: '600–679', label: 'Elevated Income Volatility', count: 1, percentage: 50.0, risk_tier: 'HIGHER_ESTIMATED RISK' },
      { range: '680–739', label: 'Moderate Cyclical Variance', count: 1, percentage: 50.0, risk_tier: 'MODERATE_ESTIMATED RISK' },
    ],
    monthly_volume: [
      { month: 'May 2026', count: 2, avg_score: 650.0 },
    ],
    sector_risk: [
      { sector: 'Food Delivery', lower_risk: 0, moderate_risk: 1, higher_risk: 0, manual_review: 0, total: 1 },
      { sector: 'Ride Logistics', lower_risk: 0, moderate_risk: 0, higher_risk: 1, manual_review: 0, total: 1 },
    ],
  };

  const mockEmptyPortfolio: BackendPortfolioAnalytics = {
    total_applications: 0,
    total_applicants: 0,
    assessed_applications: 0,
    manual_review_applications: 0,
    completed_applications: 0,
    average_credit_score: null,
    average_risk_probability: null,
    assessment_completion_rate: 0.0,
    total_assessments: 0,
    status_distribution: {
      DRAFT: 0,
      SUBMITTED: 0,
      UNDER_REVIEW: 0,
      ASSESSED: 0,
      MANUAL_REVIEW: 0,
      COMPLETED: 0,
    },
    risk_distribution: {
      LOWER: 0,
      MODERATE: 0,
      HIGHER: 0,
      INSUFFICIENT: 0,
    },
    score_distribution: [],
    monthly_volume: [],
    sector_risk: [],
  };

  function setupMockFetch(responder: (url: string) => Response) {
    interceptedUrls = [];
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      interceptedUrls.push(url);
      return responder(url);
    }) as any;
  }

  try {
    // -------------------------------------------------------------------------
    // Test 1: Unfiltered request serialization
    // -------------------------------------------------------------------------
    console.log('Test 1: Verifying unfiltered request serialization without query parameters...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    const unfilteredData = await api.getPortfolioAnalytics();

    assert.strictEqual(interceptedUrls.length, 1);
    assert.ok(
      interceptedUrls[0].endsWith('/api/v1/analytics/portfolio'),
      `Expected /api/v1/analytics/portfolio without query string, got ${interceptedUrls[0]}`
    );
    assert.strictEqual(unfilteredData.total_applications, 3);
    console.log('✓ Unfiltered request serializes clean endpoint URL without date params.\n');

    // -------------------------------------------------------------------------
    // Test 2: Start-date only serialization
    // -------------------------------------------------------------------------
    console.log('Test 2: Verifying start_date only serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    await api.getPortfolioAnalytics({ start_date: '2026-05-15' });

    assert.strictEqual(interceptedUrls.length, 1);
    assert.ok(
      interceptedUrls[0].includes('start_date=2026-05-15'),
      `URL should contain start_date=2026-05-15, got: ${interceptedUrls[0]}`
    );
    assert.ok(
      !interceptedUrls[0].includes('end_date'),
      `URL should not contain end_date, got: ${interceptedUrls[0]}`
    );
    console.log('✓ start_date parameter correctly serialized using backend contract.\n');

    // -------------------------------------------------------------------------
    // Test 3: End-date only serialization
    // -------------------------------------------------------------------------
    console.log('Test 3: Verifying end_date only serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    await api.getPortfolioAnalytics({ end_date: '2026-05-15' });

    assert.strictEqual(interceptedUrls.length, 1);
    assert.ok(
      interceptedUrls[0].includes('end_date=2026-05-15'),
      `URL should contain end_date=2026-05-15, got: ${interceptedUrls[0]}`
    );
    assert.ok(
      !interceptedUrls[0].includes('start_date'),
      `URL should not contain start_date, got: ${interceptedUrls[0]}`
    );
    console.log('✓ end_date parameter correctly serialized using backend contract.\n');

    // -------------------------------------------------------------------------
    // Test 4: Both start_date and end_date serialization
    // -------------------------------------------------------------------------
    console.log('Test 4: Verifying combined start_date and end_date serialization...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    await api.getPortfolioAnalytics({ start_date: '2026-05-10', end_date: '2026-05-20' });

    assert.strictEqual(interceptedUrls.length, 1);
    assert.ok(
      interceptedUrls[0].includes('start_date=2026-05-10') && interceptedUrls[0].includes('end_date=2026-05-20'),
      `URL should contain both start_date and end_date, got: ${interceptedUrls[0]}`
    );
    console.log('✓ Both date parameters correctly concatenated into query string.\n');

    // -------------------------------------------------------------------------
    // Test 5: getPortfolioAnalyticsAdapted with date filters
    // -------------------------------------------------------------------------
    console.log('Test 5: Verifying getPortfolioAnalyticsAdapted forwards date parameters and adapts response...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    const adapted = await api.getPortfolioAnalyticsAdapted({ start_date: '2026-05-15', end_date: '2026-05-15' });

    assert.strictEqual(adapted.totalEvaluated, 3);
    assert.strictEqual(adapted.totalApplicants, 2);
    assert.strictEqual(adapted.averageScore, 650);
    assert.strictEqual(adapted.averageRiskDifficulty, 40.0);
    assert.strictEqual(adapted.assessmentCompletionRate, 100.0);
    assert.strictEqual(adapted.riskDistribution.moderateRiskCount, 1);
    assert.strictEqual(adapted.riskDistribution.higherRiskCount, 1);
    assert.strictEqual(adapted.riskDistribution.lowerRiskCount, 0);
    assert.strictEqual(adapted.sectorRisk.length, 2);
    console.log('✓ Adapted portfolio analytics accurately presents filtered backend response.\n');

    // -------------------------------------------------------------------------
    // Test 6: Empty dataset safe defaults
    // -------------------------------------------------------------------------
    console.log('Test 6: Verifying empty dataset adaptation (date range with no records)...');
    setupMockFetch(() => new Response(JSON.stringify(mockEmptyPortfolio), { status: 200 }));
    const emptyAdapted = await api.getPortfolioAnalyticsAdapted({ start_date: '2025-01-01', end_date: '2025-01-31' });

    assert.strictEqual(emptyAdapted.totalEvaluated, 0);
    assert.strictEqual(emptyAdapted.totalApplicants, 0);
    assert.strictEqual(emptyAdapted.averageScore, null);
    assert.strictEqual(emptyAdapted.averageRiskDifficulty, null);
    assert.strictEqual(emptyAdapted.assessmentCompletionRate, 0);
    assert.strictEqual(emptyAdapted.sectorRisk.length, 0);
    assert.strictEqual(emptyAdapted.scoreDistribution.length, 0);
    console.log('✓ Empty range results provide safe null/zero fallback properties without exceptions.\n');

    // -------------------------------------------------------------------------
    // Test 7: API Error Handling (HTTP 422 Reversed Range)
    // -------------------------------------------------------------------------
    console.log('Test 7: Verifying error handling for 422 validation failure...');
    setupMockFetch(() => new Response(JSON.stringify({ detail: 'start_date must not be after end_date.' }), { status: 422 }));

    try {
      await api.getPortfolioAnalytics({ start_date: '2026-05-20', end_date: '2026-05-10' });
      assert.fail('Expected ApiError to be thrown for 422 response');
    } catch (err: any) {
      assert.ok(err instanceof ApiError, 'Thrown error must be instance of ApiError');
      assert.strictEqual(err.status, 422);
      assert.ok(err.message.includes('start_date must not be after end_date') || JSON.stringify(err.details).includes('start_date must not be after end_date'));
    }
    console.log('✓ 422 validation error propagated accurately to API client consumer.\n');

    // -------------------------------------------------------------------------
    // Test 8: Reset / Clear Behavior
    // -------------------------------------------------------------------------
    console.log('Test 8: Verifying reset / clear behavior restores unfiltered request...');
    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    // Passing undefined or empty object should not produce query params
    await api.getPortfolioAnalytics(undefined);
    assert.ok(interceptedUrls[0].endsWith('/api/v1/analytics/portfolio'));

    setupMockFetch(() => new Response(JSON.stringify(mockPortfolioResponse), { status: 200 }));
    await api.getPortfolioAnalytics({});
    assert.ok(interceptedUrls[0].endsWith('/api/v1/analytics/portfolio'));
    console.log('✓ Resetting dates accurately executes unfiltered portfolio query.\n');

    console.log('=============================================================');
    console.log('ALL PHASE 14C FRONTEND & API CLIENT TESTS PASSED! ✓');
    console.log('=============================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase14CAnalyticsFilterTests().catch((err) => {
  console.error('Test suite failed:', err);
  process.exit(1);
});
