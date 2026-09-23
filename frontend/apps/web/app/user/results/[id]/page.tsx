'use client';

import React, { use, useState, useEffect, useCallback } from 'react';
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
  AlertCircle,
  RefreshCw,
  FileQuestion,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { CreditScoreCard } from '@/components/shared/CreditScoreCard';
import { AIInsightCard } from '@/components/shared/AIInsightCard';
import { FeatureContributionCard } from '@/components/shared/FeatureContributionCard';
import { CashflowVolatilityChart } from '@/components/shared/CashflowVolatilityChart';
import {
  api,
  adaptAssessment,
  ApiError,
  type BackendCreditAssessmentResponse,
} from '@parakh/api';
import type { CreditAssessmentResult } from '@parakh/types';

interface ResultPageProps {
  params: Promise<{ id: string }>;
}

export default function CreditAssessmentResultPage({ params }: ResultPageProps) {
  const { id } = use(params);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<CreditAssessmentResult | null>(null);

  const fetchAssessment = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      let rawAssessment: BackendCreditAssessmentResponse | null = null;

      // 1. Try querying latest assessment by application UUID
      try {
        rawAssessment = await api.getLatestAssessmentByApplication(id);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          // 2. Try querying directly by assessment UUID
          try {
            rawAssessment = await api.getAssessmentById(id);
          } catch {
            rawAssessment = null;
          }
        } else {
          throw err;
        }
      }

      if (!rawAssessment) {
        setError('Assessment record not found');
        return;
      }

      const adapted = adaptAssessment(rawAssessment);
      setAssessment(adapted);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to retrieve assessment dossier.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAssessment();
  }, [fetchAssessment]);

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading Assessment Dossier...</h2>
        <p className="text-xs text-foreground-muted">Retrieving verified volatility score, SHAP drivers, and policy checks.</p>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-8 border-border bg-surface space-y-4 text-center">
          <FileQuestion className="size-10 text-foreground-muted mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">
              {error === 'Assessment record not found' ? 'Assessment Dossier Not Found' : 'Unable to Load Assessment'}
            </h2>
            <p className="text-xs text-foreground-secondary">
              {error === 'Assessment record not found'
                ? `No assessment evaluation exists for identifier '${id}'. Please verify the application ID or trigger a new assessment.`
                : error}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/user/applications">
              <Button variant="outline" size="sm" className="rounded-full text-xs">
                <ArrowLeft className="size-3.5 mr-1" /> My Applications
              </Button>
            </Link>
            {error !== 'Assessment record not found' && (
              <Button
                variant="default"
                size="sm"
                onClick={() => fetchAssessment()}
                className="rounded-full text-xs"
              >
                <RefreshCw className="size-3.5 mr-1" /> Retry
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY BAR & BREADCRUMB */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/user/dashboard">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs px-4 cursor-pointer">
              <ArrowLeft className="size-3.5" /> Back to Dashboard
            </Button>
          </Link>
          <h1 className="text-xs sm:text-sm font-semibold text-foreground">
            Credit Assessment Dossier{' '}
            <span className="text-xs text-foreground-muted font-mono font-normal">
              ({id.substring(0, 8)}...)
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground px-3.5 cursor-pointer"
          >
            <Printer className="size-3.5" /> Print Dossier
          </Button>
          <Button
            variant="pillOutline"
            size="sm"
            className="rounded-full gap-1.5 text-xs px-3.5 cursor-pointer"
          >
            <Share2 className="size-3.5" /> Share Report
          </Button>
        </div>
      </div>

      {/* 2. HERO ASSESSMENT SCORE DISPLAY */}
      <section className="space-y-2">
        <CreditScoreCard assessment={assessment} />
      </section>

      {/* 2.5 INSUFFICIENT EVIDENCE ALERT (MISSING SIGNALS) */}
      {(assessment.isInsufficientEvidence || (assessment.missingSignals && assessment.missingSignals.length > 0)) && (
        <section>
          <Card className="p-6 bg-surface border-amber-500/30 dark:border-amber-500/20 space-y-3.5">
            <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-semibold text-sm">
              <AlertTriangle className="size-4 shrink-0" />
              <span>Evidence Threshold Not Met — Required Signals Missing</span>
            </div>
            <p className="text-xs text-foreground-secondary leading-relaxed">
              The volatility-aware credit risk model could not synthesize an alternative score because core telemetry signals are missing or below minimal observation requirements:
            </p>
            <ul className="space-y-2 text-xs text-foreground">
              {(assessment.missingSignals && assessment.missingSignals.length > 0
                ? assessment.missingSignals
                : ['Continuous 30-day cashflow transaction history', 'Verified gig platform payout linkages']
              ).map((sig, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="size-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                  <span className="font-mono text-xs">{sig}</span>
                </li>
              ))}
            </ul>
            <div className="pt-2 flex items-center gap-3">
              <Link href="/user/profile">
                <Button variant="outline" size="sm" className="rounded-full text-xs">
                  Manage Connected Accounts
                </Button>
              </Link>
              <Link href="/user/applications/new">
                <Button variant="default" size="sm" className="rounded-full text-xs">
                  Submit Updated Application
                </Button>
              </Link>
            </div>
          </Card>
        </section>
      )}

      {/* 3. CONTEXTUAL AI RISK EXPLANATION */}
      <section>
        <AIInsightCard
          insight={
            assessment.isInsufficientEvidence
              ? 'Evaluation Refusal: Telemetry duration is below the minimum threshold required for automated risk scoring.'
              : 'Your alternative telemetry confirms steady weekly earning patterns with resilient rebound dynamics, indicating low credit risk.'
          }
          detail={
            assessment.isInsufficientEvidence
              ? 'Under RBI regulatory fair practice standards and PARAKH model governance, credit scores are never fabricated or estimated when core cashflow telemetry is missing. Please connect verified accounts to enable scoring.'
              : 'Traditional bureaus penalize gig income volatility as high risk. PARAKH evaluates verified 10-day recovery velocity and timely utility settlements to qualify you for fair credit evaluation.'
          }
          actionLabel="View Methodology"
        />
      </section>

      {/* 4. WHY THIS ASSESSMENT? (POSITIVE VS ATTENTION FACTORS) */}
      <section className="space-y-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground-muted uppercase tracking-wider">
            <Sparkles className="size-3.5 opacity-70" />
            <span>Explainable Evaluation Drivers</span>
          </div>
          <h2 className="text-2xl font-bold text-foreground tracking-tight">
            Why this assessment?
          </h2>
          <p className="text-xs text-foreground-muted">
            Clear, non-technical translation of the alternative indicators that contributed to your score.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Positive Factors */}
          <Card className="space-y-4 p-6 bg-surface border border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-foreground" />
                <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider">
                  Key Positive Factors (Strengths)
                </h3>
              </div>
              <Badge variant="riskLower" className="text-[10px]">High Impact</Badge>
            </div>

            <ul className="space-y-3.5 text-xs text-foreground-secondary">
              {assessment.keyPositiveFactors.length > 0 ? (
                assessment.keyPositiveFactors.map((f) => (
                  <li key={f.id} className="space-y-1">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <span className="size-1.5 rounded-full bg-foreground" />
                      <span>{f.title}</span>
                    </div>
                    <p className="text-foreground-muted leading-relaxed pl-3">
                      {f.description}
                    </p>
                  </li>
                ))
              ) : (
                <li className="text-foreground-muted italic">No positive factors flagged.</li>
              )}
            </ul>
          </Card>

          {/* Attention Factors */}
          <Card className="space-y-4 p-6 bg-surface border border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-foreground" />
                <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider">
                  Attention Areas (To Improve)
                </h3>
              </div>
              <Badge variant="outline" className="text-[10px]">Monitored</Badge>
            </div>

            <ul className="space-y-3.5 text-xs text-foreground-secondary">
              {assessment.keyAttentionFactors.length > 0 ? (
                assessment.keyAttentionFactors.map((f) => (
                  <li key={f.id} className="space-y-1">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <span className="size-1.5 rounded-full bg-foreground-muted" />
                      <span>{f.title}</span>
                    </div>
                    <p className="text-foreground-muted leading-relaxed pl-3">
                      {f.description}
                    </p>
                  </li>
                ))
              ) : (
                <li className="text-foreground-muted italic">No critical attention factors identified.</li>
              )}
            </ul>
          </Card>
        </div>
      </section>

      {/* 5. EXPLAINABLE SHAP CONTRIBUTIONS */}
      <section className="space-y-3">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-foreground">
            Feature Contribution Analysis
          </h2>
          <p className="text-xs text-foreground-muted">
            Mathematical impact of each telemetry feature on your synthesized score.
          </p>
        </div>

        <FeatureContributionCard contributions={assessment.featureContributions} />
      </section>

      {/* 6. CASHFLOW VOLATILITY TRACKING CHART */}
      {assessment.volatilityProfile && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">
              Weekly Inflow Rhythm & Rebound Curve
            </h2>
            <span className="text-xs text-foreground-muted">Verified Telemetry</span>
          </div>

          <CashflowVolatilityChart
            recoveryRate={Math.round(assessment.volatilityProfile.recoveryRateAfterLowIncome * 100)}
            title="Verified Inflow Rhythm & Rebound Curve"
          />
        </section>
      )}

      {/* 7. STATUTORY DPDP & MODEL DISCLAIMER */}
      {assessment.disclaimer && (
        <section className="pt-4 border-t border-border">
          <div className="flex items-start gap-2.5 p-4 rounded-xl bg-surface border border-border text-xs text-foreground-muted">
            <Info className="size-4 shrink-0 mt-0.5 text-foreground-muted" />
            <div className="space-y-0.5">
              <span className="font-semibold text-foreground block">Model Governance & Statutory Disclaimer</span>
              <p className="leading-relaxed">{assessment.disclaimer}</p>
            </div>
          </div>
        </section>
      )}
    </PageTransition>
  );
}
