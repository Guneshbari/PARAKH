'use client';

import React, { useState } from 'react';
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
import {
  mockPortfolioAnalytics,
  mockScoreDistributionBuckets,
  mockPipelineStages,
  mockOperationalAlerts,
  mockPriorityReviewQueue,
} from '@/data/mock/admin';
import { formatCurrency } from '@/lib/utils';
import type { ReviewActionType, UnderwriterReviewOutcome } from '@parakh/types';

export default function AdminDashboardPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Interactive review modal/drawer state
  const [selectedCase, setSelectedCase] = useState<
    (typeof mockPriorityReviewQueue)[0] | null
  >(null);
  const [reviewAction, setReviewAction] =
    useState<ReviewActionType>('MANUAL_REVIEW');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSuccess, setReviewSuccess] = useState(false);
  const [activeQueue, setActiveQueue] = useState(mockPriorityReviewQueue);

  const stats = mockPortfolioAnalytics;

  // Filter priority queue
  const filteredQueue = activeQueue.filter((item) => {
    const matchesSearch =
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.applicantName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.purpose.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.triggerReason.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesFilter =
      statusFilter === 'ALL' ||
      (statusFilter === 'REVIEW' && item.status === 'MANUAL_REVIEW_REQUIRED') ||
      (statusFilter === 'VALIDATION' && item.status === 'DATA_VALIDATION');

    return matchesSearch && matchesFilter;
  });

  const handleOpenReview = (item: (typeof mockPriorityReviewQueue)[0]) => {
    setSelectedCase(item);
    setReviewNotes(item.review?.decisionNotes || '');
    setReviewAction(item.review?.action || 'MANUAL_REVIEW');
    setReviewSuccess(false);
  };

  const handleRecordReviewOutcome = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;

    const outcome: UnderwriterReviewOutcome = {
      status: reviewAction === 'RECORD_OUTCOME' ? 'OUTCOME_RECORDED' : 'MANUAL_REVIEW_IN_PROGRESS',
      action: reviewAction,
      decisionNotes: reviewNotes || 'Underwriter review notes recorded.',
      underwriterName: 'Priya Sharma (Senior Risk Underwriter)',
      underwriterId: 'UW-402',
      recordedAt: new Date().toISOString(),
    };

    setActiveQueue((prev) =>
      prev.map((c) =>
        c.id === selectedCase.id
          ? {
              ...c,
              status: reviewAction === 'RECORD_OUTCOME' ? 'REVIEW_COMPLETED' : c.status,
              review: outcome,
            }
          : c
      )
    );

    setReviewSuccess(true);
    setTimeout(() => {
      setSelectedCase(null);
      setReviewSuccess(false);
    }, 1500);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & OPERATIONAL STATUS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Underwriter Risk Cockpit
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              Portfolio Resilient
            </Badge>
            <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
              v2.4-volatility
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Portfolio alternative credit intelligence, cyclical income volatility monitoring, and priority human-in-the-loop review queue.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-xl gap-1.5 text-xs text-muted-foreground hover:text-white"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>

          <a href="#review-queue">
            <Button
              variant="default"
              size="sm"
              className="rounded-xl gap-1.5 text-xs font-bold shadow-lg shadow-teal-500/10"
            >
              <UserCheck className="size-3.5" />
              <span>Review Queue ({activeQueue.filter(q => q.status === 'MANUAL_REVIEW_REQUIRED').length} Pending)</span>
            </Button>
          </a>
        </div>
      </div>

      {/* 2. PORTFOLIO HIGH-LEVEL KPIS (NO AUTOMATED LOAN APPROVAL RATES) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Evaluated Borrowers"
          value={stats.totalEvaluated}
          pillLabel="+12.4% MoM"
          pillVariant="mint"
          subtext="Informal & gig economy applicants"
          icon={Users}
        />

        <MetricCard
          title="Portfolio Average Score"
          value={stats.averageScore}
          suffix=" / 850"
          pillLabel="+4 pts Stability"
          pillVariant="lavender"
          subtext="Alternative volatility scoring engine"
          icon={TrendingUp}
        />

        <MetricCard
          title="Avg. Repayment Difficulty"
          value={stats.averageRiskDifficulty}
          suffix="%"
          pillLabel="-1.8% Improving"
          pillVariant="mint"
          subtext="Estimated repayment stress indicator"
          icon={Activity}
        />

        <MetricCard
          title="Assessment Completion Rate"
          value={stats.assessmentCompletionRate}
          suffix="%"
          pillLabel="91.8% Verified Feeds"
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
            className="p-4 rounded-2xl bg-[#0A162E] border border-white/[0.08] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <div className="size-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0 mt-0.5 text-cyan-300">
                <AlertCircle className="size-4" />
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold text-white">{alert.title}</h4>
                  <Badge variant="outline" className="text-[9px] py-0 px-1.5 uppercase font-mono">
                    {alert.category.replace(/_/g, ' ')}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {alert.message}
                </p>
              </div>
            </div>

            <span className="text-[11px] font-mono text-muted-foreground shrink-0 self-end sm:self-center">
              {alert.timestamp}
            </span>
          </div>
        ))}
      </div>

      {/* 4. RISK DISTRIBUTION & EVALUATION PIPELINE FUNNEL */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Approved Risk Level Distribution */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="size-4 text-teal-400" />
                Portfolio Risk Tier Distribution
              </h3>
              <p className="text-xs text-muted-foreground">
                Categorized by approved PARAKH alternative risk classifications.
              </p>
            </div>
            <span className="text-xs font-mono text-muted-foreground">
              {stats.totalEvaluated.toLocaleString()} Total
            </span>
          </div>

          {/* Segmented Progress Bar */}
          <div className="w-full h-3 rounded-full bg-white/[0.05] overflow-hidden flex">
            <div
              style={{ width: `${(stats.riskDistribution.lowerRiskCount / stats.totalEvaluated) * 100}%` }}
              className="bg-emerald-400 h-full"
              title="LOWER ESTIMATED RISK"
            />
            <div
              style={{ width: `${(stats.riskDistribution.moderateRiskCount / stats.totalEvaluated) * 100}%` }}
              className="bg-amber-400 h-full"
              title="MODERATE ESTIMATED RISK"
            />
            <div
              style={{ width: `${(stats.riskDistribution.higherRiskCount / stats.totalEvaluated) * 100}%` }}
              className="bg-red-400 h-full"
              title="HIGHER ESTIMATED RISK"
            />
            <div
              style={{ width: `${(stats.riskDistribution.manualReviewCount / stats.totalEvaluated) * 100}%` }}
              className="bg-purple-400 h-full"
              title="INSUFFICIENT EVIDENCE / MANUAL REVIEW"
            />
          </div>

          {/* Breakdown Rows */}
          <div className="space-y-3 pt-1 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2.5">
                <span className="size-2 rounded-full bg-emerald-400" />
                <span className="font-semibold text-white">LOWER ESTIMATED RISK</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-muted-foreground">
                  {stats.riskDistribution.lowerRiskCount.toLocaleString()}
                </span>
                <span className="font-mono font-bold text-emerald-300 w-12 text-right">
                  {((stats.riskDistribution.lowerRiskCount / stats.totalEvaluated) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2.5">
                <span className="size-2 rounded-full bg-amber-400" />
                <span className="font-semibold text-white">MODERATE ESTIMATED RISK</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-muted-foreground">
                  {stats.riskDistribution.moderateRiskCount.toLocaleString()}
                </span>
                <span className="font-mono font-bold text-amber-300 w-12 text-right">
                  {((stats.riskDistribution.moderateRiskCount / stats.totalEvaluated) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2.5">
                <span className="size-2 rounded-full bg-red-400" />
                <span className="font-semibold text-white">HIGHER ESTIMATED RISK</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-muted-foreground">
                  {stats.riskDistribution.higherRiskCount.toLocaleString()}
                </span>
                <span className="font-mono font-bold text-red-300 w-12 text-right">
                  {((stats.riskDistribution.higherRiskCount / stats.totalEvaluated) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2.5">
                <span className="size-2 rounded-full bg-purple-400" />
                <span className="font-semibold text-white">INSUFFICIENT EVIDENCE / MANUAL REVIEW</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-muted-foreground">
                  {stats.riskDistribution.manualReviewCount.toLocaleString()}
                </span>
                <span className="font-mono font-bold text-purple-300 w-12 text-right">
                  {((stats.riskDistribution.manualReviewCount / stats.totalEvaluated) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Right: Application Pipeline Funnel */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="size-4 text-teal-400" />
                Evaluation Pipeline & Throughput
              </h3>
              <p className="text-xs text-muted-foreground">
                Lifecycle progression from intake registration to underwriting queue.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              94.2% Synthesized
            </Badge>
          </div>

          <div className="space-y-4 pt-1">
            {mockPipelineStages.map((stage, idx) => {
              const percentage = ((stage.count / stats.totalEvaluated) * 100).toFixed(1);
              return (
                <div key={stage.id} className="space-y-1.5">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-white flex items-center gap-2">
                      <span className="font-mono text-teal-400 text-[11px]">0{idx + 1}</span>
                      {stage.name}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">{stage.subtext}</span>
                      <span className="font-mono font-bold text-white">
                        {stage.count.toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="w-full h-2 rounded-full bg-white/[0.04] overflow-hidden">
                    <div
                      style={{ width: `${percentage}%` }}
                      className={`h-full rounded-full transition-all duration-500 ${
                        idx === 4 ? 'bg-purple-400' : 'bg-teal-400'
                      }`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* 5. VISUAL ANALYTICS: MONTHLY INTAKE & SCORE STABILITY */}
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-white/[0.06]">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <TrendingUp className="size-4 text-teal-400" />
              Monthly Volume & Score Stability Trend (6 Months)
            </h3>
            <p className="text-xs text-muted-foreground">
              Compares applicant volume growth against alternative score resilience across seasonal cycles.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2.5 rounded-sm bg-teal-400/80" /> Volume
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2 rounded-full bg-[#C4B5FD]" /> Avg Score
            </span>
          </div>
        </div>

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={stats.monthlyVolume}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="month"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
              />
              <YAxis
                yAxisId="left"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                domain={[0, 3500]}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#C4B5FD"
                fontSize={11}
                tickLine={false}
                domain={[650, 800]}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-[#0E1F3D] p-3 rounded-xl border border-white/[0.1] shadow-xl text-xs space-y-1">
                        <span className="font-bold text-white block">{label}</span>
                        <span className="text-teal-300 font-mono block">
                          Intake: {payload[0]?.value} evaluations
                        </span>
                        <span className="text-[#C4B5FD] font-mono block">
                          Average Score: {payload[1]?.value} / 850
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
                fill="#2DD4BF"
                opacity={0.7}
                radius={[6, 6, 0, 0]}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avgScore"
                stroke="#C4B5FD"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#C4B5FD' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 6. SECTOR VOLATILITY & SCORE BUCKETS (TWO COLUMNS) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector Volatility Comparison */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Building2 className="size-4 text-teal-400" />
                Sector Volatility & Shock Rebound
              </h3>
              <p className="text-xs text-muted-foreground">
                Observed recovery velocity and volatility index by gig worker segment.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-1">
            {stats.volatilityTrendsBySector.map((s) => (
              <div
                key={s.sector}
                className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-2"
              >
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-white">{s.sector}</span>
                  <span className="font-mono text-muted-foreground text-[11px]">
                    {s.applicantCount.toLocaleString()} Applicants
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div className="p-2 rounded-xl bg-white/[0.02]">
                    <span className="text-[10px] text-muted-foreground block">
                      Avg Shock Recovery Rate
                    </span>
                    <span className="font-mono font-bold text-teal-300">
                      {(s.avgRecoveryRate * 100).toFixed(0)}% (10-14 days)
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-white/[0.02]">
                    <span className="text-[10px] text-muted-foreground block">
                      Income Volatility Index
                    </span>
                    <span className="font-mono font-bold text-amber-300">
                      {s.volatilityIndex.toFixed(2)} (Controlled)
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Alternative Score Distribution Buckets */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="size-4 text-teal-400" />
                Alternative Score Distribution
              </h3>
              <p className="text-xs text-muted-foreground">
                Distribution of borrower scores across volatility-calibrated tiers.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px] font-mono">
              Mean: 718
            </Badge>
          </div>

          <div className="space-y-3 pt-1">
            {mockScoreDistributionBuckets.map((bucket) => (
              <div
                key={bucket.range}
                className="p-3 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-1.5 text-xs"
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-white">{bucket.range}</span>
                    <span className="text-muted-foreground text-[11px]">• {bucket.label}</span>
                  </div>
                  <RiskBadge riskLevel={bucket.riskTier} showIcon={false} className="text-[10px] py-0 px-2" />
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full bg-white/[0.04] overflow-hidden">
                    <div
                      style={{ width: `${bucket.percentage}%` }}
                      className="h-full rounded-full bg-teal-400"
                    />
                  </div>
                  <span className="font-mono font-semibold text-slate-300 w-16 text-right">
                    {bucket.count.toLocaleString()} ({bucket.percentage}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 7. PRIORITY UNDERWRITER REVIEW QUEUE */}
      <Card id="review-queue" className="p-6 bg-[#0A162E] border-white/[0.08] space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-white/[0.06]">
          <div className="space-y-0.5">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <UserCheck className="size-4 text-teal-400" />
              Priority Underwriter Review Queue
            </h2>
            <p className="text-xs text-muted-foreground">
              Cases flagged for human underwriter scrutiny due to non-standard volatility, seasonal weather, or single-platform concentration.
            </p>
          </div>

          {/* Search & Filter */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-full sm:w-56">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search queue..."
                className="pl-9 h-8 text-xs rounded-xl bg-white/[0.03]"
              />
            </div>

            <div className="flex items-center gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
              {[
                { id: 'ALL', label: 'All Cases' },
                { id: 'REVIEW', label: 'Manual Review' },
                { id: 'VALIDATION', label: 'Data Validation' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium cursor-pointer transition-all ${
                    statusFilter === f.id
                      ? 'bg-teal-400 text-slate-950 font-bold'
                      : 'text-muted-foreground hover:text-white'
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
            <thead className="bg-white/[0.02] border-b border-white/[0.06] text-muted-foreground font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Application ID</th>
                <th className="py-3 px-4">Applicant & Sector</th>
                <th className="py-3 px-4">Requested Capital</th>
                <th className="py-3 px-4">Review Trigger</th>
                <th className="py-3 px-4">Status & Risk</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filteredQueue.map((item) => (
                <tr key={item.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="py-3.5 px-4 font-mono font-bold text-teal-300">
                    {item.id}
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="space-y-0.5">
                      <span className="font-bold text-white block">{item.applicantName}</span>
                      <span className="text-[11px] text-muted-foreground">{item.sectorTag}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="space-y-0.5">
                      <span className="font-mono font-bold text-white block">
                        {formatCurrency(item.requestedAmount)}
                      </span>
                      <span className="text-[10px] text-muted-foreground">{item.purpose}</span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 max-w-xs">
                    <span className="text-slate-300 text-xs block truncate" title={item.triggerReason}>
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
                      <Link href={`/user/applications/${item.id}`}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="rounded-xl text-xs h-8 px-2.5 text-muted-foreground hover:text-white"
                        >
                          Lifecycle
                        </Button>
                      </Link>

                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleOpenReview(item)}
                        className="rounded-xl text-xs h-8 px-3 font-semibold shadow-sm"
                      >
                        Review
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 8. INTERACTIVE HUMAN-IN-THE-LOOP REVIEW MODAL */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0A162E] border border-white/[0.1] rounded-2xl max-w-xl w-full p-6 sm:p-7 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start justify-between pb-3 border-b border-white/[0.08]">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-white">Underwriter Review Action</h3>
                  <Badge variant="outline" className="font-mono text-xs">
                    {selectedCase.id}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Record human-in-the-loop qualitative assessment or verification items.
                </p>
              </div>

              <button
                onClick={() => setSelectedCase(null)}
                className="text-muted-foreground hover:text-white p-1 rounded-lg cursor-pointer"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* Applicant Summary */}
            <div className="p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Applicant</span>
                <span className="font-bold text-white">{selectedCase.applicantName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Requested Capital</span>
                <span className="font-mono font-bold text-teal-300">
                  {formatCurrency(selectedCase.requestedAmount)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Trigger / Flag</span>
                <span className="text-amber-300 font-medium">{selectedCase.triggerReason}</span>
              </div>
            </div>

            {/* Review Form */}
            <form onSubmit={handleRecordReviewOutcome} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-white block">
                  Underwriter Action Type
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
                          ? 'border-teal-400 bg-teal-500/10 text-teal-300 shadow-sm'
                          : 'border-white/[0.08] bg-white/[0.02] text-muted-foreground hover:text-white'
                      }`}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-white block">
                  Underwriter Decision & Rationale Notes
                </label>
                <textarea
                  required
                  rows={4}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Record qualitative rationale on volatility rebound, micro-obligations, or supplementary items required..."
                  className="w-full text-xs p-3 rounded-xl bg-white/[0.03] border border-white/[0.1] text-white focus:outline-none focus:border-teal-400 leading-relaxed resize-none"
                />
              </div>

              {reviewSuccess && (
                <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="size-4 shrink-0" />
                  <span>Review outcome recorded to audit ledger successfully.</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedCase(null)}
                  className="rounded-xl text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="default"
                  size="sm"
                  className="rounded-xl text-xs font-bold gap-1.5 shadow-lg shadow-teal-500/10"
                >
                  <Send className="size-3.5" /> Save Audit Record
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 9. UNDERWRITER GOVERNANCE & REGULATORY FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-muted-foreground flex items-start gap-3">
        <Info className="size-4 text-teal-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-300 block">
            Alternative Credit Underwriting Governance Notice
          </span>
          <p>
            PARAKH functions strictly as an explainable risk evaluation intelligence engine for partner financial institutions. Underwriters record qualitative review notes and verification items in adherence with institutional credit risk policy. Automated credit approval/rejection is disabled in accordance with human-in-the-loop statutory principles.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
