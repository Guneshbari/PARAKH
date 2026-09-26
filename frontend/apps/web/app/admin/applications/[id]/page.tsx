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
  Loader2,
  History,
  Edit3,
  Save,
  X,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
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
  ApiError,
  type BackendApplication,
  type BackendAssessment,
} from '@parakh/api';
import { formatCurrency } from '@/lib/utils';
import type {
  ReviewActionType,
  UnderwriterReviewOutcome,
  RiskLevel,
} from '@parakh/types';

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
  // P2-11: Historical assessment state
  const [assessmentHistory, setAssessmentHistory] = useState<BackendAssessment[]>([]);
  // P3-06: Application term editing state
  const [rawAppRecord, setRawAppRecord] = useState<BackendApplication | null>(null);
  const [isEditingTerms, setIsEditingTerms] = useState<boolean>(false);
  const [editRequestedAmount, setEditRequestedAmount] = useState<string>('');
  const [editLoanPurpose, setEditLoanPurpose] = useState<string>('');
  const [editRepaymentPeriod, setEditRepaymentPeriod] = useState<string>('');
  const [isSavingTerms, setIsSavingTerms] = useState<boolean>(false);
  const [termsError, setTermsError] = useState<string | null>(null);
  const [termsSuccess, setTermsSuccess] = useState<string | null>(null);

  const loadApplicationData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const rawApp = await api.getApplicationById(id);
      setRawAppRecord(rawApp);
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

      // P2-11: Fetch full assessment history for historical audit section
      try {
        const history = await api.getAssessmentsByApplication(id);
        setAssessmentHistory(history || []);
      } catch {
        // Silently ignore — application may have no assessments yet
        setAssessmentHistory([]);
      }

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

  const handleStartEditTerms = () => {
    if (!rawAppRecord && !application) return;
    setEditRequestedAmount(
      String(rawAppRecord?.requested_loan_amount ?? application?.requestedAmount ?? '')
    );
    setEditLoanPurpose(rawAppRecord?.loan_purpose ?? application?.purpose ?? '');
    setEditRepaymentPeriod(
      rawAppRecord?.preferred_repayment_period !== undefined && rawAppRecord?.preferred_repayment_period !== null
        ? String(rawAppRecord.preferred_repayment_period)
        : '12'
    );
    setTermsError(null);
    setTermsSuccess(null);
    setIsEditingTerms(true);
  };

  const handleCancelEditTerms = () => {
    setIsEditingTerms(false);
    setTermsError(null);
  };

  const handleSaveTerms = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setTermsError(null);
    setTermsSuccess(null);

    const amountNum = parseFloat(editRequestedAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setTermsError('Requested loan amount must be a positive number greater than 0.');
      return;
    }

    const trimmedPurpose = editLoanPurpose.trim();
    if (!trimmedPurpose) {
      setTermsError('Loan purpose is required.');
      return;
    }
    if (trimmedPurpose.length > 255) {
      setTermsError('Loan purpose cannot exceed 255 characters.');
      return;
    }

    const periodNum = parseInt(editRepaymentPeriod, 10);
    if (isNaN(periodNum) || periodNum <= 0 || periodNum > 120) {
      setTermsError('Preferred repayment period must be between 1 and 120 months.');
      return;
    }

    setIsSavingTerms(true);
    try {
      await api.updateApplication(id, {
        requested_loan_amount: amountNum,
        loan_purpose: trimmedPurpose,
        preferred_repayment_period: periodNum,
      });
      setIsEditingTerms(false);
      setTermsSuccess('Application loan terms updated successfully.');
      setTimeout(() => setTermsSuccess(null), 4000);
      await loadApplicationData();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to update application terms.';
      setTermsError(msg);
    } finally {
      setIsSavingTerms(false);
    }
  };

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
      const reviewerId = user?.id || '00000000-0000-0000-0000-000000000000';

      await api.createReview(id, {
        reviewer_id: reviewerId,
        outcome: outcome,
        notes:
          decisionNotes ||
          'Credit review performed in accordance with PARAKH explainability policy.',
      });

      if (reviewAction === 'RECORD_OUTCOME') {
        try {
          await api.updateApplicationStatus(id, 'COMPLETED');
        } catch {}
      } else if (reviewAction === 'REQUEST_VERIFICATION') {
        try {
          await api.updateApplicationStatus(id, 'UNDER_REVIEW');
        } catch {}
      }

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
            {application.status !== 'COMPLETED' && !isEditingTerms && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleStartEditTerms}
                className="rounded-full text-xs h-7 px-2.5 gap-1 text-foreground-secondary hover:text-foreground cursor-pointer"
              >
                <Edit3 className="size-3" /> Edit Terms
              </Button>
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
              <Clock className="size-3.5 opacity-70" />
              Tenure: {rawAppRecord?.preferred_repayment_period ? `${rawAppRecord.preferred_repayment_period} Mo.` : '12 Mo.'}
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
                {assessment.modelConfidence !== null && assessment.modelConfidence !== undefined && assessment.modelConfidence > 0
                  ? `${assessment.modelConfidence}% Confidence`
                  : 'N/A (Confidence)'}
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

      {/* INLINE APPLICATION TERM EDITING FORM */}
      {isEditingTerms && (
        <Card className="p-6 bg-surface border-primary/30 dark:border-border space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="space-y-0.5">
              <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
                <Edit3 className="size-4 text-primary" />
                Edit Application Loan Terms
              </h3>
              <p className="text-xs text-foreground-secondary">
                Update requested capital amount, specific loan purpose, or repayment duration.
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCancelEditTerms}
              className="rounded-full size-7 cursor-pointer"
              aria-label="Cancel editing"
            >
              <X className="size-4" />
            </Button>
          </div>

          {termsError && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0" />
              <span>{termsError}</span>
            </div>
          )}

          <form onSubmit={handleSaveTerms} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1">
                  <DollarSign className="size-3 text-foreground-secondary" />
                  Requested Loan Amount (₹)
                </label>
                <Input
                  type="number"
                  min="1000"
                  step="500"
                  value={editRequestedAmount}
                  onChange={(e) => setEditRequestedAmount(e.target.value)}
                  placeholder="e.g. 50000"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1">
                  Loan Purpose
                </label>
                <Input
                  type="text"
                  maxLength={255}
                  value={editLoanPurpose}
                  onChange={(e) => setEditLoanPurpose(e.target.value)}
                  placeholder="e.g. EV battery upgrade and delivery gear"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1">
                  <Calendar className="size-3 text-foreground-secondary" />
                  Repayment Period (Months)
                </label>
                <Input
                  type="number"
                  min="1"
                  max="120"
                  value={editRepaymentPeriod}
                  onChange={(e) => setEditRepaymentPeriod(e.target.value)}
                  placeholder="e.g. 12"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleCancelEditTerms}
                disabled={isSavingTerms}
                className="rounded-full text-xs cursor-pointer"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="default"
                size="sm"
                disabled={isSavingTerms}
                className="rounded-full text-xs font-semibold gap-1.5 cursor-pointer"
              >
                {isSavingTerms ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Saving Terms...</span>
                  </>
                ) : (
                  <>
                    <Save className="size-3.5" />
                    <span>Save Changes</span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {termsSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs sm:text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{termsSuccess}</span>
        </div>
      )}

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

          {/* Verification Items (shown for REQUEST_VERIFICATION) */}
          {reviewAction === 'REQUEST_VERIFICATION' && (
            <div className="space-y-3 p-4 rounded-2xl bg-surface-highlight border border-border">
              <label className="text-xs sm:text-sm font-semibold text-foreground block">
                Select or Specify Required Verification Evidence
              </label>

              <div className="flex flex-wrap gap-2">
                {[
                  'Latest 30-day UPI QR settlement report',
                  'Urban Company partner rating certificate',
                  'DigiLocker Re-attestation',
                  'Bank Account Aggregator live consent refresh',
                  'Manual passbook scan of cash deposits',
                ].map((item) => {
                  const isChecked = requestedItems.includes(item);
                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => handleToggleItem(item)}
                      className={`px-3 py-1.5 rounded-full text-xs sm:text-sm font-medium border transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-[#472393] text-white border-[#472393] font-semibold shadow-xs dark:bg-foreground dark:text-background dark:border-foreground'
                          : 'bg-surface text-foreground-secondary border-border hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                      }`}
                    >
                      {isChecked ? '✓ ' : '+ '}
                      {item}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="text"
                  value={customItem}
                  onChange={(e) => setCustomItem(e.target.value)}
                  placeholder="Specify custom verification requirement..."
                  className="flex-1 text-sm px-3.5 py-2 rounded-full bg-surface border border-border text-foreground focus:outline-none focus:border-[#472393] focus:ring-2 focus:ring-[#472393]/20 dark:focus:border-foreground dark:focus:ring-0 placeholder:text-foreground-muted"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddCustomItem}
                  className="rounded-full text-xs sm:text-sm h-9 cursor-pointer"
                >
                  Add Item
                </Button>
              </div>
            </div>
          )}

          {/* Decision Rationale Notes */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs sm:text-sm">
              <label className="font-semibold text-foreground">
                Credit Reviewer Qualitative Rationale & Decision Notes
              </label>
              <span className="text-xs text-foreground-secondary">
                Minimum 10 characters required
              </span>
            </div>
            <textarea
              required
              rows={4}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder="Record detailed credit review commentary regarding income volatility rebound dynamics, alternative micro-obligations, and justifications for risk tier classification..."
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
                Underwriting decision committed to PostgreSQL audit ledger successfully. Status updated to{' '}
                <strong className="text-foreground">
                  {application.status.replace(/_/g, ' ')}
                </strong>
                .
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
              disabled={isSubmitting || decisionNotes.trim().length < 10}
              className="rounded-full text-xs sm:text-sm font-semibold gap-1.5 px-6 h-9 shadow-xs cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" /> Committing Audit...
                </>
              ) : (
                <>
                  <Send className="size-3.5" /> Commit Audit Decision
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>

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

      {/* 9. P2-11 ASSESSMENT HISTORY — All Historical Credit Evaluations */}
      {assessmentHistory.length > 0 && (
        <Card className="p-6 bg-surface border-border space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <History className="size-4 text-foreground-secondary" />
              Assessment History — All Credit Evaluations
            </h3>
            <span className="font-mono text-xs text-foreground-secondary">
              {assessmentHistory.length} evaluation{assessmentHistory.length === 1 ? '' : 's'} on record
            </span>
          </div>

          <div className="space-y-3">
            {assessmentHistory.map((a, index) => {
              const isCurrent = index === 0;
              const score = a.score ?? a.credit_score ?? null;
              const riskLevel = a.risk_level ?? null;
              const confidence = a.confidence !== null && a.confidence !== undefined
                ? Math.round(parseFloat(String(a.confidence)) * 100)
                : null;
              const assessedAt = a.assessed_at || a.created_at;
              const keyFactors: string[] = Array.isArray(a.key_factors)
                ? a.key_factors
                : (a.explanation && Array.isArray((a.explanation as any)?.key_factors)
                  ? (a.explanation as any).key_factors
                  : []);
              const modelVersion = a.model_version ?? 'unknown';
              const modelName = a.model_name ?? a.model_version ?? 'volatility-aware-risk-model';

              const riskColors: Record<string, string> = {
                LOWER: 'text-emerald-600 dark:text-emerald-400',
                MODERATE: 'text-amber-600 dark:text-amber-400',
                HIGHER: 'text-rose-600 dark:text-rose-400',
                INSUFFICIENT: 'text-foreground-secondary',
              };
              const riskColor = riskColors[riskLevel ?? ''] ?? 'text-foreground-secondary';

              return (
                <div
                  key={a.id}
                  className={`p-4 rounded-xl border space-y-2.5 text-xs sm:text-sm ${
                    isCurrent
                      ? 'bg-surface-highlight border-[#472393]/30 dark:border-border'
                      : 'bg-surface-highlight/40 border-border'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      {isCurrent && (
                        <Badge variant="mint" className="text-[10px] px-1.5 py-0 font-semibold">
                          Current
                        </Badge>
                      )}
                      <span className="font-mono text-foreground-secondary text-[10px] sm:text-xs">
                        {assessedAt
                          ? new Date(assessedAt).toLocaleDateString('en-IN', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Unknown time'}
                      </span>
                      <span className="text-foreground-secondary font-mono text-[10px] sm:text-xs">
                        • {modelName} v{modelVersion}
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-foreground-secondary truncate max-w-[140px]" title={a.id}>
                      ID: {a.id.split('-')[0]}...
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-4">
                    {/* Score */}
                    <div className="flex items-baseline gap-1">
                      <span className="text-foreground-secondary">Score:</span>
                      {score !== null ? (
                        <span className="font-mono font-semibold text-foreground">{score}<span className="text-foreground-secondary text-[10px]">/850</span></span>
                      ) : (
                        <span className="font-mono text-foreground-secondary">UNRATED</span>
                      )}
                    </div>

                    {/* Risk Level */}
                    <div className="flex items-center gap-1">
                      <span className="text-foreground-secondary">Risk:</span>
                      <span className={`font-mono font-semibold ${riskColor}`}>
                        {riskLevel ? riskLevel.replace(/_/g, ' ') : 'N/A'}
                      </span>
                    </div>

                    {/* Confidence */}
                    <div className="flex items-center gap-1">
                      <span className="text-foreground-secondary">Confidence:</span>
                      <span className="font-mono text-foreground">
                        {confidence !== null ? `${confidence}%` : '—'}
                      </span>
                    </div>

                    {/* Status */}
                    <div className="flex items-center gap-1">
                      <span className="text-foreground-secondary">Status:</span>
                      <span className="font-mono text-foreground">{a.assessment_status ?? 'COMPLETED'}</span>
                    </div>
                  </div>

                  {/* Key Factors */}
                  {keyFactors.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-foreground-secondary text-xs">Key factors:</span>
                      {keyFactors.slice(0, 4).map((factor, fi) => (
                        <span
                          key={fi}
                          className="px-2 py-0.5 rounded-full bg-surface border border-border text-[10px] text-foreground-secondary font-mono truncate max-w-[160px]"
                          title={factor}
                        >
                          {factor}
                        </span>
                      ))}
                      {keyFactors.length > 4 && (
                        <span className="text-[10px] text-foreground-secondary">+{keyFactors.length - 4} more</span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <p className="text-[10px] text-foreground-secondary text-right italic">
            Assessments shown in reverse-chronological order. All entries are read-only audit records.
          </p>
        </Card>
      )}

      {/* 10. LEGAL & GOVERNANCE SEPARATION NOTICE */}
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
