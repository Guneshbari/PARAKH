'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  FileText,
  PlusCircle,
  BarChart3,
  Sparkles,
  User,
  SlidersHorizontal,
  LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface NavLinkItem {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: string;
  highlight?: boolean;
}

interface SidebarProps {
  portal: 'user' | 'admin';
}

export function Sidebar({ portal }: SidebarProps) {
  const pathname = usePathname();

  const userLinks: NavLinkItem[] = [
    { href: '/user/dashboard', label: 'Credit Overview', icon: Home },
    { href: '/user/applications', label: 'My Applications', icon: FileText },
    { href: '/user/applications/new', label: 'New Assessment', icon: PlusCircle, highlight: true },
    { href: '/user/results/demo', label: 'Assessment Report', icon: BarChart3 },
    { href: '/user/profile', label: 'Profile & Data Sources', icon: User },
  ];

  const adminLinks: NavLinkItem[] = [
    { href: '/admin/dashboard', label: 'Cockpit Overview', icon: Home },
    { href: '/admin/applications', label: 'Review Queue', icon: FileText, badge: '4 Pending' },
    { href: '/admin/analytics', label: 'Portfolio Analytics', icon: BarChart3 },
    { href: '/admin/model-insights', label: 'Fairness & SHAP Insights', icon: Sparkles },
    { href: '/admin/profile', label: 'Underwriter Settings', icon: SlidersHorizontal },
  ];

  const links = portal === 'admin' ? adminLinks : userLinks;

  return (
    <aside className="hidden md:flex flex-col w-64 shrink-0 border-r border-white/[0.08] bg-[#060D1F] min-h-[calc(100vh-4rem)] p-4 justify-between">
      <div className="space-y-6">
        <div className="px-3 pt-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {portal === 'admin' ? 'Risk Underwriting' : 'Alternative Credit'}
          </span>
        </div>

        <nav className="space-y-1.5">
          {links.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;

            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'flex items-center justify-between px-3.5 py-2.5 rounded-2xl text-sm font-medium transition-all group',
                  isActive
                    ? 'bg-[#0E1F3D] text-white border border-cyan-500/30 shadow-sm'
                    : 'text-muted-foreground hover:text-white hover:bg-white/[0.04]'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      'size-4 transition-colors',
                      isActive ? 'text-cyan-400' : 'text-muted-foreground group-hover:text-white'
                    )}
                  />
                  <span>{link.label}</span>
                </div>

                {link.badge && (
                  <Badge variant="cyan" className="text-[10px] py-0 px-2">
                    {link.badge}
                  </Badge>
                )}

                {link.highlight && (
                  <span className="size-2 rounded-full bg-[#C8F451] animate-pulse shadow-[0_0_8px_rgba(200,244,81,0.5)]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Underwriting note / AI badge card at bottom */}
      <div className="p-3.5 rounded-2xl bg-[#0A162E] border border-white/[0.08] space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
          <Sparkles className="size-3.5 text-cyan-400" />
          <span>PARAKH Engine</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-snug">
          Volatility-aware assessment distinguishes healthy gig cycles from distress.
        </p>
      </div>
    </aside>
  );
}
