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
  LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/components/auth/AuthContext';

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
  const { user, role } = useAuth();
  const userRole = user?.role || role;
  const effectivePortal = userRole === 'applicant' ? 'user' : userRole === 'reviewer' ? 'admin' : portal;

  const userLinks: NavLinkItem[] = [
    { href: '/user/dashboard', label: 'Applicant Dashboard', icon: Home },
    { href: '/user/applications', label: 'My Applications', icon: FileText },
    { href: '/user/applications/new', label: 'New Application', icon: PlusCircle, highlight: true },
    { href: '/user/results/demo', label: 'Assessment Report', icon: BarChart3 },
    { href: '/user/profile', label: 'Applicant Profile', icon: User },
  ];

  const adminLinks: NavLinkItem[] = [
    { href: '/admin/dashboard', label: 'Credit Review Dashboard', icon: Home },
    { href: '/admin/applications', label: 'Applications', icon: FileText, badge: '4 Pending' },
    { href: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/admin/model-insights', label: 'Model Insights', icon: Sparkles },
    { href: '/admin/profile', label: 'Profile', icon: User },
  ];

  const links = effectivePortal === 'admin' ? adminLinks : userLinks;

  return (
    <aside className="hidden md:flex flex-col w-64 shrink-0 border-r border-[rgba(15,23,42,0.07)] dark:border-border bg-[#FFFFFF] dark:bg-[#0D0E10] h-full overflow-y-auto p-4 justify-between transition-colors duration-200 shadow-[0_4px_20px_rgba(15,23,42,0.04)] dark:shadow-none dashboard-sidebar">
      <div className="space-y-5">
        <div className="px-3 pt-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-foreground-muted/70">
            {effectivePortal === 'admin' ? 'Credit Review Rail' : 'Applicant Workspace'}
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
                  'flex items-center justify-between px-3.5 py-2.5 min-h-[42px] rounded-xl text-xs font-medium transition-all group',
                  isActive
                    ? 'bg-[#F1ECFF] text-[#472393] border border-[rgba(71,35,147,0.16)] font-semibold shadow-2xs dark:bg-surface-elevated dark:text-foreground dark:border-border'
                    : 'text-foreground-secondary hover:text-[#472393] hover:bg-[#F7F3FF] dark:hover:text-foreground dark:hover:bg-surface-highlight'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      'size-4 shrink-0 transition-colors',
                      isActive
                        ? 'text-[#472393] dark:text-foreground'
                        : 'text-foreground-muted group-hover:text-[#472393] dark:group-hover:text-foreground'
                    )}
                  />
                  <span className="truncate">{link.label}</span>
                </div>

                {link.badge && (
                  <Badge variant="outline" className="text-[10px] py-0 px-2 shrink-0 ml-1.5">
                    {link.badge}
                  </Badge>
                )}

                {link.highlight && (
                  <span className="size-2 rounded-full bg-[#472393] dark:bg-foreground shadow-xs animate-pulse shrink-0 ml-1.5" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Informational Session / User Identity Rail (Non-Navigation) */}
      <div className="pt-3.5 border-t border-[rgba(15,23,42,0.07)] dark:border-border space-y-2 mt-auto select-none cursor-default">
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-highlight/50 dark:bg-surface-elevated border border-border/60">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* AV / PS Initials Avatar Badge */}
            <div className="size-7 rounded-lg bg-surface-elevated text-foreground-secondary dark:bg-surface-highlight dark:text-foreground-secondary flex items-center justify-center font-bold text-[11px] shrink-0 border border-border shadow-2xs">
              {effectivePortal === 'admin' ? 'PS' : 'AV'}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-semibold text-foreground truncate">
                {user?.name || (effectivePortal === 'admin' ? 'Priya Sharma' : 'Arjun Verma')}
              </span>
              <span className="text-[10px] text-foreground-muted truncate">
                {effectivePortal === 'admin' ? 'Reviewer' : 'Verified Applicant'}
              </span>
            </div>
          </div>
          <span className="size-1.5 rounded-full bg-emerald-500 shrink-0 ml-1.5" title="Active Session" />
        </div>

        <div className="px-2 py-1 rounded-lg bg-surface-highlight/30 border border-border/40 text-[10px] text-foreground-muted flex items-center gap-1.5">
          <Sparkles className="size-3 text-foreground-muted shrink-0" />
          <span className="truncate">Human-in-the-Loop Governance</span>
        </div>
      </div>
    </aside>
  );
}
