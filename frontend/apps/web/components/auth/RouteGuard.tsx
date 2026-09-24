'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from './AuthContext';
import { Sparkles } from 'lucide-react';
import { normalizeUserRole, UserRole } from '@parakh/types';

interface RouteGuardProps {
  children: React.ReactNode;
  requiredRole: 'applicant' | 'reviewer' | 'admin' | UserRole;
}

export function RouteGuard({ children, requiredRole }: RouteGuardProps) {
  const { user, role, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const requiredRoleUpper = normalizeUserRole(requiredRole);
  const currentRoleUpper = normalizeUserRole(role);

  const hasAccess =
    currentRoleUpper === requiredRoleUpper ||
    (currentRoleUpper === 'ADMIN' && (requiredRoleUpper === 'REVIEWER' || requiredRoleUpper === 'ADMIN'));

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated || !user) {
      const portalParam = typeof requiredRole === 'string' ? requiredRole.toLowerCase() : 'applicant';
      router.replace(
        `/login?role=${portalParam}&redirect=${encodeURIComponent(pathname)}`
      );
      return;
    }

    if (!hasAccess) {
      const portalParam = typeof requiredRole === 'string' ? requiredRole.toLowerCase() : 'applicant';
      router.replace(`/unauthorized?required=${portalParam}`);
    }
  }, [isAuthenticated, user, hasAccess, requiredRole, isLoading, router, pathname]);

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

  if (!isAuthenticated || !hasAccess) {
    return null;
  }

  return <>{children}</>;
}
