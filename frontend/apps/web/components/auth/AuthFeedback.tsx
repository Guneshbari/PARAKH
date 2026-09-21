'use client';

import React from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ArrowRight, AlertCircle } from 'lucide-react';

export type AuthStatus = 'idle' | 'submitting' | 'error' | 'success';

export const SHAKE_KEYFRAMES = [0, -5, 4, -2, 0];
export const SUCCESS_COLOR = '#34C759';

/**
 * Animated SVG Checkmark with circular boundary ring
 * Reuses the OTP input design language with pathLength animation
 */
export function SuccessCheckRing({
  size = 18,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn('shrink-0 text-[#34C759]', className)}
      aria-hidden="true"
    >
      {/* Outer confirmation ring */}
      <motion.circle
        cx="12"
        cy="12"
        r="10"
        initial={shouldReduceMotion ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={
          shouldReduceMotion
            ? { duration: 0.1 }
            : {
                pathLength: { duration: 0.4, ease: 'easeOut' },
                opacity: { duration: 0.2 },
              }
        }
      />
      {/* Verification checkmark */}
      <motion.path
        d="M7.5 12.5L10.5 15.5L16.5 9.5"
        initial={shouldReduceMotion ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={
          shouldReduceMotion
            ? { duration: 0.1 }
            : {
                pathLength: { duration: 0.3, ease: 'easeOut', delay: 0.12 },
                opacity: { duration: 0.15, delay: 0.12 },
              }
        }
      />
    </svg>
  );
}

/**
 * Animated Card Wrapper for Authentication Forms
 * Triggers subtle horizontal shake on error and green status transition on success
 */
export function AuthFormCard({
  children,
  status,
  shakeKey = 0,
  className,
}: {
  children: React.ReactNode;
  status: AuthStatus;
  shakeKey?: number;
  className?: string;
}) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      key={shakeKey}
      animate={
        status === 'error' && !shouldReduceMotion
          ? { x: SHAKE_KEYFRAMES }
          : { x: 0 }
      }
      transition={{
        duration: 0.32,
        ease: 'easeOut',
      }}
      className={cn(
        'relative rounded-2xl border bg-surface p-6 sm:p-8 shadow-sm transition-colors duration-300',
        status === 'error' && 'border-destructive/50 ring-1 ring-destructive/15',
        status === 'success' && 'border-[#34C759]/60 ring-1 ring-[#34C759]/20',
        status !== 'error' && status !== 'success' && 'border-border',
        className
      )}
    >
      {/* Restrained success confirmation top accent line */}
      {status === 'success' && (
        <motion.div
          initial={shouldReduceMotion ? { opacity: 1, scaleX: 1 } : { opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="absolute -top-px left-6 right-6 h-0.5 bg-[#34C759] rounded-full shadow-[0_0_8px_rgba(52,199,89,0.35)]"
        />
      )}
      {children}
    </motion.div>
  );
}

/**
 * Authentication Feedback Alert Message
 * Clean, non-sensitive error and success alert with reduced-motion support
 */
export function AuthAlert({
  status,
  error,
  successMessage,
  className,
}: {
  status: AuthStatus;
  error?: string | null;
  successMessage?: string;
  className?: string;
}) {
  const shouldReduceMotion = useReducedMotion();

  if (status === 'error' && error) {
    return (
      <motion.div
        role="alert"
        aria-live="assertive"
        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
        className={cn(
          'mb-4 flex items-start gap-2.5 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs',
          className
        )}
      >
        <AlertCircle className="size-4 shrink-0 mt-0.5" />
        <span>{error}</span>
      </motion.div>
    );
  }

  if (status === 'success') {
    return (
      <motion.div
        role="status"
        aria-live="polite"
        initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={cn(
          'mb-4 flex items-center gap-2.5 p-3 rounded-xl bg-[#34C759]/10 border border-[#34C759]/25 text-foreground text-xs font-medium',
          className
        )}
      >
        <SuccessCheckRing size={16} />
        <span className="text-[#34C759] font-semibold">
          {successMessage || 'Credentials verified. Redirecting to workspace...'}
        </span>
      </motion.div>
    );
  }

  return null;
}

/**
 * Submit Button with Integrated Status Animation
 * IDLE -> SUBMITTING -> ERROR -> SUCCESS ("Verified")
 */
export function AuthSubmitButton({
  status,
  idleText,
  submittingText = 'Authenticating...',
  successText = 'Verified',
  idleIcon,
  disabled,
  className,
  type = 'submit',
}: {
  status: AuthStatus;
  idleText: string;
  submittingText?: string;
  successText?: string;
  idleIcon?: React.ReactNode;
  disabled?: boolean;
  className?: string;
  type?: 'submit' | 'button';
}) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <Button
      type={type}
      disabled={disabled || status === 'submitting' || status === 'success'}
      className={cn(
        'w-full h-10 mt-2 text-xs font-semibold gap-2 transition-all duration-300 cursor-pointer overflow-hidden relative',
        status === 'success' &&
          'bg-[#34C759] hover:bg-[#34C759] text-white dark:text-zinc-950 border-[#34C759] shadow-sm',
        className
      )}
    >
      <AnimatePresence mode="wait">
        {status === 'submitting' && (
          <motion.div
            key="submitting"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="flex items-center justify-center gap-2 w-full"
          >
            <span
              className="size-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"
              aria-hidden="true"
            />
            <span>{submittingText}</span>
          </motion.div>
        )}

        {status === 'success' && (
          <motion.div
            key="success"
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={
              shouldReduceMotion
                ? { duration: 0.15 }
                : { type: 'spring', stiffness: 500, damping: 35 }
            }
            className="flex items-center justify-center gap-2 w-full font-bold"
          >
            <SuccessCheckRing size={16} className="text-white dark:text-zinc-950" />
            <span>{successText}</span>
          </motion.div>
        )}

        {(status === 'idle' || status === 'error') && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="flex items-center justify-center gap-2 w-full"
          >
            <span>{idleText}</span>
            {idleIcon || <ArrowRight className="size-3.5" />}
          </motion.div>
        )}
      </AnimatePresence>
    </Button>
  );
}

/**
 * Returns dynamic class names for form inputs reflecting error/success states
 */
export function getAuthInputClassName(
  status: AuthStatus,
  hasSpecificError?: boolean
): string {
  if (status === 'success') {
    return 'border-[#34C759]/70 focus:border-[#34C759] focus-visible:ring-[#34C759]/25 transition-colors duration-200';
  }
  if (status === 'error' || hasSpecificError) {
    return 'border-destructive/60 focus:border-destructive focus-visible:ring-destructive/20 transition-colors duration-200';
  }
  return 'border-border transition-colors duration-200';
}
