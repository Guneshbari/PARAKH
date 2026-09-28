import React from 'react';
import type { RiskLevel } from '@parakh/types';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { ShieldCheck, AlertTriangle, AlertCircle, HelpCircle, MinusCircle } from 'lucide-react';

interface RiskBadgeProps extends Omit<BadgeProps, 'variant'> {
  riskLevel?: RiskLevel | 'UNRATED' | string | null;
  showIcon?: boolean;
}

export function RiskBadge({ riskLevel, showIcon = true, className, ...props }: RiskBadgeProps) {
  switch (riskLevel) {
    case 'LOWER_ESTIMATED RISK':
      return (
        <Badge variant="riskLower" className={className} {...props}>
          {showIcon && <ShieldCheck className="size-3 shrink-0" />}
          <span>LOWER ESTIMATED RISK</span>
        </Badge>
      );
    case 'MODERATE_ESTIMATED RISK':
      return (
        <Badge variant="riskModerate" className={className} {...props}>
          {showIcon && <AlertTriangle className="size-3 shrink-0" />}
          <span>MODERATE ESTIMATED RISK</span>
        </Badge>
      );
    case 'HIGHER_ESTIMATED RISK':
      return (
        <Badge variant="riskHigher" className={className} {...props}>
          {showIcon && <AlertCircle className="size-3 shrink-0" />}
          <span>HIGHER ESTIMATED RISK</span>
        </Badge>
      );
    case 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW':
      return (
        <Badge variant="riskNeutral" className={className} {...props}>
          {showIcon && <HelpCircle className="size-3 shrink-0" />}
          <span>MANUAL REVIEW REQUIRED</span>
        </Badge>
      );
    case 'UNRATED':
    case null:
    case undefined:
    default:
      return (
        <Badge variant="outline" className={className} {...props}>
          {showIcon && <MinusCircle className="size-3 shrink-0 text-foreground-secondary" />}
          <span>UNRATED</span>
        </Badge>
      );
  }
}
