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
      {/* 1. HERO SECTION (REFERENCE-BASED FINTECH HERO WITH FLOWING SILK WAVES) */}
      <section className="relative w-full bg-[#F7F8FC] dark:bg-background overflow-hidden pt-2 pb-14 sm:pb-18 transition-colors">
        {/* Subtle light-mode center illumination */}
        <div
          className="absolute inset-0 pointer-events-none -z-5 dark:hidden"
          style={{
            background:
              'radial-gradient(circle at 50% 42%, rgba(255, 255, 255, 0.92) 0%, rgba(247, 248, 252, 0.72) 48%, rgba(239, 243, 249, 0.92) 100%)',
          }}
          aria-hidden="true"
        />

        {/* Animated Silk Wave System */}
        <HeroWaveSystem />

        {/* Public Landing Navigation Bar */}
        <LandingNavbar />

        {/* Hero Content Container */}
        <div className="relative z-10 mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center pt-5 sm:pt-8 space-y-4 sm:space-y-5">
          {/* Eyebrow Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white dark:bg-surface-highlight border border-[rgba(15,23,42,0.08)] dark:border-border text-[#101828] dark:text-foreground text-[11px] font-semibold tracking-wide shadow-2xs">
            <Sparkles className="size-3.5 text-[#6366F1] dark:text-foreground-secondary" />
            <span className="font-mono uppercase tracking-widest text-[10px]">
              AI-Powered Credit Assessment
            </span>
          </div>

          {/* Main Editorial Heading */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#101828] dark:text-foreground leading-[1.1]">
            Credit assessment <br />
            for the{' '}
            <span className="text-[#475467] dark:text-foreground-secondary font-semibold italic">
              invisible.
            </span>
          </h1>

          {/* Supporting Copy */}
          <p className="text-base sm:text-lg text-[#475467] dark:text-foreground-secondary max-w-2xl mx-auto leading-relaxed font-normal">
            PARAKH evaluates financial behavior beyond traditional credit history, using alternative
            data and explainable AI.
          </p>

          {/* Action CTAs */}
          <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 pt-1">
            <Link href="/login?role=applicant">
              <Button
                variant="default"
                size="lg"
                className="gap-2 font-semibold px-7 h-11 rounded-full cursor-pointer shadow-sm hover:shadow-md bg-[#472393] text-white hover:bg-[#5630A3] active:bg-[#3B1D7A] hover:-translate-y-0.5 transition-all duration-200 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90"
              >
                <span>Applicant Portal</span>
                <ArrowRight className="size-4" />
              </Button>
            </Link>

            <Link href="/login?role=reviewer">
              <Button
                variant="pillOutline"
                size="lg"
                className="gap-2 font-semibold px-7 h-11 rounded-full cursor-pointer shadow-2xs hover:shadow-sm bg-white text-[#472393] border border-[rgba(71,35,147,0.22)] hover:bg-[#F6F2FF] hover:border-[rgba(71,35,147,0.35)] hover:-translate-y-0.5 transition-all duration-200 dark:bg-transparent dark:text-foreground dark:border-border dark:hover:bg-surface-elevated"
              >
                <ShieldCheck className="size-4 text-[#472393] dark:text-foreground" />
                <span>Credit Reviewer</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Product / Phone Mockup with Floating Cards */}
        <div className="relative z-10 w-full px-4 sm:px-6 lg:px-8 mt-2 sm:mt-3 flex justify-center overflow-visible">
          <HeroProductPreview />
        </div>

        {/* Bottom Trust Statement & Institutional Badges */}
        <div className="relative z-10 mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8 border-t border-[rgba(15,23,42,0.08)] dark:border-border flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-[#64748B] dark:text-foreground-muted">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-center sm:text-left">
            <span className="font-medium text-[#0F172A] dark:text-foreground">
              Built for transparent, explainable financial assessment.
            </span>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="px-2.5 py-0.5 rounded-full bg-white dark:bg-surface border border-[rgba(15,23,42,0.08)] dark:border-border text-[#475569] dark:text-foreground-secondary">
                DPDP Act 2023
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-white dark:bg-surface border border-[rgba(15,23,42,0.08)] dark:border-border text-[#475569] dark:text-foreground-secondary">
                RBI AA Ecosystem
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-white dark:bg-surface border border-[rgba(15,23,42,0.08)] dark:border-border text-[#475569] dark:text-foreground-secondary">
                Fairlearn Audited
              </span>
            </div>
          </div>

          {/* Right pill badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white dark:bg-surface-highlight border border-[rgba(15,23,42,0.08)] dark:border-border text-[#475569] dark:text-foreground-secondary text-[11px] font-medium shadow-2xs">
            <Sparkles className="size-3 opacity-70" />
            <span>More people. Real incomes. Better credit.</span>
          </div>
        </div>
      </section>

      {/* 2. THE CORE PARADIGM SHIFT: TRADITIONAL BUREAU VS PARAKH */}
      <section id="how-it-works" className="relative pt-4 sm:pt-6 pb-12 sm:pb-16 overflow-hidden">
        <div className="relative z-10 mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-10">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <Badge variant="outline" className="text-xs">Paradigm Shift</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
              Why traditional scoring fails the informal economy
            </h2>
            <p className="text-sm text-foreground-muted leading-relaxed">
              When legacy scoring models evaluate gig workers, normal weekly variance is misinterpreted as financial instability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            {/* Legacy Bureau Column */}
            <Card className="border border-border bg-surface space-y-5 p-6 sm:p-7 rounded-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <XCircle className="size-5 text-foreground-muted" />
                  <span className="text-sm font-semibold uppercase tracking-wider text-foreground-muted">
                    Traditional Credit Bureaus
                  </span>
                </div>
                <Badge variant="riskHigher">Thin / Zero File</Badge>
              </div>

              <div className="space-y-2">
                <div className="text-3xl font-bold text-foreground-muted font-mono">
                  - - - / 850
                </div>
                <p className="text-xs text-foreground-muted font-medium">
                  Automatic Rejection or High Risk Surcharge
                </p>
              </div>

              <ul className="space-y-2.5 text-xs text-foreground-muted border-t border-border pt-4">
                <li className="flex items-start gap-2">
                  <span className="font-bold">•</span>
                  <span>Requires historical formal debt and bureau trade-lines (CIBIL/Experian).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold">•</span>
                  <span>Penalizes income variance: off-peak earning weeks are flagged as high risk.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold">•</span>
                  <span>Zero visibility into UPI transactions, utility punctuality, or platform tenure.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold">•</span>
                  <span>Opaque, non-actionable decisions leaving applicants stranded.</span>
                </li>
              </ul>
            </Card>

            {/* PARAKH Volatility-Aware Column */}
            <Card className="border border-border-strong bg-surface space-y-5 p-6 sm:p-7 rounded-2xl shadow-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-5 text-foreground" />
                  <span className="text-sm font-semibold uppercase tracking-wider text-foreground">
                    PARAKH Alternative Intelligence
                  </span>
                </div>
                <Badge variant="riskLower">LOWER ESTIMATED RISK</Badge>
              </div>

              <div className="space-y-2">
                <div className="text-3xl font-bold text-foreground font-mono">
                  742 / 850
                </div>
                <p className="text-xs text-foreground-secondary font-medium">
                  High Confidence • 94% Shock Rebound Demonstrated
                </p>
              </div>

              <ul className="space-y-2.5 text-xs text-foreground-secondary border-t border-border pt-4">
                <li className="flex items-start gap-2">
                  <span className="font-bold text-foreground">✓</span>
                  <span>Evaluates alternative cashflow consistency, UPI cadence, and bill payments.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-foreground">✓</span>
                  <span>Distinguishes healthy cyclical gig variation from persistent deterioration.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-foreground">✓</span>
                  <span>Tracks recovery speed: verifies that earning dips are followed by active rebound.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-foreground">✓</span>
                  <span>Human-understandable SHAP explanations empower applicant improvement.</span>
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
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
              Test Volatility Resilience
            </h2>
            <p className="text-sm text-foreground-muted leading-relaxed">
              Explore how PARAKH processes real-world cashflow curves across different informal and gig sectors.
            </p>
          </div>

          {/* Profile Switcher Tabs */}
          <div className="flex flex-wrap gap-1.5 bg-surface-highlight p-1 rounded-full border border-border">
            {Object.entries(SIMULATION_PROFILES).map(([key, prof]) => (
              <button
                key={key}
                onClick={() => setSelectedProfileKey(key)}
                className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                  selectedProfileKey === key
                    ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                    : 'text-foreground-muted hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
                }`}
              >
                {prof.role.split('(')[0].trim()}
              </button>
            ))}
          </div>
        </div>

        {/* Active Profile Info Banner */}
        <div className="p-4 rounded-2xl bg-surface border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div>
            <span className="font-semibold text-foreground text-sm">{activeProfile.role}: </span>
            <span className="text-foreground-secondary">{activeProfile.description}</span>
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
          <Badge variant="secondary" className="text-xs">Model Architecture</Badge>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Built on three analytical pillars
          </h2>
          <p className="text-sm text-foreground-muted leading-relaxed">
            Engineered to provide risk analysts and credit reviewers with actionable, explainable signals.
          </p>
        </div>

        <StaggerList className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-surface border-border h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-surface-highlight border border-border flex items-center justify-center text-foreground">
                  <Activity className="size-5 opacity-80" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">Volatility Normalization</h3>
                <p className="text-xs text-foreground-muted leading-relaxed">
                  Separates expected week-to-week seasonal swings from persistent earning decline.
                  Gig demand troughs are evaluated alongside platform tenure and customer reviews.
                </p>
              </div>

              <div className="pt-4 border-t border-border text-[11px] text-foreground-secondary font-medium">
                Metric: Volatility Index (CoV)
              </div>
            </MotionCard>
          </StaggerItem>

          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-surface border-border h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-surface-highlight border border-border flex items-center justify-center text-foreground">
                  <TrendingUp className="size-5 opacity-80" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">Shock Recovery Velocity</h3>
                <p className="text-xs text-foreground-muted leading-relaxed">
                  Measures the historical speed at which an applicant recovers cashflow following illness,
                  vehicle breakdown, or seasonal platform lulls back to sustainable levels.
                </p>
              </div>

              <div className="pt-4 border-t border-border text-[11px] text-foreground-secondary font-medium">
                Metric: Mean Days to Rebound
              </div>
            </MotionCard>
          </StaggerItem>

          <StaggerItem>
            <MotionCard className="space-y-4 p-6 sm:p-7 rounded-2xl bg-surface border-border h-full flex flex-col justify-between">
              <div className="space-y-3">
                <div className="size-10 rounded-full bg-surface-highlight border border-border flex items-center justify-center text-foreground">
                  <Zap className="size-5 opacity-80" />
                </div>
                <h3 className="text-xl font-semibold text-foreground">Explainable Transparency</h3>
                <p className="text-xs text-foreground-muted leading-relaxed">
                  Every assessment surfaces positive drivers and attention areas via human-translated SHAP
                  explanations, ensuring full regulatory compliance and applicant trust.
                </p>
              </div>

              <div className="pt-4 border-t border-border text-[11px] text-foreground-secondary font-medium">
                Metric: Feature Contribution Weights
              </div>
            </MotionCard>
          </StaggerItem>
        </StaggerList>
      </section>

      {/* 5. TRUST, FAIRNESS & GOVERNANCE */}
      <section id="institutions" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <Card className="p-6 sm:p-8 space-y-6 bg-surface border border-border rounded-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="size-9 rounded-full bg-surface-highlight border border-border flex items-center justify-center text-foreground">
                <Scale className="size-5 opacity-80" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground tracking-tight">
                  Governance & Responsible Lending Standards
                </h3>
                <p className="text-xs text-foreground-muted">
                  Audited with Fairlearn for demographic parity and non-discriminatory credit assessment.
                </p>
              </div>
            </div>

            <Badge variant="mint" className="text-xs">
              <ShieldCheck className="size-3" />
              <span>Human-in-the-Loop Architecture</span>
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-foreground-secondary">
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">No Automated Legal Mandates</span>
              <p className="text-foreground-muted leading-relaxed">
                PARAKH operates as a credit reviewer intelligence assistant. Review decisions remain firmly in the
                hands of human risk officers through structured review workflows.
              </p>
            </div>
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Privacy & Data Minimization</span>
              <p className="text-foreground-muted leading-relaxed">
                Only verifiable cashflow metadata and platform signals are processed with explicit applicant
                consent. Raw sensitive credentials are never stored.
              </p>
            </div>
            <div className="space-y-1.5">
              <span className="font-semibold text-foreground block">Bias & Disparity Monitoring</span>
              <p className="text-foreground-muted leading-relaxed">
                Credit Reviewers have continuous access to model fairness metrics, monitoring demographic parity
                across gig work categories and geographic cohorts.
              </p>
            </div>
          </div>
        </Card>
      </section>

      {/* 6. DUAL PORTAL ENTRY / CTA */}
      <section id="about" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Applicant Portal Gateway */}
          <Card className="p-6 sm:p-8 space-y-5 bg-surface border border-border rounded-2xl flex flex-col justify-between">
            <div className="space-y-3">
              <Badge variant="secondary">Applicant Portal</Badge>
              <h3 className="text-2xl font-bold text-foreground">For Gig Workers & Earners</h3>
              <p className="text-xs text-foreground-muted leading-relaxed">
                Check your alternative credit assessment, understand what drives your score, and submit voluntary platform activity data.
              </p>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-between">
              <Link href="/login?role=applicant">
                <Button variant="default" className="gap-2 text-xs font-semibold px-5 rounded-full cursor-pointer">
                  Applicant Portal <ArrowRight className="size-3.5" />
                </Button>
              </Link>
              <Link href="/signup?role=applicant">
                <span className="text-xs text-foreground-secondary hover:text-foreground font-medium underline-offset-4 hover:underline">New Account →</span>
              </Link>
            </div>
          </Card>

          {/* Credit Reviewer Gateway */}
          <Card className="p-6 sm:p-8 space-y-5 bg-surface border border-border rounded-2xl flex flex-col justify-between">
            <div className="space-y-3">
              <Badge variant="outline">Credit Reviewer</Badge>
              <h3 className="text-2xl font-bold text-foreground">For Risk Analysts & NBFCs</h3>
              <p className="text-xs text-foreground-muted leading-relaxed">
                Review priority application queues, audit SHAP feature weights, perform manual human reviews, and inspect model fairness metrics.
              </p>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-between">
              <Link href="/login?role=reviewer">
                <Button variant="secondary" className="gap-2 text-xs font-semibold px-5 rounded-full cursor-pointer">
                  Credit Reviewer <ArrowRight className="size-3.5" />
                </Button>
              </Link>
              <span className="text-[11px] font-mono text-foreground-muted">Station Access Only</span>
            </div>
          </Card>
        </div>
      </section>
    </PageTransition>
  );
}
