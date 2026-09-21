'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Activity,
  Zap,
  Scale,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { MotionCard } from '@/components/motion/MotionCard';
import { PageTransition } from '@/components/motion/PageTransition';
import { StaggerList, StaggerItem } from '@/components/motion/StaggerList';
import { CashflowVolatilityChart, type CashflowDataPoint } from '@/components/shared/CashflowVolatilityChart';
import { HeroWaveSystem } from '@/components/landing/HeroWaveSystem';
import { HeroProductPreview } from '@/components/landing/HeroProductPreview';
import { LandingNavbar } from '@/components/landing/LandingNavbar';

// Preset simulation profiles for the interactive methodology explorer
const SIMULATION_PROFILES: Record<
  string,
  {
    role: string;
    description: string;
    score: number;
    riskLevel: 'LOWER_ESTIMATED RISK' | 'MODERATE_ESTIMATED RISK';
    recoveryRate: number;
    difficulty: number;
    confidence: number;
    chartData: CashflowDataPoint[];
    aiInsight: string;
    positiveDriver: string;
  }
> = {
  gig_courier: {
    role: 'Food Delivery Partner (Swiggy / Zomato)',
    description: 'Weekly earnings oscillate heavily between monsoon peak orders and off-peak weekdays.',
    score: 742,
    riskLevel: 'LOWER_ESTIMATED RISK',
    recoveryRate: 94,
    difficulty: 21,
    confidence: 87,
    aiInsight:
      'Natural week-to-week earning variation detected across gig deliveries. Inflow dips recover within 10 days, with 98% on-time micro-utility payments.',
    positiveDriver: 'Consistent 10-day rebound capacity across 3 low-inflow cycles',
    chartData: [
      { week: 'W1', inflow: 11200, obligations: 3500 },
      { week: 'W2', inflow: 13500, obligations: 3500 },
      { week: 'W3', inflow: 14800, obligations: 3500 },
      { week: 'W4', inflow: 6800, obligations: 3500, isDip: true },
      { week: 'W5', inflow: 11400, obligations: 3500, isRecovery: true },
      { week: 'W6', inflow: 13800, obligations: 3500 },
      { week: 'W7', inflow: 15600, obligations: 3500 },
      { week: 'W8', inflow: 7200, obligations: 3500, isDip: true },
      { week: 'W9', inflow: 12100, obligations: 3500, isRecovery: true },
      { week: 'W10', inflow: 14600, obligations: 3500 },
      { week: 'W11', inflow: 16400, obligations: 3500 },
      { week: 'W12', inflow: 15800, obligations: 3500 },
    ],
  },
  kirana_owner: {
    role: 'Local Kirana Store Owner',
    description: 'Bi-monthly inventory restock cycles result in recurring cash outflow spikes and seasonal customer receipts.',
    score: 718,
    riskLevel: 'LOWER_ESTIMATED RISK',
    recoveryRate: 91,
    difficulty: 26,
    confidence: 84,
    aiInsight:
      'Customer UPI inflow exhibits cyclical seasonality tied to month-end salary schedules. Supplier credit repayments are consistently cleared.',
    positiveDriver: 'Strong monthly UPI transaction frequency (180+ receipts/month)',
    chartData: [
      { week: 'W1', inflow: 18500, obligations: 6000 },
      { week: 'W2', inflow: 21000, obligations: 6000 },
      { week: 'W3', inflow: 11200, obligations: 6000, isDip: true },
      { week: 'W4', inflow: 19800, obligations: 6000, isRecovery: true },
      { week: 'W5', inflow: 22400, obligations: 6000 },
      { week: 'W6', inflow: 24100, obligations: 6000 },
      { week: 'W7', inflow: 12000, obligations: 6000, isDip: true },
      { week: 'W8', inflow: 20500, obligations: 6000, isRecovery: true },
      { week: 'W9', inflow: 23200, obligations: 6000 },
      { week: 'W10', inflow: 25800, obligations: 6000 },
      { week: 'W11', inflow: 24200, obligations: 6000 },
      { week: 'W12', inflow: 26100, obligations: 6000 },
    ],
  },
  ride_driver: {
    role: 'Cab / Auto Driver (Uber / Ola)',
    description: 'Daily cashflow subject to vehicle maintenance downtime and platform incentive threshold fluctuations.',
    score: 685,
    riskLevel: 'MODERATE_ESTIMATED RISK',
    recoveryRate: 85,
    difficulty: 34,
    confidence: 82,
    aiInsight:
      'Moderate cashflow volatility driven by a single week maintenance pause. Rebound occurred within 14 days; recommend verification of platform tenure.',
    positiveDriver: '18 months continuous verified tenure on ride-hail platforms',
    chartData: [
      { week: 'W1', inflow: 9800, obligations: 3800 },
      { week: 'W2', inflow: 10400, obligations: 3800 },
      { week: 'W3', inflow: 5200, obligations: 3800, isDip: true },
      { week: 'W4', inflow: 8900, obligations: 3800, isRecovery: true },
      { week: 'W5', inflow: 10100, obligations: 3800 },
      { week: 'W6', inflow: 11200, obligations: 3800 },
      { week: 'W7', inflow: 4800, obligations: 3800, isDip: true },
      { week: 'W8', inflow: 9300, obligations: 3800, isRecovery: true },
      { week: 'W9', inflow: 10800, obligations: 3800 },
      { week: 'W10', inflow: 11400, obligations: 3800 },
      { week: 'W11', inflow: 12100, obligations: 3800 },
      { week: 'W12', inflow: 11600, obligations: 3800 },
    ],
  },
};

export default function HomePage() {
  const [selectedProfileKey, setSelectedProfileKey] = useState<string>('gig_courier');
  const activeProfile = SIMULATION_PROFILES[selectedProfileKey];

  return (
    <PageTransition className="space-y-12 sm:space-y-16 pb-12">
      {/* 1. HERO SECTION (REFERENCE-BASED FINTECH HERO WITH FLOWING MULTICOLOR WAVES) */}
      <section className="relative w-full bg-[#051336] bg-[radial-gradient(ellipse_95%_75%_at_50%_35%,#123AA8_0%,#092472_40%,#051848_75%,#030C22_100%)] overflow-hidden pt-2 pb-10 sm:pb-14">
        {/* Animated Silk Wave System */}
        <HeroWaveSystem />

        {/* Public Landing Navigation Bar */}
        <LandingNavbar />

        {/* Hero Content Container */}
        <div className="relative z-10 mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center pt-8 sm:pt-14 space-y-6">
          {/* Eyebrow Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/15 border border-cyan-400/35 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.2)]">
            <Sparkles className="size-3.5 text-cyan-300" />
            <span className="text-[11px] font-bold uppercase tracking-widest font-mono">
              AI-Powered Credit Assessment
            </span>
          </div>

          {/* Main Editorial Heading */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight text-white leading-[1.08]">
            Credit assessment <br />
            for the{' '}
            <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-violet-400 bg-clip-text text-transparent">
              invisible.
            </span>
          </h1>

          {/* Supporting Copy */}
          <p className="text-base sm:text-lg text-slate-200/90 max-w-2xl mx-auto leading-relaxed">
            PARAKH evaluates financial behavior beyond traditional credit history, using alternative
            data and explainable AI.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 pt-2">
            <Link href="/user/applications/new">
              <Button
                variant="lime"
                size="lg"
                className="gap-2 font-bold px-7 h-12 shadow-[0_10px_25px_rgba(200,244,81,0.25)] hover:shadow-[0_12px_30px_rgba(200,244,81,0.35)] transition-all cursor-pointer"
              >
                <span>Start Assessment</span>
                <ArrowRight className="size-4" />
              </Button>
            </Link>

            <a href="#how-it-works">
              <Button
                variant="pillOutline"
                size="lg"
                className="gap-2 px-7 h-12 transition-all cursor-pointer"
              >
                <Play className="size-3.5 fill-cyan-200 text-cyan-200" />
                <span>How It Works</span>
              </Button>
            </a>
          </div>

          {/* Product / Phone Mockup with Floating Cards */}
          <HeroProductPreview />

          {/* Bottom Trust Statement & Institutional Badges */}
          <div className="pt-6 sm:pt-8 border-t border-white/[0.08] flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-300">
            <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-center sm:text-left">
              <span className="font-semibold text-white">
                Built for transparent, explainable financial assessment.
              </span>
              <div className="flex items-center gap-2 text-[11px] text-cyan-200/80">
                <span className="px-2 py-0.5 rounded-full bg-[#0A162E] border border-white/[0.08]">
                  DPDP Act 2023
                </span>
                <span className="px-2 py-0.5 rounded-full bg-[#0A162E] border border-white/[0.08]">
                  RBI AA Ecosystem
                </span>
                <span className="px-2 py-0.5 rounded-full bg-[#0A162E] border border-white/[0.08]">
                  Fairlearn Audited
                </span>
              </div>
            </div>

            {/* Right pill badge */}
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/25 text-cyan-300 text-[11px] font-medium">
              <Sparkles className="size-3 text-cyan-300" />
              <span>More people. Real incomes. Better credit.</span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THE CORE PARADIGM SHIFT: TRADITIONAL BUREAU VS PARAKH */}
      <section id="how-it-works" className="relative pt-4 sm:pt-6 pb-12 sm:pb-16 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_80%_50%_at_50%_0%,rgba(18,57,166,0.14)_0%,transparent_100%)]" />
        <div className="relative z-10 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <Badge variant="cyan" className="text-xs">Paradigm Shift</Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Why traditional scoring fails the informal economy
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              When legacy scoring models evaluate gig workers, normal weekly variance is misinterpreted as financial instability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            {/* Legacy Bureau Column */}
            <Card className="border border-red-500/20 bg-[#0A162E] space-y-5 p-6 sm:p-7 rounded-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <XCircle className="size-5 text-red-400" />
                  <span className="text-sm font-bold uppercase tracking-wider text-red-300">
                    Traditional Credit Bureaus
                  </span>
                </div>
                <Badge variant="riskHigher">Thin / Zero File</Badge>
              </div>

              <div className="space-y-2">
                <div className="text-3xl font-black text-slate-400 font-mono">
                  - - - / 850
                </div>
                <p className="text-xs text-red-200/80 font-medium">
                  Automatic Rejection or High Risk Surcharge
                </p>
              </div>

              <ul className="space-y-2.5 text-xs text-slate-300 border-t border-red-500/15 pt-4">
                <li className="flex items-start gap-2">
                  <span className="text-red-400 font-bold">•</span>
                  <span>Requires historical formal debt and bureau trade-lines (CIBIL/Experian).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-400 font-bold">•</span>
                  <span>Penalizes income variance: off-peak earning weeks are flagged as high risk.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-400 font-bold">•</span>
                  <span>Zero visibility into UPI transactions, utility punctuality, or platform tenure.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-red-400 font-bold">•</span>
                  <span>Opaque, non-actionable decisions leaving borrowers stranded.</span>
                </li>
              </ul>
            </Card>

            {/* PARAKH Volatility-Aware Column */}
            <Card className="border border-teal-500/30 bg-[#0A162E] space-y-5 p-6 sm:p-7 rounded-2xl shadow-[0_0_25px_rgba(45,212,191,0.06)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-5 text-teal-400" />
                  <span className="text-sm font-bold uppercase tracking-wider text-teal-300">
                    PARAKH Alternative Intelligence
                  </span>
                </div>
                <Badge variant="riskLower">LOWER ESTIMATED RISK</Badge>
              </div>

              <div className="space-y-2">
                <div className="text-3xl font-black text-white font-mono">
                  742 / 850
                </div>
                <p className="text-xs text-teal-300 font-medium">
                  High Confidence • 94% Shock Rebound Demonstrated
                </p>
              </div>

              <ul className="space-y-2.5 text-xs text-slate-200 border-t border-teal-500/20 pt-4">
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 font-bold">✓</span>
                  <span>Evaluates alternative cashflow consistency, UPI cadence, and bill payments.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 font-bold">✓</span>
                  <span>Distinguishes healthy cyclical gig variation from persistent deterioration.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 font-bold">✓</span>
                  <span>Tracks recovery speed: verifies that earning dips are followed by active rebound.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 font-bold">✓</span>
                  <span>Human-understandable SHAP explanations empower borrower improvement.</span>
                </li>
              </ul>
            </Card>
          </div>
        </div>
      </section>

      {/* 3. INTERACTIVE VOLATILITY SIMULATOR */}
      <section id="features" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-2 max-w-xl">
            <Badge variant="mint" className="text-xs">Interactive Simulator</Badge>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Test Volatility Resilience
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Explore how PARAKH processes real-world cashflow curves across different informal and gig sectors.
            </p>
          </div>

          {/* Profile Switcher Tabs */}
          <div className="flex flex-wrap gap-2 bg-[#0A162E] p-1.5 rounded-full border border-white/[0.08]">
            {Object.entries(SIMULATION_PROFILES).map(([key, prof]) => (
              <button
                key={key}
                onClick={() => setSelectedProfileKey(key)}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                  selectedProfileKey === key
                    ? 'bg-[#C8F451] text-[#07111F] font-bold shadow-sm'
                    : 'text-muted-foreground hover:text-white'
                }`}
              >
                {prof.role.split('(')[0].trim()}
              </button>
            ))}
          </div>
        </div>

        {/* Active Profile Info Banner */}
        <div className="p-4 rounded-2xl bg-[#0A162E] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div>
            <span className="font-bold text-white text-sm">{activeProfile.role}: </span>
            <span className="text-slate-300">{activeProfile.description}</span>
          </div>
          <Badge variant="outline" className="shrink-0 text-[11px] rounded-full">
            {activeProfile.positiveDriver}
          </Badge>
        </div>

        {/* Embedded Dynamic Cashflow Chart */}
        <CashflowVolatilityChart
          data={activeProfile.chartData}
          recoveryRate={activeProfile.recoveryRate}
          title={`Cashflow Cycle Tracking • ${activeProfile.role}`}
        />
      </section>

      {/* 4. METHODOLOGY PILLARS */}
      <section className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <Badge variant="ai" className="text-xs">Model Architecture</Badge>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Built on three analytical pillars
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Engineered to provide risk analysts and underwriters with actionable, explainable signals.
          </p>
        </div>

        <StaggerList className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-[#0A162E] border-white/[0.08] h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300">
                  <Activity className="size-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Volatility Normalization</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Separates expected week-to-week seasonal swings from persistent earning decline.
                  Gig demand troughs are evaluated alongside platform tenure and customer reviews.
                </p>
              </div>

              <div className="pt-4 border-t border-white/[0.08] text-[11px] text-cyan-300 font-semibold">
                Metric: Volatility Index (CoV)
              </div>
            </MotionCard>
          </StaggerItem>

          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-[#0A162E] border-white/[0.08] h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-300">
                  <TrendingUp className="size-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Shock Recovery Velocity</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Measures the historical speed at which a borrower recovers cashflow following illness,
                  vehicle breakdown, or seasonal platform lulls back to sustainable levels.
                </p>
              </div>

              <div className="pt-4 border-t border-white/[0.08] text-[11px] text-violet-300 font-semibold">
                Metric: Mean Days to Rebound
              </div>
            </MotionCard>
          </StaggerItem>

          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-[#0A162E] border-white/[0.08] h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-300">
                  <Zap className="size-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Explainable Transparency</h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Every assessment surfaces positive drivers and attention areas via human-translated SHAP
                  explanations, ensuring full regulatory compliance and applicant trust.
                </p>
              </div>

              <div className="pt-4 border-t border-white/[0.08] text-[11px] text-amber-300 font-semibold">
                Metric: Feature Contribution Weights
              </div>
            </MotionCard>
          </StaggerItem>
        </StaggerList>
      </section>

      {/* 5. TRUST, FAIRNESS & GOVERNANCE */}
      <section id="institutions" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Card className="p-6 sm:p-8 space-y-6 bg-[#0A162E] border border-white/[0.08] rounded-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-full bg-cyan-500/15 flex items-center justify-center text-cyan-300">
                <Scale className="size-5" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white tracking-tight">
                  Governance & Responsible Lending Standards
                </h3>
                <p className="text-xs text-muted-foreground">
                  Audited with Fairlearn for demographic parity and non-discriminatory credit assessment.
                </p>
              </div>
            </div>

            <Badge variant="mint" className="text-xs">
              <ShieldCheck className="size-3" />
              <span>Human-in-the-Loop Architecture</span>
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-slate-300">
            <div className="space-y-1.5">
              <span className="font-bold text-white block">No Automated Legal Mandates</span>
              <p className="text-muted-foreground leading-relaxed">
                PARAKH operates as an underwriter intelligence assistant. Review decisions remain firmly in the
                hands of human risk officers through structured review workflows.
              </p>
            </div>
            <div className="space-y-1.5">
              <span className="font-bold text-white block">Privacy & Data Minimization</span>
              <p className="text-muted-foreground leading-relaxed">
                Only verifiable cashflow metadata and platform signals are processed with explicit applicant
                consent. Raw sensitive credentials are never stored.
              </p>
            </div>
            <div className="space-y-1.5">
              <span className="font-bold text-white block">Bias & Disparity Monitoring</span>
              <p className="text-muted-foreground leading-relaxed">
                Underwriters have continuous access to model fairness metrics, monitoring demographic parity
                across gig work categories and geographic cohorts.
              </p>
            </div>
          </div>
        </Card>
      </section>

      {/* 6. DUAL PORTAL ENTRY / CTA */}
      <section id="about" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Borrower Portal Gateway */}
          <Card className="p-6 sm:p-8 space-y-5 bg-[#0A162E] border border-white/[0.08] rounded-2xl flex flex-col justify-between">
            <div className="space-y-3">
              <Badge variant="cyan">Borrower Experience</Badge>
              <h3 className="text-2xl font-black text-white">For Gig Workers & Earners</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Check your alternative credit score, understand what drives your evaluation, and submit voluntary alternative data.
              </p>
            </div>

            <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between">
              <Link href="/user/dashboard">
                <Button variant="lime" className="gap-2 text-xs font-bold px-5">
                  Open Borrower Portal <ArrowRight className="size-3.5" />
                </Button>
              </Link>
              <Link href="/user/applications/new">
                <span className="text-xs text-cyan-300 hover:underline">New Assessment →</span>
              </Link>
            </div>
          </Card>

          {/* Underwriter Cockpit Gateway */}
          <Card className="p-6 sm:p-8 space-y-5 bg-[#0A162E] border border-cyan-500/25 rounded-2xl flex flex-col justify-between">
            <div className="space-y-3">
              <Badge variant="mint">Underwriter Cockpit</Badge>
              <h3 className="text-2xl font-black text-white">For Risk Analysts & NBFCs</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Review priority application queues, audit SHAP feature weights, perform manual reviews, and inspect model fairness metrics.
              </p>
            </div>

            <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between">
              <Link href="/admin/dashboard">
                <Button variant="pillOutline" className="gap-2 text-xs font-bold px-5">
                  Open Underwriter Cockpit <ArrowRight className="size-3.5" />
                </Button>
              </Link>
              <Link href="/admin/applications">
                <span className="text-xs text-slate-300 hover:text-white">Review Queue (4) →</span>
              </Link>
            </div>
          </Card>
        </div>
      </section>
    </PageTransition>
  );
}
