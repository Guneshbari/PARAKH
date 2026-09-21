'use client';

import React, { useState } from 'react';
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

export default function AdminProfilePage() {
  const [alertQueue, setAlertQueue] = useState(true);
  const [alertMonsoon, setAlertMonsoon] = useState(true);
  const [alertFairness, setAlertFairness] = useState(true);

  const handleExportAuditLog = () => {
    const logData = {
      underwriter: {
        id: 'UW-402',
        name: 'Priya Sharma',
        role: 'Senior Alternative Risk Underwriter',
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
        authenticatedAt: '2026-09-20T08:00:00Z',
      },
      auditEntriesCompleted: 218,
    };

    const blob = new Blob([JSON.stringify(logData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'PARAKH_Underwriter_Audit_Ledger_UW402.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageTransition className="space-y-6 sm:space-y-8 w-full pb-16">
      {/* 1. TOP HEADER & ACTION BUTTONS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Underwriter Settings & Station Profile
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Officer credentials, underwriting discretion caps, audit signing certificates, and station notifications.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAuditLog}
            className="rounded-xl gap-1.5 text-xs text-slate-300 border-white/[0.1] hover:bg-white/[0.05]"
          >
            <Download className="size-3.5" /> Export Audit Log
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="rounded-xl gap-1.5 text-xs text-muted-foreground hover:text-white"
          >
            <Printer className="size-3.5" /> Print Profile
          </Button>
        </div>
      </div>

      {/* 2. UNDERWRITING OFFICER HERO CARD */}
      <div className="p-6 sm:p-7 rounded-2xl bg-[#0A162E] border border-white/[0.08] shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-start sm:items-center gap-5">
          {/* Avatar */}
          <div className="relative size-16 sm:size-20 rounded-2xl bg-gradient-to-tr from-teal-500/20 to-purple-500/20 border border-teal-500/30 flex items-center justify-center text-xl sm:text-2xl font-black text-teal-300 shrink-0">
            PS
            <div className="absolute -bottom-1 -right-1 size-5 rounded-full bg-teal-400 text-slate-950 flex items-center justify-center ring-4 ring-[#0A162E]">
              <CheckCircle2 className="size-3.5 stroke-[3]" />
            </div>
          </div>

          {/* Details */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Priya Sharma
              </h2>
              <Badge variant="mint" className="text-[10px] py-0.5 px-2">
                Certified Risk Underwriter
              </Badge>
              <Badge variant="outline" className="text-[10px] py-0.5 px-2 font-mono">
                UW-402
              </Badge>
            </div>

            <p className="text-xs text-slate-300 font-medium">
              Senior Alternative Risk Underwriter • Station 04 Desk
            </p>

            <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground pt-0.5">
              <span className="flex items-center gap-1">
                <Building2 className="size-3.5 text-teal-400" />
                PARAKH Partner Lending Consortium
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Mail className="size-3.5 text-teal-400" />
                p.sharma@partner-credit.in
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
              <span className="text-muted-foreground flex items-center gap-1">
                <Calendar className="size-3.5 text-teal-400" />
                Underwriting Desk Active since Jan 2024
              </span>
              <span className="text-muted-foreground">•</span>
              <span className="text-teal-300 font-medium">
                218 Human Reviews Logged
              </span>
            </div>
          </div>
        </div>

        <Link href="/admin/applications">
          <Button
            variant="lime"
            size="sm"
            className="rounded-full gap-2 text-xs font-bold px-5 shadow-lg shadow-lime-400/10 shrink-0"
          >
            <UserCheck className="size-3.5" />
            <span>Open Review Queue</span>
          </Button>
        </Link>
      </div>

      {/* 3. UNDERWRITING AUTHORITY & STATUTORY PARAMETERS */}
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Scale className="size-4 text-teal-400" />
              Underwriting Discretion Limits & Statutory Mandate
            </h3>
            <p className="text-xs text-muted-foreground">
              Parameters governing independent qualitative reviews under RBI Fair Practice Code guidelines.
            </p>
          </div>
          <Badge variant="mint" className="text-[10px]">
            Level-2 Authorized
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-1.5">
            <span className="text-xs text-muted-foreground block">Discretionary Capital Cap</span>
            <span className="text-xl font-bold text-white font-mono">₹2,00,000</span>
            <span className="text-[10px] text-teal-300 block">Single Applicant Limit</span>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-1.5">
            <span className="text-xs text-muted-foreground block">Authorized Sectors</span>
            <span className="text-sm font-bold text-white block">Gig & Informal</span>
            <span className="text-[10px] text-muted-foreground block">Food, Salon, Auto, Retail</span>
          </div>

          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.04] space-y-1.5">
            <span className="text-xs text-muted-foreground block">Fair Lending Certification</span>
            <span className="text-sm font-bold text-teal-300 flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5" /> Validated
            </span>
            <span className="text-[10px] text-muted-foreground block">Annual Audit Certified</span>
          </div>
        </div>
      </Card>

      {/* 4. STATION OPERATIONAL NOTIFICATIONS & ALERTS */}
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-5">
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="size-4 text-teal-400" />
              Operational Desk Notifications
            </h3>
            <p className="text-xs text-muted-foreground">
              Automated alerts when non-standard volatility cases enter the review queue.
            </p>
          </div>
        </div>

        <div className="space-y-3.5">
          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-white block">
                Priority Review Queue Inflow Alerts
              </span>
              <p className="text-[11px] text-muted-foreground">
                Receive immediate desktop alerts when an application is flagged with INSUFFICIENT EVIDENCE / MANUAL REVIEW.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertQueue(!alertQueue)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertQueue ? 'bg-teal-400' : 'bg-white/20'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ease-in-out ${
                  alertQueue ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-white block">
                Monsoon & Seasonal Extreme Variance Warnings
              </span>
              <p className="text-[11px] text-muted-foreground">
                Notifies when regional rain dips exceed 30% to prevent misattribution of weather shocks to borrower distress.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertMonsoon(!alertMonsoon)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertMonsoon ? 'bg-teal-400' : 'bg-white/20'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ease-in-out ${
                  alertMonsoon ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-start justify-between gap-4 p-3.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-white block">
                Algorithmic Demographic Parity Drift Alerts
              </span>
              <p className="text-[11px] text-muted-foreground">
                Automatic escalation if Fairlearn demographic parity ratio falls below 0.85 across any gig cohort.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAlertFairness(!alertFairness)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                alertFairness ? 'bg-teal-400' : 'bg-white/20'
              }`}
            >
              <span
                className={`pointer-events-none inline-block size-4 transform rounded-full bg-slate-950 shadow-lg ring-0 transition duration-200 ease-in-out ${
                  alertFairness ? 'translate-x-4' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      </Card>

      {/* 5. HARDWARE CRYPTOGRAPHIC KEY & AUDIT SIGNING */}
      <Card className="p-6 bg-[#0A162E] border-white/[0.08] space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Key className="size-4 text-teal-400" />
              Cryptographic Audit Signing & Security
            </h3>
            <p className="text-xs text-muted-foreground">
              Underwriter decisions are digitally signed and hashed to guarantee immutability.
            </p>
          </div>
          <Badge variant="outline" className="text-[10px] font-mono text-teal-300 border-teal-500/30">
            FIDO2 Hardware Attested
          </Badge>
        </div>

        <div className="space-y-2.5 text-xs">
          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div>
              <span className="font-bold text-white block">Digital Signing Certificate</span>
              <span className="text-[11px] text-muted-foreground font-mono">
                SHA-256 Fingerprint: 4F:9A:82:1C:E4:01:B7:90 • Valid till Dec 2027
              </span>
            </div>
            <Badge variant="mint" className="text-[10px]">
              Active
            </Badge>
          </div>

          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between">
            <div>
              <span className="font-bold text-white block">Current Underwriter Session</span>
              <span className="text-[11px] text-muted-foreground font-mono">
                Session ID: AUD-2026-904 • Authenticated via Hardware Key
              </span>
            </div>
            <span className="text-teal-300 font-mono text-[11px]">TLS 1.3 Secure</span>
          </div>
        </div>
      </Card>

      {/* 6. STATUTORY GOVERNANCE FOOTNOTE */}
      <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-muted-foreground flex items-start gap-3">
        <Info className="size-4 text-teal-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <span className="font-semibold text-slate-300 block">
            Human Underwriter Accountability Declaration
          </span>
          <p>
            Underwriters certified on the PARAKH platform operate under mandatory human-in-the-loop governance. Algorithmic outputs serve as alternative evidence aids and do not substitute for certified fiduciary underwriting reviews.
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
