import * as React from 'react';
import { Button as ButtonPrimitive } from '@base-ui/react/button';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent text-xs sm:text-sm font-semibold whitespace-nowrap transition-all duration-150 outline-none select-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4 cursor-pointer',
  {
    variants: {
      variant: {
        // Primary button: Dark = #F5F5F5 on #08090A; Light = #111827 on #FFFFFF
        default:
          'bg-primary text-primary-foreground hover:opacity-90 shadow-sm border border-transparent font-bold',
        // Legacy alias mapped to new primary
        lime:
          'bg-primary text-primary-foreground hover:opacity-90 shadow-sm border border-transparent font-bold',
        // Secondary button: Dark = charcoal/translucent + white border; Light = white + subtle dark border
        secondary:
          'bg-secondary text-secondary-foreground border border-border hover:bg-surface-elevated shadow-xs font-semibold',
        outline:
          'border border-border bg-surface text-foreground hover:bg-surface-highlight hover:border-border-strong',
        pillOutline:
          'border border-border-strong bg-secondary text-foreground hover:bg-surface-highlight shadow-xs',
        ghost:
          'hover:bg-surface-highlight text-foreground-secondary hover:text-foreground border-transparent',
        destructive:
          'bg-red-500/15 text-red-400 hover:bg-red-500/25 border border-red-500/20',
        link: 'text-foreground underline-offset-4 hover:underline p-0 h-auto rounded-none',
        mint:
          'bg-emerald-500/10 text-emerald-500 dark:text-foreground border border-emerald-500/20 dark:border-border hover:bg-emerald-500/20',
        lavender:
          'bg-indigo-500/10 text-indigo-500 dark:text-foreground border border-indigo-500/20 dark:border-border hover:bg-indigo-500/20',
      },
      size: {
        default: 'h-8.5 gap-2 px-4 text-xs font-semibold',
        sm: 'h-7 gap-1.5 px-3 text-xs',
        lg: 'h-10.5 gap-2.5 px-6 text-sm font-bold',
        pill: 'h-8 gap-2 px-4 text-xs font-semibold',
        icon: 'size-8.5',
        'icon-sm': 'size-7',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

function Button({
  className,
  variant = 'default',
  size = 'default',
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
