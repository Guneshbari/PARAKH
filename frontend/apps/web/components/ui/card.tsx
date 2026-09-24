import * as React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.ComponentProps<'div'> {
  variant?: 'default' | 'elevated' | 'floating';
}

function Card({ className, variant = 'default', ...props }: CardProps) {
  return (
    <div
      data-slot="card"
      className={cn(
        'rounded-2xl p-5 sm:p-6 transition-all duration-200',
        variant === 'elevated'
          ? 'bg-surface dark:bg-surface-elevated text-foreground border border-border-strong shadow-card-elevated'
          : variant === 'floating'
          ? 'bg-surface dark:bg-surface-elevated text-foreground border border-border-strong shadow-floating'
          : 'bg-surface text-foreground border border-border shadow-card',
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn('flex flex-col gap-1.5 pb-4', className)}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<'h3'>) {
  return (
    <h3
      data-slot="card-title"
      className={cn('text-lg sm:text-xl font-bold tracking-tight text-foreground', className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return (
    <p
      data-slot="card-description"
      className={cn('text-sm text-foreground-secondary leading-relaxed', className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-content"
      className={cn('pt-0', className)}
      {...props}
    />
  );
}

function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex items-center pt-4 border-t border-border', className)}
      {...props}
    />
  );
}

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
