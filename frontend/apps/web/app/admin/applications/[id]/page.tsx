'use client';

import React, { use, useState } from 'react';
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
import { getAdminApplicationById } from '@/data/mock/admin';
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
  const initialApp = getAdminApplicationById(id);

  const [application, setApplication] = useState(initialApp);
  const [reviewAction, setReviewAction] = useState<ReviewActionType>(
    application.review?.action || 'MANUAL_REVIEW'
  );
  const [selectedRisk, setSelectedRisk] = useState<RiskLevel>(
    application.assessment?.riskLevel || 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW'
  );
  const [decisionNotes, setDecisionNotes] = useState(
    application.review?.decisionNotes || ''
  );
  const [requestedItems, setRequestedItems] = useState<string[]>(
    application.review?.verificationItemsRequested || [
      'Latest 30-day UPI QR settlement report',
    ]
  );
  const [customItem, setCustomItem] = useState('');
  const [recordSuccess, setRecordSuccess] = useState(false);

  const assessment = application.assessment;

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

  const handleSaveReview = (e: React.FormEvent) => {
    e.preventDefault();

    const outcome: UnderwriterReviewOutcome = {
      status:
        reviewAction === 'RECORD_OUTCOME'
          ? 'OUTCOME_RECORDED'
          : reviewAction === 'REQUEST_VERIFICATION'
          ? 'VERIFICATION_REQUESTED'
          : 'MANUAL_REVIEW_IN_PROGRESS',
      action: reviewAction,
      decisionNotes:
        decisionNotes ||
        'Credit review performed in accordance with PARAKH explainability policy.',
      verificationItemsRequested:
        reviewAction === 'REQUEST_VERIFICATION' ? requestedItems : undefined,
      underwriterName: 'Priya Sharma (Senior Credit Reviewer)',
      underwriterId: 'UW-402',
      recordedAt: new Date().toISOString(),
    };

    setApplication((prev) => ({
      ...prev,
      status:
        reviewAction === 'RECORD_OUTCOME'
          ? 'REVIEW_COMPLETED'
          : reviewAction === 'REQUEST_VERIFICATION'
          ? 'DATA_VALIDATION'
          : 'MANUAL_REVIEW_REQUIRED',
      assessment: prev.assessment
        ? {
            ...prev.assessment,
            riskLevel: selectedRisk,
          }
        : undefined,
      review: outcome,
    }));

    setRecordSuccess(true);
    setTimeout(() => setRecordSuccess(false), 4000);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP UTILITY BAR & OFFICER STAMP */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/admin/applications">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs">
              <ArrowLeft className="size-3.5" /> Back to Queue
            </Button>
          </Link>
          <span className="text-xs text-foreground-muted font-mono">
            DOSSIER: {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-surface-highlight border border-border text-xs text-foreground-secondary">
            <UserCheck className="size-3.5 opacity-70" />
            <span>Reviewer: Priya Sharma (UW-402)</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
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

          <div className="flex flex-wrap items-center gap-4 text-xs text-foreground-muted pt-1">
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
            <div className="mt-2 p-3 rounded-xl bg-surface-highlight border border-border text-xs text-foreground-secondary flex items-start gap-2">
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
            <span className="text-[11px] font-semibold text-foreground-muted uppercase tracking-wider">
              Alternative Credit Score
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-bold text-foreground font-mono">
                {assessment.score}
              </span>
              <span className="text-xs text-foreground-muted">/ 850</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="text-foreground-secondary font-mono font-medium">
                {assessment.modelConfidence}% Confidence
              </span>
              <span className="text-foreground-muted">•</span>
              <span className="text-foreground-muted">
                {assessment.estimatedRepaymentDifficulty}% Difficulty
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 3. CONTEXTUAL AI RISK SYNTHESIS CARD */}
      <AIInsightCard
        title="Credit Reviewer Volatility Synthesis"
        insight="Applicant demonstrates robust shock recovery dynamics (10–14 days) following cyclical monsoon rainfall dips. Consistent micro-obligation settlements (98% on-time) confirm that weekly variance reflects seasonal gig rhythms rather than structural credit distress."
        detail="Tenure across Swiggy (18 months) and Urban Company (8 months) provides multi-channel diversification. Fixed debt commitments represent less than 10% of median weekly cashflow."
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
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <TrendingUp className="size-4 text-foreground-secondary" />
            Cashflow Volatility Profile
          </h3>

          <div className="space-y-3 text-xs divide-y divide-border">
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Income Volatility Index</span>
              <span className="font-mono font-semibold text-foreground">0.28 (Controlled)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Shock Rebound Velocity</span>
              <span className="font-mono text-foreground font-semibold">10–14 Days to Baseline</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Cyclical Dips Observed / Recovered</span>
              <span className="font-mono text-foreground-secondary">3 Dips / 3 Recovered (100%)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Micro-Obligation Settlement Rate</span>
              <span className="font-mono text-foreground font-semibold">98% Punctual (24 cycles)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-foreground-muted">Fixed Commitment Ratio</span>
              <span className="font-mono text-foreground-secondary">8.8% of Average Inflow</span>
            </div>
          </div>
        </Card>

        {/* Connected Telemetry Feeds */}
        <Card className="p-6 bg-surface border-border space-y-4">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Layers className="size-4 text-foreground-secondary" />
            Verified Ingestion Streams
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Swiggy Partner Telemetry</span>
                <span className="text-[11px] text-foreground-muted">18 months • 4.85 ★ • 3,420 orders</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Urban Company Connect</span>
                <span className="text-[11px] text-foreground-muted">8 months • 4.90 ★ • 312 tasks</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">Account Aggregator (HDFC Bank)</span>
                <span className="text-[11px] text-foreground-muted">Consent #AA-8910 • 12 mos data</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                AA Verified
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
              <div>
                <span className="font-semibold text-foreground block">BBPS Micro-Repayments</span>
                <span className="text-[11px] text-foreground-muted">BESCOM, Indane, Airtel • 98% on-time</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
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
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <UserCheck className="size-4 text-foreground-secondary" />
              Human-in-the-Loop Underwriting Decision Console
            </h2>
            <p className="text-xs text-foreground-muted">
              Statutory credit underwriting workspace. Reviewers exercise independent judgment in evaluating alternative volatility evidence.
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            Officer: Priya Sharma
          </Badge>
        </div>

        <form onSubmit={handleSaveReview} className="space-y-5">
          {/* Action Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground block">
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
                      : 'border-border bg-surface-highlight text-foreground-muted hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
                  }`}
                >
                  <span className="font-semibold text-xs block">{btn.label}</span>
                  <span className="text-[11px] opacity-75 block pt-0.5">
                    {btn.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Risk Level Assessment / Calibration */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground block">
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
                  className={`p-2.5 rounded-xl text-xs font-medium border text-center transition-all cursor-pointer ${
                    selectedRisk === tier
                      ? 'border-[#472393] bg-[#472393] text-white font-semibold shadow-xs dark:border-foreground dark:bg-foreground dark:text-background'
                      : 'border-border bg-surface-highlight text-foreground-muted hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
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
              <label className="text-xs font-semibold text-foreground block">
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
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-[#472393] text-white border-[#472393] font-semibold shadow-xs dark:bg-foreground dark:text-background dark:border-foreground'
                          : 'bg-surface text-foreground-muted border-border hover:text-[#472393] hover:border-[rgba(71,35,147,0.3)] dark:hover:text-foreground dark:hover:border-border'
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
                  className="flex-1 text-xs px-3 py-1.5 rounded-full bg-surface border border-border text-foreground focus:outline-none focus:border-[#472393] focus:ring-2 focus:ring-[#472393]/20 dark:focus:border-foreground dark:focus:ring-0"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddCustomItem}
                  className="rounded-full text-xs h-8"
                >
                  Add Item
                </Button>
              </div>
            </div>
          )}

          {/* Decision Rationale Notes */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-foreground">
                Credit Reviewer Qualitative Rationale & Decision Notes
              </label>
              <span className="text-[11px] text-foreground-muted">
                Minimum 10 characters required
              </span>
            </div>
            <textarea
              required
              rows={4}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder="Record detailed credit review commentary regarding income volatility rebound dynamics, alternative micro-obligations, and justifications for risk tier classification..."
              className="w-full text-xs p-3.5 rounded-2xl bg-surface-highlight/30 border border-border text-foreground focus:outline-none focus:border-[#472393] dark:focus:border-foreground leading-relaxed resize-none"
            />
          </div>

          {/* Success Banner */}
          {recordSuccess && (
            <div className="p-4 rounded-2xl bg-surface-highlight border border-border text-foreground text-xs flex items-center gap-2.5">
              <CheckCircle2 className="size-4 shrink-0" />
              <span>
                Underwriting decision committed to audit ledger successfully. Status updated to{' '}
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
              <Button variant="ghost" size="sm" className="rounded-full text-xs text-foreground-muted hover:text-foreground">
                Cancel
              </Button>
            </Link>

            <Button
              type="submit"
              variant="default"
              size="sm"
              disabled={decisionNotes.trim().length < 10}
              className="rounded-full text-xs font-semibold gap-1.5 px-6 shadow-xs cursor-pointer"
            >
              <Send className="size-3.5" /> Commit Audit Decision
            </Button>
          </div>
        </form>
      </Card>

      {/* 8. UNDERWRITER AUDIT LOG (If Review Recorded) */}
      {application.review && application.review.recordedAt && (
        <Card className="p-6 bg-surface border-border space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-foreground flex items-center gap-2">
              <FileCheck className="size-4 text-foreground-secondary" />
              Recorded Underwriting Audit File
            </h3>
            <span className="font-mono text-[11px] text-foreground-muted">
              Recorded at{' '}
              {new Date(application.review.recordedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-foreground-muted">Credit Reviewer:</span>
              <span className="text-foreground font-medium">
                {application.review.underwriterName} ({application.review.underwriterId})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-foreground-muted">Recorded Action:</span>
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
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
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
