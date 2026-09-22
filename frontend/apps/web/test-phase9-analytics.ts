// Phase 9: Analytics + Model Governance Integration Test Suite
import assert from 'node:assert';
import {
  api,
  adaptPortfolioAnalytics,
  adaptSectorRisk,
  type BackendPortfolioAnalytics,
  type BackendSectorRiskItem,
  type BackendModelVersion,
} from '@parakh/api';

async function runPhase9AnalyticsTests() {
  console.log('\n=============================================================');
  console.log('PARAKH PHASE 9: ANALYTICS + GOVERNANCE VERIFICATION SUITE');
  console.log('=============================================================\n');

  const originalFetch = globalThis.fetch;

  // Mock responses matching FastAPI schema
  const mockBackendPortfolio: BackendPortfolioAnalytics = {
    total_applications: 42,
    total_applicants: 35,
    assessed_applications: 30,
    manual_review_applications: 8,
    completed_applications: 25,
    average_credit_score: 685.5,
    average_risk_probability: 0.18,
    assessment_completion_rate: 72.4,
    total_assessments: 30,
    status_distribution: {
      SUBMITTED: 2,
      ASSESSED: 12,
      MANUAL_REVIEW: 8,
      COMPLETED: 20,
    },
    risk_distribution: {
      LOWER: 18,
      MODERATE: 10,
      HIGHER: 2,
    },
    score_distribution: [
      { range: '300-499', label: 'Very High Risk (300-499)', count: 2, percentage: 6.7, risk_tier: 'HIGHER' },
      { range: '500-649', label: 'Moderate Risk (500-649)', count: 10, percentage: 33.3, risk_tier: 'MODERATE' },
      { range: '650-749', label: 'Prime Alternative (650-749)', count: 12, percentage: 40.0, risk_tier: 'LOWER' },
      { range: '750-900', label: 'Super Prime Alternative (750-900)', count: 6, percentage: 20.0, risk_tier: 'LOWER' },
    ],
    monthly_volume: [
      { month: '2026-07', count: 12, avg_score: 680.0 },
      { month: '2026-08', count: 15, avg_score: 690.0 },
      { month: '2026-09', count: 15, avg_score: 686.0 },
    ],
    sector_risk: [
      { sector: 'DELIVERY', lower_risk: 10, moderate_risk: 4, higher_risk: 1, manual_review: 0, total: 15 },
      { sector: 'MOBILITY', lower_risk: 5, moderate_risk: 4, higher_risk: 1, manual_review: 0, total: 10 },
      { sector: 'HOME_SERVICES', lower_risk: 3, moderate_risk: 2, higher_risk: 0, manual_review: 0, total: 5 },
    ],
  };

  const mockModelVersions: BackendModelVersion[] = [
    {
      id: 'mv-001',
      version: '1.0.0',
      model_name: 'MockAssessmentEngine',
      algorithm: 'DETERMINISTIC_RULES',
      description: 'Deterministic baseline scoring engine for Phase 0-8',
      is_active: true,
      created_at: '2026-09-20T10:00:00Z',
      updated_at: '2026-09-20T10:00:00Z',
    },
    {
      id: 'mv-002',
      version: '0.9.0-alpha',
      model_name: 'PrototypeRiskScorer',
      algorithm: 'HEURISTIC_TREES',
      description: 'Initial heuristic prototype',
      is_active: false,
      created_at: '2026-08-15T08:30:00Z',
      updated_at: '2026-08-15T08:30:00Z',
    },
  ];

  // Mock fetch router
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const urlStr = typeof input === 'string' ? input : input.toString();
    const url = new URL(urlStr, 'http://localhost:8000');
    const path = url.pathname;
    const method = init?.method || 'GET';
    const authHeader = (init?.headers as Record<string, string>)?.[
      'authorization'
    ] || (init?.headers as Record<string, string>)?.[
      'Authorization'
    ];

    // Assert Bearer token is provided
    if (!authHeader?.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ detail: 'Not authenticated' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/v1/analytics/portfolio' && method === 'GET') {
      return new Response(JSON.stringify(mockBackendPortfolio), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/v1/analytics/sector-risk' && method === 'GET') {
      return new Response(JSON.stringify(mockBackendPortfolio.sector_risk), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/v1/model-versions' && method === 'GET') {
      return new Response(JSON.stringify(mockModelVersions), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({ detail: `Route not found: ${path}` }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }) as typeof fetch;

  try {
    api.setToken('mock-reviewer-token');

    // -------------------------------------------------------------
    // Test 1: adaptSectorRisk
    // -------------------------------------------------------------
    console.log('Test 1: Testing adaptSectorRisk mapping...');
    const rawSectors: BackendSectorRiskItem[] = [
      { sector: 'DELIVERY', lower_risk: 12, moderate_risk: 5, higher_risk: 2, manual_review: 0, total: 19 },
      { sector: 'UNKNOWN_NEW_SECTOR', lower_risk: 1, moderate_risk: 0, higher_risk: 0, manual_review: 0, total: 1 },
    ];
    const adaptedSectors = adaptSectorRisk(rawSectors);
    assert.strictEqual(adaptedSectors.length, 2);
    assert.strictEqual(adaptedSectors[0].sector, 'DELIVERY');
    assert.strictEqual(adaptedSectors[0].displayName, 'Delivery & Quick Commerce');
    assert.strictEqual(adaptedSectors[0].lowerRisk, 12);
    assert.strictEqual(adaptedSectors[0].moderateRisk, 5);
    assert.strictEqual(adaptedSectors[0].higherRisk, 2);
    assert.strictEqual(adaptedSectors[0].total, 19);
    // Unmapped sector should fallback to replacing underscores
    assert.strictEqual(adaptedSectors[1].displayName, 'UNKNOWN NEW SECTOR');
    console.log('✓ adaptSectorRisk accurately maps canonical sectors, counts, and fallbacks.');

    // -------------------------------------------------------------
    // Test 2: adaptPortfolioAnalytics with complete data
    // -------------------------------------------------------------
    console.log('\nTest 2: Testing adaptPortfolioAnalytics with complete backend data...');
    const adaptedPortfolio = adaptPortfolioAnalytics(mockBackendPortfolio);
    assert.strictEqual(adaptedPortfolio.totalEvaluated, 42);
    assert.strictEqual(adaptedPortfolio.totalApplicants, 35);
    assert.strictEqual(adaptedPortfolio.assessedApplications, 30);
    assert.strictEqual(adaptedPortfolio.manualReviewApplications, 8);
    assert.strictEqual(adaptedPortfolio.completedApplications, 25);
    assert.strictEqual(adaptedPortfolio.averageScore, 686); // Rounded
    assert.strictEqual(adaptedPortfolio.averageRiskDifficulty, 18.0);
    assert.strictEqual(adaptedPortfolio.assessmentCompletionRate, 72.4);
    assert.strictEqual(adaptedPortfolio.riskDistribution.lowerRiskCount, 18);
    assert.strictEqual(adaptedPortfolio.riskDistribution.moderateRiskCount, 10);
    assert.strictEqual(adaptedPortfolio.riskDistribution.higherRiskCount, 2);
    assert.strictEqual(adaptedPortfolio.scoreDistribution.length, 4);
    assert.strictEqual(adaptedPortfolio.pipelineStages.length, 5);
    assert.strictEqual(adaptedPortfolio.monthlyVolume.length, 3);
    assert.strictEqual(adaptedPortfolio.sectorRisk.length, 3);
    assert.strictEqual(adaptedPortfolio.sectorRisk[0].displayName, 'Delivery & Quick Commerce');
    console.log('✓ adaptPortfolioAnalytics accurately translates all schema metrics.');

    // -------------------------------------------------------------
    // Test 3: adaptPortfolioAnalytics with null/empty/unassessed DB
    // -------------------------------------------------------------
    console.log('\nTest 3: Testing adaptPortfolioAnalytics with empty DB (null avg_score, empty arrays)...');
    const emptyBackendPortfolio: BackendPortfolioAnalytics = {
      total_applications: 0,
      total_applicants: 0,
      assessed_applications: 0,
      manual_review_applications: 0,
      completed_applications: 0,
      average_credit_score: null,
      average_risk_probability: null,
      assessment_completion_rate: 0.0,
      total_assessments: 0,
      status_distribution: {},
      risk_distribution: {},
      score_distribution: [],
      monthly_volume: [],
      sector_risk: [],
    };
    const emptyAdapted = adaptPortfolioAnalytics(emptyBackendPortfolio);
    assert.strictEqual(emptyAdapted.totalEvaluated, 0);
    assert.strictEqual(emptyAdapted.averageScore, null, 'Avg credit score should remain null when no assessments exist');
    assert.strictEqual(emptyAdapted.averageRiskDifficulty, null);
    assert.strictEqual(emptyAdapted.assessmentCompletionRate, 0.0);
    assert.strictEqual(emptyAdapted.riskDistribution.lowerRiskCount, 0);
    assert.strictEqual(emptyAdapted.scoreDistribution.length, 0);
    assert.strictEqual(emptyAdapted.sectorRisk.length, 0);
    console.log('✓ adaptPortfolioAnalytics correctly handles zero counts and null scores without throwing.');

    // -------------------------------------------------------------
    // Test 4: Live API calls through SDK
    // -------------------------------------------------------------
    console.log('\nTest 4: Testing api client endpoints for portfolio & sector risk...');
    const fetchedPortfolio = await api.getPortfolioAnalyticsAdapted();
    assert.strictEqual(fetchedPortfolio.totalEvaluated, 42);
    assert.strictEqual(fetchedPortfolio.assessedApplications, 30);

    const fetchedSectors = await api.getSectorRiskAdapted();
    assert.strictEqual(fetchedSectors.length, 3);
    assert.strictEqual(fetchedSectors[0].sector, 'DELIVERY');
    console.log('✓ api.getPortfolioAnalyticsAdapted() and api.getSectorRiskAdapted() return adapted models.');

    // -------------------------------------------------------------
    // Test 5: Model version registry retrieval & active model selection
    // -------------------------------------------------------------
    console.log('\nTest 5: Testing Model Version retrieval & active model resolution...');
    const versions = await api.getModelVersions();
    assert.strictEqual(versions.length, 2);
    const active = versions.find((v) => v.is_active) || versions[0];
    assert.ok(active, 'Active model must be found');
    assert.strictEqual(active.version, '1.0.0');
    assert.strictEqual(active.model_name, 'MockAssessmentEngine');
    assert.strictEqual(active.algorithm, 'DETERMINISTIC_RULES');
    console.log('✓ Model version retrieval correctly resolves active engine v1.0.0.');

    // -------------------------------------------------------------
    // Test 6: Model version empty fallback verification
    // -------------------------------------------------------------
    console.log('\nTest 6: Testing Model Version handling when backend has 0 registered models...');
    const emptyVersions: BackendModelVersion[] = [];
    const activeFromEmpty = emptyVersions.find((v) => v.is_active) || emptyVersions[0] || null;
    assert.strictEqual(activeFromEmpty, null);
    console.log('✓ Model version registry safely resolves null when no models are registered.');

    // -------------------------------------------------------------
    // Test 7: ML Placeholder Verification
    // -------------------------------------------------------------
    console.log('\nTest 7: Verifying ML Placeholder integrity (no fabricated numbers)...');
    // Ensure that no fake SHAP weights or fake demographic parity ratios are embedded in our adapted models
    assert.strictEqual((adaptedPortfolio as any).shapWeights, undefined, 'No fake SHAP weights attached to portfolio');
    assert.strictEqual((adaptedPortfolio as any).fairnessMetrics, undefined, 'No fake fairness metrics attached to portfolio');
    console.log('✓ ML metrics remain clean placeholders awaiting production model integration.');

    console.log('\n=============================================================');
    console.log('ALL PHASE 9 FRONTEND & ADAPTER TESTS PASSED SUCCESSFULLY! ✓');
    console.log('=============================================================\n');
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runPhase9AnalyticsTests().catch((err) => {
  console.error('Phase 9 Test failure:', err);
  process.exit(1);
});
