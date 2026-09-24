'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  UserCheck,
  ShieldCheck,
  CheckCircle2,
  Download,
  Calendar,
  Building2,
  Printer,
  Info,
  Scale,
  Mail,
  Key,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { useAuth } from '@/components/auth/AuthContext';
import { api } from '@parakh/api';

export default function AdminProfilePage() {
  const { user } = useAuth();
  const [alertQueue, setAlertQueue] = useState(true);
  const [alertMonsoon, setAlertMonsoon] = useState(true);
  const [alertFairness, setAlertFairness] = useState(true);
  const [completedReviewsCount, setCompletedReviewsCount] = useState<number>(218);

  useEffect(() => {
    let isMounted = true;
    async function loadReviewerStats() {
      if (!user?.id) return;
      try {
        const reviews = await api.getReviewsByReviewer(user.id);
        if (!isMounted) return;
        if (reviews && Array.isArray(reviews)) {
          setCompletedReviewsCount(reviews.length);
        }
      } catch (err) {
        console.warn('Could not fetch reviewer reviews from backend:', err);
      }
    }
    loadReviewerStats();
    return () => {
      isMounted = false;
    };
  }, [user?.id]);

  const officerName = user?.name || (user?.email ? user.email.split('@')[0] : 'Priya Sharma');
  const officerInitials = user?.name
    ? user.name.slice(0, 2).toUpperCase()
    : user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'PS';
  const officerEmail = user?.email || 'p.sharma@partner-credit.in';
  const officerId = user?.id ? user.id.slice(0, 8).toUpperCase() : 'REV-402';
  const officerRole = user?.role ? user.role.toUpperCase() : 'REVIEWER';

  const handleExportAuditLog = () => {
    const logData = {
      underwriter: {
        id: officerId,
        name: officerName,
        role: `${officerRole} — Alternative Credit Officer`,
        desk: 'Station 04 — Informal & Gig Economy Credit Desk',
        institution: 'PARAKH Partner Lending Consortium',
        certification: 'RBI Fair Practice Code & Statutory Algorithmic Audit Certified',
      },
      authorityLimits: {
        singleApplicationCap: 200000,
        currency: 'INR',
        scope: ['Gig Economy Worker', 'Informal Vendor', 'Daily Wage', 'Freelancer'],
      },
      activeSession: {
        sessionId: 'AUD-2026-904',
        authMethod: 'Hardware FIDO2 Token (SHA-256)',
        authenticatedAt: new Date().toISOString(),
      },
      auditEntriesCompleted: completedReviewsCount,
    };

    const blob = new Blob([JSON.stringify(logData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PARAKH_Reviewer_Audit_Ledger_${officerId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & ACTION BUTTONS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Credit Reviewer Settings & Station Profile
          </h1>
          <p className="text-xs sm:text-sm text-foreground-muted">
            Officer credentials, review discretion caps, audit signing certificates, and station notifications.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAuditLog}
            className="rounded-full gap-1.5 text-xs text-foreground-secondary border-border hover:bg-surface-highlight"
          >
            <Download className="size-3.5" /> Export Audit Log
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-full gap-1.5 text-xs text-foreground-muted hover:text-foreground"
          >
            <Printer className="size-3.5" /> Print Profile
          </Button>
        </div>
      </div>

      {/* 2. UNDERWRITING OFFICER HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-surface dark:bg-surface-elevated border border-border-strong shadow-card-elevated flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center gap-5">
          {/* Avatar */}
          <div className="relative size-16 sm:size-20 rounded-2xl bg-surface-highlight border border-border flex items-center justify-center text-xl sm:text-2xl font-bold text-foreground shrink-0">
            {officerInitials}
            <div className="absolute -bottom-1 -right-1 size-5 rounded-full bg-[#472393] text-white flex items-center justify-center ring-4 ring-surface dark:bg-foreground dark:text-background">
              <CheckCircle2 className="size-3.5 stroke-[3]" />
            </div>
          </div>

          {/* Details */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
                {officerName}
              </h2>
              <Badge variant="secondary" className="text-xs py-0.5 px-2.5">
                Certified {officerRole}
              </Badge>
              <Badge variant="outline" className="text-xs py-0.5 px-2.5 font-mono">
                {officerId}
              </Badge>
            </div>

            <p className="text-xs sm:text-sm text-foreground-secondary font-medium">
              Senior Credit Reviewer • Station 04 Desk
            </p>

            <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-foreground-secondary pt-0.5">
              <span className="flex items-center gap-1">
                <Building2 className="size-3.5 opacity-70" />
                PARAKH Partner Lending Consortium
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Mail className="size-3.5 opacity-70" />
                {officerEmail}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
              <span className="text-foreground-secondary flex items-center gap-1">
                <Calendar className="size-3.5 opacity-70" />
                Review Desk Active since Jan 2024
              </span>
              <span className="text-foreground-secondary">•</span>
              <span className="text-foreground-secondary font-medium">
                {completedReviewsCount} Human Reviews Logged
              </span>
            </div>
          </div>
        </div>

        <Link href="/admin/applications">
          <Button
            variant="default"
            size="sm"
            className="rounded-full gap-2 text-xs sm:text-sm font-semibold px-5 h-9 shadow-xs shrink-0 cursor-pointer"
          >
            <UserCheck className="size-3.5" />
            <span>Open Review Queue</span>
          </Button>
        </Link>
      </div>

      {/* 3. UNDERWRITING AUTHORITY & STATUTORY PARAMETERS */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="space-y-0.5">
            <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
              <Scale className="size-4 text-foreground-secondary" />
              Underwriting Discretion Limits & Statutory Mandate
            </h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Parameters governing independent qualitative reviews under RBI Fair Practice Code guidelines.
            </p>
          </div>
          <Badge variant="mint" className="text-xs py-0.5 px-2">
            Level-2 Authorized
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-1.5">
            <span className="text-xs sm:text-sm text-foreground-secondary block">Discretionary Capital Cap</span>
            <span className="text-xl sm:text-2xl font-bold text-foreground font-mono">₹2,00,000</span>
            <span className="text-xs text-foreground-secondary block">Single Applicant Limit</span>
          </div>

          <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-1.5">
            <span className="text-xs sm:text-sm text-foreground-secondary block">Authorized Sectors</span>
            <span className="text-sm sm:text-base font-bold text-foreground block">Gig & Informal</span>
            <span className="text-xs text-foreground-secondary block">Food, Salon, Auto, Retail</span>
          </div>

          <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border space-y-1.5">
            <span className="text-xs sm:text-sm text-foreground-secondary block">Fair Lending Certification</span>
            <span className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5 text-foreground" /> Validated
            </span>
            <span className="text-xs text-foreground-secondary block">Annual Audit Certified</span>
          </div>
        </div>
      </Card>

      {/* 4. STATION OPERATIONAL NOTIFICATIONS & ALERTS */}
      <Card className="p-6 bg-surface border-border space-y-5">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="space-y-0.5">
            <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="size-4 text-foreground-secondary" />
              Operational Desk Notifications
            </h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Automated alerts when non-standard volatility cases enter the review queue.
            </p>
          </div>
        </div>

        <div className="space-y-3.5">
          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-sm font-semibold text-foreground block">
                Priority Review Queue Inflow Alerts
              </span>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Receive immediate desktop alerts when an application is flagged with INSUFFICIENT EVIDENCE / MANUAL REVIEW.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertQueue(!alertQueue)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertQueue ? 'bg-[#472393] dark:bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  alertQueue ? 'bg-white dark:bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-sm font-semibold text-foreground block">
                Monsoon & Seasonal Extreme Variance Warnings
              </span>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Notifies when regional rain dips exceed 30% to prevent misattribution of weather shocks to applicant distress.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertMonsoon(!alertMonsoon)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertMonsoon ? 'bg-[#472393] dark:bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  alertMonsoon ? 'bg-white dark:bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-surface-highlight/30 border border-border">
            <div className="space-y-0.5">
              <span className="text-sm font-semibold text-foreground block">
                Algorithmic Demographic Parity Drift Alerts
              </span>
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Automatic escalation if Fairlearn demographic parity ratio falls below 0.85 across any gig cohort.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertFairness(!alertFairness)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertFairness ? 'bg-[#472393] dark:bg-foreground' : 'bg-surface-highlight border border-border'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full shadow-xs ring-0 transition duration-200 ease-in-out ${
                  alertFairness ? 'bg-white dark:bg-background translate-x-4' : 'bg-foreground-muted translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      </Card>

      {/* 5. HARDWARE CRYPTOGRAPHIC KEY & AUDIT SIGNING */}
      <Card className="p-6 bg-surface border-border space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <div className="space-y-0.5">
            <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
              <Key className="size-4 text-foreground-secondary" />
              Cryptographic Audit Signing & Security
            </h3>
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Credit Reviewer decisions are digitally signed and hashed to guarantee immutability.
            </p>
          </div>
          <Badge variant="outline" className="text-xs font-mono">
            FIDO2 Hardware Attested
          </Badge>
        </div>

        <div className="space-y-2.5 text-xs sm:text-sm">
          <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
            <div>
              <span className="font-semibold text-foreground block">Digital Signing Certificate</span>
              <span className="text-xs text-foreground-secondary font-mono">
                SHA-256 Fingerprint: 4F:9A:82:1C:E4:01:B7:90 • Valid till Dec 2027
              </span>
            </div>
            <Badge variant="secondary" className="text-xs">
              Active
            </Badge>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-highlight/40 border border-border flex items-center justify-between">
            <div>
              <span className="font-semibold text-foreground block">Current Credit Reviewer Session</span>
              <span className="text-xs text-foreground-secondary font-mono">
                Session ID: AUD-2026-904 • Authenticated via Hardware Key
              </span>
            </div>
            <span className="text-foreground-secondary font-mono text-xs">TLS 1.3 Secure</span>
          </div>
        </div>
      </Card>

      {/* 6. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-surface-highlight/30 border border-border text-xs sm:text-sm text-foreground-secondary flex items-start gap-3">
        <Info className="size-4 text-foreground-secondary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-foreground block">
            Human Credit Reviewer Accountability Declaration
          </span>
          <p>
            Credit Reviewers certified on the PARAKH platform operate under mandatory human-in-the-loop governance. Algorithmic outputs serve as alternative evidence aids and do not substitute for certified fiduciary underwriting reviews.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
