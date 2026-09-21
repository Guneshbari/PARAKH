import React from 'react';
import type { SHAPContribution } from '@parakh/types';
import { Card } from '@/components/ui/card';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeatureContributionCardProps {
  contributions: SHAPContribution[];
  className?: string;
}

export function FeatureContributionCard({
  contributions,
  className,
}: FeatureContributionCardProps) {
  return (
    <Card className={cn('space-y-5', className)}>
      <div className="space-y-1">
        <h3 className="text-lg font-bold text-white tracking-tight">
          Feature Contributions & Impact
        </h3>
        <p className="text-xs text-muted-foreground leading-relaxed">
          How alternative financial behaviors and recovery patterns influenced the evaluation.
        </p>
      </div>

      <div className="space-y-3.5 pt-2">
        {contributions.map((item) => {
          const isPositive = item.direction === 'POSITIVE';
          const percentageWidth = Math.min(Math.round(Math.abs(item.contributionValue) * 100), 100);

          return (
            <div key={item.featureName} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 font-medium text-slate-200">
                  {isPositive ? (
                    <ArrowUpRight className="size-3.5 text-emerald-400" />
                  ) : (
                    <ArrowDownRight className="size-3.5 text-amber-400" />
                  )}
                  <span>{item.displayName}</span>
                </div>
                <span
                  className={cn(
                    'font-mono font-bold text-[11px]',
                    isPositive ? 'text-emerald-400' : 'text-amber-400'
                  )}
                >
                  {isPositive ? `+${percentageWidth}%` : `-${percentageWidth}%`}
                </span>
              </div>

              {/* Divergence Bar */}
              <div className="h-2 w-full bg-white/[0.05] rounded-full overflow-hidden flex">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    isPositive
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                      : 'bg-gradient-to-r from-amber-500 to-red-400'
                  )}
                  style={{ width: `${percentageWidth}%` }}
                />
              </div>

              <p className="text-[11px] text-muted-foreground leading-tight">
                {item.explanationText}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
