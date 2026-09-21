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
import {
  mockPortfolioAnalytics,
  mockSectorRiskStackedData,
  mockShockRecoveryCurveData,
} from '@/data/mock/admin';

export default function AdminAnalyticsPage() {
  const [timeRange, setTimeRange] = useState<string>('90D');
  const stats = mockPortfolioAnalytics;

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & FILTER STRIP */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Portfolio Risk & Volatility Analytics
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              Cohort Telemetry Live
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Deep-dive cohort telemetry, recovery velocity dynamics, sector-wise risk segmentation, and long-term assessment stability.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Time Range Selector */}
          <div className="flex items-center bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
            {[
              { id: '30D', label: '30D' },
              { id: '90D', label: '90D' },
              { id: '6M', label: '6M' },
              { id: 'ALL', label: 'All Time' },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setTimeRange(t.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  timeRange === t.id
                    ? 'bg-teal-400 text-slate-950 shadow-sm'
                    : 'text-muted-foreground hover:text-white'
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
            className="rounded-xl gap-1.5 text-xs text-muted-foreground hover:text-white"
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
          pillVariant="lavender"
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
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/[0.06]">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Building2 className="size-4 text-teal-400" />
              Risk Classification Distribution Across Gig Sectors
            </h3>
            <p className="text-xs text-muted-foreground">
              Segmented risk volume showing proportion of Lower, Moderate, Higher, and Manual Review cases by worker cohort.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2.5 rounded-sm bg-emerald-400" /> Lower Risk
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2.5 rounded-sm bg-amber-400" /> Moderate Risk
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2.5 rounded-sm bg-red-400" /> Higher Risk
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <span className="size-2.5 rounded-sm bg-purple-400" /> Manual Review
            </span>
          </div>
        </div>

        <div className="h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={mockSectorRiskStackedData}
              margin={{ top: 15, right: 10, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="sector" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    const total = payload.reduce((acc, p) => acc + (Number(p.value) || 0), 0);
                    return (
                      <div className="bg-[#0E1F3D] p-3 rounded-xl border border-white/[0.1] shadow-xl text-xs space-y-1">
                        <span className="font-bold text-white block">{label} ({total.toLocaleString()} Total)</span>
                        {payload.map((p) => (
                          <div key={p.name} className="flex justify-between gap-3 font-mono">
                            <span style={{ color: p.color }}>{p.name}:</span>
                            <span className="text-white">{Number(p.value).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="lowerRisk" name="Lower Estimated Risk" stackId="a" fill="#10B981" radius={[0, 0, 0, 0]} />
              <Bar dataKey="moderateRisk" name="Moderate Estimated Risk" stackId="a" fill="#F59E0B" />
              <Bar dataKey="higherRisk" name="Higher Estimated Risk" stackId="a" fill="#EF4444" />
              <Bar dataKey="manualReview" name="Manual Review Required" stackId="a" fill="#A855F7" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 4. VISUALIZATION 2: SHOCK RECOVERY VELOCITY REBOUND CURVES */}
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-white/[0.06]">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="size-4 text-teal-400" />
              Income Shock Rebound Trajectory Curves (Days 0 to 21)
            </h3>
            <p className="text-xs text-muted-foreground">
              Tracks normalized post-shock earning recovery against traditional salaried baseline expectations.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 text-teal-300 font-medium">
              <span className="size-2 rounded-full bg-teal-400" /> Food Delivery
            </span>
            <span className="flex items-center gap-1.5 text-[#C4B5FD] font-medium">
              <span className="size-2 rounded-full bg-[#C4B5FD]" /> Home Services
            </span>
            <span className="flex items-center gap-1.5 text-amber-300 font-medium">
              <span className="size-2 rounded-full bg-amber-400" /> Ride Logistics
            </span>
            <span className="flex items-center gap-1.5 text-slate-400 font-medium">
              <span className="size-2 rounded-full bg-slate-500" /> Formal Benchmark
            </span>
          </div>
        </div>

        <div className="h-64 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={mockShockRecoveryCurveData}
              margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                domain={[30, 110]}
                unit="%"
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-[#0E1F3D] p-3 rounded-xl border border-white/[0.1] shadow-xl text-xs space-y-1">
                        <span className="font-bold text-white block">{label} (Recovery Level)</span>
                        {payload.map((p) => (
                          <div key={p.name} className="flex justify-between gap-4 font-mono">
                            <span style={{ color: p.color }}>{p.name}:</span>
                            <span className="text-white font-bold">{p.value}%</span>
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
                stroke="#2DD4BF"
                strokeWidth={2.5}
                dot={{ r: 3.5, fill: '#2DD4BF' }}
              />
              <Line
                type="monotone"
                dataKey="homeServices"
                name="Home Services"
                stroke="#C4B5FD"
                strokeWidth={2.5}
                dot={{ r: 3.5, fill: '#C4B5FD' }}
              />
              <Line
                type="monotone"
                dataKey="rideLogistics"
                name="Ride Logistics"
                stroke="#F59E0B"
                strokeWidth={2.5}
                dot={{ r: 3.5, fill: '#F59E0B' }}
              />
              <Line
                type="monotone"
                dataKey="formalBenchmark"
                name="Formal Benchmark"
                stroke="#64748B"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Explainability Callout */}
        <div className="p-3.5 rounded-2xl bg-teal-500/5 border border-teal-500/20 text-xs text-slate-300 flex items-start gap-2.5">
          <Sparkles className="size-4 text-teal-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-bold text-teal-300 block">
              Core PARAKH Methodology Proof: Rapid 10–14 Day Shock Recovery
            </span>
            <p className="text-muted-foreground leading-relaxed">
              Traditional credit models treat sharp week-to-week income drops as insolvency risk. In contrast, PARAKH measures rebound velocity: 93% of observed informal earning shocks in Food Delivery recover to full baseline within 12 days, maintaining flawless micro-obligation discipline.
            </p>
          </div>
        </div>
      </Card>

      {/* 5. DETAILED SECTOR PERFORMANCE COMPARISON GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.volatilityTrendsBySector.map((s) => (
          <Card key={s.sector} className="p-5 bg-[#0A162E] border-white/[0.08] space-y-3">
            <div className="space-y-0.5">
              <h4 className="text-xs font-bold text-white line-clamp-1">{s.sector}</h4>
              <span className="text-[11px] font-mono text-teal-300">
                {s.applicantCount.toLocaleString()} Applicants
              </span>
            </div>

            <div className="space-y-2 text-xs pt-1 border-t border-white/[0.04]">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Recovery Velocity</span>
                <span className="font-mono font-bold text-teal-300">
                  {(s.avgRecoveryRate * 100).toFixed(0)}% (10–14d)
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Volatility Index</span>
                <span className="font-mono text-amber-300 font-bold">
                  {s.volatilityIndex.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Verification Rate</span>
                <span className="font-mono text-slate-200">92.4% Verified</span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 6. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-muted-foreground flex items-start gap-3">
        <Info className="size-4 text-teal-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-300 block">
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
