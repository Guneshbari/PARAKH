'use client';

import React, { use } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Sparkles,
  Building2,
  Calendar,
  DollarSign,
  UserCheck,
  Printer,
  ChevronRight,
  Info,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { getUserApplicationById } from '@/data/mock/user';
import { formatCurrency } from '@/lib/utils';
import type { ApplicationStatus } from '@parakh/types';

interface ApplicationDetailPageProps {
  params: Promise<{ id: string }>;
}

interface TimelineStage {
  id: string;
  title: string;
  description: string;
  status: 'COMPLETED' | 'ACTIVE' | 'PENDING';
  timestamp?: string;
}

export default function ApplicationDetailPage({ params }: ApplicationDetailPageProps) {
  const { id } = use(params);
  const application = getUserApplicationById(id);

  // Derive timeline stages based on application status
  const getTimelineStages = (status: ApplicationStatus): TimelineStage[] => {
    const isStage2 =
      status === 'DATA_VALIDATION' ||
      status === 'FINANCIAL_ANALYSIS' ||
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';
    const isStage3 =
      status === 'FINANCIAL_ANALYSIS' ||
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';
    const isStage4 =
      status === 'ASSESSMENT_COMPLETED' ||
      status === 'MANUAL_REVIEW_REQUIRED' ||
      status === 'REVIEW_COMPLETED';

    return [
      {
        id: 's1',
        title: 'Application Intake & Consent',
        description: 'Personal profile, gig credentials, and consent artifact #CNS-2024-8910 registered.',
        status: isStage2 ? 'COMPLETED' : status === 'SUBMITTED' ? 'ACTIVE' : 'COMPLETED',
        timestamp: new Date(application.submittedAt).toLocaleDateString('en-IN', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
      },
      {
        id: 's2',
        title: 'Alternative Data Ingestion',
        description: 'DigiLocker KYC attestation verified; active telemetry linked across platform APIs.',
        status: isStage3
          ? 'COMPLETED'
          : status === 'DATA_VALIDATION'
          ? 'ACTIVE'
          : isStage2
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage3 ? 'Verified in 42s' : undefined,
      },
      {
        id: 's3',
        title: 'Cashflow Volatility Modeling',
        description: '12-week income trends, cyclical dip rebounds, and micro-obligation cadences calculated.',
        status: isStage4
          ? 'COMPLETED'
          : status === 'FINANCIAL_ANALYSIS'
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage4 ? 'Completed in 1.4m' : undefined,
      },
      {
        id: 's4',
        title: 'Explainable Score Synthesis',
        description: 'Alternative score generated with transparent positive & attention feature factors.',
        status:
          status === 'ASSESSMENT_COMPLETED' || status === 'REVIEW_COMPLETED'
            ? 'COMPLETED'
            : status === 'MANUAL_REVIEW_REQUIRED'
            ? 'COMPLETED'
            : 'PENDING',
        timestamp: application.assessment
          ? `Score: ${application.assessment.score} / 850`
          : undefined,
      },
      {
        id: 's5',
        title:
          status === 'MANUAL_REVIEW_REQUIRED'
            ? 'Human Credit Reviewer In-Loop Review'
            : status === 'REVIEW_COMPLETED'
            ? 'Credit Reviewer Outcome Recorded'
            : 'Institutional Credit Review Readout',
        description:
          status === 'MANUAL_REVIEW_REQUIRED'
            ? 'A certified credit reviewer is reviewing non-standard monsoon variances and telemetry cross-checks.'
            : status === 'REVIEW_COMPLETED'
            ? 'Credit reviewer verified platform continuity and recorded final assessment outcome.'
            : 'Assessment ready for participating institutional credit reviewer without automated decisions.',
        status:
          status === 'REVIEW_COMPLETED'
            ? 'COMPLETED'
            : status === 'MANUAL_REVIEW_REQUIRED'
            ? 'ACTIVE'
            : status === 'ASSESSMENT_COMPLETED'
            ? 'COMPLETED'
            : 'PENDING',
        timestamp: application.review?.recordedAt
          ? new Date(application.review.recordedAt).toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })
          : undefined,
      },
    ];
  };

  const timeline = getTimelineStages(application.status);

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY BAR & NAVIGATION */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/user/applications">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs">
              <ArrowLeft className="size-3.5" /> Back to Applications
            </Button>
          </Link>
          <span className="text-xs text-foreground-muted font-mono">
            REF: {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>
          {application.assessment && (
            <Link href={`/user/results/${application.id}`}>
              <Button
                variant="default"
                size="sm"
                className="gap-1.5 text-xs font-semibold px-4 rounded-full cursor-pointer shadow-xs"
              >
                <Sparkles className="size-3.5" /> View Assessment Report
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* 2. APPLICATION HEADER HERO */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 rounded-2xl bg-surface dark:bg-surface-elevated border border-border-strong shadow-card-elevated">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight font-mono">
              {application.id}
            </h1>
            <StatusBadge status={application.status} />
            {application.assessment && (
              <RiskBadge
                riskLevel={application.assessment.riskLevel}
                showIcon={true}
                className="text-xs py-0.5 px-2.5"
              />
            )}
          </div>
          <p className="text-sm text-foreground-secondary">
            {application.purpose} • {application.applicantName}
          </p>
          <div className="flex flex-wrap items-center gap-4 text-xs text-foreground-muted pt-1">
            <span className="flex items-center gap-1.5">
              <Calendar className="size-3.5 opacity-70" />
              Submitted {new Date(application.submittedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <DollarSign className="size-3.5 opacity-70" />
              Requested {formatCurrency(application.requestedAmount)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <Building2 className="size-3.5 opacity-70" />
              Employment: Gig Economy Worker
            </span>
          </div>
        </div>

        {application.assessment && (
          <div className="flex flex-col items-start md:items-end justify-center gap-1 p-4 rounded-2xl bg-surface-highlight border border-border">
            <span className="text-[11px] font-semibold text-foreground-muted uppercase tracking-wider">
              Assessment Score
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-bold text-foreground font-mono">
                {application.assessment.score}
              </span>
              <span className="text-xs text-foreground-muted">/ 850</span>
            </div>
            <span className="text-[11px] text-foreground-secondary font-mono">
              {application.assessment.modelConfidence}% Data Confidence
            </span>
          </div>
        )}
      </div>

      {/* 3. TIMELINE & PROGRESS TRACKER */}
      <Card className="p-6 sm:p-8 bg-surface border-border space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-foreground tracking-tight flex items-center gap-2">
              <Clock className="size-4 text-foreground-secondary" />
              Evaluation Lifecycle & Audit Trail
            </h2>
            <p className="text-xs text-foreground-muted">
              End-to-end transparency of alternative telemetry ingestion, volatility scoring, and credit reviewer checkpoints.
            </p>
          </div>
          <Badge variant="outline" className="text-[11px] font-mono">
            {application.status.replace(/_/g, ' ')}
          </Badge>
        </div>

        <div className="relative pl-6 sm:pl-8 border-l border-border space-y-8 my-4 ml-3">
          {timeline.map((step) => {
            const isCompleted = step.status === 'COMPLETED';
            const isActive = step.status === 'ACTIVE';

            return (
              <div key={step.id} className="relative group">
                {/* Node icon */}
                <div
                  className={`absolute -left-[31px] sm:-left-[39px] top-0.5 size-6 rounded-full flex items-center justify-center text-xs transition-transform ring-4 ring-surface ${
                    isCompleted
                      ? 'bg-[#472393] text-white shadow-xs dark:bg-foreground dark:text-background'
                      : isActive
                      ? 'bg-[#F5F1FF] border border-[rgba(71,35,147,0.35)] text-[#472393] animate-pulse dark:bg-surface-highlight dark:border-border dark:text-foreground'
                      : 'bg-surface-highlight/50 text-foreground-muted border border-border'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="size-3.5" />
                  ) : isActive ? (
                    <Clock className="size-3.5" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-foreground-muted/30" />
                  )}
                </div>

                {/* Content */}
                <div className="space-y-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <h3
                      className={`text-sm font-semibold ${
                        isCompleted
                          ? 'text-foreground'
                          : isActive
                          ? 'text-foreground'
                          : 'text-foreground-muted'
                      }`}
                    >
                      {step.title}
                    </h3>
                    {step.timestamp && (
                      <span className="text-[11px] font-mono text-foreground-muted">
                        {step.timestamp}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-foreground-muted leading-relaxed max-w-2xl">
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 4. UNDERWRITER REVIEW CARD (Human-in-the-Loop) */}
      {application.review && (
        <Card className="p-6 sm:p-7 bg-surface border-border space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
            <div className="flex items-center gap-2.5">
              <UserCheck className="size-5 text-foreground-secondary" />
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Human-in-the-Loop Credit Reviewer Assessment
                </h3>
                <p className="text-xs text-foreground-muted">
                  Institutional risk review conducted in accordance with PARAKH explainability standards.
                </p>
              </div>
            </div>
            <Badge
              variant="outline"
              className="text-xs"
            >
              {application.review.status.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-foreground">
                  Reviewing Credit Reviewer: {application.review.underwriterName || 'Assigned Officer'}
                </span>
                {application.review.recordedAt && (
                  <span className="font-mono text-foreground-muted text-[11px]">
                    {new Date(application.review.recordedAt).toLocaleDateString('en-IN', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </div>
              {application.review.decisionNotes && (
                <p className="text-xs text-foreground-secondary leading-relaxed italic">
                  &ldquo;{application.review.decisionNotes}&rdquo;
                </p>
              )}
            </div>

            {application.review.verificationItemsRequested &&
              application.review.verificationItemsRequested.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[11px] font-semibold text-foreground-muted uppercase tracking-wider">
                    Requested Verification Evidence:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {application.review.verificationItemsRequested.map((item, idx) => (
                      <Badge
                        key={idx}
                        variant="secondary"
                        className="text-xs py-1 px-2.5"
                      >
                        {item}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
          </div>
        </Card>
      )}

      {/* 5. APPLICATION DATA SPECIFICATION */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Financial Details */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <DollarSign className="size-4 text-foreground-secondary" />
            Financial Request Overview
          </h3>

          <div className="space-y-3 text-xs divide-y divide-border">
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Requested Capital</span>
              <span className="font-mono font-semibold text-foreground">
                {formatCurrency(application.requestedAmount)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Stated Purpose</span>
              <span className="font-medium text-foreground-secondary">{application.purpose}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Employment Classification</span>
              <Badge variant="outline" className="text-[10px]">
                {application.employmentType.replace(/_/g, ' ')}
              </Badge>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Monthly Inflow (Self-Reported)</span>
              <span className="font-mono text-foreground-secondary">₹51,200</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Existing Commitments</span>
              <span className="font-mono text-foreground-secondary">₹4,500 / month (8.8%)</span>
            </div>
          </div>
        </Card>

        {/* Alternative Telemetry Analyzed */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Layers className="size-4 text-foreground-secondary" />
            Connected Feeds Evaluated
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-semibold text-foreground block">Swiggy Partner Telemetry</span>
                <span className="text-foreground-muted text-[11px]">18 months • 4.85 ★ • 3,420 orders</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Verified Feed
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-semibold text-foreground block">Urban Company Pro Connect</span>
                <span className="text-foreground-muted text-[11px]">8 months • 4.90 ★ • 312 tasks</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Verified Feed
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-semibold text-foreground block">BBPS Micro-Repayments</span>
                <span className="text-foreground-muted text-[11px]">98% on-time • Electricity & LPG</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Punctual Track
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* 6. ASSESSMENT REPORT CTA (If Assessment Exists) */}
      {application.assessment && (
        <Card className="p-6 bg-surface border border-border shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 opacity-75" />
              <h3 className="text-base font-bold text-foreground">
                Detailed Volatility & Explainability Dossier Ready
              </h3>
            </div>
            <p className="text-xs text-foreground-muted max-w-xl">
              Examine positive vs. attention factors, visual SHAP feature contributions, and the 12-week income rebound trajectory.
            </p>
          </div>

          <Link href={`/user/results/${application.id}`}>
            <Button
              variant="default"
              className="gap-2 font-semibold px-6 shadow-xs rounded-full whitespace-nowrap cursor-pointer"
            >
              <span>Inspect Full Dossier</span>
              <ChevronRight className="size-4" />
            </Button>
          </Link>
        </Card>
      )}

      {/* 7. REGULATORY & NON-LENDING NOTICE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Assessment Transparency & Non-Lending Notice
          </span>
          <p>
            PARAKH evaluates volatility-aware alternative credit intelligence for informal and gig economy workers. PARAKH does not act as a lender or issue automated loan decisions. Partner institutions use this assessment within human-in-the-loop underwriting frameworks.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
