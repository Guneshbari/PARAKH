'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Smartphone,
  Mail,
  MapPin,
  Calendar,
  Layers,
  RefreshCw,
  PlusCircle,
  Lock,
  Download,
  Trash2,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import {
  mockBorrowerProfile,
  mockConnectedDataSources,
  mockUserAssessment,
  type ConnectedDataSource,
} from '@/data/mock/user';
import { formatCurrency } from '@/lib/utils';

export default function UserProfilePage() {
  const [sources, setSources] = useState<ConnectedDataSource[]>(mockConnectedDataSources);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncedSuccessId, setSyncedSuccessId] = useState<string | null>(null);

  // Consent toggles state
  const [consentBenchmark, setConsentBenchmark] = useState(true);
  const [consentRealtime, setConsentRealtime] = useState(true);
  const [consentAlerts, setConsentAlerts] = useState(true);

  // Revocation modal/notice state
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const profile = mockBorrowerProfile;
  const assessment = mockUserAssessment;

  const handleSyncSource = (sourceId: string) => {
    setSyncingId(sourceId);
    setTimeout(() => {
      setSyncingId(null);
      setSyncedSuccessId(sourceId);
      setTimeout(() => setSyncedSuccessId(null), 3000);
    }, 1200);
  };

  const handleRevokeSource = (sourceId: string) => {
    setSources((prev) => prev.filter((s) => s.id !== sourceId));
    setRevokingId(null);
  };

  const handleDownloadArchive = () => {
    const archiveData = {
      profile,
      connectedSources: sources,
      volatilityProfile: assessment.volatilityProfile,
      consentArtifact: {
        id: 'CNS-2024-8910-ARJUN',
        statutoryFramework: 'Digital Personal Data Protection (DPDP) Act 2023',
        purpose: 'Alternative Credit Assessment and Volatility Resilience Evaluation',
        grantedAt: '2024-08-15T10:00:00Z',
        validUntil: '2027-08-15T10:00:00Z',
      },
    };

    const blob = new Blob([JSON.stringify(archiveData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PARAKH_Applicant_Data_Archive_${profile.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & BREADCRUMB */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Profile & Connected Sources
          </h1>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Manage your verified identity, gig platform telemetry, and data privacy consents.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownloadArchive}
            className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <Download className="size-3.5" /> Export Data Dossier
          </Button>
        </div>
      </div>

      {/* 2. BORROWER PROFILE HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface border border-border shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center gap-5">
          {/* Avatar */}
          <div className="relative size-16 sm:size-20 rounded-2xl bg-surface-highlight border border-border flex items-center justify-center text-xl sm:text-2xl font-bold text-foreground shrink-0">
            AV
            <div className="absolute -bottom-1 -right-1 size-5 rounded-full bg-foreground text-background flex items-center justify-center ring-4 ring-surface">
              <CheckCircle2 className="size-3.5 stroke-[3]" />
            </div>
          </div>

          {/* Details */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {profile.fullName}
              </h2>
              <Badge variant="mint" className="text-[10px] py-0.5 px-2">
                Active Assessment Profile
              </Badge>
              <Badge variant="outline" className="text-[10px] py-0.5 px-2 font-mono">
                {profile.id}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-foreground-muted">
              <span className="flex items-center gap-1">
                <Smartphone className="size-3.5 opacity-70" />
                {profile.phone}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Mail className="size-3.5 opacity-70" />
                {profile.email}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="size-3.5 opacity-70" />
                {profile.city}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
              <span className="text-foreground-muted flex items-center gap-1">
                <Calendar className="size-3.5 opacity-70" />
                Member since {profile.memberSince}
              </span>
              <span className="text-foreground-muted">•</span>
              <span className="text-foreground-secondary font-medium">
                {sources.length} Telemetry Connectors Active
              </span>
            </div>
          </div>
        </div>

        <Link href="/user/results/demo">
          <Button
            variant="pillOutline"
            size="sm"
            className="gap-2 text-xs shrink-0 px-4 rounded-full"
          >
            <Sparkles className="size-3.5 opacity-75" />
            <span>View Credit Dossier</span>
          </Button>
        </Link>
      </div>

      {/* 3. VERIFIED IDENTITY & ATTESTATIONS (KYC) */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="size-4 text-foreground-secondary" />
              Verified Identity Attestations (KYC)
            </h3>
            <p className="text-xs text-foreground-muted">
              Cryptographically validated identity documents linking informal earnings to your legal persona.
            </p>
          </div>
          <Badge variant="mint" className="text-[10px]">
            100% Attested
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">Aadhaar (UIDAI)</span>
              <CheckCircle2 className="size-3.5 text-foreground" />
            </div>
            <div className="text-xs text-foreground-muted font-mono">
              •••• •••• 9102
            </div>
            <Badge variant="outline" className="text-[10px]">
              DigiLocker Verified
            </Badge>
          </div>

          <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">PAN (NSDL)</span>
              <CheckCircle2 className="size-3.5 text-foreground" />
            </div>
            <div className="text-xs text-foreground-muted font-mono">
              ABCDE1234F
            </div>
            <Badge variant="outline" className="text-[10px]">
              Direct Attestation
            </Badge>
          </div>

          <div className="p-4 rounded-2xl bg-surface-highlight/40 border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground">Account Aggregator</span>
              <CheckCircle2 className="size-3.5 text-foreground" />
            </div>
            <div className="text-xs text-foreground-muted font-mono">
              HDFC Bank •••4912
            </div>
            <Badge variant="outline" className="text-[10px]">
              Sahamati AA Live
            </Badge>
          </div>
        </div>
      </Card>

      {/* 4. CONNECTED ALTERNATIVE TELEMETRY SOURCES */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Layers className="size-4 text-foreground-secondary" />
              Connected Alternative Data Streams
            </h3>
            <p className="text-xs text-foreground-muted">
              Real-time platform streams powering your volatility-aware assessment.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => alert('Connect New Stream: Zomato, Uber, Dunzo, or GSTIN can be linked in the partner onboarding workflow.')}
            className="rounded-full gap-1.5 text-xs text-foreground border-border hover:bg-surface-highlight"
          >
            <PlusCircle className="size-3.5" /> Connect New Platform
          </Button>
        </div>

        {/* Source Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sources.map((src) => {
            const isSyncing = syncingId === src.id;
            const isJustSynced = syncedSuccessId === src.id;

            return (
              <div
                key={src.id}
                className="p-4 rounded-2xl bg-surface-highlight/30 border border-border hover:border-border-strong transition-all space-y-3 relative group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-foreground">{src.name}</h4>
                      <span className="size-1.5 rounded-full bg-foreground ring-2 ring-foreground/20" />
                    </div>
                    <span className="text-[11px] text-foreground-muted">{src.provider}</span>
                  </div>

                  <Badge variant="mint" className="text-[10px] py-0 px-2">
                    {src.status}
                  </Badge>
                </div>

                {/* Metrics Breakdown */}
                <div className="grid grid-cols-2 gap-2 text-xs py-1 border-y border-border">
                  {src.details.tenureMonths && (
                    <div>
                      <span className="text-[10px] text-foreground-muted block">Tenure</span>
                      <span className="font-semibold text-foreground-secondary">
                        {src.details.tenureMonths} Months
                      </span>
                    </div>
                  )}
                  {src.details.monthlyAverage && (
                    <div>
                      <span className="text-[10px] text-foreground-muted block">Monthly Inflow</span>
                      <span className="font-mono font-semibold text-foreground-secondary">
                        {formatCurrency(src.details.monthlyAverage)}
                      </span>
                    </div>
                  )}
                  {src.details.rating && (
                    <div>
                      <span className="text-[10px] text-foreground-muted block">Platform Rating</span>
                      <span className="font-semibold text-foreground">
                        ★ {src.details.rating.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {src.details.completedTrips && (
                    <div>
                      <span className="text-[10px] text-foreground-muted block">Verified Deliveries</span>
                      <span className="font-semibold text-foreground-secondary">
                        {src.details.completedTrips}+ orders
                      </span>
                    </div>
                  )}
                  {src.details.onTimeRate && (
                    <div>
                      <span className="text-[10px] text-foreground-muted block">Punctuality</span>
                      <span className="font-semibold text-foreground font-mono">
                        {src.details.onTimeRate}% On-Time
                      </span>
                    </div>
                  )}
                  {src.details.accountMask && (
                    <div className="col-span-2">
                      <span className="text-[10px] text-foreground-muted block">Linked Scope</span>
                      <span className="font-mono text-foreground-muted text-[11px]">
                        {src.details.accountMask}
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions & Sync Timestamp */}
                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-[11px] text-foreground-muted">
                    Synced: {isJustSynced ? 'Just now' : src.lastSyncedAt}
                  </span>

                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={isSyncing}
                      onClick={() => handleSyncSource(src.id)}
                      className="h-7 px-2.5 rounded-full text-xs text-foreground-muted hover:text-foreground"
                    >
                      <RefreshCw
                        className={`size-3 mr-1 ${isSyncing ? 'animate-spin' : ''}`}
                      />
                      {isSyncing ? 'Syncing...' : isJustSynced ? 'Updated' : 'Sync'}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setRevokingId(src.id)}
                      className="h-7 px-2 rounded-full text-xs text-foreground-muted hover:text-rose-500"
                    >
                      <Trash2 className="size-3" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Revocation confirmation state / warning */}
        {revokingId && (
          <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="size-4 text-rose-500 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h5 className="text-xs font-bold text-foreground">
                  Confirm Revocation of Data Connector?
                </h5>
                <p className="text-[11px] text-foreground-secondary leading-relaxed">
                  Disconnecting this stream will cease real-time income ingestion. Past historical credit evaluations will remain archived for regulatory compliance, but future score updates will exclude this stream.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRevokingId(null)}
                className="h-7 rounded-full text-xs text-foreground-muted px-3"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleRevokeSource(revokingId)}
                className="h-7 rounded-full text-xs px-3"
              >
                Revoke Access
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* 5. VOLATILITY RESILIENCE SUMMARY */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
          <TrendingUp className="size-4 text-foreground-secondary" />
          Active Volatility & Resilience Footprint
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
          <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border space-y-1">
            <span className="text-[11px] text-foreground-muted block">Volatility Index</span>
            <span className="text-base font-bold text-foreground font-mono">0.28</span>
            <span className="text-[10px] text-foreground-secondary block">Controlled Variance</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border space-y-1">
            <span className="text-[11px] text-foreground-muted block">Shock Rebound</span>
            <span className="text-base font-bold text-foreground font-mono">10–14 Days</span>
            <span className="text-[10px] text-foreground-secondary block">Fast Recovery Pace</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border space-y-1">
            <span className="text-[11px] text-foreground-muted block">Micro-Repayment Rate</span>
            <span className="text-base font-bold text-foreground font-mono">98%</span>
            <span className="text-[10px] text-foreground-secondary block">Punctual Cadence</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface-highlight/40 border border-border space-y-1">
            <span className="text-[11px] text-foreground-muted block">Repayment Difficulty</span>
            <span className="text-base font-bold text-foreground font-mono">21%</span>
            <span className="text-[10px] text-foreground-muted block">Low Estimated Risk</span>
          </div>
        </div>
      </Card>

      {/* 6. DATA PRIVACY, CONSENT & DPDP ACT GOVERNANCE */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Lock className="size-4 text-foreground-secondary" />
              Consent Governance & DPDP Act 2023 Compliance
            </h3>
            <p className="text-xs text-foreground-muted">
              Granular controls over how your alternative income telemetry is utilized.
            </p>
          </div>

          <Badge variant="outline" className="text-[10px] font-mono">
            CNS-2024-8910-ARJUN
          </Badge>
        </div>

        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-foreground block">
                Continuous Telemetry Ingestion for Credit Resilience
              </span>
              <p className="text-[11px] text-foreground-muted">
                Allows PARAKH to compute rolling 12-week volatility and automatically recognize quick recovery from seasonal shock dips.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConsentRealtime(!consentRealtime)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                consentRealtime ? 'bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  consentRealtime ? 'bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-foreground block">
                Anonymized Gig Sector Benchmarking
              </span>
              <p className="text-[11px] text-foreground-muted">
                Permits fully anonymized seasonal rainfall benchmarks to adjust expectations for delivery partner cohorts across Bengaluru.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConsentBenchmark(!consentBenchmark)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                consentBenchmark ? 'bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  consentBenchmark ? 'bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-xs font-semibold text-foreground block">
                Credit Reviewer Clarification & Review SMS Alerts
              </span>
              <p className="text-[11px] text-foreground-muted">
                Receive notifications when a credit reviewer completes a human-in-the-loop review or requests supplementary documentation.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConsentAlerts(!consentAlerts)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                consentAlerts ? 'bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  consentAlerts ? 'bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-highlight/20 border border-border text-[11px] text-foreground-muted flex items-center justify-between">
          <span>
            Consent Artifact registered on {new Date().toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })} • Purpose: Alternative Creditworthiness
          </span>
          <span className="text-foreground-secondary font-medium">Valid until Aug 2027</span>
        </div>
      </Card>
    </PageTransition>
  );
}
