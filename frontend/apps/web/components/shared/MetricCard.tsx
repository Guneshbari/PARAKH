import React from 'react';
import { MotionCard } from '@/components/motion/MotionCard';
import { AnimatedNumber } from '@/components/motion/AnimatedNumber';
import { Badge } from '@/components/ui/badge';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: number;
  format?: (n: number) => string;
  prefix?: string;
  suffix?: string;
  pillLabel?: string;
  pillVariant?: 'mint' | 'lavender' | 'riskLower' | 'riskModerate' | 'riskHigher' | 'outline' | 'secondary' | 'default';
  subtext?: string;
  icon?: LucideIcon;
  className?: string;
  onClick?: () => void;
}

export function MetricCard({
  title,
  value,
  format,
  prefix = '',
  suffix = '',
  pillLabel,
  pillVariant = 'secondary',
  subtext,
  icon: Icon,
  className,
  onClick,
}: MetricCardProps) {
  return (
    <MotionCard
      className={cn('space-y-3.5', className)}
      onClick={onClick}
      hoverable={!!onClick}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-foreground-secondary">
          {title}
        </span>
        {Icon && <Icon className="size-4 text-foreground-secondary" />}
        {pillLabel && !Icon && (
          <Badge variant={pillVariant} className="text-xs py-0.5 px-2">
            {pillLabel}
          </Badge>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-3xl sm:text-4xl font-semibold text-foreground tracking-tight font-mono">
          <AnimatedNumber
            value={value}
            format={format}
            prefix={prefix}
            suffix={suffix}
          />
        </span>
        {pillLabel && Icon && (
          <Badge variant={pillVariant} className="text-xs py-0.5 px-2">
            {pillLabel}
          </Badge>
        )}
      </div>

      {subtext && (
        <div className="pt-2 border-t border-border flex items-center justify-between text-xs sm:text-sm text-foreground-secondary">
          <span>{subtext}</span>
        </div>
      )}
    </MotionCard>
  );
}
