import React from 'react';
import type { CreditAssessmentResult } from '@parakh/types';
import { MotionCard } from '@/components/motion/MotionCard';
import { AnimatedNumber } from '@/components/motion/AnimatedNumber';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { Sparkles, Activity, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CreditScoreCardProps {
  assessment: CreditAssessmentResult;
  className?: string;
  onClick?: () => void;
}

export function CreditScoreCard({
  assessment,
  className,
  onClick,
}: CreditScoreCardProps) {
  return (
    <MotionCard
      className={cn('space-y-6 relative overflow-hidden group', className)}
      onClick={onClick}
    >
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
            <Sparkles className="size-3.5 text-teal-400" />
            <span>Alternative Credit Evaluation</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">
            Your PARAKH Assessment
          </h2>
        </div>

        <RiskBadge riskLevel={assessment.riskLevel} />
      </div>

      {/* Hero Score Display */}
      <div className="flex items-baseline gap-3">
        <span className="text-5xl sm:text-6xl font-black text-white tracking-tight font-mono">
          <AnimatedNumber value={assessment.score} />
        </span>
        <span className="text-2xl text-muted-foreground font-mono font-medium">
          / {assessment.maxScore || 850}
        </span>
      </div>

      {/* Secondary Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-white/[0.06]">
        <div>
          <span className="text-xs text-muted-foreground block">
            Estimated Repayment Risk
          </span>
          <span className="text-sm font-bold text-white font-mono mt-0.5 block">
            {assessment.estimatedRepaymentDifficulty}% Difficulty
          </span>
        </div>

        <div>
          <span className="text-xs text-muted-foreground block flex items-center gap-1">
            <ShieldCheck className="size-3 text-teal-400" /> Data Confidence
          </span>
          <span className="text-sm font-bold text-teal-300 font-mono mt-0.5 block">
            {assessment.modelConfidence}% High Confidence
          </span>
        </div>

        <div className="col-span-2 sm:col-span-1">
          <span className="text-xs text-muted-foreground block flex items-center gap-1">
            <Activity className="size-3 text-purple-400" /> Shock Recovery
          </span>
          <span className="text-sm font-bold text-purple-300 font-mono mt-0.5 block">
            {Math.round((assessment.volatilityProfile?.recoveryRateAfterLowIncome ?? 0.94) * 100)}% Rebound Rate
          </span>
        </div>
      </div>
    </MotionCard>
  );
}
