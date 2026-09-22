'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  PlusCircle,
  Search,
  FileText,
  AlertCircle,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { ApplicationCard } from '@/components/shared/ApplicationCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { formatCurrency } from '@/lib/utils';
import { useAuth } from '@/components/auth/AuthContext';
import {
  api,
  adaptApplication,
  adaptAssessment,
  ApiError,
  type BackendApplicantProfile,
  type BackendApplication,
} from '@parakh/api';
import type { CreditApplication } from '@parakh/types';

export default function UserApplicationsPage() {
  const { user, isLoading: authLoading } = useAuth();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [applications, setApplications] = useState<CreditApplication[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchApplications = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Fetch Profile
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

      if (!rawProfile) {
        setApplications([]);
        setIsLoading(false);
        return;
      }

      // 2. Fetch Applications
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

      // Adapt each application, fetching assessment if completed/assessed
      const adaptedList: CreditApplication[] = await Promise.all(
        rawApps.map(async (rawApp) => {
          let assessment = null;
          if (rawApp.status === 'ASSESSED' || rawApp.status === 'COMPLETED') {
            try {
              const rawAsmt = await api.getLatestAssessmentByApplication(rawApp.id);
              assessment = adaptAssessment(rawAsmt, rawProfile?.full_name || undefined);
            } catch {
              assessment = null;
            }
          }
          return adaptApplication(rawApp, rawProfile, assessment);
        })
      );

      setApplications(adaptedList);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.userMessage : 'Failed to load applications.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading && user) {
      fetchApplications();
    } else if (!authLoading && !user) {
      setIsLoading(false);
    }
  }, [authLoading, user, fetchApplications]);

  const filteredApplications = applications.filter((app) => {
    const matchesSearch =
      app.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.purpose.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'COMPLETED' &&
        (app.status === 'ASSESSMENT_COMPLETED' || app.status === 'REVIEW_COMPLETED')) ||
      (statusFilter === 'REVIEW' && app.status === 'MANUAL_REVIEW_REQUIRED') ||
      (statusFilter === 'PENDING' &&
        (app.status === 'SUBMITTED' ||
          app.status === 'DATA_VALIDATION' ||
          app.status === 'FINANCIAL_ANALYSIS'));

    return matchesSearch && matchesStatus;
  });

  if (authLoading || isLoading) {
    return (
      <div className="py-24 text-center space-y-4 max-w-md mx-auto">
        <div className="size-10 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto" />
        <h2 className="text-base font-semibold text-foreground">Loading Applications...</h2>
        <p className="text-xs text-foreground-muted">Retrieving your credit evaluations from PARAKH.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto py-16 px-4">
        <Card className="p-6 border-red-500/30 bg-red-500/5 space-y-4 text-center">
          <AlertCircle className="size-10 text-red-500 mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-foreground">Unable to Load Applications</h2>
            <p className="text-xs text-foreground-secondary">{error}</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchApplications()}
            className="gap-1.5 rounded-full text-xs mx-auto"
          >
            <RefreshCw className="size-3.5" /> Try Again
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-12">
      {/* 1. HEADER ROW */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              My Evaluation Applications
            </h1>
            <Badge variant="outline" className="text-xs">
              {applications.length} Total
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Track your historical and active alternative credit assessments.
          </p>
        </div>

        <Link href="/user/applications/new">
          <Button variant="default" className="gap-2 font-semibold px-5 rounded-full cursor-pointer">
            <PlusCircle className="size-4" />
            <span>New Assessment</span>
          </Button>
        </Link>
      </div>

      {/* 2. FILTER & SEARCH BAR */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-foreground-muted" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ID or purpose..."
            className="pl-10 h-10 rounded-full bg-surface border-border text-foreground placeholder:text-foreground-muted"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-surface-highlight p-1 rounded-full border border-border w-full sm:w-auto justify-start sm:justify-end">
          {[
            { id: 'ALL', label: 'All Evaluations' },
            { id: 'COMPLETED', label: 'Completed' },
            { id: 'REVIEW', label: 'In Review' },
            { id: 'PENDING', label: 'Processing' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'text-foreground-muted hover:text-foreground hover:bg-surface'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. APPLICATIONS DISPLAY */}
      {applications.length === 0 ? (
        <Card className="p-12 text-center space-y-4 max-w-xl mx-auto my-6 bg-surface border-dashed border-border">
          <FileText className="size-10 text-foreground-muted mx-auto opacity-75" />
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-foreground">No Applications Yet</h3>
            <p className="text-xs text-foreground-muted max-w-sm mx-auto leading-relaxed">
              You haven&apos;t submitted any credit evaluation applications yet. Start a new assessment to evaluate your gig cashflow metrics.
            </p>
          </div>
          <Link href="/user/applications/new">
            <Button variant="default" size="sm" className="rounded-full text-xs gap-1.5 font-semibold px-5">
              <PlusCircle className="size-4" /> Start First Assessment
            </Button>
          </Link>
        </Card>
      ) : filteredApplications.length === 0 ? (
        <Card className="p-12 text-center space-y-3">
          <FileText className="size-8 text-foreground-muted mx-auto" />
          <h3 className="text-base font-semibold text-foreground">No applications match your filter</h3>
          <p className="text-xs text-foreground-muted max-w-sm mx-auto">
            Try adjusting your search terms or filter criteria.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('ALL');
            }}
            className="rounded-full text-xs mt-2"
          >
            Reset Filters
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Mobile Card List View */}
          <div className="space-y-3 sm:hidden">
            {filteredApplications.map((app) => (
              <Link key={app.id} href={`/user/applications/${app.id}`}>
                <ApplicationCard application={app} />
              </Link>
            ))}
          </div>

          {/* Desktop Table View */}
          <div className="hidden sm:block overflow-hidden rounded-2xl border border-border bg-surface">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-highlight border-b border-border text-foreground-muted uppercase font-semibold tracking-wider">
                <tr>
                  <th className="py-3.5 px-5">Application ID</th>
                  <th className="py-3.5 px-5">Loan Purpose</th>
                  <th className="py-3.5 px-5">Requested Amount</th>
                  <th className="py-3.5 px-5">Pipeline Status</th>
                  <th className="py-3.5 px-5">Risk Rating</th>
                  <th className="py-3.5 px-5">Submitted Date</th>
                  <th className="py-3.5 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredApplications.map((app) => (
                  <tr
                    key={app.id}
                    className="hover:bg-surface-highlight/50 transition-colors group cursor-pointer"
                  >
                    <td className="py-4 px-5 font-mono font-medium text-foreground">
                      <Link href={`/user/applications/${app.id}`} className="hover:underline">
                        {app.id.substring(0, 8)}...
                      </Link>
                    </td>
                    <td className="py-4 px-5 text-foreground-secondary font-medium">
                      {app.purpose}
                    </td>
                    <td className="py-4 px-5 font-semibold text-foreground">
                      {formatCurrency(app.requestedAmount)}
                    </td>
                    <td className="py-4 px-5">
                      <StatusBadge status={app.status} />
                    </td>
                    <td className="py-4 px-5">
                      <RiskBadge riskLevel={app.assessment?.riskLevel || 'MODERATE_ESTIMATED RISK'} />
                    </td>
                    <td className="py-4 px-5 text-foreground-muted">
                      {new Date(app.submittedAt).toLocaleDateString('en-IN', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>
                    <td className="py-4 px-5 text-right">
                      <Link href={`/user/applications/${app.id}`}>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 rounded-full text-xs font-semibold gap-1 text-primary hover:text-primary"
                        >
                          <span>Track</span>
                          <ArrowRight className="size-3" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </PageTransition>
  );
}
