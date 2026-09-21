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
  pillVariant?: 'mint' | 'lavender' | 'riskLower' | 'riskModerate' | 'riskHigher' | 'outline';
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
  pillVariant = 'mint',
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
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
        {Icon && <Icon className="size-4 text-teal-400" />}
        {pillLabel && !Icon && (
          <Badge variant={pillVariant} className="text-[10px] py-0.5 px-2">
            {pillLabel}
          </Badge>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight font-mono">
          <AnimatedNumber
            value={value}
            format={format}
            prefix={prefix}
            suffix={suffix}
          />
        </span>
        {pillLabel && Icon && (
          <Badge variant={pillVariant} className="text-[10px] py-0.5 px-2">
            {pillLabel}
          </Badge>
        )}
      </div>

      {subtext && (
        <div className="pt-2 border-t border-white/[0.05] flex items-center justify-between text-xs text-muted-foreground">
          <span>{subtext}</span>
        </div>
      )}
    </MotionCard>
  );
}
