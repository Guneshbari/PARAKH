'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { Sparkles, ArrowRight, Sun, Moon, Menu, X, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/components/theme/ThemeProvider';

export function LandingNavbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const { isDark, toggleTheme } = useTheme();
  const shouldReduceMotion = useReducedMotion();

  const navLinks = [
    { label: 'Home', href: '/', active: true },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Features', href: '#features' },
    { label: 'For Institutions', href: '#institutions' },
    { label: 'About', href: '#about' },
  ];

  return (
    <header className="relative z-30 w-full pt-4 sm:pt-6 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between h-14 sm:h-16 px-4 sm:px-6 rounded-full bg-surface/85 dark:bg-[#0D0E10]/85 backdrop-blur-md border border-border shadow-xs transition-colors duration-200">
        {/* Brand / Logo */}
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="flex h-8.5 w-8.5 items-center justify-center rounded-xl bg-foreground text-background font-black shadow-xs transition-transform group-hover:scale-105">
            <Sparkles className="size-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-base sm:text-lg font-black tracking-tight text-foreground flex items-center gap-1">
              PARAKH
            </span>
            <span className="text-[10px] text-foreground-muted -mt-1 font-medium tracking-wide">
              Credit for the invisible.
            </span>
          </div>
        </Link>

        {/* Desktop Center Navigation Links */}
        <nav
          className="hidden md:flex items-center gap-1 lg:gap-1.5"
          onMouseLeave={() => setHoveredIdx(null)}
        >
          {navLinks.map((link, idx) => {
            const isHovered = hoveredIdx === idx;
            return (
              <Link
                key={link.label}
                href={link.href}
                onMouseEnter={() => setHoveredIdx(idx)}
                onFocus={() => setHoveredIdx(idx)}
                onBlur={() => setHoveredIdx(null)}
                className={`relative px-3.5 py-1.5 rounded-full text-xs font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20 focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                  link.active
                    ? 'text-foreground font-semibold'
                    : isHovered
                    ? 'text-foreground'
                    : 'text-foreground-secondary'
                }`}
              >
                {/* Persistent active pill */}
                {link.active && (
                  <span
                    className="absolute inset-0 rounded-full bg-foreground/[0.07] dark:bg-white/[0.09] border border-foreground/[0.08] dark:border-white/15 -z-10 shadow-2xs"
                    aria-hidden="true"
                  />
                )}

                {/* Floating hover pill */}
                {!link.active && isHovered && (
                  <motion.span
                    layoutId={shouldReduceMotion ? undefined : 'navbar-hover-pill'}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={
                      shouldReduceMotion
                        ? { duration: 0.05 }
                        : { duration: 0.16, ease: 'easeOut' }
                    }
                    className="absolute inset-0 rounded-full bg-foreground/[0.04] dark:bg-white/[0.06] border border-foreground/[0.06] dark:border-white/10 -z-10"
                    aria-hidden="true"
                  />
                )}

                <span className="relative z-10">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right Actions & Portal Links */}
        <div className="hidden sm:flex items-center gap-2 sm:gap-2.5">
          {/* Global Theme Toggle Pill */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="flex items-center justify-center size-8 rounded-full bg-surface-elevated border border-border text-foreground-secondary hover:text-foreground hover:bg-surface-highlight transition-colors cursor-pointer"
          >
            {isDark ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          </button>

          {/* Applicant Portal CTA */}
          <Link href="/login?role=applicant">
            <Button
              variant="secondary"
              size="sm"
              className="rounded-full text-xs font-semibold h-8 px-3.5 gap-1.5"
            >
              <span>Applicant Portal</span>
              <ArrowRight className="size-3 text-foreground-muted" />
            </Button>
          </Link>

          {/* Credit Reviewer CTA */}
          <Link href="/login?role=reviewer">
            <Button
              variant="default"
              size="sm"
              className="rounded-full text-xs font-bold h-8 px-4 shadow-xs"
            >
              <ShieldCheck className="size-3.5 mr-1" />
              <span>Credit Reviewer</span>
            </Button>
          </Link>
        </div>

        {/* Mobile Hamburger Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Open mobile menu"
          className="flex sm:hidden p-2 rounded-xl text-foreground-secondary hover:text-foreground hover:bg-surface-highlight"
        >
          {mobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {/* Mobile Expanded Menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden mt-2 p-4 rounded-2xl bg-surface/95 dark:bg-[#0D0E10]/95 backdrop-blur-xl border border-border shadow-2xl space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <span className="text-xs font-bold text-foreground">Menu</span>
            <button
              type="button"
              onClick={toggleTheme}
              className="flex items-center gap-1.5 text-xs font-medium text-foreground-secondary px-2.5 py-1 rounded-full bg-surface-elevated border border-border"
            >
              {isDark ? <Sun className="size-3" /> : <Moon className="size-3" />}
              <span>{isDark ? 'Light Mode' : 'Dark Mode'}</span>
            </button>
          </div>

          <nav className="flex flex-col gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`px-3 py-2 rounded-xl text-sm font-medium ${
                  link.active
                    ? 'bg-surface-elevated text-foreground font-bold'
                    : 'text-foreground-secondary hover:text-foreground hover:bg-surface-highlight'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="pt-2 border-t border-border flex flex-col gap-2">
            <Link href="/login?role=applicant" onClick={() => setMobileMenuOpen(false)}>
              <Button
                variant="secondary"
                size="sm"
                className="w-full justify-center rounded-xl text-xs gap-1.5 h-9"
              >
                <span>Applicant Portal</span>
                <ArrowRight className="size-3 text-foreground-muted" />
              </Button>
            </Link>

            <Link href="/login?role=reviewer" onClick={() => setMobileMenuOpen(false)}>
              <Button
                variant="default"
                size="sm"
                className="w-full justify-center rounded-xl text-xs font-bold h-9"
              >
                <ShieldCheck className="size-3.5 mr-1" />
                <span>Credit Reviewer</span>
              </Button>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
