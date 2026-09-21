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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/[0.06]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              My Evaluation Applications
            </h1>
            <Badge variant="outline" className="text-xs">
              {mockUserApplications.length} Total
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Track your historical and active alternative credit assessments.
          </p>
        </div>

        <Link href="/user/applications/new">
          <Button variant="lime" className="gap-2 font-bold px-5">
            <PlusCircle className="size-4" />
            <span>New Assessment</span>
          </Button>
        </Link>
      </div>

      {/* 2. FILTER & SEARCH BAR */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ID or purpose..."
            className="pl-10 h-10 rounded-full bg-[#0A162E] border-white/[0.08]"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-[#0A162E] p-1.5 rounded-full border border-white/[0.08] w-full sm:w-auto justify-start sm:justify-end">
          {[
            { id: 'ALL', label: 'All Evaluations' },
            { id: 'COMPLETED', label: 'Completed' },
            { id: 'REVIEW', label: 'In Review' },
            { id: 'PENDING', label: 'Processing' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-[#C8F451] text-[#07111F] font-bold shadow-sm'
                  : 'text-muted-foreground hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 3. APPLICATIONS DISPLAY */}
      {filteredApplications.length === 0 ? (
        <Card className="p-12 text-center space-y-3 bg-[#0A162E] border-white/[0.08]">
          <FileText className="size-8 text-muted-foreground mx-auto" />
          <h3 className="text-base font-bold text-white">No applications match your filter</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
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
          <Card className="hidden sm:block overflow-hidden p-0 bg-[#0A162E] border-white/[0.08]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-white/[0.02] border-b border-white/[0.08] text-muted-foreground font-semibold uppercase tracking-wider text-[11px]">
                  <tr>
                    <th className="py-3.5 px-5">Application ID</th>
                    <th className="py-3.5 px-5">Purpose & Amount</th>
                    <th className="py-3.5 px-5">Date</th>
                    <th className="py-3.5 px-5">Status</th>
                    <th className="py-3.5 px-5">Assessment</th>
                    <th className="py-3.5 px-5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {filteredApplications.map((app) => (
                    <tr
                      key={app.id}
                      className="hover:bg-white/[0.02] transition-colors group"
                    >
                      <td className="py-4 px-5 font-mono font-bold text-teal-300">
                        {app.id}
                      </td>

                      <td className="py-4 px-5">
                        <div className="space-y-0.5">
                          <span className="font-bold text-white font-mono block">
                            {formatCurrency(app.requestedAmount)}
                          </span>
                          <span className="text-muted-foreground text-[11px]">
                            {app.purpose}
                          </span>
                        </div>
                      </td>

                      <td className="py-4 px-5 text-muted-foreground">
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
                            <span className="font-mono font-bold text-white">
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
                          <span className="text-muted-foreground font-mono">
                            Evaluating...
                          </span>
                        )}
                      </td>

                      <td className="py-4 px-5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link href={`/user/applications/${app.id}`}>
                            <Button variant="ghost" size="sm" className="rounded-xl text-xs text-muted-foreground hover:text-white">
                              Details
                            </Button>
                          </Link>
                          {app.assessment && (
                            <Link href={`/user/results/${app.id}`}>
                              <Button variant="outline" size="sm" className="rounded-xl text-xs text-teal-300 border-teal-500/30 hover:bg-teal-500/10">
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
