'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Search,
  ChevronRight,
  ShieldCheck,
  FileText,
  Printer,
  SlidersHorizontal,
  Loader2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { PageTransition } from '@/components/motion/PageTransition';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { api, adaptApplication } from '@parakh/api';
import { formatCurrency } from '@/lib/utils';

export default function AdminApplicationsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');
  const [employmentFilter, setEmploymentFilter] = useState<string>('ALL');

  const [allApps, setAllApps] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApps = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const rawApps = await api.getApplications();
      if (rawApps && rawApps.length > 0) {
        const mapped = rawApps.map((app) => {
          const adapted = adaptApplication(app);
          return {
            ...adapted,
            applicantName: `Applicant ${app.applicant_profile_id ? app.applicant_profile_id.slice(0, 8) : app.id.slice(0, 8)}`,
            sectorTag: adapted.purpose?.toLowerCase().includes('equipment') ? 'Micro-enterprise' : 'Urban Gig Delivery',
            triggerReason:
              app.status === 'MANUAL_REVIEW'
                ? 'Alternative cashflow volatility requires reviewer sign-off'
                : app.status === 'UNDER_REVIEW'
                ? 'Inflow signals currently under aggregation'
                : 'Standard credit risk evaluation',
            submissionDate: app.created_at,
          };
        });
        setAllApps(mapped);
      } else {
        setAllApps([]);
      }
    } catch (err: any) {
      setError(err?.userMessage || err?.message || 'Failed to retrieve applications from server.');
      setAllApps([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  // Multi-criteria filter
  const filteredApps = allApps.filter((app) => {
    const matchesSearch =
      app.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.applicantName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.purpose.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (app.triggerReason && app.triggerReason.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (app.sectorTag && app.sectorTag.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'REVIEW' && app.status === 'MANUAL_REVIEW_REQUIRED') ||
      (statusFilter === 'VALIDATION' && app.status === 'DATA_VALIDATION') ||
      (statusFilter === 'READY' && app.status === 'ASSESSMENT_COMPLETED') ||
      (statusFilter === 'COMPLETED' && app.status === 'REVIEW_COMPLETED');

    const matchesRisk =
      riskFilter === 'ALL' ||
      (app.assessment && app.assessment.riskLevel === riskFilter);

    const matchesEmployment =
      employmentFilter === 'ALL' || app.employmentType === employmentFilter;

    return matchesSearch && matchesStatus && matchesRisk && matchesEmployment;
  });

  const pendingCount = allApps.filter((a) => a.status === 'MANUAL_REVIEW_REQUIRED').length;
  const validationCount = allApps.filter((a) => a.status === 'DATA_VALIDATION').length;
  const completedCount = allApps.filter(
    (a) => a.status === 'ASSESSMENT_COMPLETED' || a.status === 'REVIEW_COMPLETED'
  ).length;

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & KPI STRIP */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
              Applications for Review
            </h1>
            <Badge variant="mint" className="text-[10px] py-0.5 px-2">
              {allApps.length} Total Dossiers
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Priority human-in-the-loop review cases, active verification pipelines, and historical alternative credit evaluations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Queue
          </Button>
          <Link href="/admin/dashboard">
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 text-xs">
              Cockpit View
            </Button>
          </Link>
        </div>
      </div>

      {/* 2. SUMMARY STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <span className="text-[11px] text-foreground-muted block">Active In Queue</span>
          <span className="text-xl font-bold text-foreground font-mono">{allApps.length}</span>
          <span className="text-[10px] text-foreground-secondary block">Digital Inflow Feeds</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <span className="text-[11px] text-foreground font-semibold block">
            Priority Review Required
          </span>
          <span className="text-xl font-bold text-foreground font-mono">{pendingCount}</span>
          <span className="text-[10px] text-foreground-muted block">Human Review Flagged</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <span className="text-[11px] text-foreground-muted block">In Data Validation</span>
          <span className="text-xl font-bold text-foreground font-mono">{validationCount}</span>
          <span className="text-[10px] text-foreground-muted block">KYC / AA Telemetry</span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
          <span className="text-[11px] text-foreground-muted block">Assessed & Recorded</span>
          <span className="text-xl font-bold text-foreground font-mono">{completedCount}</span>
          <span className="text-[10px] text-foreground-secondary block">Dossiers Ready</span>
        </div>
      </div>

      {/* 3. SEARCH & ADVANCED FILTER BAR */}
      <Card className="p-4 bg-surface border-border space-y-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-foreground-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ID, applicant name, purpose, trigger, or sector..."
              className="pl-10 h-10 rounded-full bg-surface border-border text-xs"
            />
          </div>

          {/* Quick Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5 bg-surface-highlight p-1 rounded-full border border-border">
            {[
              { id: 'ALL', label: 'All Queue' },
              { id: 'REVIEW', label: `Priority Review (${pendingCount})` },
              { id: 'VALIDATION', label: 'Validation' },
              { id: 'READY', label: 'Dossier Ready' },
              { id: 'COMPLETED', label: 'Outcome Recorded' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                  statusFilter === tab.id
                    ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                    : 'text-foreground-muted hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Secondary Filter Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-border text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-foreground-muted flex items-center gap-1 text-[11px] font-medium">
              <SlidersHorizontal className="size-3 text-foreground-secondary" /> Filter By:
            </span>

            {/* Risk Tier Select */}
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-surface-highlight border border-border rounded-full px-3 py-1 text-foreground text-xs focus:outline-none focus:border-[#472393] focus:ring-2 focus:ring-[#472393]/20 dark:focus:border-foreground dark:focus:ring-0"
            >
              <option value="ALL">All Risk Tiers</option>
              <option value="LOWER_ESTIMATED RISK">Lower Estimated Risk</option>
              <option value="MODERATE_ESTIMATED RISK">Moderate Estimated Risk</option>
              <option value="HIGHER_ESTIMATED RISK">Higher Estimated Risk</option>
              <option value="INSUFFICIENT_EVIDENCE_MANUAL_REVIEW">
                Manual Review Required
              </option>
            </select>

            {/* Employment Type Select */}
            <select
              value={employmentFilter}
              onChange={(e) => setEmploymentFilter(e.target.value)}
              className="bg-surface-highlight border border-border rounded-full px-3 py-1 text-foreground text-xs focus:outline-none focus:border-[#472393] focus:ring-2 focus:ring-[#472393]/20 dark:focus:border-foreground dark:focus:ring-0"
            >
              <option value="ALL">All Employment Sectors</option>
              <option value="GIG_WORKER">Gig Economy Worker</option>
              <option value="INFORMAL_VENDOR">Informal Vendor</option>
              <option value="DAILY_WAGE">Daily Wage Worker</option>
              <option value="FREELANCER">Freelance & Crafts</option>
            </select>
          </div>

          {(searchQuery || statusFilter !== 'ALL' || riskFilter !== 'ALL' || employmentFilter !== 'ALL') && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setStatusFilter('ALL');
                setRiskFilter('ALL');
                setEmploymentFilter('ALL');
              }}
              className="rounded-full text-xs h-7 text-foreground-muted hover:text-foreground"
            >
              Reset Filters
            </Button>
          )}
        </div>
      </Card>

      {/* 4. APPLICATIONS TABLE / CARD DISPLAY */}
      {isLoading ? (
        <Card className="p-12 text-center space-y-3 bg-surface border-border">
          <Loader2 className="size-8 animate-spin text-foreground mx-auto" />
          <h3 className="text-base font-semibold text-foreground">Loading credit dossiers from backend...</h3>
          <p className="text-xs text-foreground-muted max-w-sm mx-auto">
            Retrieving live applications and review flags from PostgreSQL.
          </p>
        </Card>
      ) : error ? (
        <Card className="p-12 text-center space-y-3 bg-surface border-border">
          <AlertCircle className="size-8 text-red-500 mx-auto" />
          <h3 className="text-base font-semibold text-foreground">Failed to Load Applications</h3>
          <p className="text-xs text-foreground-muted max-w-sm mx-auto">
            {error}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchApps}
            className="rounded-full text-xs mt-2 gap-1.5"
          >
            <RefreshCw className="size-3.5" /> Retry
          </Button>
        </Card>
      ) : allApps.length === 0 ? (
        <Card className="p-12 text-center space-y-3 bg-surface border-border">
          <FileText className="size-8 text-foreground-muted mx-auto" />
          <h3 className="text-base font-semibold text-foreground">No Applications in Queue</h3>
          <p className="text-xs text-foreground-muted max-w-sm mx-auto">
            There are currently no credit evaluation dossiers pending review.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchApps}
            className="rounded-full text-xs mt-2 gap-1.5"
          >
            <RefreshCw className="size-3.5" /> Refresh
          </Button>
        </Card>
      ) : filteredApps.length === 0 ? (
        <Card className="p-12 text-center space-y-3 bg-surface border-border">
          <FileText className="size-8 text-foreground-muted mx-auto" />
          <h3 className="text-base font-semibold text-foreground">No applications match your filter criteria</h3>
          <p className="text-xs text-foreground-muted max-w-sm mx-auto">
            Try adjusting search terms or resetting the active status and risk filters.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('ALL');
              setRiskFilter('ALL');
              setEmploymentFilter('ALL');
            }}
            className="rounded-full text-xs mt-2"
          >
            Reset Filters
          </Button>
        </Card>
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-highlight/40 border-b border-border text-foreground-muted font-medium uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3.5 px-5">Application ID</th>
                  <th className="py-3.5 px-5">Applicant & Sector</th>
                  <th className="py-3.5 px-5">Capital & Purpose</th>
                  <th className="py-3.5 px-5">Review Flag / Reason</th>
                  <th className="py-3.5 px-5">Status</th>
                  <th className="py-3.5 px-5">Assessment</th>
                  <th className="py-3.5 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredApps.map((app) => {
                  const isFlagged = app.status === 'MANUAL_REVIEW_REQUIRED';

                  return (
                    <tr
                      key={app.id}
                      className="hover:bg-surface-highlight/30 transition-colors group"
                    >
                      <td className="py-4 px-5 font-mono font-semibold text-foreground">
                        <Link
                          href={`/admin/applications/${app.id}`}
                          className="hover:underline hover:text-[#472393] dark:hover:text-foreground flex items-center gap-1"
                        >
                          {app.id}
                        </Link>
                      </td>

                      <td className="py-4 px-5">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-foreground block">
                            {app.applicantName}
                          </span>
                          <span className="text-foreground-muted text-[11px]">
                            {app.sectorTag || app.employmentType.replace(/_/g, ' ')}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-5">
                        <div className="space-y-0.5">
                          <span className="font-mono font-semibold text-foreground block">
                            {formatCurrency(app.requestedAmount)}
                          </span>
                          <span className="text-foreground-muted text-[11px]">
                            {app.purpose}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-5 max-w-xs">
                        {app.triggerReason ? (
                          <div className="flex items-start gap-1.5 text-foreground-secondary text-xs">
                            <span className="size-1.5 rounded-full bg-foreground-secondary mt-1.5 shrink-0" />
                            <span className="line-clamp-2">{app.triggerReason}</span>
                          </div>
                        ) : (
                          <span className="text-foreground-muted text-[11px] font-mono">
                            Standard flow
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-5">
                        <StatusBadge status={app.status} />
                      </td>

                      <td className="py-4 px-5">
                        {app.assessment ? (
                          <div className="space-y-1">
                            <span className="font-mono font-semibold text-foreground block">
                              {app.assessment.score} / 850
                            </span>
                            <RiskBadge
                              riskLevel={app.assessment.riskLevel}
                              showIcon={false}
                              className="text-[10px] py-0 px-2"
                            />
                          </div>
                        ) : (
                          <span className="text-foreground-muted font-mono text-[11px]">
                            Evaluating...
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-5 text-right">
                        <Link href={`/admin/applications/${app.id}`}>
                          <Button
                            variant={isFlagged ? 'default' : 'outline'}
                            size="sm"
                            className="rounded-full text-xs h-8 px-3 font-semibold cursor-pointer shadow-xs"
                          >
                            <span>{isFlagged ? 'Review Dossier' : 'Inspect'}</span>
                            <ChevronRight className="size-3.5 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* 5. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-[11px] text-foreground-muted flex items-start gap-3">
        <ShieldCheck className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Credit Reviewer Authority & Audit Logging
          </span>
          <p>
            All credit reviewer evaluations, verifications, and recorded outcomes are cryptographically timestamped in accordance with statutory fair lending audit guidelines. PARAKH never performs automated loan approval or denial.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
