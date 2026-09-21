'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sparkles, Bell, User, ShieldCheck, Sun, Moon, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/theme/ThemeProvider';
import { useAuth } from '@/components/auth/AuthContext';

export function Header() {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith('/admin');
  const isUser = pathname.startsWith('/user');
  const { isDark, toggleTheme } = useTheme();
  const { user, role, logout } = useAuth();

  if (pathname === '/' || pathname === '/login' || pathname === '/signup' || pathname === '/unauthorized') {
    return null;
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-surface/90 backdrop-blur-md transition-colors duration-200">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8.5 w-8.5 items-center justify-center rounded-xl bg-foreground text-background font-black shadow-2xs transition-transform group-hover:scale-105">
              <Sparkles className="size-4" />
            </div>
            <div className="flex flex-col">
              <span className="text-base sm:text-lg font-black tracking-tight text-foreground flex items-center gap-1.5">
                PARAKH
                <span className="text-[10px] font-mono uppercase tracking-wider text-foreground-muted px-1.5 py-0.2 rounded-full bg-surface-elevated border border-border">
                  AI
                </span>
              </span>
              <span className="text-[10px] text-foreground-muted -mt-1 font-medium">
                Credit for the invisible.
              </span>
            </div>
          </Link>

          {/* Active Portal Badge */}
          {isAdmin && (
            <Badge variant="outline" className="ml-3 text-[11px] font-semibold hidden sm:inline-flex">
              <ShieldCheck className="size-3 text-foreground-muted mr-1" /> Credit Reviewer
            </Badge>
          )}
          {isUser && (
            <Badge variant="outline" className="ml-3 text-[11px] font-semibold hidden sm:inline-flex">
              Applicant Portal
            </Badge>
          )}
        </div>

        {/* Portal Switcher & Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick role-aware switcher */}
          <div className="hidden md:flex items-center gap-1 bg-surface-elevated p-1 rounded-full border border-border">
            <Link href="/user/dashboard">
              <Button
                variant={isUser ? 'secondary' : 'ghost'}
                size="sm"
                className="rounded-full text-xs h-7 px-3.5"
              >
                Applicant Dashboard
              </Button>
            </Link>
            <Link href="/admin/dashboard">
              <Button
                variant={isAdmin ? 'secondary' : 'ghost'}
                size="sm"
                className="rounded-full text-xs h-7 px-3.5"
              >
                Credit Review Dashboard
              </Button>
            </Link>
          </div>

          {/* Global Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="flex items-center justify-center size-8 rounded-full bg-surface-elevated border border-border text-foreground-secondary hover:text-foreground hover:bg-surface-highlight transition-colors cursor-pointer"
          >
            {isDark ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          </button>

          {/* Notification Button */}
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full relative text-foreground-secondary hover:text-foreground"
            aria-label="Notifications"
          >
            <Bell className="size-4" />
            <span className="absolute top-2 right-2 size-2 rounded-full bg-foreground ring-2 ring-surface" />
          </Button>

          {/* User profile pill & sign out */}
          <div className="flex items-center gap-1.5">
            <Link href={isAdmin ? '/admin/profile' : '/user/profile'}>
              <div className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-full bg-surface-elevated border border-border hover:border-border-strong transition-colors cursor-pointer">
                <div className="size-6.5 rounded-full bg-foreground text-background flex items-center justify-center font-bold text-xs">
                  <User className="size-3.5" />
                </div>
                <span className="text-xs font-medium text-foreground-secondary hidden sm:inline">
                  {user?.name || (isAdmin ? 'Priya Sharma (Reviewer)' : 'Arjun Verma')}
                </span>
              </div>
            </Link>

            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="rounded-full size-8 text-foreground-muted hover:text-destructive transition-colors cursor-pointer"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="size-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
