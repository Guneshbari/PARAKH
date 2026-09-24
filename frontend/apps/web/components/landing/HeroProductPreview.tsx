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
  ShieldCheck,
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
    <div className="relative w-full pt-1 sm:pt-2 pb-2 flex flex-col items-center justify-center">
      {/* Subtle ambient light behind phone (restrained, non-neon, behind phone) */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[480px] sm:w-[600px] lg:w-[680px] h-[480px] sm:h-[580px] lg:h-[640px] bg-[rgba(148,163,184,0.08)] dark:bg-white/[0.03] blur-3xl pointer-events-none rounded-full -z-10"
        aria-hidden="true"
      />

      {/* Main Composition Anchor (Mathematically Centered Phone and Outside Flanked Floating Cards) */}
      <div className="relative flex items-start justify-center">
        {/* =========================================
            1. FLOATING LEFT CARD: TOTAL BALANCE
            Anchored outside phone's upper-left region
           ========================================= */}
        <motion.div
          animate={leftFloatMotion}
          className="hidden md:flex flex-col absolute top-5 sm:top-6 lg:top-7.5 right-[calc(100%+12px)] lg:right-[calc(100%+24px)] xl:right-[calc(100%+32px)] z-10 w-56 sm:w-60 lg:w-68 xl:w-72 scale-[0.74] lg:scale-95 xl:scale-100 origin-top-right pointer-events-auto"
        >
          <motion.div
            whileHover={
              shouldReduceMotion
                ? {}
                : {
                    y: -4,
                    scale: 1.01,
                    transition: { duration: 0.35, ease: 'easeOut' },
                  }
            }
            className="w-full rounded-2xl bg-white/96 dark:bg-[#121416]/95 border border-[rgba(71,85,105,0.14)] dark:border-white/[0.12] p-4 lg:p-4.5 shadow-[0_18px_45px_rgba(15,23,42,0.10),0_4px_12px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.95)] hover:shadow-[0_22px_50px_rgba(15,23,42,0.13),0_6px_16px_rgba(15,23,42,0.06),inset_0_1px_0_rgba(255,255,255,0.95)] dark:shadow-xl dark:hover:shadow-2xl text-foreground space-y-2 transition-all duration-300"
          >
            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-2">
                <div className="size-7 rounded-xl bg-[#EEF2FF] hover:bg-[#E0E7FF] dark:bg-surface-elevated border border-[#C7D2FE]/60 dark:border-border flex items-center justify-center text-[#4F46E5] dark:text-foreground-secondary shadow-2xs transition-colors">
                  <TrendingUp className="size-3.5" />
                </div>
                <span className="text-xs font-semibold text-[#172033] dark:text-foreground-secondary">
                  Total balance (12 month)
                </span>
              </div>
            </div>

            <div className="pt-0.5 flex items-baseline justify-between">
              <span className="text-2xl font-black text-[#101828] dark:text-foreground font-mono tracking-tight">
                ₹1,28,450
              </span>
              <span className="text-xs font-bold text-[#101828] dark:text-foreground bg-[#F1F5F9] dark:bg-surface-elevated border border-[rgba(15,23,42,0.08)] dark:border-border px-2.5 py-0.5 rounded-full flex items-center gap-0.5">
                +17%
              </span>
            </div>
            <span className="text-xs text-[#334155] dark:text-foreground-secondary block -mt-0.5 font-medium">
              credit the invisible
            </span>

            {/* Sparkline (Dark: monochrome white/gray dots; Light: clean blue/lavender/cyan) */}
            <div className="h-10 w-full pt-1.5">
              <svg viewBox="0 0 240 45" className="w-full h-full overflow-visible">
                <defs>
                  <linearGradient id="incomeLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#60A5FA" stopOpacity="0.85" />
                    <stop offset="50%" stopColor="#818CF8" stopOpacity="0.95" />
                    <stop offset="100%" stopColor="#22D3EE" stopOpacity="0.85" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0 35 Q 25 10 50 28 T 100 24 T 150 12 T 200 22 T 240 8"
                  fill="none"
                  stroke="url(#incomeLineGrad)"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                />
                <circle cx="50" cy="28" r="3" fill="#60A5FA" className="dark:fill-[var(--chart-primary)]" />
                <circle cx="100" cy="24" r="3" fill="#818CF8" className="dark:fill-[var(--chart-secondary)]" />
                <circle cx="150" cy="12" r="3" fill="#818CF8" className="dark:fill-[var(--chart-secondary)]" />
                <circle cx="200" cy="22" r="3" fill="#22D3EE" className="dark:fill-[var(--chart-primary)]" />
                <circle cx="240" cy="8" r="4" fill="#60A5FA" className="dark:fill-[var(--chart-primary)]" />
              </svg>
            </div>
          </motion.div>
        </motion.div>

        {/* =========================================
            2. CENTRAL SMARTPHONE MOCKUP (VISUAL ANCHOR)
            Compact height (~550px) with subtle CSS 3D depth
           ========================================= */}
        <motion.div
          data-testid="hero-phone"
          whileHover={
            shouldReduceMotion
              ? {}
              : {
                rotateY: -2.5,
                rotateX: 0.5,
                y: -2,
                transition: { duration: 0.5, ease: 'easeOut' },
              }
          }
          style={{
            transform: shouldReduceMotion
              ? 'none'
              : 'perspective(1200px) rotateY(-5deg) rotateX(1deg)',
            transformOrigin: 'center center',
            transformStyle: 'preserve-3d',
          }}
          className="relative z-20 w-[248px] sm:w-[264px] md:w-[274px] lg:w-[282px] xl:w-[288px] h-[498px] sm:h-[512px] md:h-[528px] lg:h-[542px] xl:h-[552px] rounded-[44px] p-[7.5px] sm:p-[8px] bg-gradient-to-tr from-[#1E293B] via-[#334155] to-[#0F172A] border-t border-l border-white/25 border-b border-r border-black/60 shadow-[0_22px_55px_rgba(15,23,42,0.16),0_4px_18px_rgba(100,116,139,0.10),-1px_0_0_1px_rgba(255,255,255,0.08),-4px_4px_12px_-2px_rgba(0,0,0,0.4),10px_24px_48px_-12px_rgba(0,0,0,0.5)] dark:shadow-[-1px_0_0_1px_rgba(255,255,255,0.08),-4px_4px_12px_-2px_rgba(0,0,0,0.65),10px_24px_48px_-12px_rgba(0,0,0,0.75)] shrink-0 select-none flex flex-col transition-shadow duration-500 hover:shadow-[0_26px_65px_rgba(15,23,42,0.20),0_6px_22px_rgba(100,116,139,0.14),-1px_0_0_1px_rgba(255,255,255,0.12),-5px_5px_16px_-2px_rgba(0,0,0,0.5),14px_30px_56px_-12px_rgba(0,0,0,0.6)] dark:hover:shadow-[-1px_0_0_1px_rgba(255,255,255,0.12),-5px_5px_16px_-2px_rgba(0,0,0,0.75),14px_30px_56px_-12px_rgba(0,0,0,0.85)]"
        >
          {/* Subtle 3D edge highlight on the left bezel */}
          <div
            className="absolute top-8 left-[1px] bottom-8 w-[1.5px] bg-gradient-to-b from-transparent via-white/20 to-transparent pointer-events-none rounded-full"
            aria-hidden="true"
          />

          {/* Inner Bezel Layer (Recessed depth) */}
          <div className="relative w-full h-full rounded-[38px] p-[2px] bg-black/60 shadow-[inset_0_2px_4px_rgba(0,0,0,0.8),inset_0_0_0_1px_rgba(255,255,255,0.05)]">
            {/* Inner Phone Screen (Continuous mobile fintech app flow with enhanced readability) */}
            <div
              data-testid="phone-screen"
              className="relative w-full h-full rounded-[36px] bg-[#F8FAFC] dark:bg-[#090A0B] border border-[rgba(15,23,42,0.08)] dark:border-white/[0.08] overflow-hidden text-[#0F172A] dark:text-foreground flex flex-col pt-2.5 pb-2 px-3.5 sm:px-4 shadow-[inset_0_1px_2px_rgba(255,255,255,0.8),inset_0_-2px_4px_rgba(0,0,0,0.1)] dark:shadow-[inset_0_1px_2px_rgba(255,255,255,0.08),inset_0_-2px_4px_rgba(0,0,0,0.4)] transition-colors duration-200"
            >
              {/* 1. Dynamic Island Notch & Status Bar (~20px) */}
              <div className="w-full flex items-center justify-between text-[10px] font-semibold text-[#64748B] dark:text-foreground-muted pb-0.5 px-0.5 shrink-0">
                <span className="font-mono">9:41</span>
                <div className="h-4.5 w-20 rounded-full bg-black border border-white/10 flex items-center justify-end px-2 gap-1.5 shadow-xs">
                  <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="size-1.5 rounded-full bg-zinc-500" />
                </div>
                <div className="flex items-center gap-1.5">
                  <Wifi className="size-3 text-[#64748B] dark:text-foreground-muted" />
                  <Battery className="size-3.5 text-[#64748B] dark:text-foreground-muted" />
                </div>
              </div>

              {/* 2. In-App Header (~24px) */}
              <div className="pt-0.5 pb-1.5 flex items-center justify-between border-b border-[rgba(15,23,42,0.08)] dark:border-border/80 shrink-0">
                <div className="flex items-center gap-1.5">
                  <div className="size-5 rounded-md bg-[#472393] text-white dark:bg-foreground dark:text-background flex items-center justify-center font-black text-[10px]">
                    <Sparkles className="size-3" />
                  </div>
                  <span className="text-[11px] font-extrabold tracking-tight font-mono text-[#0F172A] dark:text-foreground">
                    PARAKH
                  </span>
                </div>
                <button
                  type="button"
                  aria-label="Scan QR or Share"
                  className="p-1 rounded-md text-[#64748B] hover:text-[#0F172A] hover:bg-[#EEF2F6] dark:text-foreground-muted dark:hover:text-foreground dark:hover:bg-surface-elevated transition-colors"
                >
                  <ScanLine className="size-3.5" />
                </button>
              </div>

              {/* Main Content Area: Fills naturally with 5-9px compact rhythm */}
              <div className="flex-1 flex flex-col min-h-0">
                {/* 3. Greeting with Compact Status (~32px) */}
                <div className="pt-2 sm:pt-2.5 pb-0 shrink-0 flex items-baseline justify-between">
                  <div>
                    <h2 className="text-[11.5px] sm:text-[12px] font-bold text-[#0F172A] dark:text-foreground tracking-tight leading-tight">
                      Good morning, Arjun
                    </h2>
                    <p className="text-[8.5px] sm:text-[9px] text-[#475569] dark:text-foreground-muted leading-tight pt-0.5 font-medium">Credit for the invisible.</p>
                  </div>
                  <span className="text-[7.5px] sm:text-[8px] font-mono text-emerald-600 dark:text-emerald-400 flex items-center gap-1 bg-white dark:bg-white/[0.04] border border-[rgba(15,23,42,0.08)] dark:border-border/60 px-1.5 py-0.5 rounded-full font-semibold">
                    <span className="size-1 rounded-full bg-emerald-500" />
                    2h ago
                  </span>
                </div>

                {/* 4. Score Showcase Card (PRIMARY FOCAL POINT ~76-80px) */}
                <div className="mt-2 sm:mt-2.5 p-2.5 sm:p-3 rounded-xl bg-white dark:bg-[#121416] border border-[rgba(15,23,42,0.08)] dark:border-white/[0.1] shadow-2xs flex items-center justify-between gap-3 shrink-0">
                  <div className="space-y-1">
                    <div className="flex items-baseline gap-1">
                      <span className="text-[26px] sm:text-[28px] font-black text-[#0F172A] dark:text-foreground font-mono tracking-tight leading-none">
                        742
                      </span>
                      <span className="text-[8.5px] font-mono text-[#64748B] dark:text-foreground-muted font-semibold">/ 850</span>
                    </div>
                    <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-600 dark:text-emerald-400 text-[8px] font-bold tracking-wide">
                      <CheckCircle2 className="size-2.5 shrink-0" />
                      <span>LOWER RISK</span>
                    </div>
                  </div>

                  {/* Radial Score Gauge Visual (~42-44px) */}
                  <div className="relative size-11 sm:size-11.5 flex items-center justify-center shrink-0">
                    <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                      <defs>
                        <linearGradient id="phoneScoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#22C1DC" />
                          <stop offset="50%" stopColor="#60A5FA" />
                          <stop offset="100%" stopColor="#6366F1" />
                        </linearGradient>
                      </defs>
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="currentColor"
                        className="text-slate-200 dark:text-border/60"
                        strokeWidth="3.2"
                      />
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="url(#phoneScoreGrad)"
                        className="dark:stroke-[var(--chart-primary)]"
                        strokeWidth="3.2"
                        strokeDasharray="88"
                        strokeDashoffset="18"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                      <span className="text-[9.5px] font-black text-[#0F172A] dark:text-foreground font-mono leading-none">
                        742
                      </span>
                      <span className="text-[6.5px] text-[#64748B] dark:text-foreground-muted font-mono leading-none pt-0.5 font-bold">
                        TOP 15%
                      </span>
                    </div>
                  </div>
                </div>

                {/* 5. 3 Secondary Metrics Grid (~40-42px) */}
                <div className="mt-2 sm:mt-2.5 grid grid-cols-3 gap-1.5 text-center shrink-0">
                  <div className="py-1.5 px-1 rounded-lg bg-white dark:bg-white/[0.025] border border-[rgba(15,23,42,0.08)] dark:border-border/80 shadow-2xs">
                    <span className="text-[11px] font-bold text-[#0F172A] dark:text-foreground font-mono block leading-tight">
                      21%
                    </span>
                    <span className="text-[7.5px] sm:text-[8px] text-[#64748B] dark:text-foreground-muted font-medium block pt-0.5 whitespace-nowrap">
                      Difficulty
                    </span>
                  </div>
                  <div className="py-1.5 px-1 rounded-lg bg-white dark:bg-white/[0.025] border border-[rgba(15,23,42,0.08)] dark:border-border/80 shadow-2xs">
                    <span className="text-[11px] font-bold text-[#0F172A] dark:text-foreground font-mono block leading-tight">
                      87%
                    </span>
                    <span className="text-[7.5px] sm:text-[8px] text-[#64748B] dark:text-foreground-muted font-medium block pt-0.5 whitespace-nowrap">
                      Confidence
                    </span>
                  </div>
                  <div className="py-1.5 px-1 rounded-lg bg-white dark:bg-white/[0.025] border border-[rgba(15,23,42,0.08)] dark:border-border/80 shadow-2xs">
                    <span className="text-[11px] font-bold text-[#0F172A] dark:text-foreground font-mono block leading-tight">
                      94%
                    </span>
                    <span className="text-[7.5px] sm:text-[8px] text-[#64748B] dark:text-foreground-muted font-medium block pt-0.5 whitespace-nowrap">
                      Recovery
                    </span>
                  </div>
                </div>

                {/* 6. Income Stability Row (~24px) */}
                <div className="mt-2 sm:mt-2.5 px-2.5 py-1.5 rounded-lg bg-white dark:bg-white/[0.025] border border-[rgba(15,23,42,0.08)] dark:border-border/70 flex items-center justify-between shrink-0 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-foreground-secondary font-medium">
                    <span className="size-1.5 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-[8.5px] sm:text-[9px] font-semibold text-[#0F172A] dark:text-foreground">Income Stability</span>
                  </div>
                  <span className="font-mono text-emerald-600 dark:text-emerald-300 font-bold text-[8.5px] sm:text-[9px]">
                    Stable · 94%
                  </span>
                </div>

                {/* 7. Alternative Assessment & Cashflow Chart Section (~50-54px) */}
                <div className="mt-2 sm:mt-2.5 pt-1.5 border-t border-[rgba(15,23,42,0.08)] dark:border-border/70 space-y-1 shrink-0">
                  <div className="flex items-center justify-between">
                    <span className="text-[#0F172A] dark:text-foreground font-semibold flex items-center gap-1.5 text-[9.5px] sm:text-[10px]">
                      <Activity className="size-3 text-[#64748B] dark:text-foreground-muted" />
                      Alternative Assessment
                    </span>
                    <span className="text-[8px] font-bold text-[#0F172A] dark:text-foreground bg-[#EEF2F6] dark:bg-surface-elevated border border-[rgba(15,23,42,0.08)] dark:border-border/80 px-1.5 py-0.5 rounded leading-none flex items-center gap-0.5">
                      Now &rarr;
                    </span>
                  </div>

                  {/* Clear Chart Line */}
                  <div className="h-8 w-full pt-0.5">
                    <svg viewBox="0 0 260 36" className="w-full h-full overflow-visible">
                      <path
                        d="M 0 26 Q 30 12 65 20 T 130 14 T 195 22 T 260 10"
                        fill="none"
                        stroke="#0F172A"
                        className="dark:stroke-[var(--chart-primary)]"
                        strokeWidth="2.4"
                        strokeLinecap="round"
                      />
                      <circle cx="65" cy="20" r="2.5" fill="#0F172A" className="dark:fill-[var(--chart-primary)]" />
                      <circle cx="130" cy="14" r="2.5" fill="#60A5FA" className="dark:fill-[var(--chart-secondary)]" />
                      <circle cx="195" cy="22" r="2.5" fill="#60A5FA" className="dark:fill-[var(--chart-secondary)]" />
                      <circle cx="260" cy="10" r="3" fill="#0F172A" className="dark:fill-[var(--chart-primary)]" />
                    </svg>
                  </div>
                </div>

                {/* 8. Signal Coverage Mini Row (~44-46px) */}
                <div className="mt-2 sm:mt-2.5 p-1.5 sm:p-2 rounded-lg bg-white dark:bg-white/[0.025] border border-[rgba(15,23,42,0.08)] dark:border-border/70 shrink-0 shadow-2xs">
                  <div className="flex items-center justify-between mb-1.5 px-0.5">
                    <span className="font-bold text-[9.5px] sm:text-[10px] text-[#0F172A] dark:text-foreground flex items-center gap-1.5">
                      <ShieldCheck className="size-3 text-emerald-500" />
                      Signal Coverage
                    </span>
                    <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold text-[8px]">94% Fresh</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
                    <div className="bg-[#F8FAFC] dark:bg-white/[0.03] rounded-md px-1 py-1 border border-[rgba(15,23,42,0.06)] dark:border-border/50">
                      <span className="text-[10.5px] sm:text-[11px] font-bold text-[#0F172A] dark:text-foreground block leading-none">12</span>
                      <span className="text-[7.5px] text-[#64748B] dark:text-foreground-muted font-sans font-medium block pt-0.5 whitespace-nowrap">Signals</span>
                    </div>
                    <div className="bg-[#F8FAFC] dark:bg-white/[0.03] rounded-md px-1 py-1 border border-[rgba(15,23,42,0.06)] dark:border-border/50">
                      <span className="text-[10.5px] sm:text-[11px] font-bold text-[#0F172A] dark:text-foreground block leading-none">8</span>
                      <span className="text-[7.5px] text-[#64748B] dark:text-foreground-muted font-sans font-medium block pt-0.5 whitespace-nowrap">Sources</span>
                    </div>
                    <div className="bg-[#F8FAFC] dark:bg-white/[0.03] rounded-md px-1 py-1 border border-[rgba(15,23,42,0.06)] dark:border-border/50">
                      <span className="text-[10.5px] sm:text-[11px] font-bold text-[#0F172A] dark:text-foreground block leading-none">94%</span>
                      <span className="text-[7.5px] text-[#64748B] dark:text-foreground-muted font-sans font-medium block pt-0.5 whitespace-nowrap">Fresh</span>
                    </div>
                  </div>
                </div>

                {/* 9. Recent Activity Compact Row (~24-26px) */}
                <div className="mt-1.5 sm:mt-2 px-2.5 py-1.5 rounded-lg bg-white dark:bg-white/[0.02] border border-[rgba(15,23,42,0.08)] dark:border-border/70 flex items-center justify-between shrink-0 shadow-2xs">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="size-1.5 rounded-full bg-emerald-500 shrink-0" />
                    <span className="font-semibold text-[#0F172A] dark:text-foreground truncate text-[8.5px] sm:text-[9px] leading-tight">
                      Income pattern stable
                    </span>
                  </div>
                  <span className="font-mono text-[#64748B] dark:text-foreground-muted text-[7.5px] sm:text-[8px] shrink-0 ml-1.5 font-medium">
                    2h ago
                  </span>
                </div>
              </div>

              {/* 10. Bottom In-App Dock & Home Indicator (Anchored at the bottom) */}
              <div className="mt-auto pt-2 border-t border-[rgba(15,23,42,0.08)] dark:border-border/70 shrink-0">
                <div className="flex items-center justify-around px-1 text-foreground-muted">
                  <div className="flex flex-col items-center gap-0.5 text-[#0F172A] dark:text-foreground">
                    <span className="text-[8.5px] font-bold tracking-tight">Overview</span>
                    <div className="size-1 rounded-full bg-[#0F172A] dark:bg-foreground" />
                  </div>
                  <div className="flex flex-col items-center gap-0.5 text-[#64748B] dark:text-foreground-muted hover:text-[#0F172A] dark:hover:text-foreground cursor-pointer">
                    <span className="text-[8px] font-semibold">Timeline</span>
                    <div className="size-1 rounded-full bg-transparent" />
                  </div>
                  <div className="flex flex-col items-center gap-0.5 text-[#64748B] dark:text-foreground-muted hover:text-[#0F172A] dark:hover:text-foreground cursor-pointer">
                    <span className="text-[8px] font-semibold">Verify</span>
                    <div className="size-1 rounded-full bg-transparent" />
                  </div>
                  <div className="flex flex-col items-center gap-0.5 text-[#64748B] dark:text-foreground-muted hover:text-[#0F172A] dark:hover:text-foreground cursor-pointer">
                    <span className="text-[8px] font-semibold">SHAP</span>
                    <div className="size-1 rounded-full bg-transparent" />
                  </div>
                </div>

                {/* Home Indicator Bar (10-12px below navigation tabs) */}
                <div className="pt-2 pb-0.5 flex justify-center" aria-hidden="true">
                  <div className="w-20 sm:w-24 h-1 rounded-full bg-slate-300 dark:bg-white/25" />
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* =========================================
            3. FLOATING RIGHT CARD: TRENDS & INSIGHT
            Anchored outside phone's upper-right region
            Aligned with Total Balance card top edge
           ========================================= */}
        <motion.div
          animate={rightFloatMotion}
          className="hidden md:flex flex-col absolute top-5 sm:top-6 lg:top-7.5 left-[calc(100%+12px)] lg:left-[calc(100%+24px)] xl:left-[calc(100%+32px)] z-10 w-64 sm:w-68 lg:w-76 xl:w-80 scale-[0.74] lg:scale-95 xl:scale-100 origin-top-left pointer-events-auto overflow-visible"
        >
          <motion.div
            whileHover={
              shouldReduceMotion
                ? {}
                : {
                    y: -4,
                    scale: 1.01,
                    transition: { duration: 0.35, ease: 'easeOut' },
                  }
            }
            className="w-full rounded-2xl bg-white/96 dark:bg-[#121416]/95 border border-[rgba(71,85,105,0.14)] dark:border-white/[0.12] p-4 lg:p-4.5 shadow-[0_18px_45px_rgba(15,23,42,0.10),0_4px_12px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.95)] hover:shadow-[0_22px_50px_rgba(15,23,42,0.13),0_6px_16px_rgba(15,23,42,0.06),inset_0_1px_0_rgba(255,255,255,0.95)] dark:shadow-xl dark:hover:shadow-2xl text-foreground space-y-2.5 transition-all duration-300 relative overflow-visible"
          >
            <div className="flex items-center justify-between pb-0.5">
              <div className="flex items-center gap-2">
                <div className="size-7 rounded-xl bg-[#F6F2FF] hover:bg-[#EDE9FE] dark:bg-surface-elevated border border-[rgba(71,35,147,0.22)] dark:border-border flex items-center justify-center text-[#472393] dark:text-foreground shadow-2xs transition-colors">
                  <Sparkles className="size-3.5" />
                </div>
                <span className="text-xs sm:text-sm font-bold text-[#172033] dark:text-foreground tracking-wide font-mono">
                  Trends & Insight
                </span>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#F6F2FF] dark:bg-surface-elevated border border-[rgba(71,35,147,0.22)] dark:border-border text-[#472393] dark:text-foreground-secondary font-semibold">
                AI
              </span>
            </div>

            <p className="text-xs sm:text-sm text-[#334155] dark:text-foreground-secondary leading-relaxed font-medium">
              &ldquo;Your income shows strong stability with positive recovery across multiple
              platforms, indicating healthy cash flow resilience.&rdquo;
            </p>

            <div className="pt-2 border-t border-[rgba(15,23,42,0.08)] dark:border-border flex items-center justify-between">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsMethodologyOpen(true)}
                className="rounded-full text-xs sm:text-sm gap-1.5 h-8 px-3.5 cursor-pointer bg-white text-[#472393] border border-[rgba(71,35,147,0.22)] hover:bg-[#F6F2FF] hover:border-[rgba(71,35,147,0.35)] dark:bg-transparent dark:text-foreground dark:border-border"
              >
                <span>View Breakdown</span>
                <ArrowRight className="size-3 text-[#472393] dark:text-foreground" />
              </Button>
              <span className="text-xs text-[#334155] dark:text-foreground-secondary font-mono font-medium">Explainable AI</span>
            </div>

            {/* Corner diamond sparkle glint */}
            <div
              className="absolute -bottom-2 -right-2 size-5 pointer-events-none text-[#7C8DB5] dark:text-foreground opacity-80"
              aria-hidden="true"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" className="size-full">
                <path d="M 12 0 Q 12 12 24 12 Q 12 12 12 24 Q 12 12 0 12 Q 12 12 12 0 Z" />
              </svg>
            </div>
          </motion.div>
        </motion.div>
      </div>


      {/* =========================================
          4. MOBILE COMPACT FLOATING CARDS STRIP
          Only visible on small mobile screens (< md)
          ========================================= */}
      <div className="flex md:hidden flex-col sm:flex-row items-stretch gap-3 w-full max-w-sm sm:max-w-md pt-5 px-4">
        <div className="flex-1 rounded-2xl bg-white/96 dark:bg-[#121416] border border-[rgba(71,85,105,0.14)] dark:border-white/[0.12] p-3.5 shadow-[0_8px_24px_rgba(15,23,42,0.06),0_2px_6px_rgba(15,23,42,0.04)] dark:shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-[#EEF2FF] hover:bg-[#E0E7FF] dark:bg-surface-elevated border border-[#C7D2FE]/60 dark:border-border flex items-center justify-center text-[#4F46E5] dark:text-foreground shrink-0 transition-colors">
              <TrendingUp className="size-4" />
            </div>
            <div>
              <span className="text-xs text-[#334155] dark:text-foreground-secondary block font-medium">Total Balance (12m)</span>
              <span className="text-base font-bold text-[#101828] dark:text-foreground font-mono">₹1,28,450</span>
            </div>
          </div>
          <span className="text-xs font-bold text-[#101828] dark:text-foreground bg-[#F1F5F9] dark:bg-surface-elevated border border-[rgba(15,23,42,0.08)] dark:border-border px-2.5 py-0.5 rounded-full">
            +17%
          </span>
        </div>

        <div className="flex-1 rounded-2xl bg-white/96 dark:bg-[#121416] border border-[rgba(71,85,105,0.14)] dark:border-white/[0.12] p-3.5 shadow-[0_8px_24px_rgba(15,23,42,0.06),0_2px_6px_rgba(15,23,42,0.04)] dark:shadow-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-[#F6F2FF] hover:bg-[#EDE9FE] dark:bg-surface-elevated border border-[rgba(71,35,147,0.22)] dark:border-border flex items-center justify-center text-[#472393] dark:text-foreground shrink-0 transition-colors">
              <Sparkles className="size-4" />
            </div>
            <div>
              <span className="text-xs sm:text-sm text-[#172033] dark:text-foreground font-bold block font-mono">
                Trends & Insight
              </span>
              <span className="text-xs text-[#334155] dark:text-foreground-secondary line-clamp-1 font-medium">
                94% Recovery Resilience
              </span>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMethodologyOpen(true)}
            className="rounded-full text-xs h-8 px-3 shrink-0 bg-white text-[#472393] border border-[rgba(71,35,147,0.22)] hover:bg-[#F6F2FF] hover:border-[rgba(71,35,147,0.35)] dark:bg-transparent dark:text-foreground dark:border-border cursor-pointer"
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
