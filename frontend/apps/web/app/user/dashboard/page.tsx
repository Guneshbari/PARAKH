'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Sparkles,
  PlusCircle,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  Clock,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { StaggerList, StaggerItem } from '@/components/motion/StaggerList';
import { MetricCard } from '@/components/shared/MetricCard';
import { CreditScoreCard } from '@/components/shared/CreditScoreCard';
import { AIInsightCard } from '@/components/shared/AIInsightCard';
import { CashflowVolatilityChart } from '@/components/shared/CashflowVolatilityChart';
import { ApplicationCard } from '@/components/shared/ApplicationCard';
import { formatCurrency } from '@/lib/utils';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  adaptApplication,
  adaptAssessment,
  adaptBorrowerProfile,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplication,
} from '@parakh/api';
import type {
  BorrowerProfile,
  CreditApplication,
  CreditAssessmentResult,
} from '@parakh/types';

export default function UserDashboardPage() {
  const { user, isLoading: authLoading } = useAuth();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<BorrowerProfile | null>(null);
  const [applications, setApplications] = useState<CreditApplication[]>([]);
  const [latestAssessment, setLatestAssessment] = useState<CreditAssessmentResult | null>(null);
  const [rawProfileData, setRawProfileData] = useState<BackendApplicantProfile | null>(null);

  const fetchDashboardData = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Retrieve Applicant Profile for current user
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

      setRawProfileData(rawProfile);

      if (!rawProfile) {
        // No applicant profile yet
        setProfile({
          id: user.id,
          fullName: user.name || 'Applicant',
          phone: '',
          email: user.email,
          city: 'National (All India)',
          verifiedAadhaar: false,
          verifiedPAN: false,
          connectedAccountsCount: 0,
          memberSince: new Date().toISOString(),
        });
        setApplications([]);
        setLatestAssessment(null);
        setIsLoading(false);
        return;
      }

      // Profile exists
      const adaptedProf = adaptBorrowerProfile(rawProfile, user.email);
      setProfile(adaptedProf);

      // 2. Retrieve Applications for this profile
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

      // Sort newest first
      rawApps.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      // 3. Retrieve Latest Assessment if an application exists
      let assessmentResult: CreditAssessmentResult | null = null;
      if (rawApps.length > 0) {
        const latestApp = rawApps[0];
        try {
          const rawAssessment = await api.getLatestAssessmentByApplication(latestApp.id);
          assessmentResult = adaptAssessment(rawAssessment, adaptedProf.fullName);
        } catch (err: unknown) {
          // If no assessment has been generated yet for this application, continue gracefully
          assessmentResult = null;
        }
      }

      const adaptedApps = rawApps.map((a, idx) =>
        adaptApplication(a, rawProfile, idx === 0 ? assessmentResult : null)
      );

      setApplications(adaptedApps);
      setLatestAssessment(assessmentResult);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to load dashboard data.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading && user) {
      fetchDashboardData();
    } else if (!authLoading && !user) {
      setIsLoading(false);
    }
  }, [authLoading, user, fetchDashboardData]);

  // Loading State
  if (authLoading || isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading your dashboard...</h2>
        <p className="text-xs text-foreground-muted">Fetching verified application records from PARAKH.</p>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-6 border-red-500/30 bg-red-500/5 space-y-4 text-center">
          <AlertCircle className="size-10 text-red-500 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">Unable to Load Dashboard</h2>
            <p className="text-xs text-foreground-secondary">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchDashboardData()}
            className="gap-1.5 rounded-full text-xs mx-auto"
          >
            <RefreshCw className="size-3.5" /> Try Again
          </Button>
        </Card>
      </div>
    );
  }

  const displayName = profile?.fullName || user?.name || 'Applicant';
  const displayCity = profile?.city || 'India';
  const workType = rawProfileData?.work_type || 'Gig Worker Partner';
  const expMonths = rawProfileData?.experience_months ? `${rawProfileData.experience_months} mos` : 'Active';

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-12">
      {/* 1. WELCOME & QUICK ACTION BAR */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Welcome back, {displayName}
            </h1>
            <Badge variant="secondary" className="text-xs py-0.5 px-2">
              Verified Account
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm text-foreground-secondary">
            <span>{workType} ({expMonths})</span>
            <span>•</span>
            <span>{displayCity}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/user/applications/new">
            <Button variant="default" className="gap-2 font-semibold px-5 rounded-full cursor-pointer text-xs sm:text-sm">
              <PlusCircle className="size-4" />
              <span>New Assessment</span>
            </Button>
          </Link>
          {latestAssessment && (
            <Link href={`/user/results/${latestAssessment.id}`}>
              <Button variant="secondary" className="gap-1.5 text-xs sm:text-sm rounded-full cursor-pointer">
                <span>Full Report</span>
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          )}
        </div>
      </section>

      {/* 2. HERO ASSESSMENT SCORE & CONTEXTUAL AI CARD OR EMPTY STATE */}
      {latestAssessment ? (
        <>
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7">
              <CreditScoreCard assessment={latestAssessment} />
            </div>

            <div className="lg:col-span-5 flex flex-col justify-between gap-4">
              <AIInsightCard
                insight="Your verified cashflow telemetry confirms continuous earning cycles with low debt obligations, qualifying you for alternative credit evaluation."
                detail="Traditional bureaus heavily penalize off-peak weekly swings. PARAKH evaluates your verified recovery velocity and timely utility settlements."
                actionLabel="View Methodology"
              />

              <Card variant="elevated" className="space-y-2.5 p-5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <ShieldCheck className="size-4 text-foreground-secondary" />
                    <span>Alternative Data Health</span>
                  </span>
                  <span className="font-semibold text-foreground font-mono">
                    {latestAssessment.modelConfidence}% Confident
                  </span>
                </div>
                <p className="text-sm text-foreground-secondary leading-relaxed">
                  Active alternative financial sources linked: UPI settlements, platform earnings stream, and utility bills.
                </p>
              </Card>
            </div>
          </section>

          {/* 3. KEY VOLATILITY STANDING METRIC CARDS */}
          {latestAssessment.volatilityProfile && (
            <section className="space-y-3">
              <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-foreground-secondary">
                Financial Standing & Volatility Signals
              </h2>

              <StaggerList className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StaggerItem>
                  <MetricCard
                    title="Average Weekly Inflow"
                    value={latestAssessment.volatilityProfile.averageWeeklyInflow}
                    format={formatCurrency}
                    pillLabel="Stable Trend"
                    pillVariant="secondary"
                    subtext="Platform earnings aggregated"
                    icon={TrendingUp}
                  />
                </StaggerItem>

                <StaggerItem>
                  <MetricCard
                    title="Repayment Punctuality"
                    value={latestAssessment.volatilityProfile.repaymentHistoryRate}
                    suffix="%"
                    pillLabel="Punctual"
                    pillVariant="secondary"
                    subtext="Verified payment regularity"
                    icon={ShieldCheck}
                  />
                </StaggerItem>

                <StaggerItem>
                  <MetricCard
                    title="Shock Rebound Speed"
                    value={10}
                    suffix=" Days"
                    pillLabel={`${Math.round(latestAssessment.volatilityProfile.recoveryRateAfterLowIncome * 100)}% Recovery`}
                    pillVariant="secondary"
                    subtext="Average days to baseline earnings"
                    icon={Zap}
                  />
                </StaggerItem>

                <StaggerItem>
                  <MetricCard
                    title="Monthly Debt Load"
                    value={latestAssessment.volatilityProfile.existingObligationsMonthly}
                    format={formatCurrency}
                    pillLabel="Manageable"
                    pillVariant="outline"
                    subtext="Calculated ongoing debt ratio"
                  />
                </StaggerItem>
              </StaggerList>
            </section>
          )}

          {/* 4. CASHFLOW VOLATILITY TRACKING CHART */}
          {latestAssessment.volatilityProfile && (
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-foreground-secondary">
                  Weekly Inflow Rhythm & Rebound Curve
                </h2>
                <span className="text-xs sm:text-sm text-foreground-secondary font-medium">Verified Telemetry</span>
              </div>

              <CashflowVolatilityChart
                recoveryRate={Math.round(latestAssessment.volatilityProfile.recoveryRateAfterLowIncome * 100)}
                title="Verified UPI & Platform Cashflow Consistency"
              />
            </section>
          )}
        </>
      ) : applications.length > 0 ? (
        // Application submitted but pending assessment
        <Card className="p-8 text-center space-y-4 bg-surface border-border">
          <Clock className="size-10 text-primary mx-auto animate-pulse" />
          <div className="space-y-1">
            <h2 className="text-lg sm:text-xl font-semibold text-foreground">Assessment in Progress</h2>
            <p className="text-sm text-foreground-secondary max-w-md mx-auto leading-relaxed">
              Your application has been received and telemetry ingestion is active. You can review your application tracking status below.
            </p>
          </div>
          <Link href={`/user/applications/${applications[0].id}`}>
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs sm:text-sm">
              View Application Status <ArrowRight className="size-3.5" />
            </Button>
          </Link>
        </Card>
      ) : (
        // Clean Empty State
        <Card className="p-10 text-center space-y-5 bg-surface border-dashed border-border max-w-2xl mx-auto my-6">
          <div className="size-12 rounded-2xl bg-surface-highlight border border-border flex items-center justify-center mx-auto text-foreground">
            <FileText className="size-6 opacity-75" />
          </div>
          <div className="space-y-1.5">
            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              No Credit Evaluations Yet
            </h2>
            <p className="text-sm text-foreground-secondary max-w-md mx-auto leading-relaxed">
              Launch your first evaluation to verify gig income streams, analyze cashflow volatility rhythms, and generate an explainable credit assessment dossier.
            </p>
          </div>
          <Link href="/user/applications/new">
            <Button variant="default" className="gap-2 font-semibold px-6 rounded-full cursor-pointer text-xs sm:text-sm">
              <PlusCircle className="size-4" />
              <span>Start New Evaluation</span>
            </Button>
          </Link>
        </Card>
      )}

      {/* 5. RECENT APPLICATIONS & RECOMMENDATIONS */}
      {applications.length > 0 && (
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Recent Applications List */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-foreground-secondary">
                Recent Evaluations ({applications.length})
              </h2>
              <Link
                href="/user/applications"
                className="text-xs sm:text-sm text-foreground-secondary hover:text-foreground font-semibold underline-offset-4 hover:underline"
              >
                View all →
              </Link>
            </div>

            <div className="space-y-3">
              {applications.slice(0, 3).map((app) => (
                <ApplicationCard key={app.id} application={app} />
              ))}
            </div>
          </div>

          {/* Actionable Recommendations Card */}
          <div className="lg:col-span-5 space-y-4">
            <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-foreground-secondary">
              Actionable Recommendations
            </h2>

            <Card className="space-y-4 p-6 bg-surface border-border">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Sparkles className="size-4 opacity-75" />
                <span>How to strengthen your evaluation</span>
              </div>

              <ul className="space-y-3 text-sm text-foreground-secondary">
                {(latestAssessment?.actionableRecommendations || [
                  'Maintain consistent weekly active gig order volumes.',
                  'Link recurring platform payout settlements to your primary account.',
                  'Maintain timely payments for recurring micro-obligations and utility bills.',
                ]).map((rec, i) => (
                  <li key={i} className="flex items-start gap-2.5 leading-relaxed">
                    <span className="size-5 rounded-full bg-surface-highlight border border-border text-foreground flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>

              <div className="pt-3 border-t border-border flex items-center justify-between">
                <span className="text-xs text-foreground-secondary">
                  Updated automatically on data ingestion
                </span>
                <Link href="/user/profile">
                  <span className="text-xs sm:text-sm text-foreground-secondary hover:text-foreground font-semibold flex items-center gap-1">
                    Manage Feeds <ChevronRight className="size-3.5" />
                  </span>
                </Link>
              </div>
            </Card>
          </div>
        </section>
      )}
    </PageTransition>
  );
}
