'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { PlusCircle, Search, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { PageTransition } from '@/components/motion/PageTransition';
import { ApplicationCard } from '@/components/shared/ApplicationCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { mockUserApplications } from '@/data/mock/user';
import { formatCurrency } from '@/lib/utils';

export default function UserApplicationsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredApplications = mockUserApplications.filter((app) => {
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
              {mockUserApplications.length} Total
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
                  ? 'bg-[#472393] text-white font-semibold shadow-xs dark:bg-foreground dark:text-background'
                  : 'text-foreground-muted hover:text-[#472393] hover:bg-[#F5F1FF] dark:hover:text-foreground dark:hover:bg-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. APPLICATIONS DISPLAY */}
      {filteredApplications.length === 0 ? (
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
          <Card className="hidden sm:block overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-highlight/40 border-b border-border text-foreground-muted font-medium uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-5">Application ID</th>
                    <th className="py-3.5 px-5">Purpose & Amount</th>
                    <th className="py-3.5 px-5">Date</th>
                    <th className="py-3.5 px-5">Status</th>
                    <th className="py-3.5 px-5">Assessment</th>
                    <th className="py-3.5 px-5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredApplications.map((app) => (
                    <tr
                      key={app.id}
                      className="hover:bg-surface-highlight/30 transition-colors group"
                    >
                      <td className="py-4 px-5 font-mono font-semibold text-foreground">
                        {app.id}
                      </td>

                      <td className="py-4 px-5">
                        <div className="space-y-0.5">
                          <span className="font-semibold text-foreground font-mono block">
                            {formatCurrency(app.requestedAmount)}
                          </span>
                          <span className="text-foreground-muted text-[11px]">
                            {app.purpose}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-5 text-foreground-muted">
                        {new Date(app.submittedAt).toLocaleDateString('en-IN', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </td>

                      <td className="py-4 px-5">
                        <StatusBadge status={app.status} />
                      </td>

                      <td className="py-4 px-5">
                        {app.assessment ? (
                          <div className="space-y-1">
                            <span className="font-mono font-semibold text-foreground">
                              {app.assessment.score} / 850
                            </span>
                            <div>
                              <RiskBadge
                                riskLevel={app.assessment.riskLevel}
                                showIcon={false}
                                className="text-[10px] py-0 px-2"
                              />
                            </div>
                          </div>
                        ) : (
                          <span className="text-foreground-muted font-mono">
                            Evaluating...
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link href={`/user/applications/${app.id}`}>
                            <Button variant="ghost" size="sm" className="rounded-full text-xs text-foreground-muted hover:text-foreground">
                              Details
                            </Button>
                          </Link>
                          {app.assessment && (
                            <Link href={`/user/results/${app.id}`}>
                              <Button variant="secondary" size="sm" className="rounded-full text-xs">
                                Report
                              </Button>
                            </Link>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </PageTransition>
  );
}
