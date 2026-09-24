import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide transition-colors select-none',
  {
    variants: {
      variant: {
        default:
          'bg-surface-elevated text-foreground border border-border shadow-xs',
        secondary:
          'bg-surface-highlight text-foreground-secondary border border-border',
        outline:
          'border border-border text-foreground-secondary bg-transparent',
        mint:
          'bg-emerald-500/10 text-emerald-800 dark:text-foreground dark:bg-white/[0.06] border border-emerald-500/20 dark:border-white/[0.12]',
        cyan:
          'bg-sky-500/10 text-sky-800 dark:text-foreground dark:bg-white/[0.06] border border-sky-500/20 dark:border-white/[0.12]',
        lime:
          'bg-surface-elevated text-foreground border border-border',
        lavender:
          'bg-indigo-500/10 text-indigo-800 dark:text-foreground dark:bg-white/[0.06] border border-indigo-500/20 dark:border-white/[0.12]',
        ai:
          'bg-indigo-500/10 text-indigo-800 dark:text-foreground dark:bg-white/[0.06] border border-indigo-500/20 dark:border-white/[0.14]',

        // Assessment Risk State Badges:
        // Dark: Distinguishable subtle semantic tints (restrained institutional palette)
        // Light: Soft semantic tints with deep text for high legibility
        riskLower:
          'bg-emerald-50 text-emerald-900 border border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-500/30 font-semibold',
        riskModerate:
          'bg-amber-50 text-amber-900 border border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-500/30 font-semibold',
        riskHigher:
          'bg-rose-50 text-rose-900 border border-rose-200/80 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-500/30 font-semibold',
        riskNeutral:
          'bg-slate-100 text-slate-800 border border-slate-200/80 dark:bg-slate-900/50 dark:text-slate-300 dark:border-slate-700/50 font-semibold',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
