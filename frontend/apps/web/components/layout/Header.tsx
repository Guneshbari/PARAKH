'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sparkles, Bell, User, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function Header() {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith('/admin');
  const isUser = pathname.startsWith('/user');

  if (pathname === '/') {
    return null;
  }

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/[0.08] bg-[#060D1F]/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-600 text-slate-950 font-black shadow-md shadow-cyan-500/15 transition-transform group-hover:scale-105">
              <Sparkles className="size-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-black tracking-tight text-white flex items-center gap-1.5">
                PARAKH
                <span className="text-[10px] font-normal uppercase tracking-wider text-muted-foreground px-1.5 py-0.5 rounded-full bg-white/[0.05]">
                  AI
                </span>
              </span>
              <span className="text-[10px] text-muted-foreground -mt-1 font-medium">
                Credit for the Invisible
              </span>
            </div>
          </Link>

          {/* Active Portal Badge */}
          {isAdmin && (
            <Badge variant="cyan" className="ml-3 text-[11px] font-semibold">
              <ShieldCheck className="size-3 text-cyan-400" /> Underwriter Portal
            </Badge>
          )}
          {isUser && (
            <Badge variant="ai" className="ml-3 text-[11px] font-semibold">
              Borrower Portal
            </Badge>
          )}
        </div>

        {/* Portal Switcher & Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick portal navigation */}
          <div className="hidden md:flex items-center gap-1 bg-[#0A162E] p-1 rounded-full border border-white/[0.08]">
            <Link href="/user/dashboard">
              <Button
                variant={isUser ? 'pillOutline' : 'ghost'}
                size="sm"
                className="rounded-full text-xs h-7 px-3.5"
              >
                Borrower View
              </Button>
            </Link>
            <Link href="/admin/dashboard">
              <Button
                variant={isAdmin ? 'pillOutline' : 'ghost'}
                size="sm"
                className="rounded-full text-xs h-7 px-3.5"
              >
                Underwriter View
              </Button>
            </Link>
          </div>

          {/* Notification Button */}
          <Button
            variant="ghost"
            size="icon"
            className="rounded-full relative text-muted-foreground hover:text-white"
            aria-label="Notifications"
          >
            <Bell className="size-4" />
            <span className="absolute top-2 right-2 size-2 rounded-full bg-cyan-400 ring-2 ring-[#060D1F]" />
          </Button>

          {/* User profile pill */}
          <Link href={isAdmin ? '/admin/profile' : '/user/profile'}>
            <div className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-full bg-[#0A162E] border border-white/[0.08] hover:border-cyan-400/30 transition-colors cursor-pointer">
              <div className="size-7 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center text-white font-bold text-xs">
                <User className="size-3.5" />
              </div>
              <span className="text-xs font-medium text-slate-200 hidden sm:inline">
                {isAdmin ? 'Priya Sharma (UW-402)' : 'Arjun Verma'}
              </span>
            </div>
          </Link>
        </div>
      </div>
    </header>
  );
}
