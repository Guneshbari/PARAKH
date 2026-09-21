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

  // Floating animation variants
  const leftFloatMotion: TargetAndTransition = shouldReduceMotion
    ? {}
    : {
        y: [-7, 7, -7],
        transition: {
          duration: 5.4,
          repeat: Infinity,
          ease: 'easeInOut' as const,
        },
      };

  const rightFloatMotion: TargetAndTransition = shouldReduceMotion
    ? {}
    : {
        y: [7, -7, 7],
        transition: {
          duration: 6.2,
          repeat: Infinity,
          ease: 'easeInOut' as const,
          delay: 0.4,
        },
      };

  return (
    <div className="relative w-full max-w-5xl mx-auto pt-6 sm:pt-10 pb-4 flex flex-col items-center justify-center">
      {/* Ambient Blue Radial Glow Behind Phone */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] sm:w-[720px] h-[380px] sm:h-[480px] bg-gradient-to-tr from-blue-600/35 via-cyan-500/20 to-purple-600/25 blur-3xl pointer-events-none rounded-full -z-10"
        aria-hidden="true"
      />

      {/* Main Composition Grid */}
      <div className="relative w-full flex items-center justify-center">
        {/* =========================================
            1. FLOATING LEFT CARD: TOTAL INCOME
           ========================================= */}
        <motion.div
          animate={leftFloatMotion}
          className="hidden lg:flex flex-col absolute left-2 xl:left-8 top-1/3 -translate-y-1/2 z-20 w-72 rounded-2xl bg-[#091D4A]/85 backdrop-blur-xl border border-cyan-400/30 p-4 shadow-[0_20px_50px_rgba(4,13,33,0.7)] text-slate-100"
        >
          <div className="flex items-center justify-between pb-2">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-xl bg-cyan-400/15 border border-cyan-400/30 flex items-center justify-center text-cyan-300 shadow-sm">
                <TrendingUp className="size-3.5" />
              </div>
              <span className="text-xs font-semibold text-slate-200">
                Total Income (12 weeks)
              </span>
            </div>
          </div>

          <div className="pt-1 flex items-baseline justify-between">
            <span className="text-2xl font-extrabold text-white font-mono tracking-tight">
              ₹1,28,450
            </span>
            <span className="text-[11px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-0.5">
              ↑ 12%
            </span>
          </div>
          <span className="text-[11px] text-slate-400 pb-3">vs. previous 12 weeks</span>

          {/* Glowing mini trend sparkline */}
          <div className="h-10 w-full pt-1">
            <svg viewBox="0 0 240 45" className="w-full h-full overflow-visible">
              <defs>
                <linearGradient id="incomeLineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#22D3EE" />
                  <stop offset="50%" stopColor="#2DD4BF" />
                  <stop offset="100%" stopColor="#34D399" />
                </linearGradient>
              </defs>
              <path
                d="M 0 35 Q 25 10 50 28 T 100 24 T 150 12 T 200 22 T 240 8"
                fill="none"
                stroke="url(#incomeLineGrad)"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              {/* Data points */}
              <circle cx="50" cy="28" r="3" fill="#22D3EE" />
              <circle cx="100" cy="24" r="3" fill="#2DD4BF" />
              <circle cx="150" cy="12" r="3" fill="#2DD4BF" />
              <circle cx="200" cy="22" r="3" fill="#34D399" />
              <circle cx="240" cy="8" r="4" fill="#34D399" className="animate-pulse" />
            </svg>
          </div>
        </motion.div>

        {/* =========================================
            2. CENTRAL IPHONE MOCKUP
           ========================================= */}
        <div className="relative z-10 w-[290px] sm:w-[320px] md:w-[340px] rounded-[48px] p-[10px] bg-gradient-to-b from-[#334155] via-[#1E293B] to-[#0F172A] shadow-[0_25px_70px_-15px_rgba(2,6,23,0.85),0_0_40px_rgba(34,211,238,0.15)] border border-white/15">
          {/* Inner Phone Screen */}
          <div className="relative w-full rounded-[38px] bg-[#0A1326] border border-white/[0.08] overflow-hidden text-slate-100 flex flex-col pt-3 pb-5 px-4 sm:px-5">
            {/* Dynamic Island Notch */}
            <div className="w-full flex items-center justify-between text-[11px] font-semibold text-slate-300 pb-2 px-2">
              <span>9:41</span>
              {/* Dynamic Island Pill */}
              <div className="h-5 w-24 rounded-full bg-black border border-white/10 flex items-center justify-end px-2 gap-1.5">
                <span className="size-2 rounded-full bg-[#10B981] animate-pulse" />
                <span className="size-2 rounded-full bg-[#3B82F6]/60" />
              </div>
              <div className="flex items-center gap-1.5">
                <Wifi className="size-3 text-slate-300" />
                <Battery className="size-3.5 text-slate-300" />
              </div>
            </div>

            {/* In-App Header */}
            <div className="pt-2 pb-3 flex items-center justify-between border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="size-6 rounded-lg bg-gradient-to-tr from-cyan-400 to-teal-400 flex items-center justify-center text-slate-950 font-black">
                  <Sparkles className="size-3.5" />
                </div>
                <span className="text-sm font-black tracking-tight text-white font-mono">
                  PARAKH
                </span>
              </div>
              <button
                type="button"
                aria-label="Scan QR or Share"
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.05]"
              >
                <ScanLine className="size-4" />
              </button>
            </div>

            {/* Greeting */}
            <div className="pt-3 pb-2">
              <h2 className="text-sm sm:text-base font-bold text-white tracking-tight">
                Good morning, Arjun
              </h2>
              <p className="text-[11px] text-slate-400">Here&apos;s your credit overview</p>
            </div>

            {/* Score Showcase Card */}
            <div className="p-3.5 rounded-2xl bg-[#0F1E3D]/90 border border-cyan-500/20 shadow-inner flex items-center justify-between gap-3">
              <div className="space-y-1.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-3xl sm:text-4xl font-black text-white font-mono tracking-tight">
                    742
                  </span>
                  <span className="text-xs text-slate-400 font-mono">/ 850</span>
                </div>
                <Badge
                  variant="mint"
                  className="text-[10px] py-0.5 px-2 bg-emerald-500/15 border-emerald-500/30 text-emerald-300 font-bold"
                >
                  <CheckCircle2 className="size-2.5 mr-1" />
                  LOWER RISK
                </Badge>
              </div>

              {/* Radial Gauge Visual */}
              <div className="relative size-16 sm:size-18 flex items-center justify-center shrink-0">
                <svg className="size-full -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="#1E293B"
                    strokeWidth="3.5"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="url(#radialScoreGrad)"
                    strokeWidth="3.5"
                    strokeDasharray="88"
                    strokeDashoffset="18"
                    strokeLinecap="round"
                  />
                  <defs>
                    <linearGradient id="radialScoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#22D3EE" />
                      <stop offset="100%" stopColor="#34D399" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-[11px] font-bold text-white font-mono">742</span>
                  <span className="text-[8px] text-slate-400 font-mono">/850</span>
                </div>
              </div>
            </div>

            {/* 3 Secondary Metrics Grid */}
            <div className="grid grid-cols-3 gap-2 pt-3 pb-2 text-center">
              <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <span className="text-sm sm:text-base font-extrabold text-white font-mono block">
                  21%
                </span>
                <span className="text-[9px] text-slate-400 leading-tight block pt-0.5">
                  Repayment Difficulty
                </span>
              </div>
              <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <span className="text-sm sm:text-base font-extrabold text-cyan-300 font-mono block">
                  87%
                </span>
                <span className="text-[9px] text-slate-400 leading-tight block pt-0.5">
                  Data Confidence
                </span>
              </div>
              <div className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <span className="text-sm sm:text-base font-extrabold text-purple-300 font-mono block">
                  94%
                </span>
                <span className="text-[9px] text-slate-400 leading-tight block pt-0.5">
                  Shock Recovery Rate
                </span>
              </div>
            </div>

            {/* Financial Health Section */}
            <div className="pt-2 border-t border-white/[0.06] space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 font-medium flex items-center gap-1 text-[11px]">
                  <Activity className="size-3 text-cyan-400" />
                  Your Financial Health
                </span>
                <span className="text-[10px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-1.5 py-0.2 rounded">
                  + Stable &gt;
                </span>
              </div>

              {/* Chart line */}
              <div className="h-12 w-full pt-1">
                <svg viewBox="0 0 260 40" className="w-full h-full overflow-visible">
                  <defs>
                    <linearGradient id="phoneWaveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#22D3EE" />
                      <stop offset="50%" stopColor="#2DD4BF" />
                      <stop offset="100%" stopColor="#34D399" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M 0 30 Q 30 15 65 24 T 130 16 T 195 26 T 260 12"
                    fill="none"
                    stroke="url(#phoneWaveGrad)"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <circle cx="65" cy="24" r="2.5" fill="#22D3EE" />
                  <circle cx="130" cy="16" r="2.5" fill="#2DD4BF" />
                  <circle cx="195" cy="26" r="2.5" fill="#2DD4BF" />
                  <circle cx="260" cy="12" r="3" fill="#34D399" />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* =========================================
            3. FLOATING RIGHT CARD: PARAKH AI INSIGHT
           ========================================= */}
        <motion.div
          animate={rightFloatMotion}
          className="hidden lg:flex flex-col absolute right-2 xl:right-8 top-1/3 -translate-y-1/2 z-20 w-80 rounded-2xl bg-[#14123E]/85 backdrop-blur-xl border border-purple-400/30 p-4 shadow-[0_20px_50px_rgba(4,13,33,0.7)] text-slate-100 space-y-2.5"
        >
          <div className="flex items-center justify-between pb-1">
            <div className="flex items-center gap-2">
              <div className="size-7 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 shadow-sm">
                <Sparkles className="size-3.5 text-purple-300" />
              </div>
              <span className="text-xs font-bold text-purple-200 tracking-wide uppercase font-mono text-[11px]">
                PARAKH AI Insight
              </span>
            </div>
            <Sparkles className="size-3.5 text-purple-400/60" />
          </div>

          <p className="text-xs text-slate-200 leading-relaxed font-medium">
            &ldquo;Your income shows strong stability with positive recovery across multiple
            platforms, indicating healthy cash flow resilience.&rdquo;
          </p>

          <div className="pt-2 border-t border-purple-500/20 flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsMethodologyOpen(true)}
              className="rounded-xl text-xs gap-1.5 h-7 px-3 bg-purple-500/15 hover:bg-purple-500/25 text-purple-200 border-purple-400/40 hover:border-purple-300 cursor-pointer transition-all shadow-sm"
            >
              <span>View Methodology</span>
              <ArrowRight className="size-3" />
            </Button>
            <span className="text-[10px] text-purple-300/60 font-mono">Explainable AI</span>
          </div>
        </motion.div>
      </div>

      {/* =========================================
          4. MOBILE COMPACT FLOATING CARDS STRIP
          (Shown below phone on small/medium screens)
         ========================================= */}
      <div className="flex lg:hidden flex-col sm:flex-row items-stretch gap-3 w-full max-w-md pt-5 px-4">
        {/* Mobile Income Card */}
        <div className="flex-1 rounded-2xl bg-[#091D4A]/85 backdrop-blur-xl border border-cyan-400/30 p-3.5 shadow-lg flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-cyan-400/15 border border-cyan-400/30 flex items-center justify-center text-cyan-300 shrink-0">
              <TrendingUp className="size-4" />
            </div>
            <div>
              <span className="text-[11px] text-slate-300 block">Total Income (12w)</span>
              <span className="text-base font-bold text-white font-mono">₹1,28,450</span>
            </div>
          </div>
          <span className="text-[10px] font-bold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-full">
            ↑ 12%
          </span>
        </div>

        {/* Mobile AI Insight Card */}
        <div className="flex-1 rounded-2xl bg-[#14123E]/85 backdrop-blur-xl border border-purple-400/30 p-3.5 shadow-lg flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 shrink-0">
              <Sparkles className="size-4" />
            </div>
            <div>
              <span className="text-[11px] text-purple-200 font-bold block font-mono">
                AI Volatility Signal
              </span>
              <span className="text-[11px] text-slate-300 line-clamp-1">
                94% Shock Recovery
              </span>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsMethodologyOpen(true)}
            className="rounded-full text-[11px] h-7 px-3 bg-purple-500/15 text-purple-200 border-purple-400/40 shrink-0 hover:bg-purple-500/25"
          >
            Methodology
          </Button>
        </div>
      </div>

      {/* Methodology Modal */}
      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />
    </div>
  );
}
