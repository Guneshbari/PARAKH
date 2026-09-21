import * as React from 'react';
import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'flex h-11 w-full rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-2 text-sm text-foreground transition-colors placeholder:text-muted-foreground/60 focus:border-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-400/20 disabled:cursor-not-allowed disabled:opacity-50 font-medium',
        className
      )}
      {...props}
    />
  );
}

export { Input };
