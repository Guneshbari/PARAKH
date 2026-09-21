'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { cardHoverMotion } from '@/lib/animations';

interface MotionCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  hoverable?: boolean;
  variant?: 'default' | 'elevated' | 'floating';
  className?: string;
  onClick?: () => void;
}

export function MotionCard({
  children,
  hoverable = true,
  variant = 'default',
  className,
  onClick,
  ...props
}: MotionCardProps) {
  const shouldReduceMotion = useReducedMotion();

  const baseStyles = cn(
    'rounded-2xl p-5 sm:p-6 transition-all duration-200',
    variant === 'elevated'
      ? 'bg-surface dark:bg-surface-elevated text-foreground border border-border-strong shadow-card-elevated'
      : variant === 'floating'
      ? 'bg-surface dark:bg-surface-elevated text-foreground border border-border-strong shadow-floating'
      : 'bg-surface text-foreground border border-border shadow-card'
  );

  if (shouldReduceMotion || !hoverable) {
    return (
      <div
        className={cn(
          baseStyles,
          onClick && 'cursor-pointer hover:border-border-strong hover:shadow-card-hover',
          className
        )}
        onClick={onClick}
        {...props}
      >
        {children}
      </div>
    );
  }

  return (
    <motion.div
      variants={cardHoverMotion}
      initial="rest"
      whileHover="hover"
      whileTap={onClick ? 'tap' : undefined}
      onClick={onClick}
      className={cn(
        baseStyles,
        'hover:shadow-card-hover hover:border-border-strong',
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </motion.div>
  );
}
