import * as React from 'react';
import { cn } from '@/lib/utils';

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="skeleton"
      className={cn('animate-pulse rounded-2xl bg-white/[0.05]', className)}
      {...props}
    />
  );
}

export { Skeleton };
