import React from 'react';
import type { ApplicationStatus } from '@parakh/types';
import { Badge } from '@/components/ui/badge';
import { Clock, CheckCircle2, AlertCircle, FileSearch, ShieldAlert } from 'lucide-react';

interface StatusBadgeProps {
  status: ApplicationStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  switch (status) {
    case 'SUBMITTED':
      return (
        <Badge variant="outline" className={className}>
          <Clock className="size-3 text-slate-400" />
          <span>Submitted</span>
        </Badge>
      );
    case 'DATA_VALIDATION':
      return (
        <Badge variant="secondary" className={className}>
          <FileSearch className="size-3 text-teal-400" />
          <span>Validating Data</span>
        </Badge>
      );
    case 'FINANCIAL_ANALYSIS':
      return (
        <Badge variant="lavender" className={className}>
          <Clock className="size-3 text-[#C4B5FD]" />
          <span>Analyzing Cashflow</span>
        </Badge>
      );
    case 'ASSESSMENT_COMPLETED':
      return (
        <Badge variant="mint" className={className}>
          <CheckCircle2 className="size-3 text-emerald-400" />
          <span>Assessed</span>
        </Badge>
      );
    case 'MANUAL_REVIEW_REQUIRED':
      return (
        <Badge variant="riskModerate" className={className}>
          <AlertCircle className="size-3 text-amber-400" />
          <span>Needs Review</span>
        </Badge>
      );
    case 'REVIEW_COMPLETED':
      return (
        <Badge variant="mint" className={className}>
          <ShieldAlert className="size-3 text-teal-300" />
          <span>Review Recorded</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className={className}>
          <span>{status}</span>
        </Badge>
      );
  }
}
