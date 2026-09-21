'use client';

import React from 'react';
import Link from 'next/link';
import {
  Sparkles,
  PlusCircle,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StaggerList, StaggerItem } from '@/components/motion/StaggerList';
import { MetricCard } from '@/components/shared/MetricCard';
import { CreditScoreCard } from '@/components/shared/CreditScoreCard';
import { AIInsightCard } from '@/components/shared/AIInsightCard';
import { CashflowVolatilityChart } from '@/components/shared/CashflowVolatilityChart';
import { ApplicationCard } from '@/components/shared/ApplicationCard';
import {
  mockBorrowerProfile,
  mockUserAssessment,
  mockUserApplications,
} from '@/data/mock/user';
import { formatCurrency } from '@/lib/utils';

export default function UserDashboardPage() {
  const profile = mockBorrowerProfile;
  const assessment = mockUserAssessment;
  const applications = mockUserApplications;

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-12">
      {/* 1. WELCOME & QUICK ACTION BAR */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/[0.06]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Welcome back, {profile.fullName}
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              Verified Inflows
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>Swiggy Delivery Partner (18 mos)</span>
            <span>•</span>
            <span>Urban Company Partner (8 mos)</span>
            <span>•</span>
            <span>{profile.city}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/user/applications/new">
            <Button variant="lime" className="gap-2 font-bold px-5">
              <PlusCircle className="size-4" />
              <span>New Assessment</span>
            </Button>
          </Link>
          <Link href="/user/results/demo">
            <Button variant="pillOutline" className="gap-1.5 text-xs">
              <span>Full Report</span>
              <ArrowRight className="size-3.5" />
            </Button>
          </Link>
        </div>
      </section>

      {/* 2. HERO ASSESSMENT SCORE & CONTEXTUAL AI CARD */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <CreditScoreCard assessment={assessment} />
        </div>

        <div className="lg:col-span-5 flex flex-col justify-between gap-4">
          <AIInsightCard
            insight="Your income fluctuates naturally due to gig seasonality, yet your repayment consistency across 3 low-earning shock periods remains in the 98th percentile."
            detail="Traditional bureaus heavily penalize off-peak weekly swings. PARAKH evaluates your verified 10-day recovery velocity and timely utility settlements, qualifying you for lower estimated risk."
            actionLabel="View Methodology"
          />

          <Card className="space-y-2.5 p-5 bg-[#0A162E] border-white/[0.08]">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-cyan-400" />
                <span>Alternative Data Health</span>
              </span>
              <span className="font-bold text-cyan-300 font-mono">89% Confident</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              3 alternative financial sources linked: UPI settlements, Swiggy earnings stream, and utility bills.
            </p>
          </Card>
        </div>
      </section>

      {/* 3. KEY VOLATILITY STANDING METRIC CARDS */}
      <section className="space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
          Financial Standing & Volatility Signals
        </h2>

        <StaggerList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StaggerItem>
            <MetricCard
              title="Average Weekly Inflow"
              value={assessment.volatilityProfile.averageWeeklyInflow}
              format={formatCurrency}
              pillLabel="Stable Trend"
              pillVariant="mint"
              subtext="Dual-platform earnings aggregated"
              icon={TrendingUp}
            />
          </StaggerItem>

          <StaggerItem>
            <MetricCard
              title="Repayment Punctuality"
              value={assessment.volatilityProfile.repaymentHistoryRate}
              suffix="%"
              pillLabel="Top 5%"
              pillVariant="mint"
              subtext="Zero missed micro-obligations"
              icon={ShieldCheck}
            />
          </StaggerItem>

          <StaggerItem>
            <MetricCard
              title="Shock Rebound Speed"
              value={10}
              suffix=" Days"
              pillLabel="94% Recovery"
              pillVariant="lavender"
              subtext="Average days to baseline earnings"
              icon={Zap}
            />
          </StaggerItem>

          <StaggerItem>
            <MetricCard
              title="Monthly Debt Load"
              value={assessment.volatilityProfile.existingObligationsMonthly}
              format={formatCurrency}
              pillLabel="Manageable"
              pillVariant="outline"
              subtext="Under 35% of total inflow"
            />
          </StaggerItem>
        </StaggerList>
      </section>

      {/* 4. CASHFLOW VOLATILITY TRACKING CHART */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Weekly Inflow Rhythm & Rebound Curve
          </h2>
          <span className="text-xs text-muted-foreground">Past 12 Weeks Verified</span>
        </div>

        <CashflowVolatilityChart
          recoveryRate={Math.round(assessment.volatilityProfile.recoveryRateAfterLowIncome * 100)}
          title="Verified UPI & Platform Cashflow Consistency"
        />
      </section>

      {/* 5. RECENT APPLICATIONS & ACTIONABLE RECOMMENDATIONS */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Applications List */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Recent Evaluations ({applications.length})
            </h2>
            <Link href="/user/applications" className="text-xs text-cyan-400 hover:underline">
              View all →
            </Link>
          </div>

          <div className="space-y-3">
            {applications.map((app) => (
              <ApplicationCard key={app.id} application={app} />
            ))}
          </div>
        </div>

        {/* Actionable Recommendations Card */}
        <div className="lg:col-span-5 space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
            Actionable Recommendations
          </h2>

          <Card className="space-y-4 p-6 bg-[#0A162E] border-white/[0.08]">
            <div className="flex items-center gap-2 text-xs font-semibold text-cyan-300">
              <Sparkles className="size-4" />
              <span>How to strengthen your evaluation</span>
            </div>

            <ul className="space-y-3 text-xs text-slate-300">
              {assessment.actionableRecommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2.5 leading-relaxed">
                  <span className="size-4 rounded-full bg-cyan-500/15 text-cyan-300 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>

            <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between">
              <span className="text-[11px] text-muted-foreground">
                Updated automatically on new data ingestion
              </span>
              <Link href="/user/profile">
                <span className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                  Manage Feeds <ChevronRight className="size-3" />
                </span>
              </Link>
            </div>
          </Card>
        </div>
      </section>
    </PageTransition>
  );
}
