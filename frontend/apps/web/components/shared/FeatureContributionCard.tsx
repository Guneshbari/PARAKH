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
        <h3 className="text-base sm:text-lg font-semibold text-foreground tracking-tight">
          Feature Contributions & Impact
        </h3>
        <p className="text-xs text-foreground-muted leading-relaxed">
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
                <div className="flex items-center gap-1.5 font-medium text-foreground-secondary">
                  {isPositive ? (
                    <ArrowUpRight className="size-3.5 text-foreground" />
                  ) : (
                    <ArrowDownRight className="size-3.5 text-foreground-muted" />
                  )}
                  <span>{item.displayName}</span>
                </div>
                <span
                  className={cn(
                    'font-mono font-semibold text-[11px]',
                    isPositive ? 'text-foreground' : 'text-foreground-muted'
                  )}
                >
                  {isPositive ? `+${percentageWidth}%` : `-${percentageWidth}%`}
                </span>
              </div>

              {/* Divergence Bar */}
              <div className="h-1.5 w-full bg-surface-highlight rounded-full overflow-hidden flex">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    isPositive
                      ? 'bg-foreground'
                      : 'bg-foreground-muted/40'
                  )}
                  style={{ width: `${percentageWidth}%` }}
                />
              </div>

              <p className="text-[11px] text-foreground-muted leading-tight">
                {item.explanationText}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
