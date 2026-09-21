import React from 'react';
import type { RiskLevel } from '@parakh/types';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { ShieldCheck, AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';

interface RiskBadgeProps extends Omit<BadgeProps, 'variant'> {
  riskLevel: RiskLevel;
  showIcon?: boolean;
}

export function RiskBadge({ riskLevel, showIcon = true, className, ...props }: RiskBadgeProps) {
  switch (riskLevel) {
    case 'LOWER_ESTIMATED RISK':
      return (
        <Badge variant="riskLower" className={className} {...props}>
          {showIcon && <ShieldCheck className="size-3 text-emerald-300" />}
          <span>LOWER ESTIMATED RISK</span>
        </Badge>
      );
    case 'MODERATE_ESTIMATED RISK':
      return (
        <Badge variant="riskModerate" className={className} {...props}>
          {showIcon && <AlertTriangle className="size-3 text-amber-300" />}
          <span>MODERATE ESTIMATED RISK</span>
        </Badge>
      );
    case 'HIGHER_ESTIMATED RISK':
      return (
        <Badge variant="riskHigher" className={className} {...props}>
          {showIcon && <AlertCircle className="size-3 text-red-300" />}
          <span>HIGHER ESTIMATED RISK</span>
        </Badge>
      );
    case 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW':
    default:
      return (
        <Badge variant="riskNeutral" className={className} {...props}>
          {showIcon && <HelpCircle className="size-3 text-slate-300" />}
          <span>MANUAL REVIEW REQUIRED</span>
        </Badge>
      );
  }
}
