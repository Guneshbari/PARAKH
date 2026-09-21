import React from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { RouteGuard } from '@/components/auth/RouteGuard';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteGuard requiredRole="reviewer">
      <div className="flex min-h-[calc(100vh-4rem)]">
        <Sidebar portal="admin" />
        <div className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          {children}
        </div>
      </div>
    </RouteGuard>
  );
}
