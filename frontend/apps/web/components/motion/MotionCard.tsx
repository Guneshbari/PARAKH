'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { cardHoverMotion } from '@/lib/animations';

interface MotionCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  hoverable?: boolean;
  className?: string;
  onClick?: () => void;
}

export function MotionCard({
  children,
  hoverable = true,
  className,
  onClick,
  ...props
}: MotionCardProps) {
  const shouldReduceMotion = useReducedMotion();

  const baseStyles =
    'rounded-2xl bg-surface text-foreground border border-border p-5 sm:p-6 shadow-xs transition-colors';

  if (shouldReduceMotion || !hoverable) {
    return (
      <div
        className={cn(baseStyles, onClick && 'cursor-pointer hover:border-border-strong', className)}
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
        onClick && 'cursor-pointer',
        className
      )}
    >
      {children}
    </motion.div>
  );
}
