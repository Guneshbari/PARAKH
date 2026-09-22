'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  TrendingUp,
  Activity,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Search,
  Printer,
  UserCheck,
  Building2,
  Sparkles,
  Info,
  X,
  Send,
  Loader2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { PageTransition } from '@/components/motion/PageTransition';
import { MetricCard } from '@/components/shared/MetricCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { useTheme } from '@/components/theme/ThemeProvider';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  reverseAdaptReviewAction,
  adaptApplication,
  type AdaptedPortfolioAnalytics,
} from '@parakh/api';
import {
  mockOperationalAlerts,
} from '@/data/mock/admin';
import { formatCurrency } from '@/lib/utils';
import type { ReviewActionType, UnderwriterReviewOutcome } from '@parakh/types';

export default function AdminDashboardPage() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [portfolio, setPortfolio] = useState<AdaptedPortfolioAnalytics | null>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Interactive review modal/drawer state
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [reviewAction, setReviewAction] =
    useState<ReviewActionType>('MANUAL_REVIEW');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSuccess, setReviewSuccess] = useState(false);
  const [activeQueue, setActiveQueue] = useState<any[]>([]);

  const totalEvaluated = portfolio?.totalEvaluated ?? 0;
  const avgScore = portfolio?.averageScore !== null && portfolio?.averageScore !== undefined ? portfolio.averageScore : null;
  const avgRiskDifficulty = portfolio?.averageRiskDifficulty !== null && portfolio?.averageRiskDifficulty !== undefined ? portfolio.averageRiskDifficulty : null;
  const completionRate = portfolio?.assessmentCompletionRate ?? 0;
  const riskDist = portfolio?.riskDistribution ?? { lowerRiskCount: 0, moderateRiskCount: 0, higherRiskCount: 0, manualReviewCount: 0 };
  const totalAssessed = riskDist.lowerRiskCount + riskDist.moderateRiskCount + riskDist.higherRiskCount + riskDist.manualReviewCount;
  const pipelineStages = portfolio?.pipelineStages ?? [];
  const scoreBuckets = portfolio?.scoreDistribution ?? [];
  const monthlyVolume = portfolio?.monthlyVolume ?? [];

  // Filter priority queue
  const filteredQueue = activeQueue.filter((item) => {
    const matchesSearch =
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.applicantName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.purpose.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.triggerReason && item.triggerReason.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFilter =
      statusFilter === 'ALL' ||
      (statusFilter === 'REVIEW' && item.status === 'MANUAL_REVIEW_REQUIRED') ||
      (statusFilter === 'VALIDATION' && item.status === 'DATA_VALIDATION');

    return matchesSearch && matchesFilter;
  });

  const loadDashboardData = async () => {
    setIsLoading(true);
    setPortfolioError(null);

    try {
      const analyticsData = await api.getPortfolioAnalyticsAdapted();
      setPortfolio(analyticsData);
    } catch (err: any) {
      console.warn('Portfolio analytics fetch error:', err);
      setPortfolioError(err?.message || 'Failed to fetch portfolio analytics from database');
    }

    try {
      const rawApps = await api.getApplications();
      if (rawApps && rawApps.length > 0) {
        const mappedQueue = rawApps.map((app) => {
          const adapted = adaptApplication(app);
          return {
            ...adapted,
            applicantName: `Applicant ${app.applicant_profile_id ? app.applicant_profile_id.slice(0, 8) : app.id.slice(0, 8)}`,
            sectorTag: adapted.purpose?.toLowerCase().includes('equipment') ? 'Micro-enterprise' : 'Urban Gig Delivery',
            triggerReason:
              app.status === 'MANUAL_REVIEW'
                ? 'Alternative cashflow volatility requires reviewer sign-off'
                : app.status === 'UNDER_REVIEW'
                ? 'Inflow signals currently under aggregation'
                : 'Standard credit risk evaluation',
          };
        });
        setActiveQueue(mappedQueue);
      } else {
        setActiveQueue([]);
      }
    } catch (err) {
      console.warn('Could not load applications for review queue:', err);
      setActiveQueue([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleOpenReview = (item: (typeof activeQueue)[0]) => {
    setSelectedCase(item);
    setReviewNotes(item.review?.decisionNotes || '');
    setReviewAction(item.review?.action || 'MANUAL_REVIEW');
    setReviewSuccess(false);
    setReviewError(null);
  };

  const handleRecordReviewOutcome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;

    try {
      setIsSubmitting(true);
      setReviewError(null);
      const outcome = reverseAdaptReviewAction(reviewAction);
      const reviewerId = user?.id || '00000000-0000-0000-0000-000000000000';

      await api.createReview(selectedCase.id, {
        reviewer_id: reviewerId,
        outcome: outcome,
        notes: reviewNotes || 'Credit reviewer notes recorded.',
      });

      if (reviewAction === 'RECORD_OUTCOME') {
        try {
          await api.updateApplicationStatus(selectedCase.id, 'COMPLETED');
        } catch {
          // ignore transition error if already completed
        }
      }

      await loadDashboardData();

      setReviewSuccess(true);
      setTimeout(() => {
        setSelectedCase(null);
        setReviewSuccess(false);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to submit review:', err);
      setReviewError(err?.message || 'Failed to submit review to backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const chartBarColor = isDark ? '#FFFFFF' : '#472393';
  const chartLineColor = isDark ? '#A1A1AA' : '#9B7DE3';
  const chartGridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.06)';
  const chartAxisColor = isDark ? '#71717A' : '#94A3B8';

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & OPERATIONAL STATUS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Credit Review Dashboard
            </h1>
            <Badge variant="secondary" className="text-[10px] py-0.5 px-2">
              Portfolio Resilient
            </Badge>
            <Badge variant="outline" className="text-[10px] font-mono text-foreground-muted">
              PostgreSQL Live
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Portfolio alternative credit intelligence, cyclical income volatility monitoring, and priority human-in-the-loop review queue.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>

          <a href="#review-queue">
            <Button
              variant="default"
              size="sm"
              className="rounded-full gap-1.5 text-xs font-semibold shadow-xs cursor-pointer"
            >
              <UserCheck className="size-3.5" />
              <span>Review Queue ({activeQueue.filter(q => q.status === 'MANUAL_REVIEW_REQUIRED' || q.status === 'DATA_VALIDATION').length} Pending)</span>
            </Button>
          </a>
        </div>
      </div>

      {/* ERROR BANNER IF API FAILED */}
      {portfolioError && (
        <div className="p-3.5 rounded-2xl bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center justify-between gap-3">
          <span>Failed to load live portfolio analytics: {portfolioError}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardData}
            className="text-xs h-7 rounded-full shrink-0"
          >
            Retry
          </Button>
        </div>
      )}

      {/* 2. PORTFOLIO HIGH-LEVEL KPIS (NO AUTOMATED LOAN APPROVAL RATES) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Evaluated Applicants"
          value={totalEvaluated}
          pillLabel={portfolio?.totalApplicants ? `${portfolio.totalApplicants} profiles` : 'Active'}
          pillVariant="secondary"
          subtext="Informal & gig economy applicants"
          icon={Users}
        />

        <MetricCard
          title="Portfolio Average Score"
          value={avgScore ?? 0}
          format={(n) => (avgScore !== null ? String(n) : '—')}
          suffix={avgScore !== null ? ' / 850' : ''}
          pillLabel={avgScore !== null ? 'Calibrated' : 'Pending'}
          pillVariant="secondary"
          subtext={avgScore !== null ? 'Alternative volatility scoring engine' : 'No assessments completed yet'}
          icon={TrendingUp}
        />

        <MetricCard
          title="Avg. Repayment Difficulty"
          value={avgRiskDifficulty ?? 0}
          format={(n) => (avgRiskDifficulty !== null ? String(n) : '—')}
          suffix={avgRiskDifficulty !== null ? '%' : ''}
          pillLabel={avgRiskDifficulty !== null ? 'Risk Rate' : 'Pending'}
          pillVariant="secondary"
          subtext={avgRiskDifficulty !== null ? 'Estimated repayment stress indicator' : 'No assessments completed yet'}
          icon={Activity}
        />

        <MetricCard
          title="Assessment Completion Rate"
          value={completionRate}
          suffix="%"
          pillLabel={`${portfolio?.completedApplications ?? 0} Completed`}
          pillVariant="mint"
          subtext="Digital intake to synthesis conversion"
          icon={CheckCircle2}
        />
      </div>

      {/* 3. OPERATIONAL REVIEW ALERTS */}
      <div className="space-y-3">
        {mockOperationalAlerts.map((alert) => (
          <div
            key={alert.id}
            className="p-4 rounded-2xl bg-surface border border-border shadow-card flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <div className="size-8 rounded-xl bg-surface-highlight border border-border flex items-center justify-center shrink-0 mt-0.5 text-foreground">
                <AlertCircle className="size-4 opacity-80" />
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-semibold text-foreground">{alert.title}</h4>
                  <Badge variant="outline" className="text-[9px] py-0 px-1.5 uppercase font-mono">
                    {alert.category.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <p className="text-xs text-foreground-muted leading-relaxed">
                  {alert.message}
                </p>
              </div>
            </div>

            <span className="text-[11px] font-mono text-foreground-muted shrink-0 self-end sm:self-center">
              {alert.timestamp}
            </span>
          </div>
        ))}
      </div>

      {/* 4. RISK DISTRIBUTION & EVALUATION PIPELINE FUNNEL */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Approved Risk Level Distribution */}
        <Card className="p-6 bg-surface border-border space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <ShieldCheck className="size-4 text-foreground-secondary" />
                Portfolio Risk Tier Distribution
              </h3>
              <p className="text-xs text-foreground-muted">
                Categorized by approved PARAKH alternative risk classifications.
              </p>
            </div>
            <span className="text-xs font-mono text-foreground-muted">
              {totalAssessed.toLocaleString()} Assessed
            </span>
          </div>

          {totalAssessed === 0 ? (
            <div className="py-8 text-center text-xs text-foreground-muted">
              No credit assessments generated yet. Risk tiers will populate upon assessment execution.
            </div>
          ) : (
            <>
              {/* Segmented Progress Bar */}
              <div className="w-full h-2.5 rounded-full bg-surface-highlight overflow-hidden flex">
                <div
                  style={{ width: `${(riskDist.lowerRiskCount / totalAssessed) * 100}%` }}
                  className="bg-foreground h-full"
                  title="LOWER ESTIMATED RISK"
                />
                <div
                  style={{ width: `${(riskDist.moderateRiskCount / totalAssessed) * 100}%` }}
                  className="bg-foreground-secondary h-full opacity-70"
                  title="MODERATE ESTIMATED RISK"
                />
                <div
                  style={{ width: `${(riskDist.higherRiskCount / totalAssessed) * 100}%` }}
                  className="bg-foreground-muted h-full opacity-50"
                  title="HIGHER ESTIMATED RISK"
                />
                <div
                  style={{ width: `${(riskDist.manualReviewCount / totalAssessed) * 100}%` }}
                  className="bg-foreground-muted h-full opacity-30"
                  title="INSUFFICIENT EVIDENCE / MANUAL REVIEW"
                />
              </div>

              {/* Breakdown Rows */}
              <div className="space-y-2.5 pt-1 text-xs">
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-highlight/40 border border-border">
                  <div className="flex items-center gap-2.5">
                    <span className="size-2 rounded-full bg-foreground" />
                    <span className="font-semibold text-foreground">LOWER ESTIMATED RISK</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-foreground-muted">
                      {riskDist.lowerRiskCount.toLocaleString()}
                    </span>
                    <span className="font-mono font-semibold text-foreground w-12 text-right">
                      {((riskDist.lowerRiskCount / totalAssessed) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-highlight/40 border border-border">
                  <div className="flex items-center gap-2.5">
                    <span className="size-2 rounded-full bg-foreground-secondary opacity-70" />
                    <span className="font-semibold text-foreground">MODERATE ESTIMATED RISK</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-foreground-muted">
                      {riskDist.moderateRiskCount.toLocaleString()}
                    </span>
                    <span className="font-mono font-semibold text-foreground-secondary w-12 text-right">
                      {((riskDist.moderateRiskCount / totalAssessed) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-highlight/40 border border-border">
                  <div className="flex items-center gap-2.5">
                    <span className="size-2 rounded-full bg-foreground-muted opacity-50" />
                    <span className="font-semibold text-foreground">HIGHER ESTIMATED RISK</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-foreground-muted">
                      {riskDist.higherRiskCount.toLocaleString()}
                    </span>
                    <span className="font-mono font-semibold text-foreground-muted w-12 text-right">
                      {((riskDist.higherRiskCount / totalAssessed) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-highlight/40 border border-border">
                  <div className="flex items-center gap-2.5">
                    <span className="size-2 rounded-full bg-foreground-muted opacity-30" />
                    <span className="font-semibold text-foreground">INSUFFICIENT EVIDENCE / MANUAL REVIEW</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-foreground-muted">
                      {riskDist.manualReviewCount.toLocaleString()}
                    </span>
                    <span className="font-mono font-semibold text-foreground-muted w-12 text-right">
                      {((riskDist.manualReviewCount / totalAssessed) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>

        {/* Right: Application Pipeline Funnel */}
        <Card className="p-6 bg-surface border-border space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Activity className="size-4 text-foreground-secondary" />
                Evaluation Pipeline & Throughput
              </h3>
              <p className="text-xs text-foreground-muted">
                Lifecycle progression from intake registration to underwriting queue.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              {totalEvaluated > 0 ? `${completionRate}% Synthesized` : 'Pipeline Ready'}
            </Badge>
          </div>

          <div className="space-y-4 pt-1">
            {pipelineStages.map((stage, idx) => {
              const percentage = totalEvaluated > 0 ? ((stage.count / totalEvaluated) * 100).toFixed(1) : '0.0';
              return (
                <div key={stage.id} className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-foreground flex items-center gap-2">
                      <span className="font-mono text-foreground-muted text-[11px]">0{idx + 1}</span>
                      {stage.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-foreground">
                        {stage.count.toLocaleString()}
                      </span>
                      <span className="text-foreground-muted font-mono text-[11px]">({percentage}%)</span>
                    </div>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-surface-highlight overflow-hidden">
                    <div
                      style={{ width: `${Math.min(100, Math.max(0, Number(percentage)))}%` }}
                      className="h-full rounded-full bg-foreground transition-all duration-500"
                    />
                  </div>
                  <span className="text-[10px] text-foreground-muted block pl-5">{stage.subtext}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* 5. VISUAL ANALYTICS: MONTHLY INTAKE & SCORE STABILITY */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <TrendingUp className="size-4 text-foreground-secondary" />
              Monthly Volume & Score Stability Trend (6 Months)
            </h3>
            <p className="text-xs text-foreground-muted">
              Compares applicant volume growth against alternative score resilience across seasonal cycles.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2.5 rounded-sm bg-foreground" /> Volume
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2 rounded-full bg-foreground-secondary" /> Avg Score
            </span>
          </div>
        </div>

        <div className="h-64 w-full pt-2">
          {monthlyVolume.length === 0 || monthlyVolume.every((m) => m.count === 0) ? (
            <div className="h-full flex items-center justify-center text-xs text-foreground-muted">
              No application intake recorded in recent months.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={monthlyVolume}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                <XAxis
                  dataKey="month"
                  stroke={chartAxisColor}
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="left"
                  stroke={chartAxisColor}
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke={chartAxisColor}
                  fontSize={11}
                  tickLine={false}
                  domain={[300, 850]}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-surface p-3 rounded-xl border border-border shadow-xl text-xs space-y-1 text-foreground">
                          <span className="font-semibold text-foreground block">{label}</span>
                          <span className="font-mono block text-foreground-secondary">
                            Intake: {payload[0]?.value} evaluations
                          </span>
                          <span className="font-mono block text-foreground font-semibold">
                            Average Score: {payload[1]?.value ? `${payload[1].value} / 850` : 'N/A'}
                          </span>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar
                  yAxisId="left"
                  dataKey="count"
                  fill={chartBarColor}
                  opacity={0.8}
                  radius={[4, 4, 0, 0]}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="avgScore"
                  stroke={chartLineColor}
                  strokeWidth={2}
                  dot={{ r: 3.5, fill: chartLineColor }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </Card>

      {/* 6. SECTOR VOLATILITY & SCORE BUCKETS (TWO COLUMNS) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Volatility Comparison - Explicit ML Placeholder */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Building2 className="size-4 text-foreground-secondary" />
                Sector Volatility & Shock Rebound
              </h3>
              <p className="text-xs text-foreground-muted">
                Observed recovery velocity and volatility index by gig worker segment.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              Pending ML Pipeline
            </Badge>
          </div>

          <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-4 text-amber-500 shrink-0" />
              <span className="font-semibold text-foreground">
                ML Volatility Telemetry Integration
              </span>
            </div>
            <p className="text-foreground-muted text-[11px] leading-relaxed">
              Sector-level recovery velocity curves and cyclical volatility indices are computed by Person 2 & 3's LightGBM/XGBoost ML pipeline. In the interim, live assessments are scored through the deterministic MockAssessmentEngine registered in PostgreSQL. ML analytics unavailable until the production assessment model is integrated.
            </p>
          </div>
        </Card>

        {/* Alternative Score Distribution Buckets */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sparkles className="size-4 opacity-75" />
                Alternative Score Distribution
              </h3>
              <p className="text-xs text-foreground-muted">
                Distribution of applicant scores across volatility-calibrated tiers.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              {avgScore !== null ? `Mean: ${avgScore}` : 'Unassessed'}
            </Badge>
          </div>

          <div className="space-y-3 pt-1">
            {scoreBuckets.length === 0 ? (
              <div className="py-8 text-center text-xs text-foreground-muted">
                No score histogram available. Scores will populate once applications are assessed.
              </div>
            ) : (
              scoreBuckets.map((bucket) => (
                <div
                  key={bucket.range}
                  className="p-3 rounded-2xl bg-surface-highlight/30 border border-border space-y-1.5 text-xs"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-foreground">{bucket.range}</span>
                      <span className="text-foreground-muted text-[11px]">• {bucket.label}</span>
                    </div>
                    <RiskBadge riskLevel={bucket.riskTier} showIcon={false} className="text-[10px] py-0 px-2" />
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 rounded-full bg-surface-highlight overflow-hidden">
                      <div
                        style={{ width: `${bucket.percentage}%` }}
                        className="h-full rounded-full bg-foreground"
                      />
                    </div>
                    <span className="font-mono font-semibold text-foreground-secondary w-16 text-right">
                      {bucket.count.toLocaleString()} ({bucket.percentage}%)
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* 7. PRIORITY UNDERWRITER REVIEW QUEUE */}
      <Card id="review-queue" className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-border">
          <div className="space-y-0.5">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <UserCheck className="size-4 text-foreground-secondary" />
              Priority Credit Review Queue
            </h2>
            <p className="text-xs text-foreground-muted">
              Cases flagged for human credit reviewer scrutiny due to non-standard volatility, seasonal weather, or single-platform concentration.
            </p>
          </div>

          {/* Search & Filter */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:w-56">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-foreground-muted" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search queue..."
                className="pl-9 h-8 text-xs rounded-full bg-surface border-border text-foreground placeholder:text-foreground-muted"
              />
            </div>

            <div className="flex items-center gap-1 bg-surface-highlight p-1 rounded-full border border-border">
              {[
                { id: 'ALL', label: 'All Cases' },
                { id: 'REVIEW', label: 'Manual Review' },
                { id: 'VALIDATION', label: 'Data Validation' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  className={`px-3 py-1 rounded-full text-xs font-medium cursor-pointer transition-all ${
                    statusFilter === f.id
                      ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                      : 'text-foreground-muted hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Queue Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-highlight/40 border-b border-border text-foreground-muted font-medium uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Application ID</th>
                <th className="py-3 px-4">Applicant & Sector</th>
                <th className="py-3 px-4">Requested Capital</th>
                <th className="py-3 px-4">Review Trigger</th>
                <th className="py-3 px-4">Status & Risk</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-foreground-muted">
                    <Loader2 className="size-5 animate-spin mx-auto mb-2 text-foreground" />
                    <span>Loading priority review queue from backend...</span>
                  </td>
                </tr>
              ) : filteredQueue.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-foreground-muted">
                    No credit dossiers currently match the selected queue filter.
                  </td>
                </tr>
              ) : (
                filteredQueue.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-highlight/30 transition-colors group">
                    <td className="py-3.5 px-4 font-mono font-semibold text-foreground">
                      {item.id}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <span className="font-semibold text-foreground block">{item.applicantName}</span>
                        <span className="text-[11px] text-foreground-muted">{item.sectorTag}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <span className="font-mono font-semibold text-foreground block">
                          {formatCurrency(item.requestedAmount)}
                        </span>
                        <span className="text-[10px] text-foreground-muted">{item.purpose}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 max-w-xs">
                      <span className="text-foreground-secondary text-xs block truncate" title={item.triggerReason}>
                        {item.triggerReason}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <StatusBadge status={item.status} />
                        {item.assessment && (
                          <div>
                            <RiskBadge
                              riskLevel={item.assessment.riskLevel}
                              showIcon={false}
                              className="text-[10px] py-0 px-2"
                            />
                          </div>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Link href={`/admin/applications/${item.id}`}>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="rounded-full text-xs h-7 px-2.5 text-foreground-muted hover:text-foreground"
                          >
                            Dossier
                          </Button>
                        </Link>

                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleOpenReview(item)}
                          className="rounded-full text-xs h-7 px-3 font-semibold shadow-xs cursor-pointer"
                        >
                          Review
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 8. INTERACTIVE HUMAN-IN-THE-LOOP REVIEW MODAL */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-xl w-full p-6 sm:p-7 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between pb-3 border-b border-border">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-foreground">Reviewer Action</h3>
                  <Badge variant="outline" className="font-mono text-xs">
                    {selectedCase.id}
                  </Badge>
                </div>
                <p className="text-xs text-foreground-muted">
                  Record human-in-the-loop qualitative assessment or verification items.
                </p>
              </div>

              <button
                onClick={() => setSelectedCase(null)}
                className="text-foreground-muted hover:text-foreground p-1 rounded-lg cursor-pointer"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* Applicant Summary */}
            <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-foreground-muted">Applicant</span>
                <span className="font-semibold text-foreground">{selectedCase.applicantName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-foreground-muted">Requested Capital</span>
                <span className="font-mono font-semibold text-foreground">
                  {formatCurrency(selectedCase.requestedAmount)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-foreground-muted">Trigger / Flag</span>
                <span className="text-foreground-secondary font-medium">{selectedCase.triggerReason}</span>
              </div>
            </div>

            {/* Review Form */}
            <form onSubmit={handleRecordReviewOutcome} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground block">
                  Reviewer Action Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'MANUAL_REVIEW', label: 'Manual Review' },
                    { id: 'REQUEST_VERIFICATION', label: 'Request Verify' },
                    { id: 'RECORD_OUTCOME', label: 'Record Outcome' },
                  ].map((act) => (
                    <button
                      key={act.id}
                      type="button"
                      onClick={() => setReviewAction(act.id as ReviewActionType)}
                      className={`p-2 rounded-xl text-xs font-semibold border text-center transition-all cursor-pointer ${
                        reviewAction === act.id
                          ? 'border-[#472393] bg-[#472393] text-white shadow-xs dark:border-foreground dark:bg-foreground dark:text-background'
                          : 'border-border bg-surface-highlight text-foreground-muted hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                      }`}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground block">
                  Reviewer Decision & Rationale Notes
                </label>
                <textarea
                  required
                  rows={4}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Record qualitative rationale on volatility rebound, micro-obligations, or supplementary items required..."
                  className="w-full text-xs p-3 rounded-xl bg-surface-highlight/30 border border-border text-foreground focus:outline-none focus:border-[#472393] dark:focus:border-foreground leading-relaxed resize-none"
                />
              </div>

              {reviewError && (
                <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="size-4 shrink-0" />
                  <span>{reviewError}</span>
                </div>
              )}

              {reviewSuccess && (
                <div className="p-3 rounded-xl bg-surface-highlight border border-border text-foreground text-xs flex items-center gap-2">
                  <CheckCircle2 className="size-4 shrink-0" />
                  <span>Review outcome recorded to PostgreSQL audit ledger successfully.</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={isSubmitting}
                  onClick={() => setSelectedCase(null)}
                  className="rounded-full text-xs text-foreground-muted hover:text-foreground"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="default"
                  size="sm"
                  disabled={isSubmitting}
                  className="rounded-full text-xs font-semibold gap-1.5 shadow-xs cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" /> Saving...
                    </>
                  ) : (
                    <>
                      <Send className="size-3.5" /> Save Audit Record
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 9. UNDERWRITER GOVERNANCE & REGULATORY FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Alternative Credit Review Governance Notice
          </span>
          <p>
            PARAKH functions strictly as an explainable risk evaluation intelligence engine for partner financial institutions. Credit Reviewers record qualitative review notes and verification items in adherence with institutional credit risk policy. Automated credit approval/rejection is disabled in accordance with human-in-the-loop statutory principles.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
