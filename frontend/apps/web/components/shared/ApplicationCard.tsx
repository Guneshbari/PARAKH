import React from 'react';
import type { CreditApplication } from '@parakh/types';
import { MotionCard } from '@/components/motion/MotionCard';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { formatCurrency } from '@/lib/utils';
import { ChevronRight, Calendar, Layers } from 'lucide-react';

interface ApplicationCardProps {
  application: CreditApplication;
  onSelect?: (id: string) => void;
  className?: string;
}

export function ApplicationCard({
  application,
  onSelect,
  className,
}: ApplicationCardProps) {
  return (
    <MotionCard
      className={className}
      onClick={onSelect ? () => onSelect(application.id) : undefined}
      hoverable={!!onSelect}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-foreground">
            {application.id}
          </span>
          <span className="text-xs text-foreground-muted">•</span>
          <span className="text-xs text-foreground-muted flex items-center gap-1">
            <Calendar className="size-3" />
            {new Date(application.submittedAt).toLocaleDateString('en-IN', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={application.status} />
          {application.assessment && (
            <RiskBadge riskLevel={application.assessment.riskLevel} showIcon={false} />
          )}
        </div>
      </div>

      <div className="pt-3 flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xl sm:text-2xl font-semibold text-foreground font-mono">
              {formatCurrency(application.requestedAmount)}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-surface-highlight border border-border text-foreground-secondary">
              {application.purpose}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-foreground-muted">
            <Layers className="size-3" />
            <span>{application.applicantName}</span>
            <span>•</span>
            <span className="capitalize">{application.employmentType.replace('_', ' ').toLowerCase()}</span>
          </div>
        </div>

        {onSelect && (
          <div className="size-8 rounded-full bg-surface-highlight border border-border flex items-center justify-center text-foreground-muted hover:text-foreground transition-colors">
            <ChevronRight className="size-4" />
          </div>
        )}
      </div>
    </MotionCard>
  );
}
