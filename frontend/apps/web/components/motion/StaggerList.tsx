'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { staggerContainer, fadeInUp } from '@/lib/animations';

interface StaggerListProps {
  children: React.ReactNode;
  className?: string;
  staggerDelay?: number;
}

export function StaggerList({
  children,
  className = '',
  staggerDelay = 0.08,
}: StaggerListProps) {
  const shouldReduceMotion = useReducedMotion();

  if (shouldReduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      variants={staggerContainer(staggerDelay)}
      initial="initial"
      animate="animate"
      className={className}
    >
      {React.Children.map(children, (child) => {
        if (!React.isValidElement(child)) return child;
        return <motion.div variants={fadeInUp}>{child}</motion.div>;
      })}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const shouldReduceMotion = useReducedMotion();

  if (shouldReduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div variants={fadeInUp} className={className}>
      {children}
    </motion.div>
  );
}
