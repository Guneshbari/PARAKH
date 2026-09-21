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
            ? 'Human Underwriter In-Loop Review'
            : status === 'REVIEW_COMPLETED'
            ? 'Underwriter Review Outcome Recorded'
            : 'Institutional Underwriter Readout',
        description:
          status === 'MANUAL_REVIEW_REQUIRED'
            ? 'A certified credit underwriter is reviewing non-standard monsoon variances and telemetry cross-checks.'
            : status === 'REVIEW_COMPLETED'
            ? 'Underwriter verified platform continuity and recorded final assessment outcome.'
            : 'Assessment ready for participating lender underwriter review without automated decisions.',
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <Link href="/user/applications">
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5 text-xs">
              <ArrowLeft className="size-3.5" /> Back to Applications
            </Button>
          </Link>
          <span className="text-xs text-muted-foreground font-mono">
            REF: {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-xl gap-1.5 text-xs text-muted-foreground hover:text-white"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>
          {application.assessment && (
            <Link href={`/user/results/${application.id}`}>
              <Button
                variant="lime"
                size="sm"
                className="gap-1.5 text-xs font-bold px-4"
              >
                <Sparkles className="size-3.5" /> View Assessment Report
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* 2. APPLICATION HEADER HERO */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 rounded-2xl bg-[#0A162E] border border-white/[0.08] shadow-xl">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-mono">
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
          <p className="text-sm text-slate-300">
            {application.purpose} • {application.applicantName}
          </p>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
            <span className="flex items-center gap-1.5">
              <Calendar className="size-3.5 text-cyan-400" />
              Submitted {new Date(application.submittedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <DollarSign className="size-3.5 text-cyan-400" />
              Requested {formatCurrency(application.requestedAmount)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <Building2 className="size-3.5 text-cyan-400" />
              Employment: Gig Economy Worker
            </span>
          </div>
        </div>

        {application.assessment && (
          <div className="flex flex-col items-start md:items-end justify-center gap-1 p-4 rounded-2xl bg-[#0E1F3D] border border-white/[0.08]">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Assessment Score
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-black text-white font-mono">
                {application.assessment.score}
              </span>
              <span className="text-xs text-muted-foreground">/ 850</span>
            </div>
            <span className="text-[11px] text-cyan-300 font-mono">
              {application.assessment.modelConfidence}% Data Confidence
            </span>
          </div>
        )}
      </div>

      {/* 3. TIMELINE & PROGRESS TRACKER */}
      <Card className="p-6 sm:p-8 bg-[#0A162E] border-white/[0.08] space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <Clock className="size-4 text-cyan-400" />
              Evaluation Lifecycle & Audit Trail
            </h2>
            <p className="text-xs text-muted-foreground">
              End-to-end transparency of alternative telemetry ingestion, volatility scoring, and underwriter checkpoints.
            </p>
          </div>
          <Badge variant="outline" className="text-[11px] font-mono">
            {application.status.replace(/_/g, ' ')}
          </Badge>
        </div>

        <div className="relative pl-6 sm:pl-8 border-l border-white/[0.1] space-y-8 my-4 ml-3">
          {timeline.map((step) => {
            const isCompleted = step.status === 'COMPLETED';
            const isActive = step.status === 'ACTIVE';

            return (
              <div key={step.id} className="relative group">
                {/* Node icon */}
                <div
                  className={`absolute -left-[31px] sm:-left-[39px] top-0.5 size-6 rounded-full flex items-center justify-center text-xs transition-transform ${
                    isCompleted
                      ? 'bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20 ring-4 ring-[#0A162E]'
                      : isActive
                      ? 'bg-amber-400 text-slate-950 animate-pulse ring-4 ring-[#0A162E]'
                      : 'bg-white/[0.06] text-muted-foreground border border-white/[0.1] ring-4 ring-[#0A162E]'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="size-3.5" />
                  ) : isActive ? (
                    <Clock className="size-3.5" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-white/20" />
                  )}
                </div>

                {/* Content */}
                <div className="space-y-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <h3
                      className={`text-sm font-bold ${
                        isCompleted
                          ? 'text-white'
                          : isActive
                          ? 'text-amber-300'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {step.title}
                    </h3>
                    {step.timestamp && (
                      <span className="text-[11px] font-mono text-muted-foreground">
                        {step.timestamp}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed max-w-2xl">
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
        <Card className="p-6 sm:p-7 bg-[#0A162E] border-white/[0.08] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
            <div className="flex items-center gap-2.5">
              <UserCheck className="size-5 text-cyan-400" />
              <div>
                <h3 className="text-sm font-bold text-white">
                  Human-in-the-Loop Underwriter Assessment
                </h3>
                <p className="text-xs text-muted-foreground">
                  Institutional risk review conducted in accordance with PARAKH explainability standards.
                </p>
              </div>
            </div>
            <Badge
              variant="outline"
              className={
                application.review.status === 'OUTCOME_RECORDED'
                  ? 'border-teal-500/40 text-teal-300'
                  : 'border-amber-500/40 text-amber-300'
              }
            >
              {application.review.status.replace(/_/g, ' ')}
            </Badge>
          </div>

          <div className="space-y-3 pt-1">
            <div className="p-4 rounded-2xl bg-[#0E1F3D] border border-white/[0.06] space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  Reviewing Underwriter: {application.review.underwriterName || 'Assigned Officer'}
                </span>
                {application.review.recordedAt && (
                  <span className="font-mono text-muted-foreground text-[11px]">
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
                <p className="text-xs text-slate-300 leading-relaxed italic">
                  &ldquo;{application.review.decisionNotes}&rdquo;
                </p>
              )}
            </div>

            {application.review.verificationItemsRequested &&
              application.review.verificationItemsRequested.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Requested Verification Evidence:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {application.review.verificationItemsRequested.map((item, idx) => (
                      <Badge
                        key={idx}
                        variant="outline"
                        className="text-xs py-1 px-2.5 bg-amber-500/5 text-amber-300 border-amber-500/20"
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
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <DollarSign className="size-4 text-cyan-400" />
            Financial Request Overview
          </h3>

          <div className="space-y-3 text-xs divide-y divide-white/[0.04]">
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Requested Capital</span>
              <span className="font-mono font-bold text-white">
                {formatCurrency(application.requestedAmount)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Stated Purpose</span>
              <span className="font-medium text-slate-200">{application.purpose}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Employment Classification</span>
              <Badge variant="outline" className="text-[10px]">
                {application.employmentType.replace(/_/g, ' ')}
              </Badge>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Monthly Inflow (Self-Reported)</span>
              <span className="font-mono text-slate-200">₹51,200</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Existing Commitments</span>
              <span className="font-mono text-slate-200">₹4,500 / month (8.8%)</span>
            </div>
          </div>
        </Card>

        {/* Alternative Telemetry Analyzed */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="size-4 text-cyan-400" />
            Connected Feeds Evaluated
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-[#0E1F3D] border border-white/[0.06] flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-bold text-white block">Swiggy Partner Telemetry</span>
                <span className="text-muted-foreground text-[11px]">18 months • 4.85 ★ • 3,420 orders</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Verified Feed
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-[#0E1F3D] border border-white/[0.06] flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-bold text-white block">Urban Company Pro Connect</span>
                <span className="text-muted-foreground text-[11px]">8 months • 4.90 ★ • 312 tasks</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Verified Feed
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-[#0E1F3D] border border-white/[0.06] flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="font-bold text-white block">BBPS Micro-Repayments</span>
                <span className="text-muted-foreground text-[11px]">98% on-time • Electricity & LPG</span>
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
        <Card className="p-6 bg-[#0A162E] border border-cyan-500/30 shadow-[0_0_25px_rgba(34,211,238,0.06)] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-cyan-400" />
              <h3 className="text-base font-bold text-white">
                Detailed Volatility & Explainability Dossier Ready
              </h3>
            </div>
            <p className="text-xs text-muted-foreground max-w-xl">
              Examine positive vs. attention factors, visual SHAP feature contributions, and the 12-week income rebound trajectory.
            </p>
          </div>

          <Link href={`/user/results/${application.id}`}>
            <Button
              variant="lime"
              className="gap-2 font-bold px-6 shadow-md whitespace-nowrap"
            >
              <span>Inspect Full Dossier</span>
              <ChevronRight className="size-4" />
            </Button>
          </Link>
        </Card>
      )}

      {/* 7. REGULATORY & NON-LENDING NOTICE */}
      <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-muted-foreground flex items-start gap-3">
        <Info className="size-4 text-teal-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-300 block">
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
