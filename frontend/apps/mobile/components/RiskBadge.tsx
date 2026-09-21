import React from 'react';
import type { RiskLevel } from '@parakh/types';
import { Badge } from './Badge';

interface MobileRiskBadgeProps {
  riskLevel: RiskLevel;
}

export function RiskBadge({ riskLevel }: MobileRiskBadgeProps) {
  switch (riskLevel) {
    case 'LOWER_ESTIMATED RISK':
      return <Badge label="LOWER ESTIMATED RISK" variant="riskLower" />;
    case 'MODERATE_ESTIMATED RISK':
      return <Badge label="MODERATE ESTIMATED RISK" variant="riskModerate" />;
    case 'HIGHER_ESTIMATED RISK':
      return <Badge label="HIGHER ESTIMATED RISK" variant="riskHigher" />;
    case 'INSUFFICIENT_EVIDENCE_MANUAL_REVIEW':
    default:
      return <Badge label="MANUAL REVIEW REQUIRED" variant="riskNeutral" />;
  }
}
