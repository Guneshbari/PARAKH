'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from './AuthContext';
import { Sparkles } from 'lucide-react';

interface RouteGuardProps {
  children: React.ReactNode;
  requiredRole: 'applicant' | 'reviewer';
}

export function RouteGuard({ children, requiredRole }: RouteGuardProps) {
  const { user, role, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated || !user) {
      router.replace(
        `/login?role=${requiredRole}&redirect=${encodeURIComponent(pathname)}`
      );
      return;
    }

    if (role !== requiredRole) {
      router.replace(`/unauthorized?required=${requiredRole}`);
    }
  }, [isAuthenticated, user, role, requiredRole, isLoading, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex-1 min-h-[60vh] flex items-center justify-center">
        <div className="flex items-center gap-2 text-xs font-mono text-foreground-muted">
          <Sparkles className="size-4 animate-spin text-foreground" />
          <span>Verifying access clearance...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || role !== requiredRole) {
    return null;
  }

  return <>{children}</>;
}
