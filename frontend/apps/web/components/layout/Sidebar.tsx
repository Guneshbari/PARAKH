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
    { href: '/user/dashboard', label: 'Applicant Dashboard', icon: Home },
    { href: '/user/applications', label: 'My Applications', icon: FileText },
    { href: '/user/applications/new', label: 'New Application', icon: PlusCircle, highlight: true },
    { href: '/user/results/demo', label: 'Assessment Report', icon: BarChart3 },
    { href: '/user/profile', label: 'Applicant Profile', icon: User },
  ];

  const adminLinks: NavLinkItem[] = [
    { href: '/admin/dashboard', label: 'Credit Review Dashboard', icon: Home },
    { href: '/admin/applications', label: 'Applications for Review', icon: FileText, badge: '4 Pending' },
    { href: '/admin/analytics', label: 'Portfolio Analytics', icon: BarChart3 },
    { href: '/admin/model-insights', label: 'Model Insights & Governance', icon: Sparkles },
    { href: '/admin/profile', label: 'Reviewer Settings', icon: SlidersHorizontal },
  ];

  const links = portal === 'admin' ? adminLinks : userLinks;

  return (
    <aside className="hidden md:flex flex-col w-64 shrink-0 border-r border-border bg-surface dark:bg-[#0D0E10] min-h-[calc(100vh-4rem)] p-4 justify-between transition-colors duration-200">
      <div className="space-y-6">
        <div className="px-3 pt-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-foreground-muted">
            {portal === 'admin' ? 'Credit Review' : 'Applicant Portal'}
          </span>
        </div>

        <nav className="space-y-1">
          {links.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;

            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all group',
                  isActive
                    ? 'bg-surface-elevated text-foreground border border-border shadow-2xs font-semibold'
                    : 'text-foreground-secondary hover:text-foreground hover:bg-surface-highlight'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      'size-4 transition-colors',
                      isActive ? 'text-foreground' : 'text-foreground-muted group-hover:text-foreground'
                    )}
                  />
                  <span>{link.label}</span>
                </div>

                {link.badge && (
                  <Badge variant="outline" className="text-[10px] py-0 px-2">
                    {link.badge}
                  </Badge>
                )}

                {link.highlight && (
                  <span className="size-2 rounded-full bg-foreground shadow-xs animate-pulse" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Governance declaration card at bottom */}
      <div className="p-3.5 rounded-xl bg-surface-elevated border border-border space-y-1.5 shadow-2xs">
        <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
          <Sparkles className="size-3.5" />
          <span>PARAKH Governance</span>
        </div>
        <p className="text-[11px] text-foreground-muted leading-snug">
          Human-in-the-loop fiduciary review ensures algorithmic explanations support certified credit decisions.
        </p>
      </div>
    </aside>
  );
}
