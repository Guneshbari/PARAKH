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
        'Underwriter review performed in accordance with PARAKH explainability policy.',
      verificationItemsRequested:
        reviewAction === 'REQUEST_VERIFICATION' ? requestedItems : undefined,
      underwriterName: 'Priya Sharma (Senior Risk Underwriter)',
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <Link href="/admin/applications">
            <Button variant="outline" size="sm" className="rounded-xl gap-1.5 text-xs">
              <ArrowLeft className="size-3.5" /> Back to Queue
            </Button>
          </Link>
          <span className="text-xs text-muted-foreground font-mono">
            DOSSIER: {application.id}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-xl bg-white/[0.02] border border-white/[0.06] text-xs text-muted-foreground">
            <UserCheck className="size-3.5 text-teal-400" />
            <span>Reviewer: Priya Sharma (UW-402)</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-xl gap-1.5 text-xs text-muted-foreground hover:text-white"
          >
            <Printer className="size-3.5" /> Print Audit File
          </Button>
        </div>
      </div>

      {/* 2. APPLICANT HERO & CAPITAL REQUEST */}
      <div className="p-6 sm:p-7 rounded-2xl bg-[#0A162E] border border-white/[0.08] shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight font-mono">
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

          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300">
            <span className="font-bold text-white">{application.applicantName}</span>
            <span>•</span>
            <span>{application.phone}</span>
            <span>•</span>
            <span className="capitalize text-teal-300">
              {application.employmentType.replace(/_/g, ' ').toLowerCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
            <span className="flex items-center gap-1.5">
              <DollarSign className="size-3.5 text-teal-400" />
              Requested {formatCurrency(application.requestedAmount)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <Calendar className="size-3.5 text-teal-400" />
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
            <div className="mt-2 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-start gap-2">
              <AlertCircle className="size-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Underwriting Flag Reason:</span>
                <span>{application.triggerReason}</span>
              </div>
            </div>
          )}
        </div>

        {/* Score & Confidence Badge */}
        {assessment && (
          <div className="flex flex-col items-start md:items-end justify-center gap-1 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] shrink-0">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Alternative Credit Score
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-black text-white font-mono">
                {assessment.score}
              </span>
              <span className="text-xs text-muted-foreground">/ 850</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="text-teal-300 font-mono">
                {assessment.modelConfidence}% Confidence
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="text-muted-foreground">
                {assessment.estimatedRepaymentDifficulty}% Difficulty
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 3. CONTEXTUAL AI RISK SYNTHESIS CARD */}
      <AIInsightCard
        title="Underwriter Volatility Synthesis"
        insight="Borrower demonstrates robust shock recovery dynamics (10–14 days) following cyclical monsoon rainfall dips. Consistent micro-obligation settlements (98% on-time) confirm that weekly variance reflects seasonal gig rhythms rather than structural credit distress."
        detail="Tenure across Swiggy (18 months) and Urban Company (8 months) provides multi-channel diversification. Fixed debt commitments represent less than 10% of median weekly cashflow."
        dismissible={false}
      />

      {/* 4. VOLATILITY CASHFLOW CURVE & RESILIENCE ANALYSIS */}
      <CashflowVolatilityChart
        title="12-Week Verified Inflow Rhythm & Rebound Curve"
        recoveryRate={assessment ? assessment.volatilityProfile.recoveryRateAfterLowIncome * 100 : 94}
        className="bg-[#0A162E] border-white/[0.08]"
      />

      {/* 5. VOLATILITY ENGINE METRICS & PLATFORM TELEMETRY */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Volatility Metrics */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="size-4 text-teal-400" />
            Cashflow Volatility Profile
          </h3>

          <div className="space-y-3 text-xs divide-y divide-white/[0.04]">
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Income Volatility Index</span>
              <span className="font-mono font-bold text-white">0.28 (Controlled)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Shock Rebound Velocity</span>
              <span className="font-mono text-teal-300 font-bold">10–14 Days to Baseline</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Cyclical Dips Observed / Recovered</span>
              <span className="font-mono text-slate-200">3 Dips / 3 Recovered (100%)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Micro-Obligation Settlement Rate</span>
              <span className="font-mono text-teal-300 font-bold">98% Punctual (24 cycles)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Fixed Commitment Ratio</span>
              <span className="font-mono text-slate-200">8.8% of Average Inflow</span>
            </div>
          </div>
        </Card>

        {/* Connected Telemetry Feeds */}
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="size-4 text-teal-400" />
            Verified Ingestion Streams
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">Swiggy Partner Telemetry</span>
                <span className="text-[11px] text-muted-foreground">18 months • 4.85 ★ • 3,420 orders</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">Urban Company Connect</span>
                <span className="text-[11px] text-muted-foreground">8 months • 4.90 ★ • 312 tasks</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                Active Stream
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">Account Aggregator (HDFC Bank)</span>
                <span className="text-[11px] text-muted-foreground">Consent #AA-8910 • 12 mos data</span>
              </div>
              <Badge variant="mint" className="text-[10px] py-0 px-2">
                AA Verified
              </Badge>
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
              <div>
                <span className="font-bold text-white block">BBPS Micro-Repayments</span>
                <span className="text-[11px] text-muted-foreground">BESCOM, Indane, Airtel • 98% on-time</span>
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
          className="bg-[#0A162E] border-white/[0.08]"
        />
      )}

      {/* 7. HUMAN-IN-THE-LOOP UNDERWRITER CONTROL CONSOLE */}
      <Card className="p-6 sm:p-8 bg-[#0A162E] border-teal-500/30 shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
          <div className="space-y-1">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <UserCheck className="size-4 text-teal-400" />
              Human-in-the-Loop Underwriting Decision Console
            </h2>
            <p className="text-xs text-muted-foreground">
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
            <label className="text-xs font-semibold text-white block">
              Select Underwriter Action
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
                  desc: 'Complete underwriter audit and record decision rationale',
                },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  onClick={() => setReviewAction(btn.id as ReviewActionType)}
                  className={`p-3 rounded-2xl text-left border transition-all cursor-pointer ${
                    reviewAction === btn.id
                      ? 'border-teal-400 bg-teal-500/10 text-white shadow-md'
                      : 'border-white/[0.08] bg-white/[0.02] text-muted-foreground hover:text-white'
                  }`}
                >
                  <span className="font-bold text-xs block text-teal-300">{btn.label}</span>
                  <span className="text-[11px] text-muted-foreground block pt-0.5">
                    {btn.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Risk Level Assessment / Calibration */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-white block">
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
                      ? 'border-teal-400 bg-teal-500/10 text-teal-300 font-bold'
                      : 'border-white/[0.08] bg-white/[0.02] text-muted-foreground hover:text-white'
                  }`}
                >
                  {tier.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Verification Items (shown for REQUEST_VERIFICATION) */}
          {reviewAction === 'REQUEST_VERIFICATION' && (
            <div className="space-y-3 p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20">
              <label className="text-xs font-bold text-amber-300 block">
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
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-amber-400/20 text-amber-200 border-amber-400/40'
                          : 'bg-white/[0.02] text-muted-foreground border-white/[0.06] hover:text-white'
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
                  className="flex-1 text-xs px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.1] text-white focus:outline-none focus:border-teal-400"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddCustomItem}
                  className="rounded-xl text-xs h-8"
                >
                  Add Item
                </Button>
              </div>
            </div>
          )}

          {/* Decision Rationale Notes */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-white">
                Underwriter Qualitative Rationale & Decision Notes
              </label>
              <span className="text-[11px] text-muted-foreground">
                Minimum 10 characters required
              </span>
            </div>
            <textarea
              required
              rows={4}
              value={decisionNotes}
              onChange={(e) => setDecisionNotes(e.target.value)}
              placeholder="Record detailed underwriting commentary regarding income volatility rebound dynamics, alternative micro-obligations, and justifications for risk tier classification..."
              className="w-full text-xs p-3.5 rounded-2xl bg-white/[0.03] border border-white/[0.1] text-white focus:outline-none focus:border-teal-400 leading-relaxed resize-none"
            />
          </div>

          {/* Success Banner */}
          {recordSuccess && (
            <div className="p-4 rounded-2xl bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs flex items-center gap-2.5">
              <CheckCircle2 className="size-4 shrink-0" />
              <span>
                Underwriting decision committed to audit ledger successfully. Status updated to{' '}
                <strong className="text-white">
                  {application.status.replace(/_/g, ' ')}
                </strong>
                .
              </span>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex items-center justify-between pt-2">
            <Link href="/admin/applications">
              <Button variant="ghost" size="sm" className="rounded-xl text-xs text-muted-foreground">
                Cancel
              </Button>
            </Link>

            <Button
              type="submit"
              variant="lime"
              size="sm"
              disabled={decisionNotes.trim().length < 10}
              className="rounded-full text-xs font-bold gap-1.5 px-6 shadow-lg shadow-lime-400/10"
            >
              <Send className="size-3.5" /> Commit Audit Decision
            </Button>
          </div>
        </form>
      </Card>

      {/* 8. UNDERWRITER AUDIT LOG (If Review Recorded) */}
      {application.review && application.review.recordedAt && (
        <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-white flex items-center gap-2">
              <FileCheck className="size-4 text-teal-400" />
              Recorded Underwriting Audit File
            </h3>
            <span className="font-mono text-[11px] text-muted-foreground">
              Recorded at{' '}
              {new Date(application.review.recordedAt).toLocaleDateString('en-IN', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Underwriter:</span>
              <span className="text-white font-medium">
                {application.review.underwriterName} ({application.review.underwriterId})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Recorded Action:</span>
              <span className="text-teal-300 font-mono font-bold">
                {application.review.action}
              </span>
            </div>
            {application.review.decisionNotes && (
              <div className="pt-1 text-slate-300 leading-relaxed italic border-t border-white/[0.04]">
                &ldquo;{application.review.decisionNotes}&rdquo;
              </div>
            )}
          </div>
        </Card>
      )}

      {/* 9. LEGAL & GOVERNANCE SEPARATION NOTICE */}
      <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-muted-foreground flex items-start gap-3">
        <Info className="size-4 text-teal-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-300 block">
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
