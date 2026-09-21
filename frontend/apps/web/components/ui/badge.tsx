import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold tracking-wide transition-colors uppercase select-none',
  {
    variants: {
      variant: {
        default: 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30',
        secondary: 'bg-[#0E1F3D] text-[#F8FAFC] border border-white/[0.08]',
        outline: 'border border-white/[0.14] text-muted-foreground bg-transparent',
        mint: 'bg-emerald-400/15 text-emerald-300 border border-emerald-400/30',
        cyan: 'bg-cyan-400/15 text-cyan-300 border border-cyan-400/30',
        lime: 'bg-[#C8F451]/15 text-[#C8F451] border border-[#C8F451]/30',
        lavender: 'bg-violet-500/15 text-violet-300 border border-violet-500/30',
        ai: 'bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-[0_0_12px_rgba(139,92,246,0.15)]',
        // Assessment Risk State Badges
        riskLower: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
        riskModerate: 'bg-amber-400/15 text-amber-300 border border-amber-400/30',
        riskHigher: 'bg-red-400/15 text-red-300 border border-red-400/30',
        riskNeutral: 'bg-slate-400/15 text-slate-300 border border-slate-400/30',
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
