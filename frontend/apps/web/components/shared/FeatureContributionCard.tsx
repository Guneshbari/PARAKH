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
        <p className="text-sm text-foreground-secondary leading-relaxed">
          How alternative financial behaviors and recovery patterns influenced the evaluation.
        </p>
      </div>

      {contributions.length === 0 ? (
        <div className="py-6 px-4 rounded-lg bg-surface-highlight/50 border border-border/50 text-center space-y-1.5">
          <p className="text-sm font-semibold text-foreground">
            No Feature Attributions Available
          </p>
          <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed max-w-md mx-auto">
            Feature attributions are unavailable because no predictive score was generated. When alternative telemetry is insufficient, SHAP feature impact cannot be computed.
          </p>
        </div>
      ) : (
        <div className="space-y-4 pt-2">
          {contributions.map((item) => {
            const isPositive = item.direction === 'POSITIVE';
            const percentageWidth = Math.min(Math.round(Math.abs(item.contributionValue) * 100), 100);

            return (
              <div key={item.featureName} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-1.5 font-medium text-foreground-secondary">
                    {isPositive ? (
                      <ArrowUpRight className="size-4 text-foreground" />
                    ) : (
                      <ArrowDownRight className="size-4 text-foreground-secondary" />
                    )}
                    <span>{item.displayName}</span>
                  </div>
                  <span
                    className={cn(
                      'font-mono font-semibold text-xs sm:text-sm',
                      isPositive ? 'text-foreground' : 'text-foreground-secondary'
                    )}
                  >
                    {isPositive ? `+${percentageWidth}%` : `-${percentageWidth}%`}
                  </span>
                </div>

                {/* Divergence Bar */}
                <div className="h-2 w-full bg-surface-highlight rounded-full overflow-hidden flex">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-500',
                      isPositive
                        ? 'bg-[#472393] dark:bg-foreground'
                        : 'bg-foreground-secondary/40'
                    )}
                    style={{ width: `${percentageWidth}%` }}
                  />
                </div>

                <p className="text-xs sm:text-sm text-foreground-secondary leading-relaxed">
                  {item.explanationText}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
