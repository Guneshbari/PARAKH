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
  Pencil,
  Briefcase,
  Clock,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { formatCurrency } from '@/lib/utils';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplicantProfileUpdate,
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

  // DPDP Consent preferences state (persistent PostgreSQL backed)
  const [consentBenchmark, setConsentBenchmark] = useState<boolean>(false);
  const [consentRealtime, setConsentRealtime] = useState<boolean>(false);
  const [consentAlerts, setConsentAlerts] = useState<boolean>(false);
  const [loadingPreferences, setLoadingPreferences] = useState<boolean>(false);
  const [savingPreferenceKey, setSavingPreferenceKey] = useState<string | null>(null);
  const [preferenceSuccess, setPreferenceSuccess] = useState<string | null>(null);
  const [preferenceError, setPreferenceError] = useState<string | null>(null);

  // Applicant Profile Editing State (persistent PostgreSQL backed via PATCH /api/v1/applicants/{id})
  const [isEditingProfile, setIsEditingProfile] = useState<boolean>(false);
  const [isSavingProfile, setIsSavingProfile] = useState<boolean>(false);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [profileEditError, setProfileEditError] = useState<string | null>(null);

  // Profile Form Field States
  const [editGigWorkType, setEditGigWorkType] = useState<string>('');
  const [editYearsWorking, setEditYearsWorking] = useState<string>('');
  const [editAverageWorkingDays, setEditAverageWorkingDays] = useState<string>('');
  const [editLoanPurpose, setEditLoanPurpose] = useState<string>('');

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

      // 2. Fetch DPDP Consent Preferences
      try {
        setLoadingPreferences(true);
        const prefs = await api.getConsentPreferences();
        setConsentBenchmark(Boolean(prefs.consent_benchmark));
        setConsentRealtime(Boolean(prefs.consent_realtime));
        setConsentAlerts(Boolean(prefs.consent_alerts));
      } catch (prefErr: unknown) {
        console.warn('Could not load consent preferences:', prefErr);
      } finally {
        setLoadingPreferences(false);
      }

      if (!rawProfile) {
        setApplications([]);
        setConsents([]);
        setFinancialSignals([]);
        setIsLoading(false);
        return;
      }

      // 3. Fetch Applications for this profile
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

      // 4. If applications exist, fetch consents and financial signals for latest application
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

  const handleTogglePreference = async (
    key: 'consent_benchmark' | 'consent_realtime' | 'consent_alerts',
    nextValue: boolean
  ) => {
    setSavingPreferenceKey(key);
    setPreferenceError(null);
    setPreferenceSuccess(null);

    const prevValue =
      key === 'consent_benchmark'
        ? consentBenchmark
        : key === 'consent_realtime'
        ? consentRealtime
        : consentAlerts;

    // Optimistically update local state
    if (key === 'consent_benchmark') setConsentBenchmark(nextValue);
    if (key === 'consent_realtime') setConsentRealtime(nextValue);
    if (key === 'consent_alerts') setConsentAlerts(nextValue);

    try {
      const updated = await api.updateConsentPreferences({ [key]: nextValue });
      setConsentBenchmark(Boolean(updated.consent_benchmark));
      setConsentRealtime(Boolean(updated.consent_realtime));
      setConsentAlerts(Boolean(updated.consent_alerts));

      const label =
        key === 'consent_benchmark'
          ? 'Anonymized Volatility Benchmarking'
          : key === 'consent_realtime'
          ? 'Continuous Telemetry Refresh'
          : 'Volatile Shock Rebound Alerts';
      setPreferenceSuccess(
        `${label} ${nextValue ? 'granted and persisted' : 'revoked and saved'} to database.`
      );
      setTimeout(() => setPreferenceSuccess(null), 3500);
    } catch (err: unknown) {
      // Revert on error
      if (key === 'consent_benchmark') setConsentBenchmark(prevValue);
      if (key === 'consent_realtime') setConsentRealtime(prevValue);
      if (key === 'consent_alerts') setConsentAlerts(prevValue);

      const msg =
        err instanceof ApiError ? err.userMessage : 'Failed to update consent preference. Changes reverted.';
      setPreferenceError(msg);
      setTimeout(() => setPreferenceError(null), 5000);
    } finally {
      setSavingPreferenceKey(null);
    }
  };

  const handleStartEditProfile = () => {
    if (!profile) return;
    setEditGigWorkType(profile.gig_work_type || profile.work_type || '');
    setEditYearsWorking(
      profile.years_working !== null && profile.years_working !== undefined
        ? String(profile.years_working)
        : ''
    );
    setEditAverageWorkingDays(
      profile.average_working_days !== null && profile.average_working_days !== undefined
        ? String(profile.average_working_days)
        : ''
    );
    setEditLoanPurpose(profile.business_or_loan_purpose || '');
    setProfileEditError(null);
    setProfileSuccess(null);
    setIsEditingProfile(true);
  };

  const handleCancelEditProfile = () => {
    setIsEditingProfile(false);
    setProfileEditError(null);
  };

  const handleSaveProfile = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!profile) return;

    const trimmedWorkType = editGigWorkType.trim();
    if (!trimmedWorkType || trimmedWorkType.length < 2) {
      setProfileEditError('Gig work type must be at least 2 characters.');
      return;
    }

    const payload: BackendApplicantProfileUpdate = {
      gig_work_type: trimmedWorkType,
    };

    if (editYearsWorking.trim() !== '') {
      const parsedYears = parseFloat(editYearsWorking);
      if (isNaN(parsedYears) || parsedYears < 0 || parsedYears > 50) {
        setProfileEditError('Years of platform work must be a number between 0 and 50.');
        return;
      }
      payload.years_working = parsedYears;
    }

    if (editAverageWorkingDays.trim() !== '') {
      const parsedDays = parseInt(editAverageWorkingDays, 10);
      if (isNaN(parsedDays) || parsedDays < 0 || parsedDays > 31) {
        setProfileEditError('Average working days must be an integer between 0 and 31.');
        return;
      }
      payload.average_working_days = parsedDays;
    }

    if (editLoanPurpose.trim() !== '') {
      payload.business_or_loan_purpose = editLoanPurpose.trim();
    }

    setIsSavingProfile(true);
    setProfileEditError(null);
    setProfileSuccess(null);

    try {
      const updated = await api.updateApplicantProfile(profile.id, payload);
      setProfile(updated);
      setIsEditingProfile(false);
      setProfileSuccess('Applicant profile updated successfully and persisted to PostgreSQL.');
      setTimeout(() => setProfileSuccess(null), 4000);
    } catch (err: unknown) {
      const msg =
        err instanceof ApiError ? err.userMessage : 'Failed to save applicant profile changes.';
      setProfileEditError(msg);
    } finally {
      setIsSavingProfile(false);
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

      {/* 2.5. GIG WORKER PROFILE & ASSESSMENT ATTRIBUTES */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground">
              Gig Worker Profile & Trade Credentials
            </h2>
            <p className="text-xs text-foreground-muted">
              Authoritative occupational profile used to calibrate alternative risk baselines.
            </p>
          </div>
          {profile && !isEditingProfile && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleStartEditProfile}
              data-testid="edit-profile-button"
              className="gap-1.5 text-xs rounded-full cursor-pointer border-border hover:bg-surface-highlight"
            >
              <Pencil className="size-3.5" />
              <span>Edit Profile</span>
            </Button>
          )}
        </div>

        {profileSuccess && (
          <div
            data-testid="profile-edit-success"
            className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 dark:text-emerald-400 rounded-xl text-xs sm:text-sm"
          >
            <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
            <span>{profileSuccess}</span>
          </div>
        )}

        {profileEditError && (
          <div
            data-testid="profile-edit-error"
            className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-500 dark:text-rose-400 rounded-xl text-xs sm:text-sm"
          >
            <AlertCircle className="size-4 shrink-0 text-rose-500" />
            <span>{profileEditError}</span>
          </div>
        )}

        {isEditingProfile ? (
          <Card className="p-6 space-y-6 bg-surface border-border shadow-card">
            <form onSubmit={handleSaveProfile} className="space-y-5" data-testid="profile-edit-form">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Gig Work Type */}
                <div className="space-y-1.5">
                  <label htmlFor="edit-gig-work-type" className="text-xs font-semibold uppercase tracking-wider text-foreground-muted flex items-center gap-1.5">
                    <Briefcase className="size-3.5 text-primary" />
                    <span>Gig Work Type / Trade <span className="text-rose-500">*</span></span>
                  </label>
                  <Input
                    id="edit-gig-work-type"
                    data-testid="edit-gig-work-type"
                    value={editGigWorkType}
                    onChange={(e) => setEditGigWorkType(e.target.value)}
                    placeholder="e.g. Ride Hailing, Food Delivery, Logistics"
                    disabled={isSavingProfile}
                    maxLength={100}
                    required
                  />
                  <p className="text-[11px] text-foreground-muted">Platform service type (min 2 chars, max 100).</p>
                </div>

                {/* Experience in Years */}
                <div className="space-y-1.5">
                  <label htmlFor="edit-years-working" className="text-xs font-semibold uppercase tracking-wider text-foreground-muted flex items-center gap-1.5">
                    <Clock className="size-3.5 text-primary" />
                    <span>Platform Experience (Years)</span>
                  </label>
                  <Input
                    id="edit-years-working"
                    data-testid="edit-years-working"
                    type="number"
                    step="0.1"
                    min="0"
                    max="50"
                    value={editYearsWorking}
                    onChange={(e) => setEditYearsWorking(e.target.value)}
                    placeholder="e.g. 2.5"
                    disabled={isSavingProfile}
                  />
                  <p className="text-[11px] text-foreground-muted">Years active on gig platforms (0 to 50 years).</p>
                </div>

                {/* Average Working Days per Month */}
                <div className="space-y-1.5">
                  <label htmlFor="edit-average-working-days" className="text-xs font-semibold uppercase tracking-wider text-foreground-muted flex items-center gap-1.5">
                    <Activity className="size-3.5 text-primary" />
                    <span>Active Days / Month</span>
                  </label>
                  <Input
                    id="edit-average-working-days"
                    data-testid="edit-average-working-days"
                    type="number"
                    step="1"
                    min="0"
                    max="31"
                    value={editAverageWorkingDays}
                    onChange={(e) => setEditAverageWorkingDays(e.target.value)}
                    placeholder="e.g. 26"
                    disabled={isSavingProfile}
                  />
                  <p className="text-[11px] text-foreground-muted">Average working days logged per month (0 to 31).</p>
                </div>

                {/* Business / Loan Purpose */}
                <div className="space-y-1.5">
                  <label htmlFor="edit-loan-purpose" className="text-xs font-semibold uppercase tracking-wider text-foreground-muted flex items-center gap-1.5">
                    <FileText className="size-3.5 text-primary" />
                    <span>Primary Credit Purpose</span>
                  </label>
                  <Input
                    id="edit-loan-purpose"
                    data-testid="edit-loan-purpose"
                    value={editLoanPurpose}
                    onChange={(e) => setEditLoanPurpose(e.target.value)}
                    placeholder="e.g. EV Battery Swap, Inventory, Working Capital"
                    disabled={isSavingProfile}
                    maxLength={255}
                  />
                  <p className="text-[11px] text-foreground-muted">Intended productive use for evaluated funds (max 255 chars).</p>
                </div>
              </div>

              {/* Form Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCancelEditProfile}
                  disabled={isSavingProfile}
                  data-testid="cancel-profile-button"
                  className="rounded-full text-xs gap-1.5 cursor-pointer"
                >
                  <X className="size-3.5" />
                  <span>Cancel</span>
                </Button>

                <Button
                  type="submit"
                  variant="default"
                  size="sm"
                  disabled={isSavingProfile}
                  data-testid="save-profile-button"
                  className="rounded-full text-xs gap-1.5 cursor-pointer"
                >
                  {isSavingProfile ? (
                    <>
                      <RefreshCw className="size-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="size-3.5" />
                      <span>Save Changes</span>
                    </>
                  )}
                </Button>
              </div>
            </form>
          </Card>
        ) : profile ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 space-y-2 bg-surface border-border">
              <div className="flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
                <span className="font-medium">Gig Work Type</span>
                <Briefcase className="size-3.5 text-primary" />
              </div>
              <div className="text-base sm:text-lg font-bold text-foreground" data-testid="profile-display-work-type">
                {profile.gig_work_type || profile.work_type || 'Not specified'}
              </div>
              <div className="text-xs text-foreground-secondary">
                Primary occupational category
              </div>
            </Card>

            <Card className="p-4 space-y-2 bg-surface border-border">
              <div className="flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
                <span className="font-medium">Experience</span>
                <Clock className="size-3.5 text-primary" />
              </div>
              <div className="text-base sm:text-lg font-bold text-foreground" data-testid="profile-display-experience">
                {profile.years_working !== null && profile.years_working !== undefined
                  ? `${profile.years_working} years`
                  : 'Not specified'}
              </div>
              <div className="text-xs text-foreground-secondary">
                Tenure on platform economy
              </div>
            </Card>

            <Card className="p-4 space-y-2 bg-surface border-border">
              <div className="flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
                <span className="font-medium">Monthly Days</span>
                <Activity className="size-3.5 text-primary" />
              </div>
              <div className="text-base sm:text-lg font-bold text-foreground" data-testid="profile-display-working-days">
                {profile.average_working_days !== null && profile.average_working_days !== undefined
                  ? `${profile.average_working_days} days / mo`
                  : 'Not specified'}
              </div>
              <div className="text-xs text-foreground-secondary">
                Active working frequency
              </div>
            </Card>

            <Card className="p-4 space-y-2 bg-surface border-border">
              <div className="flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
                <span className="font-medium">Credit Purpose</span>
                <FileText className="size-3.5 text-primary" />
              </div>
              <div className="text-base sm:text-lg font-bold text-foreground truncate" title={profile.business_or_loan_purpose || undefined} data-testid="profile-display-loan-purpose">
                {profile.business_or_loan_purpose || 'Not specified'}
              </div>
              <div className="text-xs text-foreground-secondary">
                Productive fund application
              </div>
            </Card>
          </div>
        ) : (
          <Card className="p-8 text-center space-y-3 bg-surface border-dashed border-border">
            <Briefcase className="size-8 text-foreground-secondary mx-auto" />
            <div className="space-y-1">
              <h3 className="text-sm sm:text-base font-semibold text-foreground">No Profile Record Found</h3>
              <p className="text-xs sm:text-sm text-foreground-secondary max-w-sm mx-auto">
                Submit an initial credit evaluation to create your verified applicant profile.
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
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-foreground">
              Privacy Safeguards & DPDP Consent Preferences
            </h2>
            <p className="text-xs text-foreground-secondary">
              Authoritative persistent consent preferences backed by PostgreSQL audit records.
            </p>
          </div>
          {loadingPreferences && (
            <div className="flex items-center gap-1.5 text-xs text-foreground-secondary">
              <RefreshCw className="size-3.5 animate-spin text-primary" />
              <span>Syncing preferences...</span>
            </div>
          )}
        </div>

        {preferenceSuccess && (
          <div
            data-testid="consent-preference-success"
            className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-md text-xs sm:text-sm"
          >
            <CheckCircle2 className="size-4 shrink-0 text-emerald-400" />
            <span>{preferenceSuccess}</span>
          </div>
        )}

        {preferenceError && (
          <div
            data-testid="consent-preference-error"
            className="flex items-center gap-2 p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-md text-xs sm:text-sm"
          >
            <AlertCircle className="size-4 shrink-0 text-rose-400" />
            <span>{preferenceError}</span>
          </div>
        )}

        <Card className="p-6 space-y-5 bg-surface border-border">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                  Anonymized Industry Volatility Benchmarking
                </h3>
                {savingPreferenceKey === 'consent_benchmark' && (
                  <span className="text-[11px] text-primary flex items-center gap-1">
                    <RefreshCw className="size-3 animate-spin" /> Saving...
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Allow your anonymized rebound speeds to train local gig economy resilience baselines.
              </p>
            </div>
            <input
              type="checkbox"
              id="consent-benchmark-toggle"
              data-testid="consent-benchmark-toggle"
              checked={consentBenchmark}
              disabled={loadingPreferences || savingPreferenceKey === 'consent_benchmark'}
              onChange={(e) => handleTogglePreference('consent_benchmark', e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1 disabled:opacity-50"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-4 border-t border-border">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                  Continuous Telemetry Refresh
                </h3>
                {savingPreferenceKey === 'consent_realtime' && (
                  <span className="text-[11px] text-primary flex items-center gap-1">
                    <RefreshCw className="size-3 animate-spin" /> Saving...
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Periodically update weekly inflow stability indicators as new platform payouts settle.
              </p>
            </div>
            <input
              type="checkbox"
              id="consent-realtime-toggle"
              data-testid="consent-realtime-toggle"
              checked={consentRealtime}
              disabled={loadingPreferences || savingPreferenceKey === 'consent_realtime'}
              onChange={(e) => handleTogglePreference('consent_realtime', e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1 disabled:opacity-50"
            />
          </div>

          <div className="flex items-start justify-between gap-4 pt-4 border-t border-border">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <h3 className="text-xs sm:text-sm font-semibold text-foreground">
                  Volatile Shock Rebound Alerts
                </h3>
                {savingPreferenceKey === 'consent_alerts' && (
                  <span className="text-[11px] text-primary flex items-center gap-1">
                    <RefreshCw className="size-3 animate-spin" /> Saving...
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Receive proactive notifications when your 10-day recovery velocity qualifies you for better credit limits.
              </p>
            </div>
            <input
              type="checkbox"
              id="consent-alerts-toggle"
              data-testid="consent-alerts-toggle"
              checked={consentAlerts}
              disabled={loadingPreferences || savingPreferenceKey === 'consent_alerts'}
              onChange={(e) => handleTogglePreference('consent_alerts', e.target.checked)}
              className="size-4 accent-primary rounded cursor-pointer mt-1 disabled:opacity-50"
            />
          </div>
        </Card>
      </section>
    </PageTransition>
  );
}
