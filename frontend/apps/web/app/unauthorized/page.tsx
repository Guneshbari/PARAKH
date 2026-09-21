'use client';

import React, { Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { ShieldAlert, ArrowRight, User, ShieldCheck, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/components/auth/AuthContext';

function UnauthorizedContent() {
  const searchParams = useSearchParams();
  const attemptedRole = searchParams.get('required') || 'authorized';
  const { user, role, logout } = useAuth();

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background text-foreground p-4">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/25 text-destructive shadow-xs">
          <ShieldAlert className="size-7" />
        </div>

        <div className="space-y-2">
          <Badge variant="outline" className="text-[11px] font-mono border-destructive/30 text-destructive">
            SECURITY ROLE BOUNDARY
          </Badge>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Access Restricted
          </h1>
          <p className="text-xs text-foreground-secondary leading-relaxed max-w-sm mx-auto">
            {attemptedRole === 'reviewer'
              ? 'The requested section requires Certified Credit Reviewer authorization. Your current session does not have fiduciary reviewer clearance.'
              : 'The requested section requires an active Applicant account. Your current session does not match the required customer role.'}
          </p>
        </div>

        {user && (
          <div className="p-4 rounded-xl bg-surface-elevated border border-border text-left space-y-1">
            <span className="text-[10px] font-mono uppercase text-foreground-muted block">
              Current Active Identity
            </span>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-foreground">{user.name}</span>
              <Badge variant="default" className="text-[10px]">
                {role === 'reviewer' ? 'Credit Reviewer' : 'Applicant'}
              </Badge>
            </div>
            <span className="text-[11px] text-foreground-secondary block">{user.email}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-2 pt-2">
          {user && (
            <Link
              href={role === 'reviewer' ? '/admin/dashboard' : '/user/dashboard'}
              className="w-full sm:w-auto"
            >
              <Button className="w-full text-xs font-semibold gap-1.5 h-9">
                <span>Go to Your {role === 'reviewer' ? 'Credit Review Dashboard' : 'Applicant Dashboard'}</span>
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          )}

          <Link
            href={attemptedRole === 'reviewer' ? '/login?role=reviewer' : '/login?role=applicant'}
            className="w-full sm:w-auto"
          >
            <Button variant="outline" className="w-full text-xs font-semibold gap-1.5 h-9">
              <span>Sign In with Correct Role</span>
            </Button>
          </Link>
        </div>

        <div className="pt-4 border-t border-border flex items-center justify-center gap-4">
          <Link href="/" className="text-xs text-foreground-muted hover:text-foreground flex items-center gap-1">
            <Home className="size-3" /> Home
          </Link>
          {user && (
            <button
              onClick={logout}
              className="text-xs text-destructive hover:underline underline-offset-4 cursor-pointer"
            >
              Sign Out Session
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function UnauthorizedPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background" />}>
      <UnauthorizedContent />
    </Suspense>
  );
}
