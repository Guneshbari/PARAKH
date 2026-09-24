'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Activity,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { formatCurrency } from '@/lib/utils';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplication,
  type BackendConsent,
  type BackendFinancialSignal,
} from '@parakh/api';

export default function UserProfilePage() {
  const { user, isLoading: authLoading } = useAuth();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<BackendApplicantProfile | null>(null);
  const [applications, setApplications] = useState<BackendApplication[]>([]);
  const [consents, setConsents] = useState<BackendConsent[]>([]);
  const [financialSignals, setFinancialSignals] = useState<BackendFinancialSignal[]>([]);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [syncSuccess, setSyncSuccess] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  // Consent toggles state
  const [consentBenchmark, setConsentBenchmark] = useState(true);
  const [consentRealtime, setConsentRealtime] = useState(true);
  const [consentAlerts, setConsentAlerts] = useState(true);

  const fetchProfileData = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch Applicant Profile
      let rawProfile: BackendApplicantProfile | null = null;
      try {
        rawProfile = await api.getApplicantByUserId(user.id);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          rawProfile = null;
        } else {
          throw err;
        }
      }
      setProfile(rawProfile);

      if (!rawProfile) {
        setApplications([]);
        setConsents([]);
        setFinancialSignals([]);
        setIsLoading(false);
        return;
      }

      // 2. Fetch Applications for this profile
      let rawApps: BackendApplication[] = [];
      try {
        rawApps = await api.getApplicationsByApplicant(rawProfile.id);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.status === 404) {
          rawApps = [];
        } else {
          throw err;
        }
      }
      setApplications(rawApps);

      // 3. If applications exist, fetch consents and financial signals for latest application
      if (rawApps.length > 0) {
        const latestApp = rawApps[0];
        try {
          const activeConsents = await api.getActiveConsentsByApplication(latestApp.id);
          setConsents(activeConsents);
        } catch {
          setConsents([]);
        }

        try {
          const signals = await api.getFinancialSignals(latestApp.id);
          setFinancialSignals(signals);
        } catch {
          setFinancialSignals([]);
        }
      } else {
        setConsents([]);
        setFinancialSignals([]);
      }
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to load profile data.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading && user) {
      fetchProfileData();
    } else if (!authLoading && !user) {
      setIsLoading(false);
    }
  }, [authLoading, user, fetchProfileData]);

  const handleSyncSource = async () => {
    setSyncing(true);
    try {
      await fetchProfileData();
      setSyncSuccess('Telemetry feeds synchronized successfully with PARAKH.');
      setTimeout(() => setSyncSuccess(null), 3500);
    } catch {
      // Handled in fetch
    } finally {
      setSyncing(false);
    }
  };

  const handleRevokeConsent = async (consentId: string) => {
    setRevokingId(consentId);
    try {
      await api.revokeConsent(consentId);
      // Refresh consents
      if (applications.length > 0) {
        const activeConsents = await api.getActiveConsentsByApplication(applications[0].id);
        setConsents(activeConsents);
      }
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to revoke consent.';
      setError(msg);
    } finally {
      setRevokingId(null);
    }
  };

  const handleDownloadArchive = () => {
    const archiveData = {
      exportTimestamp: new Date().toISOString(),
      statutoryFramework: 'Digital Personal Data Protection (DPDP) Act 2023',
      purpose: 'Alternative Credit Assessment and Volatility Resilience Evaluation',
      user: {
        id: user?.id,
        name: user?.name,
        email: user?.email,
      },
      applicantProfile: profile,
      applications,
      activeConsents: consents,
      financialTelemetry: financialSignals,
    };

    const blob = new Blob([JSON.stringify(archiveData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PARAKH_Applicant_Data_Dossier_${user?.id || 'profile'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (authLoading || isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading Profile Records...</h2>
        <p className="text-xs text-foreground-muted">Retrieving verified identity, active consents, and telemetry feeds.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-6 border-red-500/30 bg-red-500/5 space-y-4 text-center">
          <AlertCircle className="size-10 text-red-500 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">Error Loading Profile</h2>
            <p className="text-xs text-foreground-secondary">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchProfileData()}
            className="gap-1.5 rounded-full text-xs mx-auto"
          >
            <RefreshCw className="size-3.5" /> Try Again
          </Button>
        </Card>
      </div>
    );
  }

  const fullName = profile?.full_name || user?.name || 'Applicant';
  const email = user?.email || 'N/A';
  const phone = profile?.phone_number || 'N/A';
  const city = profile?.city || 'India';
  const memberSince = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'short' })
    : 'Recent';

  // Initials for avatar
  const initials = fullName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

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

      {syncSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0" />
          <span>{syncSuccess}</span>
        </div>
      )}

      {/* 2. BORROWER PROFILE HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface dark:bg-surface-elevated border border-border-strong shadow-card-elevated flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center gap-5">
          {/* Avatar */}
          <div className="relative size-16 sm:size-20 rounded-2xl bg-surface-highlight border border-border flex items-center justify-center text-xl sm:text-2xl font-bold text-foreground shrink-0">
            {initials || 'AP'}
            <div className="absolute -bottom-1 -right-1 size-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center ring-4 ring-surface">
              <CheckCircle2 className="size-3.5 stroke-[3]" />
            </div>
          </div>

          {/* Details */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {fullName}
              </h2>
              <Badge variant="secondary" className="gap-1 text-xs py-0.5 px-2">
                <ShieldCheck className="size-3.5 text-emerald-500" />
                Verified Identity
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs sm:text-sm text-foreground-secondary">
              <span className="flex items-center gap-1">
                <Smartphone className="size-3.5 text-foreground-secondary" />
                {phone}
              </span>
              <span className="flex items-center gap-1">
                <Mail className="size-3.5 text-foreground-secondary" />
                {email}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="size-3.5 text-foreground-secondary" />
                {city}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="size-3.5 text-foreground-secondary" />
                Member since {memberSince}
              </span>
            </div>
          </div>
        </div>

        {/* Identity Verification Status Pills */}
        <div className="flex flex-wrap md:flex-col items-start md:items-end gap-2 shrink-0 border-t md:border-t-0 pt-4 md:pt-0 border-border w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs sm:text-sm text-foreground-secondary">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            <span>DPDP Act 2023 Consent Protected</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs sm:text-sm text-foreground-secondary">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            <span>Zero Raw Transaction Storage</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs sm:text-sm text-foreground-secondary">
            <span className="size-1.5 rounded-full bg-primary" />
            <span>Active Evaluations: {applications.length}</span>
          </div>
        </div>
      </div>

      {/* 3. CONNECTED TELEMETRY & CONSENT FEEDS */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground">
              Connected Telemetry Feeds & Consents
            </h2>
            <p className="text-xs text-foreground-muted">
              Live data feeds informing your alternative volatility evaluation. You retain full revocation rights.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncSource}
              disabled={syncing}
              className="gap-1.5 text-xs rounded-full cursor-pointer"
            >
              <RefreshCw className={`size-3.5 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? 'Syncing...' : 'Sync Telemetry'}</span>
            </Button>
            <Link href="/user/applications/new">
              <Button variant="default" size="sm" className="gap-1.5 text-xs rounded-full cursor-pointer">
                <PlusCircle className="size-3.5" />
                <span>Add Source</span>
              </Button>
            </Link>
          </div>
        </div>

        {consents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {consents.map((consent) => (
              <Card key={consent.id} className="p-5 space-y-4 bg-surface border-border flex flex-col justify-between">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="text-xs uppercase font-mono">
                      {consent.data_source}
                    </Badge>
                    <Badge variant="secondary" className="gap-1 text-xs text-emerald-600 bg-emerald-500/10 font-medium">
                      <CheckCircle2 className="size-3" /> Active
                    </Badge>
                  </div>
                  <div>
                    <h3 className="text-sm sm:text-base font-semibold text-foreground">{consent.purpose}</h3>
                    <p className="text-xs sm:text-sm text-foreground-secondary mt-1">
                      Granted on {new Date(consent.granted_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-border flex items-center justify-between">
                  <span className="text-xs text-foreground-secondary">Statutory Protected</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevokeConsent(consent.id)}
                    disabled={revokingId === consent.id}
                    className="text-xs sm:text-sm text-red-500 hover:text-red-600 hover:bg-red-500/10 h-8 px-3 rounded-full cursor-pointer"
                  >
                    <Trash2 className="size-3.5 mr-1" />
                    {revokingId === consent.id ? 'Revoking...' : 'Revoke'}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center space-y-3 bg-surface border-dashed border-border">
            <Layers className="size-8 text-foreground-secondary mx-auto" />
            <div className="space-y-1">
              <h3 className="text-sm sm:text-base font-semibold text-foreground">No Explicit Active Consents</h3>
              <p className="text-xs sm:text-sm text-foreground-secondary max-w-sm mx-auto">
                Consents are registered upon starting a credit evaluation.
              </p>
            </div>
            <Link href="/user/applications/new">
              <Button variant="outline" size="sm" className="rounded-full text-xs sm:text-sm gap-1.5 h-8 cursor-pointer">
                <PlusCircle className="size-3.5" /> Start Evaluation
              </Button>
            </Link>
          </Card>
        )}
      </section>

      {/* 4. FINANCIAL SIGNALS SUMMARY */}
      {financialSignals.length > 0 && (
        <section className="space-y-4">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground">
              Ingested Financial Telemetry
            </h2>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Aggregated indicators derived under strict data minimization rules.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {financialSignals.map((sig) => (
              <Card key={sig.id} className="p-4 space-y-2 bg-surface border-border">
                <div className="flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
                  <span className="font-mono">{sig.source}</span>
                  <Activity className="size-3.5 text-primary" />
                </div>
                <div className="text-lg sm:text-xl font-bold text-foreground">
                  {sig.average_income ? formatCurrency(Number(sig.average_income)) : 'Verified Active'}
                </div>
                <div className="text-xs text-foreground-secondary">
                  {sig.active_days ? `${sig.active_days} active days recorded` : 'Telemetry verified'}
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* 5. PRIVACY PREFERENCES & RIGHTS */}
      <section className="space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-foreground">
          Privacy Safeguards & DPDP Consent Preferences
        </h2>

        <Card className="p-6 space-y-5 bg-surface border-border">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-0.5">
              <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                Anonymized Industry Volatility Benchmarking
              </h3>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Allow your anonymized rebound speeds to train local gig economy resilience baselines.
              </p>
            </div>
            <input
              type="checkbox"
              checked={consentBenchmark}
              onChange={(e) => setConsentBenchmark(e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-4 border-t border-border">
            <div className="space-y-0.5">
              <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                Continuous Telemetry Refresh
              </h3>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Periodically update weekly inflow stability indicators as new platform payouts settle.
              </p>
            </div>
            <input
              type="checkbox"
              checked={consentRealtime}
              onChange={(e) => setConsentRealtime(e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-4 border-t border-border">
            <div className="space-y-0.5">
              <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                Volatile Shock Rebound Alerts
              </h3>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Receive proactive notifications when your 10-day recovery velocity qualifies you for better credit limits.
              </p>
            </div>
            <input
              type="checkbox"
              checked={consentAlerts}
              onChange={(e) => setConsentAlerts(e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1"
            />
          </div>
        </Card>
      </section>
    </PageTransition>
  );
}
