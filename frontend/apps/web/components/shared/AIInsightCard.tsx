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
          'rounded-2xl bg-[#0A162E] border border-violet-500/25 p-5 text-slate-100 shadow-sm relative overflow-hidden transition-all',
          className
        )}
      >
        {/* Subtle accent bar */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-violet-500/60 via-cyan-400/50 to-transparent" />

        {/* Header with Sparkle and Dismiss */}
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-violet-300 tracking-wide">
            <Sparkles className="size-4 text-cyan-400" />
            <span className="uppercase tracking-wider text-[11px] font-mono">{title}</span>
          </div>

          {dismissible && (
            <button
              onClick={() => setDismissed(true)}
              aria-label="Dismiss insight"
              className="p-1 rounded-lg text-violet-300/60 hover:text-violet-200 hover:bg-white/[0.05] transition-colors cursor-pointer"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        {/* Insight Text */}
        <p className="text-sm font-medium text-slate-100 leading-relaxed pr-2">
          &ldquo;{insight}&rdquo;
        </p>

        {/* Expandable Detail */}
        <AnimatePresence>
          {expanded && detail && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="pt-3 text-xs text-violet-200/80 leading-relaxed border-t border-violet-500/15 mt-3"
            >
              {detail}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Action Footer */}
        {(actionLabel || detail) && (
          <div className="pt-3.5 flex items-center justify-between gap-2 border-t border-violet-500/15 mt-3">
            {detail ? (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs font-semibold text-violet-300 hover:text-violet-100 flex items-center gap-1 cursor-pointer transition-colors"
              >
                <span>{expanded ? 'Less context' : 'Why this insight?'}</span>
                {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
              </button>
            ) : (
              <span className="text-[11px] text-violet-300/70 font-mono">Explainable Model Signal</span>
            )}

            {actionLabel && (
              <Button
                variant="pillOutline"
                size="sm"
                onClick={handleAction}
                className="rounded-full text-xs gap-1.5 h-7 px-3.5 bg-violet-500/10 hover:bg-violet-500/20 text-cyan-200 border-violet-400/30 hover:border-cyan-400/50 cursor-pointer transition-all"
              >
                <span>{actionLabel}</span>
                <ArrowRight className="size-3 text-cyan-400" />
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
