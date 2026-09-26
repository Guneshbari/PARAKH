'use client';

import React, { useState, useEffect } from 'react';
import {
  Activity,
  TrendingUp,
  ShieldCheck,
  Building2,
  Printer,
  Info,
  Clock,
  Sparkles,
  AlertTriangle,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { MetricCard } from '@/components/shared/MetricCard';
import { useTheme } from '@/components/theme/ThemeProvider';
import {
  api,
  type AdaptedPortfolioAnalytics,
} from '@parakh/api';

function toDateInputValue(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function AdminAnalyticsPage() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [timeRange, setTimeRange] = useState<string>('ALL');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [appliedStartDate, setAppliedStartDate] = useState<string>('');
  const [appliedEndDate, setAppliedEndDate] = useState<string>('');
  const [portfolio, setPortfolio] = useState<AdaptedPortfolioAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async (params?: { start_date?: string; end_date?: string }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getPortfolioAnalyticsAdapted(params);
      setPortfolio(data);
      setAppliedStartDate(params?.start_date || '');
      setAppliedEndDate(params?.end_date || '');
    } catch (err: any) {
      console.warn('Analytics page fetch error:', err);
      const msg = err?.detail || err?.userMessage || err?.message || 'Failed to load portfolio analytics from backend.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const handleApply = (overrideStart?: string, overrideEnd?: string) => {
    const s = overrideStart !== undefined ? overrideStart : startDate;
    const e = overrideEnd !== undefined ? overrideEnd : endDate;

    if (s && e && s > e) {
      setError('start_date must not be after end_date.');
      return;
    }

    const params: { start_date?: string; end_date?: string } = {};
    if (s.trim()) params.start_date = s.trim();
    if (e.trim()) params.end_date = e.trim();

    fetchAnalytics(Object.keys(params).length > 0 ? params : undefined);
  };

  const handlePreset = (presetId: string) => {
    setTimeRange(presetId);
    if (presetId === 'ALL') {
      setStartDate('');
      setEndDate('');
      fetchAnalytics();
    } else {
      const end = new Date();
      const start = new Date();
      if (presetId === '30D') {
        start.setDate(start.getDate() - 30);
      } else if (presetId === '90D') {
        start.setDate(start.getDate() - 90);
      } else if (presetId === '6M') {
        start.setMonth(start.getMonth() - 6);
      }
      const s = toDateInputValue(start);
      const e = toDateInputValue(end);
      setStartDate(s);
      setEndDate(e);
      handleApply(s, e);
    }
  };

  const handleReset = () => {
    setStartDate('');
    setEndDate('');
    setTimeRange('ALL');
    fetchAnalytics();
  };

  const hasActiveDateFilter = Boolean(appliedStartDate || appliedEndDate);
  const appliedRangeLabel = appliedStartDate && appliedEndDate
    ? `${appliedStartDate} to ${appliedEndDate}`
    : appliedStartDate
    ? `From ${appliedStartDate}`
    : appliedEndDate
    ? `Until ${appliedEndDate}`
    : null;

  const totalEvaluated = portfolio?.totalEvaluated ?? 0;
  const avgScore = portfolio?.averageScore;
  const avgRiskDifficulty = portfolio?.averageRiskDifficulty;
  const completionRate = portfolio?.assessmentCompletionRate ?? 0;
  const sectorRiskData = portfolio?.sectorRisk ?? [];

  // Chart tokens
  const chartGridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.06)';
  const chartAxisColor = isDark ? '#71717A' : '#94A3B8';

  const stackedBarColors = isDark
    ? {
        lower: '#FFFFFF',
        moderate: '#D4D4D8',
        higher: '#A1A1AA',
        review: '#71717A',
      }
    : {
        lower: '#0F172A',
        moderate: '#334155',
        higher: '#64748B',
        review: '#94A3B8',
      };

  const lineColors = isDark
    ? {
        food: '#FFFFFF',
        home: '#D4D4D8',
        ride: '#A1A1AA',
        bench: '#52525B',
      }
    : {
        food: '#0F172A',
        home: '#472393',
        ride: '#9B7DE3',
        bench: '#94A3B8',
      };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & FILTER STRIP */}
      <div className="flex flex-col gap-4 pb-4 border-b border-border">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
                Portfolio Risk & Volatility Analytics
              </h1>
              <Badge variant="mint" className="text-xs py-0.5 px-2">
                Cohort Telemetry Live
              </Badge>
              {hasActiveDateFilter && (
                <Badge variant="secondary" className="text-xs py-0.5 px-2 font-mono">
                  {appliedRangeLabel}
                </Badge>
              )}
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Deep-dive cohort telemetry, recovery velocity dynamics, sector-wise risk segmentation, and long-term assessment stability.
            </p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-secondary hover:text-foreground shrink-0 self-start md:self-center"
          >
            <Printer className="size-3.5" /> Print Analytics
          </Button>
        </div>

        {/* Date Filter Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          {/* Presets */}
          <div className="flex items-center bg-surface-highlight p-1 rounded-full border border-border">
            {[
              { id: 'ALL', label: 'All Time' },
              { id: '30D', label: '30D' },
              { id: '90D', label: '90D' },
              { id: '6M', label: '6M' },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => handlePreset(t.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
                  timeRange === t.id
                    ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                    : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Explicit Date Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 bg-surface-highlight border border-border rounded-xl px-2.5 py-1">
              <span className="text-[11px] font-semibold text-foreground-secondary uppercase tracking-wider">Start</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setTimeRange('CUSTOM');
                }}
                className="bg-transparent text-xs text-foreground focus:outline-none cursor-pointer"
                aria-label="Start Date"
                data-testid="analytics-start-date"
              />
            </div>

            <div className="flex items-center gap-1.5 bg-surface-highlight border border-border rounded-xl px-2.5 py-1">
              <span className="text-[11px] font-semibold text-foreground-secondary uppercase tracking-wider">End</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setTimeRange('CUSTOM');
                }}
                className="bg-transparent text-xs text-foreground focus:outline-none cursor-pointer"
                aria-label="End Date"
                data-testid="analytics-end-date"
              />
            </div>

            <Button
              variant="default"
              size="sm"
              onClick={() => handleApply()}
              disabled={isLoading}
              className="h-8 rounded-xl text-xs px-3.5 bg-[#472393] hover:bg-[#3b1c7c] text-white dark:bg-foreground dark:text-background cursor-pointer gap-1.5"
              data-testid="analytics-apply-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Updating...
                </>
              ) : (
                'Apply'
              )}
            </Button>

            {(startDate || endDate || hasActiveDateFilter) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleReset}
                disabled={isLoading}
                className="h-8 rounded-xl text-xs px-2.5 text-foreground-secondary hover:text-foreground cursor-pointer gap-1"
                data-testid="analytics-reset-button"
              >
                <RotateCcw className="size-3.5" />
                Reset
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ERROR BANNER IF API FAILED */}
      {error && (
        <div className="p-3.5 rounded-2xl bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center justify-between gap-3">
          <span>Failed to load live portfolio analytics: {error}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleApply()}
            className="text-xs h-7 rounded-full shrink-0"
          >
            Retry
          </Button>
        </div>
      )}

      {/* FILTER-SPECIFIC EMPTY STATE */}
      {portfolio && portfolio.totalEvaluated === 0 && !isLoading && (
        <Card className="p-8 text-center bg-surface border-border space-y-3">
          <div className="size-12 rounded-2xl bg-surface-highlight border border-border mx-auto flex items-center justify-center text-foreground-secondary">
            <Activity className="size-6" />
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <h3 className="text-base font-semibold text-foreground">No Records in Selected Date Range</h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              {appliedRangeLabel
                ? `No credit applications or assessments match the filtered date range (${appliedRangeLabel}).`
                : 'No credit applications or assessments have been registered yet.'}
            </p>
          </div>
          {hasActiveDateFilter && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="rounded-full text-xs"
            >
              Reset Date Filter
            </Button>
          )}
        </Card>
      )}

      {/* 2. PORTFOLIO RESILIENCE KPIS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Evaluated Applicants"
          value={totalEvaluated}
          pillLabel={portfolio?.totalApplicants ? `${portfolio.totalApplicants} profiles` : 'Active'}
          pillVariant="secondary"
          subtext="Informal & gig economy applicants"
          icon={Activity}
        />

        <MetricCard
          title="Portfolio Average Score"
          value={avgScore ?? 0}
          format={(n) => (avgScore !== null && avgScore !== undefined ? String(n) : '—')}
          suffix={avgScore !== null && avgScore !== undefined ? ' / 850' : ''}
          pillLabel={avgScore !== null && avgScore !== undefined ? 'Calibrated' : 'Pending'}
          pillVariant="secondary"
          subtext={avgScore !== null && avgScore !== undefined ? 'Alternative volatility scoring engine' : 'No assessments completed yet'}
          icon={TrendingUp}
        />

        <MetricCard
          title="Avg. Repayment Difficulty"
          value={avgRiskDifficulty ?? 0}
          format={(n) => (avgRiskDifficulty !== null && avgRiskDifficulty !== undefined ? String(n) : '—')}
          suffix={avgRiskDifficulty !== null && avgRiskDifficulty !== undefined ? '%' : ''}
          pillLabel={avgRiskDifficulty !== null && avgRiskDifficulty !== undefined ? 'Risk Rate' : 'Pending'}
          pillVariant="secondary"
          subtext={avgRiskDifficulty !== null && avgRiskDifficulty !== undefined ? 'Estimated repayment stress indicator' : 'No assessments completed yet'}
          icon={ShieldCheck}
        />

        <MetricCard
          title="Assessment Completion Rate"
          value={completionRate}
          suffix="%"
          pillLabel={`${portfolio?.completedApplications ?? 0} Completed`}
          pillVariant="mint"
          subtext="Digital intake to synthesis conversion"
          icon={TrendingUp}
        />
      </div>

      {/* 3. VISUALIZATION 1: RISK TIER DISTRIBUTION BY GIG SECTOR */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Building2 className="size-4 text-foreground-secondary" />
              Risk Classification Distribution Across Gig Sectors
            </h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Segmented risk volume showing proportion of Lower, Moderate, Higher, and Manual Review cases by worker cohort.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-foreground-secondary">
              <span className="size-2.5 rounded-sm bg-foreground" /> Lower Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-secondary">
              <span className="size-2.5 rounded-sm bg-foreground-secondary opacity-70" /> Moderate Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-secondary">
              <span className="size-2.5 rounded-sm bg-foreground-muted opacity-50" /> Higher Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-secondary">
              <span className="size-2.5 rounded-sm bg-foreground-muted opacity-30" /> Manual Review
            </span>
          </div>
        </div>

        {sectorRiskData.length === 0 ? (
          <div className="py-16 text-center text-xs sm:text-sm text-foreground-secondary space-y-1">
            <p className="font-semibold text-foreground">No Sector Risk Data Available</p>
            <p>Risk distribution across gig sectors will populate as applicants with profiles submit applications and complete assessments.</p>
          </div>
        ) : (
          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={sectorRiskData}
                margin={{ top: 15, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                <XAxis dataKey="sector" stroke={chartAxisColor} fontSize={12} tickLine={false} />
                <YAxis stroke={chartAxisColor} fontSize={12} tickLine={false} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const total = payload.reduce((acc, p) => acc + (Number(p.value) || 0), 0);
                      return (
                        <div className="bg-surface p-3 rounded-xl border border-border shadow-xl text-xs space-y-1 text-foreground">
                          <span className="font-semibold text-foreground block">{label} ({total.toLocaleString()} Total)</span>
                          {payload.map((p) => (
                            <div key={p.name} className="flex justify-between gap-3 font-mono">
                              <span className="text-foreground-secondary">{p.name}:</span>
                              <span className="text-foreground font-semibold">{Number(p.value).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="lowerRisk" name="Lower Estimated Risk" stackId="a" fill={stackedBarColors.lower} radius={[0, 0, 0, 0]} />
                <Bar dataKey="moderateRisk" name="Moderate Estimated Risk" stackId="a" fill={stackedBarColors.moderate} />
                <Bar dataKey="higherRisk" name="Higher Estimated Risk" stackId="a" fill={stackedBarColors.higher} />
                <Bar dataKey="manualReview" name="Manual Review Required" stackId="a" fill={stackedBarColors.review} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {/* 4. VISUALIZATION 2: SHOCK RECOVERY VELOCITY REBOUND CURVES (ML PLACEHOLDER) */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Clock className="size-4 text-foreground-secondary" />
              Income Shock Rebound Trajectory Curves (Days 0 to 21)
            </h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Tracks normalized post-shock earning recovery against traditional salaried baseline expectations.
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            Cohort Macro Analytics
          </Badge>
        </div>

        {/* Clean explicit placeholder */}
        <div className="p-6 rounded-2xl bg-surface-highlight/30 border border-border text-center space-y-3">
          <div className="size-10 rounded-2xl bg-surface border border-border mx-auto flex items-center justify-center text-amber-500">
            <AlertTriangle className="size-5" />
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <h4 className="text-sm font-semibold text-foreground">
              ML Macro Analytics Under Batch Aggregation
            </h4>
            <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
              Empirical recovery rebound curves and cyclical variance calibrations reflect the frozen volatility-aware risk model (v1.0.0). Individual assessments are actively evaluated using the TelemetryFeaturePipeline and LightGBM model, while longitudinal cohort rebound curves are being aggregated from historical assessment batches.
            </p>
          </div>
        </div>

        {/* Explainability Callout */}
        <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-2.5">
          <Sparkles className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-foreground block">
              Core PARAKH Methodology: Volatility Resilience & Recovery
            </span>
            <p className="text-foreground-secondary leading-relaxed">
              Traditional credit models treat sharp week-to-week income drops as insolvency risk. PARAKH alternative scoring is designed to recognize rapid cashflow rebound velocity across delivery and platform workers once seasonal dips resolve.
            </p>
          </div>
        </div>
      </Card>

      {/* 5. DETAILED SECTOR PERFORMANCE COMPARISON GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {sectorRiskData.length === 0 ? (
          <div className="col-span-full p-6 text-center rounded-2xl bg-surface border border-border text-xs sm:text-sm text-foreground-secondary">
            No sector breakdown records registered yet. Real applicant data will display here as profiles are registered.
          </div>
        ) : (
          sectorRiskData.map((s) => (
            <Card key={s.sector} className="p-5 bg-surface border-border space-y-3">
              <div className="space-y-0.5">
                <h4 className="text-sm font-semibold text-foreground line-clamp-1">{s.sector}</h4>
                <span className="text-xs font-mono text-foreground-secondary">
                  {s.total.toLocaleString()} Assessed Applications
                </span>
              </div>

              <div className="space-y-2 text-xs sm:text-sm pt-1 border-t border-border">
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">Lower Risk</span>
                  <span className="font-mono font-semibold text-foreground">
                    {s.lowerRisk}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">Moderate Risk</span>
                  <span className="font-mono font-semibold text-foreground">
                    {s.moderateRisk}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">Higher / Review</span>
                  <span className="font-mono font-medium text-foreground-secondary">
                    {s.higherRisk + s.manualReview}
                  </span>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* 6. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-xs text-foreground-secondary flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Portfolio Analytics Governance Notice
          </span>
          <p className="leading-relaxed">
            Portfolio analytics reflect anonymized telemetry aggregated across partner platform APIs and RBI Account Aggregators. PARAKH provides explainable risk intelligence without automated lending decisions.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
