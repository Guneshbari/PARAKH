'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Sparkles, Bell, User, ShieldCheck, Sun, Moon, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/components/theme/ThemeProvider';
import { useAuth } from '@/components/auth/AuthContext';
import { cn } from '@/lib/utils';

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  link: string;
}

const APPLICANT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'notif-app-1',
    title: 'PARAKH Assessment Ready',
    message: 'Your volatility-weighted credit score of 742 has been calculated.',
    time: '10m ago',
    unread: true,
    link: '/user/results/demo',
  },
  {
    id: 'notif-app-2',
    title: 'Cashflow Data Synced',
    message: 'Swiggy and Urban Company partner cashflows verified successfully.',
    time: '2h ago',
    unread: true,
    link: '/user/profile',
  },
  {
    id: 'notif-app-3',
    title: 'Application Active',
    message: 'Application APP-2024-001 is awaiting discretionary institutional review.',
    time: '1d ago',
    unread: false,
    link: '/user/applications',
  },
];

const REVIEWER_NOTIFICATIONS: NotificationItem[] = [
  {
    id: 'notif-rev-1',
    title: 'New Application in Queue',
    message: 'Arjun Verma (Score 742, Lower Est. Risk) requires review.',
    time: '5m ago',
    unread: true,
    link: '/admin/applications',
  },
  {
    id: 'notif-rev-2',
    title: 'Model Governance Audit',
    message: 'Model version 2.4-vol-tree passed Fairlearn demographic parity.',
    time: '1h ago',
    unread: true,
    link: '/admin/model-insights',
  },
  {
    id: 'notif-rev-3',
    title: 'Cashflow Volatility Alert',
    message: 'Gig cluster earnings increased +18% in Bengaluru delivery corridor.',
    time: '3h ago',
    unread: false,
    link: '/admin/analytics',
  },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { isDark, toggleTheme } = useTheme();
  const { user, role, logout } = useAuth();

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const notifRef = useRef<HTMLDivElement>(null);

  const userRole = user?.role || role;
  const isApplicant = userRole === 'applicant';
  const isReviewer = userRole === 'reviewer';

  useEffect(() => {
    setNotifications(isReviewer ? REVIEWER_NOTIFICATIONS : APPLICANT_NOTIFICATIONS);
  }, [isReviewer]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotificationsOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setNotificationsOpen(false);
      }
    }

    if (notificationsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('click', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [notificationsOpen]);

  const unreadCount = notifications.filter((n) => n.unread).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  const handleNotificationClick = (item: NotificationItem) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false } : n))
    );
    setNotificationsOpen(false);
    if (item.link) {
      router.push(item.link);
    }
  };

  if (pathname === '/' || pathname === '/login' || pathname === '/signup' || pathname === '/unauthorized') {
    return null;
  }

  return (
    <header className="sticky top-0 z-40 w-full h-16 border-b border-border bg-surface/90 backdrop-blur-md transition-colors duration-200">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-8.5 w-8.5 items-center justify-center rounded-xl bg-[#472393] text-white dark:bg-foreground dark:text-background font-black shadow-2xs transition-transform group-hover:scale-105">
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

          {/* Role-specific Active Portal Label */}
          {isReviewer && (
            <Badge variant="outline" className="ml-3 text-[11px] font-semibold hidden sm:inline-flex">
              <ShieldCheck className="size-3 text-foreground-muted mr-1" /> Credit Reviewer
            </Badge>
          )}
          {isApplicant && (
            <Badge variant="outline" className="ml-3 text-[11px] font-semibold hidden sm:inline-flex">
              Applicant Portal
            </Badge>
          )}
        </div>

        {/* Portal Navigation & Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Explicit Role-Aware Navigation: ONLY render the user's role dashboard */}
          {isApplicant && (
            <div className="hidden md:flex items-center bg-surface-elevated p-1 rounded-full border border-border">
              <Link href="/user/dashboard">
                <Button
                  variant={pathname.startsWith('/user') ? 'secondary' : 'ghost'}
                  size="sm"
                  className="rounded-full text-xs h-7 px-3.5"
                >
                  Applicant Dashboard
                </Button>
              </Link>
            </div>
          )}

          {isReviewer && (
            <div className="hidden md:flex items-center bg-surface-elevated p-1 rounded-full border border-border">
              <Link href="/admin/dashboard">
                <Button
                  variant={pathname.startsWith('/admin') ? 'secondary' : 'ghost'}
                  size="sm"
                  className="rounded-full text-xs h-7 px-3.5"
                >
                  Credit Review Dashboard
                </Button>
              </Link>
            </div>
          )}

          {/* Global Theme Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Toggle Theme"
            className="flex items-center justify-center size-8 rounded-full bg-surface-elevated border border-border text-foreground-secondary hover:text-foreground hover:bg-surface-highlight transition-colors cursor-pointer"
          >
            {isDark ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          </button>

          {/* Notification Button & Interactive Panel */}
          <div ref={notifRef} className="relative">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setNotificationsOpen((prev) => !prev)}
              className="rounded-full relative text-foreground-secondary hover:text-foreground cursor-pointer"
              aria-label="Notifications"
              aria-expanded={notificationsOpen}
              aria-haspopup="dialog"
            >
              <Bell className="size-4" />
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2 size-2 rounded-full bg-[#472393] dark:bg-foreground ring-2 ring-surface animate-pulse" />
              )}
            </Button>

            {notificationsOpen && (
              <div
                role="dialog"
                aria-label="Notifications Panel"
                className="absolute right-0 top-full mt-2 w-80 sm:w-96 rounded-2xl border border-border bg-surface dark:bg-surface-elevated shadow-card-elevated z-50 overflow-hidden text-foreground"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-highlight/30">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">Notifications</span>
                    {unreadCount > 0 && (
                      <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono">
                        {unreadCount} new
                      </Badge>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={markAllRead}
                      className="text-[11px] font-medium text-[#472393] dark:text-foreground hover:underline cursor-pointer"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-border/60">
                  {notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      className={cn(
                        'p-3.5 flex items-start gap-3 cursor-pointer transition-colors hover:bg-surface-highlight/50',
                        n.unread && 'bg-[#F1ECFF]/30 dark:bg-surface-highlight/30'
                      )}
                    >
                      <div
                        className={cn(
                          'size-2 rounded-full mt-1.5 shrink-0',
                          n.unread
                            ? 'bg-[#472393] dark:bg-foreground'
                            : 'bg-transparent'
                        )}
                      />
                      <div className="flex-1 min-w-0 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-semibold text-foreground truncate">
                            {n.title}
                          </p>
                          <span className="text-[10px] text-foreground-muted shrink-0">
                            {n.time}
                          </span>
                        </div>
                        <p className="text-[11px] text-foreground-secondary line-clamp-2 leading-relaxed">
                          {n.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User profile pill & sign out */}
          <div className="flex items-center gap-1.5">
            <Link href={isReviewer ? '/admin/profile' : '/user/profile'}>
              <div className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-full bg-surface-elevated border border-border hover:border-border-strong transition-colors cursor-pointer">
                <div className="size-6.5 rounded-full bg-[#472393] text-white dark:bg-foreground dark:text-background flex items-center justify-center font-bold text-xs">
                  <User className="size-3.5" />
                </div>
                <span className="text-xs font-medium text-foreground-secondary hidden sm:inline">
                  {user?.name || (isReviewer ? 'Priya Sharma (Reviewer)' : 'Arjun Verma')}
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
