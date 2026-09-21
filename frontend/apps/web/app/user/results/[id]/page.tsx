'use client';

import React, { use } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Share2,
  Printer,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { CreditScoreCard } from '@/components/shared/CreditScoreCard';
import { AIInsightCard } from '@/components/shared/AIInsightCard';
import { FeatureContributionCard } from '@/components/shared/FeatureContributionCard';
import { CashflowVolatilityChart } from '@/components/shared/CashflowVolatilityChart';
import { mockUserAssessment } from '@/data/mock/user';

interface ResultPageProps {
  params: Promise<{ id: string }>;
}

export default function CreditAssessmentResultPage({ params }: ResultPageProps) {
  const { id } = use(params);
  const assessment = mockUserAssessment;

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY BAR & BREADCRUMB */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div className="flex items-center gap-3">
          <Link href="/user/dashboard">
            <Button variant="outline" size="sm" className="rounded-full gap-1 text-xs px-4">
              <ArrowLeft className="size-3.5" /> Back to Dashboard
            </Button>
          </Link>
          <span className="text-xs text-muted-foreground font-mono">
            Report Reference: {id.toUpperCase()}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-muted-foreground hover:text-white px-3.5"
          >
            <Printer className="size-3.5" /> Print Dossier
          </Button>
          <Button
            variant="pillOutline"
            size="sm"
            className="rounded-full gap-1.5 text-xs px-3.5"
          >
            <Share2 className="size-3.5" /> Share Report
          </Button>
        </div>
      </div>

      {/* 2. HERO ASSESSMENT SCORE DISPLAY */}
      <section className="space-y-2">
        <CreditScoreCard assessment={assessment} />
      </section>

      {/* 3. CONTEXTUAL AI RISK EXPLANATION */}
      <section>
        <AIInsightCard
          insight="Your weekly earnings fluctuate between ₹8,000 and ₹15,500 due to natural gig peak hours, but your 98% utility punctuality and rapid 10-day recovery velocity confirm strong repayment capacity."
          detail="Traditional bureaus penalize earnings dips as high risk. PARAKH's explainable model verified that you absorbed 3 cyclical monsoon shocks over the past 6 months without missing any micro-obligations."
          actionLabel="View Methodology"
        />
      </section>

      {/* 4. WHY THIS ASSESSMENT? (POSITIVE VS ATTENTION FACTORS) */}
      <section className="space-y-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Sparkles className="size-3.5 text-teal-400" />
            <span>Explainable Evaluation Drivers</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Why this assessment?
          </h2>
          <p className="text-xs text-muted-foreground">
            Clear, non-technical translation of the alternative indicators that contributed to your score.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Positive Factors */}
          <Card className="space-y-4 p-6 bg-teal-950/15 border-teal-500/25">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-emerald-300 uppercase tracking-wider">
                  Key Positive Factors (Strengths)
                </h3>
              </div>
              <Badge variant="mint" className="text-[10px]">High Impact</Badge>
            </div>

            <ul className="space-y-3.5 text-xs text-slate-200">
              <li className="space-y-1">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-emerald-400" />
                  <span>Repayment Reliability (98% On-Time)</span>
                </div>
                <p className="text-muted-foreground leading-relaxed pl-3">
                  Consistent on-time settlement of mobile recharges, LPG gas, and electricity bills across 12 consecutive billing cycles.
                </p>
              </li>

              <li className="space-y-1">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-emerald-400" />
                  <span>Resilient Shock Recovery (10 Days)</span>
                </div>
                <p className="text-muted-foreground leading-relaxed pl-3">
                  Historical data proves that your earnings bounce back to baseline within 10–14 days following monsoon or vehicle maintenance dips.
                </p>
              </li>

              <li className="space-y-1">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-emerald-400" />
                  <span>Manageable Debt Burden (&lt; 35%)</span>
                </div>
                <p className="text-muted-foreground leading-relaxed pl-3">
                  Current fixed monthly commitments represent less than 35% of your average weekly inflow, leaving adequate disposable cushion.
                </p>
              </li>
            </ul>
          </Card>

          {/* Attention Factors */}
          <Card className="space-y-4 p-6 bg-amber-950/15 border-amber-500/25">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-amber-400" />
                <h3 className="text-sm font-bold text-amber-300 uppercase tracking-wider">
                  Attention Factors (Improvement Areas)
                </h3>
              </div>
              <Badge variant="riskModerate" className="text-[10px]">Monitored</Badge>
            </div>

            <ul className="space-y-3.5 text-xs text-slate-200">
              <li className="space-y-1">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-amber-400" />
                  <span>Seasonal Weather Volatility</span>
                </div>
                <p className="text-muted-foreground leading-relaxed pl-3">
                  During peak monsoon weeks, delivery volume dipped by 35%. While recovery was swift, weather dependency remains an active monitoring factor.
                </p>
              </li>

              <li className="space-y-1">
                <div className="font-semibold text-white flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-amber-400" />
                  <span>Limited Formal Credit History</span>
                </div>
                <p className="text-muted-foreground leading-relaxed pl-3">
                  Absence of legacy bank trade-lines. Compensated by alternative UPI volume, but limits initial automated score ceiling.
                </p>
              </li>
            </ul>
          </Card>
        </div>
      </section>

      {/* 5. VISUAL FEATURE CONTRIBUTION BREAKDOWN (SHAP TRANSLATION) */}
      <section className="space-y-4">
        <FeatureContributionCard contributions={assessment.featureContributions} />
      </section>

      {/* 6. VERIFIED CASHFLOW CYCLE TRACKING */}
      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-white tracking-tight">
            Verified Inflow & Shock Resilience Record
          </h2>
          <p className="text-xs text-muted-foreground">
            The historical 12-week cashflow rhythm verifying that volatility did not compromise obligation punctuality.
          </p>
        </div>

        <CashflowVolatilityChart
          recoveryRate={Math.round(assessment.volatilityProfile.recoveryRateAfterLowIncome * 100)}
          title="12-Week Cashflow Waveform & Rebound Highlights"
        />
      </section>

      {/* 7. ACTIONABLE BORROWER RECOMMENDATIONS (NO LENDING ENGINE) */}
      <section className="space-y-4">
        <Card className="p-7 space-y-5 bg-[#0A162E] border border-white/[0.08]">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2">
              <TrendingUp className="size-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                Actionable Recommendations to Strengthen Your Score
              </h2>
            </div>
            <Badge variant="mint" className="text-xs">Next Steps</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-xs">
            <div className="space-y-2 p-4 rounded-2xl bg-[#0E1F3D] border border-white/[0.08]">
              <span className="font-bold text-white flex items-center gap-2">
                <span className="size-5 rounded-full bg-cyan-400/20 text-cyan-300 flex items-center justify-center text-[10px]">
                  1
                </span>
                Maintain UPI Frequency
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Continue receiving customer settlements via verified UPI QR to maintain data confidence above 85%.
              </p>
            </div>

            <div className="space-y-2 p-4 rounded-2xl bg-[#0E1F3D] border border-white/[0.08]">
              <span className="font-bold text-white flex items-center gap-2">
                <span className="size-5 rounded-full bg-cyan-400/20 text-cyan-300 flex items-center justify-center text-[10px]">
                  2
                </span>
                Link Secondary Streams
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Connecting your Urban Company account alongside Swiggy demonstrates diversified gig resilience.
              </p>
            </div>

            <div className="space-y-2 p-4 rounded-2xl bg-[#0E1F3D] border border-white/[0.08]">
              <span className="font-bold text-white flex items-center gap-2">
                <span className="size-5 rounded-full bg-cyan-400/20 text-cyan-300 flex items-center justify-center text-[10px]">
                  3
                </span>
                Preserve Debt Cushion
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Keep fixed monthly commitments below 35% of weekly earnings to safeguard against future weather shocks.
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-muted-foreground">
              <ShieldCheck className="size-4 text-cyan-400" />
              <span>Assessment valid for 90 days from timestamp {new Date(assessment.assessedAt).toLocaleDateString('en-IN')}.</span>
            </div>

            <Link href="/user/dashboard">
              <Button variant="lime" size="sm" className="gap-2 font-bold px-4">
                <span>Return to Dashboard</span>
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          </div>
        </Card>
      </section>
    </PageTransition>
  );
}
