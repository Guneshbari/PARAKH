'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  History,
  ShieldCheck,
  Search,
  SlidersHorizontal,
  RefreshCw,
  FileDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  Lock,
  Server,
  Clock,
  Activity,
  UserCheck,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { PageTransition } from '@/components/motion/PageTransition';
import { api, type AuditLogEntry } from '@parakh/api';

const PAGE_SIZE = 20;

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'AUTH_LOGIN_SUCCESS', label: 'AUTH_LOGIN_SUCCESS' },
  { value: 'AUTH_LOGIN_FAILURE', label: 'AUTH_LOGIN_FAILURE' },
  { value: 'AUTH_ACCESS_DENIED', label: 'AUTH_ACCESS_DENIED' },
  { value: 'AUTH_OWNERSHIP_VIOLATION', label: 'AUTH_OWNERSHIP_VIOLATION' },
  { value: 'APPLICATION_CREATED', label: 'APPLICATION_CREATED' },
  { value: 'APPLICATION_STATUS_CHANGED', label: 'APPLICATION_STATUS_CHANGED' },
  { value: 'ASSESSMENT_EXECUTED', label: 'ASSESSMENT_EXECUTED' },
  { value: 'FINANCIAL_SIGNAL_CREATED', label: 'FINANCIAL_SIGNAL_CREATED' },
  { value: 'CONSENT_GRANTED', label: 'CONSENT_GRANTED' },
  { value: 'CONSENT_REVOKED', label: 'CONSENT_REVOKED' },
  { value: 'APPLICANT_PROFILE_CREATED', label: 'APPLICANT_PROFILE_CREATED' },
  { value: 'APPLICANT_PROFILE_UPDATED', label: 'APPLICANT_PROFILE_UPDATED' },
  { value: 'REVIEW_OUTCOME_RECORDED', label: 'REVIEW_OUTCOME_RECORDED' },
  { value: 'MODEL_VERSION_CREATED', label: 'MODEL_VERSION_CREATED' },
];

const ENTITY_OPTIONS = [
  { value: '', label: 'All Entity Types' },
  { value: 'Authentication', label: 'Authentication' },
  { value: 'Security', label: 'Security & RBAC' },
  { value: 'Application', label: 'Application' },
  { value: 'CreditAssessment', label: 'Credit Assessment' },
  { value: 'FinancialSignal', label: 'Financial Signal' },
  { value: 'Consent', label: 'Consent Record' },
  { value: 'ApplicantProfile', label: 'Applicant Profile' },
  { value: 'ReviewOutcome', label: 'Review Outcome' },
  { value: 'User', label: 'User Account' },
  { value: 'ModelVersion', label: 'Model Version' },
];

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('');
  const [entityFilter, setEntityFilter] = useState<string>('');
  const [applicationIdInput, setApplicationIdInput] = useState<string>('');
  const [userIdInput, setUserIdInput] = useState<string>('');

  // Pagination (1-indexed for UI display)
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(false);

  // Detail Modal
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const fetchAuditLogs = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const skip = (page - 1) * PAGE_SIZE;
      const params: {
        skip: number;
        limit: number;
        action?: string;
        entity_type?: string;
        application_id?: string;
        user_id?: string;
      } = {
        skip,
        limit: PAGE_SIZE + 1, // request 1 extra to determine hasMore
      };

      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;
      if (applicationIdInput.trim()) params.application_id = applicationIdInput.trim();
      if (userIdInput.trim()) params.user_id = userIdInput.trim();

      const results = await api.getAuditLogsAdapted(params);

      if (results && results.length > PAGE_SIZE) {
        setHasMore(true);
        setLogs(results.slice(0, PAGE_SIZE));
      } else {
        setHasMore(false);
        setLogs(results || []);
      }
    } catch (err: any) {
      setError(err?.userMessage || err?.message || 'Failed to retrieve audit logs from backend.');
      setLogs([]);
      setHasMore(false);
    } finally {
      setIsLoading(false);
    }
  }, [page, actionFilter, entityFilter, applicationIdInput, userIdInput]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const handleResetFilters = () => {
    setActionFilter('');
    setEntityFilter('');
    setApplicationIdInput('');
    setUserIdInput('');
    setPage(1);
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const exportCurrentLogsJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute(
      'download',
      `parakh_audit_trail_page_${page}_${new Date().toISOString().replace(/[:.]/g, '-')}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Metrics summary for currently loaded view
  const authEventsCount = logs.filter(
    (l) => l.entityType === 'Authentication' || l.entityType === 'Security' || l.action.startsWith('AUTH_')
  ).length;
  const assessmentEventsCount = logs.filter(
    (l) => l.entityType === 'CreditAssessment' || l.action.includes('ASSESSMENT')
  ).length;
  const appEventsCount = logs.filter(
    (l) => l.entityType === 'Application' || l.entityType === 'Consent' || l.entityType === 'FinancialSignal'
  ).length;

  const getActionBadgeColor = (action: string) => {
    if (action.includes('SUCCESS') || action.includes('CREATED') || action.includes('GRANTED')) {
      return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20';
    }
    if (action.includes('FAILURE') || action.includes('DENIED') || action.includes('VIOLATION') || action.includes('REVOKED')) {
      return 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20';
    }
    if (action.includes('ASSESSMENT') || action.includes('MODEL')) {
      return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20';
    }
    return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20';
  };

  const getOutcomeBadgeColor = (outcome?: string | null) => {
    switch (outcome?.toUpperCase()) {
      case 'SUCCESS':
        return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20';
      case 'FAILURE':
      case 'DENIED':
        return 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20';
      case 'WARNING':
        return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20';
      default:
        return 'bg-surface-highlight text-foreground-secondary border-border';
    }
  };

  const formatTimestamp = (isoString?: string) => {
    if (!isoString) return { formatted: '—', iso: '—' };
    try {
      const date = new Date(isoString);
      return {
        formatted: date.toLocaleString('en-IN', {
          year: 'numeric',
          month: 'short',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
        iso: date.toISOString(),
      };
    } catch {
      return { formatted: isoString, iso: isoString };
    }
  };

  const hasActiveFilters = Boolean(
    actionFilter || entityFilter || applicationIdInput.trim() || userIdInput.trim()
  );

  return (
    <PageTransition>
      <div className="space-y-6 pb-12">
        {/* 1. PAGE HEADER */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                <History className="size-5" />
              </span>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
                Audit Trail & System Governance
              </h1>
              <div className="flex items-center gap-1.5 ml-2">
                <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider bg-emerald-500/5 text-emerald-600 border-emerald-500/30">
                  <ShieldCheck className="size-3 mr-1 inline" /> SOC 2 Immutable
                </Badge>
                <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider bg-purple-500/5 text-purple-600 border-purple-500/30">
                  <Lock className="size-3 mr-1 inline" /> DPDP Compliant
                </Badge>
              </div>
            </div>
            <p className="text-xs sm:text-sm text-foreground-secondary max-w-3xl">
              Chronological immutable event ledger recording identity authentication, authorization checks, credit risk assessments, and underwriter decisions. Restricted to authorized reviewers and system administrators.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={exportCurrentLogsJson}
              disabled={isLoading || logs.length === 0}
              className="rounded-full text-xs gap-1.5 shadow-xs"
              title="Export current page audit events as JSON"
            >
              <FileDown className="size-3.5" /> Export JSON
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={fetchAuditLogs}
              disabled={isLoading}
              className="rounded-full text-xs gap-1.5 bg-[#472393] hover:bg-[#3b1c7d] text-white shadow-xs cursor-pointer"
            >
              <RefreshCw className={`size-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </div>

        {/* 2. STATS & MONITORING METRICS */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
            <div className="flex items-center justify-between text-xs text-foreground-secondary">
              <span>Viewed Events</span>
              <Activity className="size-3.5 text-foreground-muted" />
            </div>
            <span className="text-xl font-bold text-foreground font-mono">{logs.length}</span>
            <span className="text-[11px] text-foreground-muted block">Records on page {page}</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
            <div className="flex items-center justify-between text-xs text-foreground-secondary">
              <span>Auth & Security</span>
              <UserCheck className="size-3.5 text-emerald-500" />
            </div>
            <span className="text-xl font-bold text-foreground font-mono">{authEventsCount}</span>
            <span className="text-[11px] text-foreground-muted block">Logins, denials & tokens</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
            <div className="flex items-center justify-between text-xs text-foreground-secondary">
              <span>Assessments & ML</span>
              <Server className="size-3.5 text-purple-500" />
            </div>
            <span className="text-xl font-bold text-foreground font-mono">{assessmentEventsCount}</span>
            <span className="text-[11px] text-foreground-muted block">Risk score executions</span>
          </div>

          <div className="p-3.5 rounded-2xl bg-surface border border-border shadow-card space-y-1">
            <div className="flex items-center justify-between text-xs text-foreground-secondary">
              <span>Entity Operations</span>
              <Clock className="size-3.5 text-blue-500" />
            </div>
            <span className="text-xl font-bold text-foreground font-mono">{appEventsCount}</span>
            <span className="text-[11px] text-foreground-muted block">Apps, signals & consent</span>
          </div>
        </div>

        {/* 3. FILTERING & SEARCH CONTROLS */}
        <Card className="p-4 bg-surface border-border space-y-3">
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 flex-1">
              {/* Action Dropdown */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-foreground-secondary">
                  Action Filter
                </label>
                <select
                  value={actionFilter}
                  onChange={(e) => {
                    setActionFilter(e.target.value);
                    setPage(1);
                  }}
                  className="bg-surface-highlight border border-border rounded-xl px-3 py-1.5 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-[#472393]/20"
                >
                  {ACTION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Entity Type Dropdown */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-foreground-secondary">
                  Entity Type
                </label>
                <select
                  value={entityFilter}
                  onChange={(e) => {
                    setEntityFilter(e.target.value);
                    setPage(1);
                  }}
                  className="bg-surface-highlight border border-border rounded-xl px-3 py-1.5 text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-[#472393]/20"
                >
                  {ENTITY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Application ID Input */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-foreground-secondary">
                  Application UUID
                </label>
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-foreground-muted" />
                  <Input
                    value={applicationIdInput}
                    onChange={(e) => {
                      setApplicationIdInput(e.target.value);
                      setPage(1);
                    }}
                    placeholder="Filter by application UUID..."
                    className="pl-8 h-8 rounded-xl bg-surface-highlight border-border text-xs"
                  />
                </div>
              </div>

              {/* User ID Input */}
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold uppercase tracking-wider text-foreground-secondary">
                  Actor / User UUID
                </label>
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-foreground-muted" />
                  <Input
                    value={userIdInput}
                    onChange={(e) => {
                      setUserIdInput(e.target.value);
                      setPage(1);
                    }}
                    placeholder="Filter by user UUID..."
                    className="pl-8 h-8 rounded-xl bg-surface-highlight border-border text-xs"
                  />
                </div>
              </div>
            </div>

            {hasActiveFilters && (
              <div className="flex items-end shrink-0 pt-2 lg:pt-0">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetFilters}
                  className="rounded-full text-xs text-foreground-muted hover:text-foreground h-8 gap-1"
                >
                  <X className="size-3.5" /> Reset Filters
                </Button>
              </div>
            )}
          </div>
        </Card>

        {/* 4. AUDIT LOGS TABLE & STATES */}
        {isLoading ? (
          <Card className="p-16 text-center space-y-3 bg-surface border-border">
            <Loader2 className="size-8 animate-spin text-[#472393] mx-auto" />
            <h3 className="text-base font-semibold text-foreground">Loading audit records from ledger...</h3>
            <p className="text-xs text-foreground-muted max-w-sm mx-auto">
              Connecting to PostgreSQL audit log storage and validating cryptographic signatures.
            </p>
          </Card>
        ) : error ? (
          <Card className="p-14 text-center space-y-3 bg-surface border-border">
            <AlertCircle className="size-8 text-rose-500 mx-auto" />
            <h3 className="text-base font-semibold text-foreground">Failed to Load Audit Logs</h3>
            <p className="text-xs text-foreground-muted max-w-md mx-auto">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchAuditLogs}
              className="rounded-full text-xs mt-2 gap-1.5"
            >
              <RefreshCw className="size-3.5" /> Retry Request
            </Button>
          </Card>
        ) : logs.length === 0 ? (
          <Card className="p-14 text-center space-y-3 bg-surface border-border">
            <History className="size-8 text-foreground-muted mx-auto" />
            <h3 className="text-base font-semibold text-foreground">
              {hasActiveFilters ? 'No audit records match the selected filters' : 'Audit ledger is currently empty'}
            </h3>
            <p className="text-xs text-foreground-muted max-w-md mx-auto">
              {hasActiveFilters
                ? 'Try broadening your filter criteria or clearing the application/user UUID filters.'
                : 'System events and compliance logs will populate automatically as users authenticate and applications are processed.'}
            </p>
            {hasActiveFilters ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="rounded-full text-xs mt-2"
              >
                Reset All Filters
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={fetchAuditLogs}
                className="rounded-full text-xs mt-2 gap-1.5"
              >
                <RefreshCw className="size-3.5" /> Refresh
              </Button>
            )}
          </Card>
        ) : (
          <Card className="overflow-hidden p-0 border-border">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[750px] text-left text-xs sm:text-sm">
                <thead className="bg-surface-highlight/50 border-b border-border text-foreground-secondary font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-4">Timestamp (IST / UTC)</th>
                    <th className="py-3.5 px-4">Action</th>
                    <th className="py-3.5 px-4">Entity Type & ID</th>
                    <th className="py-3.5 px-4">Actor / User</th>
                    <th className="py-3.5 px-4">Application</th>
                    <th className="py-3.5 px-4">Outcome</th>
                    <th className="py-3.5 px-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {logs.map((log) => {
                    const timeInfo = formatTimestamp(log.createdAt);
                    const outcome = log.outcome || (log.metadata?.outcome as string | undefined);
                    const actorRole = log.actorRole || (log.metadata?.actor_role as string | undefined);

                    return (
                      <tr
                        key={log.id}
                        className="hover:bg-surface-highlight/40 transition-colors group cursor-pointer"
                        onClick={() => setSelectedLog(log)}
                      >
                        {/* Timestamp */}
                        <td className="py-3 px-4 text-foreground text-xs whitespace-nowrap">
                          <div className="font-mono font-medium">{timeInfo.formatted}</div>
                          <div className="text-[10px] text-foreground-muted font-mono truncate max-w-[140px]">
                            {timeInfo.iso}
                          </div>
                        </td>

                        {/* Action Badge */}
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-medium border ${getActionBadgeColor(
                              log.action
                            )}`}
                          >
                            {log.action}
                          </span>
                        </td>

                        {/* Entity */}
                        <td className="py-3 px-4">
                          <div className="font-medium text-foreground text-xs">{log.entityType}</div>
                          {log.entityId ? (
                            <div className="text-[11px] font-mono text-foreground-muted truncate max-w-[120px]" title={log.entityId}>
                              ID: {log.entityId.slice(0, 8)}…
                            </div>
                          ) : (
                            <span className="text-[10px] text-foreground-muted">—</span>
                          )}
                        </td>

                        {/* Actor / User */}
                        <td className="py-3 px-4">
                          {log.userId ? (
                            <div className="space-y-0.5">
                              <div className="font-mono text-xs text-foreground truncate max-w-[120px]" title={log.userId}>
                                {log.userId.slice(0, 8)}…
                              </div>
                              {actorRole && (
                                <Badge variant="outline" className="text-[9px] uppercase px-1 py-0 font-mono">
                                  {actorRole}
                                </Badge>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-foreground-muted">System / Public</span>
                          )}
                        </td>

                        {/* Application ID */}
                        <td className="py-3 px-4">
                          {log.applicationId ? (
                            <Link
                              href={`/admin/applications/${log.applicationId}`}
                              onClick={(e) => e.stopPropagation()}
                              className="font-mono text-xs text-foreground hover:underline hover:text-[#472393] dark:hover:text-purple-400 flex items-center gap-1"
                              title={`View dossier: ${log.applicationId}`}
                            >
                              <span>{log.applicationId.slice(0, 8)}…</span>
                              <ExternalLink className="size-2.5 opacity-60" />
                            </Link>
                          ) : (
                            <span className="text-xs text-foreground-muted">—</span>
                          )}
                        </td>

                        {/* Outcome */}
                        <td className="py-3 px-4">
                          {outcome ? (
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getOutcomeBadgeColor(
                                outcome
                              )}`}
                            >
                              {outcome}
                            </span>
                          ) : (
                            <span className="text-xs text-foreground-muted font-mono">INFO</span>
                          )}
                        </td>

                        {/* Inspect Button */}
                        <td className="py-3 px-4 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedLog(log);
                            }}
                            className="rounded-full text-xs h-7 px-2.5 gap-1 text-foreground-secondary hover:text-foreground hover:bg-surface-highlight"
                          >
                            <Eye className="size-3" /> Inspect
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-5 py-3 border-t border-border bg-surface-highlight/30 text-xs">
              <div className="text-foreground-secondary font-mono">
                Showing <span className="font-semibold text-foreground">{(page - 1) * PAGE_SIZE + 1}</span> to{' '}
                <span className="font-semibold text-foreground">{(page - 1) * PAGE_SIZE + logs.length}</span> events (Page {page})
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || isLoading}
                  className="rounded-full h-8 px-3 text-xs gap-1"
                >
                  <ChevronLeft className="size-3.5" /> Previous
                </Button>

                <span className="px-3 py-1 font-mono text-xs bg-surface border border-border rounded-lg text-foreground font-semibold">
                  {page}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasMore || isLoading}
                  className="rounded-full h-8 px-3 text-xs gap-1"
                >
                  Next <ChevronRight className="size-3.5" />
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* 5. EVENT INSPECT MODAL (DRAWER / DIALOG) */}
        {selectedLog && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-event-modal-title"
            className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-background/80 backdrop-blur-md animate-in fade-in duration-200"
          >
            <div className="bg-surface border border-border rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
              {/* Modal Header */}
              <div className="flex items-start justify-between p-5 border-b border-border bg-surface">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="size-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-600 dark:text-purple-400">
                      <History className="size-4" />
                    </div>
                    <h2 id="audit-event-modal-title" className="text-base sm:text-lg font-semibold text-foreground tracking-tight">
                      Audit Event Record
                    </h2>
                    <Badge variant="outline" className="text-[10px] font-mono py-0.5 px-2">
                      Immutable Entry
                    </Badge>
                  </div>
                  <p className="text-xs text-foreground-secondary">
                    Cryptographically tracked event from immutable compliance audit trail.
                  </p>
                </div>

                <button
                  onClick={() => setSelectedLog(null)}
                  className="size-8 rounded-full border border-border hover:bg-surface-highlight flex items-center justify-center text-foreground-muted hover:text-foreground transition-colors cursor-pointer"
                  aria-label="Close dialog"
                >
                  <X className="size-4" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-5 overflow-y-auto space-y-4">
                {/* Core Attributes Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      Event ID
                    </span>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-foreground break-all">{selectedLog.id}</span>
                      <button
                        onClick={() => copyToClipboard(selectedLog.id, 'event_id')}
                        className="text-foreground-muted hover:text-foreground shrink-0 cursor-pointer p-1"
                        title="Copy Event ID"
                      >
                        {copiedKey === 'event_id' ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      Action Name
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md font-mono font-medium border ${getActionBadgeColor(
                        selectedLog.action
                      )}`}
                    >
                      {selectedLog.action}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      Recorded Timestamp
                    </span>
                    <span className="font-mono text-foreground block">
                      {formatTimestamp(selectedLog.createdAt).formatted}
                    </span>
                    <span className="font-mono text-[10px] text-foreground-muted block">
                      {selectedLog.createdAt}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      Target Entity
                    </span>
                    <span className="font-medium text-foreground block">{selectedLog.entityType}</span>
                    {selectedLog.entityId && (
                      <span className="font-mono text-[11px] text-foreground-muted block break-all">
                        Entity ID: {selectedLog.entityId}
                      </span>
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      User / Actor ID
                    </span>
                    {selectedLog.userId ? (
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono text-foreground break-all">{selectedLog.userId}</span>
                        <button
                          onClick={() => copyToClipboard(selectedLog.userId!, 'user_id')}
                          className="text-foreground-muted hover:text-foreground shrink-0 cursor-pointer p-1"
                          title="Copy User ID"
                        >
                          {copiedKey === 'user_id' ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                        </button>
                      </div>
                    ) : (
                      <span className="text-foreground-muted italic">System / Unauthenticated</span>
                    )}
                  </div>

                  <div className="p-3 rounded-xl bg-surface-highlight/50 border border-border space-y-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-foreground-secondary block">
                      Associated Application
                    </span>
                    {selectedLog.applicationId ? (
                      <div className="flex items-center justify-between gap-2">
                        <Link
                          href={`/admin/applications/${selectedLog.applicationId}`}
                          className="font-mono text-foreground hover:underline hover:text-[#472393] dark:hover:text-purple-400 break-all"
                        >
                          {selectedLog.applicationId}
                        </Link>
                        <button
                          onClick={() => copyToClipboard(selectedLog.applicationId!, 'app_id')}
                          className="text-foreground-muted hover:text-foreground shrink-0 cursor-pointer p-1"
                          title="Copy Application ID"
                        >
                          {copiedKey === 'app_id' ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
                        </button>
                      </div>
                    ) : (
                      <span className="text-foreground-muted italic">Non-application event</span>
                    )}
                  </div>
                </div>

                {/* Structured Metadata Section */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-foreground-secondary">
                      Event Metadata (Sanitized)
                    </span>
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(selectedLog.metadata, null, 2), 'metadata')}
                      className="text-xs text-foreground-muted hover:text-foreground flex items-center gap-1 cursor-pointer"
                    >
                      {copiedKey === 'metadata' ? (
                        <>
                          <Check className="size-3 text-emerald-500" /> Copied JSON
                        </>
                      ) : (
                        <>
                          <Copy className="size-3" /> Copy JSON
                        </>
                      )}
                    </button>
                  </div>

                  {selectedLog.metadata && Object.keys(selectedLog.metadata).length > 0 ? (
                    <div className="p-3.5 rounded-xl bg-[#0D0E10] text-[#E0E0E0] border border-border/40 font-mono text-xs overflow-x-auto max-h-56">
                      <pre>{JSON.stringify(selectedLog.metadata, null, 2)}</pre>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-surface-highlight/30 border border-border text-center text-xs text-foreground-muted italic">
                      No additional metadata recorded for this event.
                    </div>
                  )}
                </div>

                {/* Zero PII & DPDP Assurance Notice */}
                <div className="p-3 rounded-xl bg-purple-500/5 border border-purple-500/20 text-xs text-foreground-secondary flex items-start gap-2.5">
                  <Lock className="size-4 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <span className="font-semibold text-foreground text-[11px] block">
                      DPDP & Data Minimization Guaranteed
                    </span>
                    <p className="text-[11px] leading-relaxed">
                      All audit records are automatically sanitized at ingestion to exclude plaintext credentials, tokens, raw transactional logs, and sensitive personal information.
                    </p>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex items-center justify-end p-4 border-t border-border bg-surface-highlight/30">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedLog(null)}
                  className="rounded-full text-xs"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  );
}
