import * as React from 'react';
import { cn } from '@/lib/utils';

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'flex h-10 w-full rounded-xl border border-border bg-surface px-3.5 py-2 text-xs sm:text-sm text-foreground transition-colors placeholder:text-foreground-muted/70 focus:border-[#472393] focus:outline-none focus:ring-2 focus:ring-[#472393]/20 dark:focus:border-border-strong dark:focus:ring-foreground/10 disabled:cursor-not-allowed disabled:opacity-50 font-medium shadow-2xs',
        className
      )}
      {...props}
    />
  );
}

export { Input };
