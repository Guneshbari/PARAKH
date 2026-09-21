'use client';

import React, { useState } from 'react';
import { Sparkles, X, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { MethodologyModal } from './MethodologyModal';

interface AIInsightCardProps {
  title?: string;
  insight: string;
  detail?: string;
  actionLabel?: string;
  onAction?: () => void;
  dismissible?: boolean;
  className?: string;
}

export function AIInsightCard({
  title = 'PARAKH AI Insight',
  insight,
  detail,
  actionLabel = 'View Methodology',
  onAction,
  dismissible = true,
  className,
}: AIInsightCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  if (dismissed) return null;

  const handleAction = () => {
    if (onAction) {
      onAction();
    } else {
      setIsMethodologyOpen(true);
    }
  };

  return (
    <>
      <div
        className={cn(
          'rounded-2xl bg-surface dark:bg-surface-elevated border border-border-strong p-5 text-foreground shadow-card-elevated relative overflow-hidden transition-all duration-200',
          className
        )}
      >
        {/* Subtle accent line on top (subdued, not neon) */}
        <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-[#472393]/35 via-[#472393]/15 to-transparent dark:from-foreground/25 dark:via-foreground/10" />

        {/* Header with Sparkle and Dismiss */}
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-foreground tracking-wide">
            <Sparkles className="size-3.5 text-foreground" />
            <span className="uppercase tracking-wider text-[11px] font-mono">{title}</span>
          </div>

          {dismissible && (
            <button
              onClick={() => setDismissed(true)}
              aria-label="Dismiss insight"
              className="p-1 rounded-lg text-foreground-muted hover:text-foreground hover:bg-surface-elevated transition-colors cursor-pointer"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Insight Text */}
        <p className="text-xs sm:text-sm font-medium text-foreground-secondary leading-relaxed pr-2">
          &ldquo;{insight}&rdquo;
        </p>

        {/* Expandable Detail */}
        <AnimatePresence>
          {expanded && detail && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="pt-3 text-xs text-foreground-muted leading-relaxed border-t border-border mt-3"
            >
              {detail}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Action Footer */}
        {(actionLabel || detail) && (
          <div className="pt-3 flex items-center justify-between gap-2 border-t border-border mt-3">
            {detail ? (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs font-semibold text-foreground-secondary hover:text-[#472393] dark:hover:text-foreground flex items-center gap-1 cursor-pointer transition-colors"
              >
                <span>{expanded ? 'Less context' : 'Why this insight?'}</span>
                {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
              </button>
            ) : (
              <span className="text-[10px] text-foreground-muted font-mono">Explainable Model Signal</span>
            )}

            {actionLabel && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleAction}
                className="rounded-full text-xs font-semibold gap-1.5 h-7 px-3.5 cursor-pointer shadow-none"
              >
                <span>{actionLabel}</span>
                <ArrowRight className="size-3" />
              </Button>
            )}
          </div>
        )}
      </div>

      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />
    </>
  );
}
