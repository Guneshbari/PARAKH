import * as React from 'react';
import { Button as ButtonPrimitive } from '@base-ui/react/button';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'group/button inline-flex shrink-0 items-center justify-center rounded-full border border-transparent bg-clip-padding text-sm font-semibold whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*=\'size-\'])]:size-4 cursor-pointer',
  {
    variants: {
      variant: {
        default:
          'bg-[#C8F451] text-[#07111F] hover:bg-[#B6E23B] font-bold shadow-[0_4px_16px_rgba(200,244,81,0.2)] hover:shadow-[0_6px_22px_rgba(200,244,81,0.3)] border border-transparent',
        lime:
          'bg-[#C8F451] text-[#07111F] hover:bg-[#B6E23B] font-bold shadow-[0_4px_16px_rgba(200,244,81,0.2)] hover:shadow-[0_6px_22px_rgba(200,244,81,0.3)] border border-transparent',
        secondary:
          'bg-[#0A162E]/90 text-[#F8FAFC] hover:bg-[#14274E] hover:text-[#22D3EE] border border-cyan-500/30 shadow-sm',
        outline:
          'border-white/[0.12] bg-[#0A162E]/60 text-[#F8FAFC] hover:bg-white/[0.06] hover:border-cyan-400/40',
        pillOutline:
          'bg-blue-500/10 hover:bg-blue-500/20 text-cyan-200 border border-cyan-400/35 hover:border-cyan-400/60 shadow-sm',
        ghost:
          'hover:bg-white/[0.06] text-[#A8B7CC] hover:text-[#F8FAFC] border-transparent',
        destructive:
          'bg-red-500/15 text-red-300 hover:bg-red-500/25 border border-red-500/25',
        link: 'text-cyan-400 underline-offset-4 hover:underline p-0 h-auto rounded-none',
        mint:
          'bg-emerald-400/15 text-emerald-300 border border-emerald-400/30 hover:bg-emerald-400/25',
        lavender:
          'bg-violet-500/15 text-violet-200 border border-violet-500/30 hover:bg-violet-500/25',
      },
      size: {
        default: 'h-9 gap-2 px-4',
        sm: 'h-7 gap-1.5 px-3 text-xs',
        lg: 'h-11 gap-2.5 px-6 text-sm sm:text-base font-bold',
        pill: 'h-8 gap-2 px-4 text-xs font-semibold',
        icon: 'size-9',
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
