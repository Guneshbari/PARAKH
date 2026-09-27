'use client';

import React, { use, useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  Printer,
  Calendar,
  DollarSign,
  UserCheck,
  AlertCircle,
  TrendingUp,
  Layers,
  Info,
  Send,
  FileCheck,
  FileText,
  Clock,
  Loader2,
  Eye,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { AIInsightCard } from '@/components/shared/AIInsightCard';
import { FeatureContributionCard } from '@/components/shared/FeatureContributionCard';
import { CashflowVolatilityChart } from '@/components/shared/CashflowVolatilityChart';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  reverseAdaptReviewAction,
  adaptApplication,
  adaptAssessment,
  adaptReviewOutcome,
  adaptDocumentRequest,
  ApiError,
} from '@parakh/api';
import { formatCurrency } from '@/lib/utils';
import type {
  ReviewActionType,
  UnderwriterReviewOutcome,
  RiskLevel,
  DocumentRequest,
  DocumentType,
  AllowedFileType,
} from '@parakh/types';

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  BANK_STATEMENT: 'Bank Statement',
  INCOME_PROOF: 'Income Proof',
  TRANSACTION_STATEMENT: 'Transaction Statement',
  BUSINESS_RECORD: 'Business Record',
  OTHER: 'Other',
};

interface AdminApplicationDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function AdminApplicationDetailPage({
  params,
}: AdminApplicationDetailPageProps) {
  const { id } = use(params);
  const { user } = useAuth();

  const [application, setApplication] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewAction, setReviewAction] = useState<ReviewActionType>('MANUAL_REVIEW');
  const [selectedRisk, setSelectedRisk] = useState<RiskLevel>('INSUFFICIENT_EVIDENCE_MANUAL_REVIEW');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [requestedItems, setRequestedItems] = useState<string[]>([
    'Latest 30-day UPI QR settlement report',
  ]);
  const [customItem, setCustomItem] = useState('');
  const [recordSuccess, setRecordSuccess] = useState(false);

  // Structured Document Request Form State (Phase 1)
  const [documentRequests, setDocumentRequests] = useState<DocumentRequest[]>([]);
  const [docType, setDocType] = useState<DocumentType>('BANK_STATEMENT');
  const [allowedFormats, setAllowedFormats] = useState<{ pdf: boolean; excel: boolean }>({
    pdf: true,
    excel: true,
  });
  const [docDescription, setDocDescription] = useState('Please upload your latest 3-month bank statement.');

  // Document Review and File Download State (Phase 4)
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);
  const [reviewDecisions, setReviewDecisions] = useState<
    Record<string, { decision: 'ACCEPT' | 'REJECT'; notes: string }>
  >({});
  const [reviewSubmittingId, setReviewSubmittingId] = useState<string | null>(null);
  const [reviewErrors, setReviewErrors] = useState<Record<string, string>>({});

  const formatFileSize = (bytes: number): string => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDecisionChange = (requestId: string, decision: 'ACCEPT' | 'REJECT') => {
    setReviewDecisions((prev) => ({
      ...prev,
      [requestId]: {
        decision,
        notes: prev[requestId]?.notes || '',
      },
    }));
  };

  const handleNotesChange = (requestId: string, notes: string) => {
    setReviewDecisions((prev) => ({
      ...prev,
      [requestId]: {
        decision: prev[requestId]?.decision || 'ACCEPT',
        notes,
      },
    }));
  };

  const handleViewDocument = async (requestId: string) => {
    try {
      setDownloadingDocId(requestId);
      const { blob } = await api.downloadSubmittedDocumentFile(id, requestId, false);
      const fileUrl = URL.createObjectURL(blob);
      window.open(fileUrl, '_blank');
    } catch (err: any) {
      alert(err?.message || 'Failed to open document.');
    } finally {
      setDownloadingDocId(null);
    }
  };

  const handleDownloadDocument = async (requestId: string) => {
    try {
      setDownloadingDocId(requestId);
      const { blob, filename } = await api.downloadSubmittedDocumentFile(id, requestId, true);
      const fileUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = fileUrl;
      a.download = filename || 'document';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(fileUrl);
    } catch (err: any) {
      alert(err?.message || 'Failed to download document.');
    } finally {
      setDownloadingDocId(null);
    }
  };

  const [requestingReplacementId, setRequestingReplacementId] = useState<string | null>(null);

  const handleRequestReplacement = async (requestId: string) => {
    try {
      setRequestingReplacementId(requestId);
      await api.requestDocumentReplacementAdapted(id, requestId);
      await loadApplicationData();
    } catch (err: any) {
      alert(err?.message || 'Failed to request document replacement.');
    } finally {
      setRequestingReplacementId(null);
    }
  };

  const handleSubmitDocReview = async (requestId: string) => {
    const current = reviewDecisions[requestId] || { decision: 'ACCEPT', notes: '' };
    if (current.decision === 'REJECT' && (!current.notes || current.notes.trim().length < 5)) {
      setReviewErrors((prev) => ({
        ...prev,
        [requestId]: 'Reviewer notes of at least 5 characters are required when requesting replacement.',
      }));
      return;
    }

    try {
      setReviewSubmittingId(requestId);
      setReviewErrors((prev) => ({ ...prev, [requestId]: '' }));
      await api.reviewDocumentRequest(id, requestId, {
        decision: current.decision,
        notes: current.notes.trim() || undefined,
      });
      await loadApplicationData();
    } catch (err: any) {
      setReviewErrors((prev) => ({
        ...prev,
        [requestId]: err?.message || 'Failed to submit document review.',
      }));
    } finally {
      setReviewSubmittingId(null);
    }
  };

  const loadApplicationData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const rawApp = await api.getApplicationById(id);
      let profile = null;
      if (rawApp.applicant_profile_id) {
        try {
          profile = await api.getApplicantProfile(rawApp.applicant_profile_id);
        } catch {}
      }

      let assessment = null;
      try {
        // Authoritative: fetch persisted assessment from backend API first
        assessment = await api.getLatestAssessmentByApplication(id);
      } catch (err) {
        console.warn('Failed to fetch assessment from API, trying fallback:', err);
      }
      if (!assessment && typeof window !== 'undefined' && window.sessionStorage) {
        try {
          const cached = window.sessionStorage.getItem(`parakh_assessment_${id}`);
          if (cached) assessment = JSON.parse(cached);
        } catch {}
      }

      let reviews: any[] = [];
      try {
        reviews = await api.getReviewsByApplication(id);
      } catch {}

      const latestReview = reviews && reviews.length > 0 ? reviews[reviews.length - 1] : null;

      const adapted = adaptApplication(
        rawApp,
        profile,
        assessment ? adaptAssessment(assessment) : null,
        latestReview ? adaptReviewOutcome(latestReview) : null
      );

      const appData = {
        ...adapted,
        triggerReason:
          rawApp.status === 'MANUAL_REVIEW'
            ? 'Alternative cashflow volatility requires reviewer sign-off'
            : rawApp.status === 'UNDER_REVIEW'
            ? 'Inflow signals currently under aggregation'
            : 'Standard credit risk evaluation',
        sectorTag:
          profile?.work_type === 'GIG_WORKER'
            ? 'Urban Gig Delivery'
            : profile?.work_type === 'INFORMAL_VENDOR'
            ? 'Informal Commerce'
            : 'Micro-enterprise',
      };

      setApplication(appData);

      if (adapted.assessment?.riskLevel) {
        setSelectedRisk(adapted.assessment.riskLevel);
      }
      if (latestReview) {
        setReviewAction(
          latestReview.outcome === 'REVIEWED'
            ? 'RECORD_OUTCOME'
            : latestReview.outcome === 'ADDITIONAL_INFORMATION_REQUIRED'
            ? 'REQUEST_VERIFICATION'
            : 'MANUAL_REVIEW'
        );
        if (latestReview.notes) {
          setDecisionNotes(latestReview.notes);
        }
      }

      let docReqs: DocumentRequest[] = [];
      try {
        const rawDocs = await api.getDocumentRequests(id);
        docReqs = rawDocs.map(adaptDocumentRequest);
      } catch (err) {
        console.warn('Failed to fetch document requests:', err);
      }
      setDocumentRequests(docReqs);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setError('Application not found');
      } else {
        setError(err?.userMessage || err?.message || 'Failed to load application details. Please try again.');
      }
      setApplication(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadApplicationData();
  }, [id]);

  const assessment = application?.assessment;

  const handleToggleItem = (item: string) => {
    setRequestedItems((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const handleAddCustomItem = () => {
    if (customItem.trim() && !requestedItems.includes(customItem.trim())) {
      setRequestedItems((prev) => [...prev, customItem.trim()]);
      setCustomItem('');
    }
  };

  const handleSaveReview = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setIsSubmitting(true);
      setReviewError(null);
      const outcome = reverseAdaptReviewAction(reviewAction);

      const reviewPayload: any = {
        outcome: outcome,
        notes:
          decisionNotes ||
          (reviewAction === 'REQUEST_VERIFICATION'
            ? `Verification evidence requested: ${DOCUMENT_TYPE_LABELS[docType]} - ${docDescription.trim()}`
            : 'Credit review performed in accordance with PARAKH explainability policy.'),
      };
      if (user?.id) {
        reviewPayload.reviewer_id = user.id;
      }

      if (reviewAction === 'REQUEST_VERIFICATION') {
        const fileTypes: AllowedFileType[] = [];
        if (allowedFormats.pdf) fileTypes.push('PDF');
        if (allowedFormats.excel) {
          fileTypes.push('XLS');
          fileTypes.push('XLSX');
        }

        if (fileTypes.length === 0) {
          setReviewError('Please select at least one allowed format (PDF or Excel).');
          setIsSubmitting(false);
          return;
        }

        if (!docDescription.trim() || docDescription.trim().length < 5) {
          setReviewError('Request details must contain at least 5 characters.');
          setIsSubmitting(false);
          return;
        }

        reviewPayload.document_request = {
          document_type: docType,
          description: docDescription.trim(),
          allowed_file_types: fileTypes,
        };
      }

      await api.createReview(id, reviewPayload);

      await loadApplicationData();

      setRecordSuccess(true);
      setTimeout(() => setRecordSuccess(false), 4000);
    } catch (err: any) {
      console.error('Failed to submit review:', err);
      setReviewError(err?.message || 'Failed to submit review to backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-[#472393] border-t-transparent animate-spin mx-auto dark:border-foreground" />
        <h2 className="text-base font-semibold text-foreground">Loading Credit Review Dossier...</h2>
        <p className="text-xs text-foreground-muted">Retrieving applicant signals, model telemetry, and review history.</p>
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
              {error === 'Application not found' ? 'Application Not Found' : 'Unable to Load Application Dossier'}
            </h2>
            <p className="text-xs text-foreground-secondary">
              {error === 'Application not found'
                ? `No credit evaluation application exists with identifier ${id}.`
                : error}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link href="/admin/applications">
              <Button variant="outline" size="sm" className="rounded-full text-xs">
                <ArrowLeft className="size-3.5 mr-1" /> Review Queue
              </Button>
            </Link>
            {error !== 'Application not found' && (
              <Button
                variant="default"
                size="sm"
                onClick={loadApplicationData}
                className="rounded-full text-xs"
              >
                Retry
              </Button>
            )}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY BAR & OFFICER STAMP */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/admin/applications">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs sm:text-sm cursor-pointer">
              <ArrowLeft className="size-3.5" /> Back to Queue
            </Button>
          </Link>
          <span className="text-xs sm:text-sm text-foreground-secondary font-mono">
            DOSSIER: {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-surface-highlight border border-border text-xs sm:text-sm text-foreground-secondary">
            <UserCheck className="size-3.5 opacity-70" />
            <span>Reviewer: {user?.name || user?.email || 'Certified Reviewer'}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs sm:text-sm text-foreground-secondary hover:text-foreground cursor-pointer"
          >
            <Printer className="size-3.5" /> Print Audit File
          </Button>
        </div>
      </div>

      {/* 2. APPLICANT HERO & CAPITAL REQUEST */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface border border-border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight font-mono">
              {application.id}
            </h1>
            <StatusBadge status={application.status} />
            {assessment && (
              <RiskBadge
                riskLevel={assessment.riskLevel}
                showIcon={true}
                className="text-xs py-0.5 px-2.5"
              />
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 text-sm text-foreground-secondary">
            <span className="font-semibold text-foreground">{application.applicantName}</span>
            <span>•</span>
            <span>{application.phone}</span>
            <span>•</span>
            <span className="capitalize">
              {application.employmentType.replace(/_/g, ' ').toLowerCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs sm:text-sm text-foreground-secondary pt-1">
            <span className="flex items-center gap-1.5">
              <DollarSign className="size-3.5 opacity-70" />
              Requested {formatCurrency(application.requestedAmount)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <Calendar className="size-3.5 opacity-70" />
              Submitted {new Date(application.submittedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
            <span>•</span>
            <span>Purpose: {application.purpose}</span>
          </div>

          {application.triggerReason && (
            <div className="mt-2 p-3 rounded-xl bg-surface-highlight border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-2">
              <AlertCircle className="size-4 shrink-0 mt-0.5 opacity-80" />
              <div>
                <span className="font-semibold text-foreground block">Underwriting Flag Reason:</span>
                <span>{application.triggerReason}</span>
              </div>
            </div>
          )}
        </div>

        {/* Score & Confidence Badge */}
        {assessment && (
          <div className="flex flex-col items-start md:items-end justify-center gap-1 p-4 rounded-2xl bg-surface-highlight border border-border shrink-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-foreground-secondary uppercase tracking-wider">
                Alternative Credit Score
              </span>
              {assessment.modelName && (
                <span className="text-xs text-foreground-secondary font-mono lowercase">
                  • {assessment.modelName}
                </span>
              )}
            </div>
            {assessment.score !== null ? (
              <div className="flex items-baseline gap-1.5">
                <span className="text-3xl font-bold text-foreground font-mono">
                  {assessment.score}
                </span>
                <span className="text-sm text-foreground-secondary">/ 850</span>
              </div>
            ) : (
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-black text-foreground font-mono">
                  UNRATED
                </span>
                <span className="text-sm text-foreground-secondary font-medium">
                  (Insufficient Telemetry)
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-foreground-secondary font-mono font-medium">
                {assessment.modelConfidence !== null && assessment.modelConfidence > 0
                  ? `${assessment.modelConfidence}% Confidence`
                  : '0% Confidence'}
              </span>
              <span className="text-foreground-secondary">•</span>
              <span className="text-foreground-secondary">
                {assessment.estimatedRepaymentDifficulty !== null
                  ? `${assessment.estimatedRepaymentDifficulty}% Difficulty`
                  : 'Uncalculated'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 2.5 INSUFFICIENT EVIDENCE WARNING FOR REVIEWER */}
      {assessment && (assessment.isInsufficientEvidence || (assessment.missingSignals && assessment.missingSignals.length > 0)) && (
        <Card className="p-5 bg-surface border-amber-500/30 dark:border-amber-500/20 space-y-2.5">
          <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-semibold text-xs uppercase tracking-wider">
            <AlertCircle className="size-3.5" />
            <span>Manual Review Triggered: Evidence Threshold Not Met</span>
          </div>
          <p className="text-xs text-foreground-secondary leading-relaxed">
            The volatility-aware risk model refused score synthesis due to insufficient telemetry data. The following primary signals were missing:
          </p>
          <ul className="space-y-1.5 text-xs text-foreground pl-1">
            {(assessment.missingSignals || []).map((sig: string, i: number) => (
              <li key={i} className="flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-amber-500 shrink-0" />
                <span className="font-mono text-xs">{sig}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* 3. CONTEXTUAL AI RISK SYNTHESIS CARD */}
      <AIInsightCard
        title="Credit Reviewer Volatility Synthesis"
        insight={
          assessment?.isInsufficientEvidence
            ? "Model Refusal: Telemetry history is below the statutory observation window required for algorithmic risk evaluation. Human underwriter review is required."
            : "Applicant demonstrates robust shock recovery dynamics (10–14 days) following cyclical monsoon rainfall dips. Consistent micro-obligation settlements (98% on-time) confirm that weekly variance reflects seasonal gig rhythms rather than structural credit distress."
        }
        detail={
          assessment?.isInsufficientEvidence
            ? "Under DPDP Act 2023 and PARAKH model governance, scores are never fabricated or estimated when core cashflow telemetry is missing. Reviewer may request additional verification or record an informed credit outcome."
            : "Tenure across Swiggy (18 months) and Urban Company (8 months) provides multi-channel diversification. Fixed debt commitments represent less than 10% of median weekly cashflow."
        }
        dismissible={false}
      />

      {/* 4. VOLATILITY CASHFLOW CURVE & RESILIENCE ANALYSIS */}
      <CashflowVolatilityChart
        title="12-Week Verified Inflow Rhythm & Rebound Curve"
        recoveryRate={assessment ? assessment.volatilityProfile.recoveryRateAfterLowIncome * 100 : 94}
      />

      {/* 5. VOLATILITY ENGINE METRICS & PLATFORM TELEMETRY */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Volatility Metrics */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
            <TrendingUp className="size-4 text-foreground-secondary" />
            Cashflow Volatility Profile
          </h3>

          <div className="space-y-3 text-xs sm:text-sm divide-y divide-border">
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-secondary">Income Volatility Index</span>
              <span className="font-mono font-semibold text-foreground">0.28 (Controlled)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-secondary">Shock Rebound Velocity</span>
              <span className="font-mono text-foreground font-semibold">10–14 Days to Baseline</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-secondary">Cyclical Dips Observed / Recovered</span>
              <span className="font-mono text-foreground-secondary">3 Dips / 3 Recovered (100%)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-secondary">Micro-Obligation Settlement Rate</span>
              <span className="font-mono text-foreground font-semibold">98% Punctual (24 cycles)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-secondary">Fixed Commitment Ratio</span>
              <span className="font-mono text-foreground-secondary">8.8% of Average Inflow</span>
            </div>
          </div>
        </Card>

        {/* Connected Telemetry Feeds */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
            <Layers className="size-4 text-foreground-secondary" />
            Verified Ingestion Streams
          </h3>

          <div className="space-y-2.5 text-xs sm:text-sm">
            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Swiggy Partner Telemetry</span>
                <span className="text-xs text-foreground-secondary">18 months • 4.85 ★ • 3,420 orders</span>
              </div>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Urban Company Connect</span>
                <span className="text-xs text-foreground-secondary">8 months • 4.90 ★ • 312 tasks</span>
              </div>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Account Aggregator (HDFC Bank)</span>
                <span className="text-xs text-foreground-secondary">Consent #AA-8910 • 12 mos data</span>
              </div>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5">
                AA Verified
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">BBPS Micro-Repayments</span>
                <span className="text-xs text-foreground-secondary">BESCOM, Indane, Airtel • 98% on-time</span>
              </div>
              <Badge variant="mint" className="text-xs py-0.5 px-2.5">
                Punctual Track
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* 6. ML EXPLAINABILITY & SHAP FEATURE CONTRIBUTIONS */}
      {assessment && (
        <FeatureContributionCard
          contributions={assessment.featureContributions}
        />
      )}

      {/* 7. HUMAN-IN-THE-LOOP UNDERWRITER CONTROL CONSOLE */}
      <Card variant="elevated" className="p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
          <div className="space-y-1">
            <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
              <UserCheck className="size-4 text-foreground-secondary" />
              Human-in-the-Loop Underwriting Decision Console
            </h2>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Statutory credit underwriting workspace. Reviewers exercise independent judgment in evaluating alternative volatility evidence.
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            Officer: {user?.name || user?.email || 'Certified Reviewer'}
          </Badge>
        </div>

        <form onSubmit={handleSaveReview} className="space-y-5">
          {/* Action Selector */}
          <div className="space-y-2">
            <label className="text-xs sm:text-sm font-semibold text-foreground block">
              Select Reviewer Action
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {[
                {
                  id: 'MANUAL_REVIEW',
                  label: 'Manual Review In-Progress',
                  desc: 'Flag case for deep review without finalizing outcome',
                },
                {
                  id: 'REQUEST_VERIFICATION',
                  label: 'Request Verification',
                  desc: 'Request supplementary evidence or statement verification',
                },
                {
                  id: 'RECORD_OUTCOME',
                  label: 'Record Review Outcome',
                  desc: 'Complete credit review audit and record decision rationale',
                },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  onClick={() => setReviewAction(btn.id as ReviewActionType)}
                  className={`p-3 rounded-2xl text-left border transition-all cursor-pointer ${
                    reviewAction === btn.id
                      ? 'border-[#472393] bg-[#472393] text-white shadow-xs dark:border-foreground dark:bg-foreground dark:text-background'
                      : 'border-border bg-surface-highlight text-foreground-secondary hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                  }`}
                >
                  <span className="font-semibold text-sm block">{btn.label}</span>
                  <span className="text-xs opacity-80 block pt-0.5">
                    {btn.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Risk Level Assessment / Calibration */}
          <div className="space-y-2">
            <label className="text-xs sm:text-sm font-semibold text-foreground block">
              Calibrated Risk Classification
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                'LOWER_ESTIMATED RISK',
                'MODERATE_ESTIMATED RISK',
                'HIGHER_ESTIMATED RISK',
                'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW',
              ].map((tier) => (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setSelectedRisk(tier as RiskLevel)}
                  className={`p-2.5 rounded-xl text-xs sm:text-sm font-medium border text-center transition-all cursor-pointer ${
                    selectedRisk === tier
                      ? 'border-[#472393] bg-[#472393] text-white font-semibold shadow-xs dark:border-foreground dark:bg-foreground dark:text-background'
                      : 'border-border bg-surface-highlight text-foreground-secondary hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                  }`}
                >
                  {tier.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Structured Document Request Form (shown for REQUEST_VERIFICATION) */}
          {reviewAction === 'REQUEST_VERIFICATION' && (
            <div className="space-y-4 p-5 rounded-2xl bg-surface-highlight/40 border border-border">
              <div className="flex items-center gap-2">
                <FileText className="size-4 text-[#472393] dark:text-foreground" />
                <h4 className="text-xs sm:text-sm font-semibold text-foreground">
                  Request Additional Information
                </h4>
              </div>

              {/* Document Required Dropdown */}
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-foreground block">
                  Document required
                </label>
                <select
                  value={docType}
                  onChange={(e) => setDocType(e.target.value as DocumentType)}
                  className="w-full text-sm px-3.5 py-2.5 rounded-xl bg-surface border border-border text-foreground focus:outline-none focus:border-[#472393] dark:focus:border-foreground"
                >
                  <option value="BANK_STATEMENT">Bank Statement</option>
                  <option value="INCOME_PROOF">Income Proof</option>
                  <option value="TRANSACTION_STATEMENT">Transaction Statement</option>
                  <option value="BUSINESS_RECORD">Business Record</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              {/* Allowed Formats */}
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-foreground block">
                  Allowed format
                </label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-xs sm:text-sm text-foreground cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={allowedFormats.pdf}
                      onChange={(e) =>
                        setAllowedFormats((prev) => ({ ...prev, pdf: e.target.checked }))
                      }
                      className="size-4 rounded border-border text-[#472393] focus:ring-[#472393] accent-[#472393]"
                    />
                    <span>PDF</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs sm:text-sm text-foreground cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={allowedFormats.excel}
                      onChange={(e) =>
                        setAllowedFormats((prev) => ({ ...prev, excel: e.target.checked }))
                      }
                      className="size-4 rounded border-border text-[#472393] focus:ring-[#472393] accent-[#472393]"
                    />
                    <span>Excel</span>
                  </label>
                </div>
                {!allowedFormats.pdf && !allowedFormats.excel && (
                  <p className="text-xs text-destructive">At least one allowed format must be selected.</p>
                )}
              </div>

              {/* Request Details */}
              <div className="space-y-1.5">
                <label className="text-xs sm:text-sm font-medium text-foreground block">
                  Request details
                </label>
                <textarea
                  rows={3}
                  value={docDescription}
                  onChange={(e) => setDocDescription(e.target.value)}
                  placeholder="Please specify what document is required and details for the applicant..."
                  className="w-full text-sm p-3 rounded-xl bg-surface border border-border text-foreground focus:outline-none focus:border-[#472393] dark:focus:border-foreground leading-relaxed resize-none placeholder:text-foreground-muted"
                />
              </div>
            </div>
          )}

          {/* Decision Rationale Notes */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs sm:text-sm">
              <label className="font-semibold text-foreground">
                {reviewAction === 'REQUEST_VERIFICATION'
                  ? 'Internal Reviewer Notes (Optional)'
                  : 'Credit Reviewer Qualitative Rationale & Decision Notes'}
              </label>
              {reviewAction !== 'REQUEST_VERIFICATION' && (
                <span className="text-xs text-foreground-secondary">
                  Minimum 10 characters required
                </span>
              )}
            </div>
            <textarea
              required={reviewAction !== 'REQUEST_VERIFICATION'}
              rows={reviewAction === 'REQUEST_VERIFICATION' ? 2 : 4}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder={
                reviewAction === 'REQUEST_VERIFICATION'
                  ? 'Optional internal commentary on this verification request...'
                  : 'Record detailed credit review commentary regarding income volatility rebound dynamics, alternative micro-obligations, and justifications for risk tier classification...'
              }
              className="w-full text-sm p-3.5 rounded-2xl bg-surface-highlight/30 border border-border text-foreground focus:outline-none focus:border-[#472393] dark:focus:border-foreground leading-relaxed resize-none placeholder:text-foreground-muted"
            />
          </div>

          {/* Error Banner */}
          {reviewError && (
            <div className="p-4 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2.5">
              <AlertCircle className="size-4 shrink-0" />
              <span>{reviewError}</span>
            </div>
          )}

          {/* Success Banner */}
          {recordSuccess && (
            <div className="p-4 rounded-2xl bg-surface-highlight border border-border text-foreground text-sm flex items-center gap-2.5">
              <CheckCircle2 className="size-4 shrink-0" />
              <span>
                {reviewAction === 'REQUEST_VERIFICATION'
                  ? 'Document verification request created and status updated.'
                  : `Underwriting decision committed to PostgreSQL audit ledger successfully. Status updated to ${application.status.replace(/_/g, ' ')}.`}
              </span>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex items-center justify-between pt-2">
            <Link href="/admin/applications">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={isSubmitting}
                className="rounded-full text-xs sm:text-sm text-foreground-secondary hover:text-foreground cursor-pointer"
              >
                Cancel
              </Button>
            </Link>

            <Button
              type="submit"
              variant="default"
              size="sm"
              disabled={
                isSubmitting ||
                (reviewAction === 'REQUEST_VERIFICATION'
                  ? (!allowedFormats.pdf && !allowedFormats.excel) || docDescription.trim().length < 5
                  : decisionNotes.trim().length < 10)
              }
              className="rounded-full text-xs sm:text-sm font-semibold gap-1.5 px-6 h-9 shadow-xs cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />{' '}
                  {reviewAction === 'REQUEST_VERIFICATION' ? 'Requesting Document...' : 'Committing Audit...'}
                </>
              ) : (
                <>
                  <Send className="size-3.5" />{' '}
                  {reviewAction === 'REQUEST_VERIFICATION' ? 'Request Document' : 'Commit Audit Decision'}
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>

      {/* 8. APPLICANT SUBMITTED DOCUMENTS & DOCUMENT REVIEW (Phase 4) */}
      {documentRequests && documentRequests.length > 0 && (
        <Card className="p-6 bg-surface border-border space-y-5">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <FileText className="size-4.5 text-primary" />
                Applicant Submitted Documents
              </h3>
              <p className="text-xs text-foreground-secondary mt-0.5">
                Review, view, download, and verify requested applicant documentation.
              </p>
            </div>
            <Badge variant="outline" className="font-mono text-xs">
              {documentRequests.length} request{documentRequests.length > 1 ? 's' : ''}
            </Badge>
          </div>

          <div className="space-y-4">
            {documentRequests.map((req) => {
              const subDoc = req.submittedDocument;
              const currentReview = reviewDecisions[req.id] || { decision: 'ACCEPT', notes: '' };
              const isSubmittingReview = reviewSubmittingId === req.id;
              const isDownloading = downloadingDocId === req.id;
              const errorMsg = reviewErrors[req.id];

              return (
                <div
                  key={req.id}
                  className="p-5 rounded-xl bg-surface-highlight/40 border border-border space-y-4 text-xs sm:text-sm"
                >
                  {/* Top Bar: Title & Status */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm sm:text-base text-foreground">
                        {DOCUMENT_TYPE_LABELS[req.documentType] || req.documentType}
                      </span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full ${
                          req.status === 'PENDING'
                            ? 'border-amber-500/40 text-amber-600 bg-amber-500/10 dark:text-amber-400'
                            : req.status === 'SUBMITTED'
                            ? 'border-blue-500/40 text-blue-600 bg-blue-500/10 dark:text-blue-400'
                            : req.status === 'ACCEPTED'
                            ? 'border-emerald-500/40 text-emerald-600 bg-emerald-500/10 dark:text-emerald-400'
                            : 'border-destructive/40 text-destructive bg-destructive/10'
                        }`}
                      >
                        {req.status === 'REJECTED' ? 'REPLACEMENT REQUIRED' : req.status}
                      </Badge>
                    </div>
                    <span className="text-xs text-foreground-muted">
                      Requested {new Date(req.createdAt).toLocaleDateString('en-IN', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>

                  <p className="text-foreground-secondary leading-relaxed bg-surface/60 p-3 rounded-lg border border-border/60">
                    <span className="font-semibold text-foreground-secondary block text-xs mb-0.5">Instructions:</span>
                    {req.description}
                  </p>

                  {/* Submitted Document Information (If submitted) */}
                  {subDoc ? (
                    <div className="p-4 rounded-xl bg-surface border border-border space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-foreground block truncate">
                            {subDoc.originalFilename}
                          </span>
                          <span className="text-xs text-foreground-muted font-mono">
                            {formatFileSize(subDoc.fileSize)} • Submitted {new Date(subDoc.createdAt).toLocaleDateString('en-IN', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>

                        {/* View & Download Actions */}
                        <div className="flex items-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={isDownloading}
                            onClick={() => handleViewDocument(req.id)}
                            className="text-xs h-8 px-3 rounded-lg cursor-pointer"
                          >
                            <Eye className="size-3.5 mr-1" /> View Document
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            disabled={isDownloading}
                            onClick={() => handleDownloadDocument(req.id)}
                            className="text-xs h-8 px-3 rounded-lg cursor-pointer"
                          >
                            <Download className="size-3.5 mr-1" /> Download
                          </Button>
                        </div>
                      </div>

                      {/* Review Area: Only when SUBMITTED */}
                      {req.status === 'SUBMITTED' && (
                        <div className="mt-3 pt-3 border-t border-border space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                              Document Review
                            </span>
                          </div>

                          <div className="space-y-2">
                            <span className="text-xs font-medium text-foreground-secondary block">Status</span>
                            <div className="flex items-center gap-6">
                              <label className="flex items-center gap-2 cursor-pointer text-xs sm:text-sm">
                                <input
                                  type="radio"
                                  name={`decision-${req.id}`}
                                  value="ACCEPT"
                                  checked={currentReview.decision === 'ACCEPT'}
                                  onChange={() => handleDecisionChange(req.id, 'ACCEPT')}
                                  className="text-primary focus:ring-primary"
                                />
                                <span className="text-foreground font-medium">Accept</span>
                              </label>

                              <label className="flex items-center gap-2 cursor-pointer text-xs sm:text-sm">
                                <input
                                  type="radio"
                                  name={`decision-${req.id}`}
                                  value="REJECT"
                                  checked={currentReview.decision === 'REJECT'}
                                  onChange={() => handleDecisionChange(req.id, 'REJECT')}
                                  className="text-primary focus:ring-primary"
                                />
                                <span className="text-foreground font-medium">Request replacement</span>
                              </label>
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <label className="text-xs font-medium text-foreground-secondary block">
                              Reviewer notes {currentReview.decision === 'REJECT' && <span className="text-destructive">*</span>}
                            </label>
                            <textarea
                              rows={2}
                              value={currentReview.notes}
                              onChange={(e) => handleNotesChange(req.id, e.target.value)}
                              placeholder={
                                currentReview.decision === 'REJECT'
                                  ? 'State specific reasons why a replacement document is required...'
                                  : 'Optional notes on the accepted verification document...'
                              }
                              className="w-full text-xs sm:text-sm p-2.5 rounded-lg border border-border bg-surface-highlight/30 text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>

                          {errorMsg && (
                            <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-1.5">
                              <AlertCircle className="size-4 shrink-0" />
                              <span>{errorMsg}</span>
                            </div>
                          )}

                          <div className="flex justify-end pt-1">
                            <Button
                              type="button"
                              variant="default"
                              size="sm"
                              disabled={isSubmittingReview}
                              onClick={() => handleSubmitDocReview(req.id)}
                              className="text-xs font-semibold h-8 px-4 rounded-lg cursor-pointer"
                            >
                              {isSubmittingReview ? (
                                <>
                                  <Loader2 className="size-3.5 animate-spin mr-1" /> Submitting...
                                </>
                              ) : (
                                'Submit Review'
                              )}
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* ACCEPTED State Badge */}
                      {req.status === 'ACCEPTED' && (
                        <div className="mt-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs flex items-start gap-2 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="size-4 shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="font-semibold block">Document Verified & Accepted</span>
                            {req.reviewerNotes && (
                              <p className="text-foreground-secondary mt-1">
                                <span className="font-medium text-foreground">Reviewer Note: </span>
                                {req.reviewerNotes}
                              </p>
                            )}
                          </div>
                        </div>
                      )}

                      {/* REJECTED State Badge */}
                      {req.status === 'REJECTED' && (() => {
                        const hasPendingReplacement = documentRequests.some(
                          (r) => r.id !== req.id && r.documentType === req.documentType && (r.status === 'PENDING' || r.status === 'SUBMITTED')
                        );
                        return (
                          <div className="mt-2 p-3.5 rounded-lg bg-destructive/10 border border-destructive/20 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-destructive">
                            <div className="flex items-start gap-2">
                              <AlertCircle className="size-4 shrink-0 mt-0.5" />
                              <div className="space-y-0.5">
                                <span className="font-semibold block">Replacement Required (Rejected)</span>
                                {req.reviewerNotes && (
                                  <p className="text-foreground-secondary mt-1">
                                    <span className="font-medium text-foreground">Reason: </span>
                                    {req.reviewerNotes}
                                  </p>
                                )}
                              </div>
                            </div>
                            {hasPendingReplacement ? (
                              <Badge variant="outline" className="text-[11px] font-mono text-amber-600 bg-amber-500/10 border-amber-500/30 px-2.5 py-1 shrink-0">
                                Replacement Pending
                              </Badge>
                            ) : (
                              <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                disabled={requestingReplacementId === req.id}
                                onClick={() => handleRequestReplacement(req.id)}
                                className="text-xs h-8 px-3 rounded-lg shrink-0 cursor-pointer"
                              >
                                {requestingReplacementId === req.id ? (
                                  <>
                                    <Loader2 className="size-3.5 animate-spin mr-1" /> Requesting...
                                  </>
                                ) : (
                                  'Request Replacement'
                                )}
                              </Button>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-xl bg-surface/50 border border-dashed border-border text-xs text-foreground-muted flex items-center gap-2">
                      <Clock className="size-4 text-amber-500 shrink-0" />
                      <span>Awaiting applicant upload. No document has been submitted yet.</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 8. UNDERWRITER AUDIT LOG (If Review Recorded) */}
      {application.review && application.review.recordedAt && (
        <Card className="p-6 bg-surface border-border space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <FileCheck className="size-4 text-foreground-secondary" />
              Recorded Underwriting Audit File
            </h3>
            <span className="font-mono text-xs text-foreground-secondary">
              Recorded at{' '}
              {new Date(application.review.recordedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border space-y-1.5 text-xs sm:text-sm">
            <div className="flex justify-between">
              <span className="text-foreground-secondary">Credit Reviewer:</span>
              <span className="text-foreground font-medium">
                {application.review.underwriterName} ({application.review.underwriterId})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground-secondary">Recorded Action:</span>
              <span className="text-foreground font-mono font-semibold">
                {application.review.action}
              </span>
            </div>
            {application.review.decisionNotes && (
              <div className="pt-1 text-foreground-secondary leading-relaxed italic border-t border-border">
                &ldquo;{application.review.decisionNotes}&rdquo;
              </div>
            )}
          </div>
        </Card>
      )}

      {/* 9. LEGAL & GOVERNANCE SEPARATION NOTICE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Algorithmic Scoring vs. Certified Underwriting Legal Distinction
          </span>
          <p>
            PARAKH provides explainable alternative credit intelligence to quantify income volatility and shock rebound velocity. Underwriting decisions are made solely by authorized institutional officers in compliance with applicable credit policy. Automated lending decisions are prohibited.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
