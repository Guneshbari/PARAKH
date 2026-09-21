'use client';

import React, { useState } from 'react';
import {
  Activity,
  TrendingUp,
  ShieldCheck,
  Building2,
  Printer,
  Info,
  Clock,
  Sparkles,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
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
  mockPortfolioAnalytics,
  mockSectorRiskStackedData,
  mockShockRecoveryCurveData,
} from '@/data/mock/admin';

export default function AdminAnalyticsPage() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [timeRange, setTimeRange] = useState<string>('90D');
  const stats = mockPortfolioAnalytics;

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
        home: '#3B82F6',
        ride: '#6366F1',
        bench: '#94A3B8',
      };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & FILTER STRIP */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Portfolio Risk & Volatility Analytics
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              Cohort Telemetry Live
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Deep-dive cohort telemetry, recovery velocity dynamics, sector-wise risk segmentation, and long-term assessment stability.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Time Range Selector */}
          <div className="flex items-center bg-surface-highlight p-1 rounded-full border border-border">
            {[
              { id: '30D', label: '30D' },
              { id: '90D', label: '90D' },
              { id: '6M', label: '6M' },
              { id: 'ALL', label: 'All Time' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTimeRange(t.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
                  timeRange === t.id
                    ? 'bg-foreground text-background font-semibold shadow-xs'
                    : 'text-foreground-muted hover:text-foreground'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Analytics
          </Button>
        </div>
      </div>

      {/* 2. PORTFOLIO RESILIENCE KPIS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Portfolio Volatility Index"
          value={0.29}
          format={(n) => n.toFixed(2)}
          pillLabel="Controlled Variance"
          pillVariant="mint"
          subtext="Coefficient of weekly variation"
          icon={Activity}
        />

        <MetricCard
          title="Mean Shock Rebound Velocity"
          value={11.4}
          suffix=" Days"
          format={(n) => n.toFixed(1)}
          pillLabel="Rapid Rebound"
          pillVariant="secondary"
          subtext="Days to return to 90%+ baseline"
          icon={Clock}
        />

        <MetricCard
          title="Micro-Obligation Punctuality"
          value={96.8}
          suffix="%"
          pillLabel="24-Cycle Punctual"
          pillVariant="mint"
          subtext="BBPS utility & recharge cadence"
          icon={ShieldCheck}
        />

        <MetricCard
          title="Disposable Inflow Cushion"
          value={89.2}
          suffix="%"
          pillLabel="Safe Debt Buffer"
          pillVariant="mint"
          subtext="Residual inflow after micro-commitments"
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
            <p className="text-xs text-foreground-muted">
              Segmented risk volume showing proportion of Lower, Moderate, Higher, and Manual Review cases by worker cohort.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2.5 rounded-sm bg-foreground" /> Lower Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2.5 rounded-sm bg-foreground-secondary opacity-70" /> Moderate Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2.5 rounded-sm bg-foreground-muted opacity-50" /> Higher Risk
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted">
              <span className="size-2.5 rounded-sm bg-foreground-muted opacity-30" /> Manual Review
            </span>
          </div>
        </div>

        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={mockSectorRiskStackedData}
              margin={{ top: 15, right: 10, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
              <XAxis dataKey="sector" stroke={chartAxisColor} fontSize={11} tickLine={false} />
              <YAxis stroke={chartAxisColor} fontSize={11} tickLine={false} />
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
      </Card>

      {/* 4. VISUALIZATION 2: SHOCK RECOVERY VELOCITY REBOUND CURVES */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Clock className="size-4 text-foreground-secondary" />
              Income Shock Rebound Trajectory Curves (Days 0 to 21)
            </h3>
            <p className="text-xs text-foreground-muted">
              Tracks normalized post-shock earning recovery against traditional salaried baseline expectations.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-foreground font-medium">
              <span className="size-2 rounded-full bg-foreground" /> Food Delivery
            </span>
            <span className="flex items-center gap-1.5 text-foreground-secondary font-medium">
              <span className="size-2 rounded-full bg-foreground-secondary" /> Home Services
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted font-medium">
              <span className="size-2 rounded-full bg-foreground-muted" /> Ride Logistics
            </span>
            <span className="flex items-center gap-1.5 text-foreground-muted/60 font-medium">
              <span className="size-2 rounded-full bg-foreground-muted/60" /> Formal Benchmark
            </span>
          </div>
        </div>

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={mockShockRecoveryCurveData}
              margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
              <XAxis dataKey="day" stroke={chartAxisColor} fontSize={11} tickLine={false} />
              <YAxis
                stroke={chartAxisColor}
                fontSize={11}
                tickLine={false}
                domain={[30, 110]}
                unit="%"
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-surface p-3 rounded-xl border border-border shadow-xl text-xs space-y-1 text-foreground">
                        <span className="font-semibold text-foreground block">{label} (Recovery Level)</span>
                        {payload.map((p) => (
                          <div key={p.name} className="flex justify-between gap-4 font-mono">
                            <span className="text-foreground-secondary">{p.name}:</span>
                            <span className="text-foreground font-bold">{p.value}%</span>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Line
                type="monotone"
                dataKey="foodDelivery"
                name="Food Delivery"
                stroke={lineColors.food}
                strokeWidth={2}
                dot={{ r: 3, fill: lineColors.food }}
              />
              <Line
                type="monotone"
                dataKey="homeServices"
                name="Home Services"
                stroke={lineColors.home}
                strokeWidth={2}
                dot={{ r: 3, fill: lineColors.home }}
              />
              <Line
                type="monotone"
                dataKey="rideLogistics"
                name="Ride Logistics"
                stroke={lineColors.ride}
                strokeWidth={2}
                dot={{ r: 3, fill: lineColors.ride }}
              />
              <Line
                type="monotone"
                dataKey="formalBenchmark"
                name="Formal Benchmark"
                stroke={lineColors.bench}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Explainability Callout */}
        <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border text-xs text-foreground-secondary flex items-start gap-2.5">
          <Sparkles className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-foreground block">
              Core PARAKH Methodology Proof: Rapid 10–14 Day Shock Recovery
            </span>
            <p className="text-foreground-muted leading-relaxed">
              Traditional credit models treat sharp week-to-week income drops as insolvency risk. In contrast, PARAKH measures rebound velocity: 93% of observed informal earning shocks in Food Delivery recover to full baseline within 12 days, maintaining flawless micro-obligation discipline.
            </p>
          </div>
        </div>
      </Card>

      {/* 5. DETAILED SECTOR PERFORMANCE COMPARISON GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.volatilityTrendsBySector.map((s) => (
          <Card key={s.sector} className="p-5 bg-surface border-border space-y-3">
            <div className="space-y-0.5">
              <h4 className="text-xs font-semibold text-foreground line-clamp-1">{s.sector}</h4>
              <span className="text-[11px] font-mono text-foreground-muted">
                {s.applicantCount.toLocaleString()} Applicants
              </span>
            </div>

            <div className="space-y-2 text-xs pt-1 border-t border-border">
              <div className="flex justify-between">
                <span className="text-foreground-muted">Recovery Velocity</span>
                <span className="font-mono font-semibold text-foreground">
                  {(s.avgRecoveryRate * 100).toFixed(0)}% (10–14d)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-foreground-muted">Volatility Index</span>
                <span className="font-mono font-semibold text-foreground">
                  {s.volatilityIndex.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-foreground-muted">Verification Rate</span>
                <span className="font-mono text-foreground-secondary">92.4% Verified</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 6. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Portfolio Analytics Governance Notice
          </span>
          <p>
            Portfolio analytics reflect anonymized telemetry aggregated across partner platform APIs and RBI Account Aggregators. PARAKH provides explainable risk intelligence without automated lending decisions.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
