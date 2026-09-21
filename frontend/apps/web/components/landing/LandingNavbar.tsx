'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Sparkles, ArrowRight, Sun, Moon, Menu, X, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function LandingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);

  const navLinks = [
    { label: 'Home', href: '/', active: true },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Features', href: '#features' },
    { label: 'For Institutions', href: '#institutions' },
    { label: 'About', href: '#about' },
  ];

  return (
    <header className="relative z-30 w-full pt-4 sm:pt-6 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between h-14 sm:h-16 px-4 sm:px-6 rounded-full bg-[#07173D]/60 backdrop-blur-md border border-white/[0.08] shadow-lg">
        {/* =========================================
            1. BRAND / LOGO
           ========================================= */}
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-400 via-teal-400 to-emerald-400 text-slate-950 font-black shadow-md shadow-cyan-500/20 transition-transform group-hover:scale-105">
            <Sparkles className="size-4.5" />
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-black tracking-tight text-white flex items-center gap-1">
              PARAKH
            </span>
            <span className="text-[10px] text-cyan-200/70 -mt-1 font-medium tracking-wide">
              Credit for the Invisible
            </span>
          </div>
        </Link>

        {/* =========================================
            2. DESKTOP CENTER NAVIGATION LINKS
           ========================================= */}
        <nav className="hidden md:flex items-center gap-1.5 lg:gap-2">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className={`relative px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                link.active
                  ? 'text-white'
                  : 'text-slate-300 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              {link.label}
              {link.active && (
                <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22D3EE]" />
              )}
            </Link>
          ))}
        </nav>

        {/* =========================================
            3. RIGHT ACTIONS & PORTAL SWITCHERS
           ========================================= */}
        <div className="hidden sm:flex items-center gap-2.5">
          {/* Theme Toggle Pill */}
          <button
            type="button"
            onClick={() => setIsDark(!isDark)}
            aria-label="Toggle Theme"
            className="flex items-center justify-center size-8 rounded-full bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
          >
            {isDark ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          </button>

          {/* Borrower Portal CTA */}
          <Link href="/user/dashboard">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full text-xs font-semibold h-8 px-3.5 bg-blue-500/10 hover:bg-blue-500/20 text-cyan-200 border-cyan-400/30 hover:border-cyan-400/50 gap-1.5 transition-all"
            >
              <span>Borrower Portal</span>
              <ArrowRight className="size-3 text-cyan-400" />
            </Button>
          </Link>

          {/* Underwriter Portal CTA (Lime accent from reference) */}
          <Link href="/admin/dashboard">
            <Button
              size="sm"
              className="rounded-full text-xs font-bold h-8 px-4 bg-[#C8F451] hover:bg-[#B5E03E] text-[#0A192F] shadow-sm hover:shadow-md transition-all cursor-pointer border-0"
            >
              <span>Underwriter Portal</span>
            </Button>
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Open mobile menu"
          className="flex sm:hidden p-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/[0.05]"
        >
          {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {/* =========================================
          4. MOBILE EXPANDED MENU
         ========================================= */}
      {mobileMenuOpen && (
        <div className="sm:hidden mt-2 p-4 rounded-2xl bg-[#091D4A]/95 backdrop-blur-xl border border-white/10 shadow-2xl space-y-3 animate-in fade-in duration-200">
          <nav className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-xl text-sm font-medium ${
                  link.active
                    ? 'bg-cyan-500/15 text-cyan-300 font-bold'
                    : 'text-slate-300 hover:text-white hover:bg-white/[0.05]'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="pt-2 border-t border-white/[0.08] flex flex-col gap-2">
            <Link href="/user/dashboard" onClick={() => setMobileMenuOpen(false)}>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-center rounded-xl text-xs bg-blue-500/15 text-cyan-200 border-cyan-400/30 gap-1.5 h-9"
              >
                <span>Borrower Portal</span>
                <ArrowRight className="size-3 text-cyan-400" />
              </Button>
            </Link>

            <Link href="/admin/dashboard" onClick={() => setMobileMenuOpen(false)}>
              <Button
                size="sm"
                className="w-full justify-center rounded-xl text-xs font-bold bg-[#C8F451] hover:bg-[#B5E03E] text-[#0A192F] h-9 border-0"
              >
                <ShieldCheck className="size-3.5 mr-1" />
                <span>Underwriter Portal</span>
              </Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
