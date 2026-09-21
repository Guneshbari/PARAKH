'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, FileText, Plus, BarChart3, User, LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  isAction?: boolean;
}

export function MobileNav() {
  const pathname = usePathname();
  const isAdmin = pathname.startsWith('/admin');

  const userNavItems: NavItem[] = [
    { href: '/user/dashboard', label: 'Home', icon: Home },
    { href: '/user/applications', label: 'Applications', icon: FileText },
    { href: '/user/applications/new', label: 'Assess', icon: Plus, isAction: true },
    { href: '/user/results/demo', label: 'Report', icon: BarChart3 },
    { href: '/user/profile', label: 'Profile', icon: User },
  ];

  const adminNavItems: NavItem[] = [
    { href: '/admin/dashboard', label: 'Overview', icon: Home },
    { href: '/admin/applications', label: 'Queue', icon: FileText },
    { href: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/admin/model-insights', label: 'Insights', icon: BarChart3 },
    { href: '/admin/profile', label: 'Profile', icon: User },
  ];

  const navItems = isAdmin ? adminNavItems : userNavItems;

  return (
    <div className="fixed bottom-4 inset-x-0 z-50 flex justify-center px-4 md:hidden pointer-events-none">
      <nav className="pointer-events-auto flex items-center justify-around gap-1 bg-[#0A162E]/95 backdrop-blur-xl border border-white/[0.12] rounded-full px-3 py-2 shadow-2xl shadow-black/80 w-full max-w-sm">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          if (item.isAction) {
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-label={item.label}
                className="flex items-center justify-center -my-3 group"
              >
                <div className="size-11 rounded-full bg-[#C8F451] text-[#07111F] flex items-center justify-center shadow-lg shadow-[#C8F451]/30 active:scale-95 transition-transform group-hover:scale-105">
                  <Icon className="size-5 font-bold" />
                </div>
              </Link>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex flex-col items-center justify-center py-1 px-3 rounded-full text-[10px] font-medium transition-colors',
                isActive
                  ? 'text-cyan-300 font-semibold'
                  : 'text-muted-foreground hover:text-white'
              )}
            >
              <Icon className="size-4 mb-0.5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
