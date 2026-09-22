'use client';

import React, { use, useState, useEffect, useCallback } from 'react';
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
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { formatCurrency } from '@/lib/utils';
import {
  api,
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  ApiError,
  type BackendApplication,
  type BackendApplicantProfile,
} from '@parakh/api';
import type { ApplicationStatus, CreditApplication } from '@parakh/types';

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

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [application, setApplication] = useState<CreditApplication | null>(null);

  const fetchApplicationDetails = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch Application Record
      const rawApp = await api.getApplicationById(id);

      // 2. Fetch Associated Applicant Profile
      let rawProfile: BackendApplicantProfile | null = null;
      if (rawApp.applicant_profile_id) {
        try {
          rawProfile = await api.getApplicantProfile(rawApp.applicant_profile_id);
        } catch {
          rawProfile = null;
        }
      }

      // 3. Fetch Assessment if available
      let assessment = null;
      try {
        const rawAssessment = await api.getLatestAssessmentByApplication(id);
        assessment = adaptAssessment(rawAssessment, rawProfile?.full_name || undefined);
      } catch {
        assessment = null;
      }

      // 4. Fetch Reviews if available
      let reviewOutcome = null;
      try {
        const reviews = await api.getReviewsByApplication(id);
        if (reviews.length > 0) {
          reviewOutcome = adaptReviewOutcome(reviews[0]);
        }
      } catch {
        reviewOutcome = null;
      }

      const adapted = adaptApplication(rawApp, rawProfile, assessment, reviewOutcome);
      setApplication(adapted);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 404) {
        setError('Application not found');
      } else {
        const msg = err instanceof ApiError ? err.userMessage : 'Failed to load application details.';
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchApplicationDetails();
  }, [fetchApplicationDetails]);

  // Derive timeline stages based on application status
  const getTimelineStages = (status: ApplicationStatus, app: CreditApplication): TimelineStage[] => {
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
        description: 'Personal profile, gig credentials, and statutory DPDP consent artifact registered.',
        status: isStage2 ? 'COMPLETED' : status === 'SUBMITTED' ? 'ACTIVE' : 'COMPLETED',
        timestamp: new Date(app.submittedAt).toLocaleDateString('en-IN', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        }),
      },
      {
        id: 's2',
        title: 'Alternative Data Ingestion',
        description: 'KYC attestation verified; active telemetry linked across platform APIs.',
        status: isStage3
          ? 'COMPLETED'
          : status === 'DATA_VALIDATION'
          ? 'ACTIVE'
          : isStage2
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage3 ? 'Telemetry verified' : undefined,
      },
      {
        id: 's3',
        title: 'Cashflow Volatility Modeling',
        description: 'Income trends, cyclical dip rebounds, and micro-obligation cadences calculated.',
        status: isStage4
          ? 'COMPLETED'
          : status === 'FINANCIAL_ANALYSIS'
          ? 'ACTIVE'
          : 'PENDING',
        timestamp: isStage4 ? 'Model executed' : undefined,
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
        timestamp: app.assessment
          ? `Score: ${app.assessment.score} / 850`
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
            ? 'A certified credit reviewer is reviewing telemetry cross-checks and variance indicators.'
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
        timestamp: app.review?.recordedAt
          ? new Date(app.review.recordedAt).toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })
          : undefined,
      },
    ];
  };

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading Application Details...</h2>
        <p className="text-xs text-foreground-muted">Retrieving pipeline status and evaluation records.</p>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-8 border-border bg-surface space-y-4 text-center">
          <AlertCircle className="size-10 text-red-500 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">
              {error === 'Application not found' ? 'Application Not Found' : 'Unable to Load Application'}
            </h2>
            <p className="text-xs text-foreground-secondary">
              {error === 'Application not found'
                ? `No credit evaluation application exists with identifier ${id}.`
                : error}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/user/applications">
              <Button variant="outline" size="sm" className="rounded-full text-xs">
                <ArrowLeft className="size-3.5 mr-1" /> All Applications
              </Button>
            </Link>
            {error !== 'Application not found' && (
              <Button
                variant="default"
                size="sm"
                onClick={() => fetchApplicationDetails()}
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

  const stages = getTimelineStages(application.status, application);

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/user/applications">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs px-4 cursor-pointer">
              <ArrowLeft className="size-3.5" /> Back to Applications
            </Button>
          </Link>
          <span className="text-xs text-foreground-muted font-mono">
            {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground px-3.5 cursor-pointer"
          >
            <Printer className="size-3.5" /> Print Summary
          </Button>

          {application.assessment && (
            <Link href={`/user/results/${application.id}`}>
              <Button variant="default" size="sm" className="rounded-full gap-1.5 text-xs px-4 font-semibold cursor-pointer">
                <span>View Full Assessment Dossier</span>
                <ChevronRight className="size-3.5" />
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* 2. APPLICATION SUMMARY HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface dark:bg-surface-elevated border border-border shadow-xs space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-foreground-muted uppercase tracking-wider">
                Credit Evaluation Request
              </span>
              <StatusBadge status={application.status} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              {application.purpose}
            </h1>
          </div>

          <div className="text-left md:text-right">
            <div className="text-xs text-foreground-muted">Requested Amount</div>
            <div className="text-2xl sm:text-3xl font-extrabold text-foreground">
              {formatCurrency(application.requestedAmount)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-border">
          <div className="space-y-1">
            <span className="text-[11px] text-foreground-muted flex items-center gap-1">
              <Building2 className="size-3" /> Borrower Profile
            </span>
            <div className="text-xs font-semibold text-foreground">
              {application.applicantName}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-foreground-muted flex items-center gap-1">
              <UserCheck className="size-3" /> Employment Model
            </span>
            <div className="text-xs font-semibold text-foreground">
              {application.employmentType.replace('_', ' ')}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-foreground-muted flex items-center gap-1">
              <Calendar className="size-3" /> Submitted Date
            </span>
            <div className="text-xs font-semibold text-foreground">
              {new Date(application.submittedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-foreground-muted flex items-center gap-1">
              <Sparkles className="size-3" /> Evaluation Tier
            </span>
            <div>
              <RiskBadge riskLevel={application.assessment?.riskLevel || 'MODERATE_ESTIMATED RISK'} />
            </div>
          </div>
        </div>
      </div>

      {/* 3. STEP-BY-STEP EVALUATION PIPELINE LIFECYCLE */}
      <section className="space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-foreground">
            Evaluation Pipeline Progress
          </h2>
          <p className="text-xs text-foreground-muted">
            Auditable tracking of each stage in the PARAKH alternative assessment workflow.
          </p>
        </div>

        <div className="space-y-3">
          {stages.map((stage, index) => (
            <Card
              key={stage.id}
              className={`p-5 transition-all border ${
                stage.status === 'ACTIVE'
                  ? 'border-primary/40 bg-primary/5 shadow-xs'
                  : stage.status === 'COMPLETED'
                  ? 'border-border bg-surface'
                  : 'border-border/60 bg-surface/50 opacity-65'
              }`}
            >
              <div className="flex items-start gap-4">
                {/* Step indicator */}
                <div
                  className={`size-8 rounded-full flex items-center justify-center shrink-0 font-mono font-bold text-xs ${
                    stage.status === 'COMPLETED'
                      ? 'bg-primary text-primary-foreground'
                      : stage.status === 'ACTIVE'
                      ? 'bg-primary/20 text-primary border-2 border-primary animate-pulse'
                      : 'bg-surface-highlight border border-border text-foreground-muted'
                  }`}
                >
                  {stage.status === 'COMPLETED' ? (
                    <CheckCircle2 className="size-4.5 stroke-[2.5]" />
                  ) : (
                    index + 1
                  )}
                </div>

                <div className="flex-1 space-y-1">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                    <h3
                      className={`text-sm font-semibold ${
                        stage.status === 'ACTIVE' ? 'text-foreground' : 'text-foreground-secondary'
                      }`}
                    >
                      {stage.title}
                    </h3>
                    {stage.timestamp && (
                      <span className="text-[11px] text-foreground-muted font-mono">
                        {stage.timestamp}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-foreground-muted leading-relaxed">
                    {stage.description}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* 4. UNDERWRITER REVIEW SECTION IF RECORDED */}
      {application.review && (
        <section className="space-y-3">
          <h2 className="text-lg font-bold text-foreground">
            Credit Reviewer Readout
          </h2>
          <Card className="p-5 space-y-3 border-border bg-surface">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">
                Review Status: {application.review.status.replace(/_/g, ' ')}
              </span>
              <span className="text-xs text-foreground-muted">
                Reviewer: {application.review.underwriterName || 'Underwriting Officer'}
              </span>
            </div>
            {application.review.decisionNotes && (
              <p className="text-xs text-foreground-secondary bg-surface-highlight p-3 rounded-lg border border-border">
                &ldquo;{application.review.decisionNotes}&rdquo;
              </p>
            )}
          </Card>
        </section>
      )}
    </PageTransition>
  );
}
