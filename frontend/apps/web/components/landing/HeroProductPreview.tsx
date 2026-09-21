'use client';

import React, { useState } from 'react';
import { motion, useReducedMotion, type TargetAndTransition } from 'framer-motion';
import {
  Sparkles,
  TrendingUp,
  Activity,
  ArrowRight,
  Wifi,
  Battery,
  ScanLine,
  CheckCircle2,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MethodologyModal } from '@/components/shared/MethodologyModal';

export function HeroProductPreview() {
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);
  const shouldReduceMotion = useReducedMotion();

  // Gentle floating animation variants
  const leftFloatMotion: TargetAndTransition = shouldReduceMotion
    ? {}
    : {
        y: [-6, 6, -6],
        transition: {
          duration: 5.8,
          repeat: Infinity,
          ease: 'easeInOut' as const,
        },
      };

  const rightFloatMotion: TargetAndTransition = shouldReduceMotion
    ? {}
    : {
        y: [6, -6, 6],
        transition: {
          duration: 6.4,
          repeat: Infinity,
          ease: 'easeInOut' as const,
          delay: 0.5,
        },
      };

  return (
    <div className="relative w-full pt-2 sm:pt-4 pb-2 flex flex-col items-center justify-center">
      {/* Subtle ambient light behind phone (restrained, non-neon, behind phone) */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[480px] sm:w-[640px] h-[340px] sm:h-[420px] bg-foreground/[0.03] dark:bg-white/[0.03] blur-3xl pointer-events-none rounded-full -z-10"
        aria-hidden="true"
      />

      {/* Main Composition Anchor (Strictly Centered Phone and Outside Flanked Floating Cards) */}
      <div className="relative flex items-center justify-center min-h-[480px] sm:min-h-[520px]">
        {/* =========================================
            1. FLOATING LEFT CARD: TOTAL BALANCE
            Anchored outside phone's upper-left region
           ========================================= */}
        <motion.div
          animate={leftFloatMotion}
          className="hidden md:flex flex-col absolute top-2 sm:top-4 lg:top-6 right-[calc(100%+14px)] lg:right-[calc(100%+24px)] xl:right-[calc(100%+32px)] z-10 w-56 sm:w-60 lg:w-68 xl:w-72 scale-[0.78] lg:scale-95 xl:scale-100 origin-top-right rounded-2xl bg-surface/95 dark:bg-[#121416]/95 backdrop-blur-md border border-border dark:border-white/[0.12] p-4 lg:p-4.5 shadow-xl text-foreground space-y-2 pointer-events-auto"
        >
          <div className="flex items-center justify-between pb-1">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-xl bg-surface-elevated border border-border flex items-center justify-center text-foreground-secondary shadow-2xs">
                <TrendingUp className="size-3.5" />
              </div>
              <span className="text-xs font-semibold text-foreground-secondary">
                Total balance (12 month)
              </span>
            </div>
          </div>

          <div className="pt-0.5 flex items-baseline justify-between">
            <span className="text-2xl font-black text-foreground font-mono tracking-tight">
              ₹1,28,450
            </span>
            <span className="text-[11px] font-bold text-foreground bg-surface-elevated border border-border px-2 py-0.5 rounded-full flex items-center gap-0.5">
              +17%
            </span>
          </div>
          <span className="text-[11px] text-foreground-muted block -mt-1">
            credit the invisible
          </span>

          {/* Sparkline (Dark: monochrome white/gray dots; Light: clean teal/cyan) */}
          <div className="h-10 w-full pt-1.5">
            <svg viewBox="0 0 240 45" className="w-full h-full overflow-visible">
              <defs>
                <linearGradient id="incomeLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--chart-primary)" stopOpacity="0.85" />
                  <stop offset="50%" stopColor="var(--chart-secondary)" stopOpacity="0.95" />
                  <stop offset="100%" stopColor="var(--chart-tertiary)" stopOpacity="0.8" />
                </linearGradient>
              </defs>
              <path
                d="M 0 35 Q 25 10 50 28 T 100 24 T 150 12 T 200 22 T 240 8"
                fill="none"
                stroke="url(#incomeLineGrad)"
                strokeWidth="2.2"
                strokeLinecap="round"
              />
              <circle cx="50" cy="28" r="3" fill="var(--chart-primary)" />
              <circle cx="100" cy="24" r="3" fill="var(--chart-secondary)" />
              <circle cx="150" cy="12" r="3" fill="var(--chart-secondary)" />
              <circle cx="200" cy="22" r="3" fill="var(--chart-primary)" />
              <circle cx="240" cy="8" r="4" fill="var(--chart-primary)" />
            </svg>
          </div>
        </motion.div>

        {/* =========================================
            2. CENTRAL IPHONE MOCKUP (VISUAL ANCHOR)
           ========================================= */}
        <div
          data-testid="hero-phone"
          className="relative z-20 w-[290px] sm:w-[315px] md:w-[325px] lg:w-[340px] xl:w-[350px] rounded-[48px] p-[9px] bg-gradient-to-b from-[#334155] via-[#1E293B] to-[#0F172A] shadow-2xl border border-white/20 shrink-0 select-none"
        >
          {/* Inner Phone Screen (Light: #FFFFFF / #F7F8FC; Dark: #090A0B) */}
          <div className="relative w-full rounded-[40px] bg-white dark:bg-[#090A0B] border border-black/5 dark:border-white/[0.08] overflow-hidden text-foreground flex flex-col pt-3 pb-5 px-4 sm:px-5 transition-colors duration-200">
            {/* Dynamic Island Notch */}
            <div className="w-full flex items-center justify-between text-[11px] font-semibold text-foreground-muted pb-2 px-1">
              <span>9:41</span>
              <div className="h-5 w-24 rounded-full bg-black border border-white/10 flex items-center justify-end px-2 gap-1.5">
                <span className="size-1.5 rounded-full bg-emerald-400" />
                <span className="size-1.5 rounded-full bg-zinc-500" />
              </div>
              <div className="flex items-center gap-1.5">
                <Wifi className="size-3 text-foreground-muted" />
                <Battery className="size-3.5 text-foreground-muted" />
              </div>
            </div>

            {/* In-App Header */}
            <div className="pt-1.5 pb-2.5 flex items-center justify-between border-b border-border">
              <div className="flex items-center gap-2">
                <div className="size-6 rounded-lg bg-foreground text-background flex items-center justify-center font-black text-xs">
                  <Sparkles className="size-3.5" />
                </div>
                <span className="text-xs font-black tracking-tight font-mono text-foreground">
                  PARAKH
                </span>
              </div>
              <button
                type="button"
                aria-label="Scan QR or Share"
                className="p-1 rounded-lg text-foreground-muted hover:text-foreground hover:bg-surface-elevated"
              >
                <ScanLine className="size-3.5" />
              </button>
            </div>

            {/* Greeting */}
            <div className="pt-3 pb-2">
              <h2 className="text-xs sm:text-sm font-bold text-foreground tracking-tight">
                Good morning, Arjan
              </h2>
              <p className="text-[10px] text-foreground-muted">for the invisible.</p>
            </div>

            {/* Score Showcase Card */}
            <div className="p-3 rounded-2xl bg-surface-elevated dark:bg-[#121416] border border-border dark:border-white/[0.12] shadow-xs flex items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-black text-foreground font-mono tracking-tight">
                    742
                  </span>
                  <span className="text-[10px] text-foreground-muted font-mono">/ 850</span>
                </div>
                <Badge
                  variant="riskLower"
                  className="text-[9px] py-0.5 px-2 font-bold"
                >
                  <CheckCircle2 className="size-2.5 mr-1" />
                  LOWER RISK
                </Badge>
              </div>

              {/* Radial Gauge Visual */}
              <div className="relative size-15 sm:size-16 flex items-center justify-center shrink-0">
                <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="currentColor"
                    className="text-border"
                    strokeWidth="3.2"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="var(--chart-primary)"
                    strokeWidth="3.2"
                    strokeDasharray="88"
                    strokeDashoffset="18"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-[10px] font-bold text-foreground font-mono">742</span>
                  <span className="text-[7px] text-foreground-muted font-mono">/850</span>
                </div>
              </div>
            </div>

            {/* 3 Secondary Metrics Grid */}
            <div className="grid grid-cols-3 gap-1.5 pt-2.5 pb-2 text-center">
              <div className="p-1.5 rounded-xl bg-surface-elevated dark:bg-white/[0.02] border border-border">
                <span className="text-xs sm:text-sm font-bold text-foreground font-mono block">
                  21%
                </span>
                <span className="text-[8px] text-foreground-muted leading-tight block pt-0.5">
                  Difficulty
                </span>
              </div>
              <div className="p-1.5 rounded-xl bg-surface-elevated dark:bg-white/[0.02] border border-border">
                <span className="text-xs sm:text-sm font-bold text-foreground font-mono block">
                  87%
                </span>
                <span className="text-[8px] text-foreground-muted leading-tight block pt-0.5">
                  Confidence
                </span>
              </div>
              <div className="p-1.5 rounded-xl bg-surface-elevated dark:bg-white/[0.02] border border-border">
                <span className="text-xs sm:text-sm font-bold text-foreground font-mono block">
                  94%
                </span>
                <span className="text-[8px] text-foreground-muted leading-tight block pt-0.5">
                  Recovery
                </span>
              </div>
            </div>

            {/* Financial Health Section */}
            <div className="pt-2 border-t border-border space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-foreground-secondary font-medium flex items-center gap-1 text-[10px]">
                  <Activity className="size-3 text-foreground-muted" />
                  Alternative Assessment
                </span>
                <span className="text-[9px] font-bold text-foreground bg-surface-elevated border border-border px-1.5 py-0.2 rounded">
                  Now &gt;
                </span>
              </div>

              {/* Chart line */}
              <div className="h-10 w-full pt-1">
                <svg viewBox="0 0 260 40" className="w-full h-full overflow-visible">
                  <path
                    d="M 0 30 Q 30 15 65 24 T 130 16 T 195 26 T 260 12"
                    fill="none"
                    stroke="var(--chart-primary)"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle cx="65" cy="24" r="2.5" fill="var(--chart-primary)" />
                  <circle cx="130" cy="16" r="2.5" fill="var(--chart-secondary)" />
                  <circle cx="195" cy="26" r="2.5" fill="var(--chart-secondary)" />
                  <circle cx="260" cy="12" r="3" fill="var(--chart-primary)" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* =========================================
            3. FLOATING RIGHT CARD: TRENDS & INSIGHT
            Anchored outside phone's lower-right region
           ========================================= */}
        <motion.div
          animate={rightFloatMotion}
          className="hidden md:flex flex-col absolute bottom-8 sm:bottom-10 lg:bottom-12 xl:bottom-14 left-[calc(100%+14px)] lg:left-[calc(100%+24px)] xl:left-[calc(100%+32px)] z-10 w-64 sm:w-68 lg:w-76 xl:w-80 scale-[0.78] lg:scale-95 xl:scale-100 origin-bottom-left rounded-2xl bg-surface/95 dark:bg-[#121416]/95 backdrop-blur-md border border-border dark:border-white/[0.12] p-4 lg:p-4.5 shadow-xl text-foreground space-y-2.5 pointer-events-auto overflow-visible"
        >
          <div className="flex items-center justify-between pb-0.5">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-xl bg-surface-elevated border border-border flex items-center justify-center text-foreground shadow-2xs">
                <Sparkles className="size-3.5" />
              </div>
              <span className="text-xs font-bold text-foreground tracking-wide font-mono text-[11px]">
                Trends & Insight
              </span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-elevated border border-border text-foreground-muted">
              AI
            </span>
          </div>

          <p className="text-xs text-foreground-secondary leading-relaxed font-medium">
            &ldquo;Your income shows strong stability with positive recovery across multiple
            platforms, indicating healthy cash flow resilience.&rdquo;
          </p>

          <div className="pt-2 border-t border-border flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsMethodologyOpen(true)}
              className="rounded-full text-xs gap-1.5 h-7 px-3 cursor-pointer"
            >
              <span>View Breakdown</span>
              <ArrowRight className="size-3" />
            </Button>
            <span className="text-[10px] text-foreground-muted font-mono">Explainable AI</span>
          </div>

          {/* Corner diamond sparkle glint */}
          <div
            className="absolute -bottom-2 -right-2 size-5 pointer-events-none text-foreground opacity-80"
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="size-full">
              <path d="M 12 0 Q 12 12 24 12 Q 12 12 12 24 Q 12 12 0 12 Q 12 12 12 0 Z" />
            </svg>
          </div>
        </motion.div>
      </div>

      {/* =========================================
          4. MOBILE COMPACT FLOATING CARDS STRIP
          Only visible on small mobile screens (< md)
         ========================================= */}
      <div className="flex md:hidden flex-col sm:flex-row items-stretch gap-3 w-full max-w-sm sm:max-w-md pt-5 px-4">
        <div className="flex-1 rounded-2xl bg-surface dark:bg-[#121416] border border-border dark:border-white/[0.12] p-3.5 shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-surface-elevated border border-border flex items-center justify-center text-foreground shrink-0">
              <TrendingUp className="size-4" />
            </div>
            <div>
              <span className="text-[11px] text-foreground-muted block">Total Balance (12m)</span>
              <span className="text-base font-bold text-foreground font-mono">₹1,28,450</span>
            </div>
          </div>
          <span className="text-[10px] font-bold text-foreground bg-surface-elevated border border-border px-2 py-0.5 rounded-full">
            +17%
          </span>
        </div>

        <div className="flex-1 rounded-2xl bg-surface dark:bg-[#121416] border border-border dark:border-white/[0.12] p-3.5 shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-surface-elevated border border-border flex items-center justify-center text-foreground shrink-0">
              <Sparkles className="size-4" />
            </div>
            <div>
              <span className="text-[11px] text-foreground font-bold block font-mono">
                Trends & Insight
              </span>
              <span className="text-[11px] text-foreground-muted line-clamp-1">
                94% Recovery Resilience
              </span>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMethodologyOpen(true)}
            className="rounded-full text-[11px] h-7 px-3 shrink-0"
          >
            Breakdown
          </Button>
        </div>
      </div>

      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />
    </div>
  );
}
